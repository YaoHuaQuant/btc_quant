"""
使用傅里叶变换来分解比特币价格走势
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pandas_datareader import data as pdr
import datetime

# 获取比特币价格数据
start = datetime.datetime(2020, 1, 1)
end = datetime.datetime(2025, 2, 21)
btc_data = pdr.get_data_yahoo('BTC-USD', start, end)

# 取收盘价并去除缺失值
prices = btc_data['Close'].dropna()

# 绘制原始价格数据
plt.figure(figsize=(14, 7))
plt.plot(prices, label='Original Prices')
plt.title('Bitcoin Closing Prices')
plt.xlabel('Date')
plt.ylabel('Price (USD)')
plt.legend()
plt.show()

# 对价格数据进行傅里叶变换
fft_prices = np.fft.fft(prices)
fft_freq = np.fft.fftfreq(len(prices))

# 设计低通滤波器（截断高频部分）
cutoff_low = 0.01  # 截止频率（根据需要调整）
fft_low_pass = fft_prices.copy()
fft_low_pass[np.abs(fft_freq) > cutoff_low] = 0

# 设计高通滤波器（截断低频部分）
cutoff_high = 0.01  # 截止频率（根据需要调整）
fft_high_pass = fft_prices.copy()
fft_high_pass[np.abs(fft_freq) < cutoff_high] = 0

# 应用逆傅里叶变换得到滤波后的时间域数据
prices_low_pass = np.fft.ifft(fft_low_pass)
prices_high_pass = np.fft.ifft(fft_high_pass)

# 绘制滤波后的数据
plt.figure(figsize=(14, 7))
plt.plot(prices.index, prices_low_pass.real, label='Low-pass Filtered Prices')
plt.plot(prices.index, prices_high_pass.real, label='High-pass Filtered Prices')
plt.title('Filtered Bitcoin Prices')
plt.xlabel('Date')
plt.ylabel('Price (USD)')
plt.legend()
plt.show()
