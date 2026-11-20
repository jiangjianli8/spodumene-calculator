#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""六计算器每日健康巡检

检查 6 个计算器仓库的运行健康，任一异常则退出码 1（触发 workflow 失败 → 开 Issue）。

检查项：
1. 每个仓库「最近一次工作流运行」是否为 success
2. data/price.json（或最新价格文件）的数据日期是否新鲜（工作日超过 1 天即告警）
3. 线上页面是否返回 HTTP 200

用法：
  python health_check_all.py            # 巡检，异常退出 1
  python health_check_all.py --verbose  # 打印全部明细
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sys

import requests

GH_API = "https://api.github.com"
OWNER = "jiangjianli8"

# 仓库 → 线上地址
REPOS = {
    "spodumene-calculator": "https://jiangjianli8.github.io/spodumene-calculator/",
    "nickel-calculator":    "https://jiangjianli8.github.io/nickel-calculator/",
    "tin-calculator":       "https://jiangjianli8.github.io/tin-calculator/",
    "znpb-calculator":      "https://jiangjianli8.github.io/znpb-calculator/",
    "copper-calculator":    "https://jiangjianli8.github.io/copper-calculator/",
    "tantalum-calculator":  "https://jiangjianli8.github.io/tantalum-calculator/",
}

SESSION = requests.Session()
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
if TOKEN:
    SESSION.headers["Authorization"] = f"token {TOKEN}"
SESSION.headers["Accept"] = "application/vnd.github+json"
SESSION.headers["User-Agent"] = "klt-health-check"


def gh(path: str, timeout: int = 30):
    r = SESSION.get(GH_API + path, timeout=timeout)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    return r.json(), None


def check_workflow(repo: str):
    """最近一次工作流运行是否成功"""
    data, err = gh(f"/repos/{OWNER}/{repo}/actions/runs?per_page=1")
    if err:
        return False, f"无法读取 Actions：{err}"
    runs = (data or {}).get("workflow_runs") or []
    if not runs:
        return False, "从未运行过工作流"
    run = runs[0]
    concl = run.get("conclusion") or run.get("status")
    when = (run.get("created_at") or "")[:19].replace("T", " ")
    if concl != "success":
        return False, f"最近一次运行 = {concl}（{when}）"
    return True, f"最近运行 success（{when}）"


def fetch_price_json(repo: str):
    """读取 data/price.json（取不到则返回 None）"""
    for path in ("data/price.json", "price.json"):
        data, _ = gh(f"/repos/{OWNER}/{repo}/contents/{path}")
        if data and data.get("content"):
            import base64
            try:
                txt = base64.b64decode(data["content"]).decode("utf-8", "replace")
                return json.loads(txt)
            except Exception:
                return None
    return None


def check_data_freshness(repo: str):
    """数据新鲜度：非交易日不判；交易日超过 1 天未更新即告警"""
    pj = fetch_price_json(repo)
    if not pj:
        return True, "无 price.json（跳过新鲜度检查）"

    raw = pj.get("updated_at") or pj.get("date") or ""
    if not raw:
        return True, "price.json 无时间字段（跳过）"

    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(raw))
    if not m:
        return True, f"时间格式无法解析：{raw}"

    data_date = datetime.date.fromisoformat(m.group(1))
    today = datetime.date.today()

    # 上周五（含）之前的数据，跨周末不算陈旧
    days_back = (today - data_date).days
    # 计算中间跨了几个工作日
    workdays = 0
    d = data_date
    while d < today:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            workdays += 1

    if workdays >= 2:
        return False, f"数据停在 {data_date}（已跨 {workdays} 个工作日）"
    return True, f"数据日期 {data_date}（{days_back} 天前，新鲜度 OK）"


def check_page(repo: str, url: str):
    try:
        r = SESSION.get(url, timeout=30, allow_redirects=True)
        if r.status_code == 200:
            return True, "页面 200"
        return False, f"页面 HTTP {r.status_code}"
    except Exception as e:
        return False, f"页面访问异常：{type(e).__name__}"


def main() -> int:
    verbose = "--verbose" in sys.argv
    problems = []

    print("=" * 68)
    print("六计算器每日巡检 · %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 68)

    for repo, url in REPOS.items():
        print("\n【%s】" % repo)
        ok_all = True
        for label, fn in (
            ("工作流", lambda: check_workflow(repo)),
            ("数据新鲜度", lambda: check_data_freshness(repo)),
            ("线上页面", lambda: check_page(repo, url)),
        ):
            try:
                ok, msg = fn()
            except Exception as e:
                ok, msg = False, f"{type(e).__name__}: {str(e)[:120]}"
            flag = "OK  " if ok else "FAIL"
            print("  [%s] %-10s %s" % (flag, label, msg))
            if not ok:
                ok_all = False
                problems.append(f"{repo} · {label}：{msg}")
        if ok_all:
            print("  → 全部正常")

    print("\n" + "=" * 68)
    if problems:
        print("发现 %d 处问题：" % len(problems))
        for p in problems:
            print("  ✗ " + p)
        print("\nACTION_REQUIRED=1")
        return 1

    print("6 个仓库全部正常")
    return 0


if __name__ == "__main__":
    sys.exit(main())
