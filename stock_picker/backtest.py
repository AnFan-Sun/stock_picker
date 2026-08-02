# ============================================================
# 回测模块
# 策略：MA5上穿MA10 + MACD金叉 买入，MA5下穿MA10 卖出
# ============================================================

import pandas as pd
import numpy as np
from datetime import datetime
import akshare as ak
import logging

from config import STOCK_CONFIG

logger = logging.getLogger(__name__)


# ============================================================
# 指标计算
# ============================================================
def calc_ma(series, period):
    return series.rolling(window=period, min_periods=period).mean()


def calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd_hist = (dif - dea) * 2
    return dif, dea, macd_hist


def calc_kdj(high, low, close, n=9, m1=3, m2=3):
    """计算KDJ指标"""
    lowest_low = low.rolling(window=n, min_periods=1).min()
    highest_high = high.rolling(window=n, min_periods=1).max()
    
    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    rsv = rsv.fillna(50)
    
    k = rsv.ewm(com=m1 - 1, adjust=False).mean()
    d = k.ewm(com=m2 - 1, adjust=False).mean()
    j = 3 * k - 2 * d
    
    return k, d, j


def calc_volume_ma(volume, period=5):
    """计算成交量均线"""
    return volume.rolling(window=period, min_periods=period).mean()


# ============================================================
# 信号生成
# ============================================================
def generate_signals(df, ma_short=5, ma_long=10, fast=12, slow=26, signal=9):
    """
    生成买卖信号
    返回：带 signal 列的 DataFrame（1=买入, -1=卖出, 0=无信号）
    """
    df = df.copy()
    
    # 计算指标
    df["ma_short"] = calc_ma(df["close"], ma_short)
    df["ma_long"] = calc_ma(df["close"], ma_long)
    df["dif"], df["dea"], df["macd_hist"] = calc_macd(df["close"], fast, slow, signal)
    df["k"], df["d"], df["j"] = calc_kdj(df["high"], df["low"], df["close"])
    df["vol_ma5"] = calc_volume_ma(df["volume"], 5)
    
    # MA金叉/死叉
    df["ma_cross_up"] = (df["ma_short"].shift(1) <= df["ma_long"].shift(1)) & (df["ma_short"] > df["ma_long"])
    df["ma_cross_down"] = (df["ma_short"].shift(1) >= df["ma_long"].shift(1)) & (df["ma_short"] < df["ma_long"])
    
    # MACD金叉/死叉
    df["macd_cross_up"] = (df["dif"].shift(1) <= df["dea"].shift(1)) & (df["dif"] > df["dea"])
    df["macd_cross_down"] = (df["dif"].shift(1) >= df["dea"].shift(1)) & (df["dif"] < df["dea"])
    
    # 买入信号：MA金叉 且 MACD金叉（同一天或前后几天内都算）
    # 这里简化：MA金叉当天，且MACD在金叉状态（dif > dea）
    df["buy_signal"] = df["ma_cross_up"] & (df["dif"] > df["dea"])
    
    # 卖出信号：MA死叉
    df["sell_signal"] = df["ma_cross_down"]
    
    return df


# ============================================================
# 回测执行
# ============================================================
def run_backtest(df, initial_capital=100000, position_pct=1.0, commission_rate=0.0003):
    """
    执行回测
    
    参数：
        df: 包含 date, open, close, high, low, volume, buy_signal, sell_signal 的 DataFrame
        initial_capital: 初始资金
        position_pct: 每次买入使用资金比例
        commission_rate: 手续费率（双边）
    
    返回：
        dict: 回测结果，包含 交易记录、资金曲线、各项指标
    """
    df = df.copy().reset_index(drop=True)
    
    cash = initial_capital
    shares = 0  # 持股数量
    position = 0  # 持仓状态
    trades = []  # 交易记录
    equity_curve = []  # 资金曲线
    
    entry_price = 0
    entry_date = None
    
    for i, row in df.iterrows():
        date = row["date"]
        close = row["close"]
        open_price = row["open"]
        
        # 当日总资产
        total_asset = cash + shares * close
        
        # 买入信号（次日开盘价成交，更贴近真实）
        if row["buy_signal"] and position == 0:
            # 用次日开盘价买入（如果有次日数据）
            if i + 1 < len(df):
                buy_price = df.iloc[i + 1]["open"]
                buy_date = df.iloc[i + 1]["date"]
                buy_amount = cash * position_pct
                shares = int(buy_amount / buy_price / 100) * 100  # 100股一手
                if shares > 0:
                    cost = shares * buy_price
                    commission = cost * commission_rate
                    cash -= (cost + commission)
                    position = 1
                    entry_price = buy_price
                    entry_date = buy_date
                    total_asset = cash + shares * df.iloc[i + 1]["close"]
                    trades.append({
                        "type": "买入",
                        "date": buy_date,
                        "price": round(buy_price, 2),
                        "shares": shares,
                        "amount": round(cost, 2),
                        "commission": round(commission, 2),
                    })
        
        # 卖出信号
        elif row["sell_signal"] and position == 1:
            if i + 1 < len(df):
                sell_price = df.iloc[i + 1]["open"]
                sell_date = df.iloc[i + 1]["date"]
                revenue = shares * sell_price
                commission = revenue * commission_rate
                cash += (revenue - commission)
                profit = revenue - shares * entry_price - commission - shares * entry_price * commission_rate
                profit_pct = (sell_price / entry_price - 1) * 100
                position = 0
                total_asset = cash
                trades.append({
                    "type": "卖出",
                    "date": sell_date,
                    "price": round(sell_price, 2),
                    "shares": shares,
                    "amount": round(revenue, 2),
                    "commission": round(commission, 2),
                    "profit": round(profit, 2),
                    "profit_pct": round(profit_pct, 2),
                    "hold_days": (pd.to_datetime(sell_date) - pd.to_datetime(entry_date)).days,
                })
                shares = 0
                entry_price = 0
                entry_date = None
        
        equity_curve.append({
            "date": date,
            "total_asset": round(total_asset, 2),
            "cash": round(cash, 2),
            "shares": shares,
            "position": position,
        })
    
    # 如果最后还持仓，按最后收盘价计算
    if position == 1 and len(df) > 0:
        last_close = df.iloc[-1]["close"]
        total_asset = cash + shares * last_close
        # 补一条卖出记录（标记为持仓中）
        trades.append({
            "type": "持仓中",
            "date": df.iloc[-1]["date"],
            "price": round(last_close, 2),
            "shares": shares,
            "amount": round(shares * last_close, 2),
            "commission": 0,
            "profit": round(shares * last_close - shares * entry_price, 2),
            "profit_pct": round((last_close / entry_price - 1) * 100, 2),
            "hold_days": (pd.to_datetime(df.iloc[-1]["date"]) - pd.to_datetime(entry_date)).days,
        })
    
    # 计算回测指标
    metrics = calc_metrics(equity_curve, trades, initial_capital)
    
    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "metrics": metrics,
    }


