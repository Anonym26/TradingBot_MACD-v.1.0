"""
Модуль для управления состоянием торгового бота с использованием JSON-файла.
Обеспечивает загрузку и сохранение состояния, включая информацию об открытых позициях.
"""

import json
import logging
import os
import shutil

STATE_FILE = "state.json"
BACKUP_FILE = "state_backup.json"

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

    Перед записью создается резервная копия текущего состояния, если файл существует.

    :param state: Словарь с текущим состоянием бота. Формат:
        {
            "position_open": bool,   # Флаг открытой позиции
            "symbol": str,           # Торговая пара (например, "BTCUSDT")
            "side": str,             # Сторона сделки ("Buy" или "Sell")
            "quantity": float,       # Количество актива
            "entry_price": float     # Цена открытия позиции
        }
    """
    if os.path.exists(STATE_FILE):
        try:
            shutil.copyfile(STATE_FILE, BACKUP_FILE)
            logging.info("Резервная копия состояния сохранена в '%s'", BACKUP_FILE)
        except IOError as error:
            logging.error("Ошибка при создании резервной копии: %s", error, exc_info=True)

    try:
        with open(STATE_FILE, "w") as file:
            json.dump(state, file, indent=4)
            logging.info("Состояние успешно сохранено в '%s'", STATE_FILE)
    except IOError as error:
        logging.error("Ошибка при сохранении состояния: %s", error, exc_info=True)
