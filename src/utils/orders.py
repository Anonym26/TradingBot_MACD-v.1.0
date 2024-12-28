import logging
from decimal import Decimal, ROUND_DOWN
from src.settings import DEPOSIT, MACD_FAST, MACD_SLOW, MACD_SIGNAL
from src.handlers.bybit_handler import get_precision, get_asset_balance
from src.utils.calculations import calculate_macd

# Константы состояний сигналов
SIGNAL_WAIT_DOWNWARD_CROSS = "Wait for downward cross"
SIGNAL_WAIT_UPWARD_CROSS = "Wait for upward cross"
SIGNAL_POSITION_OPEN = "Position open"

class MACDStrategy:
    def __init__(self, session, symbol):
        self.session = session
        self.symbol = symbol
        self.deposit = Decimal(DEPOSIT)
        self.last_signal = None  # Состояние последнего сигнала
        self.position_open = False  # Флаг состояния позиции (открыта или нет)

    def market_order(self, side, close_price):
        """
        Размещение рыночного ордера с учётом минимальных требований ByBit.
        :param side: Сторона сделки ("Buy" или "Sell").
        :param close_price: Список цен закрытия.
        :return: Ответ API или None при ошибке.
        """
        try:
            # Получаем параметры точности и минимальных значений для символа
            base_precision, min_order_qty, min_order_amt = get_precision(self.symbol, self.session)

            if side == "Buy":
                qty = self.deposit
                if qty < min_order_amt:
                    logging.warning(f"Сумма покупки ({qty}) меньше минимально допустимой {min_order_amt}.")
                    return None
            elif side == "Sell":
                base_asset = self.symbol.split('USDT')[0]
                qty = Decimal(get_asset_balance(self.session, base_asset))
                if qty < min_order_qty:
                    logging.warning(f"Количество для продажи ({qty}) меньше минимально допустимого {min_order_qty}.")
                    return None

            qty = qty.quantize(base_precision, rounding=ROUND_DOWN)
            logging.info(f"Qty после округления: {qty}")

            response = self.session.place_order(
                category="spot",
                symbol=self.symbol,
                side=side,
                orderType="Market",
                qty=str(qty),
                timeInForce="GTC",
            )
            logging.info(f"Ордер успешно размещён: {response}")
            return response
        except Exception as e:
            logging.error(f"Ошибка при размещении ордера: {e}")
            return None

    def process_macd(self, close_prices):
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
                result = self.market_order("Buy", close_prices)
                if result is not None:
                    logging.info("Позиция открыта.")
                    self.position_open = True
                    self.last_signal = SIGNAL_POSITION_OPEN

        if self.position_open:
            if macd[-1] < macd_signal_line[-1]:
                logging.info("MACD пересёк сигнальную линию сверху вниз. Закрываем позицию.")
                result = self.market_order("Sell", close_prices)
                if result is not None:
                    logging.info("Позиция успешно закрыта.")
                else:
                    logging.warning("Не удалось закрыть позицию.")
                self.position_open = False
                self.last_signal = SIGNAL_WAIT_UPWARD_CROSS
