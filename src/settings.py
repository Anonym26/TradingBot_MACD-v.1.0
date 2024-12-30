"""
Этот модуль содержит основные настройки проекта, включая параметры MACD,
депозита, стратегии, анализа и логирования. Эти настройки используются
для конфигурации поведения бота.
"""

# Настройки MACD
MACD_SETTINGS = {
    "FAST": 12,  # Быстрая линия
    "SLOW": 26,  # Медленная линия
    "SIGNAL": 9  # Сигнальная линия
}

# Настройки депозита
DEPOSIT_SETTINGS = {
    "USE_TOTAL_BALANCE": False,  # True - использовать весь баланс USDT, False - фиксированный депозит
    "DEPOSIT": 100  # Фиксированный депозит в USDT (используется, если USE_TOTAL_BALANCE=False)
}

# Проверка на конфликт настроек депозита
if not DEPOSIT_SETTINGS["USE_TOTAL_BALANCE"] and DEPOSIT_SETTINGS["DEPOSIT"] <= 0:
    raise ValueError("Значение 'DEPOSIT' должно быть больше 0, если 'USE_TOTAL_BALANCE' отключен.")

# Настройки стратегии
STRATEGY_SETTINGS = {
    "TRADE_SYMBOL": "BTCUSDT",  # Торговая пара
    "KLINE_TIMEFRAME": 5,  # Таймфрейм (в минутах)
    "KLINE_LIMIT": 200  # Количество загружаемых свечей
}

# Настройки анализа
ANALYSIS_SETTINGS = {
    "ANALYZE_PREVIOUS_CANDLE": True  # Включить анализ последней закрытой свечи при запуске бота
}

# Настройки логирования
LOGGING_SETTINGS = {
    "LOG_LEVEL": "INFO",  # Уровень логирования
    "LOG_FILE": "app.log",  # Имя файла для логирования
    "MAX_BYTES": 10 * 1024 * 1024,  # Максимальный размер файла логов (в байтах)
    "BACKUP_COUNT": 5  # Количество резервных копий логов
}
