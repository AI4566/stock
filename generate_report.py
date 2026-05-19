"""
生成HTML对比报告
对比我的选股 vs 实际起飞的股票
"""
import json
import os

def load_data():
    with open('logs/backtest_results.json', 'r', encoding='utf-8') as f:
        backtest = json.load(f)
    with open('logs/actual_top_stocks.json', 'r', encoding='utf-8') as f:
        actual = json.load(f)
    return backtest, actual


def generate_html(backtest, actual):
    # 准备图表数据
    months = [r['month'] for r in backtest]
    portfolio_values = [r['portfolio_value'] for r in backtest]
    monthly_returns = [r['avg_return'] for r in backtest]

    # 插入初始月
    months.insert(0, '2025-03')
    portfolio_values.insert(0, 100000)
    monthly_returns.insert(0, 0)

    # 生成每月选股表格
    monthly_picks_html = ""
    for r in backtest:
        month = r['month']
        stocks_html = ""
        for s in r.get('stocks', []):
            color = "#e74c3c" if s['return'] < 0 else "#27ae60"
            stocks_html += f"""
            <tr>
                <td>{s['stock']}</td>
                <td>{s['score']}</td>
                <td>{s['buy_price']}</td>
                <td>{s['sell_price']}</td>
                <td style="color:{color};font-weight:bold">{s['return']:+.2f}%</td>
            </tr>"""

        ret_color = "#e74c3c" if r['avg_return'] < 0 else "#27ae60"
        monthly_picks_html += f"""
        <div class="month-card">
            <h3>{month} <span style="color:{ret_color}">月收益: {r['avg_return']:+.2f}%</span>
                <span style="font-size:14px;color:#666"> | 组合市值: {r['portfolio_value']:,.0f} | 累计: {r['total_return']:+.2f}%</span>
            </h3>
            <table class="stock-table">
                <thead><tr><th>股票代码</th><th>综合得分</th><th>买入价</th><th>卖出价</th><th>月收益</th></tr></thead>
                <tbody>{stocks_html}</tbody>
            </table>
        </div>"""

    # 生成实际TOP10对比
    comparison_html = ""
    for r in backtest:
        month = r['month']
        my_stocks = {s['stock'] for s in r.get('stocks', [])}
        my_avg = r['avg_return']

        actual_top = actual.get(month, [])
        actual_html = ""
        for i, a in enumerate(actual_top[:10]):
            hit = "  " if a['stock'] in my_stocks else ""
            ret_color = "#e74c3c" if a['return'] < 0 else "#27ae60"
            actual_html += f"""
            <tr>
                <td>#{i+1}</td>
                <td>{a['stock']} {hit}</td>
                <td>{a['buy_price']:.2f}</td>
                <td>{a['sell_price']:.2f}</td>
                <td style="color:{ret_color};font-weight:bold">{a['return']*100:+.2f}%</td>
            </tr>"""

        # 检查是否有重合
        overlap = my_stocks & {a['stock'] for a in actual_top[:10]}
        overlap_text = f"命中{len(overlap)}只: {', '.join(overlap)}" if overlap else "未命中TOP10"

        ret_color = "#e74c3c" if my_avg < 0 else "#27ae60"
        comparison_html += f"""
        <div class="month-card">
            <h3>{month} 对比
                <span style="color:{ret_color}">我的月均: {my_avg:+.2f}%</span>
                <span style="color:#3498db"> | {overlap_text}</span>
            </h3>
            <table class="stock-table">
                <thead><tr><th>排名</th><th>实际最强股票</th><th>月初价</th><th>月末价</th><th>实际涨幅</th></tr></thead>
                <tbody>{actual_html}</tbody>
            </table>
        </div>"""

    # 最终统计数据
    final_value = backtest[-1]['portfolio_value']
    total_return = backtest[-1]['total_return']
    win_months = sum(1 for r in backtest if r['avg_return'] > 0)
    lose_months = len(backtest) - win_months
    best_month = max(backtest, key=lambda x: x['avg_return'])
    worst_month = min(backtest, key=lambda x: x['avg_return'])

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>A股量化投资回测报告 | 2025.04 ~ 2026.05</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, 'Microsoft YaHei', sans-serif; background: #0a0a1a; color: #e0e0e0; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
h1 {{ text-align: center; color: #00d4ff; font-size: 28px; margin: 20px 0; }}
h2 {{ color: #00d4ff; border-bottom: 2px solid #1a3a5c; padding-bottom: 10px; margin: 30px 0 15px; }}
h3 {{ color: #b0b0b0; margin-bottom: 10px; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
.stat-card {{ background: #111128; border: 1px solid #1a3a5c; border-radius: 10px; padding: 20px; text-align: center; }}
.stat-card .value {{ font-size: 28px; font-weight: bold; }}
.stat-card .label {{ color: #888; font-size: 14px; margin-top: 5px; }}
.positive {{ color: #27ae60; }}
.negative {{ color: #e74c3c; }}
.chart-container {{ background: #111128; border: 1px solid #1a3a5c; border-radius: 10px; padding: 20px; margin: 20px 0; }}
.month-card {{ background: #111128; border: 1px solid #1a3a5c; border-radius: 10px; padding: 15px; margin: 15px 0; }}
.stock-table {{ width: 100%; border-collapse: collapse; }}
.stock-table th {{ background: #1a2a4a; padding: 10px; text-align: left; color: #00d4ff; }}
.stock-table td {{ padding: 8px 10px; border-bottom: 1px solid #1a2a3a; }}
.stock-table tr:hover {{ background: #1a2a3a; }}
.tab {{ display: flex; gap: 10px; margin: 20px 0; }}
.tab button {{ padding: 10px 20px; background: #1a2a4a; color: #00d4ff; border: 1px solid #1a3a5c; border-radius: 5px; cursor: pointer; }}
.tab button.active {{ background: #00d4ff; color: #0a0a1a; }}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}
.footer {{ text-align: center; color: #555; margin-top: 40px; padding: 20px; font-size: 12px; }}
</style>
</head>
<body>
<div class="container">
    <h1>A股量化投资回测报告</h1>
    <p style="text-align:center;color:#888">回测区间: 2025年4月 ~ 2026年5月 | 初始资金: 100,000元 | 5策略加权选股</p>

    <div class="summary">
        <div class="stat-card">
            <div class="value {'positive' if total_return >= 0 else 'negative'}">{total_return:+.2f}%</div>
            <div class="label">总收益率</div>
        </div>
        <div class="stat-card">
            <div class="value">{final_value:,.0f}</div>
            <div class="label">最终市值(元)</div>
        </div>
        <div class="stat-card">
            <div class="value positive">{win_months}</div>
            <div class="label">盈利月份</div>
        </div>
        <div class="stat-card">
            <div class="value negative">{lose_months}</div>
            <div class="label">亏损月份</div>
        </div>
        <div class="stat-card">
            <div class="value positive">{best_month['avg_return']:+.2f}%</div>
            <div class="label">最佳月份 ({best_month['month']})</div>
        </div>
        <div class="stat-card">
            <div class="value negative">{worst_month['avg_return']:+.2f}%</div>
            <div class="label">最差月份 ({worst_month['month']})</div>
        </div>
    </div>

    <h2>组合市值走势</h2>
    <div class="chart-container">
        <canvas id="portfolioChart" height="100"></canvas>
    </div>

    <h2>月度收益分布</h2>
    <div class="chart-container">
        <canvas id="returnsChart" height="80"></canvas>
    </div>

    <div class="tab">
        <button class="active" onclick="showTab('picks')">我的每月选股</button>
        <button onclick="showTab('compare')">vs 实际TOP10</button>
    </div>

    <div id="picks" class="tab-content active">
        <h2>我的每月选股及盈亏</h2>
        {monthly_picks_html}
    </div>

    <div id="compare" class="tab-content">
        <h2>我的选择 vs 实际起飞股票</h2>
        <p style="color:#888;margin-bottom:15px">  表示我的组合中包含该股票。每月实际涨幅TOP10与我的选股对比。</p>
        {comparison_html}
    </div>

    <div class="footer">
        <p>数据来源: rqalpha bundle (5065只股票) | 策略: MACD+RSI+布林带+均线+动量 加权评分</p>
        <p>选股逻辑: 每月末用历史数据评分，下月初等权买入TOP10，月末结算 | 手续费: 0.15%</p>
        <p>免责声明: 本回测仅供参考，不构成投资建议</p>
    </div>
</div>

<script>
// 组合市值走势图
new Chart(document.getElementById('portfolioChart'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(months)},
        datasets: [{{
            label: '组合市值',
            data: {json.dumps(portfolio_values)},
            borderColor: '#00d4ff',
            backgroundColor: 'rgba(0,212,255,0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 4,
        }}, {{
            label: '基准 (100,000)',
            data: {json.dumps([100000] * len(months))},
            borderColor: '#555',
            borderDash: [5, 5],
            pointRadius: 0,
            fill: false,
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ labels: {{ color: '#aaa' }} }} }},
        scales: {{
            x: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#1a2a3a' }} }},
            y: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#1a2a3a' }} }}
        }}
    }}
}});

// 月度收益柱状图
new Chart(document.getElementById('returnsChart'), {{
    type: 'bar',
    data: {{
        labels: {json.dumps(months[1:])},
        datasets: [{{
            label: '月收益率(%)',
            data: {json.dumps(monthly_returns[1:])},
            backgroundColor: {json.dumps(['#27ae60' if r >= 0 else '#e74c3c' for r in monthly_returns[1:]])},
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ labels: {{ color: '#aaa' }} }} }},
        scales: {{
            x: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#1a2a3a' }} }},
            y: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#1a2a3a' }} }}
        }}
    }}
}});

function showTab(name) {{
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab button').forEach(el => el.classList.remove('active'));
    document.getElementById(name).classList.add('active');
    event.target.classList.add('active');
}}
</script>
</body>
</html>"""

    return html


if __name__ == '__main__':
    backtest, actual = load_data()
    html = generate_html(backtest, actual)
    with open('report.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"报告已生成: report.html ({len(html):,} bytes)")
