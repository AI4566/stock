"""
MACD 策略
MACD金叉买入，死叉卖出
DIF上穿DEA为金叉，下穿为死叉
"""
from rqalpha.api import order_target_percent, history_bars


def init(context):
    context.stock = '000001.XSHE'
    context.fast = 12      # 快线周期
    context.slow = 26      # 慢线周期
    context.signal = 9     # 信号线周期
    context.position_pct = 0.8


def ema(prices, period):
    """计算EMA"""
    k = 2 / (period + 1)
    result = [prices[0]]
    for i in range(1, len(prices)):
        result.append(prices[i] * k + result[-1] * (1 - k))
    return result


def handle_bar(context, bar_dict):
    need_bars = context.slow + context.signal + 1
    prices = history_bars(context.stock, need_bars, '1d', 'close')
    if len(prices) < need_bars:
        return

    ema_fast = ema(list(prices), context.fast)
    ema_slow = ema(list(prices), context.slow)

    # DIF = EMA快 - EMA慢
    dif = [f - s for f, s in zip(ema_fast, ema_slow)]
    # DEA = EMA(DIF, signal)
    dea = ema(dif, context.signal)

    position = context.portfolio.positions[context.stock]

    # 金叉：DIF上穿DEA
    if dif[-2] <= dea[-2] and dif[-1] > dea[-1]:
        if position.quantity == 0:
            order_target_percent(context.stock, context.position_pct)

    # 死叉：DIF下穿DEA
    elif dif[-2] >= dea[-2] and dif[-1] < dea[-1]:
        if position.quantity > 0:
            order_target_percent(context.stock, 0)
