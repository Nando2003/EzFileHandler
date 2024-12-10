from config import Config
from utils import logger
from models import FileModel
from services import FileManager

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application, 
    ContextTypes, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters
)

import asyncio


class EzFileHandler:
    def __init__(self):
        self.application = Application.builder()\
            .token(Config.TOKEN)\
            .build()
        
        self.user_initialized = {}
        self.user_upload_time = {}
        self.file_manager = FileManager()
        self.handler_activated = False
    
    def setup_handlers(self):
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CommandHandler('menu', self.menu))
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.upload_file))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    def run(self):
        self.setup_handlers()
        logger.info('Booting EzFileHandler...')
        self.application.run_polling()
    
    def not_start_message(self, user_id: int):
        if user_id not in self.user_initialized or not self.user_initialized[user_id]:
            return 'Digite /start para começar!'
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message and (user := update.message.from_user):
            logger.info(f'Started by {user.id} - {user.full_name}')
            await update.message.reply_text(
                Config.START_MESSAGE.format(user.full_name),
                parse_mode="HTML"
            )
            self.user_initialized[user.id] = True
    
    async def menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message and (user := update.message.from_user):
            if message := self.not_start_message(user.id):
                await update.message.reply_text(message) # type: ignore
            
            else:
                keyboard = [
                    [InlineKeyboardButton("Enviar Arquivo", callback_data='upload')],
                    [InlineKeyboardButton("Listar Arquivos", callback_data='list_files')],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(  # type: ignore
                    "Escolha uma opção abaixo:",
                    reply_markup=reply_markup
                )
    
    async def file_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, file_name: str):
        if update.callback_query and (user := update.callback_query.from_user):
            if message := self.not_start_message(user.id):
                await update.callback_query.message.reply_text(message) # type: ignore
                
            else:
                keyboard = [
                    [InlineKeyboardButton("Baixar Arquivo", callback_data=f'download_{file_name}')],
                    [InlineKeyboardButton("Remover Arquivo", callback_data=f'remove_{file_name}')],
                    [InlineKeyboardButton("Voltar", callback_data='back')],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.callback_query.message.reply_text(  # type: ignore
                    f"Arquivo: <i><b>{file_name}</b></i>",
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
    
    async def upload_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message and (user := update.message.from_user):
            if message := self.not_start_message(user.id):
                await update.message.reply_text(message)
                
            else:
                if not self.handler_activated:
                    await update.message.reply_text(
                        "Clique em <i>'Enviar Arquivo'</i> no <strong><i>/menu</i></strong> para enviar um arquivo.",
                        parse_mode="HTML"
                    )
                    return
                
                if upload_file := update.message.document:
                    processing_message = await update.message.reply_text(
                        "Processando...",
                        parse_mode="HTML"
                    )
                    
                    try:
                        processing_states = ["Processando.", "Processando..", "Processando..."]
                        state_index = 0
                        success = False

                        while not success:
                            await processing_message.edit_text(processing_states[state_index])
                            state_index = (state_index + 1) % len(processing_states)
                            await asyncio.sleep(1)
                            
                            success = await self.file_manager.save_upload_file(upload_file, context.bot, user)

                        if success:
                            await processing_message.edit_text("Arquivo carregado com sucesso!")
                            self.application.remove_handler(self.file_handler)
                            self.handler_activated = False
                    
                    except Exception as e:
                        await processing_message.edit_text(f"Erro: {str(e)}")
    
    async def download_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, file_name: str):
        if update.callback_query and (user := update.callback_query.from_user):
            if message := self.not_start_message(user.id):
                await update.callback_query.message.reply_text(message) # type: ignore
                
            else:
                success = await self.file_manager.download_file(context.bot, user, file_name)
                
                if success:
                    await update.callback_query.answer()
                else:
                    await update.callback_query.answer()
                    await update.callback_query.message.reply_text( # type: ignore
                        f"<b>Erro:</b> não foi possível encontrar o arquivo <b><i>{file_name}</i></b>.",
                        parse_mode="HTML"
                    )

    async def list_user_files(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.callback_query and (user := update.callback_query.from_user):
            if message := self.not_start_message(user.id):
                await update.callback_query.message.reply_text(message) # type: ignore
                
            else:
                files = await self.file_manager.list_user_files(user)
                
                if files:
                    keyboard = [
                        [InlineKeyboardButton(f'{file.file_name} - {FileModel.format_file_size(file.file_size)}', callback_data=f'file_{file.file_name}')] for file in files
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    total_user_size = self.file_manager.get_user_storage_usage(user.id)
                    
                    await update.callback_query.message.reply_text( # type: ignore
                        f"<b>{user.first_name}</b>, seus arquivos são esses: \n<i>Espaço disponível: <b>{FileModel.format_file_size(total_user_size)}/50.00 MB</b></i>", 
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    ) 
                else:
                    await update.callback_query.message.reply_text("Nenhum arquivo encontrado.") # type: ignore
    
    async def remove_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, file_name: str):
        if update.callback_query and (user := update.callback_query.from_user):
            if message := self.not_start_message(user.id):
                await update.callback_query.message.reply_text(message) # type: ignore
                
            else:
                user_size_before = self.file_manager.get_user_storage_usage(user.id)
                files = await self.file_manager.remove_file(context.bot, user, file_name)
                
                if files:
                    user_size_after = self.file_manager.get_user_storage_usage(user.id)
                    
                    await update.callback_query.message.reply_text( # type: ignore
                        f"Arquivo <i><b>{file_name}</b></i>, removido das suas dependencias. \nLimpando o espaço de <i><b>{FileModel.format_file_size(user_size_before - user_size_after)}</b></i>", 
                        parse_mode="HTML"
                    ) 
                else:
                    await update.callback_query.message.reply_text("Erro ao remover o arquivo.") # type: ignore
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        
        if query:
            await query.answer()
            
            if query.data == 'upload':
                if update.callback_query and (user := update.callback_query.from_user):
                    if message := self.not_start_message(user.id):
                        await update.callback_query.message.reply_text(message)  # type: ignore
                    else:
                        await update.callback_query.message.reply_text(  # type: ignore
                            "<strong>Por favor, envie o arquivo no chat dentro de 40 segs.</strong>",
                            parse_mode="HTML"
                        )
                        
                        self.file_handler = MessageHandler(filters.Document.ALL, self.upload_file)
                        self.application.add_handler(self.file_handler)
                        self.handler_activated = True
                        
                        asyncio.create_task(self.remove_upload_handler_after_timeout(update, self.file_handler))
                        
                  
            elif query.data == 'list_files':
                await self.list_user_files(update, context)
                
            elif isinstance(query.data, str) and query.data.startswith('file_'):
                file_name = query.data[len('file_'):]
                await self.file_menu(update, context, file_name)
            
            elif isinstance(query.data, str) and query.data.startswith('download_'):
                file_name = query.data[len('download_'):]
                await self.download_file(update, context, file_name)
                await query.message.delete() # type: ignore
            
            elif isinstance(query.data, str) and query.data.startswith('remove_'):
                file_name = query.data[len('remove_'):]
                await self.remove_file(update, context, file_name)
                await query.message.delete() # type: ignore
            
            elif query.data == 'back':
                await query.message.delete() # type: ignore
                
    async def remove_upload_handler_after_timeout(self, update: Update, file_handler: MessageHandler):
        await asyncio.sleep(40)
        self.application.remove_handler(file_handler)
        self.handler_activated = False 
        await update.callback_query.message.reply_text(  # type: ignore
            "Tempo expirado!",
            parse_mode="HTML"
        )