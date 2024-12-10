import os
from typing import Literal
from telegram import (
    Bot,
    User,
    Document,
    InputFile
)

from config import Config
from models.file_model import FileModel


class FileManager:
    MAX_STORAGE_PER_USER = 50 * 1024 * 1024
    MAX_FILE_SIZE = 4 * 1024 * 1024
    
    def __init__(self):
        self.STORAGE_PATH = os.path.abspath(Config.STORAGE_PATH)
        os.makedirs(self.STORAGE_PATH, exist_ok=True)
        self.user_file_cache = {}
        
    async def save_upload_file(self, document: Document, bot: Bot, user: User) -> Literal[0]:
        user_storage = os.path.join(self.STORAGE_PATH, f'{user.id}')

        if not os.path.exists(user_storage):
            os.makedirs(user_storage)

        current_usage = self.get_user_storage_usage(user.id)
        file_id = document.file_id
        file_name = document.file_name

        if not file_name:
            raise FileNotFoundError("Erro no download do arquivo!")

        if document.file_size > self.MAX_FILE_SIZE: # type: ignore
            raise Exception("Arquivo excede o tamanho máximo permitido de 20 KB.")

        upload_file = await bot.get_file(file_id)

        file_path = os.path.join(user_storage, file_name)
        await upload_file.download_to_drive(file_path)

        file_size = os.path.getsize(file_path)
        if current_usage + file_size > self.MAX_STORAGE_PER_USER:
            raise Exception("Limite de armazenamento excedido.")

        self._add_to_cache(user, file_name, file_size, file_path)
        return 0

    async def list_user_files(self, user: User) -> list[FileModel]:
        if user.id in self.user_file_cache:
            return self.user_file_cache[user.id]
        
        user_storage = os.path.join(self.STORAGE_PATH, f'{user.id}')
        file_models = []
        
        if os.path.exists(user_storage):
            for file_name in os.listdir(user_storage):
                file_path = os.path.join(user_storage, file_name)
                file_size = os.path.getsize(file_path)
                file_models.append(FileModel(file_name, file_size, file_path))
        
        self.user_file_cache[user.id] = file_models
        return file_models
    
    async def download_file(self, bot: Bot, user: User, file_name: str) -> bool:
        try:
            user_storage = os.path.join(self.STORAGE_PATH, f'{user.id}')
            file_path = os.path.join(user_storage, file_name)
            print(file_path)
            if os.path.exists(file_path):
                with open(file_path, 'rb') as file:
                    await bot.send_document(
                        chat_id=user.id,
                        document=InputFile(file, filename=file_name),
                        caption=f"Aqui está o seu arquivo: {file_name}"
                    )
                return True
            else:
                return False
            
        except Exception:
            return False
    
    async def remove_file(self, bot: Bot, user: User, file_name: str) -> bool:
        try:
            user_storage = os.path.join(self.STORAGE_PATH, f'{user.id}')
            file_path = os.path.join(user_storage, file_name)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            
            return False
        
        except Exception:
            return False
    
    def get_user_storage_usage(self, user_id: int) -> int:
        user_storage = os.path.join(self.STORAGE_PATH, f'{user_id}')
        total_size = 0
        if os.path.exists(user_storage):
            for file_name in os.listdir(user_storage):
                file_path = os.path.join(user_storage, file_name)
                total_size += os.path.getsize(file_path)
        return total_size
    
    def _add_to_cache(self, user: User, file_name: str, file_size: int, file_path: str):
        if user.id not in self.user_file_cache:
            self.user_file_cache[user.id] = []
        self.user_file_cache[user.id].append(FileModel(file_name, file_size, file_path))