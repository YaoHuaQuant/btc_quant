-- eth现货价格
CREATE TABLE kline_eth_usdt_1m
(
    `open_time` DateTime,                -- 开盘时间
    `open_price` Float64,               -- 开盘价格
    `high_price` Float64,               -- 最高价格
    `low_price` Float64,                -- 最低价格
    `close_price` Float64,              -- 收盘价格
    `volume` Float64,                   -- 成交量
    `close_time` DateTime,              -- 收盘时间
    `quote_asset_volume` Float64,       -- 报价资产成交量
    `num_of_trades` Float64,             -- 成交笔数
    `taker_buy_base_volume` Float64,    -- 主动买入成交量（基准货币）
    `taker_buy_quote_volume` Float64    -- 主动买入成交量（报价货币）
)
ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMM(open_time)        -- 按月份分区
ORDER BY (open_time);                   -- 按开盘时间排序
