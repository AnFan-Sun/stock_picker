# ============================================================
# A股选股工具 - 核心选股逻辑
# 功能：MA5上穿MA10 + MACD金叉 + 涨幅3%~5% + 换手率10%左右
# ============================================================

# 禁用代理，避免系统代理导致网络请求失败
import os
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging

from config import STOCK_CONFIG, DATA_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================================
# 1. 获取全市场股票列表（剔除ST、科创板、创业板等）
# ============================================================
def get_stock_list(max_retries=3):
    """
    获取A股股票列表，并按规则剔除不符合条件的股票。
    返回：DataFrame，包含 代码、名称 等字段
    失败自动重试 max_retries 次
    """
    logger.info("正在获取全市场股票列表...")

    # 获取沪深A股列表（带重试）- 使用腾讯数据源
    df = None
    for attempt in range(max_retries):
        try:
            df = ak.stock_zh_a_spot_tx()
            if df is not None and len(df) > 0:
                break
        except Exception as e:
            if attempt < max_retries - 1:
                logger.debug(f"获取股票列表第 {attempt+1} 次失败，重试中: {e}")
                time.sleep(2)
            else:
                raise

    if df is None or len(df) == 0:
        raise ValueError("获取股票列表失败")

    # 先删掉原来的turnover列（成交额，和我们要的换手率重名）
    if "turnover" in df.columns:
        df = df.drop(columns=["turnover"])

    # 重命名列
    col_map = {
        "code": "code_full",  # 带sh/sz前缀的完整代码
        "name": "name",
        "zxj": "price",
        "zdf": "change_pct",
        "hsl": "turnover",  # 换手率
    }
    df = df.rename(columns=col_map)

    # 提取纯数字代码（去掉sh/sz前缀）
    df["code"] = df["code_full"].str[2:]

    # 确保关键列存在
    required_cols = ["code", "name", "price", "change_pct", "turnover"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"数据列 {col} 不存在，请检查 akshare 版本或接口变更")

    # 转换为数值类型
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["change_pct"] = pd.to_numeric(df["change_pct"], errors="coerce")
    df["turnover"] = pd.to_numeric(df["turnover"], errors="coerce")

    # 去掉空值
    df = df.dropna(subset=["price", "change_pct", "turnover"])

    total_count = len(df)
    logger.info(f"获取到 {total_count} 只股票")

    # ---------- 剔除 ST / *ST / 退市股 ----------
    exclude_prefixes = STOCK_CONFIG["exclude_prefixes"]
    mask_st = df["name"].apply(
        lambda x: not any(x.startswith(prefix) for prefix in exclude_prefixes)
    )
    df = df[mask_st].copy()
    logger.info(f"剔除ST/退市股后剩余 {len(df)} 只")

    # ---------- 剔除科创板、创业板、北交所 ----------
    exclude_market = STOCK_CONFIG["exclude_market_prefixes"]
    mask_market = df["code"].apply(
        lambda x: not any(x.startswith(prefix) for prefix in exclude_market)
    )
    df = df[mask_market].copy()
    logger.info(f"剔除科创板/创业板/北交所后剩余 {len(df)} 只")

    # ---------- 当日涨幅初筛（先粗筛，减少后续计算量） ----------
    chg_min = STOCK_CONFIG["price_change_min"]
    chg_max = STOCK_CONFIG["price_change_max"]
    df = df[(df["change_pct"] >= chg_min) & (df["change_pct"] <= chg_max)].copy()
    logger.info(f"涨幅 {chg_min}%~{chg_max}% 初筛后剩余 {len(df)} 只")

    # ---------- 换手率初筛 ----------
    tur_min = STOCK_CONFIG["turnover_min"]
    tur_max = STOCK_CONFIG["turnover_max"]
    df = df[(df["turnover"] >= tur_min) & (df["turnover"] <= tur_max)].copy()
    logger.info(f"换手率 {tur_min}%~{tur_max}% 初筛后剩余 {len(df)} 只")

    # 剔除停牌（价格为0或空）
    df = df[df["price"] > 0].copy()

    df = df.reset_index(drop=True)
    return df


# ============================================================
# 2. 计算技术指标（MA + MACD）
# ============================================================
def calc_ma(series, period):
    """计算简单移动平均"""
    return series.rolling(window=period, min_periods=period).mean()


