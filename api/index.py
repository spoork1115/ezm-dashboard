from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import time

app = FastAPI(title="EasyMembers BI Dashboard API")

# Enable CORS for local development and integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Memory Cache implementation ---
CACHE = {}
CACHE_TTL = 600  # 10 minutes cache TTL

def clean_currency(x):
    if pd.isna(x):
        return 0
    if isinstance(x, str):
        x = x.replace(',', '')
    return pd.to_numeric(x, errors='coerce')

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
    if not brand_cols:
        return pd.DataFrame(columns=['브랜드'])
    brand_col = brand_cols[0]
    
    df_sub = df[[brand_col] + list(mapping.keys())].copy()
    df_sub.rename(columns={brand_col: '브랜드'}, inplace=True)
    df_sub.rename(columns={k: v for k, v in mapping.items() if k in df_sub.columns}, inplace=True)
    return df_sub

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

def get_dashboard_data():
    now = time.time()
    if 'data' in CACHE and (now - CACHE['timestamp'] < CACHE_TTL):
        return CACHE['data']
        
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
            if c not in master.columns: 
                master[c] = 0

        master['24년_실적'] = master[c24].sum(axis=1)
        master['25년_실적'] = master[c25].sum(axis=1)
        
        active_months_26 = [m for m in range(1, 13) if master[f"26.{m:02d}"].sum() > 0]
        last_month = max(active_months_26) if active_months_26 else 0
        
        ytd_25_cols = [f"25.{m:02d}" for m in range(1, last_month + 1)]
        ytd_26_cols = [f"26.{m:02d}" for m in range(1, last_month + 1)]
        
        master['25년_YTD'] = master[ytd_25_cols].sum(axis=1) if ytd_25_cols else 0
        master['26년_YTD'] = master[ytd_26_cols].sum(axis=1) if ytd_26_cols else 0

        def forecast_2026(row):
            if row['26년_YTD'] == 0: 
                return 0
            if row['25년_YTD'] > 0 and row['25년_실적'] > 0:
                return row['25년_실적'] * (row['26년_YTD'] / row['25년_YTD'])
            elif last_month > 0:
                return (row['26년_YTD'] / last_month) * 12
            return 0

        master['26년_예상'] = master.apply(forecast_2026, axis=1)
        
        CACHE['data'] = (master, last_month)
        CACHE['timestamp'] = now
        return master, last_month
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data loading failed: {str(e)}")

def apply_dark_theme(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB", family="Outfit, system-ui, sans-serif"),
        margin=dict(l=40, r=40, t=50, b=40),
        xaxis=dict(
            gridcolor="rgba(255, 255, 255, 0.08)",
            zerolinecolor="rgba(255, 255, 255, 0.15)",
            tickfont=dict(color="#9CA3AF")
        ),
        yaxis=dict(
            gridcolor="rgba(255, 255, 255, 0.08)",
            zerolinecolor="rgba(255, 255, 255, 0.15)",
            tickfont=dict(color="#9CA3AF")
        )
    )
    return fig

@app.get("/api/meta")
def get_meta():
    master, last_month = get_dashboard_data()
    return {
        "last_month": int(last_month),
        "brands": master['브랜드'].tolist()
    }

