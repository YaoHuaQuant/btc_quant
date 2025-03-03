import numpy as np
import pandas as pd
import pywt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -------------------------------
# 1. 数据加载与预处理
# 假设CSV文件 'btc_prices.csv' 中包含日期(Date)和收盘价(Close)列
data = pd.read_csv('btc_prices.csv', parse_dates=['Date'], index_col='Date')
prices = data['Close']
# 对价格取对数，减少异方差性
log_prices = np.log(prices)

# -------------------------------
# 2. 离散小波变换（DWT）
# 使用 db4 小波，对数据进行4层分解
wavelet = 'db4'
level = 4
coeffs = pywt.wavedec(log_prices, wavelet, level=level)
# coeffs[0] 为近似系数；coeffs[1:] 为各层细节系数

# 使用 Plotly 创建多子图显示原始对数价格和各层细节系数
fig = make_subplots(rows=level+1, cols=1, shared_xaxes=True,
                    subplot_titles=["Log Bitcoin Price"] + [f"Detail Coefficient D{i}" for i in range(1, level+1)],
                    vertical_spacing=0.03)

# 第一行：原始对数价格
fig.add_trace(go.Scatter(x=log_prices.index, y=log_prices,
                         mode='lines', name='Log Price'), row=1, col=1)
fig.update_yaxes(title_text="Log Price", row=1, col=1)

# 后续行：各层细节系数
for i in range(1, level+1):
    n = len(coeffs[i])
    # 构造与原始数据起止时间一致的横坐标
    x_numeric = np.linspace(log_prices.index[0].value, log_prices.index[-1].value, n)
    x_dates = pd.to_datetime(x_numeric)
    fig.add_trace(go.Scatter(x=x_dates, y=coeffs[i],
                             mode='lines', name=f'Detail D{i}'), row=i+1, col=1)
    fig.update_yaxes(title_text=f'D{i}', row=i+1, col=1)

fig.update_layout(height=800, title_text="DWT Decomposition of Log Bitcoin Prices (Plotly)")
fig.show()

# -------------------------------
# 3. 连续小波变换（CWT）
# 设置尺度范围
scales = np.arange(1, 128)
cwtmatr, frequencies = pywt.cwt(log_prices, scales, wavelet)

# 使用 Plotly 绘制 CWT 时频图（热图）
fig2 = go.Figure(data=go.Heatmap(
    z=cwtmatr,
    x=log_prices.index,  # 时间轴为日期
    y=scales,
    colorscale='Jet',
    colorbar=dict(title='Coefficient Amplitude')
))
fig2.update_layout(
    title="Continuous Wavelet Transform (CWT) of Log Bitcoin Prices",
    xaxis_title="Date",
    yaxis_title="Scale",
    height=600
)
fig2.show()
