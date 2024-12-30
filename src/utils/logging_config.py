import logging
from logging.handlers import RotatingFileHandler
from colorlog import ColoredFormatter
from src.settings import LOGGING_SETTINGS


def setup_logger(
    log_file=None,
    log_level=None,
    max_bytes=None,
    backup_count=None,
):
    """
    Настройка логирования для проекта.
    :param log_file: Имя файла для логов. По умолчанию из LOGGING_SETTINGS.
    :param log_level: Уровень логирования. По умолчанию из LOGGING_SETTINGS.
    :param max_bytes: Максимальный размер файла логов. По умолчанию из LOGGING_SETTINGS.
    :param backup_count: Количество резервных копий логов. По умолчанию из LOGGING_SETTINGS.
    """
    # Используем настройки из LOGGING_SETTINGS, если параметры не переданы
    log_file = log_file or LOGGING_SETTINGS.get("LOG_FILE", "app.log")
    max_bytes = max_bytes or LOGGING_SETTINGS.get("MAX_BYTES", 10 * 1024 * 1024)
    backup_count = backup_count or LOGGING_SETTINGS.get("BACKUP_COUNT", 5)
    log_level = getattr(logging, (log_level or LOGGING_SETTINGS.get("LOG_LEVEL", "INFO")).upper(), logging.INFO)

    # Формат логов для файла
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Ротация файлов логов
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setFormatter(file_formatter)

    # Формат логов для консоли (цветной)
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
        level=log_level,
        handlers=[file_handler, console_handler]
    )

    if log_level == logging.DEBUG:
        logging.debug("Уровень логирования установлен на DEBUG.")

    logging.info("Логирование настроено. Логи сохраняются в '%s'", log_file)
