import logging
import logging.handlers
from config import Config


class __Logger:
    logger = logging.getLogger(Config.LOG_NAME)
    logger.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(Config.LOG_FORMAT)

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    

logger = __Logger.logger

