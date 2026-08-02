"""
推送通知模块
支持：企业微信机器人
"""

import json
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class WeComNotifier:
    """企业微信群机器人推送"""

    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send_text(self, content):
        """发送纯文本消息"""
        data = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        return self._send(data)

    def send_markdown(self, content):
        """发送Markdown消息"""
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        return self._send(data)

    def send_stock_report(self, selected_stocks, run_time=None, label=""):
        """发送选股报告（Markdown格式）"""
        if run_time is None:
            now = datetime.now()
            run_time = now.strftime("%Y-%m-%d %H:%M:%S")
            date_str = now.strftime("%Y年%m月%d日")
            time_str = now.strftime("%H:%M")
            weekday_map = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
            weekday = weekday_map[now.weekday()]
        else:
            # 如果传入了时间字符串，也解析一下
            try:
                dt = datetime.strptime(run_time, "%Y-%m-%d %H:%M:%S")
                date_str = dt.strftime("%Y年%m月%d日")
                time_str = dt.strftime("%H:%M")
                weekday_map = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
                weekday = weekday_map[dt.weekday()]
            except:
                date_str = run_time.split()[0] if " " in run_time else run_time
                time_str = run_time.split()[1] if " " in run_time else ""
                weekday = ""

        # 标题后缀
        title_suffix = f" - {label}" if label else ""

        if not selected_stocks:
            content = f"""## 📊 选股报告{title_suffix}

### 📅 {date_str} {weekday}
### ⏰ {time_str}

> 今日暂无符合条件的股票

---
*仅供参考，不构成投资建议*
"""
        else:
            # 构建股票列表
            stock_list = ""
            for i, s in enumerate(selected_stocks, 1):
                change_emoji = "📈" if s["change_pct"] >= 0 else "📉"
                stock_list += f"{i}. **{s['name']}**（{s['code']}）\n"
                stock_list += f"   > 价格: {s['price']} | 涨幅: {s['change_pct']}% | 换手: {s['turnover']}%\n\n"

            content = f"""## 📊 选股报告{title_suffix}

### 📅 {date_str} {weekday}
### ⏰ {time_str}
### 🎯 命中 {len(selected_stocks)} 只

---

{stock_list}

---
*仅供参考，不构成投资建议*
"""

        return self.send_markdown(content)

    def _send(self, data):
        """发送消息"""
        if not self.webhook_url:
            logger.warning("未配置企业微信webhook，跳过推送")
            return False

        try:
            response = requests.post(
                self.webhook_url,
                data=json.dumps(data),
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            result = response.json()
            if result.get("errcode") == 0:
                logger.info("企业微信推送成功")
                return True
            else:
                logger.error(f"企业微信推送失败: {result}")
                return False
        except Exception as e:
            logger.error(f"企业微信推送异常: {e}")
            return False


# 快捷函数
def send_wecom_report(webhook_url, stocks, run_time=None):
    """发送选股报告到企业微信"""
    notifier = WeComNotifier(webhook_url)
    return notifier.send_stock_report(stocks, run_time)
