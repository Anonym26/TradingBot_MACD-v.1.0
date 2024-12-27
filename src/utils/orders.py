from decimal import Decimal, ROUND_DOWN
from ..settings import deposit


def market_order(session, symbol, side, close_price):
    """
    Размещение рыночного ордера с учетом типа сделки.
    :param session: Сессия ByBit API.
    :param symbol: Торговая пара (например, BTCUSDT).
    :param side: Сторона сделки ("Buy" или "Sell").
    :param close_price: Список цен закрытия.
    :return: Ответ API или None при ошибке.
    """
    # Получаем точность и параметры инструмента
    qty_p, _, min_order_amt = get_precision(symbol, session)

    if side == "Buy":
        # Qty при покупке выражено в USDT (депозит фиксирован)
        qty = Decimal(deposit)
        print(f"Qty для покупки (в USDT): {qty}")
    elif side == "Sell":
        # Qty при продаже определяется доступным балансом базового актива
        base_asset = symbol.split('USDT')[0]
        balance = get_asset_balance(session, base_asset)
        qty = Decimal(balance)
        print(f"Qty для продажи (баланс {base_asset}): {qty}")

    # Убираем лишние знаки после запятой
    qty = qty.quantize(Decimal(f'1e-{qty_p}'), rounding=ROUND_DOWN)

    print(f"Qty после обрезки: {qty}, Минимальная сумма ордера: {min_order_amt}")

    # Проверяем, что сумма ордера не меньше минимально допустимой
    if side == "Buy":
        order_value = qty
    else:
        order_value = qty * Decimal(close_price[-1])

    if order_value < Decimal(min_order_amt):
        print(
            f"Недостаточно средств для размещения ордера. Минимальная сумма: {min_order_amt}, текущая сумма: {order_value:.2f}")
        return None

    try:
        response = session.place_order(
            category="spot",
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=str(qty),
            timeInForce="GTC",
        )
        print(f"Ордер размещен: {response}")
        return response
    except Exception as e:
        print(f"Ошибка размещения ордера: {e}")
        return None


def get_precision(symbol, session):
    """
    Получение точности количества, цены и минимальной суммы ордера для указанного символа.
    :param symbol: Торговая пара (например, BTCUSDT).
    :param session: Сессия ByBit API.
    :return: Точность количества (qty_p), цены (limit_p), минимальная сумма ордера (min_order_amt).
    """
    response = session.get_instruments_info(
        category="spot",
        symbol=symbol
    )

    if response['retCode'] != 0:
        raise Exception(f"Ошибка получения информации об инструменте: {response['retMsg']}\n{response}")

    try:
        lot_size_filter = response['result']['list'][0]['lotSizeFilter']
        price_filter = response['result']['list'][0]['priceFilter']

        # Получаем параметры точности
        qty_step = Decimal(lot_size_filter.get('qtyStep', '1'))
        tick_size = Decimal(price_filter.get('tickSize', '1'))
        min_order_amt = lot_size_filter.get('minOrderAmt', '1')

        qty_p = abs(qty_step.as_tuple().exponent)  # Количество знаков после запятой для qty
        limit_p = abs(tick_size.as_tuple().exponent)  # Количество знаков после запятой для цены

        return qty_p, limit_p, min_order_amt
    except (KeyError, IndexError, ValueError) as e:
        raise Exception(f"Ошибка при обработке данных инструмента: {e}")


def get_asset_balance(session, asset):
    """
    Получение доступного баланса для заданного актива.
    :param session: Сессия ByBit API.
    :param asset: Название актива (например, BTC).
    :return: Баланс актива.
    """
    response = session.get_wallet_balance(accountType="UNIFIED")

    if response['retCode'] != 0:
        raise Exception(f"Ошибка получения баланса: {response['retMsg']}")

    coins = response.get('result', {}).get('list', [{}])[0].get('coin', [])
    for coin in coins:
        if coin['coin'] == asset:
            return float(coin['walletBalance'])

    print(f"Актива {asset} нет на счете.")
    return 0  # Если актив отсутствует в балансе
