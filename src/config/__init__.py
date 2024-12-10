class Config:
    # LOGGER
    from datetime import datetime
    LOG_NAME = datetime.now().strftime("%d-%m-%Y_%Hh-%Mm-%Ss")
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    
    # TOKEN 
    import os
    from dotenv import load_dotenv
    load_dotenv('./.env')
    TOKEN = os.getenv('TOKEN', '')
    
    # FILE
    STORAGE_PATH = './files'
    
    # MESSAGES
    START_MESSAGE = "<strong>Bem-vindo ao EzFileHandler, {}!</strong>\n\nEsse robô 🤖 foi produzido para servir <strong>você</strong> de maneira eficiente, facilitando o <i>upload</i> e <i>download</i> de arquivos 📁. \n\nDigite <strong><i>/menu</i></strong> para ver as opções."
    