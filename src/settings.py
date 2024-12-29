# Настройки MACD
MACD_FAST = 12  # Быстрая линия
MACD_SLOW = 26  # Медленная линия
MACD_SIGNAL = 9  # Сигнальная линия

# Настройки использования депозита
USE_TOTAL_BALANCE = False  # True - использовать весь баланс USDT, False - фиксированный депозит
DEPOSIT = 100  # Фиксированный депозит в USDT (используется, если USE_TOTAL_BALANCE=False)

# Настройки стратегии
TRADE_SYMBOL = "BTCUSDT"  # Торговая пара
KLINE_TIMEFRAME = "5"  # Таймфрейм
KLINE_LIMIT = 200

# Настройки анализа
ANALYZE_PREVIOUS_CANDLE = False  # Включить анализ последней закрытой свечи при запуске бота
