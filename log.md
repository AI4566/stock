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
