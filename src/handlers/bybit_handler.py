import logging
from decimal import Decimal, ROUND_DOWN
from pybit.unified_trading import HTTP
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()
BYBIT_API_KEY_TEST = os.getenv("BYBIT_API_KEY_TEST")
BYBIT_API_SECRET_TEST = os.getenv("BYBIT_API_SECRET_TEST")


def get_precision(symbol, session):
    """
    Получение точности количества, цены и минимальной суммы ордера для указанного символа.
    :param symbol: Торговая пара (например, BTCUSDT).
    :param session: Сессия ByBit API.
    :return: base_precision, min_order_qty, min_order_amt.
    """
    try:
        response = session.get_instruments_info(category="spot", symbol=symbol)
        if response['retCode'] != 0:
            raise Exception(f"Ошибка получения информации об инструменте {symbol}: {response['retMsg']}")

        asset_info = response['result']['list'][0]

        # Преобразуем точность в формат Decimal
        base_precision = Decimal(f"1e-{len(str(asset_info['lotSizeFilter']['basePrecision']).split('.')[-1])}")
        min_order_qty = Decimal(asset_info['lotSizeFilter']['minOrderQty'])
        min_order_amt = Decimal(asset_info['lotSizeFilter']['minOrderAmt'])

        return base_precision, min_order_qty, min_order_amt
    except KeyError as e:
        logging.error(f"Ошибка при извлечении данных точности для символа {symbol}: {e}")
        raise
    except Exception as e:
        logging.error(f"Ошибка при получении данных об инструменте {symbol}: {e}")
        raise


def get_asset_balance(session, asset):
    """
    Получение доступного баланса для заданного актива.
    :param session: Сессия ByBit API.
    :param asset: Название актива (например, BTC).
    :return: Баланс актива.
    """
    try:
        response = session.get_wallet_balance(accountType="UNIFIED")

        if response['retCode'] != 0:
            raise Exception(f"Ошибка получения баланса: {response['retMsg']}")

        coins = response['result']['list'][0]['coin']
        for coin in coins:
            if coin['coin'] == asset:
                balance = float(coin['walletBalance'])
                logging.info(f"Баланс {asset}: {balance:.8f}")
                return balance

        logging.warning(f"Актива {asset} нет в портфеле.")
        return 0
    except Exception as e:
        logging.error(f"Ошибка при получении баланса {asset}: {e}")
        raise

class ByBitHandler:
    """
    Класс для работы с API ByBit: покупка и продажа активов.
    """
    def __init__(self):
        self.session = HTTP(
            api_key=BYBIT_API_KEY_TEST,
            api_secret=BYBIT_API_SECRET_TEST,
            testnet=True  # Указываем, что работаем с тестовой сетью
        )

    def place_market_order(self, symbol, qty, side="Buy"):
        """
        Размещение рыночного ордера на ByBit.
        :param symbol: Торговая пара (например, BTCUSDT).
        :param qty: Количество актива или сумма в USDT.
        :param side: Сторона сделки ("Buy" или "Sell").
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
            return response
        except Exception as e:
            logging.error(f"Ошибка при размещении ордера: {e}")
            raise e

    def execute_trade(self, action, symbol, close_price):
        """
        Выполнение сделки на основе сигнала.
        :param action: "Buy" или "Sell".
        :param symbol: Торговая пара (например, BTCUSDT).
        :param close_price: Список цен закрытия.
        """
        try:
            base_precision, min_order_qty, min_order_amt = get_precision(symbol, self.session)

            if action == "Buy":
                qty = Decimal(100) / Decimal(close_price[-1])
                if qty < min_order_amt:
                    logging.warning(f"Сумма {qty} меньше минимально допустимой {min_order_amt}.")
                    return None
            elif action == "Sell":
                asset = symbol.split("USDT")[0]
                qty = Decimal(get_asset_balance(self.session, asset))
                if qty < min_order_qty:
                    logging.warning(f"Количество {qty:.8f} меньше минимально допустимого {min_order_qty:.8f}.")
                    return None

            qty = qty.quantize(base_precision, rounding=ROUND_DOWN)
            logging.info(f"Qty после округления: {qty}")

            return self.place_market_order(symbol, qty, side=action)
        except Exception as e:
            logging.error(f"Ошибка при выполнении сделки: {e}")
            raise
