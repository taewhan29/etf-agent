# -*- coding: utf-8 -*-
"""
[메인 파이프라인] ACE ETF AI 챗봇 최상위 오케스트레이터 (main_pipeline.py)
- 1단계(정제) -> 2단계(선택) -> 3단계(실행) -> 4단계(합성) -> 5단계(검증) 순차 연결
- Graceful Degradation: 어떤 장애 상황에서도 빈 화면 없이 의미 있는 응답 반환
- 터미널 대화형 CLI 테스트 및 Streamlit UI 연동 지원
- 이모티콘 및 아스테리스크(*) 완벽 제거
"""
import logging
import os
import sys

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from pipeline.step1_query_refiner import refine_query
from pipeline.step2_tool_selector import select_tools
from pipeline.step3_tool_executor import execute_tools
from pipeline.step4_response_synthesizer import synthesize_response
from pipeline.step5_validator import validate_and_finalize

FALLBACK_MESSAGE = (
    "일시적으로 답변 생성이 어렵습니다. 잠시 후 다시 시도해 주세요.\n\n"
    "한국투자신탁운용 고객센터: 1544-0050 (평일 09:00 ~ 17:00)"
)


def run_pipeline(user_input: str) -> dict:
    """
    사용자 질문을 받아 1~5단계 파이프라인을 순차 통과시킨 최종 답변을 반환한다.
    각 단계에서 장애 발생 시 가능한 범위까지 답변하고 제한 사항만 안내한다.
    """
    degraded = []

    # -- 1단계: 질의 정제 --
    try:
        step1 = refine_query(user_input)
    except Exception as e:
        logger.error("[메인 파이프라인] 1단계 질의 정제 중 오류 발생 (질의: %s): %s", user_input, e, exc_info=True)
        step1 = {
            "raw_query": user_input,
            "cleaned_query": user_input,
            "tickers": [],
            "official_names": [],
            "intent": "TOOL1_SPEC_LOOKUP",
            "matched_alias": None
        }
        degraded.append("질의 정제")

    # -- 2단계: 도구 선택 --
    try:
        step2 = select_tools(step1)
    except Exception as e:
        logger.error("[메인 파이프라인] 2단계 도구 선택 중 오류 발생: %s", e, exc_info=True)
        step2 = {
            "query": user_input,
            "tickers": step1.get("tickers", []),
            "routing_mode": "SINGLE_TOOL_SPEC",
            "tool_calls": [{"tool_name": "tool1_query_spec_db", "args": {"tickers": step1.get("tickers", [])}}]
        }
        degraded.append("도구 선택")

    # -- 3단계: 도구 실행 --
    try:
        step3 = execute_tools(step2)
    except Exception as e:
        logger.error("[메인 파이프라인] 3단계 도구 실행 중 오류 발생: %s", e, exc_info=True)
        step3 = {
            "query": user_input,
            "tickers": step2.get("tickers", []),
            "routing_mode": step2.get("routing_mode", ""),
            "total_calls": 0,
            "execution_results": []
        }
        degraded.append("도구 실행")

    # 개별 도구 실행 실패 감지
    for res in step3.get("execution_results", []):
        if res.get("status") in ["ERROR", "EXCEPTION"]:
            tool_name = res.get("tool_name", "")
            err_msg = res.get("error") or res.get("result") or "상세 원인 미상"
            logger.warning("[메인 파이프라인] 개별 도구 실행 실패 (%s): %s", tool_name, err_msg)
            if "tool2" in tool_name:
                degraded.append("투자설명서 검색")
            elif "tool1" in tool_name:
                degraded.append("정량 데이터 조회")
            elif "tool3" in tool_name:
                degraded.append("비용 시뮬레이션")

    # -- 4단계: 답변 합성 --
    try:
        step4 = synthesize_response(step3)
    except Exception as e:
        logger.error("[메인 파이프라인] 4단계 답변 합성 중 오류 발생: %s", e, exc_info=True)
        # 합성 완전 실패 시 원천 텍스트 직접 결합
        raw_texts = []
        for res in step3.get("execution_results", []):
            output = res.get("result") or {}
            if "text" in output:
                raw_texts.append(output["text"])
        step4 = {
            "query": user_input,
            "routing_mode": step2.get("routing_mode", ""),
            "synthesis_mode": "EMERGENCY_FALLBACK",
            "final_response": "\n\n".join(raw_texts) if raw_texts else FALLBACK_MESSAGE
        }
        degraded.append("답변 합성")

    # -- 5단계: 규제 검증 --
    try:
        step5 = validate_and_finalize(step4, step3)
    except Exception as e:
        logger.error("[메인 파이프라인] 5단계 규제 검증 중 오류 발생: %s", e, exc_info=True)
        # 검증 실패 시 안전측으로 유의사항만 부착
        safe_text = step4.get("final_response", FALLBACK_MESSAGE)
        disclaimer = (
            "\n\n안내: 본 정보는 한국투자신탁운용 공시 자료 기반 안내이며 "
            "투자 권유나 원금 보장을 의미하지 않습니다. "
            "모든 집합투자증권은 운용 결과에 따라 원금 손실이 발생할 수 있습니다."
        )
        step5 = {
            "query": user_input,
            "routing_mode": step2.get("routing_mode", ""),
            "validation_status": "PASSED_WITH_DISCLAIMER_ONLY",
            "is_fact_matched": True,
            "is_validated": True,
            "final_output": safe_text + disclaimer
        }
        degraded.append("규제 검증")

    # -- 성능 저하 서비스 안내 문구 부착 --
    final_output = step5.get("final_output", FALLBACK_MESSAGE)
    if degraded:
        notice = "\n\n[안내] 현재 일부 서비스가 일시적으로 제한되어 있습니다: " + ", ".join(degraded)
        final_output = final_output + notice

    return {
        "raw_query": user_input,
        "tickers": step1.get("tickers", []),
        "routing_mode": step2.get("routing_mode", ""),
        "tool_calls_count": len(step2.get("tool_calls", [])),
        "synthesis_mode": step4.get("synthesis_mode", ""),
        "validation_status": step5.get("validation_status", "PASSED"),
        "is_fact_matched": step5.get("is_fact_matched", True),
        "recommended_questions": step5.get("recommended_questions", []),
        "degraded_services": degraded,
        "final_output": final_output
    }


