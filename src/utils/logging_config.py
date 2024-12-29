"""
Этот модуль содержит функции для настройки логирования в проекте.
Поддерживает запись логов в файл с ротацией, а также цветное логирование в консоль.
"""


import logging
from logging.handlers import RotatingFileHandler
from colorlog import ColoredFormatter
from src.settings import LOGGING_SETTINGS

def setup_logger():
    """
    Настройка логирования для проекта с использованием параметров из settings.py.
    """
    log_file = LOGGING_SETTINGS["LOG_FILE"]
    max_bytes = LOGGING_SETTINGS["MAX_BYTES"]
    backup_count = LOGGING_SETTINGS["BACKUP_COUNT"]
    log_level = getattr(logging, LOGGING_SETTINGS["LOG_LEVEL"].upper(), logging.INFO)

    # Настройка формата для логов в файле
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    # Ротация файлов логов
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setFormatter(file_formatter)

    # Настройка цветного формата для консоли
    console_formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "white",
            "INFO": "cyan",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    # Настройка основного логгера
    logging.basicConfig(
        level=log_level,  # Уровень логирования
        handlers=[file_handler, console_handler]  # Логи в файл и консоль
    )

    logging.info("Логирование настроено. Логи сохраняются в '%s'", log_file)
