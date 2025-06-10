import pywt
import numpy as np
import pandas as pd
import plotly.graph_objects as go


# 获取比特币历史价格数据
FILE_PATH = 'C:/Users/Gx/Documents/Work/Quant/multi_pair_backtest_rs/data/back_trade/mk3/static_50.csv'
df = pd.read_csv(FILE_PATH, parse_dates=['time'], index_col='time')
df = df.sort_index()  # 确保按日期排序
df = df[0:10000] # TODO 数据裁剪
price = df['price_btc_usdt']  # 币价

# 绘制币价图像
# 创建价格图表
fig = go.Figure(data=[go.Scatter(x=df.index, y=price, mode='lines', name='比特币价格', yaxis="y")])
fig.show()

# 使用对称延拓方式进行信号扩展
pad_width = 512  # 根据需要调整填充宽度
data_padded = pywt.pad(price.values, (pad_width, pad_width), mode='symmetric')
# data_padded = pywt.pad(price.values, pad_width, mode='zero')
# data_padded = price.values # TODO 暂停裁剪

# 2. 进行连续小波变换（CWT）
scales = np.arange(1, 128)  # 选择尺度范围
coefficients, frequencies = pywt.cwt(data_padded, scales, 'cmor1.5-1.0', sampling_period=1)

# 3. 准备绘图数据
time_indices = np.arange(len(price))
X, Y = np.meshgrid(time_indices, frequencies)
Z = np.abs(coefficients)
# 去除扩展部分，恢复原始信号长度对应的能量数据
Z = Z[:, pad_width:-pad_width]

# 4. 使用 Plotly 创建交互式 3D 曲面图
fig = go.Figure(data=[go.Surface(x=X, y=Y, z=Z)])
fig.update_layout(
    title='比特币价格的连续小波变换 (CWT) 3D 图',
    scene=dict(
        xaxis_title='时间 (分钟索引)',
        yaxis_title='频率',
        zaxis_title='系数幅值',
        # yaxis=dict(type='log')  # 设置频率轴为对数坐标
    ),
    # width=800,
    # height=700
)
fig.show()

# 检测能量突变点（趋势变化点）
# 计算每个时间点的总能量
power = Z
time = df.index
total_energy = power.sum(axis=0)

# 计算能量变化率
energy_diff = np.diff(total_energy)

# 设置阈值（根据数据特点调整）
threshold = np.mean(np.abs(energy_diff)) + 2 * np.std(np.abs(energy_diff))

# 检测突变点
change_points = np.where(np.abs(energy_diff) > threshold)[0]

# 输出突变时间点
for idx in change_points:
    print(f"能量突变时间点：{time[idx]}")