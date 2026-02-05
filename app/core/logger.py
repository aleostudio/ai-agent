import logging
from app.core.config import settings

class MCPDisconnectFilter(logging.Filter):
    """Filter MCP disconnection errors."""
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage().lower()
        if "peer closed connection" in msg:
            return False
        if "sse_reader" in msg:
            return False
        if "incomplete chunked read" in msg:
            return False
        return True

def init_logger():

    # Log level
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    logger = logging.getLogger(settings.APP_NAME)
    logger.setLevel(level)

    # Custom formatter
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    logger.addHandler(console_handler)

    # Stop MCP disconnection errors
    logging.getLogger("mcp.client.sse").setLevel(logging.CRITICAL)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)    
    for logger_name in ["mcp", "httpx", "httpcore"]:
        logging.getLogger(logger_name).addFilter(MCPDisconnectFilter())

    return logger


logger = init_logger()
