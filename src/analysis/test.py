"""
提高局部最高值的拟合权重
"""
# 导入包和数据
import math

import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from lmfit import Model
from scipy.signal import find_peaks

# -------------------------------
# 1. 加载数据
# 假设CSV文件 'btc_prices.csv' 中包含 Date 和 Close 两列
df = pd.read_csv('btc_prices.csv', parse_dates=['open_date'], index_col='open_date')
df = df.sort_index()  # 确保按日期排序

# 将日期转换为数值（天数）用于回归分析
df['Time'] = np.arange(len(df))

x_data = df['Time']
y_data = df['open_price']
y_data_log = np.log(df['open_price'])

# 模型和参数
def fn_m(x, l:float, k:float, x0:float, c:float):
    return l*((x+x0)**k) + c

def fn_a(x, a:float):
    return a

def fn_s(x, x2: float, t:float):
    return np.sin(x/t + x2)

def fn_price(x, a:float, c:float, l:float, k:float, x0:float, x2:float, t:float):
    return fn_m(x, l, k, x0, c) * ( 1 + fn_a(x, a) * fn_s(x, x2, t))

def fn_log_price(x, a:float, c:float, l:float, k:float, x0:float, x2:float, t:float):
    prices = fn_price(x, a, c, l, k, x0, x2, t)
    # 将小于0的值都置为一个非常小的正数
    prices[prices < 0] = 1e-9
    return np.log(prices)

# 手动提供的参数
INIT_A = 0.8
INIT_C = 1
INIT_L = 600
INIT_K = 0.58
INIT_X0 = 1
# INIT_X1 = 600
INIT_X2 = math.pi * 0.7
INIT_T = 1400/math.pi/2

# # 回归获得的参数
# INIT_A = 5.68868564
# INIT_C = 291.096217
# INIT_L = 18.5985387
# INIT_K = 0.99999000
# INIT_X0 = 11.8565495
# INIT_X1 = 6.24777991
# INIT_X2 = 1.21494460
# INIT_T = 208.538659


# 创建 lmfit 模型
model = Model(fn_price)
model_log = Model(fn_log_price)

# 根据先验知识给出初始猜测，若无先验则可均设为1
# params = model.make_params(a=INIT_A, c=INIT_C, l=INIT_L, k=INIT_K, x0=INIT_X0, x2=INIT_X2, t=INIT_T)
params = model_log.make_params(a=INIT_A, c=INIT_C, l=INIT_L, k=INIT_K, x0=INIT_X0, x2=INIT_X2, t=INIT_T)

# 如果有参数边界、固定值或者其他约束，可使用：
params['a'].set(min=0+1e-9, max=1-1e-9) # a>0
params['c'].set(min=0+1e-9) # c>0
params['l'].set(min=0+1e-9) # L>0
params['k'].set(min=0+1e-9, max=1-1e-9) # 0<k<1
params['x0'].set(min=0+1e-9) # x0>0
params['x2'].set(min=0, max=2*math.pi) # 0<=x2<=2pi
params['t'].set(min=0) # T>0


# 准备数据
true_params = [INIT_A, INIT_C, INIT_L, INIT_K, INIT_X0, INIT_X2, INIT_T]
y_true = fn_price(x_data, *true_params) # 初始参数曲线
y_true_log = fn_log_price(x_data, *true_params) # 初始参数log曲线
y_true_m = fn_m(x_data, l=INIT_L, k=INIT_K, x0=INIT_X0, c=INIT_C) # 均值曲线

# 初始拟合
result = model_log.fit(y_data_log, params, x=x_data, method='trust-constr')

# 计算初次拟合的残差
residuals = np.abs(y_data_log - result.best_fit)

# 为极大值/极小值赋予更高的权重
distance = 300
# 找出Price的局部极大值
peaks, _ = find_peaks(y_data, distance=distance)
# 找出局部极小值（取负后找峰）
valleys, _ = find_peaks(-y_data, distance=distance)
# 合并所有极值点
extrema = np.concatenate([peaks, valleys])  # 合并所有极值点

