"""
Этот модуль содержит реализацию торговой стратегии на основе MACD.
Включает методы для размещения рыночных ордеров, анализа сигналов MACD
и управления состоянием позиций.
"""

import logging
from decimal import Decimal
from src.settings import DEPOSIT_SETTINGS, MACD_SETTINGS, RISK_MANAGEMENT_SETTINGS
from src.utils.calculations import calculate_macd
from src.utils.json_state import save_state

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
            "entry_price": 0.0,
            "tp_price": 0.0,
            "sl_price": 0.0,
            "ts_price": 0.0
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
        logging.info("Начат анализ MACD...")
        logging.info("MACD: %.2f, Signal: %.2f", macd[-1], macd_signal_line[-1])

        current_price = close_prices[-1]

        if self.should_buy(macd[-1], macd_signal_line[-1]):
            logging.info("MACD пересёк сигнальную линию снизу вверх. Подготовка к открытию позиции.")
            result = await self.market_order("Buy")
            if result is not None:
                logging.info("Позиция открыта.")
                entry_price = result.get("entry_price", current_price)
                tp_price = entry_price * (1 + RISK_MANAGEMENT_SETTINGS["TP_PERCENTAGE"] / 100)
                sl_price = entry_price * (1 - RISK_MANAGEMENT_SETTINGS["SL_PERCENTAGE"] / 100)
                ts_price = sl_price

                self.position_open = True
                self.last_signal = SIGNAL_POSITION_OPEN
                self.state.update({
                    "position_open": True,
                    "side": "Buy",
                    "quantity": result.get("quantity", 0.0),
                    "entry_price": entry_price,
                    "tp_price": tp_price,
                    "sl_price": sl_price,
                    "ts_price": ts_price
                })
                await save_state(self.state)
                logging.info(
                    "Позиция открыта: Цена входа %.2f, TP: %.2f, SL: %.2f, TS: %.2f",
                    entry_price, tp_price, sl_price, ts_price
                )

        if self.position_open:
            tp_price = self.state["tp_price"]
            sl_price = self.state["sl_price"]
            ts_price = self.state.get("ts_price", sl_price)
        else:
            tp_price = None
            sl_price = None
            ts_price = None

        logging.info(
            "Мониторинг позиции: MACD=%.2f, Signal=%.2f, Цена=%.2f, TP=%s, SL=%s, TS=%s",
            macd[-1], macd_signal_line[-1], current_price,
            f"{tp_price:.2f}" if tp_price else "N/A",
            f"{sl_price:.2f}" if sl_price else "N/A",
            f"{ts_price:.2f}" if ts_price else "N/A"
        )

        if self.position_open:
            if current_price >= tp_price:
                logging.info("Take Profit достигнут. Закрытие позиции.")
                await self.market_order("Sell")
                self._reset_state()
                return

            if current_price <= sl_price:
                logging.info("Stop Loss достигнут. Закрытие позиции.")
                await self.market_order("Sell")
                self._reset_state()
                return

            if current_price > ts_price:
                new_ts_price = max(ts_price,
                                   current_price * (1 - RISK_MANAGEMENT_SETTINGS["TRAILING_STOP_PERCENTAGE"] / 100))
                self.state["ts_price"] = new_ts_price
                logging.info("Trailing Stop обновлён до %.2f", new_ts_price)
                await save_state(self.state)

            if current_price <= ts_price:
                logging.info("Trailing Stop достигнут. Закрытие позиции.")
                await self.market_order("Sell")
                self._reset_state()
                return

        logging.info("Анализ MACD завершён.")
