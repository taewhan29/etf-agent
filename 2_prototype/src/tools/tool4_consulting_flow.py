# -*- coding: utf-8 -*-
"""[도구 4] 상담 플로우 조율 및 규제 안내 모듈 (Consulting_Flow_Handler)"""
import re
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "etf_spec.db")

GUARDRAIL_PATTERNS = [
    r"원금\s*보장", r"원금\s*보전", r"원금\s*보호", r"원금\s*손실\s*없", r"원금\s*손상\s*없",
    r"확정\s*수익", r"확정\s*금리", r"수익\s*보장", r"이익\s*보장", r"고정\s*수익률", r"확정\s*이율",
    r"손실\s*없", r"리스크\s*없", r"위험\s*없", r"100%\s*안전", r"손실\s*제로", r"마이너스\s*없", r"예금자\s*보호\s*100%",
    r"무조건\s*벌", r"무조건\s*상승", r"무조건\s*오른", r"무조건\s*대박", r"절대\s*손해", r"절대\s*안\s*떨어"
]

AMBIGUOUS_CATEGORY_MAP = {
    "미국주식": ["ACE 미국S&P500", "ACE 미국나스닥100", "ACE 미국배당다우존스", "ACE 미국빅테크TOP7 Plus"],
    "미국": ["ACE 미국S&P500", "ACE 미국나스닥100", "ACE 미국배당다우존스", "ACE 미국30년국채액티브(H)"],
    "채권": ["ACE 미국30년국채액티브(H)", "ACE 종합채권(AA-이상)액티브"],
    "배당": ["ACE 미국배당다우존스", "ACE 미국30년국채액티브(H)"],
    "주식": ["ACE 미국S&P500", "ACE 미국나스닥100", "ACE 200", "ACE 글로벌반도체TOP4 Plus"]
}

REFERRAL_PATTERNS = [
    r"세금\s*환급", r"상속", r"증여", r"절세\s*팁", r"개인\s*연금\s*계산", r"계좌\s*이체", r"비밀번호"
]

LIST_PATTERNS = [
    r"etf\s*종류", r"상품\s*종류", r"종류.*뭐", r"어떤\s*etf", r"무슨\s*etf", r"etf\s*목록", r"상품\s*목록",
    r"종목\s*목록", r"종목\s*리스트", r"답할\s*수\s*있는", r"조회\s*가능한", r"지원하는\s*etf", r"전체\s*etf"
]

GREETING_PATTERNS = [
    r"^(안녕|안녕하세요|반가워|하이|hi|hello)",
    r"너\s*(누구|뭐하는|이름)", r"자기\s*소개", r"챗봇\s*소개",
    r"^도움말$", r"^사용법$", r"어떻게\s*써", r"어떤\s*기능", r"무엇을\s*할\s*수"
]

COMPETITOR_PATTERNS = [
    r"kodex", r"코덱스", r"tiger", r"타이거", r"rise", r"라이즈",
    r"kbstar", r"케イビー스타", r"sol\b", r"쏠\b", r"타사", r"다른\s*운용사", r"타운용사"
]

DOMAIN_FAQ_PATTERNS = {
    "pension": [
        r"연금\s*저축", r"퇴직\s*연금", r"irp\b", r"isa\b", r"연금\s*계좌",
        r"절세\s*계좌", r"연금\s*편입", r"연금에서\s*살\s*수", r"irp에서\s*살\s*수",
        r"연금.*투자", r"irp.*투자", r"isa.*투자"
    ],
    "hedge": [
        r"환헤지", r"환노출", r"\(h\)", r"환율\s*영향", r"환헤지가\s*뭐",
        r"환노출이\s*뭐", r"환율\s*변동", r"환율\s*효과", r"환헤지.*차이"
    ],
    "dividend": [
        r"분배금.*언제", r"배당금.*언제", r"배당락", r"지급\s*기준일",
        r"입금\s*일", r"분배금\s*받으려면", r"월배당.*언제", r"배당.*언제"
    ],
    "real_cost": [
        r"실부담\s*비용", r"기타\s*비용", r"매매\s*중개\s*수수료", r"총비용\s*비율",
        r"실제\s*수수료", r"증권\s*거래\s*비용", r"실제\s*총비용"
    ],
    "active": [
        r"액티브\s*etf", r"액티브가\s*뭐", r"패시브.*차이", r"액티브.*패시브",
        r"액티브\s*펀드", r"액티브란"
    ]
}

