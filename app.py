"""
股票智能分析平台 - 主程式
執行方式：streamlit run app.py
"""

import streamlit as st
import sys
import os
import re
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ───────────────────────────────────────────────
# 頁面基本設定（必須是第一個 Streamlit 呼叫）
# ───────────────────────────────────────────────
st.set_page_config(
    page_title="股票智能分析平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ───────────────────────────────────────────────
# 全域 CSS
# ───────────────────────────────────────────────
st.markdown("""
<style>
/* 主標題 */
.main-title {
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(90deg, #00b09b, #5352ed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0;
}
.main-subtitle {
    font-size: 0.95rem;
    color: #a4b0be;
    margin-top: 2px;
}

/* 區塊標題 */
.section-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #00b09b;
    border-left: 4px solid #00b09b;
    padding-left: 10px;
    margin: 18px 0 10px 0;
}

/* 指標卡片 */
.metric-row { display: flex; gap: 12px; flex-wrap: wrap; margin: 10px 0; }
.metric-card {
    background: #1a1f2e;
    border-radius: 10px;
    padding: 14px 18px;
    min-width: 130px;
    border: 1px solid #2d3436;
    flex: 1;
}
.metric-card .label { font-size: 0.75rem; color: #a4b0be; }
.metric-card .value { font-size: 1.35rem; font-weight: 700; color: #dfe6e9; }
.metric-card .delta { font-size: 0.8rem; margin-top: 2px; }

/* 風險標籤 */
.badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 700;
}
.badge-green  { background: rgba(0,176,155,0.2); color: #00b09b; }
.badge-blue   { background: rgba(83,82,237,0.2); color: #7a79f0; }
.badge-yellow { background: rgba(255,165,2,0.2);  color: #ffa502; }
.badge-orange { background: rgba(255,107,0,0.2);  color: #ff6b00; }
.badge-red    { background: rgba(255,71,87,0.2);  color: #ff4757; }

/* 快速按鈕 */
.quick-btn { cursor: pointer; }

/* sidebar 輸入框 */
div[data-testid="stSidebar"] .stTextInput input {
    background: #1a1f2e;
    border: 1px solid #2d3436;
    color: #dfe6e9;
    border-radius: 8px;
}

/* 隱藏 streamlit 預設 footer */
footer { visibility: hidden; }

/* 分析 tab 內容 */
.analysis-box {
    background: #141820;
    border-radius: 8px;
    padding: 18px 22px;
    border: 1px solid #2d3436;
    line-height: 1.9;
}
</style>
""", unsafe_allow_html=True)


# ───────────────────────────────────────────────
# 常數
# ───────────────────────────────────────────────
POPULAR_STOCKS = {
    "台積電 2330": "2330",
    "聯發科 2454": "2454",
    "鴻海 2317":   "2317",
    "台達電 2308": "2308",
    "NVIDIA":      "NVDA",
    "Apple":       "AAPL",
    "Tesla":       "TSLA",
    "Amazon":      "AMZN",
}

RISK_BADGE = {
    "優質":    ("badge-green",  "🟢 優質"),
    "良好":    ("badge-blue",   "🔵 良好"),
    "普通":    ("badge-yellow", "🟡 普通"),
    "偏高風險": ("badge-orange","🟠 偏高風險"),
    "高風險":  ("badge-red",    "🔴 高風險"),
}

FEATURE_LIST = [
    ("📋", "財務健康檢查", True),
    ("📈", "技術面分析",   True),
    ("🏭", "產業競爭分析", True),
    ("🔍", "隱藏風險偵測", True),
    ("💎", "內在價值估算", True),
]


# ───────────────────────────────────────────────
# 工具函式
# ───────────────────────────────────────────────
def fmt(v, suffix="", decimals=1, prefix=""):
    if v is None:
        return "N/A"
    return f"{prefix}{v:.{decimals}f}{suffix}"

def color_val(v, good_above=None, bad_above=None, suffix="%", decimals=1):
    """回傳帶色彩 HTML 的數值字串"""
    if v is None:
        return "<span style='color:#a4b0be'>N/A</span>"
    s = f"{v:.{decimals}f}{suffix}"
    if good_above is not None and v >= good_above:
        return f"<span style='color:#00b09b;font-weight:700'>{s}</span>"
    if bad_above is not None and v >= bad_above:
        return f"<span style='color:#ff4757;font-weight:700'>{s}</span>"
    return f"<span style='color:#dfe6e9'>{s}</span>"


# ───────────────────────────────────────────────
# 歡迎畫面
# ───────────────────────────────────────────────
# Dashboard 工具函式
# ───────────────────────────────────────────────
@st.cache_data(ttl=300)   # 快取5分鐘
def _fetch_market_snapshot():
    """取得市場即時快照（大盤指數 + 熱門股）"""
    import yfinance as yf
    watch = {
        "台灣加權": "^TWII",
        "S&P 500":  "^GSPC",
        "NASDAQ":   "^IXIC",
        "台積電":   "2330.TW",
        "聯發科":   "2454.TW",
        "NVIDIA":   "NVDA",
        "Apple":    "AAPL",
        "Tesla":    "TSLA",
    }
    result = {}
    for name, symbol in watch.items():
        try:
            t    = yf.Ticker(symbol)
            info = t.fast_info
            price = float(info.last_price or 0)
            prev  = float(info.previous_close or price)
            chg   = price - prev
            pct   = chg / prev * 100 if prev else 0
            result[name] = {
                'symbol': symbol,
                'price':  price,
                'chg':    chg,
                'pct':    pct,
            }
        except Exception:
            result[name] = None
    return result


def _mini_sparkline(symbol: str) -> "go.Figure":
    """小型走勢圖（1個月）"""
    import yfinance as yf
    import plotly.graph_objects as go
    try:
        hist = yf.Ticker(symbol).history(period='1mo')
        if hist.empty:
            raise ValueError
        close = hist['Close']
        color = "#00c896" if float(close.iloc[-1]) >= float(close.iloc[0]) else "#ff4444"
        fig = go.Figure(go.Scatter(
            x=list(range(len(close))), y=close.tolist(),
            mode='lines', line=dict(color=color, width=1.5),
            fill='tozeroy', fillcolor=color.replace(')', ',0.1)').replace('rgb', 'rgba'),
        ))
        fig.update_layout(
            margin=dict(t=0, b=0, l=0, r=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=50, width=120,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            showlegend=False,
        )
        return fig
    except Exception:
        return None


# ───────────────────────────────────────────────
# 歡迎 / Dashboard 首頁
# ───────────────────────────────────────────────
def show_welcome():
    import plotly.graph_objects as go

    # ══ 主標題 ══
    st.markdown("""
    <div style='text-align:center;padding:20px 0 8px 0'>
        <div style='font-size:2.6rem;font-weight:900;
             background:linear-gradient(90deg,#00b09b,#4a9eff,#9b59b6);
             -webkit-background-clip:text;-webkit-text-fill-color:transparent;
             line-height:1.2'>
            📊 股票智能分析平台
        </div>
        <div style='font-size:1rem;color:#a4b0be;margin-top:6px'>
            Taiwan & US Stocks · 5 大分析功能 · AI 輔助報告
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ══ 市場即時行情 ══
    st.markdown('<p class="section-title">🌐 市場即時行情</p>', unsafe_allow_html=True)

    with st.spinner("載入行情中..."):
        snapshot = _fetch_market_snapshot()

    # 大盤指數（前3個）
    idx_names = ["台灣加權", "S&P 500", "NASDAQ"]
    idx_cols  = st.columns(3)
    for col, name in zip(idx_cols, idx_names):
        d = snapshot.get(name)
        with col:
            if d:
                arrow  = "▲" if d['pct'] >= 0 else "▼"
                color  = "#00c896" if d['pct'] >= 0 else "#ff4444"
                price_fmt = f"{d['price']:,.0f}" if d['price'] > 100 else f"{d['price']:,.2f}"
                st.markdown(f"""
                <div style='background:#1a1f2e;border-radius:12px;padding:16px 20px;
                            border:1px solid #2d3436;text-align:center'>
                    <div style='font-size:0.78rem;color:#a4b0be'>{name}</div>
                    <div style='font-size:1.6rem;font-weight:800;color:#dfe6e9'>{price_fmt}</div>
                    <div style='font-size:1rem;font-weight:700;color:{color}'>
                        {arrow} {abs(d['pct']):.2f}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style='background:#1a1f2e;border-radius:12px;padding:16px 20px;
                            border:1px solid #2d3436;text-align:center;color:#555'>
                    {name}<br>—
                </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 個股行情
    stock_names = ["台積電", "聯發科", "NVIDIA", "Apple", "Tesla"]
    s_cols = st.columns(5)
    for col, name in zip(s_cols, stock_names):
        d = snapshot.get(name)
        with col:
            if d:
                arrow = "▲" if d['pct'] >= 0 else "▼"
                color = "#00c896" if d['pct'] >= 0 else "#ff4444"
                price_fmt = (f"{d['price']:,.1f}" if d['price'] > 100
                             else f"{d['price']:,.2f}")
                # 點擊直接分析
                code = d['symbol'].replace('.TW', '')
                st.markdown(f"""
                <div style='background:#141820;border-radius:10px;padding:12px;
                            border:1px solid #2d3436;text-align:center;cursor:pointer'>
                    <div style='font-size:0.72rem;color:#a4b0be'>{name}</div>
                    <div style='font-size:1.1rem;font-weight:700;color:#dfe6e9'>{price_fmt}</div>
                    <div style='font-size:0.85rem;font-weight:600;color:{color}'>
                        {arrow}{abs(d['pct']):.2f}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style='background:#141820;border-radius:10px;padding:12px;
                            border:1px solid #2d3436;text-align:center;color:#555'>
                    {name}<br>—
                </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ══ 五大功能卡片 ══
    st.markdown('<p class="section-title">🚀 五大分析功能</p>', unsafe_allow_html=True)

    FEATURE_CARDS = [
        {
            "icon": "📋", "name": "財務健康檢查",
            "color": "#00b09b", "code": "財務健康檢查",
            "desc": "3年財務趨勢 · 五維雷達圖",
            "items": ["營收/毛利/淨利率趨勢", "現金流品質評估", "負債結構分析",
                      "P/E · P/B · P/S 估值", "0-100 健康風險評分"],
        },
        {
            "icon": "📈", "name": "技術面分析",
            "color": "#4a9eff", "code": "技術面分析",
            "desc": "K線 · 均線 · 籌碼 · 支撐阻力",
            "items": ["RSI · MACD · KD · 布林通道", "5均線排列強弱訊號",
                      "支撐/阻力自動偵測", "三大法人買賣超（台股）",
                      "ATR 停損進場建議"],
        },
        {
            "icon": "🏭", "name": "產業競爭分析",
            "color": "#9b59b6", "code": "產業競爭分析",
            "desc": "產業定位 · SWOT · 競爭矩陣",
            "items": ["市場規模成長預測", "同業財務指標對比",
                      "競爭定位五維雷達", "SWOT 分析", "AI 深度產業報告"],
        },
        {
            "icon": "🔍", "name": "隱藏風險偵測",
            "color": "#ff8c00", "code": "隱藏風險偵測",
            "desc": "六大財報異常信號掃描",
            "items": ["應收帳款 / 存貨異常", "CFO vs 淨利品質",
                      "債務壓力 Altman Z-Score", "Beneish M-Score 財報操縱",
                      "Piotroski F-Score 財務強度"],
        },
        {
            "icon": "💎", "name": "內在價值估算",
            "color": "#f0c040", "code": "內在價值估算",
            "desc": "DCF · DDM · 安全邊際",
            "items": ["DCF 三情境現金流折現", "DDM 股息折現模型",
                      "歷史 P/E 帶狀比較", "同業相對估值", "敏感度矩陣分析"],
        },
    ]

    feat_cols = st.columns(5)
    for col, card in zip(feat_cols, FEATURE_CARDS):
        with col:
            items_html = "".join(
                f"<div style='font-size:0.72rem;color:#a4b0be;"
                f"padding:2px 0;border-bottom:1px solid #2a2d3e'>✦ {item}</div>"
                for item in card['items']
            )
            st.markdown(f"""
            <div style='background:#1a1f2e;border-radius:12px;padding:16px;
                        border:1px solid {card['color']}44;height:100%'>
                <div style='font-size:1.8rem;text-align:center'>{card['icon']}</div>
                <div style='font-size:0.95rem;font-weight:700;color:{card['color']};
                            text-align:center;margin:6px 0 2px 0'>{card['name']}</div>
                <div style='font-size:0.72rem;color:#a4b0be;text-align:center;
                            margin-bottom:10px'>{card['desc']}</div>
                {items_html}
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f"使用 {card['icon']}", use_container_width=True,
                         key=f"feat_card_{card['code']}"):
                st.session_state['pending_feature'] = card['code']
                st.rerun()

    st.markdown("---")

    # ══ 熱門快速查詢 ══
    st.markdown('<p class="section-title">⚡ 熱門股票快速查詢</p>', unsafe_allow_html=True)
    cols = st.columns(len(POPULAR_STOCKS))
    for idx, (label, code) in enumerate(POPULAR_STOCKS.items()):
        with cols[idx]:
            if st.button(label, use_container_width=True, key=f"quick_{code}"):
                st.session_state.stock_input = code
                st.session_state.trigger_run = True
                st.rerun()

    st.markdown("---")

    # ══ 使用說明 ══
    with st.expander("💡 使用說明", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("""
**輸入股票代碼**
- 台股：輸入4碼數字（如 `2330`、`2454`）
- 美股：輸入英文代碼（如 `AAPL`、`NVDA`）
- 左側 Sidebar 輸入後點「開始分析」
            """)
        with c2:
            st.markdown("""
**選擇分析功能**
- Sidebar 功能按鈕切換5大模組
- 或點擊上方功能卡片直接使用
- 熱門股票按鈕可快速查詢
            """)
        with c3:
            st.markdown("""
**啟用 AI 報告（選用）**
- 設定 Anthropic API Key
- 功能3/5 可生成 AI 深度報告
- 在各功能頁面展開 AI 報告區塊
            """)

    st.caption("⚠️ 本平台資料來自 Yahoo Finance 公開資料，僅供研究參考，不構成投資建議。")


# ───────────────────────────────────────────────
# 功能四：隱藏風險偵測
# ───────────────────────────────────────────────
def run_feature4(stock_input: str):
    from modules.data_fetcher import StockDataFetcher
    from modules.feature4_risk import RiskSignalDetector
    from modules.charts_risk import RiskChartBuilder

    progress = st.progress(0, text="⏳ 正在連線取得財務資料...")

    try:
        fetcher = StockDataFetcher(stock_input)
        progress.progress(10, text="✅ 連線成功，驗證股票...")

        if not fetcher.is_valid():
            progress.empty()
            st.error(f"❌ 找不到股票「{stock_input}」")
            return

        progress.progress(25, text="✅ 正在分析應收帳款與存貨...")
        detector = RiskSignalDetector(fetcher)

        progress.progress(45, text="✅ 正在計算現金流品質與債務壓力...")
        result = detector.run_full_analysis()

        progress.progress(75, text="✅ 正在計算 M-Score 與 F-Score...")
        charts = RiskChartBuilder()

        progress.progress(100, text="✅ 完成！")
        progress.empty()

        _display_feature4(fetcher, result, charts)

    except Exception as e:
        progress.empty()
        st.error(f"❌ 風險分析發生錯誤：{e}")
        import traceback; st.code(traceback.format_exc())


def _display_feature4(fetcher, result: dict, charts):
    signals  = result.get('signals', {})
    overall  = result.get('overall', {})
    m_score  = result.get('m_score', {})
    f_score  = result.get('f_score', {})

    # Extract year labels from any available signal's details.years
    yr_lbl = []
    for sig in signals.values():
        yrs = sig.get('details', {}).get('years', [])
        if yrs:
            yr_lbl = yrs
            break

    name   = fetcher.get_company_name()
    ticker = fetcher.ticker_symbol
    is_tw  = fetcher.stock_type == 'TW'

    score = overall.get('score', 0)
    label = overall.get('level', '—')

    # ── 頁頭 ──
    col_h1, col_h2 = st.columns([4, 1.5])
    with col_h1:
        st.markdown(f'<p class="main-title">🔍 {name}</p>', unsafe_allow_html=True)
        st.markdown(
            f'<p class="main-subtitle">{ticker} · 財報隱藏風險信號深度掃描</p>',
            unsafe_allow_html=True,
        )
    with col_h2:
        color_map = {
            "無明顯風險": "#00b09b",
            "低風險":     "#ffa502",
            "中等風險":   "#ff6b00",
            "高風險":     "#ff4757",
        }
        bar_color = color_map.get(label, "#aaa")
        st.markdown(f"""
        <div style='background:{bar_color}22;border:1.5px solid {bar_color};
                    border-radius:10px;padding:14px;text-align:center'>
            <div style='font-size:0.75rem;color:#aaa'>整體風險評分</div>
            <div style='font-size:2rem;font-weight:800;color:{bar_color}'>{score:.0f}</div>
            <div style='font-size:0.85rem;color:{bar_color}'>{label}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── 整體儀表板 + 信號熱圖 ──
    st.markdown('<p class="section-title">🎯 風險儀表板</p>', unsafe_allow_html=True)
    col_g, col_h = st.columns([1, 2])
    with col_g:
        st.plotly_chart(charts.plot_overall_gauge(overall), use_container_width=True)
    with col_h:
        st.plotly_chart(charts.plot_signal_heatmap(signals), use_container_width=True)

    # ── Top 警示旗幟 ──
    all_flags = overall.get('all_flags', [])
    if all_flags:
        st.markdown('<p class="section-title">🚨 主要風險警示</p>', unsafe_allow_html=True)
        for f in all_flags:
            color = "#ff4757" if "🚨" in f else "#ff9f43"
            st.markdown(
                f"<div style='background:{color}18;border-left:3px solid {color};"
                f"padding:8px 14px;border-radius:0 6px 6px 0;margin:4px 0;"
                f"font-size:0.9rem'>{f}</div>",
                unsafe_allow_html=True
            )

    st.markdown("---")

    # ── M-Score / F-Score ──
    st.markdown('<p class="section-title">📐 財報品質評分</p>', unsafe_allow_html=True)
    st.plotly_chart(charts.plot_m_f_score(m_score, f_score), use_container_width=True)

    # M-Score 成分說明
    m_components = m_score.get('components', {})
    if m_components:
        with st.expander("查看 Beneish M-Score 各成分"):
            comp_labels = {
                'DSRI': ('應收帳款天數指數', 'AR/Revenue 年比，> 1 表示 AR 增速超過營收'),
                'GMI':  ('毛利率指數', '前期/本期毛利率，> 1 表示毛利率惡化'),
                'AQI':  ('資產品質指數', '非流動有形資產比，> 1 表示資產品質下降'),
                'SGI':  ('營收成長指數', '本期/前期營收，高成長公司操縱動機更強'),
                'DEPI': ('折舊率指數', '折舊率下降可能虛增利潤'),
                'LVGI': ('槓桿指數', '負債增加可能有財務壓力'),
                'TATA': ('應計項目佔總資產', '應計利潤越高，現金流品質越差'),
            }
            comp_cols = st.columns(4)
            for i, (k, v) in enumerate(m_components.items()):
                lbl, desc = comp_labels.get(k, (k, ''))
                with comp_cols[i % 4]:
                    st.markdown(f"""
                    <div style='background:#1a1f2e;border-radius:8px;padding:10px;
                                border:1px solid #2d3436;margin-bottom:8px'>
                        <div style='font-size:0.72rem;color:#a4b0be'>{lbl} ({k})</div>
                        <div style='font-size:1.1rem;font-weight:700;color:#dfe6e9'>{v:.3f}</div>
                        <div style='font-size:0.72rem;color:#a4b0be'>{desc}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # F-Score 通過/未通過項目（從 criteria dict 解析）
    f_criteria = f_score.get('criteria', {})
    if f_criteria:
        f_passed = [v['desc'] for v in f_criteria.values() if v.get('score') == 1]
        f_failed = [v['desc'] for v in f_criteria.values() if v.get('score') == 0]
        with st.expander("查看 Piotroski F-Score 細項"):
            fc1, fc2 = st.columns(2)
            with fc1:
                st.markdown("**✅ 通過項目**")
                for item in f_passed:
                    st.markdown(f"- {item}")
            with fc2:
                st.markdown("**❌ 未通過項目**")
                for item in f_failed:
                    st.markdown(f"- {item}")

    st.markdown("---")

    # ── 六大風險信號詳細圖表 (Tabs) ──
    st.markdown('<p class="section-title">📊 六大風險信號詳細分析</p>', unsafe_allow_html=True)

    tabs = st.tabs([
        "📦 應收帳款",
        "🏭 存貨分析",
        "💰 現金流品質",
        "🏦 債務壓力",
        "📋 特殊項目",
        "👤 持股變動",
    ])

    def _show_flags(sig: dict):
        flags = sig.get('flags', [])
        for f in flags:
            st.markdown(f"- {f}")
        if not flags and not sig.get('available'):
            st.info(sig.get('message', '資料不足'))

    # Tab 1: AR
    with tabs[0]:
        ar = signals.get('ar_revenue', {})
        _show_flags(ar)
        st.plotly_chart(charts.plot_ar_revenue(ar, yr_lbl), use_container_width=True)

    # Tab 2: Inventory
    with tabs[1]:
        inv = signals.get('inventory', {})
        _show_flags(inv)
        st.plotly_chart(charts.plot_inventory(inv, yr_lbl), use_container_width=True)

    # Tab 3: CFO Quality  (key = cashflow_quality)
    with tabs[2]:
        cfo = signals.get('cashflow_quality', {})
        _show_flags(cfo)
        st.plotly_chart(charts.plot_cfo_vs_ni(cfo, yr_lbl), use_container_width=True)

    # Tab 4: Debt  (key = debt_structure)
    with tabs[3]:
        debt = signals.get('debt_structure', {})
        _show_flags(debt)
        col_z, col_debt = st.columns([1, 2])
        with col_z:
            st.plotly_chart(charts.plot_altman_z(debt), use_container_width=True)
        with col_debt:
            st.plotly_chart(charts.plot_debt_trend(debt, yr_lbl), use_container_width=True)

    # Tab 5: Special Items
    with tabs[4]:
        si = signals.get('special_items', {})
        _show_flags(si)
        # Show unusual ratio table
        import pandas as pd
        si_details = si.get('details', {})
        tax_list = si_details.get('tax_rates', []) or []
        oti_list = si_details.get('unusual_ratios', []) or []
        if any(v is not None for v in tax_list) or any(v is not None for v in oti_list):
            n = max(len(tax_list), len(oti_list), 1)
            table_data = {'年度': yr_lbl[-n:] if yr_lbl else list(range(n))}
            if tax_list:
                table_data['有效稅率(%)'] = [f"{v*100:.1f}%" if v is not None else 'N/A' for v in tax_list]
            if oti_list:
                table_data['一次性項目佔淨利(%)'] = [f"{v:.1f}%" if v is not None else 'N/A' for v in oti_list]
            st.dataframe(pd.DataFrame(table_data), use_container_width=True)

    # Tab 6: Insider  (key = insider_activity)
    with tabs[5]:
        ins = signals.get('insider_activity', {})
        _show_flags(ins)
        st.plotly_chart(charts.plot_insider_activity(ins, yr_lbl), use_container_width=True)
        # US: show transactions table
        ins_details = ins.get('details', {})
        transactions = ins_details.get('transactions', [])
        if transactions:
            import pandas as pd
            st.dataframe(pd.DataFrame(transactions), use_container_width=True)

    st.markdown("---")

    # ── 風險解讀說明 ──
    st.markdown('<p class="section-title">💡 風險信號解讀指引</p>', unsafe_allow_html=True)
    with st.expander("點擊展開：如何解讀各風險信號？"):
        st.markdown("""
**📦 應收帳款異常**
> 若 AR 成長速度持續超過營收成長，可能表示公司在「虛灌營收」或客戶付款延遲（信用風險上升）。
> DSO（應收帳款天數）持續增加超過 30 天應特別留意。

**🏭 存貨風險**
> 存貨周轉率下降表示產品銷售放緩或積壓。DIO > 90 天（科技業）或 > 120 天（製造業）需警惕。
> 急速增加的存貨可能是需求崩潰的先兆。

**💰 現金流品質**
> 健康公司的 CFO 應持續 > NI（應計利潤應為正向轉換）。
> CFO/NI < 0.8 表示利潤品質偏低；長期 CFO 為負而 NI 為正屬重大警訊。

**🏦 債務壓力**
> Altman Z-Score < 1.81 = 財務困境風險高。流動比率 < 1.0 = 短期流動性不足。
> 利息保障倍數 (ICR) < 3x 表示還息壓力大。

**📋 特殊項目**
> 一次性收益佔淨利超過 30% 代表本業獲利能力偏弱。
> 有效稅率異常低（< 5%）或高（> 40%）可能有稅務操作。

**👤 持股變動**
> 台股：外資持股比率大幅下降（-5% 以上）通常是外資出走訊號。
> 美股：內部人大量拋售股票（尤其高管）值得關注，但需排除例行財務規劃出售。
        """)

    st.markdown("---")
    st.caption("⚠️ 本風險評估基於公開財務數據的量化模型，不構成投資建議。")
    st.caption("📡 資料來源：Yahoo Finance · FinMind · Beneish(1999) · Piotroski(2000) · Altman(1968)")


# ───────────────────────────────────────────────
# 功能三：產業競爭分析
# ───────────────────────────────────────────────
def run_feature3(stock_input: str):
    from modules.data_fetcher import StockDataFetcher
    from modules.feature3_industry import IndustryAnalyzer
    from modules.charts_industry import IndustryChartBuilder
    import os

    progress = st.progress(0, text="⏳ 正在初始化產業分析...")

    try:
        fetcher = StockDataFetcher(stock_input)
        progress.progress(10, text="✅ 連線成功，驗證股票...")

        if not fetcher.is_valid():
            progress.empty()
            st.error(f"❌ 找不到股票「{stock_input}」")
            return

        progress.progress(30, text="✅ 正在取得同業比較數據...")
        analyzer = IndustryAnalyzer(fetcher)
        result   = analyzer.run_full_analysis()

        progress.progress(65, text="✅ 數據分析完成，載入產業知識庫...")
        charts = IndustryChartBuilder()

        # 取得 Claude API Key
        api_key = (
            st.session_state.get('claude_api_key', '') or
            os.environ.get('ANTHROPIC_API_KEY', '')
        )

        ai_report = None
        if api_key:
            progress.progress(80, text="🤖 AI 分析師正在撰寫深度報告...")
            ai_report = analyzer.generate_ai_report(result, api_key)
        else:
            progress.progress(80, text="✅ 生成分析報告...")

        progress.progress(100, text="✅ 完成！")
        progress.empty()

        _display_feature3(fetcher, result, charts, ai_report)

    except Exception as e:
        progress.empty()
        st.error(f"❌ 產業分析發生錯誤：{e}")
        import traceback; st.code(traceback.format_exc())


def _display_feature3(fetcher, result: dict, charts, ai_report: Optional[str]):
    cd   = result['company_data']
    ki   = result['industry_info']
    swot = result['swot']
    peers = result['peer_data']
    pos  = result['positioning']
    share = result['market_share']
    ind_key = result['industry_key']

    name   = cd['name']
    ticker = cd['ticker']
    overall = pos.get('overall', 50)

    # ── 頁頭 ──
    col_h1, col_h2 = st.columns([4, 1.5])
    with col_h1:
        st.markdown(f'<p class="main-title">🏭 {name}</p>', unsafe_allow_html=True)
        st.markdown(
            f'<p class="main-subtitle">{ticker} · 產業競爭地位與發展前景分析</p>',
            unsafe_allow_html=True,
        )
    with col_h2:
        score_10 = round(overall / 10, 1)
        color_map = {9: "#00b09b", 8: "#5cb85c", 7: "#ffa502",
                     6: "#ff9f43", 5: "#e67e22"}
        bar_color = color_map.get(int(score_10), "#ff4757")
        st.markdown(f"""
        <div style='background:{bar_color}22;border:1.5px solid {bar_color};
                    border-radius:10px;padding:14px;text-align:center'>
            <div style='font-size:0.75rem;color:#aaa'>產業競爭地位</div>
            <div style='font-size:2rem;font-weight:800;color:{bar_color}'>{score_10}</div>
            <div style='font-size:0.75rem;color:{bar_color}'>/ 10 分</div>
        </div>
        """, unsafe_allow_html=True)

    # API Key 提示（若無）
    if not ai_report:
        with st.expander("🤖 啟用 AI 深度報告（Claude API）", expanded=False):
            st.markdown("設定 Claude API Key 後，本功能將由 AI 分析師撰寫 2000+ 字深度報告。")
            col_k1, col_k2 = st.columns([4, 1])
            with col_k1:
                key_input = st.text_input(
                    "Anthropic API Key", type="password",
                    value=st.session_state.get('claude_api_key', ''),
                    key="api_key_input_f3",
                    label_visibility="collapsed",
                    placeholder="sk-ant-..."
                )
            with col_k2:
                if st.button("套用並重新分析", use_container_width=True):
                    st.session_state.claude_api_key = key_input
                    st.session_state.stock_input   = fetcher.original_input
                    st.session_state.trigger_run   = True
                    st.rerun()

    st.markdown("---")

    # ── 產業總覽指標 ──
    st.markdown('<p class="section-title">🌐 產業概況</p>', unsafe_allow_html=True)
    ci1, ci2, ci3, ci4 = st.columns(4)
    with ci1:
        st.metric("所屬產業", ki.get('full_name', ind_key)[:20])
    with ci2:
        st.metric("市場規模（2024）", ki.get('market_size_now', 'N/A'))
    with ci3:
        st.metric("預測規模（2028E）", ki.get('market_size_2028', 'N/A'))
    with ci4:
        st.metric("預估 CAGR", ki.get('cagr', 'N/A'))

    st.markdown("---")

    # ── 圖表區 ──
    st.markdown('<p class="section-title">📊 競爭地位視覺化</p>', unsafe_allow_html=True)

    row1_c1, row1_c2 = st.columns(2)
    with row1_c1:
        # 市場規模成長預測
        fig_mkt = charts.plot_market_size_bar(ki)
        if fig_mkt:
            st.plotly_chart(fig_mkt, use_container_width=True)
        else:
            st.info("市場規模預測圖暫無法繪製")

    with row1_c2:
        # 競爭地位雷達圖
        st.plotly_chart(
            charts.plot_positioning_radar(pos, name),
            use_container_width=True,
        )

    row2_c1, row2_c2 = st.columns(2)
    with row2_c1:
        # 競爭定位矩陣
        if peers:
            st.plotly_chart(
                charts.plot_competitive_matrix(cd, peers),
                use_container_width=True,
            )
        else:
            st.info("競爭定位矩陣：同業數據不足")

    with row2_c2:
        # 同業市值比較
        if peers:
            st.plotly_chart(
                charts.plot_market_cap_comparison(cd, peers),
                use_container_width=True,
            )
        else:
            st.info("市值比較：同業數據不足")

    # 同業財務指標比較
    if peers:
        st.markdown('<p class="section-title">📈 同業財務指標對比</p>', unsafe_allow_html=True)
        st.plotly_chart(
            charts.plot_peer_comparison_bars(cd, peers),
            use_container_width=True,
        )

    # 市場份額
    if share:
        st.markdown('<p class="section-title">🥧 同業收入規模比較</p>', unsafe_allow_html=True)
        fig_share = charts.plot_market_share(share)
        if fig_share:
            st.plotly_chart(fig_share, use_container_width=True)

    st.markdown("---")

    # ── SWOT ──
    st.markdown('<p class="section-title">🔍 SWOT 分析</p>', unsafe_allow_html=True)
    st.markdown(charts.build_swot_html(swot), unsafe_allow_html=True)

    st.markdown("---")

    # ── 分析報告 ──
    st.markdown('<p class="section-title">📝 產業競爭深度報告</p>', unsafe_allow_html=True)

    if ai_report:
        st.markdown(f"""
        <div style='background:#141820;border-left:4px solid #00b09b;
                    border-radius:0 8px 8px 0;padding:20px 24px;
                    line-height:1.9;font-size:0.95rem'>
        🤖 <em>以下報告由 Claude AI 分析師根據最新市場數據生成</em>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(ai_report)
    else:
        # 直接從 result dict 組裝各 Tab 內容（不依賴文字切割）
        swot    = result.get('swot', {})
        ki_tab  = result.get('industry_info', {})
        peers_t = result.get('peer_data', [])
        pos_t   = result.get('positioning', {})
        cd_tab  = result.get('company_data', {})

        def _box(md_text: str):
            st.markdown(
                f'<div class="analysis-box" style="line-height:1.9">{md_text}</div>',
                unsafe_allow_html=True)

        tabs = st.tabs(["🌐 產業前景", "⚔️ 競爭比較", "📋 政策技術", "⚡ 風險催化劑", "💡 投資啟示"])

        # ── Tab 1：產業前景 ──
        with tabs[0]:
            lines = []
            lines.append(f"### 市場規模預測\n")
            lines.append(f"**{ind_key}** 產業 2024 年市場規模 **{ki_tab.get('market_size_now','N/A')}**，"
                         f"預計 2028 年達 **{ki_tab.get('market_size_2028','N/A')}**，"
                         f"CAGR **{ki_tab.get('cagr','N/A')}**。\n")
            themes = ki_tab.get('key_themes', [])
            if themes:
                lines.append("\n**關鍵成長驅動力：**\n")
                for t in themes[:5]:
                    lines.append(f"- {t}")
            _box('\n'.join(lines))

        # ── Tab 2：競爭比較 ──
        with tabs[1]:
            lines = []
            strengths = swot.get('strengths', [])
            weaknesses = swot.get('weaknesses', [])
            lines.append("### ✅ 公司核心競爭優勢\n")
            for s in strengths[:4]:
                lines.append(f"- {s}")
            lines.append("\n### ⚠️ 主要劣勢與挑戰\n")
            for w in weaknesses[:3]:
                lines.append(f"- {w}")
            if peers_t:
                lines.append("\n### 📊 同業財務比較\n")
                lines.append("| 公司 | 毛利率 | 淨利率 | P/E |")
                lines.append("|------|--------|--------|-----|")
                my_gm = f"{cd_tab.get('gross_margin',0):.1f}%" if cd_tab.get('gross_margin') else 'N/A'
                my_nm = f"{cd_tab.get('net_margin',0):.1f}%"   if cd_tab.get('net_margin')   else 'N/A'
                my_pe = f"{cd_tab.get('pe_ratio',0):.1f}x"     if cd_tab.get('pe_ratio')     else 'N/A'
                lines.append(f"| **{cd_tab.get('name','本股')[:10]}（本股）** | **{my_gm}** | **{my_nm}** | **{my_pe}** |")
                for p in peers_t[:5]:
                    gm = f"{p['gross_margin']:.1f}%" if p.get('gross_margin') else 'N/A'
                    nm = f"{p['net_margin']:.1f}%"   if p.get('net_margin')   else 'N/A'
                    pe = f"{p['pe_ratio']:.1f}x"     if p.get('pe_ratio')     else 'N/A'
                    lines.append(f"| {p.get('name','—')[:14]} | {gm} | {nm} | {pe} |")
            _box('\n'.join(lines))

        # ── Tab 3：政策技術 ──
        with tabs[2]:
            lines = []
            policy = ki_tab.get('policy', [])
            if policy:
                lines.append("### 🏛️ 相關政策動向\n")
                for p in policy[:4]:
                    lines.append(f"- {p}")
            lines.append("\n### 🔬 技術趨勢與變革\n")
            for t in ki_tab.get('key_themes', [])[:5]:
                lines.append(f"- {t}")
            _box('\n'.join(lines))

        # ── Tab 4：風險催化劑 ──
        with tabs[3]:
            lines = []
            opps = swot.get('opportunities', [])
            threats = swot.get('threats', [])
            lines.append("### 🔺 成長催化劑（Upside Catalysts）\n")
            for c in opps[:5]:
                lines.append(f"- {c}")
            lines.append("\n### 🔻 潛在風險（Downside Risks）\n")
            for r in threats[:5]:
                lines.append(f"- {r}")
            extra_risks = ki_tab.get('risks', [])
            if extra_risks:
                for r in extra_risks[:3]:
                    lines.append(f"- {r}")
            _box('\n'.join(lines))

        # ── Tab 5：投資啟示 ──
        with tabs[4]:
            lines = []
            overall_score = pos_t.get('overall', 50)
            score_10 = round(overall_score / 10, 1)
            if overall_score >= 70:
                stance = "✅ **長線偏多**：公司在同業中競爭地位強，具備護城河優勢"
            elif overall_score >= 50:
                stance = "➡️ **中性觀察**：競爭地位中等，等待業績進一步確認"
            else:
                stance = "⚠️ **謹慎看待**：相較同業競爭力偏弱，建議等待轉折訊號"
            lines.append(f"### 🏆 投資評級：{score_10}/10 分\n")
            lines.append(f"{stance}\n")
            lines.append("\n### 📊 五維競爭評分\n")
            lines.append("| 評估維度 | 分數 |")
            lines.append("|----------|------|")
            for dim, val in pos_t.get('scores', {}).items():
                bar = "▓" * (val // 10) + "░" * (10 - val // 10)
                lines.append(f"| {dim} | {bar} {val}/100 |")
            lines.append("\n> 💡 設定 Claude API Key 可取得 AI 生成的 2000字完整深度報告")
            lines.append("> ⚠️ 本報告僅供參考，不構成投資建議")
            _box('\n'.join(lines))

    st.markdown("---")
    # 全球主要競爭者列表
    if ki.get('global_peers'):
        st.markdown('<p class="section-title">🌍 全球主要競爭者</p>', unsafe_allow_html=True)
        cols = st.columns(len(ki['global_peers']))
        for col, peer in zip(cols, ki['global_peers']):
            with col:
                st.markdown(f"""
                <div style='background:#1a1f2e;border-radius:8px;padding:10px;
                            text-align:center;border:1px solid #2d3436;font-size:0.85rem'>
                    {peer}
                </div>
                """, unsafe_allow_html=True)
        st.markdown("")

    st.markdown("---")
    st.caption("⚠️ 本報告為系統自動生成，僅供研究參考，不構成投資建議。")
    st.caption("📡 資料來源：Yahoo Finance · FinMind · 自建產業知識庫（2025 Q1）")


# ───────────────────────────────────────────────
# 功能二：技術面分析
# ───────────────────────────────────────────────
def run_feature2(stock_input: str):
    from modules.data_fetcher import StockDataFetcher
    from modules.feature2_technical import TechnicalAnalyzer
    from modules.charts_technical import TechnicalChartBuilder

    progress = st.progress(0, text="⏳ 正在取得歷史價格資料...")

    try:
        fetcher = StockDataFetcher(stock_input)
        progress.progress(15, text="✅ 連線成功，驗證股票中...")

        if not fetcher.is_valid():
            progress.empty()
            st.error(f"❌ 找不到股票「{stock_input}」")
            return

        progress.progress(35, text="✅ 正在計算技術指標...")
        analyzer = TechnicalAnalyzer(fetcher)
        result   = analyzer.run_full_analysis()

        if 'error' in result:
            progress.empty()
            st.error(f"❌ {result['error']}")
            return

        progress.progress(75, text="✅ 正在繪製技術圖表...")
        charts = TechnicalChartBuilder()

        progress.progress(100, text="✅ 完成！")
        progress.empty()

        _display_feature2(fetcher, result, charts)

    except Exception as e:
        progress.empty()
        st.error(f"❌ 技術分析發生錯誤：{e}")


def _display_feature2(fetcher, result: dict, charts):
    hist = result['hist']
    ind  = result['indicators']
    sr   = result['sr_levels']
    pat  = result['pattern']
    sugg = result['suggestions']
    inst = result['institutional']
    analysis = result['analysis']

    name   = fetcher.get_company_name()
    ticker = fetcher.ticker_symbol
    is_tw  = fetcher.stock_type == 'TW'
    ccy    = '' if is_tw else '$'
    price  = sr['price']
    overall = pat.get('overall', {})

    # ── 頁頭 ──
    col_h1, col_h2, col_h3 = st.columns([3, 1.2, 1.2])
    with col_h1:
        st.markdown(f'<p class="main-title">📈 {name}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="main-subtitle">{ticker} · 技術面走勢分析</p>',
                    unsafe_allow_html=True)
    with col_h2:
        price_disp = f"{price:,.2f}"
        chg_1d = float(hist['Close'].iloc[-1]) - float(hist['Close'].iloc[-2])
        chg_pct = chg_1d / float(hist['Close'].iloc[-2]) * 100
        st.metric("目前股價", f"{ccy}{price_disp}",
                  delta=f"{chg_pct:+.2f}%",
                  delta_color="normal")
    with col_h3:
        score = overall.get('score', 0)
        label = overall.get('label', '')
        color = overall.get('color', '#ffa502')
        st.markdown(f"""
        <div style='background:{color}22;border:1px solid {color};border-radius:8px;
                    padding:10px 14px;text-align:center'>
            <div style='font-size:0.78rem;color:#aaa'>綜合技術訊號</div>
            <div style='font-size:1.1rem;font-weight:700;color:{color}'>{label}</div>
            <div style='font-size:0.85rem;color:{color}'>評分 {score:+d}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── 快速指標儀表板 ──
    st.markdown('<p class="section-title">🎯 技術指標快覽</p>', unsafe_allow_html=True)
    st.plotly_chart(charts.plot_indicator_gauges(pat), use_container_width=True)

    # 指標狀態卡片列
    card_data = [
        ("RSI(14)", f"{pat.get('rsi_value',50):.1f}",
         f"{pat.get('rsi_signal',('','',''))[1]} {pat.get('rsi_signal',('N/A','',''))[0]}"),
        ("KD(9,3,3)",
         f"K={pat.get('kd_values',(0,0))[0]:.0f} D={pat.get('kd_values',(0,0))[1]:.0f}",
         f"{pat.get('kd_signal',('','',''))[1]} {pat.get('kd_signal',('N/A','',''))[0]}"),
        ("MACD",
         f"{pat.get('macd_values',(0,0,0))[0]:.3f}",
         f"{pat.get('macd_signal',('','',''))[1]} {pat.get('macd_signal',('N/A','',''))[0]}"),
        ("布林%B",
         f"{pat.get('bb_pct',0.5):.2f}",
         f"{pat.get('bb_signal',('','',''))[1]} {pat.get('bb_signal',('N/A','',''))[0]}"),
        ("均線排列",
         "—",
         f"{pat.get('ma_arrangement',('','',''))[1]} {pat.get('ma_arrangement',('N/A','',''))[0]}"),
        ("量價關係",
         f"{pat.get('vol_ratio',1):.2f}x 均量",
         f"{pat.get('vol_price',('','',''))[1]} {pat.get('vol_price',('N/A','',''))[0]}"),
    ]
    cols = st.columns(6)
    for col, (title, val, sig) in zip(cols, card_data):
        with col:
            st.markdown(f"""
            <div style='background:#1a1f2e;border-radius:8px;padding:10px 12px;
                        border:1px solid #2d3436;text-align:center'>
                <div style='font-size:0.72rem;color:#a4b0be'>{title}</div>
                <div style='font-size:1.05rem;font-weight:700;color:#dfe6e9;margin:4px 0'>{val}</div>
                <div style='font-size:0.78rem;color:#dfe6e9'>{sig}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ── 主技術圖 ──
    st.markdown('<p class="section-title">📊 K線技術分析圖（含均線、布林通道）</p>',
                unsafe_allow_html=True)

    # 顯示天數選擇
    n_days = st.select_slider(
        "顯示天數", options=[30, 60, 120, 250, 500], value=120,
        label_visibility="collapsed"
    )
    hist_plot = hist.tail(n_days)

    # 重新計算 ind（只用選擇的資料長度，避免圖表 x 軸過長）
    from modules.feature2_technical import (
        calc_ma, calc_rsi, calc_macd, calc_kd, calc_bb, calc_atr
    )
    c2 = hist_plot['Close']
    ind_plot = {
        'close':     c2,
        'volume':    hist_plot['Volume'],
        'ma':        calc_ma(c2, [5, 20, 60, 120, 240]),
        'rsi':       calc_rsi(c2),
        'macd':      calc_macd(c2)[0],
        'macd_sig':  calc_macd(c2)[1],
        'macd_hist': calc_macd(c2)[2],
        'k':         calc_kd(hist_plot)[0],
        'd':         calc_kd(hist_plot)[1],
        'bb_ma':     calc_bb(c2)[0],
        'bb_upper':  calc_bb(c2)[1],
        'bb_lower':  calc_bb(c2)[2],
        'bb_pct':    calc_bb(c2)[3],
        'atr':       calc_atr(hist_plot),
        'vol_ma20':  hist_plot['Volume'].rolling(20).mean(),
    }

    st.plotly_chart(
        charts.plot_full_chart(hist_plot, ind_plot, sr, is_tw=is_tw),
        use_container_width=True
    )

    # ── 台股三大法人圖 ──
    if is_tw and inst.get('available'):
        st.markdown('<p class="section-title">🏢 三大法人買賣超</p>', unsafe_allow_html=True)
        inst_fig = charts.plot_institutional_tw(inst)
        if inst_fig:
            st.plotly_chart(inst_fig, use_container_width=True)
        else:
            st.info("三大法人圖表資料不足")
    elif not is_tw and inst.get('available'):
        st.markdown('<p class="section-title">🏢 美股機構持股資訊</p>', unsafe_allow_html=True)
        ci1, ci2, ci3, ci4 = st.columns(4)
        io = inst.get('held_by_institutions')
        ins_ = inst.get('held_by_insiders')
        sr_ = inst.get('short_ratio')
        sf = inst.get('short_pct_float')
        with ci1:
            st.metric("機構持股%", f"{io*100:.1f}%" if io else "N/A")
        with ci2:
            st.metric("內部人持股%", f"{ins_*100:.1f}%" if ins_ else "N/A")
        with ci3:
            st.metric("空頭回補天數", f"{sr_:.1f}天" if sr_ else "N/A")
        with ci4:
            st.metric("空頭比率", f"{sf*100:.1f}%" if sf else "N/A")

    st.markdown("---")

    # ── 文字分析 Tabs ──
    st.markdown('<p class="section-title">📝 技術分析報告</p>', unsafe_allow_html=True)
    tabs = st.tabs([
        "📍 支撐與阻力",
        "📊 技術指標解讀",
        "💹 成交量與籌碼",
        "🔮 走勢預測",
        "🎯 進場停損建議",
    ])
    tab_keys = ['support_resistance', 'indicators', 'volume_institutional',
                'forecast', 'entry_stoploss']
    for tab, key in zip(tabs, tab_keys):
        with tab:
            content = analysis.get(key, "暫無分析資料")
            st.markdown(f'<div class="analysis-box">{content}</div>',
                        unsafe_allow_html=True)

    st.markdown("---")
    st.caption("⚠️ 技術分析僅供參考，不構成投資建議。任何交易決策請自行承擔風險。")
    st.caption("📡 資料來源：Yahoo Finance · FinMind（公開資料）")


# ───────────────────────────────────────────────
# 股票快速概覽（點「開始分析」後的預設頁面）
# ───────────────────────────────────────────────
def run_stock_overview(stock_input: str):
    from modules.data_fetcher import StockDataFetcher
    from modules.charts_overview import (
        get_bb_signal, get_ma_status, get_macd_signal, get_kd_signal,
        plot_bollinger_chart, plot_ma_chart, plot_macd_chart, plot_kd_chart,
        GREEN, RED, YELLOW, BLUE, ORANGE,
    )
    import requests as _req
    from datetime import datetime, timedelta

    progress = st.progress(0, text="⏳ 正在取得資料...")

    try:
        fetcher = StockDataFetcher(stock_input)
        progress.progress(15, text="✅ 連線成功，驗證股票中...")

        if not fetcher.is_valid():
            progress.empty()
            is_tw_fmt = re.match(r'^\d{4,6}[A-Z]?$', stock_input.strip().upper())
            st.error(f"❌ 找不到股票代碼「{stock_input}」，Yahoo Finance 查無此代碼。")
            if is_tw_fmt:
                st.info("📌 台股請輸入代碼（如 2330、0050、00919）。部分冷門 ETF Yahoo Finance 可能尚未收錄。")
            else:
                st.info("📌 美股請輸入英文代碼（如 AAPL、NVDA、TSLA）。")
            return

        hist = fetcher.get_historical_prices(period='1y')
        progress.progress(40, text="✅ 正在計算技術指標...")

        if hist is None or len(hist) < 30:
            st.warning("⚠️ 歷史資料不足（< 30 筆），無法進行技術分析。")
            return

        name     = fetcher.get_company_name()
        is_tw    = fetcher.stock_type == 'TW'
        ccy      = '' if is_tw else '$'
        info     = fetcher.info or {}

        bb_signal   = get_bb_signal(hist)
        ma_status   = get_ma_status(hist)
        macd_signal = get_macd_signal(hist)
        kd_signal   = get_kd_signal(hist)

        progress.progress(70, text="✅ 正在取得機構資料...")

        # ── 取得中文股票名稱（台股）──
        chinese_name = ''
        if is_tw:
            from config.peer_stocks import TAIWAN_INDUSTRY_PEERS as _PEERS
            _tw_names = {}
            for _ind_data in _PEERS.values():
                _tw_names.update(_ind_data.get('names', {}))
            chinese_name = _tw_names.get(fetcher.ticker_symbol, '')
            if not chinese_name:
                try:
                    _r = _req.get(
                        "https://api.finmindtrade.com/api/v4/data",
                        params={"dataset": "TaiwanStockInfo",
                                "data_id": fetcher.stock_id},
                        timeout=6)
                    _d = _r.json().get('data', [])
                    if _d:
                        chinese_name = _d[0].get('stock_name', '')
                except Exception:
                    pass

        # ── 頁首 ──
        col_h1, col_h2, col_h3, col_h4 = st.columns([3, 1.2, 1.2, 1.2])
        price_now  = float(hist['Close'].iloc[-1])
        price_prev = float(hist['Close'].iloc[-2])
        chg_pts    = price_now - price_prev
        chg_pct    = chg_pts / price_prev * 100
        chg_color  = GREEN if chg_pct >= 0 else RED

        with col_h1:
            if is_tw and chinese_name:
                st.markdown(
                    f'<p style="font-size:1.5rem;font-weight:900;color:#dfe6e9;margin:0 0 2px 0">'
                    f'{chinese_name}</p>',
                    unsafe_allow_html=True)
            st.markdown(f'<p class="main-title">📈 {name}</p>', unsafe_allow_html=True)
            st.markdown(
                f'<p class="main-subtitle">{fetcher.ticker_symbol} · 技術快速概覽</p>',
                unsafe_allow_html=True)
        with col_h2:
            st.markdown(f"""
            <div style='background:{chg_color}18;border:1.5px solid {chg_color};
                        border-radius:10px;padding:12px;text-align:center'>
                <div style='font-size:0.72rem;color:#aaa'>目前股價</div>
                <div style='font-size:1.5rem;font-weight:800;color:{chg_color}'>{ccy}{price_now:,.2f}</div>
                <div style='font-size:0.8rem;color:{chg_color}'>{chg_pts:+.2f} ({chg_pct:+.1f}%)</div>
            </div>""", unsafe_allow_html=True)
        with col_h3:
            vol = info.get('volume') or info.get('regularMarketVolume') or info.get('_volume')
            if vol:
                vol_str = f"{int(vol)//1000}千張" if is_tw else f"{int(vol)/1e6:.1f}M"
            else:
                vol_str = "N/A"
            st.markdown(f"""
            <div style='background:#1a1f2e;border:1px solid #2d3436;
                        border-radius:10px;padding:12px;text-align:center'>
                <div style='font-size:0.72rem;color:#aaa'>成交量</div>
                <div style='font-size:1.2rem;font-weight:700;color:#dfe6e9'>{vol_str}</div>
            </div>""", unsafe_allow_html=True)
        with col_h4:
            mc = info.get('marketCap')
            if mc:
                mc_str = (f"{mc/1e12:.2f}兆" if mc >= 1e12 else f"{mc/1e8:.0f}億") if is_tw else f"${mc/1e9:.1f}B"
            else:
                mc_str = "N/A"
            st.markdown(f"""
            <div style='background:#1a1f2e;border:1px solid #2d3436;
                        border-radius:10px;padding:12px;text-align:center'>
                <div style='font-size:0.72rem;color:#aaa'>市值</div>
                <div style='font-size:1.2rem;font-weight:700;color:#dfe6e9'>{mc_str}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("")

        # ── 四大訊號摘要卡片 ──
        sig_items = [
            ("布林通道", bb_signal),
            ("均線狀態", (ma_status['summary'], "", ma_status['color'])),
            ("MACD",     macd_signal),
            ("KD 指標",  kd_signal),
        ]
        s_cols = st.columns(4)
        for col, (label, sig) in zip(s_cols, sig_items):
            sn, sd, sc = sig
            with col:
                st.markdown(f"""
                <div style='background:{sc}18;border:1.5px solid {sc};
                            border-radius:10px;padding:10px;text-align:center'>
                    <div style='font-size:0.72rem;color:#aaa'>{label}</div>
                    <div style='font-size:0.95rem;font-weight:700;color:{sc}'>{sn}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # ── 布林通道 ──
        st.markdown('<p class="section-title">📊 布林通道 (Bollinger Bands)</p>',
                    unsafe_allow_html=True)
        st.plotly_chart(plot_bollinger_chart(hist, bb_signal), use_container_width=True)
        sn, sd, sc = bb_signal
        st.markdown(f"""<div style='background:{sc}12;border-left:4px solid {sc};
            border-radius:0 8px 8px 0;padding:9px 15px;margin-bottom:18px'>
            <b style='color:{sc}'>【{sn}】</b> {sd}</div>""", unsafe_allow_html=True)

        # ── 移動平均線 ──
        st.markdown('<p class="section-title">📉 移動平均線</p>', unsafe_allow_html=True)
        st.plotly_chart(plot_ma_chart(hist, ma_status), use_container_width=True)

        # MA 小卡片列
        mas = ma_status.get('mas', {})
        ma_cols = st.columns(len(mas))
        for col, (ma_name, mv) in zip(ma_cols, mas.items()):
            with col:
                if mv:
                    c = GREEN if mv['above'] else RED
                    lbl = "站上" if mv['above'] else "跌破"
                    st.markdown(f"""
                    <div style='background:{c}12;border:1px solid {c}40;border-radius:8px;
                                padding:7px;text-align:center;margin-bottom:4px'>
                        <div style='font-size:0.68rem;color:#aaa'>{ma_name}</div>
                        <div style='font-size:0.85rem;font-weight:700;color:{c}'>{lbl}</div>
                        <div style='font-size:0.75rem;color:{c}'>{mv["diff_pct"]:+.1f}%</div>
                        <div style='font-size:0.68rem;color:#888'>{mv["value"]:,.1f}</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style='background:#1a1f2e;border:1px solid #2d3436;border-radius:8px;
                                padding:7px;text-align:center;margin-bottom:4px'>
                        <div style='font-size:0.68rem;color:#aaa'>{ma_name}</div>
                        <div style='font-size:0.8rem;color:#555'>資料不足</div>
                    </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # ── MACD + KD ──
        col_macd, col_kd = st.columns(2)
        with col_macd:
            st.markdown('<p class="section-title">⚡ MACD</p>', unsafe_allow_html=True)
            st.plotly_chart(plot_macd_chart(hist, macd_signal), use_container_width=True)
            sn, sd, sc = macd_signal
            st.markdown(f"""<div style='background:{sc}12;border-left:4px solid {sc};
                border-radius:0 8px 8px 0;padding:8px 14px;margin-bottom:12px'>
                <b style='color:{sc}'>【{sn}】</b> {sd}</div>""", unsafe_allow_html=True)
        with col_kd:
            st.markdown('<p class="section-title">🎯 KD 指標</p>', unsafe_allow_html=True)
            st.plotly_chart(plot_kd_chart(hist, kd_signal), use_container_width=True)
            sn, sd, sc = kd_signal
            st.markdown(f"""<div style='background:{sc}12;border-left:4px solid {sc};
                border-radius:0 8px 8px 0;padding:8px 14px;margin-bottom:12px'>
                <b style='color:{sc}'>【{sn}】</b> {sd}</div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.caption("⚠️ 以上為技術面快速概覽，僅供研究參考，不構成投資建議。")
        st.caption("👈 點選左側「選擇功能」可進行財務健康、產業競爭、隱藏風險或內在價值的深度分析。")

        # ════════════════════════════════════════════════════
        # 機構評等（獨立區塊，位於技術快速概覽下方）
        # ════════════════════════════════════════════════════
        st.markdown("""
        <div style='margin-top:32px;padding:18px 22px 4px 22px;
                    background:#10141c;border-radius:14px;
                    border:1px solid #2d3436'>
        <p style='font-size:1.15rem;font-weight:700;color:#5352ed;
                  border-left:4px solid #5352ed;padding-left:10px;margin:0 0 14px 0'>
        🏛 機構評等 &amp; 分析師目標價</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<p class="section-title" style="display:none">🏛 機構評等</p>',
                    unsafe_allow_html=True)

        # ── 第一排：分析師共識目標價 ──
        _mean_t = info.get('targetMeanPrice')
        _low_t  = info.get('targetLowPrice')
        _high_t = info.get('targetHighPrice')
        _num_a  = info.get('numberOfAnalystOpinions') or info.get('numberOfAnalysts')
        if _mean_t and price_now:
            _upside = (_mean_t - price_now) / price_now * 100
            _up_clr = GREEN if _upside > 0 else RED
            st.markdown(
                f"<div style='background:#1a1f2e;border:1px solid #2d3436;border-radius:12px;"
                f"padding:16px 20px;margin-bottom:14px'>"
                f"<div style='font-size:0.78rem;color:#aaa;margin-bottom:8px'>📌 分析師共識目標價"
                f"{'（' + str(int(_num_a)) + ' 位分析師）' if _num_a else ''}</div>"
                f"<div style='display:flex;gap:32px;flex-wrap:wrap;align-items:center'>"
                f"<div><div style='font-size:0.7rem;color:#aaa'>目標均價</div>"
                f"<div style='font-size:1.7rem;font-weight:900;color:{_up_clr}'>{ccy}{_mean_t:,.2f}</div>"
                f"<div style='font-size:0.85rem;color:{_up_clr};font-weight:700'>{_upside:+.1f}% 空間</div></div>"
                f"<div style='color:#2d3436;font-size:1.4rem'>|</div>"
                f"<div><div style='font-size:0.7rem;color:#aaa'>目標低價</div>"
                f"<div style='font-size:1.1rem;font-weight:700;color:#aaa'>{ccy}{_low_t:,.2f}</div></div>"
                f"<div><div style='font-size:0.7rem;color:#aaa'>目標高價</div>"
                f"<div style='font-size:1.1rem;font-weight:700;color:#aaa'>{ccy}{_high_t:,.2f}</div></div>"
                f"<div><div style='font-size:0.7rem;color:#aaa'>現價</div>"
                f"<div style='font-size:1.1rem;font-weight:700;color:#dfe6e9'>{ccy}{price_now:,.2f}</div></div>"
                f"</div></div>",
                unsafe_allow_html=True)
        else:
            st.info("⚠️ 暫無分析師共識目標價資料（Yahoo Finance 未收錄此股票的分析師預測）")

        # ── 第二排：左欄=機構評等明細，右欄=三大法人 or 買賣比例 ──
        col_i1, col_i2 = st.columns([3, 2])

        with col_i1:
            st.markdown("**📋 近期機構評等異動**")
            _ud_shown = False
            try:
                ud = fetcher._yf_ticker.upgrades_downgrades
                if ud is not None and not ud.empty:
                    # 取欄位名稱（可能大小寫不同）
                    ud_cols = {c.lower(): c for c in ud.columns}
                    firm_col  = ud_cols.get('firm',      ud.columns[0] if len(ud.columns) > 0 else None)
                    to_col    = ud_cols.get('tograde',   ud_cols.get('to grade',   None))
                    from_col  = ud_cols.get('fromgrade', ud_cols.get('from grade', None))

                    rows_shown = 0
                    for idx, row in ud.head(15).iterrows():
                        firm   = str(row[firm_col]).strip()  if firm_col  else '–'
                        to_g   = str(row[to_col]).strip()    if to_col    else ''
                        from_g = str(row[from_col]).strip()  if from_col  else ''
                        if not firm or firm in ('nan', '–', '') or not to_g or to_g == 'nan':
                            continue

                        to_up = to_g.upper()
                        if any(x in to_up for x in ['BUY','OUTPERFORM','OVERWEIGHT','STRONG BUY','POSITIVE','ACCUMULATE']):
                            g_clr, arrow = GREEN, '↑'
                        elif any(x in to_up for x in ['SELL','UNDERPERFORM','UNDERWEIGHT','NEGATIVE','REDUCE']):
                            g_clr, arrow = RED, '↓'
                        else:
                            g_clr, arrow = YELLOW, '→'

                        date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)[:10]
                        from_part = (f"<span style='color:#666;font-size:0.7rem'> ← {from_g}</span>"
                                     if from_g and from_g not in ('nan', '') else '')

                        st.markdown(
                            f"<div style='display:flex;justify-content:space-between;align-items:center;"
                            f"padding:6px 4px;border-bottom:1px solid #23272f'>"
                            f"<div>"
                            f"<span style='color:{g_clr};font-size:1rem;font-weight:700'>{arrow}</span>"
                            f"&nbsp;<span style='color:#dfe6e9;font-weight:600'>{firm}</span>"
                            f"&nbsp;&nbsp;<span style='background:{g_clr}22;color:{g_clr};font-size:0.75rem;"
                            f"padding:2px 8px;border-radius:10px;font-weight:700'>{to_g}</span>"
                            f"{from_part}</div>"
                            f"<span style='color:#555;font-size:0.72rem'>{date_str}</span>"
                            f"</div>",
                            unsafe_allow_html=True)
                        rows_shown += 1
                        if rows_shown >= 10:
                            break

                    if rows_shown > 0:
                        _ud_shown = True
                        st.caption("※ 目前 yfinance 免費資料僅提供評等方向，個別機構目標價需付費資料源（Bloomberg / FactSet）")
            except Exception:
                pass

            if not _ud_shown:
                st.info("暫無機構評等異動資料（此股票 Yahoo Finance 未收錄海外分析師評等）")

        with col_i2:
            if is_tw:
                # 台灣三大法人
                try:
                    end_d   = datetime.today().strftime('%Y-%m-%d')
                    start_d = (datetime.today() - timedelta(days=20)).strftime('%Y-%m-%d')
                    resp = _req.get(
                        "https://api.finmindtrade.com/api/v4/data",
                        params={"dataset": "TaiwanStockInstitutionalInvestors",
                                "data_id": fetcher.stock_id,
                                "start_date": start_d, "end_date": end_d},
                        timeout=8,
                    )
                    data = resp.json().get('data', [])
                    if data:
                        df_i = pd.DataFrame(data)
                        recent_dates = sorted(df_i['date'].unique())[-5:]
                        df_r = df_i[df_i['date'].isin(recent_dates)]

                        inst_result = {}
                        for display_name, pattern, exclude in [
                            ('外資', '外資', '自營商'),
                            ('投信', '投信', None),
                            ('自營商', '自營商', '外資'),
                        ]:
                            mask = df_r['name'].str.contains(pattern, na=False)
                            if exclude:
                                mask = mask & ~df_r['name'].str.contains(exclude, na=False)
                            rows = df_r[mask]
                            if not rows.empty:
                                buy_col  = 'buy'  if 'buy'  in rows.columns else rows.columns[3]
                                sell_col = 'sell' if 'sell' in rows.columns else rows.columns[4]
                                net = int(rows[buy_col].sum() - rows[sell_col].sum())
                                inst_result[display_name] = net

                        if inst_result:
                            latest_date = recent_dates[-1]
                            st.markdown(
                                f"**台灣三大法人近5日買賣超（張）**"
                                f"<span style='font-size:0.72rem;color:#aaa'> 截至 {latest_date}</span>",
                                unsafe_allow_html=True)
                            for inv, net in inst_result.items():
                                clr = GREEN if net > 0 else RED
                                st.markdown(f"""
                                <div style='display:flex;justify-content:space-between;align-items:center;
                                            background:{clr}12;border:1px solid {clr}40;border-radius:8px;
                                            padding:8px 14px;margin-bottom:6px'>
                                    <span style='color:#aaa;font-size:0.82rem'>{inv}</span>
                                    <span style='color:{clr};font-weight:800;font-size:1rem'>{net:+,} 張</span>
                                </div>""", unsafe_allow_html=True)
                        else:
                            st.info("三大法人資料暫無")
                    else:
                        st.info("三大法人資料暫無（FinMind）")
                except Exception:
                    st.info("三大法人資料暫無")
            else:
                # 美股：買賣彙總
                st.markdown("**📊 分析師評等彙總**")
                _rs_shown = False
                try:
                    rec_sum = fetcher._yf_ticker.recommendations_summary
                    if rec_sum is not None and not rec_sum.empty:
                        _row = rec_sum.iloc[0]
                        sb = int(_row.get('strongBuy',  0) or 0)
                        b  = int(_row.get('buy',        0) or 0)
                        h  = int(_row.get('hold',       0) or 0)
                        s  = int(_row.get('sell',       0) or 0)
                        ss = int(_row.get('strongSell', 0) or 0)
                        total = sb + b + h + s + ss
                        if total > 0:
                            _rs_shown = True
                            for lbl, cnt, clr in [
                                ('強力買進', sb, GREEN), ('買入', b, GREEN),
                                ('持有', h, YELLOW),
                                ('賣出', s, RED),  ('強力賣出', ss, RED),
                            ]:
                                if cnt == 0:
                                    continue
                                pct = cnt / total * 100
                                bar_w = int(pct)
                                st.markdown(
                                    f"<div style='margin-bottom:5px'>"
                                    f"<div style='display:flex;justify-content:space-between;"
                                    f"font-size:0.78rem'>"
                                    f"<span style='color:{clr}'>{lbl}</span>"
                                    f"<span style='color:#aaa'>{cnt} ({pct:.0f}%)</span></div>"
                                    f"<div style='background:#23272f;border-radius:4px;height:6px'>"
                                    f"<div style='width:{bar_w}%;background:{clr};height:6px;"
                                    f"border-radius:4px'></div></div></div>",
                                    unsafe_allow_html=True)
                except Exception:
                    pass
                if not _rs_shown:
                    st.info("暫無評等彙總資料")

        progress.progress(100)
        progress.empty()

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("⚠️ 機構評等資料來源：Yahoo Finance。個別機構目標價需付費資料源（Bloomberg / FactSet），此處顯示分析師共識目標價。")

    except Exception as e:
        progress.empty()
        st.error(f"❌ 分析發生錯誤：{e}")
        import traceback
        st.code(traceback.format_exc())


# ───────────────────────────────────────────────
# 功能一：財務健康檢查
# ───────────────────────────────────────────────
def run_feature1(stock_input: str):
    from modules.data_fetcher import StockDataFetcher
    from modules.feature1_health import FinancialHealthChecker
    from modules.charts import ChartBuilder

    progress = st.progress(0, text="⏳ 正在連線取得資料...")

    try:
        fetcher = StockDataFetcher(stock_input)
        progress.progress(20, text="✅ 連線成功，正在驗證股票...")

        if not fetcher.is_valid():
            progress.empty()
            st.error(f"❌ 找不到股票代碼「{stock_input}」，Yahoo Finance 查無此代碼。")
            is_tw = re.match(r'^\d{4,6}[A-Z]?$', stock_input.strip().upper())
            if is_tw:
                st.info("📌 台股請輸入代碼（如 2330、0050、00919）。部分冷門 ETF 或新上市商品 Yahoo Finance 可能尚未收錄。")
            else:
                st.info("📌 美股請輸入英文代碼（如 AAPL、NVDA、TSLA）。")
            return

        progress.progress(40, text="✅ 驗證完成，正在擷取財務數據...")
        checker = FinancialHealthChecker(fetcher)

        progress.progress(65, text="✅ 資料擷取中，正在計算指標...")
        health = checker.run_full_analysis()

        progress.progress(90, text="✅ 計算完成，正在繪製圖表...")
        charts = ChartBuilder()

        progress.progress(100, text="✅ 完成！")
        progress.empty()

        _display_feature1(fetcher, health, charts)

    except Exception as e:
        progress.empty()
        st.error(f"❌ 分析過程發生錯誤：{e}")
        st.info("請稍後再試，或嘗試其他股票代碼。")


def _display_feature1(fetcher, health: dict, charts):
    m   = health.get('key_metrics', {})
    rev = health.get('revenue_data', {})
    mg  = health.get('margin_data', {})
    cf  = health.get('cashflow_data', {})
    val = health.get('valuation_data', {})
    debt= health.get('debt_data', {})
    peer= health.get('peer_data', [])
    analysis = health.get('analysis', {})
    risk_score = health.get('risk_score', 0)
    risk_level = health.get('risk_level', '未知')
    radar = health.get('radar_scores', {})

    name   = fetcher.get_company_name()
    ticker = fetcher.ticker_symbol

    # ── 頁面標題 ──
    badge_cls, badge_txt = RISK_BADGE.get(risk_level, ("badge-yellow", risk_level))
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.markdown(f'<p class="main-title">📋 {name}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="main-subtitle">{ticker} · 財務健康全面檢查報告</p>',
                    unsafe_allow_html=True)
    with col_h2:
        st.metric("健康評分", f"{risk_score} / 100")
        st.markdown(f'<span class="badge {badge_cls}">{badge_txt}</span>',
                    unsafe_allow_html=True)

    st.markdown("---")

    # ── 核心指標 ──
    st.markdown('<p class="section-title">📊 關鍵指標一覽</p>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        cagr = m.get('revenue_cagr_3y')
        st.metric("3年營收CAGR", fmt(cagr, "%") if cagr is not None else "N/A",
                  delta="強勁" if cagr and cagr > 10 else "持平" if cagr and cagr > 0 else "衰退" if cagr else None)
    with c2:
        st.metric("毛利率", fmt(m.get('latest_gross_margin'), "%"))
    with c3:
        st.metric("淨利率", fmt(m.get('latest_net_margin'), "%"))
    with c4:
        dr = m.get('debt_ratio')
        st.metric("負債比", fmt(dr, "%"),
                  delta="低" if dr and dr < 40 else "高" if dr and dr > 60 else None,
                  delta_color="normal" if not dr else "inverse" if dr > 60 else "off")
    with c5:
        st.metric("本益比 P/E", fmt(m.get('pe_ratio'), "x"))
    with c6:
        cr = m.get('current_ratio')
        st.metric("流動比率", fmt(cr, "x", 2))

    st.markdown("---")

    # ── 圖表區（2x2）──
    st.markdown('<p class="section-title">📈 財務趨勢圖表</p>', unsafe_allow_html=True)

    row1_c1, row1_c2 = st.columns(2)
    with row1_c1:
        if rev.get('revenue'):
            st.plotly_chart(charts.plot_revenue_trend(rev), use_container_width=True)
        else:
            st.info("📭 年度營收資料暫無法取得")

    with row1_c2:
        if any(mg.get(k) for k in ['gross_margin', 'operating_margin', 'net_margin']):
            st.plotly_chart(charts.plot_margin_trend(mg), use_container_width=True)
        else:
            st.info("📭 獲利率資料暫無法取得")

    row2_c1, row2_c2 = st.columns(2)
    with row2_c1:
        if cf.get('operating_cf'):
            st.plotly_chart(charts.plot_cashflow(cf), use_container_width=True)
        else:
            st.info("📭 現金流資料暫無法取得")

    with row2_c2:
        if val:
            st.plotly_chart(
                charts.plot_valuation_comparison(val, peer),
                use_container_width=True
            )
        else:
            st.info("📭 估值資料暫無法取得")

    # ── 負債儀表板 ──
    dr_val = m.get('debt_ratio')
    cr_val = m.get('current_ratio')
    if dr_val is not None and cr_val is not None:
        st.markdown('<p class="section-title">🏦 負債與流動性儀表板</p>', unsafe_allow_html=True)
        st.plotly_chart(charts.plot_debt_gauge(dr_val, cr_val), use_container_width=True)

    st.markdown("---")

    # ── 雷達圖 ──
    if radar:
        st.markdown('<p class="section-title">🎯 財務健康五維雷達圖</p>', unsafe_allow_html=True)
        col_r1, col_r2 = st.columns([3, 2])
        with col_r1:
            st.plotly_chart(charts.plot_radar_chart(radar, name), use_container_width=True)
        with col_r2:
            st.markdown("**各維度說明**")
            desc = {
                "成長力": "近3年營收CAGR，反映業務擴張能力",
                "獲利力": "毛利率與淨利率，反映定價能力與費用控制",
                "現金流": "自由現金流持續性，反映本業造血能力",
                "財務健全": "負債比與流動比率，反映財務穩健度",
                "估值合理": "P/E與P/B水準，反映市場定價合理性",
            }
            for dim, score in radar.items():
                bar_pct = score
                color = "#00b09b" if score >= 70 else "#ffa502" if score >= 50 else "#ff4757"
                st.markdown(f"""
**{dim}** — {score}分
<div style='background:#2d3436;border-radius:4px;height:8px;width:100%'>
  <div style='background:{color};border-radius:4px;height:8px;width:{bar_pct}%'></div>
</div>
<small style='color:#a4b0be'>{desc.get(dim, '')}</small>
""", unsafe_allow_html=True)
                st.markdown("")

    st.markdown("---")

    # ── 文字分析 ──
    st.markdown('<p class="section-title">📝 專業分析報告</p>', unsafe_allow_html=True)
    tabs = st.tabs(["💰 營收與獲利", "💵 現金流與負債", "📊 估值分析", "🏢 同業比較", "⚠️ 投資風險評估"])

    tab_keys = ['revenue_profit', 'cashflow_debt', 'valuation', 'peer_comparison', 'risk_assessment']
    for tab, key in zip(tabs, tab_keys):
        with tab:
            content = analysis.get(key, "數據不足，暫無法生成分析。")
            st.markdown(f'<div class="analysis-box">{content}</div>', unsafe_allow_html=True)

    # ── 免責聲明 ──
    st.markdown("---")
    st.caption("⚠️ 本平台分析報告純屬資訊參考，不構成任何投資建議。投資有風險，請務必自行研判後決策。")
    st.caption("📡 資料來源：Yahoo Finance · FinMind（公開資料）· 資料可能有延遲，以官方公告為準。")


# ───────────────────────────────────────────────
# 功能五：內在價值估算
# ───────────────────────────────────────────────
COLOR_GREEN = "#00c896"
COLOR_RED   = "#ff4444"

def run_feature5(stock_input: str):
    from modules.data_fetcher import StockDataFetcher
    from modules.feature5_valuation import ValuationAnalyzer
    from modules.charts_valuation import ValuationChartBuilder
    import os

    progress = st.progress(0, text="⏳ 正在取得財務資料...")

    try:
        fetcher = StockDataFetcher(stock_input)
        progress.progress(10, text="✅ 連線成功，驗證股票...")

        if not fetcher.is_valid():
            progress.empty()
            st.error(f"❌ 找不到股票「{stock_input}」")
            return

        progress.progress(25, text="✅ 正在計算 WACC 與 DCF 模型...")
        analyzer = ValuationAnalyzer(fetcher)

        progress.progress(50, text="✅ 正在進行同業估值比較...")
        result = analyzer.run_full_analysis()

        progress.progress(75, text="✅ 分析完成，生成估值報告...")
        charts = ValuationChartBuilder()

        api_key = (
            st.session_state.get('claude_api_key', '') or
            os.environ.get('ANTHROPIC_API_KEY', '')
        )
        ai_report = None
        if api_key:
            progress.progress(88, text="🤖 AI 分析師正在撰寫估值報告...")
            ai_report = analyzer.generate_ai_report(result, api_key)

        progress.progress(100, text="✅ 完成！")
        progress.empty()

        _display_feature5(fetcher, result, charts, analyzer, ai_report)

    except Exception as e:
        progress.empty()
        st.error(f"❌ 估值分析發生錯誤：{e}")
        import traceback; st.code(traceback.format_exc())


def _display_feature5(fetcher, result: dict, charts, analyzer, ai_report: Optional[str]):
    syn      = result.get('synthesis', {})
    dcf      = result.get('dcf', {})
    ddm      = result.get('ddm', {})
    hist_val = result.get('hist_val', {})
    peer_val = result.get('peer_val', {})
    wacc_r   = result.get('wacc', {})
    sens     = result.get('sensitivity', {})
    price    = result.get('current_price') or 0.0
    val_m    = result.get('val_metrics', {})

    name   = fetcher.get_company_name()
    ticker = fetcher.ticker_symbol
    is_tw  = fetcher.stock_type == 'TW'
    ccy    = '' if is_tw else '$'

    verdict = syn.get('verdict', '—')
    mos     = syn.get('mos')
    iv_w    = syn.get('iv_weighted')
    color_map = {
        "顯著低估": "#00c896",
        "略有低估": "#5cb85c",
        "合理定價": "#f0c040",
        "略有高估": "#ff8c00",
        "明顯高估": "#ff4444",
    }
    bar_color = color_map.get(verdict, "#aaa")

    # ── 頁頭 ──
    col_h1, col_h2, col_h3 = st.columns([3, 1.3, 1.3])
    with col_h1:
        st.markdown(f'<p class="main-title">💎 {name}</p>', unsafe_allow_html=True)
        st.markdown(
            f'<p class="main-subtitle">{ticker} · 內在價值評估 · 價值投資分析師視角</p>',
            unsafe_allow_html=True,
        )
    with col_h2:
        iv_disp = f"{ccy}{iv_w:,.1f}" if iv_w else "N/A"
        st.markdown(f"""
        <div style='background:{bar_color}22;border:1.5px solid {bar_color};
                    border-radius:10px;padding:14px;text-align:center'>
            <div style='font-size:0.75rem;color:#aaa'>加權內在價值</div>
            <div style='font-size:1.6rem;font-weight:800;color:{bar_color}'>{iv_disp}</div>
            <div style='font-size:0.8rem;color:{bar_color}'>{verdict}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_h3:
        mos_str = f"{mos:+.1f}%" if mos is not None else "N/A"
        mos_color = bar_color
        st.markdown(f"""
        <div style='background:{mos_color}22;border:1.5px solid {mos_color};
                    border-radius:10px;padding:14px;text-align:center'>
            <div style='font-size:0.75rem;color:#aaa'>安全邊際</div>
            <div style='font-size:1.6rem;font-weight:800;color:{mos_color}'>{mos_str}</div>
            <div style='font-size:0.8rem;color:#aaa'>目前股價 {ccy}{f"{price:,.1f}" if price else "N/A"}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── API Key 提示 ──
    if not ai_report:
        with st.expander("🤖 啟用 AI 深度估值報告（Claude API）", expanded=False):
            st.markdown("設定 Claude API Key 後，將由 AI 撰寫 1500+ 字完整估值報告。")
            col_k1, col_k2 = st.columns([4, 1])
            with col_k1:
                key_input = st.text_input(
                    "API Key", type="password",
                    value=st.session_state.get('claude_api_key', ''),
                    key="api_key_input_f5", label_visibility="collapsed",
                    placeholder="sk-ant-..."
                )
            with col_k2:
                if st.button("套用並重新分析", use_container_width=True, key="rerun_f5"):
                    st.session_state.claude_api_key = key_input
                    st.session_state.stock_input    = fetcher.original_input
                    st.session_state.trigger_run    = True
                    st.rerun()

    # ── WACC 參數卡片 ──
    st.markdown('<p class="section-title">⚙️ 折現率參數 (WACC)</p>', unsafe_allow_html=True)
    wc1, wc2, wc3, wc4, wc5 = st.columns(5)
    with wc1:
        st.metric("WACC", f"{wacc_r.get('wacc', 0)*100:.1f}%")
    with wc2:
        st.metric("股東必要報酬 Ke", f"{wacc_r.get('ke', 0)*100:.1f}%")
    with wc3:
        st.metric("稅後負債成本 Kd", f"{wacc_r.get('kd', 0)*100:.1f}%")
    with wc4:
        st.metric("Beta 係數", f"{wacc_r.get('beta', 0):.2f}")
    with wc5:
        we_pct = wacc_r.get('we', 0) * 100
        wd_pct = wacc_r.get('wd', 0) * 100
        st.metric("股權/負債比", f"{we_pct:.0f}% / {wd_pct:.0f}%")

    st.markdown("---")

    # ── 估值總覽 + 各方法彙整 ──
    st.markdown('<p class="section-title">🎯 估值總覽</p>', unsafe_allow_html=True)
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        if syn.get('available'):
            st.plotly_chart(charts.plot_value_summary(syn, price), use_container_width=True)
        else:
            st.warning(syn.get('message', '估值資料不足'))
    with col_v2:
        st.plotly_chart(charts.plot_estimates_bar(syn, price), use_container_width=True)

    st.markdown("---")

    # ── DCF 分析 ──
    if dcf.get('available'):
        st.markdown('<p class="section-title">📊 DCF 現金流折現分析</p>', unsafe_allow_html=True)

        # FCF 成長率資訊
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            fcf = dcf.get('fcf_latest', 0)
            st.metric("最新年度 FCF", f"{ccy}{fcf/1e8:.1f}億" if fcf else "N/A")
        with fc2:
            hcagr = dcf.get('hist_cagr')
            st.metric("FCF 歷史 CAGR", f"{hcagr*100:.1f}%" if hcagr else "N/A")
        with fc3:
            rcagr = dcf.get('rev_cagr')
            st.metric("營收 CAGR", f"{rcagr*100:.1f}%" if rcagr else "N/A")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.plotly_chart(charts.plot_dcf_scenarios(dcf, price), use_container_width=True)
        with col_d2:
            # 情境選擇
            scenario_choice = st.radio("查看 DCF 現金流分解：",
                                        ["基本", "樂觀", "悲觀"],
                                        horizontal=True, key="dcf_scene")
            st.plotly_chart(charts.plot_dcf_breakdown(dcf, scenario_choice),
                            use_container_width=True)
    else:
        st.info(f"⚠️ {dcf.get('message', 'DCF 資料不足')}")

    st.markdown("---")

    # ── 敏感度矩陣 ──
    if sens.get('available'):
        st.markdown('<p class="section-title">🔥 DCF 敏感度分析（WACC × 成長率）</p>',
                    unsafe_allow_html=True)
        st.plotly_chart(charts.plot_sensitivity_heatmap(sens, price), use_container_width=True)
        st.caption(f"💡 綠色格子代表估值高於目前股價（潛在低估），紅色代表低於目前股價（潛在高估）。"
                   f"基礎 WACC = {wacc_r.get('wacc', 0)*100:.1f}%")

    st.markdown("---")

    # ── 歷史估值帶 + DDM ──
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.markdown('<p class="section-title">📅 歷史 P/E 帶狀圖</p>', unsafe_allow_html=True)
        if hist_val.get('available') and hist_val.get('price_bands'):
            st.plotly_chart(charts.plot_historical_pe_band(hist_val), use_container_width=True)
            pe_data = hist_val.get('pe', {})
            if pe_data:
                pc1, pc2, pc3, pc4 = st.columns(4)
                pc1.metric("目前 P/E", f"{pe_data.get('current') or 'N/A':.1f}x"
                           if pe_data.get('current') else "N/A")
                pc2.metric("5y 均值", f"{pe_data.get('avg') or 'N/A':.1f}x"
                           if pe_data.get('avg') else "N/A")
                pc3.metric("5y 低點", f"{pe_data.get('min') or 'N/A':.1f}x"
                           if pe_data.get('min') else "N/A")
                pc4.metric("5y 高點", f"{pe_data.get('max') or 'N/A':.1f}x"
                           if pe_data.get('max') else "N/A")
        else:
            st.info("歷史 P/E 帶：EPS 資料不足，無法繪製")

    with col_h2:
        st.markdown('<p class="section-title">💰 DDM 股息折現模型</p>', unsafe_allow_html=True)
        if ddm.get('available'):
            dd1, dd2, dd3 = st.columns(3)
            dd1.metric("DPS（年化）", f"{ccy}{ddm.get('dps', 0):.4f}")
            dd2.metric("股息殖利率", f"{ddm.get('div_yield', 0):.2f}%")
            dd3.metric("DDM 合理股價", f"{ccy}{ddm.get('iv_ddm', 0):,.2f}")

            st.markdown("**DDM 三情境（不同股息成長假設）：**")
            ddm_sc = ddm.get('scenarios', {})
            sc_cols = st.columns(len(ddm_sc))
            for col_obj, (lbl, sc) in zip(sc_cols, ddm_sc.items()):
                with col_obj:
                    st.markdown(f"""
                    <div style='background:#1a1f2e;border-radius:8px;padding:12px;
                                text-align:center;border:1px solid #2d3436'>
                        <div style='font-size:0.75rem;color:#aaa'>{lbl}情境</div>
                        <div style='font-size:1.2rem;font-weight:700;color:#dfe6e9'>
                            {ccy}{sc.get('iv', 0):,.1f}
                        </div>
                        <div style='font-size:0.75rem;color:#a4b0be'>g={sc.get('g', 0):.1f}%</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown(f"""<small style='color:#a4b0be'>
            ROE={ddm.get('roe') or 'N/A'}%，
            配息率={ddm.get('payout') or 'N/A'}%，
            永續成長率 g={ddm.get('g_ddm', 0):.2f}%，
            股東必要報酬率 Ke={ddm.get('ke', 0):.2f}%
            </small>""", unsafe_allow_html=True)
        else:
            st.info(ddm.get('message', '此股票不適用 DDM（不配息）'))

    st.markdown("---")

    # ── 同業估值比較 ──
    st.markdown('<p class="section-title">🏭 同業估值比較</p>', unsafe_allow_html=True)
    if peer_val.get('available'):
        col_p1, col_p2 = st.columns([3, 1])
        with col_p1:
            st.plotly_chart(charts.plot_peer_valuation(peer_val), use_container_width=True)
        with col_p2:
            st.plotly_chart(charts.plot_valuation_radar(syn, peer_val), use_container_width=True)

        # 同業相對估值推算
        if peer_val.get('peer_iv'):
            peer_iv = peer_val['peer_iv']
            med_pe  = peer_val.get('medians', {}).get('pe') or 0
            mos_peer = (peer_iv - price) / peer_iv * 100 if peer_iv and price else None
            mos_color = bar_color if mos_peer is None else (
                COLOR_GREEN if mos_peer >= 0 else COLOR_RED)
            med_pe_str  = f"{med_pe:.1f}" if med_pe else "N/A"
            mos_peer_str = f"{mos_peer:+.1f}%" if mos_peer is not None else "N/A"
            st.markdown(f"""
            <div style='background:{mos_color}15;border:1px solid {mos_color};
                        border-radius:8px;padding:12px 16px;margin:8px 0'>
                <b>同業 P/E 相對估值：</b> 依同業中位數 P/E（{med_pe_str}x）推算合理股價
                <span style='font-size:1.2rem;font-weight:700;color:{mos_color}'>
                {ccy}{peer_iv:,.1f}
                </span>
                （折溢價：{mos_peer_str}）
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info(peer_val.get('message', '同業資料不足'))

    st.markdown("---")

    # ── 估值報告 ──
    st.markdown('<p class="section-title">📝 估值深度報告</p>', unsafe_allow_html=True)
    if ai_report:
        st.markdown(f"""
        <div style='background:#141820;border-left:4px solid #00b09b;
                    border-radius:0 8px 8px 0;padding:12px 20px;
                    line-height:1.8;font-size:0.92rem;margin-bottom:8px'>
        🤖 <em>以下報告由 Claude AI 分析師根據量化估值模型生成</em>
        </div>""", unsafe_allow_html=True)
        st.markdown(ai_report)
    else:
        tabs = st.tabs(["🔢 DCF 分析", "💰 相對估值 / DDM", "📅 歷史 P/E 區間",
                        "🎯 綜合結論 / 安全邊際", "⚠️ 風險提示"])

        # ── Tab 0：DCF 分析 ──
        with tabs[0]:
            if dcf.get('available'):
                sc = dcf.get('scenarios', {})
                wacc_pct = dcf.get('wacc', 0) * 100
                lines = [
                    f"**WACC：{wacc_pct:.1f}%**　永續成長率：{dcf.get('g_term',0)*100:.1f}%　投影期：10年",
                    "",
                    "| 情境 | 年均成長率 | 每股內在價值 |",
                    "|------|----------|------------|",
                ]
                for lbl in ['樂觀', '基本', '悲觀']:
                    s = sc.get(lbl, {})
                    iv_s = s.get('iv_per_share')
                    iv_str = f"{iv_s:,.1f}" if iv_s and iv_s > 0 else 'N/A'
                    lines.append(f"| {lbl} | {s.get('g_proj','—')}% | {ccy}{iv_str} |")
                fcf_v = dcf.get('fcf_latest', 0)
                lines += [
                    "",
                    f"**最新年度 FCF：** {ccy}{fcf_v/1e8:.1f} 億",
                    f"**FCF 歷史 CAGR：** {(dcf.get('hist_cagr') or 0)*100:.1f}%",
                    f"**營收 CAGR：** {(dcf.get('rev_cagr') or 0)*100:.1f}%",
                ]
                st.markdown('\n'.join(lines))
            else:
                st.info(f"⚠️ DCF 資料不足：{dcf.get('message','FCF 無法取得')}")

        # ── Tab 1：相對估值 / DDM ──
        with tabs[1]:
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.markdown("**同業相對估值**")
                if peer_val.get('available') and peer_val.get('peer_iv'):
                    med_pe = peer_val.get('medians', {}).get('pe', 0) or 0
                    peer_iv_v = peer_val['peer_iv']
                    st.markdown(f"- 同業中位數 P/E：**{med_pe:.1f}x**")
                    st.markdown(f"- P/E 相對估值股價：**{ccy}{peer_iv_v:,.1f}**")
                    mos_peer = (peer_iv_v - price) / peer_iv_v * 100 if peer_iv_v and price else None
                    if mos_peer is not None:
                        arrow = "🟢" if mos_peer >= 0 else "🔴"
                        st.markdown(f"- 折溢價：{arrow} **{mos_peer:+.1f}%**")
                else:
                    st.info(peer_val.get('message', '同業資料不足'))
            with col_t2:
                st.markdown("**DDM 股息折現**")
                if ddm.get('available'):
                    st.markdown(f"- DPS（年化）：**{ccy}{ddm.get('dps',0):.4f}**")
                    st.markdown(f"- 股息殖利率：**{ddm.get('div_yield',0):.2f}%**")
                    st.markdown(f"- 永續成長率 g：**{ddm.get('g_ddm',0):.2f}%**")
                    st.markdown(f"- 股東必要報酬 Ke：**{ddm.get('ke',0):.2f}%**")
                    st.markdown(f"- **DDM 合理股價：{ccy}{ddm.get('iv_ddm',0):,.2f}**")
                else:
                    st.info(ddm.get('message', '此股票不配息，不適用 DDM'))

        # ── Tab 2：歷史 P/E 區間 ──
        with tabs[2]:
            if hist_val.get('available') and hist_val.get('pe'):
                pe_d = hist_val['pe']
                st.markdown("**近5年 P/E 估值帶**")
                cols_pe = st.columns(4)
                cols_pe[0].metric("目前 P/E", f"{pe_d.get('current') or '—'}x"
                                  if not pe_d.get('current') else f"{pe_d['current']:.1f}x")
                cols_pe[1].metric("5y 均值", f"{pe_d.get('avg',0):.1f}x")
                cols_pe[2].metric("5y 低點", f"{pe_d.get('min',0):.1f}x")
                cols_pe[3].metric("5y 高點", f"{pe_d.get('max',0):.1f}x")
                eps_l = pe_d.get('eps_latest')
                if eps_l:
                    avg_pe = pe_d.get('avg', 0)
                    st.markdown(
                        f"**均值估值股價：** {ccy}{avg_pe * eps_l:,.1f}  "
                        f"（最新 EPS = {ccy}{eps_l:,.2f}）"
                    )
            else:
                st.info("歷史 P/E 區間資料不足（EPS 無法取得）")

        # ── Tab 3：綜合結論 / 安全邊際 ──
        with tabs[3]:
            if syn.get('available'):
                st.markdown(f"### 投資結論：{syn.get('verdict','—')}")
                st.markdown(f"> {syn.get('advice','')}")
                st.markdown("")
                iv_w_v  = syn.get('iv_weighted', 0)
                mos_v   = syn.get('mos')
                iv_lo   = syn.get('iv_low', 0)
                iv_hi   = syn.get('iv_high', 0)
                sc2, sc3, sc4 = st.columns(3)
                sc2.metric("加權內在價值", f"{ccy}{iv_w_v:,.1f}")
                sc3.metric("估值範圍", f"{ccy}{iv_lo:,.1f} ~ {ccy}{iv_hi:,.1f}")
                sc4.metric("安全邊際", f"{mos_v:+.1f}%" if mos_v is not None else "N/A")
                st.markdown("**各方法估值彙整：**")
                for e in syn.get('estimates', []):
                    arrow = "🟢" if e['iv'] >= price else "🔴"
                    st.markdown(
                        f"- {arrow} **{e['method']}**：{ccy}{e['iv']:,.1f}  "
                        f"（權重 {e['weight']*100:.0f}%）"
                    )
            else:
                st.warning(syn.get('message', '估值資料不足'))

        # ── Tab 4：風險提示 ──
        with tabs[4]:
            st.markdown("""
**使用本估值模型前，請留意以下風險因素：**

1. **成長率假設的不確定性**
   DCF 模型高度依賴未來成長率假設，實際成長可能大幅偏離預測。

2. **折現率 (WACC) 的敏感性**
   WACC 每變動 1%，估值可能波動 15~30%，請參考敏感度矩陣。

3. **FCF 的異常波動**
   資本密集產業（如半導體）在大規模資本支出年份 FCF 可能為負，此時以代理值估算。

4. **同業比較的局限**
   同業 P/E 基準反映市場情緒，在市場泡沫或恐慌時可能高度失真。

5. **本模型基於公開財務數據**
   不包含非公開資訊、政策風險、地緣政治等定性因素。

⚠️ *以上估值結果純屬研究用途，不構成任何投資建議。*
""")


    st.markdown("---")
    st.caption("⚠️ 本估值模型基於公開財務數據，結果高度依賴成長率與折現率假設，僅供研究參考，不構成投資建議。")
    st.caption("📡 資料來源：Yahoo Finance · FinMind · DCF/DDM/Beneish/Piotroski 學術模型")


# ───────────────────────────────────────────────
# 觀察清單（所有用戶共用同一份）
# ───────────────────────────────────────────────
import json as _json, os as _os

_WL_FILE = '/tmp/wl.json'

def _wl_load() -> list:
    try:
        with open(_WL_FILE, 'r', encoding='utf-8') as f:
            return _json.load(f)
    except Exception:
        return []

def _wl_save(lst: list):
    try:
        with open(_WL_FILE, 'w', encoding='utf-8') as f:
            _json.dump(lst, f, ensure_ascii=False)
    except Exception:
        pass

def _watchlist_add(code: str, label: str):
    lst = _wl_load()
    code = code.strip().upper()
    if code and not any(s['code'] == code for s in lst):
        lst.append({'code': code, 'label': label or code})
        _wl_save(lst)

def _watchlist_remove(code: str):
    lst = [s for s in _wl_load() if s['code'] != code]
    _wl_save(lst)


# ───────────────────────────────────────────────
# Sidebar
# ───────────────────────────────────────────────
def build_sidebar() -> tuple[str, str]:
    with st.sidebar:
        st.markdown("### 📊 股票分析平台")
        st.markdown("---")

        # 股票輸入
        default_val = st.session_state.get('stock_input', '')
        stock_input = st.text_input(
            "🔍 輸入股票代碼",
            value=default_val,
            placeholder="台股:2330  美股:AAPL",
            help="台股輸入4碼數字，美股輸入英文代碼",
        )

        run_btn = st.button("🔍 開始分析", type="primary", use_container_width=True)
        st.markdown("---")

        # ── 觀察清單 ──
        st.markdown("**👁 觀察清單**")
        watchlist = _wl_load()

        if watchlist:
            for item in watchlist:
                col_w1, col_w2 = st.columns([4, 1])
                with col_w1:
                    if st.button(item['label'], key=f"wl_{item['code']}",
                                 use_container_width=True):
                        st.session_state.stock_input = item['code']
                        st.session_state.trigger_run = True
                        st.rerun()
                with col_w2:
                    if st.button("✕", key=f"wl_del_{item['code']}",
                                 help="從清單移除"):
                        _watchlist_remove(item['code'])
                        st.rerun()
        else:
            st.caption("尚無觀察股票，請在下方新增")

        # 新增到觀察清單
        with st.expander("＋ 新增股票到清單"):
            wl_input = st.text_input("股票代碼", placeholder="如 2330 或 AAPL",
                                     key="wl_add_code")
            wl_label = st.text_input("顯示名稱（可空白）", placeholder="如 台積電",
                                     key="wl_add_label")
            if st.button("加入清單", use_container_width=True, key="wl_add_btn"):
                if wl_input.strip():
                    label = wl_label.strip() or wl_input.strip().upper()
                    _watchlist_add(wl_input.strip(), f"{label} {wl_input.strip().upper()}"
                                   if wl_label.strip() else wl_input.strip().upper())
                    st.rerun()

        st.markdown("---")

        # 功能選單
        st.markdown("**選擇功能**")
        selected_feature = None
        for icon, name, enabled in FEATURE_LIST:
            label = f"{icon} {name}" if enabled else f"{icon} {name} *(即將推出)*"
            if st.button(label, use_container_width=True,
                         disabled=not enabled,
                         key=f"feat_{name}"):
                selected_feature = name

        st.markdown("---")

        # 熱門快速選股
        st.markdown("**快速選股**")
        for label, code in list(POPULAR_STOCKS.items())[:4]:
            if st.button(label, use_container_width=True, key=f"sb_{code}"):
                st.session_state.stock_input = code
                st.session_state.trigger_run = True
                st.rerun()

        st.markdown("---")
        st.caption("📡 資料：Yahoo Finance · FinMind")
        st.caption("🔄 更新：每次查詢即時抓取")

    return stock_input, "概覽" if run_btn else (selected_feature or "")


# ───────────────────────────────────────────────
# 主流程
# ───────────────────────────────────────────────
def main():
    stock_input, action = build_sidebar()

    # 快速按鈕（熱門股/觀察清單）觸發 → 預設顯示概覽
    if st.session_state.get('trigger_run'):
        st.session_state.trigger_run = False
        stock_input = st.session_state.get('stock_input', stock_input)
        action = st.session_state.get('pending_feature', '概覽')
        st.session_state.pop('pending_feature', None)

    # Dashboard 功能卡片點擊：有 pending_feature 但還沒輸入股票 → 提示輸入
    if st.session_state.get('pending_feature') and not stock_input.strip():
        pending = st.session_state.pop('pending_feature')
        show_welcome()
        st.info(f"請在左側 Sidebar 輸入股票代碼，然後點「開始分析」使用「{pending}」功能。")
        return

    # 功能卡片 + 已有股票代碼 → 直接執行
    if st.session_state.get('pending_feature') and stock_input.strip():
        action = st.session_state.pop('pending_feature')

    if not stock_input.strip() or not action:
        show_welcome()
        return

    if action == "概覽":
        run_stock_overview(stock_input.strip())
    elif action == "財務健康檢查":
        run_feature1(stock_input.strip())
    elif action == "技術面分析":
        run_feature2(stock_input.strip())
    elif action == "產業競爭分析":
        run_feature3(stock_input.strip())
    elif action == "隱藏風險偵測":
        run_feature4(stock_input.strip())
    elif action == "內在價值估算":
        run_feature5(stock_input.strip())
    else:
        st.info(f"「{action}」功能即將推出，敬請期待！")


if __name__ == "__main__":
    for key in ['trigger_run', 'pending_feature']:
        if key not in st.session_state:
            st.session_state[key] = False if key == 'trigger_run' else None
    main()
