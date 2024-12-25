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
- 回测
  - 回测系统开发
    - [ ] 订单管理
    - [ ] 资金管理（保证金与清算逻辑）
    - [ ] 订单成交逻辑（根据k线与挂单进行计算）
- 实盘
  - [ ] 交易所订单API
  - [ ] 订单同步（防止实际挂单与策略预期的挂单不一致）