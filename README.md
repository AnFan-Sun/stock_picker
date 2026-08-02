# A股选股工具

白天自动选股推送，晚上Web看盘复盘。

## 功能模块

### 1. 定时推送（main.py）
- 每个交易日 14:35 / 14:45 / 14:55 自动选股
- 推送到企业微信（或邮件）
- 自动保存推送历史

### 2. Web看盘（app.py）
- 查看今日推送的所有股票
- K线图 + 成交量 + MACD + KDJ 四图联动
- 策略回测功能

## 项目结构

```
stock_picker/
├── config.py          # 配置文件（推送方式、选股参数等）
├── stock_picker.py    # 选股核心逻辑
├── notifier.py        # 推送模块（企业微信）
├── push_history.py    # 推送历史记录
├── main.py            # 定时推送入口
├── app.py             # Web看盘入口
├── backtest.py        # 回测模块
├── mail_sender.py     # 邮件推送（备选）
├── templates/
│   └── index.html     # 前端页面
└── data/
    └── push_history.json  # 推送历史数据
```

## 快速开始

### 1. 安装依赖
```bash
pip install flask akshare pandas numpy schedule requests
```

### 2. 配置企业微信推送
编辑 `config.py`：
```python
PUSH_TYPE = "wecom"
WECOM_CONFIG = {
    "webhook_url": "你的企业微信机器人Webhook地址",
}
```

**获取Webhook地址：**
1. 打开企业微信，创建一个群
2. 群设置 → 添加群机器人
3. 复制Webhook地址

### 3. 测试推送
```bash
python main.py test
```

### 4. 启动定时推送
```bash
python main.py
```

### 5. 启动Web看盘
```bash
python app.py
```
浏览器访问 http://localhost:5000

## 选股策略

- **技术指标**：MA5上穿MA10 + MACD金叉
- **涨幅**：3% ~ 5%
- **换手率**：8% ~ 12%
- **剔除**：ST、科创板、创业板、北交所

## 命令说明

| 命令 | 说明 |
|------|------|
| `python main.py` | 启动定时推送 |
| `python main.py now` | 立即执行一次选股 |
| `python main.py test` | 发送测试推送 |
| `python app.py` | 启动Web看盘 |

## 自定义配置

编辑 `config.py` 可以调整：
- 推送方式（企业微信/邮件）
- 选股参数（涨幅、换手率、金叉天数等）
- 定时发送时间
- 历史K线天数

## 注意事项

1. 数据源来自东方财富，非交易时间可能不稳定
2. 回测结果仅供参考，不构成投资建议
3. 建议在交易日实际验证后再用于实盘

---
*仅供学习研究，不构成投资建议*
