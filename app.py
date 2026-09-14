# -*- coding: utf-8 -*-
"""
한국투자신탁운용 ACE ETF AI 투자 파트너 (app.py)
- 디자인 스타일: web-precision-fintech (정밀 핀테크 라이트 팩)
- 노 사이드바(No Sidebar) 및 중앙 단일 컬럼(Single-Column) 레이아웃
- 개발자용 모니터링 요소 100% 제거 및 100% Ground Truth 원천 데이터 연동
- 상단 히어로 추천 퀵 질의 및 답변 하단 원클릭 다음 추천 질문(Next Action) 연동
- 이모티콘 및 아스테리스크(*) 완전 제거 준수
"""
import os
import sys

# 상위 경로 모듈 참조 설정
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(CURRENT_DIR, "2_prototype", "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

import streamlit as st  # type: ignore
from pipeline.main_pipeline import run_pipeline

# 페이지 기본 설정 (사이드바 숨김 및 중앙 집중형 단일 레이아웃)
st.set_page_config(
    page_title="한국투자신탁운용 ACE ETF AI 투자 파트너",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# web-precision-fintech 정밀 핀테크 커스텀 스타일 정의
st.markdown("""
<style>
    /* 1. 사이드바 완전 제거 */
    [data-testid="stSidebar"] {
        display: none !important;
    }
    [data-testid="collapsedControl"] {
        display: none !important;
    }
    
    /* 2. 배경 및 캔버스 설정 */
    .stApp {
        background-color: #f6f5f3 !important;
        font-family: 'Inter', 'Pretendard', -apple-system, sans-serif;
        color: #1a2233;
    }
    .main .block-container {
        max-width: 860px !important;
        padding-top: 32px !important;
        padding-bottom: 50px !important;
    }
    
    /* 3. 상단 이리데센트 핀테크 헤더 밴드 */
    .fintech-header-band {
        background: linear-gradient(105deg, #fef6e4 0%, #fcd9c6 26%, #e6d6f5 58%, #cdd3f5 82%, #c3c9f0 100%);
        padding: 30px 36px;
        border-radius: 12px;
        border: 1px solid #e4e2dd;
        margin-bottom: 24px;
    }
    .fintech-brand-label {
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.08em;
        color: #4f46e5;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .fintech-title {
        font-family: 'Inter Tight', 'Pretendard', sans-serif;
        font-size: 27px;
        font-weight: 600;
        color: #1a2233;
        margin: 0 0 8px 0;
        letter-spacing: -0.03em;
    }
    .fintech-subtitle {
        font-size: 14.5px;
        color: #5b6472;
        margin: 0;
        line-height: 1.55;
    }
    
    /* 4. 등폭 숫자 정렬 (Tabular Nums) */
    .tabular-num {
        font-family: 'IBM Plex Mono', monospace, sans-serif;
        font-variant-numeric: tabular-nums;
    }
    
    /* 5. 챗봇 대화 말풍선 디테일 */
    .user-msg-box {
        background-color: #4f46e5;
        color: #ffffff;
        padding: 14px 20px;
        border-radius: 14px 14px 2px 14px;
        margin: 10px 0;
        float: right;
        clear: both;
        max-width: 82%;
        font-size: 15px;
        line-height: 1.55;
        box-shadow: 0 1px 2px rgba(79,70,229,0.12);
        white-space: pre-wrap;
    }
    .assistant-msg-box {
        background-color: #ffffff;
        color: #1a2233;
        border: 1px solid #e4e2dd;
        padding: 20px 24px;
        border-radius: 14px 14px 14px 2px;
        margin: 10px 0;
        float: left;
        clear: both;
        max-width: 95%;
        font-size: 15px;
        line-height: 1.65;
        box-shadow: 0 1px 2px rgba(26,34,51,0.03);
        white-space: pre-wrap;
    }
    .clear-fix {
        clear: both;
    }
    
    /* 6. 추천 질문 영역 스타일 */
    .rec-section-title {
        font-size: 13px;
        font-weight: 600;
        color: #5b6472;
        margin: 10px 0 6px 0;
        clear: both;
    }
    
    /* 7. 법적 유의사항 푸터 박스 */
    .legal-disclaimer {
        font-size: 12px;
        color: #6b7280;
        background-color: #eae8e3;
        border: 1px solid #dcd9d2;
        border-radius: 8px;
        padding: 14px 18px;
        margin-top: 32px;
        line-height: 1.6;
        clear: both;
    }
    
    /* 8. Streamlit 버튼 디테일 스타일링 */
    div.stButton > button {
        border-radius: 8px !important;
        border: 1px solid #e4e2dd !important;
        background-color: #ffffff !important;
        color: #1a2233 !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease-out !important;
        padding: 8px 14px !important;
    }
    div.stButton > button:hover {
        border-color: #4f46e5 !important;
        color: #4f46e5 !important;
        background-color: #f8f8ff !important;
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None


# --- 1. 상단 핀테크 헤더 밴드 ---
st.markdown("""
<div class="fintech-header-band">
    <div class="fintech-brand-label">KOREA INVESTMENT MANAGEMENT</div>
    <div class="fintech-title">한국투자신탁운용 ACE ETF AI 투자 파트너</div>
    <div class="fintech-subtitle">공식 공시 데이터 및 정형 DB 기반 100% 무결성 ETF 상품 정보, 수수료 시뮬레이션, 절세 계좌 투자 가이드 서비스</div>
</div>
""", unsafe_allow_html=True)


# --- 2. 상단 추천 퀵 질의 가로 칩 영역 ---
st.markdown("<div style='font-size:13px; font-weight:600; color:#5b6472; margin-bottom:8px;'>자주 찾는 추천 질의:</div>", unsafe_allow_html=True)
q_cols = st.columns(4)

quick_queries = [
    ("IRP 주식형 70% 한도", "퇴직연금 IRP에서 주식형 ETF 살 수 있어?"),
    ("환헤지(H) 원리 안내", "환헤지랑 환노출 차이가 뭐야?"),
    ("S&P500 수수료/스펙", "ACE 미국S&P500 수수료 알려줘"),
    ("1천만원 3년 수수료 계산", "1천만원 3년 수수료 계산해줘")
]

for idx, (label, q_text) in enumerate(quick_queries):
    with q_cols[idx]:
        if st.button(label, key=f"quick_chip_{idx}", use_container_width=True):
            st.session_state.pending_query = q_text

st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)


# --- 3. 메인 AI 대화 스트림 영역 ---
for msg_idx, msg in enumerate(st.session_state.messages):
    role = msg["role"]
    content = msg["content"]
    recs = msg.get("recommendations", [])
    
    if role == "user":
        st.markdown(f'<div class="user-msg-box">{content}</div><div class="clear-fix"></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-msg-box">{content}</div><div class="clear-fix"></div>', unsafe_allow_html=True)
        
        # 하단 원클릭 다음 추천 질문(Next Action) 칩 버튼 렌더링
        if recs:
            st.markdown('<div class="rec-section-title">다음 추천 질문:</div>', unsafe_allow_html=True)
            r_cols = st.columns(len(recs))
            for r_idx, rec_q in enumerate(recs):
                with r_cols[r_idx]:
                    if st.button(rec_q, key=f"rec_chip_{msg_idx}_{r_idx}", use_container_width=True):
                        st.session_state.pending_query = rec_q


# 질의 실행 및 파이프라인 연동 처리 함수
def handle_submit(user_input_text: str):
    if not user_input_text.strip():
        return

    # 사용자 질의 저장
    st.session_state.messages.append({"role": "user", "content": user_input_text})
    
    # 5단계 파이프라인 연동 (100% Ground Truth 원천 데이터)
    with st.spinner("공식 공시 DB 검증 답변 생성 중..."):
        res = run_pipeline(user_input_text)
        final_output = res.get("final_output", "")
        recommended_questions = res.get("recommended_questions", [])

    # 답변 본문과 추천 질문 분리
    display_text = final_output
    if "[다음 추천 질문]" in display_text:
        display_text = display_text.split("[다음 추천 질문]")[0].strip()

    st.session_state.messages.append({
        "role": "assistant",
        "content": display_text,
        "recommendations": recommended_questions
    })
    st.rerun()


# 상단 퀵 칩 또는 추천 질문 칩 클릭 시 자동 전송 처리
if st.session_state.pending_query:
    q_to_run = st.session_state.pending_query
    st.session_state.pending_query = None
    handle_submit(q_to_run)


# 하단 질의 입력창
user_query = st.chat_input("ACE ETF 상품 정보, 수수료 시뮬레이션, 연금 투자 기준을 입력하세요...")
if user_query:
    handle_submit(user_query)


# --- 4. 하단 금융투자 유의사항 및 고객센터 푸터 ---
st.markdown("""
<div class="legal-disclaimer">
    안내: 본 정보는 한국투자신탁운용 공시 자료 기반 안내이며 투자 권유나 원금 보장을 의미하지 않습니다. 
    모든 집합투자증권은 운용 결과에 따라 원금 손실이 발생할 수 있습니다. 
    <br>한국투자신탁운용 고객센터: 1544-0050 (평일 09:00 ~ 17:00)
</div>
""", unsafe_allow_html=True)
