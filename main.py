"""
A股量化交易项目入口
用法：
  python main.py fetch          # 获取数据
  python main.py backtest       # 运行回测
  python main.py realtime       # 获取实时行情
"""
import sys


def cmd_fetch():
    """获取数据演示"""
    from data.fetcher import get_stock_data

    print(">>> 获取贵州茅台日线数据 (auto)")
    df = get_stock_data('600519', source='auto')
    print(df.tail(10))
    print(f"\n共 {len(df)} 条记录")

    print("\n>>> 获取上证指数日线数据 (Ashare)")
    df2 = get_stock_data('sh000001', source='ashare', count=10)
    print(df2)


def cmd_backtest():
    """运行回测"""
    import subprocess
    config_path = 'config/rqalpha_config.yml'
    strategy_path = 'strategies/demo_strategy.py'
    print(f">>> 运行 rqalpha 回测: {strategy_path}")
    subprocess.run([
        'rqalpha', 'run',
        '-f', strategy_path,
        '-c', config_path,
        '-o', 'logs/result.pkl',
    ])


def cmd_realtime():
    """获取实时行情"""
    from data.fetcher import fetch_akshare_realtime
    print(">>> 获取全市场实时行情")
    df = fetch_akshare_realtime()
    print(df.head(20).to_string())


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    commands = {
        'fetch': cmd_fetch,
        'backtest': cmd_backtest,
        'realtime': cmd_realtime,
    }

    cmd = sys.argv[1]
    if cmd in commands:
        commands[cmd]()
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)
