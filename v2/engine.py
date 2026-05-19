"""
v2.0 量化交易引擎
1. 板块优先：先选热点板块，再选个股
2. 每日信号：每天检查买卖，灵活进出
3. 多因子：板块热度 + 技术指标 + 量价关系
"""
import os, sys, json, time
import h5py, numpy as np, pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
BUNDLE = r"C:\Users\Jptr\.rqalpha\bundle"

# === 参数 ===
INIT_CASH = 100000
MAX_POS = 10
STOP_LOSS = -0.08
TAKE_PROFIT = 0.20
HOLD_MAX_DAYS = 25      # 最长持有天数（到期评估是否续持）
COMMISSION = 0.0015
START = '2025-04-01'
END = '2026-05-15'
REBALANCE_FREQ = 5       # 每N天重评板块


def load_dates():
    return pd.to_datetime(np.load(os.path.join(BUNDLE, 'trading_dates.npy')), format='%Y%m%d')


def load_df(sid):
    """加载单只股票数据"""
    with h5py.File(os.path.join(BUNDLE, 'stocks.h5'), 'r') as f:
        if sid not in f:
            return None
        raw = f[sid][:]
    df = pd.DataFrame(raw)
    df['date'] = pd.to_datetime(df['datetime'] // 1000000, format='%Y%m%d')
    df.set_index('date', inplace=True)
    df.drop('datetime', axis=1, inplace=True)
    return df


def load_ids():
    with h5py.File(os.path.join(BUNDLE, 'stocks.h5'), 'r') as f:
        return list(f.keys())


def ema(data, period):
    k = 2 / (period + 1)
    r = [data[0]]
    for v in data[1:]:
        r.append(v * k + r[-1] * (1 - k))
    return r


def score_sector(stocks_data, date):
    """板块热度: 动量40% + 广度30% + 量能30%"""
    date = pd.Timestamp(date)
    moms, ups, vols = [], 0, []
    for df in stocks_data:
        d = df[df.index <= date]
        if len(d) < 11:
            continue
        ret = (d['close'].iloc[-1] - d['close'].iloc[-11]) / d['close'].iloc[-11]
        moms.append(ret)
        if ret > 0: ups += 1
        avg20 = d['volume'].iloc[-20:].mean() if len(d) >= 20 else d['volume'].mean()
        if avg20 > 0:
            vols.append(d['volume'].iloc[-1] / avg20)
    if len(moms) < 5:
        return None
    return np.mean(moms) * 0.4 + (ups/len(moms) - 0.5) * 0.3 + (np.mean(vols) - 1) * 0.03 * 0.3


def score_stock(df, date):
    """个股评分: RSI + MACD + 布林 + 量能 + 动量"""
    date = pd.Timestamp(date)
    d = df[df.index <= date]
    if len(d) < 30:
        return None
    c = d['close'].values
    v = d['volume'].values
    p = c[-1]

    # RSI
    delta = np.diff(c[-15:])
    g = np.mean(np.where(delta > 0, delta, 0))
    l = np.mean(np.where(delta < 0, -delta, 0))
    rsi = 100 - 100 / (1 + g / l) if l > 0 else 50

    # MACD
    e12 = ema(list(c), 12)
    e26 = ema(list(c), 26)
    dif_chg = (e12[-1] - e26[-1]) - (e12[-2] - e26[-2])

    # 布林位置 (0=下轨 1=上轨)
    ma20 = np.mean(c[-20:])
    std = np.std(c[-20:])
    boll = (p - (ma20 - 2*std)) / (4*std) if std > 0 else 0.5

    # 量比
    vr = np.mean(v[-5:]) / np.mean(v[-20:]) if np.mean(v[-20:]) > 0 else 1

    # 5日动量
    mom5 = (c[-1] - c[-6]) / c[-6] if len(c) > 5 else 0

    # 综合（越高越好）
    s = (50 - rsi)/100 * 0.2 + dif_chg/p*50 * 0.3 + (0.35 - boll) * 0.2 + (min(vr,2)-1)*0.15 + mom5*0.15
    return {'score': s, 'price': p, 'rsi': rsi, 'boll': boll, 'vol_ratio': vr, 'momentum': mom5}


def run(sectors, active_pool):
    """回测主循环"""
    dates = load_dates()
    dates = dates[(dates >= pd.Timestamp(START)) & (dates <= pd.Timestamp(END))]

    # 过滤板块
    valid = {}
    for name, stocks in sectors.items():
        if name in ['[其他]', '其他']:
            continue
        pool = [s for s in stocks if s in active_pool]
        if len(pool) >= 15:
            valid[name] = pool
    print(f"有效板块: {len(valid)} | 交易日: {len(dates)}")

    # 按需加载缓存
    cache = {}
    def get(sid):
        if sid not in cache:
            cache[sid] = load_df(sid)
        return cache[sid]

    cash = INIT_CASH
    hold = {}  # sid -> {buy_price, buy_date, shares, sector}
    daily = []
    trades = []
    hot_sectors = []

    for i, date in enumerate(dates):
        ds = date.strftime('%Y-%m-%d')

        # 重评板块
        if i % REBALANCE_FREQ == 0:
            sec_scores = {}
            for sname, sids in valid.items():
                dfs = []
                for sid in sids[:40]:
                    df = get(sid)
                    if df is not None:
                        dfs.append(df)
                sc = score_sector(dfs, date)
                if sc is not None:
                    sec_scores[sname] = sc
            hot_sectors = sorted(sec_scores, key=sec_scores.get, reverse=True)[:5]

        # 卖出检查
        to_sell = []
        for sid, pos in hold.items():
            df = get(sid)
            if df is None:
                continue
            row = df[df.index == date]
            if len(row) == 0:
                continue
            px = row['close'].iloc[0]
            pnl = (px - pos['buy_price']) / pos['buy_price']
            days = (date - pos['buy_date']).days

            if pnl <= STOP_LOSS:
                to_sell.append((sid, px, pnl, f'止损{pnl*100:.1f}%'))
            elif pnl >= TAKE_PROFIT:
                to_sell.append((sid, px, pnl, f'止盈{pnl*100:.1f}%'))
            elif days >= HOLD_MAX_DAYS:
                s = score_stock(df, date)
                if s and s['score'] < 0:
                    to_sell.append((sid, px, pnl, f'持有{days}天信号转弱'))
                # 否则续持

        for sid, px, pnl, reason in to_sell:
            pos = hold.pop(sid)
            cash += pos['shares'] * px * (1 - COMMISSION)
            trades.append({'date': ds, 'act': 'SELL', 'stock': sid,
                           'buy': pos['buy_price'], 'sell': round(px,2),
                           'pnl': round(pnl*100,2), 'reason': reason,
                           'sector': pos['sector']})

        # 买入检查
        if len(hold) < MAX_POS:
            cands = []
            for sname in hot_sectors:
                for sid in valid.get(sname, [])[:30]:
                    if sid in hold:
                        continue
                    df = get(sid)
                    if df is None:
                        continue
                    s = score_stock(df, date)
                    if s and s['score'] > 0.02:
                        cands.append((sid, sname, s))
            cands.sort(key=lambda x: x[2]['score'], reverse=True)

            slots = MAX_POS - len(hold)
            budget = cash / max(slots, 1)
            for sid, sname, s in cands[:slots]:
                shares = int(budget / s['price'] / 100) * 100
                if shares < 100:
                    continue
                cost = shares * s['price'] * (1 + COMMISSION)
                if cost > cash:
                    continue
                cash -= cost
                hold[sid] = {'buy_price': s['price'], 'buy_date': date,
                             'shares': shares, 'sector': sname}
                trades.append({'date': ds, 'act': 'BUY', 'stock': sid,
                               'price': round(s['price'],2), 'shares': shares,
                               'sector': sname, 'score': round(s['score'],4)})

        # 记录
        val = cash
        for sid, pos in hold.items():
            df = get(sid)
            if df is not None:
                row = df[df.index == date]
                if len(row) > 0:
                    val += pos['shares'] * row['close'].iloc[0]

        daily.append({'date': ds, 'value': round(val,2), 'cash': round(cash,2),
                       'pos': len(hold), 'ret': round((val/INIT_CASH-1)*100,2)})

        if i % 20 == 0:
            print(f"  {ds} | 市值 {val:,.0f} | 持仓{len(hold)} | {daily[-1]['ret']:>+.2f}%")

    # 清算
    for sid, pos in list(hold.items()):
        df = get(sid)
        if df is not None:
            last = df[df.index <= pd.Timestamp(END)]
            if len(last) > 0:
                px = last['close'].iloc[-1]
                pnl = (px - pos['buy_price']) / pos['buy_price']
                cash += pos['shares'] * px * (1 - COMMISSION)
                trades.append({'date': END, 'act': 'SELL(清算)', 'stock': sid,
                               'buy': pos['buy_price'], 'sell': round(px,2),
                               'pnl': round(pnl*100,2), 'reason': '回测结束'})

    return daily, trades


if __name__ == '__main__':
    os.makedirs('v2/logs', exist_ok=True)
    with open('v2/sectors.json', 'r', encoding='utf-8') as f:
        sectors = json.load(f)

    # 筛选活跃股票
    print("筛选活跃股票...")
    all_ids = load_ids()
    active = set()
    with h5py.File(os.path.join(BUNDLE, 'stocks.h5'), 'r') as f:
        for sid in all_ids:
            raw = f[sid][:]
            last_dt = raw['datetime'][-1] // 1000000
            if last_dt >= 20250401 and len(raw) > 200:
                active.add(sid)
    print(f"活跃股票: {len(active)}")

    daily, trades = run(sectors, active)

    with open('v2/logs/daily.json', 'w', encoding='utf-8') as f:
        json.dump(daily, f, ensure_ascii=False)
    with open('v2/logs/trades.json', 'w', encoding='utf-8') as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)

    sells = [t for t in trades if 'SELL' in t['act']]
    wins = [t for t in sells if t['pnl'] > 0]
    print(f"\n{'='*50}")
    print(f"最终市值: {daily[-1]['value']:,.2f}")
    print(f"总收益: {daily[-1]['ret']:.2f}%")
    print(f"交易: {len([t for t in trades if t['act']=='BUY'])}买 {len(sells)}卖")
    print(f"胜率: {len(wins)/len(sells)*100:.1f}%" if sells else "无交易")
