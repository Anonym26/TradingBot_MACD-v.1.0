import logging
from decimal import Decimal, ROUND_DOWN
from pybit.unified_trading import HTTP
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
from src.settings import DEPOSIT, USE_TOTAL_BALANCE

load_dotenv()
BYBIT_API_KEY_TEST = os.getenv("BYBIT_API_KEY_TEST")
BYBIT_API_SECRET_TEST = os.getenv("BYBIT_API_SECRET_TEST")

class ByBitHandler:
    """
    Класс для работы с API ByBit: покупка и продажа активов.
    """
    def __init__(self):
        self.deposit = DEPOSIT
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

    async def get_asset_balance(self, asset):
        """
        Получение доступного баланса для заданного актива.
        :param asset: Название актива (например, BTC).
        :return: Баланс актива.
        """
        try:
            response = self.session.get_wallet_balance(accountType="UNIFIED")

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

    async def place_market_order(self, symbol, side, close_price, use_total_balance=USE_TOTAL_BALANCE):
        """
        Размещение рыночного ордера с учётом минимальных требований ByBit.
        :param symbol: Торговая пара (например, BTCUSDT).
        :param side: Сторона сделки ("Buy" или "Sell").
        :param close_price: Текущая цена актива.
        :param use_total_balance: Использовать весь баланс для покупки (True) или фиксированную сумму (False).
        :return: Ответ API или None при ошибке.
        """
        try:
            # Получаем параметры точности и минимальных значений
            base_precision, min_order_qty, min_order_amt = await self.get_precision(symbol)

            if side == "Buy":
                if use_total_balance:
                    usdt_balance = Decimal(await self.get_asset_balance("USDT"))
                    qty = usdt_balance
                    if qty < min_order_amt:
                        logging.warning(f"Баланс USDT ({qty}) "
                                        f"меньше минимально допустимой суммы {min_order_amt}.")
                        return None
                else:
                    qty = Decimal(self.deposit)   # Здесь используется фиксированный депозит
                    if qty < min_order_amt:
                        logging.warning(f"Сумма покупки ({qty }) меньше минимально допустимой {min_order_amt}.")
                        return None

            elif side == "Sell":
                base_asset = symbol.split('USDT')[0]
                qty = Decimal(await self.get_asset_balance(base_asset))
                if qty < min_order_qty:
                    logging.warning(f"Количество для продажи ({qty}) меньше минимально допустимого {min_order_qty}.")
                    return None
            else:
                raise ValueError(f"Некорректная сторона сделки: {side}")

            qty = qty.quantize(base_precision, rounding=ROUND_DOWN)
            logging.info(f"Qty после округления: {qty}")

            response = self.session.place_order(
                category="spot",
                symbol=symbol,
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
