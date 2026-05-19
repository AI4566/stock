# 项目开发日志

## 2026-05-18 项目初始化

### 完成事项
1. **GitHub 仓库创建**：https://github.com/AI4566/stock
2. **安装 GitHub CLI**：gh v2.92.0
3. **项目依赖安装**：
   - akshare 1.18.62 — A股历史/实时数据接口
   - Ashare (GitHub 克隆) — 新浪/腾讯双源行情数据
   - rqalpha 6.1.4 — 量化回测框架
   - 解决了 numpy 1.x/2.x 兼容问题，统一升级到 numpy 2.4.6
4. **项目目录结构搭建**：
   ```
   stock/
   ├── main.py              # 项目入口（fetch/backtest/realtime）
   ├── requirements.txt     # 依赖列表
   ├── config/
   │   └── rqalpha_config.yml  # rqalpha 回测配置
   ├── data/
   │   └── fetcher.py       # 统一数据获取接口（akshare + Ashare）
   ├── strategies/
   │   └── demo_strategy.py # 示例策略：双均线交叉
   ├── vendor/
   │   └── Ashare/          # Ashare 源码
   └── logs/                # 回测输出
   ```
5. **数据获取验证**：
   - Ashare：获取上证指数5日行情 ✅
   - akshare：获取贵州茅台日线数据 ✅

### 待办
- [ ] 测试 rqalpha 回测运行
- [ ] 添加更多策略模板
- [ ] 添加数据存储模块

---

## 2026-05-18 (续) 数据源优化

### 改进
1. **fetcher.py 增加网络重试**：akshare 请求失败时自动重试3次，间隔2秒
2. **新增 `auto` 模式**：`get_stock_data(code, source='auto')` 先尝试 akshare，失败自动降级到 Ashare
3. **main.py 使用 auto 模式**：默认走自动降级策略

### 验证结果
- akshare：贵州茅台 242 条日线 ✅（偶有网络抖动，重试后成功）
- Ashare：上证指数 10 日行情 ✅
- `python main.py fetch` 运行正常 ✅

---

## 2026-05-19 rqalpha 回测 + 多策略

### rqalpha 环境修复
- 下载 rqalpha 数据包（bundle 202605）
- 修补 pandas 3.x 兼容问题：
  - `mode.use_inf_as_na` → `replace([inf], nan).fillna(0)`
  - DatetimeIndex 整数索引 → `arr.values` 转 numpy 数组

### 新增策略（共5个）
| 策略 | 文件 | 逻辑 |
|------|------|------|
| demo | demo_strategy.py | 双均线交叉（5/20日） |
| MACD | macd_strategy.py | DIF上穿DEA买入，下穿卖出 |
| RSI | rsi_strategy.py | RSI<30买入，>70卖出 |
| 布林带 | boll_strategy.py | 跌破下轨买入，突破上轨卖出 |
| 动量轮动 | momentum_rotation.py | 5只股票中选20日涨幅最高持有 |

### 回测结果（2024.01 ~ 2025.05，初始10万）
| 策略 | 总收益 | 年化 | 最大回撤 | 夏普 | 胜率 |
|------|--------|------|---------|------|------|
| demo | -2.00% | -1.58% | 13.46% | -0.14 | 22.19% |
| MACD | +21.41% | +16.51% | 7.74% | 0.92 | 18.75% |
| RSI | +14.66% | +11.37% | 9.68% | 0.69 | 19.69% |
| 布林带 | +29.20% | +22.35% | 5.80% | 2.21 | 17.19% |
| 动量轮动 | +5.01% | +3.92% | 23.49% | 0.20 | 41.88% |
| *基准* | *+9.89%* | *+7.71%* | | | |

### 新增工具
- `run_backtest.py`：批量回测+策略对比脚本

### 待办
- [ ] 添加数据存储模块（本地缓存）
- [ ] 优化策略参数（可配置化）
- [ ] 添加实时监控模块
