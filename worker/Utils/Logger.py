import logging
from pythonjsonlogger import jsonlogger
from Utils.constants import *


# Define the new JSON Logger class
class Logger:
    def __init__(self, account_key=None):
        """Initialize the JSON logger."""
        self.logger = logging.getLogger("JsonEngineLogger")
        self.logger.setLevel(logging.INFO)  # Set the log level

        # Add a stream handler for console output
        console_handler = logging.StreamHandler()

        # Use JsonFormatter for structured JSON logging
        formatter = jsonlogger.JsonFormatter(
            '%(levelname)s %(asctime)s %(message)s %(account_key)s'
        )
        console_handler.setFormatter(formatter)

        # Add the console handler to the logger
        self.logger.addHandler(console_handler)
        self.logger.propagate = False

        # Configure root logger so library loggers (e.g. "waveassist") are captured as JSON
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            root_handler = logging.StreamHandler()
            root_handler.setFormatter(formatter)
            root_logger.setLevel(logging.INFO)
            root_logger.addHandler(root_handler)

        # Suppress urllib3 logs if needed
        urllib3_logger = logging.getLogger('urllib3')
        urllib3_logger.setLevel(logging.CRITICAL)

        # Store default parameters
        self.account_key = account_key

    def log(self, level, message, **extra):
        """Log a message at the given level with optional extra context."""
        if not message or not message.strip():
            # Avoid logging if the message is empty or only whitespace
            return

        if hasattr(self.logger, level):
            log_method = getattr(self.logger, level)
            # Add default parameters to the extra context
            extra.setdefault("account_key", self.account_key)
            log_method(message, extra=extra)

    def info(self, message, **extra):
        """Log an info message with optional extra context."""
        self.log("info", message, **extra)

    def error(self, message, **extra):
        """Log an error message with optional extra context."""
        self.log("error", message, **extra)

