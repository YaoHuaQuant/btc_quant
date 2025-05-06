import pandas as pd
from IPython.display import display

# 创建示例数据
data = {'姓名': ['张三', '李四', '王五'], '年龄': [28, 34, 29]}
df = pd.DataFrame(data)

# 直接显示表格
display(df)