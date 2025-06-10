import plotly.graph_objects as go
import numpy as np

# 生成网格数据
x = np.linspace(-5, 5, 100)
y = np.linspace(-5, 5, 100)
x, y = np.meshgrid(x, y)
z = np.sin(np.sqrt(x**2 + y**2))

# 创建三维曲面图
fig = go.Figure(data=[go.Surface(z=z, x=x, y=y)])

# 设置布局
fig.update_layout(title='3D Surface Plot',
                  scene=dict(xaxis_title='X Axis',
                             yaxis_title='Y Axis',
                             zaxis_title='Z Axis'),
                  autosize=False, width=800, height=800)

# 显示图形
fig.show()
