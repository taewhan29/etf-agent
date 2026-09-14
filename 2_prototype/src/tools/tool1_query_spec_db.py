# -*- coding: utf-8 -*-
"""[도구 1] ETF 기본 스펙 및 7대 정량지표 조회 모듈 (Query_Spec_DB)"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "etf_spec.db")

def get_7_quantitative_indicators(tickers: list) -> dict:
    if not tickers:
        return {"status": "ERROR", "message": "조회할 티커가 지정되지 않았습니다."}

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    records = []
    for ticker in tickers:
        cur.execute("""
            SELECT ticker, name, category, underlying_index, ter, management_fee, distribution_cycle, aum
            FROM etf_spec
            WHERE ticker = ?
        """, (ticker,))
        row = cur.fetchone()
        if row:
            records.append({
                "ticker": row[0],
                "name": row[1],
                "category": row[2],
                "underlying_index": row[3],
                "ter": row[4],
                "management_fee": row[5],
                "distribution_cycle": row[6],
                "aum": row[7]
            })
            
    conn.close()

    if not records:
        return {"status": "ERROR", "message": "DB에서 해당 종목 정보를 찾을 수 없습니다."}

    if len(records) == 1:
        r = records[0]
        output_text = (
            f"[{r['name']} ({r['ticker']})] 정량 지표 개요\n\n"
            f"- 공식 종목명: {r['name']} (종목코드: {r['ticker']})\n"
            f"- 자산군 및 기초지수: {r['category']} 자산군 / {r['underlying_index']} 지수 추종\n"
            f"- 실질 총보수율(TER): 연 {r['ter']}%\n"
            f"- 분배금 지급주기: {r['distribution_cycle']}\n"
            f"- 순자산총액(AUM): {r['aum']}\n\n"
            f"출처: 한국투자신탁운용 정형 DB"
        )
        return {"status": "SUCCESS", "mode": "SINGLE", "records": records, "text": output_text}

    else:
        output_text = "[ACE ETF 7대 정량 지표 비교 표]\n\n"
        output_text += "| 항목 | " + " | ".join([r['name'] for r in records]) + " |\n"
        output_text += "| :--- | " + " | ".join([":---:" for _ in records]) + " |\n"
        output_text += "| 종목코드 | " + " | ".join([r['ticker'] for r in records]) + " |\n"
        output_text += "| 자산군 분류 | " + " | ".join([r['category'] for r in records]) + " |\n"
        output_text += "| 기초지수 | " + " | ".join([r['underlying_index'] for r in records]) + " |\n"
        output_text += "| 총보수율(TER) | " + " | ".join([f"연 {r['ter']}%" for r in records]) + " |\n"
        output_text += "| 분배금 지급주기 | " + " | ".join([r['distribution_cycle'] for r in records]) + " |\n"
        output_text += "| 순자산총액(AUM) | " + " | ".join([r['aum'] for r in records]) + " |\n\n"
        output_text += "출처: 한국투자신탁운용 투자설명서"
        return {"status": "SUCCESS", "mode": "COMPARISON", "records": records, "text": output_text}
