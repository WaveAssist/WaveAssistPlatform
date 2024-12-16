import logging
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger
from Utils.constants import *
# Define the new JSON Logger class
class Logger:
    def __init__(self, log_file_path=PROJECT_LOGS_PATH, max_bytes=100000, backup_count=100, account_key=None):
        """Initialize the JSON logger."""
        self.logger = logging.getLogger("JsonEngineLogger")
        self.logger.setLevel(logging.INFO)  # Set the log level

        # Add a rotating file handler
        handler = RotatingFileHandler(log_file_path, maxBytes=max_bytes, backupCount=backup_count)

        # Use JsonFormatter for structured JSON logging
        formatter = jsonlogger.JsonFormatter(
            '%(levelname)s %(asctime)s %(message)s %(account_key)s'
        )
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)

        # Suppress urllib3 logs if needed
        urllib3_logger = logging.getLogger('urllib3')
        urllib3_logger.setLevel(logging.CRITICAL)

        # Store default parameters
        self.account_key = account_key

    def log(self, level, message, **extra):
        if not message or not message.strip():
            # Avoid logging if the message is empty or only whitespace
            return

        """Log a message at the given level with optional extra context."""
        if hasattr(self.logger, level):
            log_method = getattr(self.logger, level)
            # Add default parameters to the extra context
            extra.setdefault("account_key", self.account_key)
            log_method(message, extra=extra)

    def info(self,message, **extra):
        """Log an info message with optional extra context."""
        self.log("info", message, **extra)

    def error(self, message, **extra):
        """Log an error message with optional extra context."""
        self.log("error", message, **extra)
