# -*- coding: utf-8 -*-
"""
[2단계] 의도 및 도구 선택 오케스트레이터 (Step 2: Tool Selector)
- LangChain Tool Calling 표준 JSON Schema 구조 준수
- 1단계 정제 결과를 바탕으로 단일/다중 툴 호출(Multi-Tool Calling) 계획 수립
- 불분명한 질문 및 카테고리 질의 역질문 동적 분기
- 이모티콘 및 아스테리스크(*) 완벽 제거
"""
import os
import sys

# 상위 경로 모듈 참조 설정
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from pipeline.step1_query_refiner import refine_query


def select_tools(refined_info: dict) -> dict:
    """
    1단계 결과를 전달받아 LangChain Tool Calling 스펙의 실행 지시서(Execution Plan)를 생성
    """
    raw_query = refined_info.get("raw_query", "")
    cleaned_query = refined_info.get("cleaned_query", "")
    tickers = refined_info.get("tickers", [])
    intent = refined_info.get("intent", "")
    matched_alias = refined_info.get("matched_alias")

    tool_calls = []

    # 1. 사전 금소법 차단 / 고객센터 연계 / 역질문 처리 (도구 4 연동)
    if intent == "TOOL4_GUARDRAIL_BLOCKED":
        tool_calls.append({
            "tool_name": "tool4_consulting_flow",
            "args": {
                "sub_action": "guardrail_block",
                "query": raw_query
            }
        })
        return {
            "query": raw_query,
            "tickers": tickers,
            "routing_mode": "GUARDRAIL_BLOCK",
            "tool_calls": tool_calls
        }

    if intent == "TOOL4_CUSTOMER_REFERRAL":
        tool_calls.append({
            "tool_name": "tool4_consulting_flow",
            "args": {
                "sub_action": "customer_referral",
                "query": raw_query
            }
        })
        return {
            "query": raw_query,
            "tickers": tickers,
            "routing_mode": "CUSTOMER_REFERRAL",
            "tool_calls": tool_calls
        }

    if intent == "TOOL4_AMBIGUOUS_CLARIFICATION":
        tool_calls.append({
            "tool_name": "tool4_consulting_flow",
            "args": {
                "sub_action": "clarification_options",
                "category": matched_alias
            }
        })
        return {
            "query": raw_query,
            "tickers": tickers,
            "routing_mode": "CLARIFICATION_REQUIRED",
            "tool_calls": tool_calls
        }

    if intent == "TOOL4_ALL_ETF_LIST":
        tool_calls.append({
            "tool_name": "tool4_consulting_flow",
            "args": {
                "sub_action": "all_etf_list"
            }
        })
        return {
            "query": raw_query,
            "tickers": tickers,
            "routing_mode": "ALL_ETF_LIST",
            "tool_calls": tool_calls
        }

    if intent == "TOOL4_COMPARISON_CLARIFICATION":
        tool_calls.append({
            "tool_name": "tool4_consulting_flow",
            "args": {
                "sub_action": "comparison_clarification"
            }
        })
        return {
            "query": raw_query,
            "tickers": tickers,
            "routing_mode": "COMPARISON_CLARIFICATION_REQUIRED",
            "tool_calls": tool_calls
        }

    if intent == "TOOL4_GREETING":
        tool_calls.append({
            "tool_name": "tool4_consulting_flow",
            "args": {
                "sub_action": "greeting"
            }
        })
        return {
            "query": raw_query,
            "tickers": tickers,
            "routing_mode": "GREETING_GUIDE",
            "tool_calls": tool_calls
        }

    if intent == "TOOL4_COMPETITOR_GUIDE":
        tool_calls.append({
            "tool_name": "tool4_consulting_flow",
            "args": {
                "sub_action": "competitor_guide"
            }
        })
        return {
            "query": raw_query,
            "tickers": tickers,
            "routing_mode": "COMPETITOR_GUIDE",
            "tool_calls": tool_calls
        }

    if intent == "TOOL4_DOMAIN_FAQ":
        tool_calls.append({
            "tool_name": "tool4_consulting_flow",
            "args": {
                "sub_action": "domain_faq",
                "category": matched_alias
            }
        })
        return {
            "query": raw_query,
            "tickers": tickers,
            "routing_mode": "DOMAIN_FAQ",
            "tool_calls": tool_calls
        }

    # 2. 복합 질의 (Multi-Tool Calling) 및 단일 질의 동적 판단
    has_math_keywords = any(k in cleaned_query for k in ["비용", "수수료", "계산", "얼마", "시뮬레이션"])
    has_rag_keywords = any(k in cleaned_query for k in ["위험", "설명서", "공시", "개요", "특징", "전략", "지수"])
    has_spec_keywords = any(k in cleaned_query for k in ["스펙", "보수율", "ter", "분배", "비교", "기초지수", "aum", "정보"])

    # 2-1. 복합 질의 1: 수수료 연산 + PDF RAG 공시 탐색 (Multi-Tool)
    if has_math_keywords and has_rag_keywords:
        tool_calls.append({
            "tool_name": "tool3_math_engine",
            "args": {
                "tickers": tickers,
                "query": cleaned_query
            }
        })
        tool_calls.append({
            "tool_name": "tool2_search_pdf_rag",
            "args": {
                "query": cleaned_query
            }
        })
        routing_mode = "MULTI_TOOL_MATH_RAG"

    # 2-2. 복합 질의 2: 정량 스펙 비교 + PDF RAG 공시 탐색 (Multi-Tool)
    elif has_spec_keywords and has_rag_keywords:
        tool_calls.append({
            "tool_name": "tool1_query_spec_db",
            "args": {
                "tickers": tickers
            }
        })
        tool_calls.append({
            "tool_name": "tool2_search_pdf_rag",
            "args": {
                "query": cleaned_query
            }
        })
        routing_mode = "MULTI_TOOL_SPEC_RAG"

    # 2-3. 단일 질의: 수수료 연산 (Math Engine)
    elif intent == "TOOL3_MATH_SIMULATION" or has_math_keywords:
        tool_calls.append({
            "tool_name": "tool3_math_engine",
            "args": {
                "tickers": tickers,
                "query": cleaned_query
            }
        })
        routing_mode = "SINGLE_TOOL_MATH"

    # 2-4. 단일 질의: PDF RAG 공시 탐색
    elif intent == "TOOL2_RAG_SEARCH" or has_rag_keywords:
        tool_calls.append({
            "tool_name": "tool2_search_pdf_rag",
            "args": {
                "query": cleaned_query
            }
        })
        routing_mode = "SINGLE_TOOL_RAG"

    # 2-5. 기본 정량 지표 조회 (Default Spec Look-up)
    else:
        tool_calls.append({
            "tool_name": "tool1_query_spec_db",
            "args": {
                "tickers": tickers
            }
        })
        routing_mode = "SINGLE_TOOL_SPEC"

    return {
        "query": raw_query,
        "tickers": tickers,
        "routing_mode": routing_mode,
        "tool_calls": tool_calls
    }


if __name__ == "__main__":
    test_queries = [
        "S&P500이랑 나스닥100 보수율 비교해줘",
        "ACE 미국S&P500 1천만원 3년 수수료 계산해주고 운용전략이랑 투자위험도 같이 알려줘",
        "금현물 주요 투자 위험 알려줘",
        "원금보장 되는 상품 있나요",
        "미국주식 etf",
        "상속세 절세 팁 알려줘"
    ]

    print("=== [2단계 의도 및 도구 선택 오케스트레이터 검증] ===")
    for q in test_queries:
        ref_info = refine_query(q)
        plan = select_tools(ref_info)
        print(f"질문: '{plan['query']}'")
        print(f"  라우팅 모드: {plan['routing_mode']}")
        print(f"  툴콜 수: {len(plan['tool_calls'])}개")
        for idx, tc in enumerate(plan['tool_calls'], 1):
            print(f"    [Tool Call {idx}] {tc['tool_name']} -> args: {tc['args']}")
        print()
