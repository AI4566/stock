"""
A股数据获取模块
统一接口：封装 akshare + Ashare 两个数据源
"""
import sys
import os
import datetime
import pandas as pd

# 添加 vendor 路径以导入 Ashare
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'vendor', 'Ashare'))
from Ashare import get_price as ashare_get_price


def fetch_ashare(code, end_date='', count=100, frequency='1d'):
    """通过 Ashare 获取行情数据（新浪/腾讯双源）"""
    return ashare_get_price(code, end_date=end_date, count=count, frequency=frequency)


def fetch_akshare_daily(symbol, start_date=None, end_date=None, adjust="qfq"):
    """
    通过 akshare 获取日线数据
    symbol: 股票代码，如 '600519'
    adjust: qfq=前复权, hfq=后复权, 空=不复权
    """
    import akshare as ak
    if end_date is None:
        end_date = datetime.datetime.now().strftime('%Y%m%d')
    if start_date is None:
        start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y%m%d')

    df = ak.stock_zh_a_hist(
        symbol=symbol,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust=adjust
    )
    df = df.rename(columns={
        '日期': 'date', '开盘': 'open', '收盘': 'close',
        '最高': 'high', '最低': 'low', '成交量': 'volume',
        '成交额': 'amount', '振幅': 'amplitude',
        '涨跌幅': 'pct_change', '涨跌额': 'change',
        '换手率': 'turnover'
    })
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df.index.name = ''
    return df


def fetch_akshare_realtime():
    """通过 akshare 获取实时行情（全市场）"""
    import akshare as ak
    return ak.stock_zh_a_spot_em()


def get_stock_data(code, source='ashare', **kwargs):
    """
    统一数据获取入口
    code: 股票代码
    source: 'ashare' 或 'akshare'
    """
    if source == 'ashare':
        return fetch_ashare(code, **kwargs)
    elif source == 'akshare':
        return fetch_akshare_daily(code, **kwargs)
    else:
        raise ValueError(f"未知数据源: {source}，可选 'ashare' 或 'akshare'")


if __name__ == '__main__':
    print("=== Ashare 数据源测试 ===")
    df1 = fetch_ashare('sh000001', count=5)
    print(df1)

    print("\n=== akshare 数据源测试 ===")
    df2 = fetch_akshare_daily('600519', start_date='20250101', end_date='20250501')
    print(df2.head())
