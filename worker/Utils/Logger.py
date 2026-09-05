import logging
import os
import socket
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger
from Utils.constants import *


class ProcessFileHandler(logging.Handler):
    """Each prefork worker owns its file so rotations cannot race."""
    def __init__(self, directory, formatter):
        super().__init__()
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.setFormatter(formatter)
        self.pid = None
        self.output = None

    def emit(self, record):
        try:
            if self.pid != os.getpid():
                if self.output:
                    self.output.close()
                self.pid = os.getpid()
                for path in self.directory.glob('worker-*.log*'):
                    if path.stat().st_mtime < time.time() - 7 * 86400:
                        path.unlink(missing_ok=True)
                path = self.directory / f'worker-{socket.gethostname()}-{self.pid}.log'
                self.output = RotatingFileHandler(path, maxBytes=2_000_000, backupCount=3)
                self.output.setFormatter(self.formatter)
            self.output.emit(record)
        except Exception:
            self.handleError(record)


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
        if os.getenv('WAVEASSIST_LOG_DIR'):
            self.logger.addHandler(ProcessFileHandler(os.environ['WAVEASSIST_LOG_DIR'], formatter))
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
