"""
Модуль для управления состоянием торгового бота с использованием JSON-файла.
Обеспечивает загрузку и сохранение состояния, включая информацию об открытых позициях.
"""

import json
import logging
import os

STATE_FILE = "state.json"

def load_state():
    """
    Загружает состояние бота из JSON-файла.

    Если файл состояния существует, он будет прочитан и данные будут возвращены.
    Если файл не найден, возвращается состояние по умолчанию.

    :return: Словарь с состоянием бота. Формат:
        {
            "position_open": bool,   # Флаг открытой позиции
            "symbol": str,           # Торговая пара (например, "BTCUSDT")
            "side": str,             # Сторона сделки ("Buy" или "Sell")
            "quantity": float,       # Количество актива
            "entry_price": float     # Цена открытия позиции
        }
    """
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as error:
                # Если файл повреждён, возвращаем состояние по умолчанию
                logging.warning("Ошибка при чтении файла состояния: %s", error)
                return {"position_open": False, "symbol": None, "side": None, "quantity": 0.0, "entry_price": 0.0}
    return {"position_open": False, "symbol": None, "side": None, "quantity": 0.0, "entry_price": 0.0}


def save_state(state):
    """
    Сохраняет текущее состояние бота в JSON-файл.

    Записывает переданное состояние в файл `state.json` в формате JSON с отступами для читаемости.

    :param state: Словарь с текущим состоянием бота. Формат:
        {
            "position_open": bool,   # Флаг открытой позиции
            "symbol": str,           # Торговая пара (например, "BTCUSDT")
            "side": str,             # Сторона сделки ("Buy" или "Sell")
            "quantity": float,       # Количество актива
            "entry_price": float     # Цена открытия позиции
        }
    """
    with open(STATE_FILE, "w") as file:
        json.dump(state, file, indent=4)
