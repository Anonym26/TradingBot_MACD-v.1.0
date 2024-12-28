import asyncio
import logging
from dotenv import load_dotenv
from src.utils.logging_config import setup_logger
from src.handlers.bybit_handler import ByBitHandler
from src.utils.orders import MACDStrategy
from settings import TRADE_SYMBOL, KLINE_TIMEFRAME, KLINE_LIMIT

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
setup_logger("main.log")

# Инициализация ByBitHandler
bybit_handler = ByBitHandler()

async def run():
    """
    Основной цикл бота для анализа данных и выполнения сделок.
    """
    strategy = MACDStrategy(session=bybit_handler.session, symbol=TRADE_SYMBOL)

    while True:
        try:
            # Получаем свечные данные
            resource = bybit_handler.session.get_kline(  # Если метод синхронный, вызов без await
                category='spot',
                symbol=TRADE_SYMBOL,
                interval=KLINE_TIMEFRAME,
                limit=200
            )
            klines = resource.get('result', {}).get('list', [])
            klines = sorted(klines, key=lambda x: int(x[0]))

            close_price = [float(candle[4]) for candle in klines]

            # Обработка стратегии MACD
            await strategy.process_macd(close_prices=close_price)  # Добавлено await

            await asyncio.sleep(60 * int(KLINE_TIMEFRAME))  # Ждем время таймфрейма перед следующим анализом

        except Exception as e:
            logging.error(f"Ошибка в основном цикле: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.info("Работа программы завершена вручную.")