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


# 每个仓库的「行情更新」工作流文件路径。
# 必须按路径精确锁定，原因有二：
#   1. 巡检自身（daily-health-check.yml）也在 spodumene 里，按名字取最新会读到自己
#   2. pages-build-deployment 是 Pages 部署副产品，它成功不代表行情抓取成功，
#      若把它当「最近一次运行」，行情更新挂了也会假绿
MARKET_WORKFLOW_PATHS = {
    "spodumene-calculator": ".github/workflows/update_price.yml",
    "nickel-calculator":    ".github/workflows/update-nickel-price.yml",
    "tin-calculator":       ".github/workflows/update-price.yml",
    "znpb-calculator":      ".github/workflows/update-prices.yml",
    "copper-calculator":    ".github/workflows/update-copper-price.yml",
    "tantalum-calculator":  ".github/workflows/update-price.yml",
}


def check_workflow(repo: str):
    """该仓库「行情更新」工作流最近一条**已完成**运行是否成功

    只看已出结论的运行：行情任务每 5 分钟一跑，随时可能撞上 in_progress，
    正在跑不算故障。
    """
    want = MARKET_WORKFLOW_PATHS.get(repo)
    if not want:
        return False, "脚本未配置该仓库的行情工作流路径"

    data, err = gh(f"/repos/{OWNER}/{repo}/actions/runs?per_page=30")
    if err:
        return False, f"无法读取 Actions：{err}"

    runs = [
        r for r in ((data or {}).get("workflow_runs") or [])
        if r.get("path") == want and r.get("conclusion")
    ]
    if not runs:
        return False, f"「{want}」无已完成运行记录"

    run = runs[0]  # 列表按时间倒序
    concl = run.get("conclusion")
    when = (run.get("created_at") or "")[:19].replace("T", " ")
    if concl != "success":
        return False, f"「{run.get('name')}」最近一次运行 = {concl}（{when}）"
    return True, f"「{run.get('name')}」success（{when}）"


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


DEFAULT_SOURCE_HINTS = ("default", "默认", "fallback")


def collect_sources(obj):
    """递归收集 price.json 里所有 source 字段（znpb 的结构是 zn/pb 子对象）"""
    found = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "source" and isinstance(v, str):
                    found.append(v)
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(obj)
    return found


def check_data_freshness(repo: str):
    """数据新鲜度：非交易日不判；交易日超过 1 天未更新即告警

    注意：只看 updated_at 会被「抓价失败写默认价 + 时间戳打当前时间」骗过去——
    所以必须先查 source / is_realtime，默认参考价一律判故障。
    """
    pj = fetch_price_json(repo)
    if not pj:
        return True, "无 price.json（跳过新鲜度检查）"

    # ① 默认价 / 非实时 检测（优先级高于时间检查）
    if pj.get("is_realtime") is False:
        return False, "数据源标记为非实时（is_realtime=false）"

    sources = collect_sources(pj)
    bad = [s for s in sources if any(h in s.lower() for h in DEFAULT_SOURCE_HINTS)]
    if bad:
        return False, "数据源是默认参考价而非实时行情：%s" % "、".join(sorted(set(bad)))

    # ② 时间新鲜度
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
