# -*- coding: utf-8 -*-
"""[도구 3] 투자 보수 비용 시뮬레이션 모듈 (Math_Engine_Simulator)"""
import os
import re
import sqlite3
from decimal import Decimal

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "etf_spec.db")

def parse_amount_and_period(query: str):
    amount = 10000000
    period = 3.0
    period_str = "3년"

    billion_match = re.search(r"(\d+(?:\.\d+)?)\s*억", query)
    ten_million_match = re.search(r"(\d+)\s*천\s*만", query)
    ten_thousand_match = re.search(r"(\d+)\s*만", query)
    raw_number_match = re.search(r"(\d{1,3}(?:,\d{3})+|\d+)\s*원", query)

    if billion_match:
        amount = int(float(billion_match.group(1)) * 100000000)
    elif ten_million_match:
        amount = int(ten_million_match.group(1)) * 10000000
    elif ten_thousand_match:
        amount = int(ten_thousand_match.group(1)) * 10000
    elif raw_number_match:
        raw_str = raw_number_match.group(1).replace(",", "")
        if int(raw_str) >= 10000:
            amount = int(raw_str)

    month_match = re.search(r"(\d+)\s*개월", query)
    year_match = re.search(r"(\d+)\s*년", query)

    if month_match:
        months = int(month_match.group(1))
        period = months / 12.0
        period_str = f"{months}개월"
    elif year_match:
        years = int(year_match.group(1))
        period = float(years)
        period_str = f"{years}년"

    return amount, period, period_str

def calculate_fee_simulation(tickers: list, query: str = "") -> dict:
    if not tickers:
        return {"status": "ERROR", "message": "연산할 종목 티커가 전달되지 않았습니다."}

    amount_krw, period_years, period_str = parse_amount_and_period(query)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    records = []
    for ticker in tickers:
        cur.execute("SELECT ticker, name, ter FROM etf_spec WHERE ticker = ?", (ticker,))
        row = cur.fetchone()
        if row:
            records.append({
                "ticker": row[0],
                "name": row[1],
                "ter": Decimal(str(row[2]))
            })

    conn.close()

    if not records:
        return {"status": "ERROR", "message": "DB에서 해당 종목 수수료 데이터를 찾지 못했습니다."}

    principal = Decimal(str(amount_krw))
    years = Decimal(str(period_years))

    if len(records) == 1:
        r = records[0]
        total_cost = principal * (r["ter"] / Decimal("100")) * years
        cost_int = int(total_cost)

        response_text = (
            f"[{r['name']} ({r['ticker']})] 투자 보수 비용 시뮬레이션 결과\n\n"
            f"1. 투자 원금: {amount_krw:,} 원\n"
            f"2. 투자 기간: {period_str}\n"
            f"3. 적용 총보수율(TER): 연 {r['ter']}%\n"
            f"4. 예상 누적 총 보수 비용: 약 {cost_int:,} 원"
        )
        return {
            "status": "SUCCESS",
            "mode": "SINGLE",
            "amount": amount_krw,
            "period": period_str,
            "total_cost": cost_int,
            "text": response_text
        }

    else:
        results_list = []
        for r in records:
            cost = principal * (r["ter"] / Decimal("100")) * years
            results_list.append({
                "ticker": r["ticker"],
                "name": r["name"],
                "ter": r["ter"],
                "cost": int(cost)
            })

        # 보수 비용 기준 오름차순 정렬
        results_list.sort(key=lambda x: x["cost"])

        if len(results_list) == 2:
            diff_cost = abs(results_list[0]["cost"] - results_list[1]["cost"])
            diff_text = f"예상 수수료 차액: 약 {diff_cost:,} 원"
        else:
            diff_cost = results_list[-1]["cost"] - results_list[0]["cost"]
            diff_text = f"최대 수수료 차액 ({results_list[-1]['name']} 대비 {results_list[0]['name']}): 약 {diff_cost:,} 원 절감"

        response_text = (
            f"[ACE ETF 장기 보유 수수료 비용 비교 시뮬레이션]\n\n"
            f"설정 조건: 투자원금 {amount_krw:,} 원 / 보유기간 {period_str}\n\n"
        )
        for idx, item in enumerate(results_list, 1):
            response_text += f"{idx}. {item['name']} (TER 연 {item['ter']}%): 예상 누적 보수 약 {item['cost']:,} 원\n"

        response_text += f"\n{diff_text}"

        return {
            "status": "SUCCESS",
            "mode": "COMPARISON",
            "amount": amount_krw,
            "period": period_str,
            "diff_cost": diff_cost,
            "details": results_list,
            "text": response_text
        }