def check_compliance_and_guardrail(text: str) -> dict:
    for pattern in GUARDRAIL_PATTERNS:
        if re.search(pattern, text):
            return {
                "status": "BLOCKED",
                "is_safe": False,
                "text": (
                    "[금융소비자보호법 규제 안내]\n\n"
                    "요청하신 질의 또는 답변에 원금 보장이나 확정 수익과 같은 규제 위반 단정 표현이 감지되어 답변 생성을 제한합니다.\n\n"
                    "안내: 본 집합투자증권은 실적배당형 상품으로 운용 결과에 따라 원금 손실이 발생할 수 있으며 예금자보호법에 따라 보호되지 않습니다."
                )
            }
            
    notice_text = (
        "\n\n안내: 본 정보는 공시 자료에 기반한 참고용 안내이며, 투자 권유나 원금 보장을 의미하지 않습니다. "
        "모든 집합투자증권은 운용 결과에 따라 원금 손실이 발생할 수 있습니다."
    )
    return {
        "status": "SAFE",
        "is_safe": True,
        "text": text + notice_text
    }

def handle_ambiguous_query(query: str) -> dict:
    query_cleaned = query.strip()
    
    for category_key, etf_list in AMBIGUOUS_CATEGORY_MAP.items():
        if query_cleaned == category_key or query_cleaned == f"{category_key} etf" or query_cleaned == f"{category_key} 추천":
            options_str = ", ".join(etf_list)
            return {
                "status": "CLARIFICATION_NEEDED",
                "is_ambiguous": True,
                "text": (
                    f"[질의 대상 선택 안내]\n\n"
                    f"문의하신 '{category_key}' 관련 대표 상품으로 아래 4가지 ETF가 있습니다.\n"
                    f"선택지: {options_str}\n\n"
                    f"구체적으로 어떤 종목의 스펙이나 공시 문맥을 찾으시는지 선택해 주세요."
                )
            }
            
    return {"status": "CLEAR", "is_ambiguous": False}

def handle_customer_referral(query: str) -> dict:
    for pattern in REFERRAL_PATTERNS:
        if re.search(pattern, query):
            return {
                "status": "REFERRAL_REQUIRED",
                "is_referral": True,
                "text": (
                    "[전문 상담 고객센터 연계 안내]\n\n"
                    "문의하신 개별 세무, 절세 계산 및 종합 자산 관리 상담은 전문 상담원의 확인이 필요합니다.\n\n"
                    "한국투자신탁운용 고객센터: 1544-0050 (평일 09:00 ~ 17:00)"
                )
            }
            
    return {"status": "NORMAL", "is_referral": False}

def handle_all_etf_list() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT ticker, name, category FROM etf_spec ORDER BY category, ticker")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return {"status": "ERROR", "text": "DB에서 ETF 목록을 조회할 수 없습니다."}

    category_map = {}
    for ticker, name, category in rows:
        cat = category or "기타"
        if cat not in category_map:
            category_map[cat] = []
        category_map[cat].append(f"{name} ({ticker})")

    output_text = f"[ACE ETF 지원 상품 전체 목록 (총 {len(rows)}종)]\n\n"
    output_text += "현재 시스템에서 상세 정량 스펙, 수수료 계산 및 공시 탐색이 가능한 ETF 상품 목록입니다:\n\n"
    
    for cat, etf_list in category_map.items():
        output_text += f"■ {cat}\n"
        for etf in etf_list:
            output_text += f"  - {etf}\n"
        output_text += "\n"
    
    output_text += "[안내] 구체적인 종목 스펙 비교나 수수료 계산, 공시 검색을 원하시면 종목명을 포함하여 질문해 주세요.\n"
    output_text += "(예: 'ACE 미국S&P500 수수료 알려줘', 'S&P500이랑 나스닥100 보수율 비교해줘')"

    return {"status": "ALL_ETF_LIST", "text": output_text}


def handle_comparison_clarification() -> dict:
    return {
        "status": "COMPARISON_CLARIFICATION_NEEDED",
        "text": (
            "[비교 대상 선택 안내]\n\n"
            "구체적으로 어떤 ETF 종목이나 카테고리의 비교를 원하시나요?\n\n"
            "[추천 질문 예시]\n"
            "- 특정 종목 비교: 'S&P500이랑 나스닥100 보수율 비교해줘'\n"
            "- 카테고리 비교: '미국주식 ETF 비교해줘', '배당 ETF 비교해줘', '채권 ETF 비교해줘'"
        )
    }


