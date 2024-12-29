"""
Основной модуль проекта. Запускает цикл работы бота, обрабатывает данные свечей,
анализирует сигналы MACD и выполняет торговые операции согласно стратегии.
"""

import asyncio
import logging
from datetime import datetime

from dotenv import load_dotenv

from src.handlers.bybit_handler import ByBitHandler
from src.settings import STRATEGY_SETTINGS, ANALYSIS_SETTINGS
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
    Вычисление времени до закрытия текущей свечи.

    :param interval_minutes: Таймфрейм свечи в минутах.
    :return: Время ожидания до закрытия текущей свечи в секундах.
    """
    server_time_response = bybit_handler.session.get_server_time()  # Синхронный вызов
    server_time = datetime.utcfromtimestamp(server_time_response["time"] / 1000)  # Время сервера в UTC

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
    strategy = MACDStrategy(symbol=STRATEGY_SETTINGS["TRADE_SYMBOL"])

    try:
        # Если включен анализ последней закрытой свечи, анализируем ее сразу после запуска
        if ANALYSIS_SETTINGS["ANALYZE_PREVIOUS_CANDLE"]:
            logging.info("Анализ последней закрытой свечи...")
            resource = bybit_handler.session.get_kline(  # Синхронный вызов
                category="spot",
                symbol=STRATEGY_SETTINGS["TRADE_SYMBOL"],
                interval=STRATEGY_SETTINGS["KLINE_TIMEFRAME"],
                limit=STRATEGY_SETTINGS["KLINE_LIMIT"],
            )
            klines = resource.get("result", {}).get("list", [])
            klines = sorted(klines, key=lambda x: int(x[0]))
            close_price = [float(candle[4]) for candle in klines]
            await strategy.process_macd(close_prices=close_price)

        # Ожидание времени до закрытия текущей свечи
        sleep_time = await calculate_sleep_time(STRATEGY_SETTINGS["KLINE_TIMEFRAME"])
        await asyncio.sleep(sleep_time + 2)  # Добавляем задержку в 2 секунды

        while True:
            try:
                # Получаем свечные данные
                resource = bybit_handler.session.get_kline(  # Синхронный вызов
                    category="spot",
                    symbol=STRATEGY_SETTINGS["TRADE_SYMBOL"],
                    interval=STRATEGY_SETTINGS["KLINE_TIMEFRAME"],
                    limit=STRATEGY_SETTINGS["KLINE_LIMIT"],
                )
                klines = resource.get("result", {}).get("list", [])
                klines = sorted(klines, key=lambda x: int(x[0]))
                close_price = [float(candle[4]) for candle in klines]

                # Обработка стратегии MACD
                await strategy.process_macd(close_prices=close_price)

                # Ожидаем следующий анализ через таймфрейм
                await asyncio.sleep(60 * STRATEGY_SETTINGS["KLINE_TIMEFRAME"])
            except KeyError as error:
                logging.error("Ошибка в основном цикле: %s", error)

    except ValueError as error:
        logging.error("Ошибка при вычислении времени до закрытия свечи: %s", error)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.info("Работа программы завершена вручную.")
