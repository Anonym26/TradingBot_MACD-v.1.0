import logging
from decimal import Decimal, ROUND_DOWN
from ..settings import deposit
from ..handlers.bybit_handler import get_precision, get_asset_balance

def market_order(session, symbol, side, close_price):
    """
    Размещение рыночного ордера с учётом минимальных требований ByBit.
    :param session: Сессия ByBit API.
    :param symbol: Торговая пара (например, BTCUSDT).
    :param side: Сторона сделки ("Buy" или "Sell").
    :param close_price: Список цен закрытия.
    :return: Ответ API или None при ошибке.
    """
    try:
        # Получаем параметры точности и минимальных значений для символа
        base_precision, min_order_qty, min_order_amt = get_precision(symbol, session)

        if side == "Buy":
            # Количество для покупки фиксировано в USDT
            qty = Decimal(deposit)
            if qty < min_order_amt:
                logging.warning(f"Сумма покупки ({qty}) меньше минимально допустимой {min_order_amt}.")
                return None
        elif side == "Sell":
            # Получаем баланс базового актива
            base_asset = symbol.split('USDT')[0]
            qty = Decimal(get_asset_balance(session, base_asset))
            if qty < min_order_qty:
                logging.warning(f"Количество для продажи ({qty}) меньше минимально допустимого {min_order_qty}.")
                return None

        # Округляем qty до base_precision
        qty = qty.quantize(base_precision, rounding=ROUND_DOWN)
        logging.info(f"Qty после округления: {qty}")

        # Размещение ордера
        response = session.place_order(
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
