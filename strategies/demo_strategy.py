"""
rqalpha 示例策略：双均线交叉
当短期均线上穿长期均线时买入，下穿时卖出
"""
from rqalpha.api import order_target_percent, history_bars


def init(context):
    """策略初始化"""
    context.stock = '000001.XSHE'  # 平安银行
    context.short_window = 5       # 短期均线周期
    context.long_window = 20       # 长期均线周期
    context.position_pct = 0.8     # 持仓比例


def handle_bar(context, bar_dict):
    """每日盘后调用"""
    # 获取历史收盘价
    prices = history_bars(context.stock, context.long_window + 1, '1d', 'close')

    if len(prices) < context.long_window + 1:
        return

    # 计算均线
    short_ma = prices[-context.short_window:].mean()
    long_ma = prices[-context.long_window:].mean()
    prev_short_ma = prices[-context.short_window - 1:-1].mean()
    prev_long_ma = prices[-context.long_window - 1:-1].mean()

    # 获取当前持仓
    position = context.portfolio.positions[context.stock]

    # 金叉买入
    if prev_short_ma <= prev_long_ma and short_ma > long_ma:
        if position.quantity == 0:
            order_target_percent(context.stock, context.position_pct)

    # 死叉卖出
    elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
        if position.quantity > 0:
            order_target_percent(context.stock, 0)
