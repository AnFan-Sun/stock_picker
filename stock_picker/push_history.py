"""
推送历史记录模块
保存每天推送的股票，支持历史查询和统计分析
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

# 数据文件路径
DATA_DIR = Path(__file__).parent / "data"
HISTORY_FILE = DATA_DIR / "push_history.json"


def _ensure_data_dir():
    """确保数据目录存在"""
    DATA_DIR.mkdir(exist_ok=True)


def _load_history():
    """加载历史记录"""
    _ensure_data_dir()
    if not HISTORY_FILE.exists():
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_history(history):
    """保存历史记录"""
    _ensure_data_dir()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def save_push_result(stocks, push_label=""):
    """
    保存一次推送结果
    
    Args:
        stocks: 选中的股票列表
        push_label: 推送标签（如 "14:35"、"第一次"）
    """
    history = _load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M:%S")

    if today not in history:
        history[today] = []

    # 记录这次推送
    record = {
        "push_time": now_time,
        "push_label": push_label,
        "stock_count": len(stocks),
        "stocks": stocks
    }
    history[today].append(record)

    # 只保留最近90天的记录
    days = sorted(history.keys(), reverse=True)[:90]
    history = {k: history[k] for k in days}

    _save_history(history)
    return record


def get_date_list():
    """获取所有有记录的日期列表（倒序）"""
    history = _load_history()
    return sorted(history.keys(), reverse=True)


def get_date_pushes(date_str):
    """获取指定日期的所有推送（合并去重）"""
    history = _load_history()

    if date_str not in history:
        return []

    # 合并所有推送的股票，去重
    all_stocks = {}
    for push in history[date_str]:
        for stock in push["stocks"]:
            code = stock["code"]
            if code not in all_stocks:
                all_stocks[code] = stock
                all_stocks[code]["first_push"] = push["push_time"]
                all_stocks[code]["push_count"] = 1
            else:
                all_stocks[code].update(stock)
                all_stocks[code]["push_count"] += 1

    return list(all_stocks.values())


def get_date_push_details(date_str):
    """获取指定日期推送的详细记录（按推送批次）"""
    history = _load_history()

    if date_str not in history:
        return []

    return history[date_str]


def get_today_pushes():
    """获取今天所有推送的股票（合并去重）"""
    today = datetime.now().strftime("%Y-%m-%d")
    return get_date_pushes(today)


def get_today_push_details():
    """获取今天推送的详细记录（按推送批次）"""
    today = datetime.now().strftime("%Y-%m-%d")
    return get_date_push_details(today)


def analyze_stocks(days=7):
    """
    统计分析最近N天的股票
    
    Returns:
        {
            "hot_stocks": [  # 命中次数最多的股票
                {"code": "000001", "name": "平安银行", "hit_count": 5, "hit_days": ["2026-08-01", ...]},
                ...
            ],
            "consecutive_stocks": [  # 连续命中的股票
                {"code": "000001", "name": "平安银行", "consecutive_days": 3, "last_date": "2026-08-02"},
                ...
            ],
            "total_days": 统计天数,
            "total_pushes": 总推送次数,
        }
    """
    history = _load_history()
    
    # 获取最近N天的日期
    all_dates = sorted(history.keys(), reverse=True)[:days]
    if not all_dates:
        return {
            "hot_stocks": [],
            "consecutive_stocks": [],
            "total_days": 0,
            "total_pushes": 0,
        }
    
    # 统计每只股票的命中情况
    stock_stats = {}  # code -> {name, hit_days: set, ...}
    
    total_pushes = 0
    for date_str in all_dates:
        pushes = history[date_str]
        total_pushes += len(pushes)
        
        # 合并当天所有推送的股票
        day_stocks = set()
        for push in pushes:
            for stock in push["stocks"]:
                code = stock["code"]
                day_stocks.add(code)
                if code not in stock_stats:
                    stock_stats[code] = {
                        "code": code,
                        "name": stock["name"],
                        "hit_days": set(),
                        "hit_count": 0,
                    }
                stock_stats[code]["hit_count"] += 1
        
        # 记录命中日期
        for code in day_stocks:
            stock_stats[code]["hit_days"].add(date_str)
    
    # 转换为列表并排序
    stocks_list = []
    for code, stats in stock_stats.items():
        stocks_list.append({
            "code": code,
            "name": stats["name"],
            "hit_count": len(stats["hit_days"]),  # 命中天数
            "total_hits": stats["hit_count"],     # 总命中次数（一天多次推送算多次）
            "hit_days": sorted(list(stats["hit_days"]), reverse=True),
        })
    
    # 按命中天数排序
    hot_stocks = sorted(stocks_list, key=lambda x: (-x["hit_count"], -x["total_hits"]))[:10]
    
    # 找出连续命中的股票
    consecutive_stocks = []
    sorted_dates = sorted(all_dates)  # 正序
    
    for stock in stocks_list:
        hit_dates = sorted(stock["hit_days"])
        
        # 计算最长连续天数
        max_consecutive = 0
        current_consecutive = 0
        last_date = None
        
        for d in hit_dates:
            if last_date is None:
                current_consecutive = 1
            else:
                # 检查是否连续（只算交易日，这里简单按日期差1判断）
                d1 = datetime.strptime(last_date, "%Y-%m-%d")
                d2 = datetime.strptime(d, "%Y-%m-%d")
                diff = (d2 - d1).days
                
                if diff == 1:
                    current_consecutive += 1
                elif diff <= 3 and d1.weekday() == 4:  # 周五到周一，差3天也算连续
                    current_consecutive += 1
                else:
                    current_consecutive = 1
            
            max_consecutive = max(max_consecutive, current_consecutive)
            last_date = d
        
        if max_consecutive >= 2:  # 连续2天以上才算
            consecutive_stocks.append({
                "code": stock["code"],
                "name": stock["name"],
                "consecutive_days": max_consecutive,
                "last_date": hit_dates[-1],
                "hit_days": stock["hit_days"],
            })
    
    # 按连续天数排序
    consecutive_stocks = sorted(consecutive_stocks, key=lambda x: -x["consecutive_days"])[:10]
    
    return {
        "hot_stocks": hot_stocks,
        "consecutive_stocks": consecutive_stocks,
        "total_days": len(all_dates),
        "total_pushes": total_pushes,
    }