def calc_macd(close, fast=12, slow=26, signal=9):
    """
    计算 MACD 指标
    返回：dif, dea, macd_hist
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd_hist = (dif - dea) * 2  # A股习惯乘以2
    return dif, dea, macd_hist


# ============================================================
# 3. 判断金叉条件
# ============================================================
def check_ma_golden_cross(df_hist, ma_short=5, ma_long=10, lookback_days=5):
    """
    检查近 lookback_days 个交易日内是否出现 MA_short 上穿 MA_long
    """
    ma_s = calc_ma(df_hist["close"], ma_short)
    ma_l = calc_ma(df_hist["close"], ma_long)

    # 上穿：前一天 ma_s <= ma_l，当天 ma_s > ma_l
    cross = (ma_s.shift(1) <= ma_l.shift(1)) & (ma_s > ma_l)

    # 取最近 lookback_days 天（含当日）
    recent_cross = cross.tail(lookback_days)
    return recent_cross.any()


def check_macd_golden_cross(df_hist, fast=12, slow=26, signal=9, lookback_days=5):
    """
    检查近 lookback_days 个交易日内是否出现 MACD 金叉（DIF 上穿 DEA）
    """
    dif, dea, _ = calc_macd(df_hist["close"], fast, slow, signal)

    # 金叉：前一天 dif <= dea，当天 dif > dea
    cross = (dif.shift(1) <= dea.shift(1)) & (dif > dea)

    recent_cross = cross.tail(lookback_days)
    return recent_cross.any()


# ============================================================
# 4. 获取单只股票历史K线
# ============================================================
def get_stock_history(code, days=60, max_retries=3):
    """
    获取单只股票近 days 天的日K线数据
    返回：DataFrame，包含 date, open, close, high, low, volume 等
    失败自动重试 max_retries 次
    """
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

    # 构造腾讯格式的股票代码（带sh/sz前缀）
    if code.startswith("6"):
        tx_code = f"sh{code}"
    else:
        tx_code = f"sz{code}"

    for attempt in range(max_retries):
        try:
            # 使用腾讯数据源
            df = ak.stock_zh_a_hist_tx(
                symbol=tx_code,
                start_date=start_date,
                end_date=end_date,
            )

            if df is None or len(df) == 0:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return None

            # 确保关键列存在
            if "close" not in df.columns:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return None

            df = df.tail(days).reset_index(drop=True)
            return df

        except Exception as e:
            if attempt < max_retries - 1:
                logger.debug(f"获取 {code} 历史数据第 {attempt+1} 次失败，重试中: {e}")
                time.sleep(1)
            else:
                logger.warning(f"获取 {code} 历史数据失败（重试 {max_retries} 次）: {e}")
                return None


# ============================================================
# 5. 主选股流程
# ============================================================
def run_stock_pick():
    """
    执行完整选股流程，返回选中的股票列表
    """
    logger.info("=" * 50)
    logger.info("开始选股...")
    start_time = time.time()

    # Step 1: 获取股票列表并做初筛
    stock_list = get_stock_list()
    if len(stock_list) == 0:
        logger.warning("初筛后无符合条件的股票")
        return []

    # Step 2: 逐只检查技术指标
    selected = []
    ma_short = STOCK_CONFIG["ma_short"]
    ma_long = STOCK_CONFIG["ma_long"]
    fast = STOCK_CONFIG["macd_fast"]
    slow = STOCK_CONFIG["macd_slow"]
    signal = STOCK_CONFIG["macd_signal"]
    lookback = STOCK_CONFIG["golden_cross_days"]
    history_days = DATA_CONFIG["history_days"]
    interval = DATA_CONFIG["request_interval"]

    total = len(stock_list)
    logger.info(f"开始逐只检查技术指标，共 {total} 只股票...")

    for idx, row in stock_list.iterrows():
        code = row["code"]
        name = row["name"]
        price = row["price"]
        change_pct = row["change_pct"]
        turnover = row["turnover"]

        if (idx + 1) % 20 == 0:
            logger.info(f"进度: {idx + 1}/{total}")

        # 获取历史K线
        df_hist = get_stock_history(code, history_days)
        if df_hist is None or len(df_hist) < ma_long + slow:
            time.sleep(interval)
            continue

        # 检查 MA 金叉
        ma_cross = check_ma_golden_cross(
            df_hist, ma_short, ma_long, lookback
        )
        if not ma_cross:
            time.sleep(interval)
            continue

        # 检查 MACD 金叉
        macd_cross = check_macd_golden_cross(
            df_hist, fast, slow, signal, lookback
        )
        if not macd_cross:
            time.sleep(interval)
            continue

        # 全部条件满足
        selected.append({
            "code": code,
            "name": name,
            "price": round(price, 2),
            "change_pct": round(change_pct, 2),
            "turnover": round(turnover, 2),
        })
        logger.info(f"  ✓ 选中: {code} {name} 涨幅{change_pct}% 换手{turnover}%")

        time.sleep(interval)

    elapsed = time.time() - start_time
    logger.info(f"选股完成，共选中 {len(selected)} 只股票，耗时 {elapsed:.1f} 秒")
    logger.info("=" * 50)

    return selected


# ============================================================
# 测试
# ============================================================
if __name__ == "__main__":
    results = run_stock_pick()
    print("\n===== 选股结果 =====")
    if results:
        for s in results:
            print(f"{s['code']} {s['name']}  价格:{s['price']}  涨幅:{s['change_pct']}%  换手率:{s['turnover']}%")
    else:
        print("暂无符合条件的股票")
