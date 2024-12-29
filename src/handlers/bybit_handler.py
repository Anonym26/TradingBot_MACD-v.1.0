"""
Этот модуль содержит класс для работы с API ByBit. Предоставляет функционал
для размещения рыночных ордеров, получения информации об активах,
балансе и параметрах точности торговых пар.
"""

import logging
import os
from decimal import Decimal, ROUND_DOWN
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
            response = self.session.get_instruments_info(
                category="spot",
                symbol=symbol
            )
            if response["retCode"] != 0:
                raise ValueError(
                    f"Ошибка получения информации об инструменте {symbol}: {response['retMsg']}"
                )

            asset_info = response["result"]["list"][0]
            base_precision = Decimal(
                f"1e-{str(asset_info['lotSizeFilter']['basePrecision']).rsplit('.', maxsplit=1)[-1]}"
            )
            min_order_qty = Decimal(asset_info["lotSizeFilter"]["minOrderQty"])
            min_order_amt = Decimal(asset_info["lotSizeFilter"]["minOrderAmt"])

            return base_precision, min_order_qty, min_order_amt
        except KeyError as key_error:
            logging.error("Ошибка при извлечении данных точности для символа %s: %s", symbol, key_error)
            raise
        except ValueError as value_error:
            logging.error("Ошибка при обработке данных инструмента %s: %s", symbol, value_error)
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
                raise ValueError(f"Ошибка получения баланса: {response['retMsg']}")

            coins = response["result"]["list"][0]["coin"]
            for coin in coins:
                if coin["coin"] == asset:
                    balance = float(coin["walletBalance"])
                    logging.info("Баланс %s: %.8f", asset, balance)
                    return balance

            logging.warning("Актива %s нет в портфеле.", asset)
            return 0
        except ValueError as value_error:
            logging.error("Ошибка при получении баланса %s: %s", asset, value_error)
            raise

    async def place_market_order(self, symbol, side):
        """
        Размещение рыночного ордера с учётом минимальных требований ByBit.

        :param symbol: Торговая пара (например, BTCUSDT).
        :param side: Сторона сделки ("Buy" или "Sell").
        :return: Ответ API или None при ошибке.
        """
        try:
            base_precision, min_order_qty, min_order_amt = await self.get_precision(symbol)

            if side == "Buy":
                if self.deposit_settings["USE_TOTAL_BALANCE"]:
                    usdt_balance = Decimal(await self.get_asset_balance("USDT"))
                    qty = usdt_balance
                    if qty < min_order_amt:
                        logging.warning(
                            "Баланс USDT (%.8f) меньше минимально допустимой суммы %.8f.", qty, min_order_amt
                        )
                        return None
                else:
                    qty = Decimal(self.deposit_settings["DEPOSIT"])
                    if qty < min_order_amt:
                        logging.warning(
                            "Сумма покупки (%.8f) меньше минимально допустимой %.8f.", qty, min_order_amt
                        )
                        return None

            elif side == "Sell":
                base_asset = symbol.split("USDT")[0]
                qty = Decimal(await self.get_asset_balance(base_asset))
                if qty < min_order_qty:
                    logging.warning(
                        "Количество для продажи (%.8f) меньше минимально допустимого %.8f.", qty, min_order_qty
                    )
                    return None
            else:
                raise ValueError(f"Некорректная сторона сделки: {side}")

            qty = qty.quantize(base_precision, rounding=ROUND_DOWN)
            logging.info("Qty после округления: %.8f", qty)

            response = self.session.place_order(
                category="spot",
                symbol=symbol,
                side=side,
                orderType="Market",
                qty=str(qty),
                timeInForce="GTC",
            )
            logging.info("Ордер успешно размещён: %s", response)
            return response
        except ValueError as value_error:
            logging.error("Ошибка в параметрах ордера: %s", value_error)
        except KeyError as key_error:
            logging.error("Ошибка данных при размещении ордера: %s", key_error)
