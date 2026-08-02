"""
A股选股工具 - 定时推送入口
功能：每个交易日定时选股，推送到企业微信，并记录历史
"""

import sys
import time
import logging
from datetime import datetime

import schedule

from config import SCHEDULE_TIMES, PUSH_TYPE, WECOM_CONFIG, EMAIL_CONFIG
from stock_picker import run_stock_pick
from notifier import WeComNotifier
from push_history import save_push_result

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def is_trading_day():
    """判断今天是否为交易日（简单判断：周一到周五）"""
    return datetime.now().weekday() < 5


def push_notification(stocks, label=""):
    """推送选股结果"""
    if PUSH_TYPE == "wecom":
        notifier = WeComNotifier(WECOM_CONFIG["webhook_url"])
        return notifier.send_stock_report(stocks, label=label)
    elif PUSH_TYPE == "email":
        # 邮件推送（备选）
        from mail_sender import send_email
        return send_email(stocks, subject_prefix=f"选股报告-{label}")
    else:
        logger.warning(f"未知推送方式: {PUSH_TYPE}")
        return False


def job(schedule_label=""):
    """执行一次选股 + 推送"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{schedule_label}] 定时任务触发，当前时间: {now}")

    if not is_trading_day():
        logger.info("今天不是交易日，跳过")
        return

    try:
        # 执行选股
        selected = run_stock_pick()

        # 推送
        push_notification(selected, schedule_label)

        # 保存历史记录
        save_push_result(selected, push_label=schedule_label)
        logger.info(f"已保存推送历史，共 {len(selected)} 只股票")

    except Exception as e:
        logger.error(f"任务执行失败: {e}", exc_info=True)


def main():
    """主程序入口"""
    logger.info("=" * 60)
    logger.info("  A股选股工具已启动")
    logger.info(f"  推送方式: {PUSH_TYPE}")
    logger.info(f"  定时时间: {', '.join(SCHEDULE_TIMES)}")
    logger.info("  按 Ctrl+C 退出")
    logger.info("=" * 60)

    # 注册定时任务
    for t in SCHEDULE_TIMES:
        schedule.every().day.at(t).do(job, schedule_label=t)
        logger.info(f"  ✓ 已注册: 每天 {t}")

    # 主循环
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("\n程序已退出")
        sys.exit(0)


# 命令行参数
if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "now":
            # 立即执行一次
            logger.info("立即执行一次选股...")
            job(schedule_label="手动触发")

        elif arg == "test":
            # 测试推送
            logger.info("发送测试推送...")
            test_stocks = [
                {"code": "000001", "name": "平安银行", "price": 12.34, "change_pct": 4.56, "turnover": 10.2},
                {"code": "000002", "name": "万科A", "price": 8.56, "change_pct": 3.21, "turnover": 9.8},
            ]
            push_notification(test_stocks, "测试推送")
            logger.info("测试推送已发送")

        else:
            print(f"未知参数: {arg}")
            print("用法:")
            print("  python main.py          启动定时任务")
            print("  python main.py now      立即执行一次")
            print("  python main.py test     测试推送")
    else:
        main()
