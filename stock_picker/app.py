"""
Web看盘工具
功能：查看今日推送股票的K线走势、回测等
"""

import logging
import random
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template

import akshare as ak
import pandas as pd
import numpy as np

from config import DATA_CONFIG
from stock_picker import (
    get_stock_history,
    calc_ma,
    calc_macd,
)
from backtest import (
    backtest_stock,
    calc_kdj,
    calc_volume_ma,
)
from push_history import (
    get_today_pushes,
    get_today_push_details,
    get_date_list,
    get_date_pushes,
    analyze_stocks,
)

app = Flask(__name__)
logger = logging.getLogger(__name__)

# 缓存
_cache = {
    "kline": {},  # code -> {data, time}
}
CACHE_TTL = 300  # K线缓存5分钟


def generate_mock_kline(code, days=60):
    """生成模拟K线数据（用于数据源不可用时展示）"""
    random.seed(hash(code) % 2**32)

    base_price = random.uniform(10, 50)
    dates = []
    current_date = datetime.now() - timedelta(days=days * 2)

    for i in range(days):
        while current_date.weekday() >= 5:
            current_date += timedelta(days=1)
        dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)

    data = []
    price = base_price
    for i in range(days):
        change = random.gauss(0, 0.02)
        open_price = price
        close_price = price * (1 + change)
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.015))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.015))
        volume = int(random.uniform(500000, 2000000))

        data.append({
            "date": dates[i],
            "open": round(open_price, 2),
            "close": round(close_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "volume": volume,
        })
        price = close_price

    return pd.DataFrame(data)


# ============================================================
# 页面路由
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")


# ============================================================
# API: 历史日期列表
# ============================================================
@app.route("/api/dates")
def api_dates():
    """获取所有有记录的日期列表"""
    try:
        dates = get_date_list()
        # 如果没有历史数据，返回今天的日期（显示模拟数据）
        if not dates:
            dates = [datetime.now().strftime("%Y-%m-%d")]
        return jsonify({
            "success": True,
            "data": dates,
        })
    except Exception as e:
        logger.error(f"获取日期列表出错: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# API: 指定日期的股票列表
# ============================================================
@app.route("/api/stocks")
def api_stocks():
    """获取指定日期推送的股票列表（默认今天）"""
    try:
        date_str = request.args.get("date", "")
        is_today = not date_str or date_str == datetime.now().strftime("%Y-%m-%d")

        if date_str:
            stocks = get_date_pushes(date_str)
        else:
            stocks = get_today_pushes()

        is_mock = False

        # 如果没有数据，显示模拟数据（方便测试）
        if len(stocks) == 0:
            is_mock = True
            mock_codes = [
                ("000001", "平安银行"),
                ("000002", "万科A"),
                ("000063", "中兴通讯"),
                ("000651", "格力电器"),
                ("000858", "五粮液"),
                ("002415", "海康威视"),
                ("002594", "比亚迪"),
                ("600036", "招商银行"),
                ("600519", "贵州茅台"),
                ("601318", "中国平安"),
            ]
            random.seed(42)
            stocks = []
            for code, name in mock_codes:
                stocks.append({
                    "code": code,
                    "name": f"{name}（示例）",
                    "price": round(random.uniform(10, 100), 2),
                    "change_pct": round(random.uniform(3, 5), 2),
                    "turnover": round(random.uniform(8, 12), 2),
                    "first_push": "--:--",
                })

        return jsonify({
            "success": True,
            "data": stocks,
            "date": date_str if date_str else datetime.now().strftime("%Y-%m-%d"),
            "is_today": is_today,
            "is_mock": is_mock,
        })

    except Exception as e:
        logger.error(f"获取股票列表出错: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# API: 统计分析（推荐股票）
# ============================================================
@app.route("/api/analyze")
def api_analyze():
    """统计分析最近N天的股票，给出推荐"""
    try:
        days = int(request.args.get("days", 7))
        result = analyze_stocks(days)

        # 生成推荐原因
        for stock in result["consecutive_stocks"]:
            reasons = []
            reasons.append(f"连续 {stock['consecutive_days']} 天命中")
            reasons.append("MA金叉 + MACD金叉")
            stock["reasons"] = reasons

        for stock in result["hot_stocks"]:
            reasons = []
            reasons.append(f"近 {result['total_days']} 天命中 {stock['hit_count']} 天")
            reasons.append("MA金叉 + MACD金叉")
            stock["reasons"] = reasons

        return jsonify({
            "success": True,
            "data": result,
        })

    except Exception as e:
        logger.error(f"统计分析出错: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# API: K线数据
# ============================================================
@app.route("/api/kline/<code>")
def api_kline(code):
    """获取单只股票K线数据，含所有指标"""
    now = datetime.now()

    # 检查缓存
    if code in _cache["kline"]:
        cached = _cache["kline"][code]
        if (now - cached["time"]).total_seconds() < CACHE_TTL:
            return jsonify({
                "success": True,
                "data": cached["data"],
                "cached": True,
            })

    try:
        days = DATA_CONFIG["history_days"]
        df = get_stock_history(code, days)
        is_mock = False

        # 真实数据获取失败时，使用模拟数据
        if df is None or len(df) == 0:
            logger.warning(f"获取 {code} 真实数据失败，使用模拟数据")
            df = generate_mock_kline(code, days)
            is_mock = True

        # 计算指标
        df["ma5"] = calc_ma(df["close"], 5)
        df["ma10"] = calc_ma(df["close"], 10)
        df["ma20"] = calc_ma(df["close"], 20)
        df["dif"], df["dea"], df["macd"] = calc_macd(df["close"])
        df["k"], df["d"], df["j"] = calc_kdj(df["high"], df["low"], df["close"])
        df["vol_ma5"] = calc_volume_ma(df["volume"], 5)
        df["vol_ma10"] = calc_volume_ma(df["volume"], 10)

        # 标记金叉
        df["ma_golden_cross"] = (
            (df["ma5"].shift(1) <= df["ma10"].shift(1)) & (df["ma5"] > df["ma10"])
        )
        df["macd_golden_cross"] = (
            (df["dif"].shift(1) <= df["dea"].shift(1)) & (df["dif"] > df["dea"])
        )

        # 获取股票名称
        name = code
        if not is_mock:
            try:
                spot = ak.stock_zh_a_spot_em()
                row = spot[spot["代码"] == code]
                if len(row) > 0:
                    name = row.iloc[0]["名称"]
            except Exception:
                pass
        else:
            name = f"{code}（模拟数据）"

        # 转换为前端格式
        kline_data = []
        for _, row in df.iterrows():
            kline_data.append({
                "date": str(row["date"]),
                "open": round(float(row["open"]), 2),
                "close": round(float(row["close"]), 2),
                "high": round(float(row["high"]), 2),
                "low": round(float(row["low"]), 2),
                "volume": int(row["volume"]),
                "ma5": round(float(row["ma5"]), 2) if pd.notna(row["ma5"]) else None,
                "ma10": round(float(row["ma10"]), 2) if pd.notna(row["ma10"]) else None,
                "ma20": round(float(row["ma20"]), 2) if pd.notna(row["ma20"]) else None,
                "dif": round(float(row["dif"]), 4) if pd.notna(row["dif"]) else None,
                "dea": round(float(row["dea"]), 4) if pd.notna(row["dea"]) else None,
                "macd": round(float(row["macd"]), 4) if pd.notna(row["macd"]) else None,
                "k": round(float(row["k"]), 2) if pd.notna(row["k"]) else None,
                "d": round(float(row["d"]), 2) if pd.notna(row["d"]) else None,
                "j": round(float(row["j"]), 2) if pd.notna(row["j"]) else None,
                "vol_ma5": round(float(row["vol_ma5"]), 0) if pd.notna(row["vol_ma5"]) else None,
                "vol_ma10": round(float(row["vol_ma10"]), 0) if pd.notna(row["vol_ma10"]) else None,
                "ma_golden_cross": bool(row["ma_golden_cross"]),
                "macd_golden_cross": bool(row["macd_golden_cross"]),
            })

        result = {
            "code": code,
            "name": name,
            "kline": kline_data,
            "is_mock": is_mock,
        }

        # 更新缓存
        _cache["kline"][code] = {"data": result, "time": now}

        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(f"K线API出错 {code}: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# API: 回测
# ============================================================
@app.route("/api/backtest", methods=["POST"])
def api_backtest():
    """执行回测"""
    try:
        data = request.get_json()
        code = data.get("code", "")
        days = int(data.get("days", 250))
        initial_capital = float(data.get("initial_capital", 100000))

        if not code:
            return jsonify({"success": False, "error": "股票代码不能为空"}), 400

        result = backtest_stock(code, days=days, initial_capital=initial_capital)

        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 500

        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(f"回测API出错: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# API: 刷新缓存
# ============================================================
@app.route("/api/refresh")
def api_refresh():
    """强制刷新缓存"""
    _cache["kline"] = {}
    return jsonify({"success": True, "message": "缓存已刷新"})


# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("=" * 50)
    logger.info("  选股工具 Web 版启动中...")
    logger.info("  访问地址: http://localhost:5000")
    logger.info("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False)
