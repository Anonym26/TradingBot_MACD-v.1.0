"""
Модуль для вычисления индикатора MACD (Moving Average Convergence Divergence).
"""

import numpy as np
from src.settings import MACD_SETTINGS

try:
    import talib
except ImportError as exc:
    raise ImportError("Модуль 'talib' не установлен. Установите его с помощью 'pip install TA-Lib'.") from exc

def calculate_macd(close_prices):
    """
    Вычисление MACD на основе цен закрытия.

    :param close_prices: Список или массив цен закрытия.
    :return: Кортеж из двух массивов: (MACD, сигнальная линия MACD).
    :raises ValueError: Если входной массив пуст или библиотека talib вызывает ошибку.
    """
    if not close_prices:
        raise ValueError("Массив цен закрытия пуст. Невозможно вычислить MACD.")

    try:
        # pylint: disable=no-member
        macd, macd_signal, _ = talib.MACD(
            np.array(close_prices, dtype="float"),
            fastperiod=MACD_SETTINGS["FAST"],
            slowperiod=MACD_SETTINGS["SLOW"],
            signalperiod=MACD_SETTINGS["SIGNAL"]
        )
        return macd, macd_signal
    except Exception as e:
        raise RuntimeError(f"Ошибка при вычислении MACD: {e}") from e
