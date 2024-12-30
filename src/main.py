"""
Основной модуль проекта. Запускает цикл работы бота, обрабатывает данные свечей,
анализирует сигналы MACD и выполняет торговые операции согласно стратегии.
"""

import asyncio
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv

from src.handlers.bybit_handler import ByBitHandler
from src.settings import STRATEGY_SETTINGS, ANALYSIS_SETTINGS
from src.utils.json_state import load_state, save_state
from src.utils.logging_config import setup_logger
from src.utils.orders import MACDStrategy

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
setup_logger()

# Инициализация ByBitHandler
bybit_handler = ByBitHandler()


async def calculate_sleep_time(interval_minutes):
    """
    Вычисление времени до закрытия текущей свечи с синхронизацией с временной зоной биржи.

    :param interval_minutes: Таймфрейм свечи в минутах.
    :return: Время ожидания до закрытия текущей свечи в секундах.
    """
    server_time_response = bybit_handler.session.get_server_time()  # Синхронный вызов
    server_time = datetime.utcfromtimestamp(server_time_response["time"] / 1000).replace(tzinfo=timezone.utc)

    next_candle_minute = (server_time.minute // interval_minutes + 1) * interval_minutes
    if next_candle_minute >= 60:
        next_candle_time = server_time.replace(
            hour=(server_time.hour + 1) % 24, minute=0, second=0, microsecond=0
        )
    else:
        next_candle_time = server_time.replace(minute=next_candle_minute, second=0, microsecond=0)

    sleep_time = (next_candle_time - server_time).total_seconds()
    hours, remainder = divmod(sleep_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    logging.info(
        "До закрытия текущей свечи осталось: %d ч %d мин %d сек.",
        int(hours), int(minutes), int(seconds)
    )
    return sleep_time


async def run():
    """
    Основной цикл бота для анализа данных и выполнения сделок.
    """
    # Загружаем текущее состояние
    state = load_state()
    strategy = MACDStrategy(
        symbol=STRATEGY_SETTINGS["TRADE_SYMBOL"],
        handler=bybit_handler,
        state=state
    )

    try:
        # Синхронизация позиции с биржей
        await strategy.sync_position()

        if strategy.position_open:
            logging.info("Обнаружена открытая позиция: %s", strategy.state)
        else:
            logging.info("Открытых позиций нет. Ожидание нового сигнала.")

        # Если включен анализ последней закрытой свечи, анализируем ее сразу после запуска
        if ANALYSIS_SETTINGS["ANALYZE_PREVIOUS_CANDLE"]:
            logging.info("Анализ последней закрытой свечи...")
            resource = bybit_handler.session.get_kline(
                category="spot",
                symbol=STRATEGY_SETTINGS["TRADE_SYMBOL"],
                interval=STRATEGY_SETTINGS["KLINE_TIMEFRAME"],
                limit=STRATEGY_SETTINGS["KLINE_LIMIT"]
            )
            klines = resource.get("result", {}).get("list", [])
            klines = sorted(klines, key=lambda x: int(x[0]))

            # Исключаем текущую свечу и обрабатываем последнюю закрытую свечу
            close_price = [float(candle[4]) for candle in klines[:-1]]  # Исключаем текущую свечу
            await strategy.process_macd(close_prices=close_price)

        while True:
            try:
                # Ожидаем до закрытия текущей свечи
                sleep_time = await calculate_sleep_time(STRATEGY_SETTINGS["KLINE_TIMEFRAME"])
                await asyncio.sleep(sleep_time + 2)  # Дополнительная задержка для гарантии закрытия свечи

                # Получаем свечные данные
                resource = bybit_handler.session.get_kline(
                    category="spot",
                    symbol=STRATEGY_SETTINGS["TRADE_SYMBOL"],
                    interval=STRATEGY_SETTINGS["KLINE_TIMEFRAME"],
                    limit=STRATEGY_SETTINGS["KLINE_LIMIT"]
                )
                klines = resource.get("result", {}).get("list", [])
                klines = sorted(klines, key=lambda x: int(x[0]))

                # Исключаем текущую свечу для анализа
                close_price = [float(candle[4]) for candle in klines[:-1]]  # Исключаем текущую свечу

                # Обработка стратегии MACD
                await strategy.process_macd(close_prices=close_price)

                # Сохранение текущего состояния
                save_state(strategy.state)

            except Exception as error:
                logging.error("Ошибка в основном цикле: %s", error, exc_info=True)

    except Exception as error:
        logging.error("Ошибка при запуске бота: %s", error, exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.info("Работа программы завершена вручную.")