def calc_metrics(equity_curve, trades, initial_capital):
    """计算回测指标"""
    if not equity_curve:
        return {}
    
    df_eq = pd.DataFrame(equity_curve)
    total_return = (df_eq["total_asset"].iloc[-1] / initial_capital - 1) * 100
    
    # 年化收益率
    days = (pd.to_datetime(df_eq["date"].iloc[-1]) - pd.to_datetime(df_eq["date"].iloc[0])).days
    annual_return = ((1 + total_return / 100) ** (365 / max(days, 1)) - 1) * 100 if days > 0 else 0
    
    # 最大回撤
    peak = df_eq["total_asset"].cummax()
    drawdown = (df_eq["total_asset"] - peak) / peak * 100
    max_drawdown = drawdown.min()
    
    # 交易统计
    sell_trades = [t for t in trades if t["type"] == "卖出"]
    win_trades = [t for t in sell_trades if t.get("profit", 0) > 0]
    loss_trades = [t for t in sell_trades if t.get("profit", 0) <= 0]
    
    total_trades = len(sell_trades)
    win_rate = len(win_trades) / total_trades * 100 if total_trades > 0 else 0
    
    avg_win = np.mean([t["profit_pct"] for t in win_trades]) if win_trades else 0
    avg_loss = np.mean([t["profit_pct"] for t in loss_trades]) if loss_trades else 0
    profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")
    
    avg_hold_days = np.mean([t.get("hold_days", 0) for t in sell_trades]) if sell_trades else 0
    
    # 基准收益（买入持有）
    if len(df_eq) > 1:
        # 这里需要价格数据，暂时用资金曲线近似
        pass
    
    return {
        "initial_capital": initial_capital,
        "final_asset": round(df_eq["total_asset"].iloc[-1], 2),
        "total_return": round(total_return, 2),
        "annual_return": round(annual_return, 2),
        "max_drawdown": round(max_drawdown, 2),
        "total_trades": total_trades,
        "win_trades": len(win_trades),
        "loss_trades": len(loss_trades),
        "win_rate": round(win_rate, 2),
        "avg_win_pct": round(avg_win, 2),
        "avg_loss_pct": round(avg_loss, 2),
        "profit_loss_ratio": round(profit_loss_ratio, 2),
        "avg_hold_days": round(avg_hold_days, 1),
        "trade_days": days,
    }


# ============================================================
# 获取历史数据并回测
# ============================================================
def backtest_stock(code, days=365, initial_capital=100000):
    """
    对单只股票进行回测
    
    参数：
        code: 股票代码
        days: 回测天数
        initial_capital: 初始资金
    
    返回：
        dict: 回测结果
    """
    try:
        from datetime import timedelta
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
        
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )
        
        if df is None or len(df) == 0:
            return {"error": "获取数据失败"}
        
        col_map = {
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
            "换手率": "turnover",
            "涨跌幅": "change_pct",
        }
        df = df.rename(columns=col_map)
        
        if "close" not in df.columns or len(df) < 30:
            return {"error": "数据不足"}
        
        df = df.tail(days).reset_index(drop=True)
        
        # 生成信号
        df = generate_signals(df)
        
        # 执行回测
        result = run_backtest(df, initial_capital)
        
        # 把K线数据也带上（前端画图用）
        result["kline"] = df.tail(120).to_dict("records")  # 最近120个交易日
        
        return result
        
    except Exception as e:
        logger.error(f"回测失败 {code}: {e}", exc_info=True)
        return {"error": str(e)}


# ============================================================
# 测试
# ============================================================
if __name__ == "__main__":
    result = backtest_stock("000001", days=250)
    if "error" in result:
        print(f"错误: {result['error']}")
    else:
        m = result["metrics"]
        print(f"总收益率: {m['total_return']}%")
        print(f"年化收益率: {m['annual_return']}%")
        print(f"最大回撤: {m['max_drawdown']}%")
        print(f"交易次数: {m['total_trades']}")
        print(f"胜率: {m['win_rate']}%")
        print(f"盈亏比: {m['profit_loss_ratio']}")
        print(f"平均持仓天数: {m['avg_hold_days']}天")
        print(f"\n交易记录:")
        for t in result["trades"]:
            print(f"  {t['date']} {t['type']} 价格:{t['price']} 数量:{t['shares']}", end="")
            if "profit_pct" in t:
                print(f" 盈亏:{t['profit_pct']}% 持仓:{t['hold_days']}天", end="")
            print()
