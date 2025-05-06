import logging
import sys
from typing import Optional, Union

# ANSI escape codes for colors
LOG_COLORS = {
    "DEBUG": "\033[92m",  # Green
    "INFO": "\033[94m",  # Blue
    "WARNING": "\033[93m",  # Yellow
    "ERROR": "\033[91m",  # Red
    "CRITICAL": "\033[91m",  # Red
}
RESET_COLOR = "\033[0m"


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname
        if levelname in LOG_COLORS:
            colored_levelname = f"{LOG_COLORS[levelname]}[{levelname}]{RESET_COLOR}"
        else:
            colored_levelname = f"[{levelname}]"
        original = self._style._fmt
        self._style._fmt = original.replace("[%(levelname)s]", colored_levelname)
        result = super().format(record)
        self._style._fmt = original  # restore for future calls
        return result


class Logger:
    _instances = {}

    def __new__(cls, name: str = __name__):
        if name not in cls._instances:
            cls._instances[name] = super(Logger, cls).__new__(cls)
            cls._instances[name]._initialized = False
        return cls._instances[name]

    def __init__(
        self,
        name: str = __name__,
        log_file: Optional[str] = None,
        level: Union[int, str] = logging.INFO,
        fmt: str = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        stream: Union[None, str, object] = "stdout",
    ):
        if self._initialized:
            return
        self.logger = logging.getLogger(name)

        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)

        self.logger.setLevel(level)

        formatter = ColorFormatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

        if stream:
            stream_obj = {"stdout": sys.stdout, "stderr": sys.stderr}.get(
                stream, stream
            )
            sh = logging.StreamHandler(stream_obj)
            sh.setFormatter(formatter)
            self.logger.addHandler(sh)

        if log_file:
            fh = logging.FileHandler(log_file)
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

        self._initialized = True

    def get_logger(self) -> logging.Logger:
        return self.logger
