import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import time

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
    'spx': {'symbol': '^GSPC', 'name': 'S&P 500', 'ticker': 'S&P 500'},
}

def get_unit(symbol):
    """심볼에 따른 단위 반환"""
    if symbol in ['^TNX']:
        return 'percentage'
    elif symbol in ['DX-Y.NYB', '^SKEW', '^VIX', '^GSPC']:
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

 


def main():
    # 헤더
    st.markdown('<h1 class="main-header">📊 Financial Indices Dashboard</h1>', unsafe_allow_html=True)
    
    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        if st.button("🔄 데이터 새로고침"):
            # 데이터 새로고침 시작 시간 기록
            st.session_state['refresh_started_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            st.cache_data.clear()
            st.rerun()
        # 단일 차트 시작일 선택
        default_start = (datetime.now() - timedelta(days=365)).date()
        single_chart_start = st.date_input("단일 차트 시작일", value=default_start)
    
    # 데이터 가져오기
    with st.spinner("시장 데이터를 가져오는 중..."):
        t0 = time.perf_counter()
        market_data = fetch_market_data()
        t1 = time.perf_counter()
        # 데이터 로드 완료 시간 기록
        st.session_state['refresh_finished_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        st.session_state['refresh_elapsed_sec'] = round(t1 - t0, 2)
    
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

    # 과거 차트 섹션
    st.divider()
    st.subheader("📉 과거 차트 (5년 / 3년)")

    @st.cache_data(ttl=600)
    def fetch_history(symbol: str, years: int) -> pd.DataFrame:
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # 여유를 두기 위해 +30일
        start = start.replace(year=start.year)  # no-op; keep explicit
        try:
            df = yf.Ticker(symbol).history(period=f"{years}y")
            if df is None or df.empty:
                # period가 실패하면 수동 기간으로 재시도
                from datetime import timedelta
                df = yf.Ticker(symbol).history(start=datetime.now() - timedelta(days=365*years+30))
        except Exception:
            df = pd.DataFrame()
        return df

    def render_history_tab(years: int):
        # 모든 심볼의 히스토리를 먼저 가져온 뒤 그립니다 (로딩 에러 방지)
        with st.spinner(f"{years}년 데이터 불러오는 중..."):
            history_map = {}
            for key, info in TICKER_MAP.items():
                history_map[key] = fetch_history(info['symbol'], years)
        cols = st.columns(2)
        idx = 0
        for key, info in TICKER_MAP.items():
            hist_df = history_map.get(key)
            with cols[idx % 2]:
                if hist_df is None or hist_df.empty or 'Close' not in getattr(hist_df, 'columns', []):
                    st.warning(f"{info['name']} ({info['ticker']}) 데이터 없음")
                else:
                    import plotly.express as px
                    fig = px.line(
                        hist_df.reset_index(), x='Date', y='Close',
                        title=f"{info['name']} ({info['ticker']}) - {years}년"
                    )
                    fig.update_layout(height=300, margin=dict(l=10, r=10, t=40, b=10))
                    if info['symbol'] == '^TNX':
                        fig.update_yaxes(title_text='Yield (%)')
                    st.plotly_chart(fig, use_container_width=True)
            idx += 1

    tab5, tab3 = st.tabs(["5년", "3년"])
    with tab5:
        render_history_tab(5)
    with tab3:
        render_history_tab(3)

    
    
    # 하단 정보
    st.divider()
    # 전체 지수 합산 차트 (사용자 지정 시작일, 기준=100)
    st.subheader("🧩 모든 모니터링 지수: 단일 차트 (기준=100)")

    @st.cache_data(ttl=600)
    def fetch_all_history_rebased_from(start_date):
        result = {}
        for key, info in TICKER_MAP.items():
            try:
                h = yf.Ticker(info['symbol']).history(start=start_date)
                if h is None or h.empty or 'Close' not in h.columns:
                    continue
                base = h['Close'].iloc[0]
                if base and base != 0:
                    rebased = (h['Close'] / base) * 100.0
                    result[key] = {
                        'name': info['name'],
                        'ticker': info['ticker'],
                        'series': rebased
                    }
            except Exception:
                continue
        return result

    with st.spinner("모든 지수 히스토리 로딩 중..."):
        all_hist = fetch_all_history_rebased_from(single_chart_start)

    if not all_hist:
        st.warning("모든 지수 히스토리를 불러오지 못했습니다.")
    else:
        import plotly.graph_objects as go
        # 하이라이트 선택 컨트롤
        highlight_options = [v['name'] for v in all_hist.values()]
        selected_highlights = st.multiselect("하이라이트 지수 선택 (선택 시 나머지는 회색 처리)", options=highlight_options, default=[])

        fig_all = go.Figure()
        # 날짜 범위가 서로 다를 수 있으므로 각 시리즈 자체 x를 사용해 trace 추가
        for key, item in all_hist.items():
            s = item['series']
            is_dimmed = len(selected_highlights) > 0 and item['name'] not in selected_highlights
            fig_all.add_trace(
                go.Scatter(
                    x=s.index,
                    y=s.values,
                    mode='lines',
                    name=item['name'],
                    line=dict(color='#cccccc', width=1) if is_dimmed else None,
                    opacity=0.3 if is_dimmed else 1.0,
                )
            )
        fig_all.update_layout(
            height=420,
            margin=dict(l=10, r=10, t=30, b=10),
            yaxis_title='Rebased (Start=100)',
            legend_title_text='지수'
        )
        st.plotly_chart(fig_all, use_container_width=True)

    # 하단 정보
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        # 로드 타이밍 정보 표시
        started = st.session_state.get('refresh_started_at')
        finished = st.session_state.get('refresh_finished_at')
        elapsed = st.session_state.get('refresh_elapsed_sec')
        timing = []
        if started:
            timing.append(f"시작: {started}")
        if finished:
            timing.append(f"완료: {finished}")
        if elapsed is not None:
            timing.append(f"소요: {elapsed}s")
        timing_text = " | ".join(timing) if timing else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        st.info(f"🕐 데이터 로드 타이밍: {timing_text}")
    with col2:
        st.info("📡 데이터 소스: Yahoo Finance")

if __name__ == "__main__":
    main()
