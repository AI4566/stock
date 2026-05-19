"""
RSI 策略
RSI < 30 超卖买入，RSI > 70 超买卖出
"""
from rqalpha.api import order_target_percent, history_bars
import numpy as np


def init(context):
    context.stock = '000001.XSHE'
    context.period = 14
    context.oversold = 30
    context.overbought = 70
    context.position_pct = 0.8


def calc_rsi(prices, period):
    """计算RSI"""
    prices = np.array(prices)
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def handle_bar(context, bar_dict):
    need_bars = context.period + 2
    prices = history_bars(context.stock, need_bars, '1d', 'close')
    if len(prices) < need_bars:
        return

    rsi_now = calc_rsi(list(prices), context.period)
    rsi_prev = calc_rsi(list(prices[:-1]), context.period)

    position = context.portfolio.positions[context.stock]

    # RSI从超卖区上穿：买入
    if rsi_prev <= context.oversold and rsi_now > context.oversold:
        if position.quantity == 0:
            order_target_percent(context.stock, context.position_pct)

    # RSI从超买区下穿：卖出
    elif rsi_prev >= context.overbought and rsi_now < context.overbought:
        if position.quantity > 0:
            order_target_percent(context.stock, 0)