def handle_greeting() -> dict:
    return {
        "status": "GREETING_GUIDE",
        "text": (
            "[한국투자신탁운용 ACE ETF 안내 챗봇]\n\n"
            "안녕하세요! 한국투자신탁운용 ACE ETF 공식 질의응답 챗봇입니다.\n"
            "투자설명서 공시 문서와 정형 DB를 바탕으로 객관적인 스펙 및 수수료 정보를 제공합니다.\n\n"
            "[추천 질문 예시]\n"
            "- 스펙 및 비교: 'S&P500이랑 나스닥100 보수율 비교해줘', '미국주식 ETF 비교해줘'\n"
            "- 수수료 계산: 'ACE 미국S&P500 1천만원 3년 투자 시 수수료 얼마야?'\n"
            "- 공시 내용 검색: 'ACE 미국배당다우존스 투자 위험 알려줘'\n"
            "- 지원 상품 목록: '답할 수 있는 ETF 종류는 뭐가 있어?'"
        )
    }


def handle_competitor_guide() -> dict:
    return {
        "status": "COMPETITOR_GUIDE",
        "text": (
            "[타사 ETF 질의 안내 및 ACE 대응 상품 매핑]\n\n"
            "문의하신 상품은 타 운용사의 ETF 브랜드입니다.\n"
            "본 챗봇은 한국투자신탁운용 ACE ETF 전용 시스템으로, 타사 상품의 실시간 데이터는 제공하지 않습니다.\n\n"
            "[대응되는 ACE ETF 대표 상품 안내]\n"
            "- 미국 대표지수: ACE 미국S&P500, ACE 미국나스닥100\n"
            "- 미국 배당/테크: ACE 미국배당다우존스, ACE 미국빅테크TOP7 Plus\n"
            "- 국내 대표지수: ACE 200\n"
            "- 채권/파킹형: ACE 미국30년국채액티브(H), ACE 머니마켓액티브\n\n"
            "위 ACE 상품의 상세 스펙이나 보수율이 궁금하시면 종목명을 입력해 주세요."
        )
    }


