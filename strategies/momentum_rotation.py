"""
多股票动量轮动策略
定期计算N日涨幅，持有最强的一只
"""
from rqalpha.api import order_target_percent, history_bars
import numpy as np


def init(context):
    # 备选股票池
    context.stocks = [
        '000001.XSHE',  # 平安银行
        '000002.XSHE',  # 万科A
        '600519.XSHG',  # 贵州茅台
        '601318.XSHG',  # 中国平安
        '000858.XSHE',  # 五粮液
    ]
    context.lookback = 20     # 回看周期（日）
    context.rebalance_day = 5  # 每N天调仓
    context.position_pct = 0.9


def handle_bar(context, bar_dict):
    # 每N天调仓一次
    if context.now.day % context.rebalance_day != 0:
        return

    best_stock = None
    best_return = -999

    for stock in context.stocks:
        prices = history_bars(stock, context.lookback + 1, '1d', 'close')
        if len(prices) < context.lookback + 1:
            continue
        ret = (prices[-1] - prices[0]) / prices[0]
        if ret > best_return:
            best_return = ret
            best_stock = stock

    if best_stock is None:
        return

    # 卖出非最强股
    for stock in context.stocks:
        position = context.portfolio.positions[stock]
        if position.quantity > 0 and stock != best_stock:
            order_target_percent(stock, 0)

    # 买入最强股
    order_target_percent(best_stock, context.position_pct)