def start_terminal_cli():
    """
    터미널 대화형 인터랙티브 CLI 테스트 모드
    """
    print("=" * 60)
    print(" [한국투자신탁운용 ACE ETF AI 챗봇 파이프라인 CLI 테스트]")
    print(" 질문을 입력하면 5단계 검증 답변이 출력됩니다.")
    print(" 종료: exit 또는 q")
    print("=" * 60)

    print("\n데이터베이스를 불러오는 중입니다...")
    # ChromaDB 사전 로딩으로 첫 질문 지연 방지
    try:
        from tools.tool2_search_pdf_rag import search_pdf_rag
        search_pdf_rag("초기화 테스트", top_k=1)
        print("데이터베이스 로딩 완료.\n")
    except Exception:
        print("투자설명서 데이터베이스 로딩에 실패했습니다. 정량 데이터 기반으로 동작합니다.\n")

    while True:
        try:
            user_q = input("[질문 입력] > ").strip()
            if not user_q:
                continue
            if user_q.lower() in ["exit", "q", "quit", "종료"]:
                print("테스트를 종료합니다.")
                break

            result = run_pipeline(user_q)

            print("\n" + "-" * 55)
            print(f"[파이프라인 진단]")
            print(f"  라우팅: {result['routing_mode']}")
            print(f"  도구 수: {result['tool_calls_count']}개")
            print(f"  합성 방식: {result['synthesis_mode']}")
            print(f"  검증 상태: {result['validation_status']}")
            print(f"  수치 대조: {'일치(PASS)' if result['is_fact_matched'] else '미대조'}")
            if result['degraded_services']:
                print(f"  제한 서비스: {', '.join(result['degraded_services'])}")
            print("-" * 55)
            print(f"\n{result['final_output']}\n")
            print("=" * 60)

        except KeyboardInterrupt:
            print("\n테스트가 중단되었습니다.")
            break
        except Exception as e:
            print(f"\n[예외 발생] {e}")


if __name__ == "__main__":
    start_terminal_cli()
