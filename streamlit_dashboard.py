import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import os
from typing import Optional

try:
    import google.generativeai as genai
    _HAS_GEMINI = True
except Exception:
    _HAS_GEMINI = False

# 페이지 설정
st.set_page_config(
    page_title="Financial Indices Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일링
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .positive-change {
        color: #28a745;
        font-weight: bold;
    }
    .negative-change {
        color: #dc3545;
        font-weight: bold;
    }
    .neutral-change {
        color: #6c757d;
        font-weight: bold;
    }
    .status-stable {
        background-color: #d4edda;
        color: #155724;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
    }
    .status-rising {
        background-color: #cce5ff;
        color: #004085;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
    }
    .status-falling {
        background-color: #f8d7da;
        color: #721c24;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
    }
</style>
""", unsafe_allow_html=True)

# 지수 데이터 설정
TICKER_MAP = {
    'gold': {'symbol': 'GC=F', 'name': '금 (Gold)', 'ticker': 'XAU/USD'},
    'silver': {'symbol': 'SI=F', 'name': '은 (Silver)', 'ticker': 'XAG/USD'},
    'dxy': {'symbol': 'DX-Y.NYB', 'name': '달러 지수 (DXY)', 'ticker': 'DXY'},
    'us10y': {'symbol': '^TNX', 'name': '미 10년물 채권', 'ticker': 'US10Y'},
    'btc': {'symbol': 'BTC-USD', 'name': '비트코인', 'ticker': 'BTC/USD'},
    'skew': {'symbol': '^SKEW', 'name': '블랙스완 지수', 'ticker': 'SKEW'},
    'vix': {'symbol': '^VIX', 'name': '변동성 지수 (VIX)', 'ticker': 'VIX'},
}

def get_unit(symbol):
    """심볼에 따른 단위 반환"""
    if symbol in ['^TNX']:
        return 'percentage'
    elif symbol in ['DX-Y.NYB', '^SKEW', '^VIX']:
        return 'points'
    return 'currency'

def format_value(value, unit):
    """값을 단위에 맞게 포맷팅"""
    if unit == 'percentage':
        return f"{value:.2f}%"
    elif unit == 'points':
        return f"{value:.2f}"
    else:  # currency
        return f"${value:,.2f}"

def get_status_class(change_pct):
    """변화율에 따른 상태 클래스 반환"""
    if abs(change_pct) < 1:
        return "status-stable"
    elif change_pct > 0:
        return "status-rising"
    else:
        return "status-falling"

def get_change_class(change_pct):
    """변화율에 따른 색상 클래스 반환"""
    if change_pct > 0:
        return "positive-change"
    elif change_pct < 0:
        return "negative-change"
    else:
        return "neutral-change"

@st.cache_data(ttl=60)  # 1분 캐시
def fetch_market_data():
    """시장 데이터 가져오기"""
    data = []
    
    for key, info in TICKER_MAP.items():
        try:
            ticker = yf.Ticker(info['symbol'])
            hist = ticker.history(period="2d")
            
            if len(hist) >= 2:
                current_price = hist['Close'].iloc[-1]
                previous_price = hist['Close'].iloc[-2]
                change_pct = ((current_price - previous_price) / previous_price) * 100
            else:
                current_price = hist['Close'].iloc[-1] if not hist.empty else 0
                change_pct = 0
            
            unit = get_unit(info['symbol'])
            status = "안정" if abs(change_pct) < 1 else ("상승" if change_pct > 0 else "하락")
            
            data.append({
                'id': key,
                'name': info['name'],
                'ticker': info['ticker'],
                'current_value': current_price,
                'previous_value': previous_price if len(hist) >= 2 else current_price,
                'change_pct': change_pct,
                'unit': unit,
                'status': status,
                'formatted_value': format_value(current_price, unit),
                'positive_is_good': not info['symbol'].startswith('^')
            })
            
        except Exception as e:
            st.error(f"Error fetching data for {info['name']}: {str(e)}")
            data.append({
                'id': key,
                'name': info['name'],
                'ticker': info['ticker'],
                'current_value': 0,
                'previous_value': 0,
                'change_pct': 0,
                'unit': get_unit(info['symbol']),
                'status': "오류",
                'formatted_value': "N/A",
                'positive_is_good': True
            })
    
    return data

def get_item(data, key):
    for item in data:
        if item['id'] == key:
            return item
    return None

def compute_risk_signal(market_data):
    """간단한 휴리스틱으로 위험 점수와 신호등 색상을 계산합니다."""
    score = 0
    factors = []

    vix = get_item(market_data, 'vix')
    if vix and vix['current_value']:
        vix_level = vix['current_value']
        if vix_level > 35:
            score += 3; factors.append(f"VIX 매우 높음 ({vix_level:.1f}) +3")
        elif vix_level > 25:
            score += 2; factors.append(f"VIX 높음 ({vix_level:.1f}) +2")
        elif vix_level > 15:
            score += 1; factors.append(f"VIX 다소 높음 ({vix_level:.1f}) +1")

    skew = get_item(market_data, 'skew')
    if skew and skew['current_value']:
        skew_level = skew['current_value']
        if skew_level > 150:
            score += 2; factors.append(f"SKEW 매우 높음 ({skew_level:.0f}) +2")
        elif skew_level > 140:
            score += 1; factors.append(f"SKEW 높음 ({skew_level:.0f}) +1")

    dxy = get_item(market_data, 'dxy')
    if dxy:
        dxy_chg = dxy['change_pct']
        if dxy_chg > 1.0:
            score += 2; factors.append(f"달러지수 급등 ({dxy_chg:+.2f}%) +2")
        elif dxy_chg > 0.5:
            score += 1; factors.append(f"달러지수 상승 ({dxy_chg:+.2f}%) +1")

    us10y = get_item(market_data, 'us10y')
    if us10y and us10y['current_value'] is not None and us10y['previous_value'] is not None:
        move_bp = abs(us10y['current_value'] - us10y['previous_value'])
        if move_bp > 0.20:
            score += 2; factors.append(f"미10년물 급변 ({move_bp:.2f}p) +2")
        elif move_bp > 0.10:
            score += 1; factors.append(f"미10년물 변동 확대 ({move_bp:.2f}p) +1")

    gold = get_item(market_data, 'gold')
    if gold:
        gchg = gold['change_pct']
        if gchg > 2.0:
            score += 2; factors.append(f"금 강세 ({gchg:+.2f}%) +2")
        elif gchg > 1.0:
            score += 1; factors.append(f"금 상승 ({gchg:+.2f}%) +1")

    silver = get_item(market_data, 'silver')
    if silver:
        schg = silver['change_pct']
        if schg > 3.0:
            score += 2; factors.append(f"은 강세 ({schg:+.2f}%) +2")
        elif schg > 1.5:
            score += 1; factors.append(f"은 상승 ({schg:+.2f}%) +1")

    btc = get_item(market_data, 'btc')
    if btc:
        bchg = btc['change_pct']
        if bchg > 6.0:
            score += 2; factors.append(f"BTC 급등 ({bchg:+.2f}%) +2")
        elif bchg > 3.0:
            score += 1; factors.append(f"BTC 상승 ({bchg:+.2f}%) +1")

    # 점수 → 신호등
    if score >= 6:
        level = '높음'
        color = '#dc3545'  # red
        emoji = '🔴'
    elif score >= 3:
        level = '중간'
        color = '#ffc107'  # yellow
        emoji = '🟡'
    else:
        level = '낮음'
        color = '#28a745'  # green
        emoji = '🟢'

    return {'score': score, 'level': level, 'color': color, 'emoji': emoji, 'factors': factors}

def _format_snapshot_for_prompt(market_data, risk):
    lines = []
    lines.append("[현재 지수 스냅샷]")
    for item in market_data:
        lines.append(
            f"- {item['name']} ({item['ticker']}): 현재 {item['formatted_value']}, 변화율 {item['change_pct']:+.2f}%"
        )
    lines.append("")
    lines.append(
        f"[휴리스틱 위험도] 수준={risk['level']}, 점수={risk['score']}, 요인={'; '.join(risk['factors']) if risk['factors'] else '없음'}"
    )
    return "\n".join(lines)

def analyze_with_gemini(api_key: str, market_data, risk, model_name: Optional[str] = None) -> Optional[str]:
    if not _HAS_GEMINI:
        return "google-generativeai 패키지가 설치되어 있지 않습니다. 'pip install google-generativeai'로 설치하세요."
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        # 일부 환경에서는 -latest 접미사가 404를 유발할 수 있어 기본값을 고정 버전으로 사용
        model_id = model_name or "gemini-1.5-flash"
        try:
            model = genai.GenerativeModel(model_id)
        except Exception:
            # 호환 모델 폴백
            for fallback in ["gemini-1.5-pro", "gemini-1.5-flash-8b", "gemini-1.0-pro"]:
                try:
                    model = genai.GenerativeModel(fallback)
                    model_id = fallback
                    break
                except Exception:
                    model = None
            if model is None:
                return f"Gemini 모델 초기화 실패 (시도한 모델: {model_id})."
        snapshot = _format_snapshot_for_prompt(market_data, risk)
        system_prompt = (
            "당신은 거시/시장 리스크 분석가입니다. 아래 지표와 휴리스틱 위험도를 참고해 "
            "향후 수일~수주의 미국 내 정치적 불안(예: 사회적 갈등 격화)과 경제 변동(변동성 확대, 레버리지 축소) 가능성을 "
            "보수적으로 해석하세요. 과도한 확신을 피하고, 데이터 한계를 명시하며, 관찰 가능한 신호와 조건부 시나리오로 답하세요.\n\n"
        )
        user_prompt = (
            f"입력 데이터:\n{snapshot}\n\n"
            "요구사항:\n"
            "1) 신호의 강/중/약 근거를 항목별로 정리\n"
            "2) 단기(1주) / 단중기(2~4주) 시나리오 범위 제시\n"
            "3) 리스크 완화/확대 트리거 3~5개\n"
            "4) 포트폴리오 차원에서의 일반적 유의점(투자자문 아님)\n"
            "5) 데이터/모델 한계와 불확실성 명시"
        )
        prompt = system_prompt + user_prompt
        resp = model.generate_content(prompt)
        return getattr(resp, 'text', None) or (resp.candidates[0].content.parts[0].text if getattr(resp, 'candidates', None) else None)
    except Exception as e:
        return f"Gemini 호출 오류: {e}"


def main():
    # 헤더
    st.markdown('<h1 class="main-header">📊 Financial Indices Dashboard</h1>', unsafe_allow_html=True)
    
    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        if st.button("🔄 데이터 새로고침"):
            st.cache_data.clear()
            st.rerun()
        st.divider()
        st.header("🧠 Gemini 설정")
        try:
            default_key = st.secrets.get('google_api_key', '')
        except Exception:
            default_key = ''
        user_key = st.text_input("Google API Key", value=default_key, type="password", placeholder="AIza...")
        model_choice = st.selectbox(
            "Gemini 모델",
            options=[
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-1.5-flash-8b",
                "gemini-1.0-pro"
            ],
            index=0
        )
        run_ai = st.button("🤖 Gemini 해석 실행")
    
    # 데이터 가져오기
    with st.spinner("시장 데이터를 가져오는 중..."):
        market_data = fetch_market_data()
    
    # 신호등 계산 및 표시
    risk = compute_risk_signal(market_data)
    st.subheader("🚨 미국 내전 발발 가능성 신호등")
    st.markdown(
        f"""
        <div style="background:{risk['color']}; color:white; padding:14px; border-radius:8px; font-size:1.1rem;">
            {risk['emoji']} 현재 수준: <b>{risk['level']}</b> (점수: {risk['score']})
        </div>
        """,
        unsafe_allow_html=True
    )
    if risk['factors']:
        with st.expander("기여 요인 보기", expanded=False):
            for f in risk['factors']:
                st.write("- " + f)
    
    # 자동 새로고침 제거: 사용자가 버튼으로 새로고침합니다.
    
    # 메트릭 카드들
    st.subheader("📈 실시간 지수 현황")
    
    # 상태별 통계
    stable_count = sum(1 for item in market_data if item['status'] == '안정')
    rising_count = sum(1 for item in market_data if item['status'] == '상승')
    falling_count = sum(1 for item in market_data if item['status'] == '하락')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("총 지수", len(market_data))
    with col2:
        st.metric("안정", stable_count, delta=None)
    with col3:
        st.metric("상승", rising_count, delta=None)
    with col4:
        st.metric("하락", falling_count, delta=None)
    
    st.divider()
    
    # 메인 데이터 테이블
    st.subheader("📊 상세 데이터")
    
    # 데이터프레임 생성
    df_data = []
    for item in market_data:
        df_data.append({
            '지수명': item['name'],
            '심볼': item['ticker'],
            '현재가': item['formatted_value'],
            '변화율': f"{item['change_pct']:+.2f}%",
            '상태': item['status'],
            '업데이트': datetime.now().strftime('%H:%M:%S')
        })
    
    df = pd.DataFrame(df_data)
    
    # 테이블 스타일링
    def style_status(val):
        if val == '안정':
            return 'background-color: #d4edda; color: #155724'
        elif val == '상승':
            return 'background-color: #cce5ff; color: #004085'
        elif val == '하락':
            return 'background-color: #f8d7da; color: #721c24'
        else:
            return 'background-color: #f8d7da; color: #721c24'
    
    styled_df = df.style.applymap(style_status, subset=['상태'])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    # 차트 섹션 제거: 단순 테이블 중심 UI

    # Gemini 해석 섹션
    st.divider()
    st.subheader("🧠 Gemini 해석 (정성적 리스크 코멘트)")
    if 'run_ai' not in st.session_state:
        st.session_state.run_ai = False
    # 버튼은 사이드바에 있으므로, 그 신호를 받아서 실행
    try:
        triggered = run_ai
    except NameError:
        triggered = False
    if triggered:
        with st.spinner("Gemini로 해석 중..."):
            try:
                ai_text = analyze_with_gemini(user_key, market_data, risk, model_choice)
            except Exception as _:
                ai_text = "Gemini 분석 실행 중 오류가 발생했습니다."
        if ai_text:
            st.write(ai_text)
        else:
            st.warning("API Key를 입력하거나, 'pip install google-generativeai'로 패키지를 설치하세요.")
    st.caption("본 해석은 정보 제공용이며, 투자/정치적 의사결정에 대한 조언이 아닙니다.")
    
    # 하단 정보
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"🕐 마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    with col2:
        st.info("📡 데이터 소스: Yahoo Finance")

if __name__ == "__main__":
    main()
