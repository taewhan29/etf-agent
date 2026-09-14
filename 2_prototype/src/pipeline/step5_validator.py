# -*- coding: utf-8 -*-
"""
[5단계] 규제 및 출처 검증 모듈 (Step 5: Validator)
- 4단계 합성 답변을 바탕으로 2차 금소법 규제 검증 수행
- 3단계 정형 DB 수치 데이터 1:1 팩트체킹 대조
- 투자설명서 PDF 공시 출처 표기 및 법적 투자 유의사항 부착
- 이모티콘 및 아스테리스크(*) 완벽 제거
"""
import os
import re
import sys

# 상위 경로 모듈 참조 설정
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from pipeline.step1_query_refiner import refine_query
from pipeline.step2_tool_selector import select_tools
from pipeline.step3_tool_executor import execute_tools
from pipeline.step4_response_synthesizer import synthesize_response, clean_prohibited_characters
from tools.tool4_consulting_flow import GUARDRAIL_PATTERNS


def verify_compliance_guardrail(text: str) -> bool:
    """
    답변 텍스트 내 금소법 위반 단정 표현(원금보장 등) 2차 검증
    """
    for pattern in GUARDRAIL_PATTERNS:
        if re.search(pattern, text):
            return False
    return True


def check_numeric_fact_checking(text: str, exec_results: list) -> bool:
    """
    3단계 정형 DB 수치(TER 등)가 답변에 올바르게 반영되었는지 1:1 수치 대조
    """
    for res in exec_results:
        tool_name = res.get("tool_name")
        output = res.get("result") or {}
        if tool_name == "tool1_query_spec_db" and "records" in output:
            for rec in output["records"]:
                ter_val = str(rec.get("ter", ""))
                # 수치가 존재할 경우 답변 텍스트 내 수치 존재 여부 대조
                if ter_val and ter_val not in text:
                    return False
    return True


def attach_compliance_disclaimer(text: str, routing_mode: str) -> str:
    """
    법적 투자 유의사항 및 출처 유의 문구 부착
    """
    # 이미 가드레일 통과 전용 안내문이 작성된 경우 중복 부착 방지
    if "금융소비자보호법" in text or "고객센터" in text:
        return text

    disclaimer = (
        "\n\n안내: 본 정보는 한국투자신탁운용 공시 자료 기반 안내이며 투자 권유나 원금 보장을 의미하지 않습니다. "
        "모든 집합투자증권은 운용 결과에 따라 원금 손실이 발생할 수 있습니다."
    )

    if disclaimer.strip() not in text:
        text = text + disclaimer

    return text


# 종목별 대표 후속 추천 질문 사전 (etf_spec.db 실제 티커 기준)
TICKER_RECOMMENDED_QUESTIONS = {
    "360200": [  # ACE 미국S&P500
        "ACE 미국나스닥100과 총보수율 비교해줘",
        "1천만원을 3년간 투자했을 때 총수수료 시뮬레이션해줘"
    ],
    "367380": [  # ACE 미국나스닥100
        "ACE 미국S&P500과 총보수율 비교해줘",
        "주요 편입 종목과 운용 전략 알려줘"
    ],
    "402970": [  # ACE 미국배당다우존스
        "분배금 지급 주기와 최근 분배 현황 알려줘",
        "ACE 미국S&P500과 총보수율 및 배당 전략 비교해줘"
    ],
    "453850": [  # ACE 미국30년국채액티브(H)
        "환헤지형(H)과 환노출형의 차이점이 뭐야?",
        "퇴직연금 IRP 계좌에서 100% 안전자산으로 매수 가능한가요?"
    ],
    "465580": [  # ACE 미국빅테크TOP7 Plus
        "ACE 글로벌반도체TOP4 Plus와 총보수율 비교해줘",
        "1천만원 투자 시 3년 총수수료 계산해줘"
    ],
    "446770": [  # ACE 글로벌반도체TOP4 Plus
        "ACE 미국빅테크TOP7 Plus와 총보수율 비교해줘",
        "주요 편입 종목 및 투자위험 알려줘"
    ],
    "411060": [  # ACE KRX금현물
        "연금저축이나 IRP 계좌에서 금현물 ETF 매수할 수 있어?",
        "금선물 ETF와 KRX금현물 ETF의 차이점 알려줘"
    ],
    "105190": [  # ACE 200
        "ACE 미국S&P500과 총보수율 비교해줘",
        "퇴직연금 계좌에서 편입 한도가 어떻게 되나요?"
    ],
    "356540": [  # ACE 종합채권(AA-이상)액티브
        "퇴직연금 IRP에서 100% 안전자산으로 매수 가능한가요?",
        "1천만원 투자 시 3년 수수료 계산해줘"
    ],
    "487340": [  # ACE 머니마켓액티브
        "머니마켓액티브 ETF의 주요 투자 대상과 수익 구조 알려줘",
        "퇴직연금 안전자산 100% 편입 가능한가요?"
    ]
}


