import asyncio
import logging
from dotenv import load_dotenv
from src.utils.logging_config import setup_logger
from src.handlers.bybit_handler import ByBitHandler
from src.utils.calculations import calculate_macd
from src.utils.orders import market_order
from settings import symbol, kline_time, macd_fast, macd_slow, macd_signal

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
    last_signal = None  # Текущее состояние: None, "Buy" или "Sell"

    while True:
        try:
            # Получаем свечные данные
            resource = bybit_handler.session.get_kline(
                category='spot',
                symbol=symbol,
                interval=kline_time,
                limit=200
            )
            klines = resource.get('result', {}).get('list', [])
            klines = sorted(klines, key=lambda x: int(x[0]))

            close_price = [float(candle[4]) for candle in klines]

            # Вычисляем MACD
            macd, macd_signal_line = calculate_macd(
                close_prices=close_price,
                fast=macd_fast,
                slow=macd_slow,
                signal=macd_signal
            )
            logging.info(f"MACD: {macd[-1]:.2f}, Signal: {macd_signal_line[-1]:.2f}")

            # Условия для сделок
            if macd[-1] > macd_signal_line[-1] and last_signal != "Buy":
                logging.info("Условие для покупки выполнено. Открываем позицию BUY.")
                result = market_order(bybit_handler.session, symbol, "Buy", close_price)
                if result is None:
                    logging.warning("Покупка не выполнена.")
                else:
                    last_signal = "Buy"

            elif macd[-1] < macd_signal_line[-1] and last_signal != "Sell":
                logging.info("Условие для продажи выполнено. Открываем позицию SELL.")
                result = market_order(bybit_handler.session, symbol, "Sell", close_price)
                if result is None:
                    logging.warning("Продажа не выполнена.")
                else:
                    last_signal = "Sell"

            await asyncio.sleep(60)  # Ждем 1 минуту перед следующим анализом

        except Exception as e:
            logging.error(f"Ошибка в основном цикле: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.info("Работа программы завершена вручную.")
