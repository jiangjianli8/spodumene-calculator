#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锂辉石计价器 - 碳酸锂期货行情自动更新
数据源：新浪财经实时行情（AKShare futures_zh_realtime）
合约：LC0（碳酸锂连续主力合约）
输出：data/price.json

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
    # 优先使用实时接口（交易时段可用，盘中秒级更新）
    df = ak.futures_zh_realtime(symbol=SYMBOL)

    if df.empty:
        raise ValueError(f"未获取到 {SYMBOL} 实时行情数据")

    # 找到主力合约（LC0 连续合约，成交量最大）
    main_row = df[df["symbol"] == "LC0"]
    if main_row.empty:
        # 如果没有LC0，取成交量最大的合约
        main_row = df[df["volume"] == df["volume"].max()]

    row = main_row.iloc[0]

    price = int(float(row["close"]))        # 最新价（收盘价/最新成交价）
    high = int(float(row["high"]))           # 最高价
    low = int(float(row["low"]))             # 最低价
    open_price = int(float(row["open"]))     # 开盘价
    volume = int(float(row["volume"]))       # 成交量
    position = int(float(row["position"]))   # 持仓量
    pre_close = int(float(row["preclose"]))  # 昨收价
    tick_time = str(row["ticktime"])         # 行情时间
    trade_date = str(row["tradedate"])       # 交易日期

    return {
        "symbol": row["symbol"],
        "name": str(row["name"]),
        "price": price,
        "high": high,
        "low": low,
        "open": open_price,
        "pre_close": pre_close,
        "volume": volume,
        "hold": position,
        "date": trade_date,
        "tick_time": tick_time,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "sina_realtime",
    }


def save_price(data):
    """保存行情数据到 price.json"""
    os.makedirs(os.path.dirname(PRICE_FILE), exist_ok=True)
    with open(PRICE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 行情已更新: {PRICE_FILE}")
    print(f"   合约: {data['name']} ({data['symbol']})")
    print(f"   最新: ¥{data['price']:,}/吨")
    print(f"   日期: {data['date']} {data['tick_time']}")
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
