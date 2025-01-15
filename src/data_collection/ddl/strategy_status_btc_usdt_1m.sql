-- btc现货交易策略的status信息
create table strategy_status_btc_usdt_1m
(
    -- 主键
    `open_time`                         DateTime comment '开盘时间',
    `version`                           VARCHAR(255) comment '策略版本',
    -- 市场数据
    `price`                             Nullable(Decimal(26, 6)) comment '市场价格',
    -- 增量数据
    -- -- 开仓挂单
    `opening_order_num`                 Nullable(Decimal(26, 6)) comment '开仓挂单数',
    `opening_order_quantity`            Nullable(Decimal(26, 6)) comment '开仓挂单BTC总量',
    `opening_order_value`               Nullable(Decimal(26, 6)) comment '开仓挂单总价', -- 开仓成本=开仓总价 因此不单独计算开仓成本
    -- -- 平仓挂单
    `closing_order_num`                 Nullable(Decimal(26, 6)) comment '平仓挂单数',
    `closing_order_quantity`            Nullable(Decimal(26, 6)) comment '平仓挂单BTC总量',
    `closing_order_value`               Nullable(Decimal(26, 6)) comment '平仓挂单总价',
    `closing_order_cost`                Nullable(Decimal(26, 6)) comment '平仓挂单成本 = sum(每单成本(每单BTC总量 * 每单开仓挂单价格))',
    -- -- 开仓成交
    `opened_order_num`                  Nullable(Decimal(26, 6)) comment '开仓成交单数',
    `opened_order_quantity`             Nullable(Decimal(26, 6)) comment '开仓成交BTC总量',
    `opened_order_value`                Nullable(Decimal(26, 6)) comment '开仓成交总价', -- 开仓成本=开仓总价 因此不单独计算开仓成本
    -- -- 平仓成交
    `closed_order_num`                  Nullable(Decimal(26, 6)) comment '平仓成交单数',
    `closed_order_quantity`             Nullable(Decimal(26, 6)) comment '平仓成交BTC总量',
    `closed_order_value`                Nullable(Decimal(26, 6)) comment '平仓成交总价',
    `closed_order_cost`                 Nullable(Decimal(26, 6)) comment '平仓成交成本 = sum(每单成本(每单BTC总量 * 每单开仓挂单价格))',

    -- 累计数据
    -- -- 开仓挂单
    `cumulative_opening_order_num`      Nullable(Decimal(26, 6)) comment '开仓挂单数',
    `cumulative_opening_order_quantity` Nullable(Decimal(26, 6)) comment '开仓挂单BTC总量',
    `cumulative_opening_order_value`    Nullable(Decimal(26, 6)) comment '开仓挂单总价', -- 开仓成本=开仓总价 因此不单独计算开仓成本
    -- -- 平仓挂单
    `cumulative_closing_order_num`      Nullable(Decimal(26, 6)) comment '平仓挂单数',
    `cumulative_closing_order_quantity` Nullable(Decimal(26, 6)) comment '平仓挂单BTC总量',
    `cumulative_closing_order_value`    Nullable(Decimal(26, 6)) comment '平仓挂单总价',
    `cumulative_closing_order_cost`     Nullable(Decimal(26, 6)) comment '平仓挂单成本 = sum(每单成本(每单BTC总量 * 每单开仓挂单价格))',
    -- -- 开仓成交
    `cumulative_opened_order_num`       Nullable(Decimal(26, 6)) comment '开仓成交单数',
    `cumulative_opened_order_quantity`  Nullable(Decimal(26, 6)) comment '开仓成交BTC总量',
    `cumulative_opened_order_value`     Nullable(Decimal(26, 6)) comment '开仓成交总价', -- 开仓成本=开仓总价 因此不单独计算开仓成本
    -- -- 平仓成交
    `cumulative_closed_order_num`       Nullable(Decimal(26, 6)) comment '平仓成交单数（累计已成交订单数）',
    `cumulative_closed_order_quantity`  Nullable(Decimal(26, 6)) comment '平仓成交BTC总量',
    `cumulative_closed_order_value`     Nullable(Decimal(26, 6)) comment '平仓成交总价',
    `cumulative_closed_order_cost`      Nullable(Decimal(26, 6)) comment '平仓成交成本 = sum(每单成本(每单BTC总量 * 每单开仓挂单价格))',

    -- 状态数据
    ---- 原子指标
    `cash`                              Nullable(Decimal(26, 6)) comment '现金余额（包含本金和借贷资金）',
    `loan`                              Nullable(Decimal(26, 6)) comment '借贷资金（欠款）',
    `holding_quantity`                  Nullable(Decimal(26, 6)) comment '实际持仓BTC总量',
    `holding_value`                     Nullable(Decimal(26, 6)) comment '实际持仓BTC总价',
    `total_value`                       Nullable(Decimal(26, 6)) comment '实际总资产 = 现金 + 实际持仓BTC总价',

    ---- 复合指标
    `expected_closing_profit`           Nullable(Decimal(26, 6)) comment '期望未成交收益 = 平仓挂单总价 - 平仓挂单成本',
    `actual_closed_profit`              Nullable(Decimal(26, 6)) comment '实际已成交收益 =平仓成交总价 - 平仓成交成本',
    `expected_market_close_profit`      Nullable(Decimal(26, 6)) comment '市价平仓期望收益(亏损) = sum((市场价格 - 每单开仓挂单价格) * 每单BTC总量）',
    `expected_closed_profit`            Nullable(Decimal(26, 6)) comment '期望总收益 = 实际已成交收益 + 期望未成交收益',
    `expected_holding_value`            Nullable(Decimal(26, 6)) comment '期望持仓市值 = 平仓挂单总价',
    `expected_total_value`              Nullable(Decimal(26, 6)) comment '期望总资产 = 现金余额 + 期望持仓市值（平仓挂单BTC总价）',
    `actual_net_value`                  Nullable(Decimal(26, 6)) comment '实际净资产 = 总资产 - 借贷资金；若净资产归零 则强制平仓',
    `expected_net_value`                Nullable(Decimal(26, 6)) comment '期望净资产 = 净资产 - 平仓挂单亏损',
    `ave_profit_per_closed_order`       Nullable(Decimal(26, 6)) comment '已成交订单平均每单盈利',

    `create_time` DateTime DEFAULT now() comment '数据更新时间'
)
    engine = ReplacingMergeTree()
        PARTITION BY version -- 按策略分区
        ORDER BY (open_time, version) comment 'btc现货交易策略的status信息';