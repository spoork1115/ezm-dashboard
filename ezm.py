# pm2 start "streamlit run ezm.py --server.port 8501" --name my-streamlit-app
# streamlit run ezm.py --server.port 8501 --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false
# nohup python -m streamlit run ezm.py --server.port 8501 &

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="이지멤버스 인사이트 대시보드", layout="wide")

# --- Brand Categories Configuration ---
BRAND_CATEGORY_MAP = {
    'GS25': '유통/편의점',
    'GS더프레시': '유통/편의점',
    '랄라블라': '뷰티/케어',
    '예스24': '도서/교육',
    '교보문고': '도서/교육',
    '고피자': '식음료(F&B)',
    '이지웨이': '식음료(F&B)',
    '크리스탈 제이드': '식음료(F&B)',
    '베베쿡': '도서/교육',
    '히어로플레이파크': '기타 서비스',
    '파크 하얏트 서울': '기타 서비스',
    '슬로베이커리': '식음료(F&B)',
    '뉴발란스': '유통/편의점',
    '멤버샵': '기타 서비스',
    '제휴몰A': '기타 서비스'
}

# --- 보안 비밀번호 인증 기능 ---
def check_password():
    """사용자가 올바른 비밀번호를 입력했는지 확인하고 로그인 화면을 렌더링합니다."""
    
    def password_entered():
        """입력한 비밀번호가 st.secrets 또는 기본값과 일치하는지 검사합니다."""
        correct_password = st.secrets.get("DASHBOARD_PASSWORD", "1115")
        if st.session_state["password_input"] == str(correct_password):
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]  # 보안을 위해 세션에서 즉시 삭제
        else:
            st.session_state["password_correct"] = False

    # 이미 로그인 성공한 경우 True 반환
    if st.session_state.get("password_correct", False):
        return True

    # 로그인 화면 디자인 (CSS 주입)
    st.markdown(
        """
        <style>
        /* 톤앤매너에 맞춘 비밀번호 로그인 카드 디자인 */
        .login-card {
            max-width: 400px;
            margin: 80px auto 0 auto;
            padding: 35px 25px;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(66, 72, 116, 0.08);
            border: 1px solid rgba(166, 177, 225, 0.2);
            text-align: center;
        }
        .login-logo {
            font-size: 40px;
            color: #424874;
            margin-bottom: 15px;
        }
        .login-title {
            font-family: 'Outfit', sans-serif;
            font-size: 22px;
            font-weight: 700;
            color: #424874;
            margin-bottom: 3px;
        }
        .login-subtitle {
            font-size: 11px;
            font-weight: 600;
            color: #A6B1E1;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            margin-bottom: 20px;
        }
        .login-card p {
            font-size: 13px;
            color: #6b7280;
            line-height: 1.6;
            margin-bottom: 25px;
        }
        /* 스트림릿 기본 폼 스타일 오버라이딩 */
        div[data-testid="stForm"] {
            border: none !important;
            padding: 0 !important;
            background: transparent !important;
            max-width: 320px !important;
            margin: 0 auto !important;
        }
        div[data-testid="stForm"] button {
            background-color: #424874 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 8px 0 !important;
            font-weight: 600 !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 10px rgba(66, 72, 116, 0.2) !important;
        }
        div[data-testid="stForm"] button:hover {
            background-color: #353a5e !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 15px rgba(66, 72, 116, 0.3) !important;
        }
        </style>
        <div class="login-card">
            <div class="login-logo">🔒</div>
            <div class="login-title">이지멤버스 BI 대시보드</div>
            <div class="login-subtitle">Secure Insight Portal</div>
            <p>본 시스템은 관계자 외 접근이 제한되어 있습니다.<br>보안 비밀번호를 입력해 주십시오.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 중앙 정렬용 컬럼 구성
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login_form", clear_on_submit=True):
            st.text_input("비밀번호 입력", type="password", key="password_input", placeholder="••••")
            submit = st.form_submit_button("인증 및 접속")
            if submit:
                password_entered()
                if st.session_state.get("password_correct", False):
                    st.rerun()
                else:
                    st.error("비밀번호가 올바르지 않습니다.")
        return False

# 비밀번호 검증 미통과 시 대시보드 렌더링 및 데이터 로딩 차단
if not check_password():
    st.stop()

# --- 1. 데이터 로드 및 전처리 ---
@st.cache_data
def load_and_clean_data():
    sheet_id = "1ZGwQoIfAM7TpgtyREW7EioOzHHJVqMtp1yz-ttdDS3Q"
    url_24 = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=2118374135"
    url_25 = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=1858969876"
    url_26 = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=527577312"
    
    df_24 = pd.read_csv(url_24)
    df_25 = pd.read_csv(url_25)
    df_26 = pd.read_csv(url_26)
    
    for df in [df_24, df_25, df_26]:
        df.columns = [str(c).strip() for c in df.columns]
        
    if '이지멤버스 브랜드' in df_24.columns: 
        df_24.rename(columns={'이지멤버스 브랜드': '브랜드'}, inplace=True)
    
    return df_24, df_25, df_26

def standardize_columns(df, year_prefix):
    mapping = {}
    for c in df.columns:
        cs = str(c).strip()
        if cs.startswith(f"{year_prefix}."):
            parts = cs.split('.')
            m_str = parts[1].strip()
            m_num = 10 if m_str == '1' else int(m_str)
            mapping[c] = f"{year_prefix}.{m_num:02d}"
            
    brand_cols = [c for c in df.columns if '브랜드' in c]
    if not brand_cols: return pd.DataFrame(columns=['브랜드'])
    brand_col = brand_cols[0]
    
    df_sub = df[[brand_col] + list(mapping.keys())].copy()
    df_sub.rename(columns={brand_col: '브랜드'}, inplace=True)
    df_sub.rename(columns=mapping, inplace=True)
    return df_sub

def clean_currency(x):
    if pd.isna(x): return 0
    if isinstance(x, str): x = x.replace(',', '')
    return pd.to_numeric(x, errors='coerce')

# --- 2. 마스터 데이터 병합 ---
try:
    df_24, df_25, df_26 = load_and_clean_data()
    
    d24 = standardize_columns(df_24, "24")
    d25 = standardize_columns(df_25, "25")
    d26 = standardize_columns(df_26, "26")
    
    all_brands = pd.concat([d24['브랜드'], d25['브랜드'], d26['브랜드']]).dropna().unique()
    all_brands = [b for b in all_brands if b != '합계']
    master = pd.DataFrame({'브랜드': all_brands})
    
    master = pd.merge(master, d24, on='브랜드', how='left')
    master = pd.merge(master, d25, on='브랜드', how='left')
    master = pd.merge(master, d26, on='브랜드', how='left')
    
    for c in master.columns:
        if c != '브랜드':
            master[c] = master[c].apply(clean_currency).fillna(0)

    c24 = [f"24.{m:02d}" for m in range(1, 13)]
    c25 = [f"25.{m:02d}" for m in range(1, 13)]
    c26 = [f"26.{m:02d}" for m in range(1, 13)]
    
    for c in c24 + c25 + c26:
        if c not in master.columns: master[c] = 0

    master['24년_실적'] = master[c24].sum(axis=1)
    master['25년_실적'] = master[c25].sum(axis=1)
    
    active_months_26 = [m for m in range(1, 13) if master[f"26.{m:02d}"].sum() > 0]
    last_month = max(active_months_26) if active_months_26 else 0
    
    ytd_25_cols = [f"25.{m:02d}" for m in range(1, last_month + 1)]
    ytd_26_cols = [f"26.{m:02d}" for m in range(1, last_month + 1)]
    
    master['25년_YTD'] = master[ytd_25_cols].sum(axis=1) if ytd_25_cols else 0
    master['26년_YTD'] = master[ytd_26_cols].sum(axis=1) if ytd_26_cols else 0

    def forecast_2026(row):
        if row['26년_YTD'] == 0: return 0
        if row['25년_YTD'] > 0 and row['25년_실적'] > 0:
            return row['25년_실적'] * (row['26년_YTD'] / row['25년_YTD'])
        elif last_month > 0:
            return (row['26년_YTD'] / last_month) * 12
        return 0

    master['26년_예상'] = master.apply(forecast_2026, axis=1)

    # --- 사이드바 및 레이아웃 ---
    st.sidebar.markdown("### ⚙️ 분석 설정")
    analysis_mode = st.sidebar.radio("분석 뷰 선택", [
        "📈 연간/누적 종합 트렌드", 
        "🧩 브랜드 포트폴리오 분석 (신규)",
        "📅 세부 월별 분석"
    ])

    st.title("📊 이지멤버스 BI 대시보드")
    if last_month > 0:
        st.caption(f"기준월: 2026년 {last_month}월 누적 데이터(YTD) 반영")

    # ==========================================
    # 모드 1: 연간 종합 트렌드 & 폭포수 차트
    # ==========================================
    if analysis_mode == "📈 연간/누적 종합 트렌드":
        tot_24 = master['24년_실적'].sum()
        tot_25 = master['25년_실적'].sum()
        tot_26_ytd = master['26년_YTD'].sum()
        tot_25_ytd = master['25년_YTD'].sum()
        tot_26_fcst = master['26년_예상'].sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("24년 총 매출", f"{tot_24/1e8:,.1f}억 원")
        c2.metric("25년 총 매출", f"{tot_25/1e8:,.1f}억 원", f"{(tot_25/tot_24*100-100 if tot_24 else 0):.1f}% (YoY)")
        c3.metric(f"26년 누적({last_month}개월)", f"{tot_26_ytd/1e8:,.1f}억 원", f"동기비 {(tot_26_ytd/tot_25_ytd*100-100 if tot_25_ytd else 0):.1f}%")
        c4.metric("26년 예상 매출(연말)", f"{tot_26_fcst/1e8:,.1f}억 원", f"예상 증감 {(tot_26_fcst/tot_25*100-100 if tot_25 else 0):.1f}%")
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📌 26년 누적 매출 증감 원인 (Waterfall)")
            # 폭포수 차트 로직
            inc_brands = master[master['26년_YTD'] > master['25년_YTD']]
            dec_brands = master[master['26년_YTD'] < master['25년_YTD']]
            inc_sum = inc_brands['26년_YTD'].sum() - inc_brands['25년_YTD'].sum()
            dec_sum = dec_brands['26년_YTD'].sum() - dec_brands['25년_YTD'].sum()
            
            fig_wf = go.Figure(go.Waterfall(
                orientation="v",
                measure=["absolute", "relative", "relative", "total"],
                x=["25년 동기간 누적", "성장 브랜드 기여", "하락 브랜드 손실", f"26년 {last_month}월 누적"],
                y=[tot_25_ytd, inc_sum, dec_sum, tot_26_ytd],
                text=[f"{v/1e8:,.1f}억" for v in [tot_25_ytd, inc_sum, dec_sum, tot_26_ytd]],
                textposition="outside",
                connector={"line":{"color":"rgb(63, 63, 63)"}},
                increasing={"marker":{"color":"#424874"}},
                decreasing={"marker":{"color":"#DCD6F7"}},
                totals={"marker":{"color":"#A6B1E1"}}
            ))
            st.plotly_chart(fig_wf, use_container_width=True)

        with col2:
            st.subheader("📌 3개년 월별 누적 실적(YTD) 비교")
            if last_month > 0:
                ytd_trend = pd.DataFrame({
                    '월': [f"{m}월" for m in range(1, 13)],
                    '24년': [master[f"24.{m:02d}"].sum() for m in range(1, 13)],
                    '25년': [master[f"25.{m:02d}"].sum() for m in range(1, 13)],
                    '26년': [master[f"26.{m:02d}"].sum() if m <= last_month else None for m in range(1, 13)]
                })
                fig_line = go.Figure()
                fig_line.add_trace(go.Scatter(x=ytd_trend['월'], y=ytd_trend['24년'].cumsum(), name='24년 누적', line=dict(dash='dot', color='gray')))
                fig_line.add_trace(go.Scatter(x=ytd_trend['월'], y=ytd_trend['25년'].cumsum(), name='25년 누적', line=dict(color='#A6B1E1')))
                fig_line.add_trace(go.Scatter(x=ytd_trend['월'], y=ytd_trend['26년'].cumsum(), name='26년 누적', mode='lines+markers', line=dict(color='#424874', width=3)))
                st.plotly_chart(fig_line, use_container_width=True)

    # ==========================================
    # 모드 2: 브랜드 포트폴리오 분석 (새로운 분석 기법 추가)
    # ==========================================
    elif analysis_mode == "🧩 브랜드 포트폴리오 분석 (신규)":
        st.markdown("### 🔍 제휴 브랜드 포지셔닝 및 건전성 진단")
        
        tab_scat, tab_heat = st.tabs(["🎯 포지셔닝 맵 (성장성 vs 규모)", "🔥 브랜드별 계절성 히트맵"])
        
        with tab_scat:
            st.subheader("매출 규모와 성장성 기반 전략 매트릭스 (BCG Matrix 응용)")
            st.caption("우상단(Star): 규모와 성장률이 모두 높은 핵심 브랜드 / 우하단(Cash Cow): 규모는 크지만 성장세가 둔화된 브랜드")
            
            df_scatter = master[(master['26년_YTD'] > 0) | (master['25년_YTD'] > 0)].copy()
            df_scatter['증감률(%)'] = np.where(df_scatter['25년_YTD']>0, (df_scatter['26년_YTD']-df_scatter['25년_YTD'])/df_scatter['25년_YTD']*100, 0)
            df_scatter['증감률(표시)'] = df_scatter['증감률(%)'].clip(lower=-50, upper=150) # 극단값 보정
            
            # 매출 상위 40개 브랜드만 표시 (시각적 깔끔함 유지)
            df_scatter_top = df_scatter.sort_values('26년_YTD', ascending=False).head(40)
            
            fig_scat = px.scatter(
                df_scatter_top, x="26년_YTD", y="증감률(표시)", text="브랜드",
                size="26년_YTD", color="증감률(표시)", color_continuous_scale="RdBu",
                hover_data={"26년_YTD":':,.0f', "증감률(%)":':.1f%'},
                labels={"26년_YTD": "26년 누적 매출액", "증감률(표시)": "전년비 성장률 (%)"}
            )
            fig_scat.update_traces(textposition='top center')
            fig_scat.add_hline(y=0, line_dash="dash", line_color="red")
            avg_rev = df_scatter_top['26년_YTD'].mean()
            fig_scat.add_vline(x=avg_rev, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_scat, use_container_width=True, height=600)

        with tab_heat:
            st.subheader("TOP 15 브랜드 월별 매출 트렌드 히트맵")
            st.caption("각 브랜드의 매출이 집중되는 '계절성'을 파악하여 프로모션 시기를 조율할 수 있습니다. (25년 1년치 데이터 기준)")
            
            top_15_brands = master.sort_values('25년_실적', ascending=False)['브랜드'].head(15).tolist()
            df_hm = master[master['브랜드'].isin(top_15_brands)].set_index('브랜드')[c25]
            
            fig_hm = px.imshow(
                df_hm, 
                labels=dict(x="월", y="브랜드", color="매출액"), 
                x=[f"{m}월" for m in range(1, 13)],
                color_continuous_scale="Blues",
                aspect="auto"
            )
            st.plotly_chart(fig_hm, use_container_width=True)

    # ==========================================
    # 모드 3: 세부 월별 분석 (파레토 차트 포함)
    # ==========================================
    elif analysis_mode == "📅 세부 월별 분석":
        tgt_m = st.sidebar.selectbox("분석 대상 월 선택", range(1, 13), index=(last_month-1 if last_month>0 else 0), format_func=lambda x: f"{x}월")
        m25_col, m26_col = f"25.{tgt_m:02d}", f"26.{tgt_m:02d}"

        val_25, val_26 = master[m25_col].sum(), master[m26_col].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric(f"25년 {tgt_m}월 매출", f"{val_25/1e8:,.1f}억 원")
        c2.metric(f"26년 {tgt_m}월 매출", f"{val_26/1e8:,.1f}억 원", f"{(val_26/val_25*100-100 if val_25 else 0):.1f}% (YoY)")
        c3.metric("해당 월 1위 브랜드", master.loc[master[m26_col].idxmax()]['브랜드'] if val_26 > 0 else "데이터 없음")
        st.markdown("---")

        if val_26 > 0:
            st.subheader(f"📌 {tgt_m}월 매출 집중도 분석 (Pareto Chart)")
            st.caption("상위 브랜드들이 전체 실적의 몇 %를 견인하는지 확인하는 포트폴리오 의존도 지표입니다.")
            
            df_m = master[['브랜드', m26_col]].copy()
            df_m = df_m[df_m[m26_col] > 0].sort_values(m26_col, ascending=False)
            df_m['누적비율(%)'] = (df_m[m26_col].cumsum() / df_m[m26_col].sum()) * 100
            
            # 상위 20개만 시각화
            df_pareto = df_m.head(20)
            
            fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
            fig_pareto.add_trace(go.Bar(x=df_pareto['브랜드'], y=df_pareto[m26_col], name="매출액", marker_color='#A6B1E1'), secondary_y=False)
            fig_pareto.add_trace(go.Scatter(x=df_pareto['브랜드'], y=df_pareto['누적비율(%)'], name="누적 점유율(%)", mode='lines+markers', line=dict(color='#424874', width=3)), secondary_y=True)
            
            fig_pareto.update_yaxes(title_text="매출액", secondary_y=False)
            fig_pareto.update_yaxes(title_text="누적 점유율 (%)", range=[0, 105], secondary_y=True)
            st.plotly_chart(fig_pareto, use_container_width=True)

        # --- [신규 추가] 세부 월별 심층 분석 도표 ---
        if last_month > 0:
            st.markdown("---")
            st.subheader(f"🔍 {tgt_m}월 세부 심층 분석 도표")
            
            # 차트 1 & 차트 2 가로 배치
            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                # 1. 월별 누적 매출 추이 (Area Chart)
                top_brands = ['GS25', '예스24', 'GS더프레시', '교보문고']
                area_data = []
                for m in range(1, last_month + 1):
                    col = f"26.{m:02d}"
                    m_label = f"{m}월"
                    
                    for brand in top_brands:
                        brand_row = master[master['브랜드'] == brand]
                        val = float(brand_row[col].iloc[0]) / 1e6 if not brand_row.empty else 0
                        area_data.append({'월': m_label, '브랜드': brand, '매출액': val})
                        
                    others_row = master[~master['브랜드'].isin(top_brands)]
                    others_val = float(others_row[col].sum()) / 1e6
                    area_data.append({'월': m_label, '브랜드': '기타 브랜드', '매출액': others_val})
                    
                df_area = pd.DataFrame(area_data)
                fig_monthly_area = px.area(
                    df_area, x="월", y="매출액", color="브랜드",
                    color_discrete_map={
                        'GS25': '#FF4D4D', '예스24': '#A6B1E1', 'GS더프레시': '#424874', 
                        '교보문고': '#DCD6F7', '기타 브랜드': '#8E94F2'
                    },
                    labels={"매출액": "매출액 (백만원)"}
                )
                fig_monthly_area.update_layout(
                    title={"text": f"26년 1월~{last_month}월 브랜드별 누적 매출 추이"},
                    hovermode="x unified",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#E5E7EB"),
                    xaxis=dict(gridcolor="rgba(255, 255, 255, 0.08)", tickfont=dict(color="#9CA3AF")),
                    yaxis=dict(gridcolor="rgba(255, 255, 255, 0.08)", tickfont=dict(color="#9CA3AF"))
                )
                st.plotly_chart(fig_monthly_area, use_container_width=True)
                
            with col_c2:
                # 2. 성장률-매출 비중 매트릭스 (BCG Scatter Chart)
                if val_26 > 0:
                    curr_col = f"26.{tgt_m:02d}"
                    prev_col = "25.12" if tgt_m == 1 else f"26.{(tgt_m-1):02d}"
                    
                    df_scatter = master[['브랜드', curr_col, prev_col]].copy()
                    df_scatter['category'] = df_scatter['브랜드'].map(lambda b: BRAND_CATEGORY_MAP.get(b, '기타 서비스'))
                    
                    total_curr = df_scatter[curr_col].sum()
                    df_scatter['share'] = np.where(total_curr > 0, (df_scatter[curr_col] / total_curr) * 100, 0)
                    df_scatter['growth'] = np.where(
                        df_scatter[prev_col] > 0,
                        ((df_scatter[curr_col] - df_scatter[prev_col]) / df_scatter[prev_col]) * 100,
                        0
                    )
                    
                    df_scatter = df_scatter[df_scatter[curr_col] > 0].copy()
                    df_scatter['매출액(백만원)'] = df_scatter[curr_col] / 1e6
                    df_scatter['성장률(%)'] = df_scatter['growth'].clip(-50, 150)
                    
                    fig_monthly_bcg = px.scatter(
                        df_scatter, x="share", y="성장률(%)", text="브랜드",
                        size="매출액(백만원)", color="category",
                        color_discrete_map={
                            '유통/편의점': '#FF4D4D', '도서/교육': '#A6B1E1', 
                            '식음료(F&B)': '#DCD6F7', '뷰티/케어': '#8E94F2', 
                            '기타 서비스': '#6B7280'
                        },
                        labels={"share": "매출 비중 (%)", "성장률(%)": "전월비 성장률 (%)"}
                    )
                    fig_monthly_bcg.update_traces(textposition='top center', marker=dict(line=dict(width=1, color='rgba(255, 255, 255, 0.5)')))
                    fig_monthly_bcg.add_hline(y=0, line_dash="dash", line_color="#EF4444")
                    
                    avg_share = float(df_scatter['share'].mean()) if not df_scatter.empty else 0
                    fig_monthly_bcg.add_vline(x=avg_share, line_dash="dash", line_color="#9CA3AF")
                    fig_monthly_bcg.update_layout(
                        title={"text": f"{tgt_m}월 성장률-매출 비중 매트릭스 (BCG Matrix)"},
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#E5E7EB"),
                        xaxis=dict(gridcolor="rgba(255, 255, 255, 0.08)", tickfont=dict(color="#9CA3AF")),
                        yaxis=dict(gridcolor="rgba(255, 255, 255, 0.08)", tickfont=dict(color="#9CA3AF"))
                    )
                    st.plotly_chart(fig_monthly_bcg, use_container_width=True)
                else:
                    st.info("성장률 분석을 위한 당월 매출 데이터가 존재하지 않습니다.")
                    
            # 3. 카테고리별 100% 기준 누적 막대 차트 (Bar Chart)
            cat_data = []
            for m in range(1, last_month + 1):
                col = f"26.{m:02d}"
                m_label = f"{m}월"
                
                m_df = master[['브랜드', col]].copy()
                m_df['category'] = m_df['브랜드'].map(lambda b: BRAND_CATEGORY_MAP.get(b, '기타 서비스'))
                cat_rev = m_df.groupby('category')[col].sum().reset_index()
                
                total_m = cat_rev[col].sum()
                for _, row in cat_rev.iterrows():
                    share = (row[col] / total_m * 100) if total_m > 0 else 0
                    cat_data.append({
                        '월': m_label,
                        '카테고리': row['category'],
                        '비중(%)': share,
                        '매출액': row[col] / 1e6
                    })
                    
            df_cat = pd.DataFrame(cat_data)
            fig_monthly_cat = px.bar(
                df_cat, x="월", y="비중(%)", color="카테고리",
                color_discrete_map={
                    '유통/편의점': '#FF4D4D', '도서/교육': '#A6B1E1', 
                    '식음료(F&B)': '#DCD6F7', '뷰티/케어': '#8E94F2', 
                    '기타 서비스': '#6B7280'
                },
                labels={"비중(%)": "매출 비중 (%)"},
                barmode="relative"
            )
            fig_monthly_cat.update_layout(
                title={"text": f"26년 1월~{last_month}월 카테고리별 매출 비중 (100% Stacked Bar)"},
                yaxis=dict(range=[0, 100]),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E5E7EB"),
                xaxis=dict(gridcolor="rgba(255, 255, 255, 0.08)", tickfont=dict(color="#9CA3AF")),
                yaxis=dict(gridcolor="rgba(255, 255, 255, 0.08)", tickfont=dict(color="#9CA3AF"))
            )
            st.plotly_chart(fig_monthly_cat, use_container_width=True)

        # --- 브랜드별 상세 매출 추이 그래프 (표의 윗부분) ---
        if 'selected_brand' not in st.session_state:
            st.session_state['selected_brand'] = None
            
        m_data = master[['브랜드', m26_col, m25_col]].copy()
        m_data['증감액'] = m_data[m26_col] - m_data[m25_col]
        m_data['증감률(%)'] = np.where(m_data[m25_col]>0, (m_data['증감액']/m_data[m25_col]*100).round(1), 0)
        m_data = m_data[(m_data[m26_col] > 0) | (m_data[m25_col] > 0)]
        
        # 기본값 정렬 후 브랜드 목록 추출
        m_data_sorted = m_data.sort_values(m26_col, ascending=False).copy()
        sorted_brands = m_data_sorted['브랜드'].tolist()
        
        # 기본 선택 브랜드 설정
        if sorted_brands and (st.session_state['selected_brand'] not in sorted_brands):
            st.session_state['selected_brand'] = sorted_brands[0]
            
        selected_brand = st.session_state['selected_brand']
        
        if selected_brand:
            st.markdown("---")
            st.subheader(f"📈 {selected_brand} 월별 매출 비교 추이 (단위: 백만원)")
            
            # 선택된 브랜드의 연간 데이터 추출 및 백만원 단위 변환 (25년 1~12월, 26년 1~last_month)
            brand_row = master[master['브랜드'] == selected_brand].iloc[0]
            sales_25_list = [float(brand_row[f"25.{m:02d}"]) / 1e6 for m in range(1, 13)]
            sales_26_list = [float(brand_row[f"26.{m:02d}"]) / 1e6 for m in range(1, last_month + 1)] if last_month > 0 else []
            
            months = [f"{m}월" for m in range(1, 13)]
            
            fig_brand = go.Figure()
            # 25년도 전체 트렌드 - 얇고 차분한 회청색 점선 (#A6B1E1)
            fig_brand.add_trace(go.Scatter(
                x=months, 
                y=sales_25_list, 
                name='25년 매출 (전체)', 
                line=dict(color='#A6B1E1', width=2, dash='dot'),
                hovertemplate="<b>25년 %{x}</b><br>매출액: %{y:,.1f}백만원<extra></extra>",
                hoverlabel=dict(
                    bgcolor='rgba(30, 30, 30, 0.9)',
                    bordercolor='#A6B1E1',
                    font=dict(color='#A6B1E1')
                )
            ))
            # 26년도 (데이터가 존재하는 월까지) - 굵고 선명한 코랄 레드 (#FF4D4D)
            if last_month > 0:
                fig_brand.add_trace(go.Scatter(
                    x=months[:last_month], 
                    y=sales_26_list, 
                    name='26년 매출 (누적)', 
                    mode='lines+markers', 
                    line=dict(color='#FF4D4D', width=4),
                    marker=dict(size=8),
                    hovertemplate="<b>26년 %{x}</b><br>매출액: %{y:,.1f}백만원<extra></extra>",
                    hoverlabel=dict(
                        bgcolor='rgba(30, 30, 30, 0.9)',
                        bordercolor='#FF4D4D',
                        font=dict(color='#FF4D4D')
                    )
                ))
                
            fig_brand.update_layout(
                xaxis_title="월",
                yaxis_title="매출액 (백만원)",
                hovermode="closest",
                margin=dict(l=40, r=40, t=20, b=40)
            )
            st.plotly_chart(fig_brand, use_container_width=True)
            
        st.markdown("---")
        st.subheader(f"📊 {tgt_m}월 전체 브랜드 실적 현황")
        st.caption("아래 표에서 브랜드를 클릭하시면 상단의 매출 추이 그래프가 해당 브랜드로 변경됩니다.")

        # 동적 헤더 이름 설정: 26년 X월, 25년 X월
        col_26_name = f"26년 {tgt_m}월"
        col_25_name = f"25년 {tgt_m}월"

        m_data_display = m_data_sorted.copy()
        m_data_display = m_data_display.rename(columns={
            m26_col: col_26_name,
            m25_col: col_25_name
        })
        m_data_display = m_data_display[['브랜드', col_26_name, col_25_name, '증감액', '증감률(%)']]

        # st.dataframe을 위한 column_config 설정 (정렬을 위해 원본 데이터 타입을 유지하되 표시 형식만 기호 및 쉼표 표기)
        col_config = {
            "브랜드": st.column_config.TextColumn("브랜드"),
            col_26_name: st.column_config.NumberColumn(col_26_name, format="%,.0f"),
            col_25_name: st.column_config.NumberColumn(col_25_name, format="%,.0f"),
            "증감액": st.column_config.NumberColumn("증감액", format="%+,.0f"),
            "증감률(%)": st.column_config.NumberColumn("증감률", format="%+,.1f%%")
        }

        # 1.35.0+ 테이블 행 선택 처리 지원
        try:
            event = st.dataframe(
                m_data_display,
                hide_index=True,
                use_container_width=True,
                column_config=col_config,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            if event and "rows" in event.selection and event.selection["rows"]:
                selected_idx = event.selection["rows"][0]
                clicked_brand = m_data_display.iloc[selected_idx]['브랜드']
                if st.session_state['selected_brand'] != clicked_brand:
                    st.session_state['selected_brand'] = clicked_brand
                    st.rerun()
        except Exception as e:
            # 하위 버전 스트림릿용 폴백
            st.dataframe(m_data_display, hide_index=True, use_container_width=True, column_config=col_config)
            fallback_idx = sorted_brands.index(st.session_state['selected_brand']) if st.session_state['selected_brand'] in sorted_brands else 0
            fallback_brand = st.selectbox("상세 매출 추이를 확인할 브랜드 선택 (버전 폴백)", sorted_brands, index=fallback_idx)
            if st.session_state['selected_brand'] != fallback_brand:
                st.session_state['selected_brand'] = fallback_brand
                st.rerun()


except Exception as e:
    st.error(f"오류 발생: {e}")

