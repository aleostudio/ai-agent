import logging
from app.core.config import settings

def init_logger():

    # Log level
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    logger = logging.getLogger(settings.APP_NAME)
    logger.setLevel(level)

    # Custom formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    logger.addHandler(console_handler)

    return logger

logger = init_logger()