import plotly.graph_objects as go

# 创建图形对象
fig = go.Figure()

# 添加第一条折线，使用默认的 Y 轴（yaxis）
fig.add_trace(go.Scatter(
    x=[1, 2, 3],
    y=[10, 20, 30],
    name="数据 1",
    yaxis="y"
))

# 添加第二条折线，使用第二个 Y 轴（yaxis2）
fig.add_trace(go.Scatter(
    x=[1, 2, 3],
    y=[100, 200, 300],
    name="数据 2",
    yaxis="y2"
))

# 添加第三条折线，使用第三个 Y 轴（yaxis3）
fig.add_trace(go.Scatter(
    x=[1, 2, 3],
    y=[1000, 2000, 3000],
    name="数据 3",
    yaxis="y3"
))

# 更新布局，定义三个 Y 轴
fig.update_layout(
    title="具有三个 Y 轴的折线图",
    xaxis=dict(domain=[0.1, 0.9]),  # 设置 x 轴的显示范围

    yaxis=dict(
        title=dict(
            text="数据 1",
            font=dict(color="blue")
        ),
        tickfont=dict(color="blue")
    ),
    yaxis2=dict(
        title=dict(
            text="数据 2",
            font=dict(color="red")
        ),
        tickfont=dict(color="red"),
        anchor="free",
        overlaying="y",
        side="right",
        position=0.9
    ),
    yaxis3=dict(
        title=dict(
            text="数据 3",
            font=dict(color="green")
        ),
        tickfont=dict(color="green"),
        anchor="free",
        overlaying="y",
        side="right",
        position=1.0
    )
)

# 显示图形
fig.show()
