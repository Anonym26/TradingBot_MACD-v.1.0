"""
Модуль для работы с API ByBit: покупка и продажа активов, проверка баланса,
определение параметров точности и минимальных размеров ордеров.
"""

import logging
import os
from decimal import Decimal, ROUND_DOWN, InvalidOperation
from pybit.unified_trading import HTTP
from dotenv import load_dotenv
from src.settings import DEPOSIT_SETTINGS

# Загрузка переменных окружения
load_dotenv()
BYBIT_API_KEY_TEST = os.getenv("BYBIT_API_KEY_TEST")
BYBIT_API_SECRET_TEST = os.getenv("BYBIT_API_SECRET_TEST")


class ByBitHandler:
    """
    Класс для работы с API ByBit: покупка и продажа активов.
    """

    def __init__(self):
        self.deposit_settings = DEPOSIT_SETTINGS
        self.session = HTTP(
            api_key=BYBIT_API_KEY_TEST,
            api_secret=BYBIT_API_SECRET_TEST,
            testnet=True  # Указываем, что работаем с тестовой сетью
        )

    async def get_precision(self, symbol):
        """
        Получение точности количества, цены и минимальной суммы ордера для указанного символа.

        :param symbol: Торговая пара (например, BTCUSDT).
        :return: base_precision, min_order_qty, min_order_amt.
        """
        try:
            response = self.session.get_instruments_info(category="spot", symbol=symbol)
            if response["retCode"] != 0:
                raise ValueError(
                    "Ошибка получения данных инструмента %s: %s", symbol, response['retMsg']
                )

            asset_info = response["result"]["list"][0]
            base_precision = Decimal(
                f"1e-{len(str(asset_info['lotSizeFilter']['basePrecision']).split('.')[-1])}"
            )
            min_order_qty = Decimal(asset_info["lotSizeFilter"]["minOrderQty"])
            min_order_amt = Decimal(asset_info["lotSizeFilter"]["minOrderAmt"])

            logging.info(
                "Точность инструмента %s: base_precision=%s, min_order_qty=%s, min_order_amt=%s",
                symbol, base_precision, min_order_qty, min_order_amt
            )
            return base_precision, min_order_qty, min_order_amt
        except (KeyError, ValueError, InvalidOperation) as error:
            logging.error("Ошибка получения точности инструмента %s: %s", symbol, error)
            raise

    async def get_asset_balance(self, asset):
        """
        Получение доступного баланса для заданного актива.

        :param asset: Название актива (например, BTC).
        :return: Баланс актива.
        """
        try:
            response = self.session.get_wallet_balance(accountType="UNIFIED")
            if response["retCode"] != 0:
                raise ValueError("Ошибка получения баланса: %s", response['retMsg'])

            coins = response["result"]["list"][0]["coin"]
            for coin in coins:
                if coin["coin"] == asset:
                    try:
                        balance = Decimal(coin["walletBalance"]).quantize(
                            Decimal("1e-8"), rounding=ROUND_DOWN
                        )
                        logging.info("Баланс %s: %.8f", asset, balance)
                        return balance
                    except InvalidOperation:
                        logging.error("Ошибка преобразования баланса %s. Raw: %s", asset, coin["walletBalance"])
                        return Decimal("0.0")

            logging.warning("Актив %s не найден в портфеле.", asset)
            return Decimal("0.0")
        except ValueError as error:
            logging.error("Ошибка получения баланса %s: %s", asset, error)
            raise

    async def get_asset_price(self, symbol):
        """
        Получение текущей цены актива.

        :param symbol: Торговая пара (например, BTCUSDT).
        :return: Текущая цена актива.
        """
        try:
            response = self.session.get_tickers(category="spot", symbol=symbol)
            if response["retCode"] != 0:
                raise ValueError("Ошибка получения цены %s: %s", symbol, response['retMsg'])

            price = Decimal(response["result"]["list"][0]["lastPrice"])
            logging.info("Текущая цена %s: %.2f", symbol, price)
            return price
        except ValueError as error:
            logging.error("Ошибка получения цены %s: %s", symbol, error)
            raise

    async def place_market_order(self, symbol, side):
        """
        Размещение рыночного ордера.

        :param symbol: Торговая пара (например, BTCUSDT).
        :param side: Сторона сделки ("Buy" или "Sell").
        :return: Результат API или None при ошибке.
        """
        try:
            base_precision, min_order_qty, min_order_amt = await self.get_precision(symbol)

            if side == "Buy":
                usdt_balance = await self.get_asset_balance("USDT")
                qty = (
                    usdt_balance
                    if self.deposit_settings["USE_TOTAL_BALANCE"]
                    else Decimal(self.deposit_settings["DEPOSIT"])
                )
                qty = min(qty, usdt_balance) / await self.get_asset_price(symbol)

            elif side == "Sell":
                qty = await self.get_asset_balance(symbol.split("USDT")[0])

            else:
                raise ValueError("Некорректная сторона сделки: %s", side)

            if qty < (min_order_qty if side == "Sell" else min_order_amt):
                logging.warning(
                    "Количество для сделки (%.8f) меньше минимального (%.8f).",
                    qty, min_order_qty if side == "Sell" else min_order_amt
                )
                return None

            qty = qty.quantize(base_precision, rounding=ROUND_DOWN)

            if qty <= Decimal("0.0"):
                logging.error("Количество для ордера равно 0. Сделка не будет выполнена.")
                return None

            response = self.session.place_order(
                category="spot",
                symbol=symbol,
                side=side,
                orderType="Market",
                qty=str(qty),
                timeInForce="GTC",
            )
            if response["retCode"] != 0:
                logging.error("Ошибка размещения ордера: %s", response['retMsg'])
                return None

            logging.info("Ордер успешно размещён: %s", response)
            return response.get("result", {})
        except (ValueError, InvalidOperation) as error:
            logging.error("Ошибка размещения ордера: %s", error)
            return None
