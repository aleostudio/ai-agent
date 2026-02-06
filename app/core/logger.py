import logging
import sys
from app.core.config import settings

# MCP disconnection errors filter
class MCPDisconnectFilter(logging.Filter):
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

    # Custom formatter
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Console Handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    # Root logger (uvicorn included)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]

    # Stop verbose logger
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Stop MCP disconnection errors
    logging.getLogger("mcp.client.sse").setLevel(logging.CRITICAL)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)    
    for logger_name in ["mcp", "httpx", "httpcore"]:
        logging.getLogger(logger_name).addFilter(MCPDisconnectFilter())

    # Logger app
    logger = logging.getLogger(settings.APP_NAME)
    logger.setLevel(level)

    return logger


# Instance
logger = init_logger()
