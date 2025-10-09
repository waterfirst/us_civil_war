import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import time
import numpy as np

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
# 지수 데이터 설정
TICKER_MAP = {
    'gold': {'symbol': 'GC=F', 'name': '금 (Gold)', 'ticker': 'XAU/USD'},
    'silver': {'symbol': 'SI=F', 'name': '은 (Silver)', 'ticker': 'XAG/USD'},
    'dxy': {'symbol': 'DX-Y.NYB', 'name': '달러 지수 (DXY)', 'ticker': 'DXY'},
    'us10y': {'symbol': '^TNX', 'name': '미 10년물 채권', 'ticker': 'US10Y'},
    'btc': {'symbol': 'BTC-USD', 'name': '비트코인', 'ticker': 'BTC/USD'},
    'krwjpy': {'symbol': 'KRWJPY=X', 'name': '원-엔 환율', 'ticker': 'KRW/JPY'},
    'krwusd': {'symbol': 'KRW=X', 'name': '원-달러 환율', 'ticker': 'USD/KRW'},
    'usdjpy': {'symbol': 'JPY=X', 'name': '달러-엔 환율', 'ticker': 'USD/JPY'},
    'spx': {'symbol': '^GSPC', 'name': 'S&P 500', 'ticker': 'S&P 500'},
    'ndx': {'symbol': '^NDX', 'name': '나스닥 100', 'ticker': 'NASDAQ 100'},
    'vix': {'symbol': '^VIX', 'name': '변동성 지수 (VIX)', 'ticker': 'VIX'},
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

    # 기본 지수들
    vix = get_item(market_data, 'vix')
    dxy = get_item(market_data, 'dxy')
    usdjpy = get_item(market_data, 'usdjpy')
    krwusd = get_item(market_data, 'krwusd')
    krwjpy = get_item(market_data, 'krwjpy')
    spx = get_item(market_data, 'spx')
    ndx = get_item(market_data, 'ndx')



        # S&P 500 분석 (기존 코드 유지)
    spx = get_item(market_data, 'spx')
    if spx:
        spx_chg = spx['change_pct']
        if spx_chg < -3.0:
            score += 3; factors.append(f"S&P500 급락 ({spx_chg:+.2f}%) +3")
        elif spx_chg < -1.5:
            score += 2; factors.append(f"S&P500 하락 ({spx_chg:+.2f}%) +2")
        elif spx_chg < -0.5:
            score += 1; factors.append(f"S&P500 약세 ({spx_chg:+.2f}%) +1")

    # 나스닥 100 분석 추가
    ndx = get_item(market_data, 'ndx')
    if ndx:
        ndx_chg = ndx['change_pct']
        if ndx_chg < -3.0:
            score += 3; factors.append(f"나스닥100 급락 ({ndx_chg:+.2f}%) +3")
        elif ndx_chg < -1.5:
            score += 2; factors.append(f"나스닥100 하락 ({ndx_chg:+.2f}%) +2")
        elif ndx_chg < -0.5:
            score += 1; factors.append(f"나스닥100 약세 ({ndx_chg:+.2f}%) +1")
    
    # S&P 500과 나스닥 100의 디버전스 체크 (추가 분석)
    if spx and ndx:
        spx_chg = spx['change_pct']
        ndx_chg = ndx['change_pct']
        divergence = abs(spx_chg - ndx_chg)
        
        # 두 지수가 2% 이상 다르게 움직이면 시장 불안정
        if divergence > 2.0:
            score += 2; factors.append(f"S&P-나스닥 디버전스 ({divergence:.2f}%p) +2")
        elif divergence > 1.0:
            score += 1; factors.append(f"지수 간 괴리 확대 ({divergence:.2f}%p) +1")

    # VIX 분석
    if vix and vix['current_value']:
        vix_level = vix['current_value']
        if vix_level > 35:
            score += 3; factors.append(f"VIX 매우 높음 ({vix_level:.1f}) +3")
        elif vix_level > 25:
            score += 2; factors.append(f"VIX 높음 ({vix_level:.1f}) +2")
        elif vix_level > 15:
            score += 1; factors.append(f"VIX 다소 높음 ({vix_level:.1f}) +1")

    # 달러 지수 분석
    if dxy:
        dxy_chg = dxy['change_pct']
        dxy_level = dxy['current_value']
        
        if dxy_chg > 1.0:
            score += 2; factors.append(f"달러지수 급등 ({dxy_chg:+.2f}%) +2")
        elif dxy_chg > 0.5:
            score += 1; factors.append(f"달러지수 상승 ({dxy_chg:+.2f}%) +1")
        
        # 달러지수 절대 수준도 고려 (105 이상이면 강세)
        if dxy_level > 110:
            score += 2; factors.append(f"달러 매우 강세 ({dxy_level:.1f}) +2")
        elif dxy_level > 105:
            score += 1; factors.append(f"달러 강세 ({dxy_level:.1f}) +1")

    # 크로스 환율 분석: 달러 강세 시 원화 vs 엔화 약세 비교
    if dxy and krwusd and usdjpy and krwjpy:
        dxy_chg = dxy['change_pct']
        krwusd_chg = krwusd['change_pct']
        usdjpy_chg = usdjpy['change_pct']
        krwjpy_chg = krwjpy['change_pct']
        
        # 달러 강세 시 원화가 엔화보다 더 약세인 경우 (원-엔 하락)
        if dxy_chg > 0.5 and krwjpy_chg < -1.0:
            score += 2; factors.append(f"달러 강세 시 원화 상대적 급락 ({krwjpy_chg:+.2f}%) +2")
        elif dxy_chg > 0.3 and krwjpy_chg < -0.5:
            score += 1; factors.append(f"달러 강세 시 원화 상대적 약세 ({krwjpy_chg:+.2f}%) +1")
        
        # 달러 약세 시 원화가 엔화보다 덜 강세인 경우 (원-엔 하락)
        if dxy_chg < -0.5 and krwjpy_chg < -1.0:
            score += 1; factors.append(f"달러 약세에도 원화 부진 ({krwjpy_chg:+.2f}%) +1")

    # 원-달러 환율 분석
    if krwusd:
        krwusd_chg = krwusd['change_pct']
        if krwusd_chg > 2.0:
            score += 3; factors.append(f"원화 급락 대비 달러 ({krwusd_chg:+.2f}%) +3")
        elif krwusd_chg > 1.0:
            score += 2; factors.append(f"원화 약세 대비 달러 ({krwusd_chg:+.2f}%) +2")
        elif krwusd_chg > 0.5:
            score += 1; factors.append(f"원화 하락 대비 달러 ({krwusd_chg:+.2f}%) +1")
        elif krwusd_chg < -2.0:
            score += 2; factors.append(f"원화 급등 대비 달러 ({krwusd_chg:+.2f}%) +2")
        elif krwusd_chg < -1.0:
            score += 1; factors.append(f"원화 강세 대비 달러 ({krwusd_chg:+.2f}%) +1")

    # 달러-엔 환율 분석 (캐리 트레이드 지표)
    if usdjpy:
        usdjpy_chg = usdjpy['change_pct']
        if usdjpy_chg > 2.0:
            score += 2; factors.append(f"엔화 급락 ({usdjpy_chg:+.2f}%) +2")
        elif usdjpy_chg > 1.0:
            score += 1; factors.append(f"엔화 약세 ({usdjpy_chg:+.2f}%) +1")
        elif usdjpy_chg < -2.0:
            score += 3; factors.append(f"엔화 급등, 캐리 청산 ({usdjpy_chg:+.2f}%) +3")
        elif usdjpy_chg < -1.0:
            score += 2; factors.append(f"엔화 강세 ({usdjpy_chg:+.2f}%) +2")

    # 원-엔 환율 단독 분석 (한국 특화)
    if krwjpy:
        krwjpy_chg = krwjpy['change_pct']
        # 원-엔 급락은 원화의 구조적 약세 신호
        if krwjpy_chg < -2.0:
            score += 2; factors.append(f"원화 구조적 약세 ({krwjpy_chg:+.2f}%) +2")
        elif krwjpy_chg < -1.0:
            score += 1; factors.append(f"원화 대비 엔화 강세 ({krwjpy_chg:+.2f}%) +1")

    # 나머지 지표들...
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


def calculate_pair_trading_signals(market_data):
    """페어 트레이딩 신호 계산 (5단계)"""
    signals = {}
    
    # 1. 금-은 페어 트레이딩
    gold = get_item(market_data, 'gold')
    silver = get_item(market_data, 'silver')
    
    if gold and silver:
        gold_value = gold['current_value']
        silver_value = silver['current_value']
        
        # 금/은 비율 계산
        gold_silver_ratio = gold_value / silver_value if silver_value > 0 else 0
        
        # 5단계 신호 (역사적 범위: 60-90)
        if gold_silver_ratio > 90:
            signal = '🟢🟢 은 강력매수 / 금 강력매도'
            color = '#00aa00'
            level = 'strong_buy'
            description = f'금은비율 {gold_silver_ratio:.1f} (매우 높음 → 은 심각한 저평가)'
        elif gold_silver_ratio > 82:
            signal = '🟢 은 매수 / 금 매도'
            color = '#28a745'
            level = 'buy'
            description = f'금은비율 {gold_silver_ratio:.1f} (높음 → 은 저평가)'
        elif gold_silver_ratio < 60:
            signal = '🔴🔴 금 강력매수 / 은 강력매도'
            color = '#cc0000'
            level = 'strong_sell'
            description = f'금은비율 {gold_silver_ratio:.1f} (매우 낮음 → 금 심각한 저평가)'
        elif gold_silver_ratio < 68:
            signal = '🔴 금 매수 / 은 매도'
            color = '#dc3545'
            level = 'sell'
            description = f'금은비율 {gold_silver_ratio:.1f} (낮음 → 금 저평가)'
        else:
            signal = '🟡 중립'
            color = '#ffc107'
            level = 'neutral'
            description = f'금은비율 {gold_silver_ratio:.1f} (정상 범위 68-82)'
        
        signals['gold_silver'] = {
            'signal': signal,
            'color': color,
            'level': level,
            'description': description,
            'ratio': gold_silver_ratio
        }
    
    # 2. VIX 기반 채권-주식 페어 트레이딩
    vix = get_item(market_data, 'vix')
    
    if vix:
        vix_level = vix['current_value']
        vix_chg = vix.get('change_pct', 0)
        
        # 5단계 신호
        if vix_level > 35 or (vix_level > 30 and vix_chg > 10):
            signal = '🔴🔴 주식 강력매수 / 채권 강력매도'
            color = '#cc0000'
            level = 'strong_buy_stocks'
            description = f'VIX {vix_level:.1f} (극도의 공포 → 주식 바닥 근접)'
        elif vix_level > 25 or (vix_level > 22 and vix_chg > 5):
            signal = '🔴 주식 매수 / 채권 매도'
            color = '#dc3545'
            level = 'buy_stocks'
            description = f'VIX {vix_level:.1f} (높은 공포 → 주식 저평가)'
        elif vix_level < 12:
            signal = '🟢🟢 채권 강력매수 / 주식 강력매도'
            color = '#00aa00'
            level = 'strong_sell_stocks'
            description = f'VIX {vix_level:.1f} (극도의 낙관 → 주식 고평가)'
        elif vix_level < 15:
            signal = '🟢 채권 매수 / 주식 매도'
            color = '#28a745'
            level = 'sell_stocks'
            description = f'VIX {vix_level:.1f} (낮은 공포 → 주식 고평가)'
        else:
            signal = '🟡 중립'
            color = '#ffc107'
            level = 'neutral'
            description = f'VIX {vix_level:.1f} (정상 범위 15-25)'
        
        signals['vix_bonds_stocks'] = {
            'signal': signal,
            'color': color,
            'level': level,
            'description': description,
            'vix_level': vix_level
        }
    
    # 3. 달러-엔 캐리 트레이드
    usdjpy = get_item(market_data, 'usdjpy')
    
    if usdjpy:
        usdjpy_value = usdjpy['current_value']
        usdjpy_chg = usdjpy['change_pct']
        
        # 5단계 신호 (역사적 범위: 100-160)
        if usdjpy_value > 160 or (usdjpy_value > 155 and usdjpy_chg > 2):
            signal = '🟢🟢 엔화 강력매수 / 달러 강력매도'
            color = '#00aa00'
            level = 'strong_buy_jpy'
            description = f'USD/JPY {usdjpy_value:.2f} (엔화 극도의 약세 → 반등 임박)'
        elif usdjpy_value > 152 or (usdjpy_value > 148 and usdjpy_chg > 1):
            signal = '🟢 엔화 매수 / 달러 매도'
            color = '#28a745'
            level = 'buy_jpy'
            description = f'USD/JPY {usdjpy_value:.2f} (엔화 과도한 약세)'
        elif usdjpy_value < 135 or (usdjpy_value < 140 and usdjpy_chg < -2):
            signal = '🔴🔴 달러 강력매수 / 엔화 강력매도'
            color = '#cc0000'
            level = 'strong_sell_jpy'
            description = f'USD/JPY {usdjpy_value:.2f} (엔화 극도의 강세 → 캐리 청산 완료)'
        elif usdjpy_value < 142 or (usdjpy_value < 145 and usdjpy_chg < -1):
            signal = '🔴 달러 매수 / 엔화 매도'
            color = '#dc3545'
            level = 'sell_jpy'
            description = f'USD/JPY {usdjpy_value:.2f} (엔화 과도한 강세 → 캐리 청산 위험)'
        else:
            signal = '🟡 중립'
            color = '#ffc107'
            level = 'neutral'
            description = f'USD/JPY {usdjpy_value:.2f} (정상 범위 142-152)'
        
        signals['usd_jpy'] = {
            'signal': signal,
            'color': color,
            'level': level,
            'description': description,
            'usdjpy_value': usdjpy_value
        }
    
    # 4. S&P 500 - 나스닥 100 페어 트레이딩
    spx = get_item(market_data, 'spx')
    ndx = get_item(market_data, 'ndx')
    
    if spx and ndx:
        spx_chg = spx['change_pct']
        ndx_chg = ndx['change_pct']
        
        # 성과 차이 계산
        performance_gap = ndx_chg - spx_chg
        
        # 5단계 신호
        if performance_gap > 3.0:
            signal = '🟢🟢 S&P 강력매수 / 나스닥 강력매도'
            color = '#00aa00'
            level = 'strong_buy_spx'
            description = f'격차 {performance_gap:+.2f}%p (기술주 극도 과열 → S&P 심각한 저평가)'
        elif performance_gap > 1.5:
            signal = '🟢 S&P 매수 / 나스닥 매도'
            color = '#28a745'
            level = 'buy_spx'
            description = f'격차 {performance_gap:+.2f}%p (기술주 과열 → S&P 저평가)'
        elif performance_gap < -3.0:
            signal = '🔴🔴 나스닥 강력매수 / S&P 강력매도'
            color = '#cc0000'
            level = 'strong_buy_ndx'
            description = f'격차 {performance_gap:+.2f}%p (기술주 극도 약세 → 나스닥 심각한 저평가)'
        elif performance_gap < -1.5:
            signal = '🔴 나스닥 매수 / S&P 매도'
            color = '#dc3545'
            level = 'buy_ndx'
            description = f'격차 {performance_gap:+.2f}%p (기술주 약세 → 나스닥 저평가)'
        else:
            signal = '🟡 중립'
            color = '#ffc107'
            level = 'neutral'
            description = f'격차 {performance_gap:+.2f}%p (균형 범위 -1.5 ~ +1.5%p)'
        
        signals['spx_ndx'] = {
            'signal': signal,
            'color': color,
            'level': level,
            'description': description,
            'performance_gap': performance_gap
        }
    
    return signals


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
        default_start = (datetime.now() - timedelta(days=365*2)).date()
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

    # 각 지수별 위험 신호 방향 정의
    RISK_INDICATORS = {
        'gold': 'up',      # 금 상승 = 위험 증가
        'silver': 'up',    # 은 상승 = 위험 증가
        'dxy': 'up',       # 달러지수 상승 = 위험 증가
        'us10y': 'up',     # 채권 금리 상승 = 위험 증가
        'btc': 'up',       # 비트코인 상승 = 위험 증가
        'krwjpy': 'down',  # 원-엔 하락 = 원화 약세 = 위험 증가
        'krwusd': 'up',    # 원-달러 상승 = 원화 약세 = 위험 증가
        'usdjpy': 'both',  # 달러-엔은 급변동 자체가 위험
        'vix': 'up',       # VIX 상승 = 위험 증가
        'spx': 'down',     # S&P500 하락 = 위험 증가
        'ndx': 'down',     # 나스닥100 하락 = 위험 증가
    }

    # 데이터프레임 생성
    df_data = []
    for item in market_data:
        risk_direction = RISK_INDICATORS.get(item['id'], 'neutral')
        
        # 위험도에 따른 상태 결정
        if item['status'] == '안정':
            risk_status = '중립'
            risk_color = 'neutral'
        elif item['status'] == '상승':
            if risk_direction == 'up':
                risk_status = '위험↑'
                risk_color = 'danger'
            elif risk_direction == 'down':
                risk_status = '안전↑'
                risk_color = 'safe'
            else:  # both
                if abs(item['change_pct']) > 1.5:
                    risk_status = '위험↑'
                    risk_color = 'danger'
                else:
                    risk_status = '변동↑'
                    risk_color = 'neutral'
        else:  # 하락
            if risk_direction == 'up':
                risk_status = '안전↓'
                risk_color = 'safe'
            elif risk_direction == 'down':
                risk_status = '위험↓'
                risk_color = 'danger'
            else:  # both
                if abs(item['change_pct']) > 1.5:
                    risk_status = '위험↓'
                    risk_color = 'danger'
                else:
                    risk_status = '변동↓'
                    risk_color = 'neutral'
        
        df_data.append({
            '지수명': item['name'],
            '심볼': item['ticker'],
            '현재가': item['formatted_value'],
            '변화율': f"{item['change_pct']:+.2f}%",
            '상태': risk_status,
            '_상태색상': risk_color,  # 숨겨진 컬럼
            '업데이트': datetime.now().strftime('%H:%M:%S')
        })

    df = pd.DataFrame(df_data)

    # 상태 색상 매핑 딕셔너리 생성
    status_color_map = dict(zip(df['상태'], df['_상태색상']))

    # 테이블 스타일링 함수
    def style_status_cell(val):
        """상태 셀 스타일링"""
        color = status_color_map.get(val, 'neutral')
        if color == 'danger':
            return 'background-color: #dc3545; color: white; font-weight: bold'
        elif color == 'safe':
            return 'background-color: #007bff; color: white; font-weight: bold'
        else:  # neutral
            return 'background-color: #6c757d; color: white'

    def style_change_cell(val):
        """변화율 셀 스타일링"""
        if isinstance(val, str):
            if val.startswith('+'):
                return 'color: #28a745; font-weight: bold'
            elif val.startswith('-'):
                return 'color: #dc3545; font-weight: bold'
        return ''

    # 숨겨진 컬럼 제거하고 스타일 적용
    display_df = df.drop('_상태색상', axis=1)
    styled_df = display_df.style.applymap(
        style_status_cell, subset=['상태']
    ).applymap(
        style_change_cell, subset=['변화율']
    )

    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # 범례 추가
    st.caption("""
    **상태 색상 의미:**  
    🔴 **빨강 (위험)** = 미국 내전 위험도 증가 신호 | 
    🔵 **파랑 (안전)** = 미국 내전 위험도 감소 신호 | 
    ⚪ **회색 (중립)** = 안정 또는 영향 미미
    """)



    # 과거 차트 섹션
    st.divider()
    st.subheader("📉 과거 차트 (5년 / 3년)")

    @st.cache_data(ttl=1200)
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
        selected_highlights = st.multiselect(
            "하이라이트 지수 선택 (선택 시 나머지는 회색 처리)", 
            options=highlight_options, 
            default=[]
        )

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
                    line=dict(
                        color='#cccccc' if is_dimmed else None, 
                        width=1 if is_dimmed else 2
                    ),
                    opacity=0.3 if is_dimmed else 1.0,
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                '날짜: %{x|%Y-%m-%d}<br>' +
                                '지수: %{y:.2f}<br>' +
                                '<extra></extra>'
                )
            )
        
        fig_all.update_layout(
            height=420,
            margin=dict(l=10, r=10, t=30, b=10),
            yaxis_title='Rebased (Start=100)',
            legend_title_text='지수',
            # 크로스헤어 활성화
            hovermode='x unified',  # x축 기준으로 모든 시리즈의 값 표시
            hoverdistance=100,
            spikedistance=1000,
            # 세로선 추가
            xaxis=dict(
                showspikes=True,  # 세로선 활성화
                spikemode='across',  # 차트 전체를 가로지름
                spikesnap='cursor',  # 커서 위치에 정확히 표시
                spikecolor='rgba(255, 255, 0, 0.8)',  # 선 색상
                spikethickness=1,  # 선 두께
                spikedash='dot'  # 점선 스타일
            ),
            # 가로선 추가
            yaxis=dict(
                showspikes=True,  # 가로선 활성화
                spikemode='across',
                spikesnap='cursor',
                spikecolor='rgba(255, 255, 25, 0.5)',
                spikethickness=1,
                spikedash='dot'
            )
        )
        
        st.plotly_chart(fig_all, use_container_width=True)
        
        # 사용 팁 추가
        st.info("💡 **사용 팁**: 차트 위에 마우스를 올리면 세로선/가로선이 표시되며, 모든 지수의 해당 시점 값을 동시에 확인할 수 있습니다.")



    
    st.divider()
    
    # ===== 페어 트레이딩 신호등 섹션 =====
    st.subheader("💱 페어 트레이딩 신호등 (5단계)")

    pair_signals = calculate_pair_trading_signals(market_data)

    # 2x2 그리드
    col1, col2 = st.columns(2)

    with col1:
        # 금-은 페어
        if 'gold_silver' in pair_signals:
            gs = pair_signals['gold_silver']
            st.markdown(
                f"""
                <div style="background:{gs['color']}; color:white; padding:12px; border-radius:8px; margin-bottom:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h4 style="margin:0; color:white;">💰 금-은 페어</h4>
                    <p style="margin:8px 0; font-size:1.15rem; font-weight:bold;">{gs['signal']}</p>
                    <p style="margin:0; font-size:0.9rem; opacity:0.95;">{gs['description']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        # VIX 채권-주식 페어
        if 'vix_bonds_stocks' in pair_signals:
            vbs = pair_signals['vix_bonds_stocks']
            st.markdown(
                f"""
                <div style="background:{vbs['color']}; color:white; padding:12px; border-radius:8px; margin-bottom:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h4 style="margin:0; color:white;">📊 VIX 채권-주식</h4>
                    <p style="margin:8px 0; font-size:1.15rem; font-weight:bold;">{vbs['signal']}</p>
                    <p style="margin:0; font-size:0.9rem; opacity:0.95;">{vbs['description']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

    with col2:
        # 달러-엔 캐리 트레이드
        if 'usd_jpy' in pair_signals:
            uj = pair_signals['usd_jpy']
            st.markdown(
                f"""
                <div style="background:{uj['color']}; color:white; padding:12px; border-radius:8px; margin-bottom:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h4 style="margin:0; color:white;">💴 달러-엔 캐리</h4>
                    <p style="margin:8px 0; font-size:1.15rem; font-weight:bold;">{uj['signal']}</p>
                    <p style="margin:0; font-size:0.9rem; opacity:0.95;">{uj['description']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        # S&P-나스닥 페어
        if 'spx_ndx' in pair_signals:
            sn = pair_signals['spx_ndx']
            st.markdown(
                f"""
                <div style="background:{sn['color']}; color:white; padding:12px; border-radius:8px; margin-bottom:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h4 style="margin:0; color:white;">📈 S&P-나스닥 페어</h4>
                    <p style="margin:8px 0; font-size:1.15rem; font-weight:bold;">{sn['signal']}</p>
                    <p style="margin:0; font-size:0.9rem; opacity:0.95;">{sn['description']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

    # 신호 강도 요약
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)

    signal_counts = {
        'strong_buy': 0,
        'buy': 0,
        'neutral': 0,
        'sell': 0,
        'strong_sell': 0
    }

    for signal_data in pair_signals.values():
        level = signal_data.get('level', 'neutral')
        if 'strong_buy' in level or 'strong_sell_stocks' in level or 'strong_buy_spx' in level:
            signal_counts['strong_buy'] += 1
        elif 'buy' in level and 'strong' not in level:
            signal_counts['buy'] += 1
        elif 'strong_sell' in level or 'strong_buy_ndx' in level:
            signal_counts['strong_sell'] += 1
        elif 'sell' in level and 'strong' not in level:
            signal_counts['sell'] += 1
        else:
            signal_counts['neutral'] += 1

    with col1:
        st.metric("🟢🟢 강력매수", signal_counts['strong_buy'])
    with col2:
        st.metric("🟢 매수", signal_counts['buy'])
    with col3:
        st.metric("🟡 중립", signal_counts['neutral'])
    with col4:
        st.metric("🔴 매도", signal_counts['sell'])
    with col5:
        st.metric("🔴🔴 강력매도", signal_counts['strong_sell'])

    # 페어 트레이딩 설명 업데이트
    with st.expander("📚 페어 트레이딩 5단계 전략 설명", expanded=False):
        st.markdown("""
        ## 신호 단계 설명
        
        - 🟢🟢 **강력매수**: 극단적 저평가, 높은 확신도
        - 🟢 **매수**: 명확한 저평가 신호
        - 🟡 **중립**: 정상 범위, 대기
        - 🔴 **매도**: 명확한 고평가 신호
        - 🔴🔴 **강력매도**: 극단적 고평가, 높은 확신도
        
        ---
        
        ### 1. 금-은 페어 트레이딩
        - **🟢🟢 강력**: 금은비율 > 90 또는 < 60
        - **🟢/🔴 일반**: 금은비율 82-90 또는 60-68
        - **🟡 중립**: 금은비율 68-82 (정상)
        - **역사적 평균**: 약 75
        
        ### 2. VIX 채권-주식 페어
        - **🟢🟢 주식 강력매수**: VIX > 35 (극도의 공포)
        - **🟢 주식 매수**: VIX 25-35 (높은 공포)
        - **🟡 중립**: VIX 15-25 (정상)
        - **🔴 주식 매도**: VIX 12-15 (낮은 공포)
        - **🔴🔴 주식 강력매도**: VIX < 12 (극도의 낙관)
        
        ### 3. 달러-엔 캐리 트레이드
        - **🟢🟢 엔화 강력매수**: USD/JPY > 160 (엔화 극약세)
        - **🟢 엔화 매수**: USD/JPY 152-160
        - **🟡 중립**: USD/JPY 142-152 (정상)
        - **🔴 달러 매수**: USD/JPY 135-142
        - **🔴🔴 달러 강력매수**: USD/JPY < 135 (캐리 청산 완료)
        
        ### 4. S&P-나스닥 페어
        - **🟢🟢 S&P 강력매수**: 격차 > +3.0%p (기술주 극과열)
        - **🟢 S&P 매수**: 격차 +1.5 ~ +3.0%p
        - **🟡 중립**: 격차 -1.5 ~ +1.5%p (균형)
        - **🔴 나스닥 매수**: 격차 -3.0 ~ -1.5%p
        - **🔴🔴 나스닥 강력매수**: 격차 < -3.0%p (기술주 극약세)
        """)

    st.divider()


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
