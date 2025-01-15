"""
使用plotly做可视化
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# 示例数据
data = {
    'Date': ['2023-12-22', '2023-12-23', '2023-12-24', '2023-12-25', '2023-12-26'],
    'Open': [100, 105, 102, 108, 110],
    'High': [106, 108, 109, 112, 115],
    'Low': [99, 102, 101, 107, 109],
    'Close': [105, 107, 108, 110, 114],
    'Volume': [1200, 1500, 1800, 2000, 1700]
}
df = pd.DataFrame(data)
df['Date'] = pd.to_datetime(df['Date'])

# 创建主图和副图
fig = make_subplots(
    rows=2,  # 两行布局
    cols=1,  # 一列布局
    shared_xaxes=True,  # 共享 X 轴
    row_heights=[0.7, 0.3],  # 主图 70%，副图 30%
    vertical_spacing=0.05,  # 主图和副图之间的间距
    subplot_titles=("k-line", "volume")
)

# 主图：绘制K线图
fig.add_trace(
    go.Candlestick(
        x=df['Date'],
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='K-Line'
    ),
    row=1, col=1
)

# 副图：绘制成交量柱状图
fig.add_trace(
go.Bar(
    x=df['Date'],
    y=df['Volume'],
    name='Volume',
    marker=dict(color='gray', opacity=0.7)
),
row = 2, col = 1
)

# 更新布局
fig.update_layout(
    title='K-Line Chart with Volume',
    xaxis = dict(title='Date'),
    # yaxis = dict(title='Price', row=1),
    # yaxis2 = dict(title='Volume', row=2),
    xaxis_rangeslider_visible = False,  # 隐藏 X 轴的范围滑块
    showlegend=False  # 隐藏图例
)

# 显示图表
fig.show()
