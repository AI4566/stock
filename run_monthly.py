"""
月度回测运行入口
分两步：先回测选股+盈亏，再获取实际起飞股票
"""
import os
import sys
import json
import time
import h5py
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from strategies.portfolio import load_stock_data, select_stocks, score_stock
from monthly_backtest import (
    BUNDLE_PATH, INIT_CASH, TOP_N, COMMISSION, MONTHS,
    get_month_range, get_prev_month_end, get_actual_top_stocks
)


def build_filtered_pool(min_days=500):
    """筛选有足够历史的活跃股票"""
    pool = []
    with h5py.File(os.path.join(BUNDLE_PATH, 'stocks.h5'), 'r') as f:
        for stock_id in f.keys():
            data = f[stock_id][:]
            # 2025年之后仍有交易
            dates = data['datetime'] // 1000000
            has_recent = np.any(dates >= 20250401)
            has_enough = len(data) >= min_days
            # 排除ST、退市等（简单过滤：数据足够长）
            if has_recent and has_enough:
                pool.append(stock_id)
    print(f"筛选后股票池: {len(pool)}只 (原始5500+)")
    return pool


def run_backtest(pool):
    """运行月度回测"""
    os.makedirs('logs', exist_ok=True)
    results = []
    portfolio_value = INIT_CASH

    for month_str in MONTHS:
        t0 = time.time()
        select_date = get_prev_month_end(month_str)
        month_start, month_end = get_month_range(month_str)

        print(f"\n{'='*50}")
        print(f"月份: {month_str} | 截止: {select_date} | 组合: {portfolio_value:,.0f}")
        print(f"{'='*50}")

        # 选股
        picks = select_stocks(select_date, top_n=TOP_N, pool=pool)

        if not picks:
            results.append({
                'month': month_str, 'select_date': str(select_date)[:10],
                'stocks': [], 'avg_return': 0, 'portfolio_value': round(portfolio_value, 2),
                'monthly_pnl': 0, 'total_return': round((portfolio_value / INIT_CASH - 1) * 100, 2),
            })
            continue

        # 计算月收益
        stock_details = []
        month_returns = []
        for p in picks:
            sid = p['stock']
            df = load_stock_data(sid)
            if df is None:
                continue
            before = df[df.index <= pd.Timestamp(select_date)]
            during = df[(df.index >= pd.Timestamp(month_start)) &
                        (df.index < pd.Timestamp(month_end))]
            if len(before) < 1 or len(during) < 1:
                continue
            buy = float(before['close'].iloc[-1])
            sell = float(during['close'].iloc[-1])
            ret = (sell - buy) / buy
            month_returns.append(ret)
            stock_details.append({
                'stock': sid,
                'score': round(p['total_score'], 6),
                'buy_price': round(buy, 2),
                'sell_price': round(sell, 2),
                'return': round(ret * 100, 2),
            })

        avg_ret = np.mean(month_returns) - COMMISSION if month_returns else 0
        monthly_pnl = portfolio_value * avg_ret
        portfolio_value *= (1 + avg_ret)

        result = {
            'month': month_str,
            'select_date': str(select_date)[:10],
            'stocks': stock_details,
            'avg_return': round(avg_ret * 100, 2),
            'portfolio_value': round(portfolio_value, 2),
            'monthly_pnl': round(monthly_pnl, 2),
            'total_return': round((portfolio_value / INIT_CASH - 1) * 100, 2),
        }
        results.append(result)

        # 打印本月结果
        for s in stock_details:
            emoji = "  " if s['return'] >= 0 else "  "
            print(f"  {emoji} {s['stock']:15s} {s['buy_price']:>8.2f} → {s['sell_price']:>8.2f}  {s['return']:>+7.2f}%")
        sign = "+" if avg_ret >= 0 else ""
        print(f"  月收益: {sign}{avg_ret*100:.2f}% | 市值: {portfolio_value:,.2f} | 累计: {(portfolio_value/INIT_CASH-1)*100:>+.2f}% | {time.time()-t0:.1f}s")

    with open('logs/backtest_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return results


def collect_actual_top(pool, results):
    """获取每月实际涨幅前10（用于对比报告）"""
    actual = {}
    for r in results:
        month = r['month']
        print(f"获取 {month} 实际TOP10...")
        top = get_actual_top_stocks(month, top_n=10)
        actual[month] = top
        if top:
            print(f"  实际最强: {top[0]['stock']} {top[0]['return']*100:>+.2f}%")
    with open('logs/actual_top_stocks.json', 'w', encoding='utf-8') as f:
        json.dump(actual, f, ensure_ascii=False, indent=2)
    return actual


if __name__ == '__main__':
    print("第一步：构建股票池...")
    pool = build_filtered_pool(min_days=500)
    print(f"\n第二步：月度回测 ({len(MONTHS)}个月)...")
    results = run_backtest(pool)
    print(f"\n第三步：获取每月实际TOP10...")
    actual = collect_actual_top(pool, results)
    print(f"\n完成！最终市值: {results[-1]['portfolio_value']:,.2f} | 总收益: {results[-1]['total_return']:.2f}%")
