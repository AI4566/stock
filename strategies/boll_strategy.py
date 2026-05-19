"""
布林带策略
价格突破下轨买入，突破上轨卖出
"""
from rqalpha.api import order_target_percent, history_bars
import numpy as np


def init(context):
    context.stock = '000001.XSHE'
    context.period = 20     # 布林带周期
    context.std_mult = 2.0  # 标准差倍数
    context.position_pct = 0.8


def handle_bar(context, bar_dict):
    need_bars = context.period + 1
    closes = history_bars(context.stock, need_bars, '1d', 'close')
    if len(closes) < need_bars:
        return

    closes = np.array(closes)
    price = closes[-1]
    ma = np.mean(closes[-context.period:])
    std = np.std(closes[-context.period:])

    upper = ma + context.std_mult * std
    lower = ma - context.std_mult * std

    position = context.portfolio.positions[context.stock]

    # 价格跌破下轨：买入
    if price <= lower:
        if position.quantity == 0:
            order_target_percent(context.stock, context.position_pct)

    # 价格突破上轨：卖出
    elif price >= upper:
        if position.quantity > 0:
            order_target_percent(context.stock, 0)
