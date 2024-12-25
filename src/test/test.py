import ccxt

# 初始化交易所（以 Binance 为例）
exchange = ccxt.binance({
    'proxies': {
        'http': 'http://127.0.0.1:7890',  # HTTP 代理
        'https': 'http://127.0.0.1:7890'  # HTTPS 代理
    },
    'apiKey': 'fgFwVCEKGlS3AlgNcZoT8i7Qm4g6Q8AOe5f5SZ6qxu8H5Ip3rdf8XCFpG2YjZ01V',
    'secret': 'ckSLVE8WNJNfD6lzTNIiI3GJGv8nXtF8NCriCIp1Kj7h9zqpOFYzz5lJ5nFp1QTQ',
})

# 获取 BTC/USDT 的最新价格
# ticker = exchange.fetch_ticker('BTC/USDT')
# print(ticker['last'])  # 输出最新成交价

# 获取 BTC/USDT 的 1 小时 K 线数据
ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='1h', limit=10)
for candle in ohlcv:
    print(candle)  # [时间戳, 开盘价, 最高价, 最低价, 收盘价, 成交量]