# 构造权重数组，初始全为1
weights = np.ones_like(y_data)
# 对局部极大值和极小值位置赋予更高的权重
weights[extrema] = 1 + distance * residuals[extrema] / np.max(residuals)  # 根据残差调整权重

# 二次拟合 加入权重
result = model_log.fit(y_data_log, params, x=x_data, weights=weights, method='trust-constr')
y_regression_fit = np.exp(result.best_fit)

# 输出拟合报告
print(result.fit_report())

# 最终参数
params = result.best_values

#
y_regression_fit_m = fn_m(x_data, l=params['l'], k=params['k'], x0=params['x0'], c=params['c'])
y_regression_fit_m_log = np.log(y_regression_fit_m)

# 创建log图表
fig = make_subplots()

# 添加log价格曲线
fig.add_trace(go.Scatter(x=df.index, y=y_data_log, mode='lines', name='比特币log价格'))

# 添加初始参数拟合曲线
fig.add_trace(go.Scatter(x=df.index, y=y_true_log, mode='lines', name='初始参数log拟合曲线'))

# 添加初始参数均值曲线
fig.add_trace(go.Scatter(x=df.index, y=np.log(y_true_m), mode='lines', name='初始参数log均值曲线'))

# 添加拟合价格曲线
fig.add_trace(go.Scatter(x=df.index, y=result.best_fit, mode='lines', name='拟合log价格'))

# 添加拟合log均值曲线
fig.add_trace(go.Scatter(x=df.index, y=y_regression_fit_m_log, mode='lines', name='拟合log均值曲线'))

# 添加局部最高值
fig.add_trace(
    go.Scatter(
        x=df.index[peaks],
        y=y_data_log[peaks],
        mode='markers',
        marker=dict(color='red', size=3),
        name='局部最高值'
    )
)
# 添加局部最低值
fig.add_trace(
    go.Scatter(
        x=df.index[valleys],
        y=y_data_log[valleys],
        mode='markers',
        marker=dict(color='blue', size=3),
        textposition='bottom center',
        name='局部最低值'
    )
)

# 更新布局
fig.update_layout(
    title='比特币拟合log价格',
    xaxis_title='日期',
    yaxis_title='价格',
    legend=dict(x=0, y=1)
)

# 显示图表
fig.show()

# 创建价格图表
fig = make_subplots()

# 添加实际价格曲线
fig.add_trace(go.Scatter(x=df.index, y=y_data, mode='lines', name='比特币价格'))

# 添加初始参数拟合曲线
fig.add_trace(go.Scatter(x=df.index, y=y_true, mode='lines', name='初始参数拟合曲线'))

# 添加初始参数均值曲线
fig.add_trace(go.Scatter(x=df.index, y=y_true_m, mode='lines', name='初始参数均值曲线'))

# 添加拟合价格曲线
fig.add_trace(go.Scatter(x=df.index, y=y_regression_fit, mode='lines', name='拟合价格'))

# 添加拟合log均值曲线
fig.add_trace(go.Scatter(x=df.index, y=y_regression_fit_m, mode='lines', name='拟合均值曲线'))

# 添加局部最高值
fig.add_trace(
    go.Scatter(
        x=df.index[peaks],
        y=y_data[peaks],
        mode='markers',
        marker=dict(color='red', size=3),
        name='局部最高值'
    )
)
# 添加局部最低值
fig.add_trace(
    go.Scatter(
        x=df.index[valleys],
        y=y_data[valleys],
        mode='markers',
        marker=dict(color='blue', size=3),
        name='局部最低值'
    )
)

# 更新布局
fig.update_layout(
    title='比特币拟合价格',
    xaxis_title='日期',
    yaxis_title='价格',
    legend=dict(x=0, y=1)
)

# 显示图表
fig.show()
