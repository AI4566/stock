"""
月度回测系统
从2025年4月到2026年5月，每月选股票并跟踪盈亏
模拟真实投资：每月末选股，下月初买入，月末结算
"""
import sys
import os
import json
import time
import h5py
import numpy as np
import pandas as pd
from strategies.portfolio import (
    load_stock_data, get_stock_list, select_stocks, score_stock
)

BUNDLE_PATH = r"C:\Users\Jptr\.rqalpha\bundle"
INIT_CASH = 100000
TOP_N = 10  # 每月选几只
COMMISSION = 0.0015  # 手续费 0.15%（双边）

# 回测月份
MONTHS = [
    '2025-04', '2025-05', '2025-06', '2025-07', '2025-08', '2025-09',
    '2025-10', '2025-11', '2025-12', '2026-01', '2026-02', '2026-03',
    '2026-04', '2026-05',
]


def get_month_range(month_str):
    """获取月份的起止日期"""
    year, month = month_str.split('-')
    start = f'{year}-{month}-01'
    if month == '12':
        end = f'{int(year) + 1}-01-01'
    else:
        end = f'{year}-{int(month) + 1:02d}-01'
    return start, end


def get_prev_month_end(month_str):
    """获取上个月最后一天"""
    year, month = month_str.split('-')
    month = int(month)
    if month == 1:
        return f'{int(year) - 1}-12-31'
    else:
        return pd.Timestamp(f'{year}-{month:02d}-01') - pd.Timedelta(days=1)
        return prev.strftime('%Y-%m-%d')


def get_actual_top_stocks(month_str, top_n=10):
    """获取该月实际涨幅最大的股票"""
    month_start, month_end = get_month_range(month_str)
    prev_end = get_prev_month_end(month_str)

    with h5py.File(os.path.join(BUNDLE_PATH, 'stocks.h5'), 'r') as f:
        stock_ids = list(f.keys())

    performers = []
    for stock_id in stock_ids:
        try:
            df = load_stock_data(stock_id)
            if df is None or len(df) < 2:
                continue
            month_data = df[(df.index >= pd.Timestamp(month_start)) &
                            (df.index < pd.Timestamp(month_end))]
            before_data = df[df.index <= pd.Timestamp(prev_end)]
            if len(month_data) < 2 or len(before_data) < 1:
                continue
            buy_price = before_data['close'].iloc[-1]
            sell_price = month_data['close'].iloc[-1]
            ret = (sell_price - buy_price) / buy_price
            performers.append({
                'stock': stock_id,
                'buy_price': buy_price,
                'sell_price': sell_price,
                'return': ret,
            })
        except Exception:
            continue

    performers.sort(key=lambda x: x['return'], reverse=True)
    return performers[:top_n]


def run_monthly_backtest():
    """运行月度回测"""
    results = []
    portfolio_value = INIT_CASH
    prev_end = None

    # 加载全部股票ID用于选股
    all_stocks = get_stock_list()
    print(f"股票池总数: {len(all_stocks)}")

    for month_str in MONTHS:
        t0 = time.time()
        month_start, month_end = get_month_range(month_str)
        select_date = get_prev_month_end(month_str)

        print(f"\n{'='*60}")
        print(f"月份: {month_str} | 选股日期: {select_date}")
        print(f"{'='*60}")

        # 选股（只用选股日期之前的数据）
        picks = select_stocks(select_date, top_n=TOP_N, pool=all_stocks)

        if not picks:
            print(f"  无选股结果，跳过")
            results.append({
                'month': month_str,
                'stocks': [],
                'returns': [],
                'avg_return': 0,
                'portfolio_value': portfolio_value,
                'monthly_pnl': 0,
            })
            continue

        # 计算每只股票的月收益
        month_returns = []
        stock_details = []
        for p in picks:
            stock_id = p['stock']
            df = load_stock_data(stock_id)
            if df is None:
                continue
            before = df[df.index <= pd.Timestamp(select_date)]
            during = df[(df.index >= pd.Timestamp(month_start)) &
                        (df.index < pd.Timestamp(month_end))]
            if len(before) < 1 or len(during) < 1:
                continue
            buy = before['close'].iloc[-1]
            sell = during['close'].iloc[-1]
            ret = (sell - buy) / buy
            month_returns.append(ret)
            stock_details.append({
                'stock': stock_id,
                'score': round(p['total_score'], 6),
                'buy_price': round(buy, 2),
                'sell_price': round(sell, 2),
                'return': round(ret * 100, 2),
            })

        # 等权组合收益（扣除手续费）
        if month_returns:
            avg_return = np.mean(month_returns) - COMMISSION
        else:
            avg_return = 0

        monthly_pnl = portfolio_value * avg_return
        portfolio_value = portfolio_value * (1 + avg_return)

        result = {
            'month': month_str,
            'select_date': str(select_date)[:10],
            'stocks': stock_details,
            'avg_return': round(avg_return * 100, 2),
            'portfolio_value': round(portfolio_value, 2),
            'monthly_pnl': round(monthly_pnl, 2),
            'total_return': round((portfolio_value / INIT_CASH - 1) * 100, 2),
        }
        results.append(result)

        # 打印
        print(f"  选股 ({len(stock_details)}只):")
        for s in stock_details:
            print(f"    {s['stock']:15s}  买入{s['buy_price']:>8.2f}  卖出{s['sell_price']:>8.2f}  收益{s['return']:>+7.2f}%")
        print(f"  月均收益: {avg_return * 100:>+.2f}%")
        print(f"  组合市值: {portfolio_value:,.2f}")
        print(f"  累计收益: {(portfolio_value / INIT_CASH - 1) * 100:>+.2f}%")
        print(f"  耗时: {time.time() - t0:.1f}s")

    # 保存结果
    with open('logs/backtest_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results


def get_monthly_actual_top(results):
    """获取每月实际涨幅前10的股票"""
    actual_data = {}
    for r in results:
        month = r['month']
        print(f"获取 {month} 实际涨幅前10...")
        top = get_actual_top_stocks(month, top_n=10)
        actual_data[month] = top
        for i, t in enumerate(top[:5]):
            print(f"  #{i+1}: {t['stock']} {t['return']*100:>+.2f}%")

    with open('logs/actual_top_stocks.json', 'w', encoding='utf-8') as f:
        json.dump(actual_data, f, ensure_ascii=False, indent=2)

    return actual_data


if __name__ == '__main__':
    os.makedirs('logs', exist_ok=True)
    print("开始月度回测 (2025.04 ~ 2026.05)")
    print(f"初始资金: {INIT_CASH:,.0f} | 每月选股: {TOP_N}只")

    results = run_monthly_backtest()

    print(f"\n{'='*60}")
    print("回测完成，获取每月实际涨幅前10...")
    print(f"{'='*60}")
    actual = get_monthly_actual_top(results)

    print(f"\n最终组合市值: {results[-1]['portfolio_value']:,.2f}")
    print(f"总收益: {results[-1]['total_return']:.2f}%")
