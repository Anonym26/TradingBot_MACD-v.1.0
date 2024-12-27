import logging
from pybit.unified_trading import HTTP
from decimal import Decimal
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()
BYBIT_API_KEY_TEST = os.getenv("BYBIT_API_KEY_TEST")
BYBIT_API_SECRET_TEST = os.getenv("BYBIT_API_SECRET_TEST")

class ByBitHandler:
    """
    Класс для работы с API ByBit.
    """
    def __init__(self):
        self.session = HTTP(
            api_key=BYBIT_API_KEY_TEST,
            api_secret=BYBIT_API_SECRET_TEST,
            testnet=True
        )

    def place_market_order(self, symbol, qty, side="Buy"):
        """
        Размещение рыночного ордера.
        :param symbol: Торговая пара (например, BTCUSDT).
        :param qty: Количество актива.
        :param side: Сторона сделки ("Buy" или "Sell").
        :return: Ответ API.
        """
        try:
            response = self.session.place_order(
                category="spot",
                symbol=symbol,
                side=side,
                orderType="Market",
                qty=str(qty),
                timeInForce="GTC",
            )
            logging.info(f"Ордер успешно размещен: {response}")
            return response
        except Exception as e:
            logging.error(f"Ошибка размещения ордера: {e}")
            raise e

    def get_asset_balance(self, asset):
        """
        Получение доступного баланса для указанного актива.
        :param asset: Название актива (например, BTC).
        :return: Баланс актива.
        """
        try:
            response = self.session.get_wallet_balance(accountType="UNIFIED")
            if response['retCode'] != 0:
                raise Exception(f"Ошибка получения баланса: {response['retMsg']}")

            coins = response.get('result', {}).get('list', [{}])[0].get('coin', [])
            for coin in coins:
                if coin['coin'] == asset:
                    return float(coin['walletBalance'])

            logging.warning(f"Актив {asset} отсутствует на балансе.")
            return 0
        except Exception as e:
            logging.error(f"Ошибка получения баланса актива {asset}: {e}")
            raise e

    def get_precision(self, symbol):
        """
        Получение точности и минимальной суммы ордера для символа.
        :param symbol: Торговая пара (например, BTCUSDT).
        :return: Точность количества (qty_p), цены (limit_p), минимальная сумма ордера (min_order_amt).
        """
        try:
            response = self.session.get_instruments_info(category="spot", symbol=symbol)
            if response['retCode'] != 0:
                raise Exception(f"Ошибка получения информации об инструменте: {response['retMsg']}")

            lot_size_filter = response['result']['list'][0]['lotSizeFilter']
            price_filter = response['result']['list'][0]['priceFilter']

            qty_step = Decimal(lot_size_filter.get('qtyStep', '1'))
            tick_size = Decimal(price_filter.get('tickSize', '1'))
            min_order_amt = lot_size_filter.get('minOrderAmt', '1')

            qty_p = abs(qty_step.as_tuple().exponent)  # Точность количества
            limit_p = abs(tick_size.as_tuple().exponent)  # Точность цены

            return qty_p, limit_p, min_order_amt
        except (KeyError, IndexError, ValueError) as e:
            logging.error(f"Ошибка при обработке данных инструмента: {e}")
            raise e
