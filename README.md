# BTC Quant
---

## Desc

- BTC 量化分析/交易 系统

## 系统架构设计：

1. 数据采集模块
    - 获取 BTC 实时和历史交易数据（价格、交易量等）。
    - 定期存储数据到 ClickHouse。
    - 数据来源：交易所 API（如 Binance、Coinbase 等）。
2. 策略制定模块
    - 使用 Python 编写策略逻辑。
    - 定义策略的指标计算、信号生成（如均线交叉、RSI 等）。
3. 回测模块
    - 使用 Backtrader 执行回测。
    - 从 ClickHouse 获取历史数据。
    - 输出策略的关键指标（如夏普比率、回撤等）。
4. 实盘交易模块
    - 对接交易所 API。
    - 将策略信号转换为真实订单。
    - 实时监控订单状态和账户余额。

## 各模块定义

|        |                     |                          |
|--------|---------------------|--------------------------|
| 中文模块名称 | 	英文模块名称             | 	说明                      |
| 数据采集模块 | 	data_collection    | 	负责采集 BTC 的实时和历史数据       |
| 数据存储   | 	data_collection/db | 	负责管理 ClickHouse 数据存储    |
| 策略制定模块 | 	strategy           | 	负责开发交易策略，包括指标和信号生成      |
| 交易模块   | 	trade              | 	包括回测交易和实盘交易             |
| 回测模块   | 	trade/backtesting  | 	使用 Backtrader 进行回测和策略优化 |
| 实盘交易模块 | 	trade/live_trading | 	对接交易所 API，实现实盘交易        |

## 各模块实现

1. 数据采集模块
    - 使用 ccxt 库连接交易所 API。
    - 数据存储格式与 ClickHouse 表一致。
    - 定时任务通过 schedule 或 Airflow 管理。
    - 示例代码

   ```python
   import ccxt
   import pandas as pd
   from clickhouse_driver import Client
   
   exchange = ccxt.binance()
   client = Client('localhost')
   
   def fetch_data():
   ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='1h', limit=1000)
   df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
   client.execute('INSERT INTO btc_data VALUES', df.to_dict('records'))
   ```

2. 策略制定模块
    - 结合 Pandas 或 TA-Lib 进行指标计算。
    - 定义信号生成规则。
    - 示意策略：

   ```python
   def sma_crossover(data):
       data['SMA_10'] = data['close'].rolling(window=10).mean()
       data['SMA_30'] = data['close'].rolling(window=30).mean()
       data['signal'] = (data['SMA_10'] > data['SMA_30']).astype(int)
       return data
   ```

3. 回测模块
    - 从 ClickHouse 加载数据。
    - 使用 Backtrader 进行回测并记录结果。
    - 示例代码:

   ```python
   import backtrader as bt
   
   class MyStrategy(bt.Strategy):
       def __init__(self):
           self.sma10 = bt.indicators.SimpleMovingAverage(self.data.close, period=10)
           self.sma30 = bt.indicators.SimpleMovingAverage(self.data.close, period=30)
   
       def next(self):
           if self.sma10 > self.sma30:
               self.buy()
           elif self.sma10 < self.sma30:
               self.sell()
   
   cerebro = bt.Cerebro()
   cerebro.addstrategy(MyStrategy)
   cerebro.run()
   ```

