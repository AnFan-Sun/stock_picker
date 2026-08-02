# ============================================================
# 选股工具配置文件（示例）
# 使用方法：复制本文件为 config.py，然后填入你的真实配置
# ============================================================

# ---------- 推送方式 ----------
# 可选: "wecom" (企业微信), "email" (邮件)
PUSH_TYPE = "wecom"

# ---------- 企业微信机器人配置 ----------
# 获取方式：企业微信群 → 右上角 → 添加群机器人 → 复制Webhook地址
WECOM_CONFIG = {
    "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的webhook_key",
}

# ---------- 邮件配置（备选） ----------
EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "use_ssl": True,
    "sender_email": "your_email@qq.com",
    "sender_password": "your_auth_code_or_password",
    "receivers": ["your_email@qq.com"],
    "sender_name": "选股助手",
}

# ---------- 选股参数 ----------
STOCK_CONFIG = {
    # 当日涨幅区间（百分比）
    "price_change_min": 3.0,   # 最小涨幅 3%
    "price_change_max": 5.0,   # 最大涨幅 5%

    # 换手率区间（百分比），10% 左右
    "turnover_min": 8.0,       # 最小换手率 8%
    "turnover_max": 12.0,      # 最大换手率 12%

    # 近 N 个交易日内出现金叉
    "golden_cross_days": 5,    # 近 5 个交易日

    # MA 均线周期
    "ma_short": 5,             # 短期均线（5日线）
    "ma_long": 10,             # 长期均线（10日线）

    # MACD 参数（标准参数：12, 26, 9）
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,

    # 剔除的股票前缀
    "exclude_prefixes": [
        "ST", "*ST", "退",      # ST / 退市股
    ],

    # 剔除的板块代码前缀
    # 688xxx = 科创板
    # 300xxx = 创业板
    # 8xxxxx / 4xxxxx = 北交所
    # 689xxx = 科创板CDR
    "exclude_market_prefixes": [
        "688", "689",   # 科创板
        "300", "301",   # 创业板
        "8", "4",       # 北交所
    ],
}

# ---------- 定时发送时间 ----------
# 24小时制，格式 "HH:MM"
SCHEDULE_TIMES = [
    "09:30",
    "10:00",
    "14:35",
    "14:45",
    "14:55",
]

# ---------- 数据获取配置 ----------
DATA_CONFIG = {
    # 每次请求间隔（秒），避免请求过快被限流
    "request_interval": 0.3,
    # 历史K线获取天数（需要足够计算 MA10 + MACD）
    "history_days": 60,
}
