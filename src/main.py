import asyncio
import logging
from datetime import datetime, timedelta

from dotenv import load_dotenv
from src.utils.logging_config import setup_logger
from src.handlers.bybit_handler import ByBitHandler
from src.utils.orders import MACDStrategy
from settings import TRADE_SYMBOL, KLINE_TIMEFRAME, KLINE_LIMIT, ANALYZE_PREVIOUS_CANDLE

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
setup_logger("main.log")

# Инициализация ByBitHandler
bybit_handler = ByBitHandler()

async def calculate_sleep_time(interval_minutes):
    """
    Вычисление времени до закрытия текущей свечи.
    :param interval_minutes: Таймфрейм свечи в минутах.
    :return: Время ожидания до закрытия текущей свечи в секундах.
    """
    server_time_response = bybit_handler.session.get_server_time()  # Синхронный вызов
    server_time = datetime.utcfromtimestamp(server_time_response['time'] / 1000)  # Время сервера в UTC
    next_candle_time = (
        server_time + timedelta(minutes=interval_minutes)
    ).replace(second=0, microsecond=0, minute=(server_time.minute // interval_minutes + 1) * interval_minutes)

    sleep_time = (next_candle_time - server_time).total_seconds()
    logging.info(f"До закрытия текущей свечи осталось: {sleep_time:.2f} секунд.")
    return sleep_time

async def run():
    """
    Основной цикл бота для анализа данных и выполнения сделок.
    """
    strategy = MACDStrategy(session=bybit_handler.session, symbol=TRADE_SYMBOL)

    try:
        # Если включен анализ последней закрытой свечи, анализируем ее сразу после запуска
        if ANALYZE_PREVIOUS_CANDLE:
            logging.info("Анализ последней закрытой свечи...")
            resource = bybit_handler.session.get_kline(  # Синхронный вызов
                category='spot',
                symbol=TRADE_SYMBOL,
                interval=KLINE_TIMEFRAME,
                limit=KLINE_LIMIT
            )
            klines = resource.get('result', {}).get('list', [])
            klines = sorted(klines, key=lambda x: int(x[0]))
            close_price = [float(candle[4]) for candle in klines]
            await strategy.process_macd(close_prices=close_price)

        # Ожидание времени до закрытия текущей свечи
        sleep_time = await calculate_sleep_time(int(KLINE_TIMEFRAME))
        await asyncio.sleep(sleep_time + 2)  # Добавляем задержку в 2 секунды

        while True:
            try:
                # Получаем свечные данные
                resource = bybit_handler.session.get_kline(  # Синхронный вызов
                    category='spot',
                    symbol=TRADE_SYMBOL,
                    interval=KLINE_TIMEFRAME,
                    limit=KLINE_LIMIT
                )
                klines = resource.get('result', {}).get('list', [])
                klines = sorted(klines, key=lambda x: int(x[0]))
                close_price = [float(candle[4]) for candle in klines]

                # Обработка стратегии MACD
                await strategy.process_macd(close_prices=close_price)

                # Ожидаем следующий анализ через таймфрейм
                await asyncio.sleep(60 * int(KLINE_TIMEFRAME))
            except Exception as e:
                logging.error(f"Ошибка в основном цикле: {e}")

    except Exception as e:
        logging.error(f"Ошибка при вычислении времени до закрытия свечи: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.info("Работа программы завершена вручную.")
