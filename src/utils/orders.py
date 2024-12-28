import logging
from decimal import Decimal, ROUND_DOWN
from src.settings import DEPOSIT, MACD_FAST, MACD_SLOW, MACD_SIGNAL, USE_TOTAL_BALANCE
from src.handlers.bybit_handler import ByBitHandler
from src.utils.calculations import calculate_macd

# Константы состояний сигналов
SIGNAL_WAIT_DOWNWARD_CROSS = "Wait for downward cross"
SIGNAL_WAIT_UPWARD_CROSS = "Wait for upward cross"
SIGNAL_POSITION_OPEN = "Position open"

class MACDStrategy:
    def __init__(self, session, symbol):
        self.handler = ByBitHandler()
        self.symbol = symbol
        self.deposit = Decimal(DEPOSIT)
        self.last_signal = None  # Состояние последнего сигнала
        self.position_open = False  # Флаг состояния позиции (открыта или нет)

    async def market_order(self, side, close_price, use_total_balance=USE_TOTAL_BALANCE):
        """
        Размещение рыночного ордера через ByBitHandler.
        :param side: Сторона сделки ("Buy" или "Sell").
        :param close_price: Текущая цена актива.
        :param use_total_balance: Использовать весь баланс депозита для покупки.
        :return: Ответ API или None при ошибке.
        """
        return await self.handler.place_market_order(self.symbol,
                                                     side,
                                                     close_price,
                                                     use_total_balance=use_total_balance)

    async def process_macd(self, close_prices):
        """
        Обработка MACD для принятия торговых решений.
        :param close_prices: Список цен закрытия.
        """
        macd, macd_signal_line = calculate_macd(close_prices, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
        logging.info(f"MACD: {macd[-1]:.2f}, Signal: {macd_signal_line[-1]:.2f}")

        if not self.position_open:
            if self.last_signal is None:
                if macd[-1] > macd_signal_line[-1]:
                    logging.info("MACD выше сигнальной линии. Ждем пересечения сверху вниз.")
                    self.last_signal = SIGNAL_WAIT_DOWNWARD_CROSS
                elif macd[-1] <= macd_signal_line[-1]:
                    logging.info("MACD ниже сигнальной линии. Готов к покупке и жду сигнала.")
                    self.last_signal = SIGNAL_WAIT_UPWARD_CROSS

            elif self.last_signal == SIGNAL_WAIT_UPWARD_CROSS and macd[-1] > macd_signal_line[-1]:
                logging.info("Пересечение снизу вверх. Открываем покупку.")
                result = await self.market_order("Buy", close_prices[-1])
                if result is not None:
                    logging.info("Позиция открыта.")
                    self.position_open = True
                    self.last_signal = SIGNAL_POSITION_OPEN

        if self.position_open:
            if macd[-1] < macd_signal_line[-1]:
                logging.info("MACD пересёк сигнальную линию сверху вниз. Закрываем позицию.")
                result = await self.market_order("Sell", close_prices[-1])
                if result is not None:
                    logging.info("Позиция успешно закрыта.")
                else:
                    logging.warning("Не удалось закрыть позицию.")
                self.position_open = False
                self.last_signal = SIGNAL_WAIT_UPWARD_CROSS