def generate_recommended_questions(query: str, routing_mode: str, exec_results: list, tickers: list) -> list:
    """
    사용자의 질문 및 실행 맥락에 기반하여 2개의 연관 후속 질문 추천
    """
    # 1. 추천 질문 제외 모드 (규제 차단, 고객센터 연계, 역질문 확인, 인사말)
    if routing_mode in [
        "GUARDRAIL_BLOCK",
        "CUSTOMER_REFERRAL",
        "COMPARISON_CLARIFICATION",
        "COMPARISON_CLARIFICATION_REQUIRED",
        "GREETING_GUIDE"
    ] or "CLARIFICATION" in routing_mode:
        return []

    q_lower = query.lower()

    # 2. 복수 종목 비교 모드
    if routing_mode == "MULTI_TOOL_COMPARISON" or len(tickers) >= 2:
        return [
            "비교한 종목들의 1천만원 3년 투자 시 총비용 차이 계산해줘",
            "이 종목들은 퇴직연금 IRP 계좌에서 매수할 수 있어?"
        ]

    # 3. 단일 종목 특정 질의 (티커 1개 기반 맞춤 추천)
    if tickers and len(tickers) == 1:
        t = tickers[0]
        if t in TICKER_RECOMMENDED_QUESTIONS:
            return TICKER_RECOMMENDED_QUESTIONS[t]

    # 4. 비용 시뮬레이션 질의 (종목 미지정 계산 등)
    if routing_mode == "MULTI_TOOL_MATH_SPEC" or any(k in query for k in ["수수료", "비용", "계산", "시뮬레이션"]):
        return [
            "기타비용과 매매중개수수료를 포함한 실질 총비용 알려줘",
            "다른 유사 ETF와 총보수율 비교해줘"
        ]

    # 5. 도메인 FAQ 모드
    if routing_mode == "DOMAIN_FAQ" or any(k in query for k in ["연금", "irp", "환헤지", "환노출", "분배금", "배당", "실부담", "총보수", "액티브", "패시브"]):
        if any(k in query for k in ["연금", "irp", "퇴직"]):
            return [
                "ACE 미국S&P500을 IRP 계좌에서 살 수 있어?",
                "퇴직연금 안전자산 100% 편입 가능한 채권형 ETF 알려줘"
            ]
        elif any(k in query for k in ["환헤지", "환노출", "환율"]):
            return [
                "ACE 미국30년국채액티브(H) 환헤지 구조 알려줘",
                "환노출 ETF와 환헤지 ETF 중 어떤 것이 유리한가요?"
            ]
        elif any(k in query for k in ["분배금", "배당", "입금"]):
            return [
                "ACE 미국배당다우존스 분배금 지급일 알려줘",
                "월배당 ETF 목록 조회해줘"
            ]
        elif any(k in query for k in ["실부담", "기타비용", "실질비용"]):
            return [
                "ACE 미국S&P500 기타비용 포함 총비용 얼마야?",
                "1천만원 투자 시 3년 실질 수수료 시뮬레이션해줘"
            ]
        elif any(k in query for k in ["액티브", "패시브"]):
            return [
                "ACE 미국30년국채액티브 운용 전략 알려줘",
                "액티브 ETF와 패시브 ETF의 총보수 차이 비교해줘"
            ]

    # 6. 타사 ETF 매핑
    if routing_mode == "COMPETITOR_GUIDE" or any(k in q_lower for k in ["kodex", "tiger", "rise", "타사"]):
        return [
            "매핑된 ACE ETF의 총보수율과 상세 정보 알려줘",
            "1천만원 투자 시 3년 총수수료 시뮬레이션해줘"
        ]

    # 7. 전체 목록 조회
    if routing_mode == "ALL_ETF_LIST" or any(k in query for k in ["목록", "종목들", "전체", "리스트"]):
        return [
            "미국 대표지수 ETF 보수율 비교해줘",
            "퇴직연금 IRP 계좌에서 100% 투자 가능한 안전자산 ETF 알려줘"
        ]

    # 8. 기본 추천 질문 (Default)
    return [
        "ACE ETF 전체 상품 목록 보여줘",
        "퇴직연금 IRP에서 투자 가능한 ETF 기준 알려줘"
    ]


