# import
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# config
FILE_PATH = 'C:/Users/Gx/Documents/Work/Quant/multi_pair_backtest_rs/data/back_trade/20250422_150235.csv'
STRATEGY_NAME = 'Mk1'

# visualization
# -------------------------------
# 1. 加载数据
# 假设CSV文件 'btc_prices.csv' 中包含 Date 和 Close 两列
df = pd.read_csv(FILE_PATH, parse_dates=['time'], index_col='time')
df = df.sort_index()  # 确保按日期排序

# 将日期转换为数值（天数）用于回归分析
df['time'] = np.arange(len(df))

x_time = df['time']
y_prince = df['price_btc_usdt']  # 币价
y_total_usdt = df['total_usdt']  # 总资产量
y_actual_position_ratio = df['actual_position_ratio']  # 实际仓位占比
# 一号对冲基金（注：对冲基金使用50%资产做多波动率 使用50%资产进行1倍做空现货 实现对冲（无法做到完全动态对冲））
y_hedge_fund1 = y_total_usdt / 2 + y_total_usdt[0] - y_prince / y_prince[0] * y_total_usdt[0] / 2  # 一号对冲基金资产量
# print(y_hedge_fund1)
# 二号对冲基金（完全动态对冲）
y_prince_changes = y_prince.pct_change().fillna(0)
y_total_usdt_changes = y_total_usdt.pct_change().fillna(0)
y_hedge_fund2_combined_returns = 0.5 * y_prince_changes - 0.5 * y_total_usdt_changes
y_hedge_fund2 = y_total_usdt[0] * (1 + y_hedge_fund2_combined_returns).cumprod()

# 计算资产收益率
asset_return_rate = (y_total_usdt[-1] - y_total_usdt[0]) / y_total_usdt[0]
print("资产收益率:", asset_return_rate * 100, "%")

# 计算比特币现货收益率
btc_return_rate = (y_prince[-1] - y_prince[0]) / y_prince[0]
print("比特币收益率:", btc_return_rate * 100, "%")

# 计算差值收益率
diff_btc_return_rate = asset_return_rate - btc_return_rate
print("差值收益率:", diff_btc_return_rate * 100, "%")

# 计算对冲收益率
hedge1_return_rate = (y_hedge_fund1[-1] - y_hedge_fund1[0]) / y_hedge_fund1[0]
print("一号对冲基金收益率:", hedge1_return_rate * 100, "%")
hedge2_return_rate = (y_hedge_fund2[-1] - y_hedge_fund2[0]) / y_hedge_fund2[0]
print("一号对冲基金收益率:", hedge2_return_rate * 100, "%")

# 计算资产预期年化收益率
expected_asset_annualized_return_rate = (y_total_usdt[-1] / y_total_usdt[0]) ** (365 / len(x_time) * 1440) - 1
print("资产年化收益率:", expected_asset_annualized_return_rate * 100, "%")

# 计算现货预期年化收益率
expected_btc_annualized_return_rate = (y_prince[-1] / y_prince[0]) ** (365 / len(x_time) * 1440) - 1
print("现货年化收益率:", expected_btc_annualized_return_rate * 100, "%")

# 计算差值预期年化收益率
expected_diff_annualized_return_rate = (1 + diff_btc_return_rate) ** (365 / len(x_time) * 1440) - 1
print("差值年化收益率:", expected_diff_annualized_return_rate * 100, "%")

# 计算对冲年化收益率
expected_hedge1_annualized_return_rate = (1 + hedge1_return_rate) ** (365 / len(x_time) * 1440) - 1
print("一号对冲基金年化收益率:", expected_hedge1_annualized_return_rate / 2 * 100, "%")
expected_hedge2_annualized_return_rate = (1 + hedge2_return_rate) ** (365 / len(x_time) * 1440) - 1
print("二号对冲基金年化收益率:", expected_hedge2_annualized_return_rate / 2 * 100, "%")

# 创建价格图表
fig = make_subplots()

# 添加实际价格曲线
fig.add_trace(go.Scatter(x=df.index, y=y_prince, mode='lines', name='比特币价格', yaxis="y"))
# 添加总资产曲线
fig.add_trace(go.Scatter(x=df.index, y=y_total_usdt, mode='lines', name='策略-' + STRATEGY_NAME, yaxis="y2"))
# 添加对冲收益曲线
fig.add_trace(go.Scatter(x=df.index, y=y_hedge_fund1, mode='lines', name='一号对冲基金', yaxis="y2"))
fig.add_trace(go.Scatter(x=df.index, y=y_hedge_fund2, mode='lines', name='二号对冲基金', yaxis="y2"))
# 添加仓位曲线
fig.add_trace(go.Scatter(x=df.index, y=y_actual_position_ratio, mode='lines', name='仓位', yaxis="y3"))

# 更新布局
fig.update_layout(
    title='量化策略-' + STRATEGY_NAME + '-回测结果',
    xaxis_title='日期',
    # yaxis_title='价格',
    # legend=dict(x=0, y=1)
    yaxis=dict(
        title=dict(
            text="比特币价格",
        ),
    ),
    yaxis2=dict(
        title=dict(
            text="资产价格",
        ),
        anchor="free",
        overlaying="y",
        side="right",
        position=0.9
    ),
    yaxis3=dict(
        title=dict(
            text="仓位",
        ),
        anchor="free",
        overlaying="y",
        side="right",
        position=1.0,
        tickformat=".0%",  # 设置为整数百分比
    )
)

# 显示图表
fig.show()