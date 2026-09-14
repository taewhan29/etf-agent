# -*- coding: utf-8 -*-
"""
[3단계] 전용 도구 실행 엔진 (Step 3: Tool Executor)
- LLM 추론을 전면 배제하고 자체 구축 3대 데이터 엔진 및 규제 모듈 가동
- 2단계 Tool Calling 지시서(plan_info)를 수신하여 단일/다중 도구 순차 및 병렬 수집 실행
- 100% 원천 데이터 무결성 보장 및 안정적인 에러 핸들링
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
from pipeline.step2_tool_selector import select_tools
from tools.tool1_query_spec_db import get_7_quantitative_indicators
from tools.tool2_search_pdf_rag import search_pdf_rag
from tools.tool3_math_engine import calculate_fee_simulation
from tools.tool4_consulting_flow import handle_consulting_flow

# 4대 전용 도구 레지스트리
TOOL_REGISTRY = {
    "tool1_query_spec_db": get_7_quantitative_indicators,
    "tool2_search_pdf_rag": search_pdf_rag,
    "tool3_math_engine": calculate_fee_simulation,
    "tool4_consulting_flow": handle_consulting_flow
}

def execute_tools(plan_info: dict) -> dict:
    """
    2단계 실행 지시서(plan_info)를 받아 4대 전용 도구를 실행하고 원천 결과를 수집
    """
    query = plan_info.get("query", "")
    tickers = plan_info.get("tickers", [])
    routing_mode = plan_info.get("routing_mode", "SINGLE_TOOL_SPEC")
    tool_calls = plan_info.get("tool_calls", [])

    execution_results = []

    for idx, tool_call in enumerate(tool_calls, 1):
        tool_name = tool_call.get("tool_name")
        args = tool_call.get("args", {})

        target_func = TOOL_REGISTRY.get(tool_name)
        if not target_func:
            execution_results.append({
                "call_index": idx,
                "tool_name": tool_name,
                "status": "ERROR",
                "message": f"등록되지 않은 도구명입니다: {tool_name}",
                "result": None
            })
            continue

        try:
            # 3대 핵심 데이터 엔진 및 규제 모듈 실제 호출
            tool_output = target_func(**args)
            execution_results.append({
                "call_index": idx,
                "tool_name": tool_name,
                "status": tool_output.get("status", "SUCCESS"),
                "args": args,
                "result": tool_output
            })
        except Exception as e:
            execution_results.append({
                "call_index": idx,
                "tool_name": tool_name,
                "status": "EXCEPTION",
                "message": f"도구 실행 중 예외 발생: {str(e)}",
                "result": None
            })

    return {
        "query": query,
        "tickers": tickers,
        "routing_mode": routing_mode,
        "total_calls": len(tool_calls),
        "execution_results": execution_results
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

    print("=== [3단계 전용 도구 실행 엔진 데이터 수집 검증] ===")
    for q in test_queries:
        ref_info = refine_query(q)
        plan_info = select_tools(ref_info)
        exec_info = execute_tools(plan_info)

        print(f"\n질문: '{exec_info['query']}'")
        print(f"  라우팅 모드: {exec_info['routing_mode']}")
        print(f"  실행된 도구 수: {exec_info['total_calls']}개")

        for res in exec_info["execution_results"]:
            tname = res["tool_name"]
            status = res["status"]
            output = res["result"]
            print(f"    - [도구 {res['call_index']}] {tname} (Status: {status})")
            if output and "text" in output:
                preview = output["text"].replace("\n", " ")[:90]
                print(f"      결과 텍스트: {preview}...")