@app.get("/api/trend")
def get_trend_data():
    master, last_month = get_dashboard_data()
    
    tot_24 = float(master['24년_실적'].sum())
    tot_25 = float(master['25년_실적'].sum())
    tot_26_ytd = float(master['26년_YTD'].sum())
    tot_25_ytd = float(master['25년_YTD'].sum())
    tot_26_fcst = float(master['26년_예상'].sum())

    # 1. Waterfall Chart
    inc_brands = master[master['26년_YTD'] > master['25년_YTD']]
    dec_brands = master[master['26년_YTD'] < master['25년_YTD']]
    inc_sum = float(inc_brands['26년_YTD'].sum() - inc_brands['25년_YTD'].sum())
    dec_sum = float(dec_brands['26년_YTD'].sum() - dec_brands['25년_YTD'].sum())
    
    fig_wf = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "total"],
        x=["25년 동기간 누적", "성장 브랜드 기여", "하락 브랜드 손실", f"26년 {last_month}월 누적"],
        y=[tot_25_ytd, inc_sum, dec_sum, tot_26_ytd],
        text=[f"{v/1e8:,.1f}억" for v in [tot_25_ytd, inc_sum, dec_sum, tot_26_ytd]],
        textposition="outside",
        connector={"line":{"color":"rgba(255, 255, 255, 0.3)"}},
        increasing={"marker":{"color":"#10B981"}}, # Emerald Green
        decreasing={"marker":{"color":"#EF4444"}}, # Rose Red
        totals={"marker":{"color":"#3B82F6"}}       # Blue
    ))
    fig_wf.update_layout(title={"text": "26년 누적 매출 증감 원인 분석 (Waterfall)"})
    fig_wf = apply_dark_theme(fig_wf)

    # 2. Cumulative Line Chart
    ytd_trend = pd.DataFrame({
        '월': [f"{m}월" for m in range(1, 13)],
        '24년': [float(master[f"24.{m:02d}"].sum()) for m in range(1, 13)],
        '25년': [float(master[f"25.{m:02d}"].sum()) for m in range(1, 13)],
        '26년': [float(master[f"26.{m:02d}"].sum()) if m <= last_month else None for m in range(1, 13)]
    })
    
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=ytd_trend['월'], y=ytd_trend['24년'].cumsum(), name='24년 누적', line=dict(dash='dot', color='rgba(156, 163, 175, 0.5)')))
    fig_line.add_trace(go.Scatter(x=ytd_trend['월'], y=ytd_trend['25년'].cumsum(), name='25년 누적', line=dict(color='#818CF8', width=2))) # Indigo Light
    fig_line.add_trace(go.Scatter(x=ytd_trend['월'], y=ytd_trend['26년'].cumsum(), name='26년 누적', mode='lines+markers', line=dict(color='#3B82F6', width=4))) # Blue Bold
    
    fig_line.update_layout(title={"text": "3개년 월별 누적 실적(YTD) 비교"})
    fig_line = apply_dark_theme(fig_line)

    return {
        "kpi": {
            "tot_24": tot_24,
            "tot_25": tot_25,
            "tot_26_ytd": tot_26_ytd,
            "tot_25_ytd": tot_25_ytd,
            "tot_26_fcst": tot_26_fcst,
            "yoy_25": float(tot_25 / tot_24 * 100 - 100) if tot_24 else 0,
            "yoy_26_ytd": float(tot_26_ytd / tot_25_ytd * 100 - 100) if tot_25_ytd else 0,
            "yoy_26_fcst": float(tot_26_fcst / tot_25 * 100 - 100) if tot_25 else 0
        },
        "charts": {
            "waterfall": json.loads(fig_wf.to_json()),
            "line": json.loads(fig_line.to_json())
        }
    }

@app.get("/api/portfolio")
def get_portfolio_data():
    master, last_month = get_dashboard_data()
    
    # 1. Scatter Chart
    df_scatter = master[(master['26년_YTD'] > 0) | (master['25년_YTD'] > 0)].copy()
    df_scatter['증감률(%)'] = np.where(df_scatter['25년_YTD'] > 0, (df_scatter['26년_YTD'] - df_scatter['25년_YTD']) / df_scatter['25년_YTD'] * 100, 0)
    df_scatter['증감률(표시)'] = df_scatter['증감률(%)'].clip(lower=-50, upper=150)
    
    df_scatter_top = df_scatter.sort_values('26년_YTD', ascending=False).head(40)
    
    fig_scat = px.scatter(
        df_scatter_top, 
        x="26년_YTD", 
        y="증감률(표시)", 
        text="브랜드",
        size="26년_YTD", 
        color="증감률(표시)", 
        color_continuous_scale="RdBu",
        labels={"26년_YTD": "26년 누적 매출액", "증감률(표시)": "전년비 성장률 (%)"}
    )
    fig_scat.update_traces(textposition='top center', marker=dict(line=dict(width=1, color='rgba(255, 255, 255, 0.5)')))
    fig_scat.add_hline(y=0, line_dash="dash", line_color="#EF4444")
    avg_rev = float(df_scatter_top['26년_YTD'].mean())
    fig_scat.add_vline(x=avg_rev, line_dash="dash", line_color="#9CA3AF")
    fig_scat.update_layout(title={"text": "전략적 브랜드 매트릭스 (성장성 vs 규모)"})
    fig_scat = apply_dark_theme(fig_scat)

    # 2. Heatmap Chart
    top_15_brands = master.sort_values('25년_실적', ascending=False)['브랜드'].head(15).tolist()
    c25 = [f"25.{m:02d}" for m in range(1, 13)]
    df_hm = master[master['브랜드'].isin(top_15_brands)].set_index('브랜드')[c25]
    
    fig_hm = px.imshow(
        df_hm, 
        labels=dict(x="월", y="브랜드", color="매출액"), 
        x=[f"{m}월" for m in range(1, 13)],
        color_continuous_scale="Blues",
        aspect="auto"
    )
    fig_hm.update_layout(title={"text": "TOP 15 브랜드 월별 매출 트렌드 히트맵 (2025년)"})
    fig_hm = apply_dark_theme(fig_hm)

    return {
        "charts": {
            "scatter": json.loads(fig_scat.to_json()),
            "heatmap": json.loads(fig_hm.to_json())
        }
    }

