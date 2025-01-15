-- btc现货交易策略的action信息
create table strategy_action_btc_usdt_1m
(
    `id`                   UUID DEFAULT generateUUIDv4(),
    `version`              VARCHAR(255) comment '策略版本',
    `action_time`          DateTime comment '挂单时间/交易完成时间',
    `status`               Int8 comment '订单状态: 1.开仓挂单opening 2.已开仓opened 3.平仓挂单closing 4.已平仓closed 5.已取消canceled',
    `open_price`           DECIMAL(26, 6) comment '开仓价格',
    `close_price`          DECIMAL(26, 6) comment '平仓价格',
    `quantity`             Nullable(Decimal(26, 6)) comment '交易量',
    `open_cost`            DECIMAL(26, 6) comment '开仓成本 = 开仓价格 * 交易量',
    `expected_gross_value` Nullable(Decimal(26, 6)) comment '期望毛利润',
    `actual_gross_value`   Nullable(Decimal(26, 6)) comment '实际毛利润',
    `expected_commission`  Nullable(Decimal(26, 6)) comment '期望佣金值',
    `actual_commission`    Nullable(Decimal(26, 6)) comment '实际佣金值',

    `create_time` DateTime DEFAULT now() comment '数据更新时间'
)
engine = MergeTree()
PARTITION BY version -- 按策略分区
ORDER BY (version, action_time, id) comment 'btc现货交易策略的action信息';