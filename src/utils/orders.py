"""
Этот модуль содержит реализацию торговой стратегии на основе MACD.
Включает методы для размещения рыночных ордеров, анализа сигналов MACD
и управления состоянием позиций.
"""

import logging
from decimal import Decimal
from src.settings import DEPOSIT_SETTINGS, MACD_SETTINGS
from src.utils.calculations import calculate_macd

# Константы состояний сигналов
SIGNAL_WAIT_DOWNWARD_CROSS = "Wait for downward cross"
SIGNAL_WAIT_UPWARD_CROSS = "Wait for upward cross"
SIGNAL_POSITION_OPEN = "Position open"

class MACDStrategy:
    """
    Класс для реализации стратегии на основе MACD.
    """

    def __init__(self, symbol, handler, state):
        """
        Инициализация стратегии.

        :param symbol: Торговая пара (например, BTCUSDT).
        :param handler: Экземпляр ByBitHandler для работы с API ByBit.
        :param state: Состояние бота, загруженное из JSON-файла.
        """
        self.handler = handler
        self.symbol = symbol
        self.state = state
        self.deposit = Decimal(DEPOSIT_SETTINGS["DEPOSIT"])
        self.use_total_balance = DEPOSIT_SETTINGS["USE_TOTAL_BALANCE"]
        self.last_signal = self.state.get("last_signal", None)
        self.position_open = self.state.get("position_open", False)

    async def sync_position(self):
        """
        Синхронизация состояния с биржей.

        Проверяет наличие активов на балансе, и обновляет состояние в соответствии с результатом.
        """
        try:
            asset = self.symbol.split("USDT")[0]
            balance = await self.handler.get_asset_balance(asset)
            _, min_order_qty, _ = await self.handler.get_precision(self.symbol)

            if Decimal(balance) >= min_order_qty:
                self.position_open = True
                self.state.update({
                    "position_open": True,
                    "side": "Buy",
                    "quantity": float(balance),
                    "entry_price": self.state.get("entry_price", 0.0)
                })
                logging.info("Обнаружена открытая позиция на бирже. Состояние обновлено: %s", self.state)
            else:
                self._reset_state()
                logging.info("Открытых позиций на бирже нет. Состояние сброшено.")
        except Exception as error:
            logging.error("Ошибка при синхронизации позиции с биржей: %s", error, exc_info=True)
            self._reset_state()

    def _reset_state(self):
        """
        Сбрасывает состояние позиции в начальное состояние.
        """
        self.position_open = False
        self.state.update({
            "position_open": False,
            "side": None,
            "quantity": 0.0,
            "entry_price": 0.0
        })

    async def market_order(self, side):
        """
        Размещение рыночного ордера через ByBitHandler.

        :param side: Сторона сделки ("Buy" или "Sell").
        :return: Ответ API или None при ошибке.
        """
        return await self.handler.place_market_order(
            symbol=self.symbol,
            side=side
        )

    def should_buy(self, macd, macd_signal_line):
        """
        Определяет, следует ли открывать позицию на покупку.

        :param macd: Значение MACD.
        :param macd_signal_line: Значение сигнальной линии MACD.
        :return: True, если следует покупать, иначе False.
        """
        return self.last_signal == SIGNAL_WAIT_UPWARD_CROSS and macd > macd_signal_line

    def should_sell(self, macd, macd_signal_line):
        """
        Определяет, следует ли закрывать позицию на продажу.

        :param macd: Значение MACD.
        :param macd_signal_line: Значение сигнальной линии MACD.
        :return: True, если следует продавать, иначе False.
        """
        return self.position_open and macd < macd_signal_line

    async def process_macd(self, close_prices):
        """
        Обработка MACD для принятия торговых решений.

        :param close_prices: Список цен закрытия.
        """
        macd, macd_signal_line = calculate_macd(close_prices)
        logging.info("MACD: %.2f, Signal: %.2f", macd[-1], macd_signal_line[-1])

        if self.should_buy(macd[-1], macd_signal_line[-1]):
            logging.info("Пересечение снизу вверх. Открываем покупку.")
            result = await self.market_order("Buy")
            if result is not None:
                logging.info("Позиция открыта.")
                self.position_open = True
                self.last_signal = SIGNAL_POSITION_OPEN
                self.state.update({
                    "position_open": True,
                    "side": "Buy",
                    "quantity": result.get("quantity", 0.0),
                    "entry_price": result.get("entry_price", 0.0)
                })

        if self.should_sell(macd[-1], macd_signal_line[-1]):
            logging.info("MACD пересёк сигнальную линию сверху вниз. Закрываем позицию.")
            result = await self.market_order("Sell")
            if result is not None:
                logging.info("Позиция успешно закрыта.")
                self._reset_state()
