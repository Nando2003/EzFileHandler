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
            .read_timeout(30)\
            .write_timeout(30)\
            .connect_timeout(30)\
            .pool_timeout(30)\
            .build()
        
        self.user_initialized = {}
        self.user_upload_states = {}
        self.file_manager = FileManager()
    
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
            logger.warning(f'User {user_id} tried to access without initialization.')
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
            logger.info(f'User {user.id} accessed /menu.')
            if message := self.not_start_message(user.id):
                await update.message.reply_text(message)  # type: ignore
            
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
        logger.info(f'File menu accessed for file: {file_name}')
        if update.callback_query and (user := update.callback_query.from_user):
            if message := self.not_start_message(user.id):
                await update.callback_query.message.reply_text(message)  # type: ignore
                
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
            logger.info(f'User {user.id} attempted to upload a file.')
            if message := self.not_start_message(user.id):
                await update.message.reply_text(message)
                
            else:
                if not self.user_upload_states.get(user.id, False):
                    logger.warning(f'User {user.id} tried to upload without permission.')
                    await update.message.reply_text(
                        "Clique em <i>'Enviar Arquivo'</i> no <strong><i>/menu</i></strong> para enviar um arquivo.",
                        parse_mode="HTML"
                    )
                    return
                
                if upload_file := update.message.document:
                    logger.info(f'Processing file upload: {upload_file.file_name}')
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

                        if success == 0:
                            logger.info(f'File {upload_file.file_name} uploaded successfully.')
                            await processing_message.edit_text("Arquivo carregado com sucesso!")
                    
                    except Exception as e:
                        logger.error(f'Error during file upload: {str(e)}')
                        await processing_message.edit_text(f"Erro: {str(e)}")

                    self.user_upload_states[user.id] = False
                    
    async def download_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, file_name: str):
        logger.info(f'User requested to download file: {file_name}')
        if update.callback_query and (user := update.callback_query.from_user):
            if message := self.not_start_message(user.id):
                await update.callback_query.message.reply_text(message)  # type: ignore
                
            else:
                success = await self.file_manager.download_file(context.bot, user, file_name)
                
                if success:
                    logger.info(f'File {file_name} downloaded successfully.')
                    await update.callback_query.answer()
                else:
                    logger.warning(f'Failed to download file: {file_name}')
                    await update.callback_query.answer()
                    await update.callback_query.message.reply_text(  # type: ignore
                        f"<b>Erro:</b> não foi possível encontrar o arquivo <b><i>{file_name}</i></b>.",
                        parse_mode="HTML"
                    )

    async def list_user_files(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info('Listing user files.')
        if update.callback_query and (user := update.callback_query.from_user):
            if message := self.not_start_message(user.id):
                await update.callback_query.message.reply_text(message)  # type: ignore
                
            else:
                try:
                    files = await self.file_manager.list_user_files(user)
                    logger.info(f'Found {len(files)} files for user {user.id}.')
                    
                    if files:
                        keyboard = [
                            [InlineKeyboardButton(f'{file.file_name} - {FileModel.format_file_size(file.file_size)}', callback_data=f'file_{file.file_name}')] for file in files
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        total_user_size = self.file_manager.get_user_storage_usage(user.id)
                        
                        await update.callback_query.message.reply_text(  # type: ignore
                            f"<b>{user.first_name}</b>, seus arquivos são esses: \n<i>Espaço disponível: <b>{FileModel.format_file_size(total_user_size)}/50.00 MB</b></i>", 
                            reply_markup=reply_markup,
                            parse_mode="HTML"
                        )
                    else:
                        logger.info(f'No files found for user {user.id}.')
                        await update.callback_query.message.reply_text("Nenhum arquivo encontrado.")  # type: ignore
                except Exception as e:
                    logger.error(f'Error while listing files for user {user.id}: {str(e)}')
    
    async def remove_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, file_name: str):
        logger.info(f'Remove file request for: {file_name}')
        if update.callback_query and (user := update.callback_query.from_user):
            if message := self.not_start_message(user.id):
                await update.callback_query.message.reply_text(message)  # type: ignore
                
            else:
                try:
                    user_size_before = self.file_manager.get_user_storage_usage(user.id)
                    success = await self.file_manager.remove_file(context.bot, user, file_name)
                    
                    if success:
                        user_size_after = self.file_manager.get_user_storage_usage(user.id)
                        freed_space = FileModel.format_file_size(user_size_before - user_size_after)
                        logger.info(f'File {file_name} removed successfully for user {user.id}, freed {freed_space}.')
                        
                        await update.callback_query.message.reply_text(  # type: ignore
                            f"Arquivo <i><b>{file_name}</b></i> removido. \nEspaço liberado: <i><b>{freed_space}</b></i>", 
                            parse_mode="HTML"
                        )
                    else:
                        logger.warning(f'Failed to remove file {file_name} for user {user.id}.')
                        await update.callback_query.message.reply_text("Erro ao remover o arquivo.")  # type: ignore
                except Exception as e:
                    logger.error(f'Error while removing file {file_name} for user {user.id}: {str(e)}')
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info('Handling callback query.')
        query = update.callback_query
        
        if query:
            await query.answer()
            logger.info(f'Callback data: {query.data}')
            
            try:
                if query.data == 'upload':
                    if update.callback_query and (user := update.callback_query.from_user):
                        if message := self.not_start_message(user.id):
                            await update.callback_query.message.reply_text(message)  # type: ignore
                        else:
                            self.user_upload_states[user.id] = True
                            logger.info(f'Upload enabled for user {user.id}.')
                            
                            await query.message.reply_text(  # type: ignore
                                "<strong>Por favor, envie o arquivo no chat dentro de 80 segundos.</strong>",
                                parse_mode="HTML"
                            )
                            
                            # Desativar permissão após 45 segundos
                            asyncio.create_task(self.disable_upload_after_timeout(user.id))
                      
                elif query.data == 'list_files':
                    await self.list_user_files(update, context)
                    
                elif isinstance(query.data, str) and query.data.startswith('file_'):
                    file_name = query.data[len('file_'):]
                    await self.file_menu(update, context, file_name)
                
                elif isinstance(query.data, str) and query.data.startswith('download_'):
                    file_name = query.data[len('download_'):]
                    await self.download_file(update, context, file_name)
                    await query.message.delete()  # type: ignore
                
                elif isinstance(query.data, str) and query.data.startswith('remove_'):
                    file_name = query.data[len('remove_'):]
                    await self.remove_file(update, context, file_name)
                    await query.message.delete()  # type: ignore
                
                elif query.data == 'back':
                    logger.info('User selected "Back" option.')
                    await query.message.delete()  # type: ignore
            except Exception as e:
                logger.error(f'Error while handling callback: {str(e)}')
                
    async def disable_upload_after_timeout(self, user_id: int):
        logger.info(f'Setting upload timeout for user {user_id}.')
        await asyncio.sleep(80)
        self.user_upload_states[user_id] = False
        logger.info(f'Upload disabled for user {user_id} after timeout.')