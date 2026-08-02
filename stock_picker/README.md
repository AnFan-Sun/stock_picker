# A股选股工具

自动选股 + 邮件推送，每个交易日下午自动筛选符合技术形态的股票。

## 选股逻辑

| 条件 | 说明 |
|------|------|
| MA金叉 | 近5个交易日内，5日均线上穿10日均线 |
| MACD金叉 | 近5个交易日内，DIF上穿DEA |
| 当日涨幅 | 3% ~ 5% |
| 当日换手率 | 8% ~ 12%（10%左右） |
| 剔除ST | ST / *ST / 退市股全部剔除 |
| 剔除门槛板块 | 科创板(688)、创业板(300)、北交所(8/4开头) 全部剔除 |

## 文件结构

```
stock_picker/
├── config.py        # 配置文件（邮件账号、选股参数等）
├── stock_picker.py  # 选股核心逻辑
├── mail_sender.py   # 邮件发送模块
├── main.py          # 主程序（定时调度）
└── README.md        # 说明文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install akshare pandas schedule
```

### 2. 配置邮件

打开 `config.py`，修改 `EMAIL_CONFIG` 部分：

```python
EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",       # SMTP服务器
    "smtp_port": 465,                    # 端口
    "use_ssl": True,                     # 是否SSL
    "sender_email": "your_email@qq.com", # 你的邮箱
    "sender_password": "your_auth_code", # 授权码（不是登录密码！）
    "receivers": ["your_email@qq.com"],  # 收件人
    "sender_name": "选股助手",            # 发件人名称
}
```

> **关于授权码**：
> - QQ邮箱：设置 → 账户 → POP3/SMTP服务 → 开启 → 生成授权码
> - 163邮箱：设置 → POP3/SMTP/IMAP → 客户端授权密码
> - Gmail：需要开启"不太安全的应用访问"或使用应用专用密码

### 3. 测试邮件

```bash
python main.py test
```

如果收到测试邮件，说明配置正确。

### 4. 立即选股一次（测试选股逻辑）

```bash
python main.py now
```

### 5. 启动定时任务

```bash
python main.py
```

程序会在每个交易日的 **14:35、14:45、14:55** 自动选股并发送邮件。

> 注意：当前判断交易日仅按周一到周五，未排除法定节假日。
> 如需精确交易日历，可以在 `main.py` 的 `is_trading_day()` 函数中接入 akshare 的交易日历接口。

## 自定义配置

所有参数都在 `config.py` 中，可按需调整：

### 选股参数

```python
STOCK_CONFIG = {
    "price_change_min": 3.0,     # 最小涨幅
    "price_change_max": 5.0,     # 最大涨幅
    "turnover_min": 8.0,         # 最小换手率
    "turnover_max": 12.0,        # 最大换手率
    "golden_cross_days": 5,      # 金叉回看天数
    "ma_short": 5,               # 短期均线周期
    "ma_long": 10,               # 长期均线周期
    # ...
}
```

### 发送时间

```python
SCHEDULE_TIMES = [
    "14:35",
    "14:45",
    "14:55",
]
```

## 常见问题

**Q: 收不到邮件？**
- 检查邮箱是否开启了 SMTP 服务
- 确认使用的是"授权码"而非登录密码
- 检查垃圾邮件文件夹
- 运行 `python main.py test` 排查

**Q: 选股速度慢？**
- 初筛后通常只有几十只股票需要逐只查K线，整体约1-2分钟
- 可在 `config.py` 中调整 `request_interval` 控制请求间隔

**Q: 节假日也会发邮件？**
- 当前版本仅排除周末，法定节假日仍会触发但选不出股票（市场休市无数据）
- 如需精确控制，可接入交易日历

## 免责声明

本工具仅供学习和研究使用，不构成任何投资建议。股市有风险，投资需谨慎。
