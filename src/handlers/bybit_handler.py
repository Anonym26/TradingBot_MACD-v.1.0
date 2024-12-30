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
            logging.error(
                "Ошибка при извлечении данных точности для символа %s: %s", symbol, key_error
            )
            raise
        except ValueError as value_error:
            logging.error(
                "Ошибка при обработке данных инструмента %s: %s", symbol, value_error
            )
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
            return 0.0
        except ValueError as value_error:
            logging.error("Ошибка при получении баланса %s: %s", asset, value_error)
            raise

    async def check_open_position(self, symbol):
        """
        Проверка открытой позиции по наличию баланса актива, превышающего минимальный размер ордера.

        :param symbol: Торговая пара (например, BTCUSDT).
        :return: Словарь с информацией о позиции.
        """
        try:
            base_asset = symbol.split("USDT")[0]
            balance = await self.get_asset_balance(base_asset)
            _, min_order_qty, _ = await self.get_precision(symbol)

            if balance >= min_order_qty:
                logging.info("Обнаружена открытая позиция для %s: %.8f", base_asset, balance)
                return {
                    "position_open": True,
                    "quantity": balance,
                    "side": "Buy"  # Наличие актива указывает на покупку
                }

            logging.info("Нет открытой позиции для %s (баланс меньше минимального).", base_asset)
            return {"position_open": False}
        except Exception as exc:
            logging.error("Ошибка при проверке открытой позиции: %s", exc)
            return {"position_open": False}

    async def place_market_order(self, symbol, side):
        """
        Размещение рыночного ордера.

        :param symbol: Торговая пара (например, BTCUSDT).
        :param side: Сторона сделки ("Buy" или "Sell").
        :return: Ответ API или None при ошибке.
        """
        try:
            base_precision, min_order_qty, min_order_amt = await self.get_precision(symbol)

            if side == "Buy":
                # Рассчитываем количество для покупки
                usdt_balance = Decimal(await self.get_asset_balance("USDT"))
                qty = usdt_balance if self.deposit_settings["USE_TOTAL_BALANCE"] else Decimal(self.deposit_settings["DEPOSIT"])
                if qty > usdt_balance:
                    qty = usdt_balance
                qty /= Decimal(await self.get_asset_price(symbol))

            elif side == "Sell":
                # Получаем количество актива для продажи
                qty = Decimal(await self.get_asset_balance(symbol.split("USDT")[0]))

            else:
                raise ValueError(f"Некорректная сторона сделки: {side}")

            if qty < (min_order_qty if side == "Sell" else min_order_amt):
                logging.warning(
                    "Количество для сделки (%.8f) меньше минимально допустимого %.8f.",
                    qty, min_order_qty if side == "Sell" else min_order_amt
                )
                return None

            qty = qty.quantize(base_precision, rounding=ROUND_DOWN)

            response = self.session.place_order(
                category="spot",
                symbol=symbol,
                side=side,
                orderType="Market",
                qty=str(qty),
                timeInForce="GTC",
            )
            if response["retCode"] != 0:
                logging.error("Ошибка размещения ордера: %s", response["retMsg"])
                return None

            logging.info("Ордер успешно размещён: %s", response)
            return response.get("result", {})
        except Exception as exc:
            logging.error("Ошибка при размещении ордера: %s", exc)
            return None
