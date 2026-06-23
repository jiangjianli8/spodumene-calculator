#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锂辉石计价器 - 碳酸锂期货行情自动更新
数据源：新浪财经实时行情（AKShare futures_zh_realtime）
合约：LC0（碳酸锂连续主力合约）
输出：data/price.json

盘中：trade字段为实时成交价，close=0
收盘后：close字段为收盘价，trade=0

用法：
  python update_price.py           # 手动更新
  # 建议交易时段每5分钟执行一次，盘中实时刷新
"""

import json
import os
import sys
from datetime import datetime

import akshare as ak


PRICE_FILE = os.path.join(os.path.dirname(__file__), "data", "price.json")
SYMBOL = "碳酸锂"  # AKShare futures_zh_realtime 用品种中文名


def fetch_lc_price():
    """从新浪财经获取碳酸锂期货实时行情（盘中实时刷新）"""
    df = ak.futures_zh_realtime(symbol=SYMBOL)

    if df.empty:
        raise ValueError(f"未获取到 {SYMBOL} 实时行情数据")

    # 找到主力合约（LC0 连续合约）
    main_row = df[df["symbol"] == "LC0"]
    if main_row.empty:
        # 如果没有LC0，取成交量最大的合约
        main_row = df[df["volume"] == df["volume"].max()]

    row = main_row.iloc[0]

    # 盘中：trade有值（实时成交价），close=0
    # 收盘后：close有值（收盘价），trade=0
    trade_val = float(row["trade"])
    close_val = float(row["close"])

    if trade_val > 0:
        # 盘中：取trade（实时成交价）
        price = int(trade_val)
        is_realtime = True
    elif close_val > 0:
        # 收盘后：取close（收盘价）
        price = int(close_val)
        is_realtime = False
    else:
        # 都没有（极端情况），用昨收
        price = int(float(row["preclose"]))
        is_realtime = False

    high = int(float(row["high"]))
    low = int(float(row["low"]))
    open_price = int(float(row["open"]))
    volume = int(float(row["volume"]))
    position = int(float(row["position"]))
    pre_close = int(float(row["preclose"]))
    tick_time = str(row["ticktime"])
    trade_date = str(row["tradedate"])

    # 涨跌额和涨跌幅
    change = price - pre_close
    change_pct = (change / pre_close * 100) if pre_close > 0 else 0

    status = "盘中实时" if is_realtime else "收盘"

    return {
        "symbol": row["symbol"],
        "name": str(row["name"]),
        "price": price,
        "high": high,
        "low": low,
        "open": open_price,
        "pre_close": pre_close,
        "change": change,
        "change_pct": round(change_pct, 2),
        "volume": volume,
        "hold": position,
        "date": trade_date,
        "tick_time": tick_time,
        "status": status,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "sina_realtime",
    }


def save_price(data):
    """保存行情数据到 price.json"""
    os.makedirs(os.path.dirname(PRICE_FILE), exist_ok=True)
    with open(PRICE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    chg_str = f"{'+' if data['change'] >= 0 else ''}{data['change']}" 
    print(f"✅ 行情已更新: {PRICE_FILE}")
    print(f"   合约: {data['name']} ({data['symbol']})")
    print(f"   最新: ¥{data['price']:,}/吨 ({chg_str}, {data['change_pct']:+.2f}%)")
    print(f"   时间: {data['date']} {data['tick_time']} [{data['status']}]")
    print(f"   来源: {data['source']}")


def main():
    try:
        print("⏳ 正在获取碳酸锂期货实时行情...")
        data = fetch_lc_price()
        save_price(data)
    except Exception as e:
        print(f"❌ 行情更新失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