def attach_recommended_questions(text: str, questions: list) -> str:
    """
    답변 본문 뒤에 다음 추천 질문(Next Action) 블록 부착
    """
    if not questions or "[다음 추천 질문]" in text:
        return text

    rec_block = "\n\n[다음 추천 질문]\n" + "\n".join(f"- {q}" for q in questions)
    return text + rec_block


def validate_and_finalize(synth_info: dict, exec_info: dict) -> dict:
    """
    4단계 결과를 수신하여 최종 컴플라이언스 검증 및 출처/유의문구가 완비된 최종 답변 반환
    """
    query = synth_info.get("query", "")
    routing_mode = synth_info.get("routing_mode", "")
    synthesis_mode = synth_info.get("synthesis_mode", "")
    raw_response = synth_info.get("final_response", "")
    exec_results = exec_info.get("execution_results", [])
    tickers = exec_info.get("tickers", [])

    # 1. 금소법 규제 2차 재검증
    is_safe = verify_compliance_guardrail(raw_response)
    if not is_safe:
        blocked_text = (
            "[금융소비자보호법 규제 검증 차단]\n\n"
            "생성된 답변에 원금 보장 또는 확정 수익 관련 단정 표현이 포함되어 답변 제공이 제한됩니다.\n\n"
            "안내: 본 집합투자증권은 실적배당형 상품으로 운용 결과에 따라 원금 손실이 발생할 수 있습니다."
        )
        return {
            "query": query,
            "routing_mode": routing_mode,
            "validation_status": "BLOCKED_BY_GUARDRAIL",
            "is_validated": False,
            "recommended_questions": [],
            "final_output": clean_prohibited_characters(blocked_text)
        }

    # 2. 정형 DB 수치 팩트체킹 대조
    is_fact_matched = check_numeric_fact_checking(raw_response, exec_results)

    # 3. 다음 추천 질문(Next Action) 생성 및 부착
    recommended_questions = generate_recommended_questions(query, routing_mode, exec_results, tickers)
    text_with_recs = attach_recommended_questions(raw_response, recommended_questions)

    # 4. 법적 투자 유의사항 및 출처 부착
    final_text = attach_compliance_disclaimer(text_with_recs, routing_mode)

    # 5. 아스테리스크 및 이모티콘 최종 소독
    cleaned_final_output = clean_prohibited_characters(final_text)

    return {
        "query": query,
        "routing_mode": routing_mode,
        "synthesis_mode": synthesis_mode,
        "validation_status": "PASSED",
        "is_fact_matched": is_fact_matched,
        "is_validated": True,
        "recommended_questions": recommended_questions,
        "final_output": cleaned_final_output
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

    print("=== [5단계 규제 및 출처 검증 모듈 테스트] ===")
    for q in test_queries:
        ref_info = refine_query(q)
        plan_info = select_tools(ref_info)
        exec_info = execute_tools(plan_info)
        synth_info = synthesize_response(exec_info)
        val_info = validate_and_finalize(synth_info, exec_info)

        print(f"\n질문: '{val_info['query']}'")
        print(f"  검증 상태: {val_info['validation_status']} (팩트체크: {val_info.get('is_fact_matched', True)})")
        print(f"  최종 완성 출력:\n{val_info['final_output']}\n")
        print("=" * 60)
