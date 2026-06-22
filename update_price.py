#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锂辉石计价器 - 碳酸锂期货行情自动更新
数据源：新浪财经（AKShare futures_main_sina）
合约：LC0（碳酸锂连续主力合约）
输出：data/price.json

用法：
  python update_price.py           # 手动更新
  # 或通过 Windows 任务计划定时执行（建议每个交易日 15:15 执行一次）
"""

import json
import os
import sys
from datetime import datetime

import akshare as ak


PRICE_FILE = os.path.join(os.path.dirname(__file__), "data", "price.json")
SYMBOL = "LC0"  # 广期所碳酸锂连续主力合约


def fetch_lc_price():
    """从新浪财经获取碳酸锂期货主力合约最新行情"""
    df = ak.futures_main_sina(symbol=SYMBOL, start_date="20200101", end_date="22220101")
    if df.empty:
        raise ValueError(f"未获取到 {SYMBOL} 行情数据")

    latest = df.iloc[-1]
    price = int(latest["收盘价"])
    date_str = str(latest["日期"])[:10]
    high = int(latest["最高价"])
    low = int(latest["最低价"])
    open_price = int(latest["开盘价"])
    volume = int(latest["成交量"])
    hold = int(latest["持仓量"])

    return {
        "symbol": SYMBOL,
        "price": price,
        "date": date_str,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "high": high,
        "low": low,
        "open": open_price,
        "volume": volume,
        "hold": hold,
        "source": "akshare_sina",
    }


def save_price(data):
    """保存行情数据到 price.json"""
    os.makedirs(os.path.dirname(PRICE_FILE), exist_ok=True)
    with open(PRICE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 行情已更新: {PRICE_FILE}")
    print(f"   合约: {data['symbol']}")
    print(f"   收盘: ¥{data['price']:,}/吨")
    print(f"   日期: {data['date']}")
    print(f"   来源: {data['source']}")


def main():
    try:
        print("⏳ 正在获取碳酸锂期货行情...")
        data = fetch_lc_price()
        save_price(data)
    except Exception as e:
        print(f"❌ 行情更新失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
