"""
v2.0 板块分类系统
基于股票代码和行业信息对5000+只股票进行板块分类
"""
import os
import json
import h5py
import numpy as np
import pandas as pd
from collections import defaultdict

BUNDLE_PATH = r"C:\Users\Jptr\.rqalpha\bundle"


def load_instruments():
    """加载股票基本信息"""
    import pickle
    with open(os.path.join(BUNDLE_PATH, 'instruments.pk'), 'rb') as f:
        instruments = pickle.load(f)
    return instruments


def classify_by_code(stock_id):
    """按代码前缀分类（交易所/板块）"""
    code = stock_id.split('.')[0]
    exchange = stock_id.split('.')[1] if '.' in stock_id else 'UNKNOWN'

    if exchange == 'XSHG':
        if code.startswith('688'):
            return '科创板'
        elif code.startswith('600') or code.startswith('601') or code.startswith('603'):
            return '沪市主板'
        elif code.startswith('605'):
            return '沪市主板'
    elif exchange == 'XSHE':
        if code.startswith('300'):
            return '创业板'
        elif code.startswith('002'):
            return '中小板'
        elif code.startswith('000'):
            return '深市主板'
        elif code.startswith('001') or code.startswith('003'):
            return '深市主板'
    return '其他'


def classify_by_industry(instruments):
    """根据行业信息分类"""
    industry_map = defaultdict(list)
    for inst in instruments:
        sid = inst.get('order_book_id', '')
        industry = inst.get('industry_code', '') or inst.get('industry_name', '') or ''
        if not industry:
            industry = classify_by_code(sid)
        industry_map[industry].append(sid)
    return dict(industry_map)


def build_sector_map():
    """构建完整的板块映射"""
    instruments = load_instruments()

    # 按交易所板块分类
    board_map = defaultdict(list)
    for inst in instruments:
        sid = inst.get('order_book_id', '')
        if not sid:
            continue
        board = classify_by_code(sid)
        board_map[board].append(sid)

    # 按行业分类（如果有行业信息）
    industry_map = classify_by_industry(instruments)

    # 合并：优先用行业分类，如果没有就用交易所板块
    sectors = {}

    # 交易所板块
    for board, stocks in board_map.items():
        sectors[f'[{board}]'] = stocks

    # 行业板块
    for industry, stocks in industry_map.items():
        if len(stocks) >= 10:  # 至少10只股票才算一个板块
            sectors[industry] = stocks

    return sectors


def get_stock_sector_map():
    """获取每只股票所属的所有板块"""
    sectors = build_sector_map()
    stock_sectors = defaultdict(list)
    for sector, stocks in sectors.items():
        for s in stocks:
            stock_sectors[s].append(sector)
    return dict(stock_sectors)


if __name__ == '__main__':
    print("构建板块映射...")
    sectors = build_sector_map()
    print(f"总板块数: {len(sectors)}")

    # 按板块大小排序
    sorted_sectors = sorted(sectors.items(), key=lambda x: len(x[1]), reverse=True)
    print("\n前20大板块:")
    for name, stocks in sorted_sectors[:20]:
        print(f"  {name}: {len(stocks)}只")

    # 保存
    os.makedirs('v2', exist_ok=True)
    with open('v2/sectors.json', 'w', encoding='utf-8') as f:
        json.dump(sectors, f, ensure_ascii=False)
    print(f"\n已保存到 v2/sectors.json")
