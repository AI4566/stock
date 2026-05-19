"""
v2.0 HTML报告生成器
对比 v1.5（月度）和 v2.0（每日灵活）的表现
"""
import json
import os

def generate():
    # 加载 v2.0 数据
    with open('v2/logs/daily.json', 'r', encoding='utf-8') as f:
        daily = json.load(f)
    with open('v2/logs/trades.json', 'r', encoding='utf-8') as f:
        trades = json.load(f)

    # 加载 v1.5 数据
    v1_daily = []
    v1_trades = []
    if os.path.exists('logs/backtest_results.json'):
        with open('logs/backtest_results.json', 'r') as f:
            v1_results = json.load(f)
        v1_daily = [{'date': r['month']+'-15', 'value': r['portfolio_value'], 'ret': r['total_return']}
                    for r in v1_results]
        v1_daily.insert(0, {'date': '2025-03-31', 'value': 100000, 'ret': 0})

    # 统计
    sells = [t for t in trades if 'SELL' in t['act']]
    wins = [t for t in sells if t['pnl'] > 0]
    losses = [t for t in sells if t['pnl'] <= 0]
    win_rate = len(wins) / len(sells) * 100 if sells else 0
    avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0

    # 持仓天数分布
    hold_days = []
    buy_map = {}
    for t in trades:
        if t['act'] == 'BUY':
            buy_map[t['stock']] = t
        elif 'SELL' in t['act'] and t['stock'] in buy_map:
            from datetime import datetime
            bd = datetime.strptime(buy_map[t['stock']]['date'], '%Y-%m-%d')
            sd = datetime.strptime(t['date'], '%Y-%m-%d')
            hold_days.append((sd - bd).days)

    # 板块命中统计
    sector_wins = {}
    for t in sells:
        sec = t.get('sector', '未知')
        if sec not in sector_wins:
            sector_wins[sec] = {'total': 0, 'win': 0}
        sector_wins[sec]['total'] += 1
        if t['pnl'] > 0:
            sector_wins[sec]['win'] += 1

    # 生成HTML
    dates_json = json.dumps([d['date'] for d in daily])
    values_json = json.dumps([d['value'] for d in daily])

    # v1.5 数据
    v1_dates = json.dumps([d['date'] for d in v1_daily])
    v1_values = json.dumps([d['value'] for d in v1_daily])

    # 交易记录表格
    trades_html = ""
    for t in reversed(trades[-100:]):  # 最近100笔
        color = "#27ae60" if t.get('pnl', 0) > 0 else "#e74c3c" if t.get('pnl', 0) < 0 else "#888"
        pnl_str = f"{t['pnl']:+.2f}%" if 'pnl' in t else ""
        trades_html += f"""<tr>
            <td>{t['date']}</td>
            <td>{t['act']}</td>
            <td>{t['stock']}</td>
            <td>{t.get('sector','')}</td>
            <td>{t.get('price', t.get('buy',''))}</td>
            <td>{t.get('sell','')}</td>
            <td style="color:{color};font-weight:bold">{pnl_str}</td>
            <td>{t.get('reason','')}</td>
            <td>{t.get('score','')}</td>
        </tr>"""

    # 板块胜率表
    sector_html = ""
    for sec, st in sorted(sector_wins.items(), key=lambda x: x[1]['win']/max(x[1]['total'],1), reverse=True):
        wr = st['win'] / st['total'] * 100 if st['total'] > 0 else 0
        bar_w = int(wr)
        sector_html += f"""<tr>
            <td>{sec}</td>
            <td>{st['total']}</td>
            <td>{st['win']}</td>
            <td><div style="background:#1a3a5c;width:100%;height:16px;border-radius:3px">
                <div style="background:{'#27ae60' if wr>=50 else '#e74c3c'};width:{bar_w}%;height:16px;border-radius:3px"></div>
            </div></td>
            <td style="color:{'#27ae60' if wr>=50 else '#e74c3c'}">{wr:.0f}%</td>
        </tr>"""

    # 持仓天数分布
    if hold_days:
        buckets = {'0-5天': 0, '6-10天': 0, '11-15天': 0, '16-20天': 0, '21-25天': 0, '25天+': 0}
        for d in hold_days:
            if d <= 5: buckets['0-5天'] += 1
            elif d <= 10: buckets['6-10天'] += 1
            elif d <= 15: buckets['11-15天'] += 1
            elif d <= 20: buckets['16-20天'] += 1
            elif d <= 25: buckets['21-25天'] += 1
            else: buckets['25天+'] += 1
        hold_labels = json.dumps(list(buckets.keys()))
        hold_values = json.dumps(list(buckets.values()))
    else:
        hold_labels = '[]'
        hold_values = '[]'

    final = daily[-1]
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>v2.0 量化回测报告</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'Microsoft YaHei',sans-serif;background:#0a0a1a;color:#e0e0e0}}
.c{{max-width:1200px;margin:0 auto;padding:20px}}
h1{{text-align:center;color:#00d4ff;margin:20px 0}}
h2{{color:#00d4ff;border-bottom:2px solid #1a3a5c;padding:10px 0;margin:25px 0 10px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:15px 0}}
.card{{background:#111128;border:1px solid #1a3a5c;border-radius:10px;padding:15px;text-align:center}}
.card .v{{font-size:26px;font-weight:bold}}
.card .l{{color:#888;font-size:13px;margin-top:4px}}
.pos{{color:#27ae60}}.neg{{color:#e74c3c}}
.box{{background:#111128;border:1px solid #1a3a5c;border-radius:10px;padding:15px;margin:15px 0}}
table{{width:100%;border-collapse:collapse}}
th{{background:#1a2a4a;padding:8px;text-align:left;color:#00d4ff;font-size:13px}}
td{{padding:6px 8px;border-bottom:1px solid #1a2a3a;font-size:13px}}
tr:hover{{background:#1a2a3a}}
.compare{{display:grid;grid-template-columns:1fr 1fr;gap:15px}}
@media(max-width:768px){{.compare{{grid-template-columns:1fr}}}}
</style></head><body><div class="c">
<h1>v2.0 量化交易回测报告</h1>
<p style="text-align:center;color:#888">灵活进出 | 板块优先 | 每日信号 | {START}~{END}</p>

<div class="grid">
<div class="card"><div class="v {'pos' if final['ret']>=0 else 'neg'}">{final['ret']:+.2f}%</div><div class="l">v2.0 总收益</div></div>
<div class="card"><div class="v">{final['value']:,.0f}</div><div class="l">最终市值</div></div>
<div class="card"><div class="v">{len([t for t in trades if t['act']=='BUY'])}</div><div class="l">买入次数</div></div>
<div class="card"><div class="v">{len(sells)}</div><div class="l">卖出次数</div></div>
<div class="card"><div class="v {'pos' if win_rate>=50 else 'neg'}">{win_rate:.1f}%</div><div class="l">胜率</div></div>
<div class="card"><div class="v pos">{avg_win:+.2f}%</div><div class="l">平均盈利</div></div>
<div class="card"><div class="v neg">{avg_loss:+.2f}%</div><div class="l">平均亏损</div></div>
<div class="card"><div class="v">{sum(hold_days)/len(hold_days):.1f}天</div><div class="l">平均持仓</div></div>
</div>

<h2>v2.0 vs v1.5 市值走势对比</h2>
<div class="compare">
<div class="box"><canvas id="chart1" height="200"></canvas></div>
<div class="box"><canvas id="chart2" height="200"></canvas></div>
</div>

<h2>持仓天数分布</h2>
<div class="box"><canvas id="chart3" height="120"></canvas></div>

<h2>板块胜率排名</h2>
<div class="box"><table>
<thead><tr><th>板块</th><th>交易数</th><th>盈利数</th><th>胜率</th><th>比例</th></tr></thead>
<tbody>{sector_html}</tbody>
</table></div>

<h2>交易记录（最近100笔）</h2>
<div class="box" style="overflow-x:auto"><table>
<thead><tr><th>日期</th><th>操作</th><th>股票</th><th>板块</th><th>买入价</th><th>卖出价</th><th>盈亏</th><th>原因</th><th>评分</th></tr></thead>
<tbody>{trades_html}</tbody>
</table></div>

<div style="text-align:center;color:#555;margin-top:30px;padding:15px;font-size:12px">
<p>v2.0: 板块优先选股 + 每日信号灵活进出 | 止损-8% 止盈+20% 最长持有25天</p>
<p>v1.5: 5策略加权月度等权TOP10 | 对比参考</p>
</div></div>

<script>
new Chart(document.getElementById('chart1'),{{
    type:'line',data:{{
        labels:{dates_json},
        datasets:[
            {{label:'v2.0',data:{values_json},borderColor:'#00d4ff',fill:true,backgroundColor:'rgba(0,212,255,0.1)',tension:0.3,pointRadius:2}},
            {{label:'基准100k',data:{json.dumps([100000]*len(daily))},borderColor:'#555',borderDash:[5,5],pointRadius:0,fill:false}}
        ]
    }},options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#aaa'}}}}}},scales:{{x:{{ticks:{{color:'#888',maxTicksLimit:12}}}},y:{{ticks:{{color:'#888'}}}}}}}}
}});
new Chart(document.getElementById('chart2'),{{
    type:'line',data:{{
        labels:{v1_dates},
        datasets:[
            {{label:'v1.5',data:{v1_values},borderColor:'#f39c12',fill:true,backgroundColor:'rgba(243,156,18,0.1)',tension:0.3,pointRadius:3}},
            {{label:'基准100k',data:{json.dumps([100000]*max(len(v1_daily),1))},borderColor:'#555',borderDash:[5,5],pointRadius:0,fill:false}}
        ]
    }},options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#aaa'}}}}}},scales:{{x:{{ticks:{{color:'#888'}}}},y:{{ticks:{{color:'#888'}}}}}}}}
}});
new Chart(document.getElementById('chart3'),{{
    type:'bar',data:{{
        labels:{hold_labels},
        datasets:[{{label:'交易次数',data:{hold_values},backgroundColor:'#00d4ff'}}]
    }},options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#aaa'}}}}}},scales:{{x:{{ticks:{{color:'#888'}}}},y:{{ticks:{{color:'#888'}}}}}}}}
}});
</script></body></html>"""

    with open('v2/report.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"v2.0 报告已生成: v2/report.html")


START = '2025-04-01'
END = '2026-05-15'

if __name__ == '__main__':
    generate()
