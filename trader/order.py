import ccxt


def make_order(
    exchange: ccxt.Exchange,
    symbol: str,
    order_type: str,
    side: str,
    amount: float,
    price: float = None,
    params: dict = {},
) -> dict:
    """
    下單的 helper function
    Support : 市價單 & 限價單
    """
    if order_type == "market":
        order = exchange.create_market_order(symbol, side, amount, params)
    elif order_type == "limit":
        if price is None:
            raise ValueError("Price must be specified for limit orders.")
        order = exchange.create_limit_order(symbol, side, amount, price, params)
    else:
        raise ValueError(f"Unsupported order type: {order_type}")

    return order