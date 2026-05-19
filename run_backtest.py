"""
回测运行脚本 - 批量运行所有策略并对比结果
用法: python run_backtest.py [策略名]
"""
import subprocess
import pickle
import sys
import os

STRATEGIES = {
    'demo': {
        'file': 'strategies/demo_strategy.py',
        'desc': '双均线交叉',
    },
    'macd': {
        'file': 'strategies/macd_strategy.py',
        'desc': 'MACD金叉死叉',
    },
    'rsi': {
        'file': 'strategies/rsi_strategy.py',
        'desc': 'RSI超买超卖',
    },
    'boll': {
        'file': 'strategies/boll_strategy.py',
        'desc': '布林带突破',
    },
    'momentum': {
        'file': 'strategies/momentum_rotation.py',
        'desc': '多股票动量轮动',
    },
}

BUNDLE_PATH = r"C:\Users\Jptr\.rqalpha\bundle"
START_DATE = '20240101'
END_DATE = '20250501'
INIT_CASH = '100000'


def run_backtest(name, info):
    """运行单个策略回测"""
    output_file = f'logs/{name}_result.pkl'
    cmd = [
        'rqalpha', 'run',
        '-f', info['file'],
        '-s', START_DATE,
        '-e', END_DATE,
        '-a', 'stock', INIT_CASH,
        '-d', BUNDLE_PATH,
        '-o', output_file,
        '-mt', 'current_bar',
        '-bm', '000300.XSHG',
    ]
    print(f"\n{'='*50}")
    print(f"运行策略: {name} - {info['desc']}")
    print(f"{'='*50}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[FAIL] {name}: 回测异常")
        if result.stderr:
            print(result.stderr[-500:])
        return None

    print(f"[OK] {name}: 回测完成")
    return output_file


def print_result(name, info, pkl_path):
    """打印单个策略结果"""
    if not os.path.exists(pkl_path):
        return None
    with open(pkl_path, 'rb') as f:
        result = pickle.load(f)
    s = result.get('summary', {})
    return {
        '策略': f"{name} ({info['desc']})",
        '总收益': f"{s.get('total_returns', 0) * 100:.2f}%",
        '年化收益': f"{s.get('annualized_returns', 0) * 100:.2f}%",
        '最大回撤': f"{s.get('max_drawdown', 0) * 100:.2f}%",
        '夏普比率': f"{s.get('sharpe', 0):.4f}",
        '胜率': f"{s.get('win_rate', 0) * 100:.2f}%",
    }


if __name__ == '__main__':
    os.makedirs('logs', exist_ok=True)

    # 确定要运行的策略
    if len(sys.argv) > 1:
        names = [sys.argv[1]]
    else:
        names = list(STRATEGIES.keys())

    # 运行回测
    results = []
    for name in names:
        if name not in STRATEGIES:
            print(f"未知策略: {name}，可选: {', '.join(STRATEGIES.keys())}")
            continue
        info = STRATEGIES[name]
        pkl = run_backtest(name, info)
        if pkl:
            row = print_result(name, info, pkl)
            if row:
                results.append(row)

    # 汇总对比
    if results:
        print(f"\n{'='*70}")
        print("策略对比汇总")
        print(f"{'='*70}")
        # 打印表头
        keys = list(results[0].keys())
        header = '  '.join(f'{k:>12}' for k in keys)
        print(header)
        print('-' * len(header))
        for row in results:
            line = '  '.join(f'{row[k]:>12}' for k in keys)
            print(line)
        print(f"\n基准(沪深300): 年化 +7.71%")
