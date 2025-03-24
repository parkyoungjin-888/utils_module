import os
import json
import logging
from logging.handlers import RotatingFileHandler
from threading import Lock


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'time': self.formatTime(record, self.datefmt),
            'name': record.name,
            'level': record.levelname
        }

        if isinstance(record.msg, dict):
            log_record.update(record.msg)
        else:
            log_record["message"] = record.getMessage()

        return json.dumps(log_record, ensure_ascii=False)


class LoggerSingleton:
    _instances = {}
    _lock = Lock()

    @staticmethod
    def get_logger(name: str,
                   file_name: str = None, max_file_size: int = 1*1024*1024, file_count: int = 10,
                   level=logging.INFO) -> logging.Logger:
        if file_name is not None:
            log_dir = os.path.dirname(file_name)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

        with LoggerSingleton._lock:
            if name not in LoggerSingleton._instances:
                LoggerSingleton._instances[name] = LoggerSingleton._create_logger(name, file_name, max_file_size, file_count, level)
            return LoggerSingleton._instances[name]

    @staticmethod
    def _create_logger(name: str,
                       file_name: str = None, max_file_size: int = 1*1024*1024, file_count: int = 10,
                       level=logging.INFO) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(level)

        json_formatter = JsonFormatter()

        if file_name is not None:
            file_handler = RotatingFileHandler(file_name, maxBytes=max_file_size, backupCount=file_count)
            file_handler.setFormatter(json_formatter)
            logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(json_formatter)
        logger.addHandler(stream_handler)

        return logger
