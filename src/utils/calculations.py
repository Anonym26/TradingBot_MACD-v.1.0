import talib
import numpy as np

def calculate_macd(close_prices, fast=12, slow=26, signal=9):
    """
    Вычисление MACD.
    :param close_prices: Массив цен закрытия.
    :param fast: Период для быстрой EMA.
    :param slow: Период для медленной EMA.
    :param signal: Период для сигнальной линии.
    :return: MACD и сигнальная линия.
    """
    macd, macd_signal, _ = talib.MACD(
        np.array(close_prices, dtype='float'),
        fastperiod=fast,
        slowperiod=slow,
        signalperiod=signal
    )
    return macd, macd_signal