4. 实盘交易模块
    - 使用 ccxt 发送交易订单。
    - 实时监控账户状态和市场价格。

   ```python
   def place_order(symbol, side, amount):
       order = exchange.create_order(symbol=symbol, type='market', side=side, amount=amount)
       print(f"Order placed: {order}")
   
   def trade_signal(signal):
   if signal == 1:
   place_order('BTC/USDT', 'buy', 0.01)
   elif signal == -1:
   place_order('BTC/USDT', 'sell', 0.01)
   ````

## 技术选型

| 模块      | 技术/工具                 | 功能描述         |
|---------|-----------------------|--------------|
| 数据采集    | 	ccxt	                | 连接交易所API     |
| 数据存储    | 	ClickHouse	          | 高性能时序数据存储    |
| 策略制定与回测 | 	Backtrader	          | 支持指标、回测、性能评估 |
| 实盘交易    | 	ccxt	                | 支持多交易所实盘交易   |
| 定时任务    | 	schedule / Airflow	  | 定期采集数据、回测    |
| 可视化与报告  | 	Matplotlib / Plotly	 | 绘制回测结果、策略表现  |

## 策略

### MakerOnlyVolatilityStrategy只做Maker的做多波动率交易策略
- 策略名称：MakerOnlyVolatilityStrategy
- 核心概念：一种利用市场波动性的高频量化做市策略，通过在明确的支撑（底部）和阻力（顶部）之间进行深度交易，在多空两侧获利。策略通过小额、频繁的交易以及动态杠杆调整来优化收益。

#### 策略逻辑

1. 确定关键价位
    - 顶部（阻力）：
        - 只做多策略：取近期最高价的95%作为顶部。
        - 只做空策略（未来实现）：取近期最低价的105%作为顶部。
    - 底部（支撑）：
        - 只做多策略：取近期最高价的50%作为底部。
        - 只做空策略：取近期最低价的200%作为底部。
2. 交易逻辑
    - 方向性策略：
        - 只做多：
            - 当价格接近底部时逐步买入。
            - 当价格接近顶部时逐步卖出。
        - 只做空（未来实现）：
            - 当价格接近顶部时逐步卖出。
            - 当价格接近底部时逐步买入。
        - 双边交易（震荡行情）：
            - 在区间震荡的市场中，同时进行多空双向交易。
        - 订单分配：
            - 将资本均匀分布在顶部和底部之间。
            - 每个订单使用少量资金（例如，总资产的0.2%）。
                - 设置紧密的止损/止盈范围以实现频繁交易（例如，0.2%）。
        - 利润优化：
            - 在显著的趋势（如大涨或大跌）中被套牢的订单通过动态调整止盈水平获取更高利润：
                - 多单：逐步上移止盈价格，但不能超过顶部。
                - 空单：逐步下移止盈价格，但不能低于底部。
            - 避免在相同的止盈水平设置多个订单，以优化收益分布。
3. 杠杆管理
    - 动态杠杆调整：
        - 随着仓位接近顶部（空单）或底部（多单），逐步提高杠杆。
        - 根据清算线确定杠杆：
            - 多单以底部为清算线。
            - 空单以顶部为清算线。
        - 确保高效利用资金，同时控制风险。

4. 特殊场景处理
    - 平仓区间饱和：
        - 当止盈区间饱和（例如，每个止盈价都有挂单）时：
            - 以市价平掉最高价（或最低价）的单子，并重新分配其他挂单。
        - 意义：
            - 提高低杠杆订单的收益率。
            - 为底部波动提供足够的获利空间。
    - 资金不足：
        - 动态调整资金分配或暂停新挂单，直到部分仓位被平仓。
5. 风险管理
    - 仓位控制：
        - 每个订单保持一致的仓位大小，避免过度敞口。
    - 清算保护：
        - 仓位设置基于清算线，避免强制平仓。
    - 锁定收益：
        - 设置止盈点，即使在显著趋势中也能实现盈利。

#### 意见与建议

##### 潜在缺点

1. 流动性依赖：
    - 需要足够的市场流动性以填充频繁的小额订单，避免滑点过高。
2. 执行复杂性：
    - 动态调整止盈水平和杠杆可能增加策略的操作难度。
3. 资金占用：
    - 在长期趋势中，可能有部分订单无法平仓，需要额外资金支持继续操作。

#### 与现有策略的对比：

1. 相似策略：
    - 网格交易：类似于将资金分布在价格区间，但通常不考虑趋势或动态杠杆。
    - 均值回归策略：基于价格波动获利，但缺乏杠杆优化和饱和处理机制。
2. 差异点：
    - 本策略结合了网格交易和波动性捕捉，增加了动态杠杆和饱和处理机制，使其更灵活、更激进。

#### 建议：

1. 强化回测：
    - 在不同市场环境（牛市、熊市、震荡）中测试策略表现。
    - 模拟极端情况（例如闪崩）以验证风险控制能力。
2. 引入自动化：
    - 实现平仓区间饱和时的自动调整，以减少人工干预。
3. 增加止损机制：
    - 在意外趋势中设置全局止损水平，避免极端亏损。

#### 英文参考
<details>
    <summary>英文参考</summary>

#### **Strategy Name: MakerOnlyVolatilityStrategy**

#### **Core Concept**:
A high-frequency market-making strategy leveraging volatility. The strategy utilizes depth trading on both long and short sides, aiming to profit from price oscillations between defined support (bottom) and resistance (top) levels. The strategy optimizes returns through small, frequent trades and dynamic leverage adjustments.

---

### **Strategy Logic**

#### **1. Define Key Price Levels**
- **Top (Resistance)**:
    - For long-only strategies: 95% of the recent highest price.
    - For short-only strategies (future implementation): 105% of the recent lowest price.
- **Bottom (Support)**:
    - For long-only strategies: 50% of the recent highest price.
    - For short-only strategies: 200% of the recent lowest price.

#### **2. Trading Logic**
- **Directional Strategy**:
    - **Long-only**:
        - Gradually buy as price declines toward the bottom.
        - Gradually sell as price rises toward the top.
    - **Short-only** (future implementation):
        - Gradually sell as price rises toward the top.
        - Gradually buy as price declines toward the bottom.
    - **Dual-Sided (Mean Reversion)**:
        - Operates in a range-bound market with both long and short positions.

- **Order Allocation**:
    - Divide capital across the price range between top and bottom.
    - Each order uses a small fraction of total assets (e.g., 0.2% per order).
    - Stop-loss/profit-taking is set at a tight range for frequent trade execution (e.g., 0.2%).

- **Profit Optimization**:
    - Orders trapped in significant trends (e.g., large upward/downward moves) are managed for higher profit margins.
        - Adjust take-profit levels dynamically based on repetitive trades at similar price points:
            - **For Long Positions**: Shift take-profit prices upward, capped at the defined top.
            - **For Short Positions**: Shift take-profit prices downward, capped at the defined bottom.
    - Avoid multiple orders at the same take-profit level to optimize profit distribution.

#### **3. Leverage Management**
- **Dynamic Leverage Adjustment**:
    - Leverage increases as positions approach the top (for shorts) or bottom (for longs).
    - Determine leverage based on defined liquidation levels:
        - Long: Use bottom as the liquidation threshold.
        - Short: Use top as the liquidation threshold.
    - This ensures efficient capital usage while minimizing overexposure.

#### **4. Special Scenarios**
- **Saturated Profit Zones**:
    - When take-profit levels are saturated (e.g., all levels have active orders), execute the highest (lowest for shorts) position at market price and redistribute the remaining orders.
    - Rationale: This action enhances profitability of high-leverage orders near support/resistance zones.
- **Cash Shortage**:
    - Manage risk to avoid over-leveraging by dynamically reallocating capital or suspending new orders until positions are closed.

#### **5. Risk Management**
- **Position Size**:
    - Each order maintains a consistent size to avoid overexposure.
- **Liquidation Protection**:
    - Positions are calibrated to avoid forced liquidation through defined leverage and liquidation levels.
- **Profit Lock-In**:
    - Set profit-taking points to ensure realized profits even during significant market trends.

---

### **Comments and Suggestions**

#### **Strengths**:
1. **Volatility Exploitation**: The strategy is well-suited for high-volatility environments, such as cryptocurrency markets.
2. **Dynamic Adaptation**: Incorporates adjustments for market trends (uptrend, downtrend, range-bound).
3. **Risk Mitigation**: Leverage control tied to liquidation thresholds minimizes catastrophic losses.

#### **Potential Weaknesses**:
1. **Liquidity Dependency**:
    - Requires sufficient market liquidity to fill frequent small orders without excessive slippage.
2. **Execution Complexity**:
    - Continuous recalibration of profit levels and dynamic leverage adjustments can introduce operational challenges.
3. **Trapped Capital**:
    - Positions might remain unexecuted in extended trends, requiring additional capital or margin to continue operating effectively.

#### **Comparative Analysis with Existing Strategies**:
1. **Similar Strategies**:
    - Grid Trading: Similar in dividing capital across price ranges, but grid trading typically doesn’t adjust for trends or use dynamic leverage.
    - Mean Reversion: Shares concepts like profiting from oscillations but lacks the structured leverage and saturation handling of this strategy.
2. **Differentiation**:
    - Your strategy combines grid trading with volatility targeting and leverage optimization, making it more flexible and aggressive.

#### **Recommendations**:
1. **Enhance Backtesting**:
    - Test under different market conditions (bull, bear, range-bound).
    - Simulate extreme scenarios (e.g., flash crashes) to ensure robust risk management.
2. **Introduce Automation**:
    - Implement automated rebalancing for saturated zones to reduce manual interventions.
3. **Add Stop-Loss Mechanisms**:
    - Prevent extreme losses during unexpected trends by setting global stop-loss levels.

This strategy represents a sophisticated evolution of grid trading, optimized for the unique characteristics of cryptocurrency markets. Implementing and refining it through comprehensive backtesting and live validation is essential to ensure its practical efficacy.
</details>
## todolist

- 数据采集
    - 历史数据收集
        - [x] k线
    - 实时数据采集
        - [x] k线
        - [ ] 订单
        - [ ] 资金
    - 数据采集统一接口输出
- 数据存储
    - Clickhouse
        - [x] btc 1m k线 历史数据（回溯至2020.1.1）
    - memory
        - [ ] 订单
        - [ ] 资金
- 策略制定
    - [ ] only maker 做多波动率 中高频量化策略
      - [ ] 虚拟订单
      - [ ] 虚拟订单 -> 实际订单 映射
        - [ ] 虚拟订单变化时 实际订单需要相应发生变化
- 回测
    - 回测系统开发
        - [ ] 订单管理
        - [ ] 资金管理（保证金与清算逻辑）
        - [ ] 订单成交逻辑（根据k线与挂单进行计算）
- 实盘
    - [ ] 交易所订单API
    - [ ] 订单同步（防止实际挂单与策略预期的挂单不一致）