def handle_domain_faq(faq_type: str) -> dict:
    if faq_type == "pension":
        text = (
            "[연금계좌 및 ISA 투자 규정 안내]\n\n"
            "한국투자신탁운용 ACE ETF의 절세계좌(연금/ISA) 투자 원칙은 다음과 같습니다:\n\n"
            "1. 퇴직연금 (IRP / DC):\n"
            "- 주식형 ETF: 위험자산으로 분류되어 계좌 총자산의 최대 70%까지 편입 가능합니다 (예: ACE 미국S&P500, ACE 미국나스닥100, ACE 미국배당다우존스).\n"
            "- 채권형 및 파킹형 ETF: 안전자산으로 분류되어 계좌 내 100% 편입 가능합니다 (예: ACE 종합채권(AA-이상)액티브, ACE 미국30년국채액티브(H), ACE 머니마켓액티브).\n\n"
            "2. 연금저축펀드:\n"
            "- 주식형 ETF를 포함하여 100% 자유롭게 편입 가능합니다 (단, 레버리지/인버스 및 선물형 ETF는 법적으로 편입 불가).\n\n"
            "3. ISA (개인종합자산관리계좌):\n"
            "- 국내 상장된 모든 ACE ETF에 100% 한도 없이 투자 가능하며, 비과세 및 분리과세 혜택이 적용됩니다."
        )
    elif faq_type == "hedge":
        text = (
            "[환헤지(H) vs 환노출 상품 안내]\n\n"
            "해외 자산에 투자하는 ETF의 환율 전략 차이는 다음과 같습니다:\n\n"
            "1. 환헤지형 (종목명 끝에 '(H)' 표기):\n"
            "- 대표 상품: ACE 미국30년국채액티브(H)\n"
            "- 특징: 통화선도 계약을 통해 원/달러 환율 변동 영향을 사전에 차단합니다. 환율이 오르거나 내려도 기초자산의 순수 가격 변동만 수익률에 반영됩니다.\n\n"
            "2. 환노출형 (종목명 끝에 '(H)' 없음):\n"
            "- 대표 상품: ACE 미국S&P500, ACE 미국나스닥100, ACE 미국배당다우존스\n"
            "- 특징: 기초자산의 가격 변동뿐만 아니라 원/달러 환율 변동이 수익률에 직접 연동됩니다. 달러 환율 상승 시 추가 환차익, 하락 시 환차손이 발생합니다."
        )
    elif faq_type == "dividend":
        text = (
            "[분배금(배당금) 지급 기준일 및 일정 안내]\n\n"
            "ACE ETF의 분배금 지급 및 수령 절차는 다음과 같습니다:\n\n"
            "1. 지급기준일:\n"
            "- 월분배형: 매월 마지막 영업일 (예: ACE 미국배당다우존스)\n"
            "- 분기분배형: 매 분기(1월, 4월, 7월, 10월) 마지막 영업일 (예: ACE 미국S&P500)\n\n"
            "2. 매수 완료 시점 (중요):\n"
            "- 국내 주식 결제 주기(T+2일)에 따라 분배금을 지급받으려면 지급기준일 2영업일 전 장 마감 전까지 매수를 완료하셔야 합니다.\n\n"
            "3. 실제 입금 시점:\n"
            "- 통상 지급기준일 이후 약 7영업일 이내에 투자자 명의의 증권사 계좌로 입금됩니다."
        )
    elif faq_type == "real_cost":
        text = (
            "[총보수율(TER) vs 실부담비용율 안내]\n\n"
            "ETF 투자 시 실제로 투자자가 부담하는 비용 구조는 다음과 같습니다:\n\n"
            "1. 총보수율(TER):\n"
            "- 투자설명서에 공시되는 고정 보수로 운용, 신탁, 사무수탁, 판매보수의 합계입니다 (예: ACE 미국S&P500 연 0.0047%).\n\n"
            "2. 실부담비용 (총보수비용 + 매매·중개수수료율):\n"
            "- 총보수(TER) 외에 펀드가 포트폴리오를 편입/리밸런싱할 때 발생하는 '매매·중개수수료율'과 지수사용료/회계감사비 등의 '기타비용'이 추가로 순자산에서 일할 차감됩니다.\n\n"
            "[안내] 최신 회계연도 기준 실부담비용율은 금융투자협회 전자공시서비스(dis.kofia.or.kr)에서 확인하실 수 있습니다."
        )
    elif faq_type == "active":
        text = (
            "[액티브(Active) vs 패시브(Passive) ETF 안내]\n\n"
            "ETF의 운용 방식에 따른 주요 차이점은 다음과 같습니다:\n\n"
            "1. 패시브(Passive) ETF:\n"
            "- 기초지수를 그대로 복제하여 추종 오차(Tracking Error)를 최소화하고 지수 수익률을 1:1로 따라가는 것을 목표로 합니다.\n\n"
            "2. 액티브(Active) ETF (예: ACE 미국30년국채액티브(H), ACE 머니마켓액티브):\n"
            "- 비교지수와의 상관계수 0.7 이상을 유지하면서, 펀드매니저의 분석과 포트폴리오 조율(듀레이션 조절, 종목 선별 등)을 통해 비교지수 대비 초과 수익(Alpha)을 추구하는 상품입니다."
        )
    else:
        text = "해당 주제에 대한 상세 안내 문서를 준비 중입니다."

    return {
        "status": "DOMAIN_FAQ",
        "faq_type": faq_type,
        "text": text
    }


def handle_consulting_flow(sub_action: str, query: str = None, category: str = None) -> dict:
    """
    2단계 Tool Selector 오케스트레이터 연동용 도구 4 통합 래퍼 함수
    """
    if sub_action == "guardrail_block":
        return check_compliance_and_guardrail(query or "원금보장")
    elif sub_action == "customer_referral":
        return handle_customer_referral(query or "상속세")
    elif sub_action == "clarification_options":
        cat = category or query or "미국주식"
        return handle_ambiguous_query(cat)
    elif sub_action == "all_etf_list":
        return handle_all_etf_list()
    elif sub_action == "comparison_clarification":
        return handle_comparison_clarification()
    elif sub_action == "greeting":
        return handle_greeting()
    elif sub_action == "competitor_guide":
        return handle_competitor_guide()
    elif sub_action == "domain_faq":
        faq_key = category or "pension"
        return handle_domain_faq(faq_key)
    else:
        return {"status": "UNKNOWN_ACTION", "text": "요청한 상담 플로우 동작을 수행할 수 없습니다."}


