# -*- coding: utf-8 -*-
"""
[1단계] 질의 정제 및 엔티티/의도 파악 경량 모듈 (개정 완결본)
- 텍스트 기본 정제 및 오타 자동 보정 (difflib)
- 복수 종목 티커 식별 지원 (tickers 리스트 반환)
- 4대 도구(도구 1~4)와 1:1 매핑되는 정밀 의도(Intent) 파악
- 이모티콘 및 아스테리스크(*) 완벽 제거
"""
import os
import re
import sqlite3
import difflib
from contextlib import closing
from tools.tool4_consulting_flow import (  # type: ignore
    GUARDRAIL_PATTERNS,
    AMBIGUOUS_CATEGORY_MAP,
    REFERRAL_PATTERNS,
    LIST_PATTERNS,
    GREETING_PATTERNS,
    COMPETITOR_PATTERNS,
    DOMAIN_FAQ_PATTERNS
)

from config.paths import DB_PATH

def refine_query(user_input: str) -> dict:
    """
    1단계 질의 정제 및 4대 도구 연동 전처리 핵심 함수
    """
    # 0. 텍스트 기본 정제
    cleaned = re.sub(r"[^\w\s%&.-]", "", user_input).strip()
    words = cleaned.split()
    cleaned_lower = cleaned.lower()

    # 1. 도구 4 관련 사전 감지 (금소법 차단 / 고객센터 연계 / 인사말 / 타사 안내 / FAQ / 전체 ETF 목록 / 모호성 역질문)
    for pattern in GUARDRAIL_PATTERNS:
        if re.search(pattern, cleaned):
            return {
                "raw_query": user_input,
                "cleaned_query": cleaned,
                "tickers": [],
                "official_names": [],
                "intent": "TOOL4_GUARDRAIL_BLOCKED",
                "matched_alias": None
            }

    for pattern in REFERRAL_PATTERNS:
        if re.search(pattern, cleaned):
            return {
                "raw_query": user_input,
                "cleaned_query": cleaned,
                "tickers": [],
                "official_names": [],
                "intent": "TOOL4_CUSTOMER_REFERRAL",
                "matched_alias": None
            }

    for pattern in GREETING_PATTERNS:
        if re.search(pattern, cleaned_lower):
            return {
                "raw_query": user_input,
                "cleaned_query": cleaned,
                "tickers": [],
                "official_names": [],
                "intent": "TOOL4_GREETING",
                "matched_alias": None
            }

    for pattern in COMPETITOR_PATTERNS:
        if re.search(pattern, cleaned_lower):
            return {
                "raw_query": user_input,
                "cleaned_query": cleaned,
                "tickers": [],
                "official_names": [],
                "intent": "TOOL4_COMPETITOR_GUIDE",
                "matched_alias": None
            }

    for faq_key, patterns in DOMAIN_FAQ_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, cleaned_lower):
                return {
                    "raw_query": user_input,
                    "cleaned_query": cleaned,
                    "tickers": [],
                    "official_names": [],
                    "intent": "TOOL4_DOMAIN_FAQ",
                    "matched_alias": faq_key
                }

    for pattern in LIST_PATTERNS:
        if re.search(pattern, cleaned_lower):
            return {
                "raw_query": user_input,
                "cleaned_query": cleaned,
                "tickers": [],
                "official_names": [],
                "intent": "TOOL4_ALL_ETF_LIST",
                "matched_alias": None
            }

    for category_key in AMBIGUOUS_CATEGORY_MAP.keys():
        if cleaned_lower == category_key or cleaned_lower == f"{category_key} etf" or cleaned_lower == f"{category_key} 추천":
            return {
                "raw_query": user_input,
                "cleaned_query": cleaned,
                "tickers": [],
                "official_names": [],
                "intent": "TOOL4_AMBIGUOUS_CLARIFICATION",
                "matched_alias": category_key
            }

    # 2. DB에서 별칭 사전을 통한 복수 종목 티커 및 오타 보정 파싱
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT alias, ticker FROM etf_alias")
        alias_rows = cur.fetchall()

        alias_dict = {row[0]: row[1] for row in alias_rows}
        all_aliases = list(alias_dict.keys())

        found_tickers = []
        matched_aliases = []

        has_compare_keyword = any(k in cleaned_lower for k in ["비교", "차이", "대조", "어느 게 더", "어떤 게 더", "뭐가 더"])

        # 2-1. 복수 종목 키워드 대조 (긴 별칭 우선 매칭)
        sorted_aliases = sorted(alias_dict.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            if alias in cleaned_lower:
                ticker = alias_dict[alias]
                if ticker not in found_tickers:
                    found_tickers.append(ticker)
                    matched_aliases.append(alias)

        # 2-2. 매칭 실패 시 단어 단위 오타 보정 (difflib)
        if not found_tickers:
            for word in words:
                word_lower = word.lower()
                matches = difflib.get_close_matches(word_lower, all_aliases, n=1, cutoff=0.6)
                if matches:
                    matched_alias = matches[0]
                    ticker = alias_dict[matched_alias]
                    if ticker not in found_tickers:
                        found_tickers.append(ticker)
                        matched_aliases.append(matched_alias)
                    break

        # 2-3. 비교 질문 시 카테고리 감지 처리 및 미지정 역질문 분기
        if has_compare_keyword:
            # 특정 종목이 2개 이상 매칭되지 않은 경우
            if len(found_tickers) < 2:
                # 카테고리 키워드가 있는지 확인
                detected_category_tickers = []
                for cat_key, etf_names in AMBIGUOUS_CATEGORY_MAP.items():
                    if cat_key in cleaned_lower:
                        # 해당 카테고리의 대표 상품 티커 조회
                        for name in etf_names:
                            cur.execute("SELECT ticker FROM etf_spec WHERE name=?", (name,))
                            row = cur.fetchone()
                            if row and row[0] not in detected_category_tickers:
                                detected_category_tickers.append(row[0])
                        break
                
                if detected_category_tickers:
                    found_tickers = detected_category_tickers
                elif len(found_tickers) < 2:
                    # 카테고리도, 2개 이상 종목도 없는 비교 질문 -> 역질문 라우팅 (with 블록 자동 close)
                    return {
                        "raw_query": user_input,
                        "cleaned_query": cleaned,
                        "tickers": [],
                        "official_names": [],
                        "intent": "TOOL4_COMPARISON_CLARIFICATION",
                        "matched_alias": None
                    }

        # 2-4. 식별 실패 시 범용 추천/카테고리 감지 처리 및 기본 대표 종목 fallback
        if not found_tickers:
            for cat_key in AMBIGUOUS_CATEGORY_MAP.keys():
                if cat_key in cleaned_lower or "추천" in cleaned_lower:
                    return {
                        "raw_query": user_input,
                        "cleaned_query": cleaned,
                        "tickers": [],
                        "official_names": [],
                        "intent": "TOOL4_AMBIGUOUS_CLARIFICATION",
                        "matched_alias": cat_key if cat_key in cleaned_lower else "미국주식"
                    }
            found_tickers = ["360200"]

        # 식별된 티커들의 공식 종목명 조회
        official_names = []
        for ticker in found_tickers:
            cur.execute("SELECT name FROM etf_spec WHERE ticker=?", (ticker,))
            row = cur.fetchone()
            if row:
                official_names.append(row[0])

    # 3. 질문 의도(Intent) 4대 도구 라우팅 매핑
    intent = "TOOL1_SPEC_LOOKUP"
    if any(k in cleaned for k in ["비용", "수수료", "계산", "얼마", "시뮬레이션"]):
        intent = "TOOL3_MATH_SIMULATION"
    elif any(k in cleaned for k in ["위험", "설명서", "공시", "개요", "특징", "전략", "지수"]):
        intent = "TOOL2_RAG_SEARCH"

    return {
        "raw_query": user_input,
        "cleaned_query": cleaned,
        "tickers": found_tickers,
        "official_names": official_names,
        "intent": intent,
        "matched_alias": ", ".join(matched_aliases) if matched_aliases else None
    }


if __name__ == "__main__":
    test_queries = [
        "S&P500이랑 나스닥100 보수율 비교해줘",
        "스엔피300 수수료 얼마야",
        "금현믈 주요 투자 위험 알려줘",
        "원금보장 되는 상품 있나요",
        "미국주식 etf",
        "상속세 절세 팁 알려줘"
    ]

    print("=== [개정된 1단계 모듈 복수 종목 & 4대 도구 라우팅 검증] ===")
    for q in test_queries:
        res = refine_query(q)
        print(f"질문: '{res['raw_query']}'")
        print(f"  티커리스트: {res['tickers']} ({res['official_names']})")
        print(f"  의도 라우팅: {res['intent']}\n")