@app.get("/api/monthly")
def get_monthly_data(month: int = Query(..., ge=1, le=12)):
    master, last_month = get_dashboard_data()
    
    m25_col, m26_col = f"25.{month:02d}", f"26.{month:02d}"
    val_25 = float(master[m25_col].sum())
    val_26 = float(master[m26_col].sum())
    
    if val_26 > 0:
        top_brand_row = master.loc[master[m26_col].idxmax()]
        top_brand = top_brand_row['브랜드']
    else:
        top_brand = "데이터 없음"
        
    # Pareto Chart logic
    fig_pareto = None
    if val_26 > 0:
        df_m = master[['브랜드', m26_col]].copy()
        df_m = df_m[df_m[m26_col] > 0].sort_values(m26_col, ascending=False)
        df_m['누적비율(%)'] = (df_m[m26_col].cumsum() / df_m[m26_col].sum()) * 100
        df_pareto = df_m.head(20)
        
        fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
        fig_pareto.add_trace(go.Bar(x=df_pareto['브랜드'], y=df_pareto[m26_col], name="매출액", marker_color='#818CF8'), secondary_y=False)
        fig_pareto.add_trace(go.Scatter(x=df_pareto['브랜드'], y=df_pareto['누적비율(%)'], name="누적 점유율(%)", mode='lines+markers', line=dict(color='#F59E0B', width=3)), secondary_y=True) # Amber color
        
        fig_pareto.update_yaxes(title_text="매출액", secondary_y=False)
        fig_pareto.update_yaxes(title_text="누적 점유율 (%)", range=[0, 105], secondary_y=True)
        fig_pareto.update_layout(title={"text": f"{month}월 매출 집중도 분석 (Pareto Chart)"})
        fig_pareto = apply_dark_theme(fig_pareto)

    # Ranking logic
    m_data = master[['브랜드', m26_col, m25_col]].copy()
    m_data['증감액'] = m_data[m26_col] - m_data[m25_col]
    m_data['증감률(%)'] = np.where(m_data[m25_col] > 0, (m_data['증감액'] / m_data[m25_col] * 100).round(1), 0)
    m_data = m_data[(m_data[m26_col] > 0) | (m_data[m25_col] > 0)]
    
    # Sort and format tables
    top_up = m_data.sort_values('증감액', ascending=False).head(10)
    top_down = m_data.sort_values('증감액', ascending=True).head(10)
    
    def convert_to_records(df):
        records = []
        for _, row in df.iterrows():
            records.append({
                "브랜드": row['브랜드'],
                "sales_26": float(row[m26_col]),
                "sales_25": float(row[m25_col]),
                "diff": float(row['증감액']),
                "pct": float(row['증감률(%)'])
            })
        return records

    return {
        "kpi": {
            "sales_25": val_25,
            "sales_26": val_26,
            "yoy": float(val_26 / val_25 * 100 - 100) if val_25 else 0,
            "top_brand": top_brand
        },
        "chart": json.loads(fig_pareto.to_json()) if fig_pareto else None,
        "tables": {
            "top_up": convert_to_records(top_up),
            "top_down": convert_to_records(top_down)
        }
    }
