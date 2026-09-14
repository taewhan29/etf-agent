# -*- coding: utf-8 -*-
"""
[4단계] 근거 기반 답변 합성 엔진 (Step 4: Response Synthesizer)
- 3단계 원천 수집 데이터(Ground Truth) 기반 엄격한 근거 작성
- 미확인 정보 생성(Hallucination) 방지 및 불필요한 사족 제거 (단문 구성)
- Streamlit secrets (st.secrets["GEMINI_API_KEY"]) 및 os.environ 키 호환 지원
- API 키 부재 시 템플릿 기반 안전망(Fallback Synthesizer) 탑재
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
from pipeline.step3_tool_executor import execute_tools


def get_gemini_api_key() -> str:
    """
    Streamlit secrets 및 환경변수에서 Gemini API 키 탐색
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if api_key:
        return api_key

    try:
        import streamlit as st  # type: ignore
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"].strip()
    except Exception:
        pass

    return ""


def clean_prohibited_characters(text: str) -> str:
    """
    아스테리스크(*) 및 이모티콘 기호 완전 제거
    """
    text = text.replace("*", "")
    # 이모지 및 특수 기호 제거
    clean_chars = []
    for ch in text:
        if ord(ch) < 0x1F600 or ord(ch) > 0x1F64F:
            clean_chars.append(ch)
    return "".join(clean_chars)


def fallback_synthesize(query: str, execution_results: list) -> str:
    """
    API 키 미설정 또는 호출 실패 시 3단계 원천 결과를 바탕으로 작성하는 경량 템플릿 합성기
    """
    combined_texts = []
    has_success_spec_or_math = False

    for res in execution_results:
        tname = res.get("tool_name")
        status = res.get("status")
        if tname in ["tool1_query_spec_db", "tool3_math_engine"] and status == "SUCCESS":
            has_success_spec_or_math = True

    for res in execution_results:
        output = res.get("result")
        tname = res.get("tool_name")
        status = res.get("status")
        if output and isinstance(output, dict) and "text" in output:
            txt = output["text"]
            if tname == "tool2_search_pdf_rag" and status == "NOT_FOUND" and has_success_spec_or_math:
                txt = "[공시 문맥 안내]\n상세 공시 본문은 확인되지 않았으나, 정량 지표 데이터는 위와 같습니다."
            combined_texts.append(txt)

    if not combined_texts:
        return "조회된 데이터가 없거나 답변을 합성할 수 없습니다."

    # 원천 데이터를 단문 결합
    final_text = "\n\n".join(combined_texts)
    return clean_prohibited_characters(final_text)


def synthesize_response(exec_info: dict) -> dict:
    """
    3단계 도구 수집 결과를 바탕으로 최종 근거 답변 합성
    """
    query = exec_info.get("query", "")
    routing_mode = exec_info.get("routing_mode", "")
    exec_results = exec_info.get("execution_results", [])

    # 1. 규제 차단 / 역질문 / 세무 연계 처리 (도구 4 연동 결과 원문 100% 보존)
    for res in exec_results:
        tool_name = res.get("tool_name")
        output = res.get("result") or {}
        status = res.get("status")

        if tool_name == "tool4_consulting_flow" and status in [
            "BLOCKED", "CLARIFICATION_NEEDED", "REFERRAL_REQUIRED",
            "ALL_ETF_LIST", "COMPARISON_CLARIFICATION_NEEDED",
            "GREETING_GUIDE", "COMPETITOR_GUIDE", "DOMAIN_FAQ"
        ]:
            return {
                "query": query,
                "routing_mode": routing_mode,
                "synthesis_mode": "GUARDRAIL_DIRECT",
                "final_response": clean_prohibited_characters(output.get("text", ""))
            }

    # 2. 3단계 수집 결과 텍스트 및 레코드 취합 (Ground Truth Context)
    context_blocks = []
    for idx, res in enumerate(exec_results, 1):
        output = res.get("result") or {}
        if "text" in output:
            context_blocks.append(f"[도구 {idx} 실행 데이터]\n{output['text']}")

    ground_truth_context = "\n\n".join(context_blocks)

    # 3. Gemini API 키 확인 및 LLM 합성 시도
    api_key = get_gemini_api_key()
    
    if api_key:
        try:
            # google-genai 라이브러리 사용 시도
            from google import genai  # type: ignore
            client = genai.Client(api_key=api_key)

            prompt = (
                f"당신은 한국투자신탁운용 ACE ETF 전문 챗봇입니다.\n"
                f"오직 아래 제공된 [도구 실행 데이터]만을 바탕으로 사용자의 질문에 답변하십시오.\n"
                f"데이터에 없는 내용은 절대 추측하거나 지어내지 마십시오.\n"
                f"불필요한 인사말이나 서론, 사족을 전면 배제하고 명확한 단문 위주로 작성하십시오.\n"
                f"아스테리스크(*) 기호와 이모티콘은 절대 사용하지 마십시오.\n\n"
                f"[사용자 질문]: {query}\n\n"
                f"[도구 실행 데이터]:\n{ground_truth_context}\n\n"
                f"[답변]:"
            )

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            raw_text = response.text or ""
            final_response = clean_prohibited_characters(raw_text.strip())

            return {
                "query": query,
                "routing_mode": routing_mode,
                "synthesis_mode": "GEMINI_LLM_SYNTHESIS",
                "final_response": final_response
            }

        except Exception as e:
            # API 키 오류나 네트워크 예외 발생 시 Fallback으로 전환
            print(f"[알림] Gemini API 호출 예외 발생 -> Fallback 템플릿 사용 (사유: {e})")

    # 4. API 키 미설정 또는 호출 실패 시 Fallback 템플릿 사용
    fallback_response = fallback_synthesize(query, exec_results)
    return {
        "query": query,
        "routing_mode": routing_mode,
        "synthesis_mode": "FALLBACK_TEMPLATE",
        "final_response": fallback_response
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

    print("=== [4단계 근거 기반 답변 합성 엔진 검증] ===")
    for q in test_queries:
        ref_info = refine_query(q)
        plan_info = select_tools(ref_info)
        exec_info = execute_tools(plan_info)
        synth_info = synthesize_response(exec_info)

        print(f"\n질문: '{synth_info['query']}'")
        print(f"  합성 모드: {synth_info['synthesis_mode']} (라우팅: {synth_info['routing_mode']})")
        print(f"  최종 답변:\n{synth_info['final_response']}\n")
        print("-" * 60)
