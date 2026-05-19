"""
多策略组合选股票系统
每个策略对股票打分，加权组合后选前N只持有
"""
import sys
import os
import h5py
import numpy as np
import pandas as pd
from datetime import datetime

BUNDLE_PATH = r"C:\Users\Jptr\.rqalpha\bundle"


def load_stock_data(order_book_id, start_date=None, end_date=None):
    """从 bundle 加载单只股票数据"""
    with h5py.File(os.path.join(BUNDLE_PATH, 'stocks.h5'), 'r') as f:
        if order_book_id not in f:
            return None
        raw = f[order_book_id][:]

    df = pd.DataFrame(raw)
    df['date'] = df['datetime'] // 1000000
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    df.set_index('date', inplace=True)
    df.drop('datetime', axis=1, inplace=True)
    if start_date:
        df = df[df.index >= pd.Timestamp(start_date)]
    if end_date:
        df = df[df.index <= pd.Timestamp(end_date)]
    return df


def get_stock_list():
    """获取所有股票代码"""
    with h5py.File(os.path.join(BUNDLE_PATH, 'stocks.h5'), 'r') as f:
        return list(f.keys())


def score_ma_cross(prices, short=5, long=20):
    """双均线得分：短期>长期得正分"""
    if len(prices) < long + 1:
        return 0
    sma_s = prices[-short:].mean()
    sma_l = prices[-long:].mean()
    prev_s = prices[-short - 1:-1].mean()
    prev_l = prices[-long - 1:-1].mean()
    # 趋势强度
    trend = (sma_s - sma_l) / sma_l
    # 金叉加分
    if prev_s <= prev_l and sma_s > sma_l:
        trend += 0.02
    return trend


def score_macd(prices, fast=12, slow=26, signal=9):
    """MACD得分：DIF-DEA差值"""
    if len(prices) < slow + signal + 1:
        return 0
    prices = list(prices)

    def ema(data, period):
        k = 2 / (period + 1)
        result = [data[0]]
        for i in range(1, len(data)):
            result.append(data[i] * k + result[-1] * (1 - k))
        return result

    ema_f = ema(prices, fast)
    ema_s = ema(prices, slow)
    dif = [f - s for f, s in zip(ema_f, ema_s)]
    dea = ema(dif, signal)
    macd_hist = dif[-1] - dea[-1]
    # 归一化
    close = prices[-1]
    return macd_hist / close if close > 0 else 0


def score_rsi(prices, period=14):
    """RSI得分：越低越有反弹空间"""
    if len(prices) < period + 2:
        return 0
    prices = np.array(prices)
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return -0.5  # RSI=100 超买
    rs = avg_gain / avg_loss
    rsi = 100 - 100 / (1 + rs)
    # RSI越低分数越高（超卖反弹机会）
    return (50 - rsi) / 100


def score_boll(prices, period=20, std_mult=2.0):
    """布林带得分：价格越接近下轨分数越高"""
    if len(prices) < period:
        return 0
    closes = np.array(prices[-period:])
    ma = closes.mean()
    std = closes.std()
    upper = ma + std_mult * std
    lower = ma - std_mult * std
    price = prices[-1]
    if upper == lower:
        return 0
    # 位置：0=下轨, 1=上轨
    pos = (price - lower) / (upper - lower)
    # 越靠近下轨分数越高
    return (0.5 - pos)


def score_momentum(prices, lookback=20):
    """动量得分：近期涨幅"""
    if len(prices) < lookback + 1:
        return 0
    return (prices[-1] - prices[-lookback - 1]) / prices[-lookback - 1]


def score_stock(df, weights=None):
    """
    综合打分：5个策略加权
    weights: dict, 各策略权重
    """
    if df is None or len(df) < 60:
        return None

    if weights is None:
        weights = {
            'ma': 0.15,
            'macd': 0.25,
            'rsi': 0.15,
            'boll': 0.30,
            'momentum': 0.15,
        }

    closes = df['close'].values
    scores = {
        'ma': score_ma_cross(closes),
        'macd': score_macd(closes),
        'rsi': score_rsi(closes),
        'boll': score_boll(closes),
        'momentum': score_momentum(closes),
    }

    total = sum(scores[k] * weights.get(k, 0) for k in scores)
    return {
        'total_score': total,
        'detail': scores,
    }


def select_stocks(as_of_date, top_n=10, weights=None, pool=None):
    """
    在 as_of_date 时点选股票
    只用 as_of_date 及之前的数据
    返回 top_n 只综合得分最高的股票
    """
    if pool is None:
        pool = get_stock_list()

    results = []
    as_of = pd.Timestamp(as_of_date)

    for stock_id in pool:
        try:
            df = load_stock_data(stock_id, end_date=as_of)
            if df is None or len(df) < 60:
                continue
            # 只用最近一年的数据计算
            one_year_ago = as_of - pd.Timedelta(days=400)
            df_recent = df[df.index >= one_year_ago]
            if len(df_recent) < 60:
                continue

            result = score_stock(df_recent, weights)
            if result is not None:
                result['stock'] = stock_id
                result['last_price'] = df['close'].iloc[-1]
                result['last_date'] = df.index[-1].strftime('%Y%m%d')
                results.append(result)
        except Exception:
            continue

    # 按总分排序
    results.sort(key=lambda x: x['total_score'], reverse=True)
    return results[:top_n]


if __name__ == '__main__':
    import time
    test_date = '2025-03-31'
    print(f"在 {test_date} 选股...")

    # 先用少量股票测试
    sample_pool = [
        '000001.XSHE', '000002.XSHE', '600519.XSHG', '601318.XSHG',
        '000858.XSHE', '002415.XSHE', '600036.XSHG', '000333.XSHE',
        '002714.XSHE', '300750.XSHE', '000725.XSHE', '601012.XSHG',
        '300059.XSHE', '600276.XSHG', '002352.XSHE',
    ]

    t0 = time.time()
    picks = select_stocks(test_date, top_n=5, pool=sample_pool)
    print(f"耗时: {time.time() - t0:.1f}s")

    for i, p in enumerate(picks):
        print(f"\n#{i + 1}: {p['stock']}")
        print(f"  总分: {p['total_score']:.6f}")
        print(f"  最新价: {p['last_price']}")
        print(f"  各策略: {', '.join(f'{k}={v:.5f}' for k, v in p['detail'].items())}")
