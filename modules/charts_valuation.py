"""
Feature 5: Valuation Analysis - Chart Builder
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

BG   = "#0e1117"
CARD = "#1a1d2e"
TEXT = "#e0e0e0"
GRID = "#2a2d3e"

COLOR_GREEN  = "#00c896"
COLOR_YELLOW = "#f0c040"
COLOR_ORANGE = "#ff8c00"
COLOR_RED    = "#ff4444"
COLOR_BLUE   = "#4a9eff"
COLOR_PURPLE = "#9b59b6"
COLOR_TEAL   = "#26d0ce"


def _verdict_color(mos: float) -> str:
    if mos is None:
        return "#aaa"
    if mos >= 30:
        return COLOR_GREEN
    if mos >= 15:
        return "#5cb85c"
    if mos >= -10:
        return COLOR_YELLOW
    if mos >= -25:
        return COLOR_ORANGE
    return COLOR_RED


class ValuationChartBuilder:

    # ──────────────────────────────────────────
    # 1. 綜合估值儀表（核心卡片）
    # ──────────────────────────────────────────
    def plot_value_summary(self, synthesis: dict, current_price: float) -> go.Figure:
        if not synthesis.get('available'):
            return _empty_fig("估值綜合摘要 (資料不足)")

        iv     = synthesis.get('iv_weighted', 0)
        iv_low = synthesis.get('iv_low', iv * 0.8)
        iv_hig = synthesis.get('iv_high', iv * 1.2)
        mos    = synthesis.get('mos')
        verdict = synthesis.get('verdict', '—')
        color  = _verdict_color(mos)

        fig = go.Figure()

        # 估值範圍帶（灰色底）
        fig.add_shape(type="rect",
                      x0=-0.4, x1=0.4,
                      y0=iv_low, y1=iv_hig,
                      fillcolor="rgba(255,255,255,0.06)",
                      line=dict(color=GRID, width=1))

        # 內在價值（加權）
        fig.add_trace(go.Scatter(
            x=[0], y=[iv],
            mode='markers+text',
            marker=dict(size=22, color=COLOR_BLUE, symbol='diamond'),
            text=[f"  內在價值<br>  {iv:,.1f}"],
            textposition='middle right',
            textfont=dict(color=COLOR_BLUE, size=13),
            name='加權內在價值',
        ))

        # 目前股價
        price_color = color
        fig.add_hline(y=current_price,
                      line=dict(color=price_color, width=2.5, dash='solid'),
                      annotation_text=f"  目前股價  {current_price:,.1f}",
                      annotation_font=dict(color=price_color, size=13),
                      annotation_position="right")

        # 低/高估值邊界
        fig.add_hline(y=iv_low, line=dict(color=GRID, width=1, dash='dot'),
                      annotation_text=f" 低估 {iv_low:,.1f}",
                      annotation_font=dict(color=GRID, size=10))
        fig.add_hline(y=iv_hig, line=dict(color=GRID, width=1, dash='dot'),
                      annotation_text=f" 高估 {iv_hig:,.1f}",
                      annotation_font=dict(color=GRID, size=10))

        # 各方法估值點
        estimates = synthesis.get('estimates', [])
        for i, e in enumerate(estimates):
            if not e.get('iv'):
                continue
            fig.add_trace(go.Scatter(
                x=[0.05 * (i - len(estimates) // 2)],
                y=[e['iv']],
                mode='markers+text',
                marker=dict(size=10, color=COLOR_TEAL, opacity=0.7),
                text=[f"  {e['method']}<br>  {e['iv']:,.1f}"],
                textposition='middle right',
                textfont=dict(color=TEXT, size=10),
                name=e['method'],
                showlegend=False,
            ))

        mos_str = f"{mos:+.1f}%" if mos is not None else "N/A"
        fig.update_layout(
            title={"text": f"估值總覽  ·  {verdict}  ·  安全邊際 {mos_str}",
                   "font": {"color": color, "size": 16}, "x": 0.02},
            paper_bgcolor=BG, plot_bgcolor=CARD,
            font={"color": TEXT},
            height=400,
            margin=dict(t=55, b=30, l=30, r=180),
            xaxis=dict(visible=False, range=[-1, 1]),
            yaxis=dict(showgrid=True, gridcolor=GRID, tickfont={"color": TEXT},
                       zeroline=False),
            showlegend=False,
        )
        return fig

    # ──────────────────────────────────────────
    # 2. DCF 現金流分解圖（瀑布圖）
    # ──────────────────────────────────────────
    def plot_dcf_breakdown(self, dcf: dict, scenario: str = '基本') -> go.Figure:
        if not dcf.get('available'):
            return _empty_fig("DCF 現金流分解 (資料不足)")

        sc = dcf.get('scenarios', {}).get(scenario)
        if not sc:
            return _empty_fig(f"DCF {scenario}情境 (資料不足)")

        pv_fcfs = sc.get('pv_fcfs', [])
        pv_tv   = sc.get('pv_tv', 0)

        if not pv_fcfs:
            return _empty_fig("DCF 分解 (年度資料不足)")

        years  = [f"Y{p['year']}" for p in pv_fcfs]
        pvs    = [p['pv'] / 1e8 for p in pv_fcfs]  # 億元
        tv_bn  = pv_tv / 1e8

        colors = [COLOR_BLUE] * len(pvs) + [COLOR_TEAL]
        fig = go.Figure(go.Bar(
            x=years + ['終端價值'],
            y=pvs + [tv_bn],
            marker_color=colors,
            marker_opacity=0.85,
            text=[f"{v:.1f}億" for v in pvs] + [f"{tv_bn:.1f}億"],
            textposition='outside',
            textfont=dict(color=TEXT, size=10),
        ))

        sum_pv_bn = sum(pvs)
        fig.add_hline(y=0, line=dict(color=GRID, width=1))
        fig.add_annotation(
            x=len(years) - 1, y=max(pvs + [tv_bn]) * 1.15,
            text=f"投影現值總和：{sum_pv_bn:.1f}億<br>終端價值現值：{tv_bn:.1f}億<br>成長率假設：{sc.get('g_proj', 0):.1f}%",
            showarrow=False,
            font=dict(color=TEXT, size=11),
            bgcolor=CARD, bordercolor=GRID, borderwidth=1,
            align='left',
        )

        fig.update_layout(
            title={"text": f"DCF 現金流分解 — {scenario}情境（億元）",
                   "font": {"color": TEXT, "size": 15}, "x": 0.02},
            paper_bgcolor=BG, plot_bgcolor=CARD,
            font={"color": TEXT}, height=380,
            margin=dict(t=55, b=40, l=60, r=20),
            xaxis=dict(showgrid=False, tickfont={"color": TEXT}),
            yaxis=dict(showgrid=True, gridcolor=GRID, tickfont={"color": TEXT},
                       title="億元", title_font={"color": TEXT}),
        )
        return fig

    # ──────────────────────────────────────────
    # 3. DCF 三情境比較
    # ──────────────────────────────────────────
    def plot_dcf_scenarios(self, dcf: dict, current_price: float) -> go.Figure:
        if not dcf.get('available'):
            return _empty_fig("DCF 情境比較 (資料不足)")

        scenarios = dcf.get('scenarios', {})
        labels, ivs, colors = [], [], []
        for lbl, col in [('悲觀', COLOR_RED), ('基本', COLOR_BLUE), ('樂觀', COLOR_GREEN)]:
            sc = scenarios.get(lbl, {})
            iv = sc.get('iv_per_share')
            if iv and iv > 0:
                labels.append(f"{lbl}\n({sc.get('g_proj', 0):.0f}%成長)")
                ivs.append(iv)
                colors.append(col)

        if not ivs:
            return _empty_fig("DCF 情境比較 (FCF 資料不足)")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=labels, y=ivs,
            marker_color=colors, marker_opacity=0.85,
            text=[f"{v:,.1f}" for v in ivs],
            textposition='outside',
            textfont=dict(color=TEXT, size=12),
            name='內在價值',
        ))
        if current_price:
            fig.add_hline(y=current_price,
                          line=dict(color=COLOR_YELLOW, width=2, dash='dash'),
                          annotation_text=f"  目前股價 {current_price:,.1f}",
                          annotation_font=dict(color=COLOR_YELLOW, size=12))

        fig.update_layout(
            title={"text": "DCF 三情境內在價值比較",
                   "font": {"color": TEXT, "size": 15}, "x": 0.02},
            paper_bgcolor=BG, plot_bgcolor=CARD,
            font={"color": TEXT}, height=360,
            margin=dict(t=55, b=40, l=60, r=20),
            xaxis=dict(showgrid=False, tickfont={"color": TEXT}),
            yaxis=dict(showgrid=True, gridcolor=GRID, tickfont={"color": TEXT}),
            showlegend=False,
        )
        return fig

    # ──────────────────────────────────────────
    # 4. 敏感度矩陣 Heatmap
    # ──────────────────────────────────────────
    def plot_sensitivity_heatmap(self, sensitivity: dict, current_price: float) -> go.Figure:
        if not sensitivity.get('available'):
            return _empty_fig("敏感度矩陣 (資料不足)")

        matrix     = sensitivity.get('matrix', [])
        wacc_lbl   = sensitivity.get('wacc_labels', [])
        g_lbl      = sensitivity.get('g_labels', [])

        if not matrix or not wacc_lbl or not g_lbl:
            return _empty_fig("敏感度矩陣 (資料不足)")

        # 標記目前股價相對位置（綠=低於現價/便宜, 紅=高於現價/貴）
        z_text = []
        z_vals = []
        for row in matrix:
            text_row, val_row = [], []
            for v in row:
                if v is None:
                    text_row.append("N/A")
                    val_row.append(None)
                else:
                    text_row.append(f"{v:,.0f}")
                    # 用與現價的折溢價百分比作為顏色值
                    val_row.append((v - current_price) / current_price * 100 if current_price else 0)
            z_text.append(text_row)
            z_vals.append(val_row)

        fig = go.Figure(go.Heatmap(
            z=z_vals,
            x=wacc_lbl,
            y=g_lbl,
            text=z_text,
            texttemplate="%{text}",
            textfont=dict(size=11, color="white"),
            colorscale=[
                [0.0,  "#660000"],
                [0.35, "#993300"],
                [0.50, "#443300"],
                [0.65, "#004433"],
                [1.0,  "#006622"],
            ],
            zmid=0,
            colorbar=dict(
                title=dict(text="折溢價%", font=dict(color=TEXT)),
                tickfont=dict(color=TEXT),
                ticksuffix="%",
            ),
            hovertemplate="成長率: %{y}<br>WACC: %{x}<br>內在價值: %{text}<extra></extra>",
        ))

        fig.update_layout(
            title={"text": "DCF 敏感度矩陣：不同 WACC × 成長率假設下的內在價值",
                   "font": {"color": TEXT, "size": 14}, "x": 0.02},
            paper_bgcolor=BG, plot_bgcolor=CARD,
            font={"color": TEXT}, height=380,
            margin=dict(t=60, b=50, l=70, r=80),
            xaxis=dict(title="WACC（折現率）", tickfont={"color": TEXT},
                       title_font={"color": TEXT}),
            yaxis=dict(title="投影成長率（前5年）", tickfont={"color": TEXT},
                       title_font={"color": TEXT}),
        )
        return fig

    # ──────────────────────────────────────────
    # 5. 歷史 P/E 帶狀圖
    # ──────────────────────────────────────────
    def plot_historical_pe_band(self, hist_val: dict) -> go.Figure:
        if not hist_val.get('available'):
            return _empty_fig("歷史 P/E 帶狀圖 (資料不足)")

        bands = hist_val.get('price_bands')
        pe    = hist_val.get('pe', {})

        if not bands:
            return _empty_fig("歷史 P/E 帶狀圖 (EPS 資料不足)")

        dates = bands.get('dates', [])
        price = bands.get('price', [])
        b_low = bands.get('fair_band_low', 0)
        b_hig = bands.get('fair_band_high', 0)
        b_avg = bands.get('avg_band', 0)

        fig = go.Figure()

        # 公平價值帶（25%-75%）
        fig.add_trace(go.Scatter(
            x=dates + dates[::-1],
            y=[b_hig] * len(dates) + [b_low] * len(dates),
            fill='toself',
            fillcolor='rgba(74,158,255,0.12)',
            line=dict(color='rgba(0,0,0,0)'),
            name='歷史公平帶 (P25-P75)',
            hoverinfo='skip',
        ))

        # 歷史均值帶
        fig.add_hline(y=b_avg, line=dict(color=COLOR_BLUE, width=1.5, dash='dash'),
                      annotation_text=f"  均值 P/E × EPS = {b_avg:,.1f}",
                      annotation_font=dict(color=COLOR_BLUE, size=11))

        # 股價曲線
        fig.add_trace(go.Scatter(
            x=dates, y=price,
            name='股價', line=dict(color=COLOR_YELLOW, width=2),
            mode='lines',
        ))

        # 目前 P/E 位置
        pe_cur  = pe.get('current')
        pe_avg  = pe.get('avg')
        pe_min  = pe.get('min')
        pe_max  = pe.get('max')

        if pe_cur and pe_avg:
            vs_avg = (pe_cur - pe_avg) / pe_avg * 100
            annotation_txt = (f"目前 P/E: {pe_cur:.1f}x<br>"
                               f"5y 均值: {pe_avg:.1f}x<br>"
                               f"5y 區間: {pe_min:.1f}x ~ {pe_max:.1f}x<br>"
                               f"vs 均值: {vs_avg:+.1f}%")
            fig.add_annotation(
                x=0.98, y=0.98, xref='paper', yref='paper',
                text=annotation_txt, showarrow=False,
                align='right', font=dict(color=TEXT, size=11),
                bgcolor=CARD, bordercolor=GRID, borderwidth=1,
            )

        fig.update_layout(
            title={"text": "股價 vs 歷史 P/E 公平帶（近5年）",
                   "font": {"color": TEXT, "size": 15}, "x": 0.02},
            paper_bgcolor=BG, plot_bgcolor=CARD,
            font={"color": TEXT}, height=380,
            margin=dict(t=55, b=40, l=60, r=20),
            legend=dict(bgcolor=CARD, bordercolor=GRID, borderwidth=1),
            xaxis=dict(showgrid=False, tickfont={"color": TEXT}),
            yaxis=dict(showgrid=True, gridcolor=GRID, tickfont={"color": TEXT}),
        )
        return fig

    # ──────────────────────────────────────────
    # 6. 同業估值比較（多指標）
    # ──────────────────────────────────────────
    def plot_peer_valuation(self, peer_val: dict) -> go.Figure:
        if not peer_val.get('available'):
            return _empty_fig("同業估值比較 (資料不足)")

        subject = peer_val.get('subject', {})
        peers   = peer_val.get('peers', [])
        if not peers:
            return _empty_fig("同業估值比較 (無同業資料)")

        # 合併主體與同業
        all_cos = [subject] + peers
        names   = [c.get('name', c.get('ticker', '?'))[:12] for c in all_cos]
        colors  = [COLOR_YELLOW] + [COLOR_BLUE] * len(peers)

        fig = make_subplots(rows=1, cols=3,
                            subplot_titles=("P/E 市盈率", "P/B 市淨率", "P/S 市銷率"),
                            horizontal_spacing=0.08)

        for col_idx, metric in enumerate(['pe', 'pb', 'ps'], start=1):
            vals = [c.get(metric) for c in all_cos]
            fig.add_trace(go.Bar(
                x=names, y=vals,
                marker_color=colors,
                marker_opacity=0.85,
                text=[f"{v:.1f}x" if v is not None else "N/A" for v in vals],
                textposition='outside',
                textfont=dict(size=10, color=TEXT),
                showlegend=False,
            ), row=1, col=col_idx)

            # 同業中位數線
            med = peer_val.get('medians', {}).get(metric)
            if med:
                fig.add_hline(y=med, line=dict(color=COLOR_TEAL, width=1.5, dash='dash'),
                              annotation_text=f" 中位 {med:.1f}x",
                              annotation_font=dict(color=COLOR_TEAL, size=10),
                              row=1, col=col_idx)

        fig.update_layout(
            title={"text": "同業估值倍數比較（黃色=標的公司，藍色=同業）",
                   "font": {"color": TEXT, "size": 14}, "x": 0.02},
            paper_bgcolor=BG, plot_bgcolor=CARD,
            font={"color": TEXT}, height=380,
            margin=dict(t=60, b=50, l=40, r=20),
        )
        fig.update_xaxes(showgrid=False, tickfont={"color": TEXT}, tickangle=-30)
        fig.update_yaxes(showgrid=True, gridcolor=GRID, tickfont={"color": TEXT})
        for ann in fig.layout.annotations:
            ann.font.color = TEXT
        return fig

    # ──────────────────────────────────────────
    # 7. 估值指標雷達圖
    # ──────────────────────────────────────────
    def plot_valuation_radar(self, synthesis: dict, peer_val: dict) -> go.Figure:
        """5維雷達：本益比、淨值比、股息率、成長性、安全邊際"""
        if not synthesis.get('available'):
            return _empty_fig("估值雷達圖 (資料不足)")

        subject = peer_val.get('subject', {}) if peer_val.get('available') else {}
        medians = peer_val.get('medians', {}) if peer_val.get('available') else {}

        def _score_pe(pe, med_pe):
            if pe is None or med_pe is None or med_pe == 0:
                return 50
            ratio = pe / med_pe
            return max(10, min(90, 100 - ratio * 50))

        def _score_pb(pb, med_pb):
            if pb is None or med_pb is None or med_pb == 0:
                return 50
            ratio = pb / med_pb
            return max(10, min(90, 100 - ratio * 40))

        def _score_ps(ps, med_ps):
            if ps is None or med_ps is None or med_ps == 0:
                return 50
            ratio = ps / med_ps
            return max(10, min(90, 100 - ratio * 40))

        def _score_mos(mos):
            if mos is None:
                return 50
            return max(10, min(90, 50 + mos * 1.5))

        dims   = ['P/E 合理性', 'P/B 合理性', 'P/S 合理性', '安全邊際', '估值確定性']
        scores = [
            _score_pe(subject.get('pe'), medians.get('pe')),
            _score_pb(subject.get('pb'), medians.get('pb')),
            _score_ps(subject.get('ps'), medians.get('ps')),
            _score_mos(synthesis.get('mos')),
            max(10, min(90, 60 - len(synthesis.get('estimates', [])) * 3)),  # 方法一致性
        ]
        scores_closed = scores + [scores[0]]
        dims_closed   = dims + [dims[0]]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=scores_closed, theta=dims_closed,
            fill='toself',
            fillcolor='rgba(74,158,255,0.15)',
            line=dict(color=COLOR_BLUE, width=2),
            name='目標公司',
        ))
        # 中性基準（50分）
        fig.add_trace(go.Scatterpolar(
            r=[50] * len(dims_closed), theta=dims_closed,
            line=dict(color=GRID, width=1, dash='dot'),
            name='中性基準',
            fill=None,
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100],
                                gridcolor=GRID, linecolor=GRID,
                                tickfont=dict(color=TEXT)),
                angularaxis=dict(gridcolor=GRID, linecolor=GRID,
                                 tickfont=dict(color=TEXT)),
                bgcolor=CARD,
            ),
            title={"text": "估值合理性五維雷達",
                   "font": {"color": TEXT, "size": 15}, "x": 0.02},
            paper_bgcolor=BG, font={"color": TEXT},
            height=380,
            margin=dict(t=55, b=20, l=40, r=40),
            legend=dict(bgcolor=CARD, bordercolor=GRID, borderwidth=1,
                        font=dict(color=TEXT)),
        )
        return fig

    # ──────────────────────────────────────────
    # 8. 各方法估值彙整瀑布
    # ──────────────────────────────────────────
    def plot_estimates_bar(self, synthesis: dict, current_price: float) -> go.Figure:
        if not synthesis.get('available'):
            return _empty_fig("各方法估值彙整 (資料不足)")

        estimates = synthesis.get('estimates', [])
        if not estimates:
            return _empty_fig("各方法估值彙整 (無有效估值)")

        methods = [e['method'] for e in estimates]
        ivs     = [e['iv'] for e in estimates]
        weights = [e['weight'] for e in estimates]

        # 顏色：相對現價高的綠（低估），低的紅（高估）
        bar_colors = [COLOR_GREEN if iv > current_price else COLOR_RED for iv in ivs]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=methods, y=ivs,
            marker_color=bar_colors, marker_opacity=0.8,
            text=[f"{v:,.1f}\n({w*100:.0f}%)" for v, w in zip(ivs, weights)],
            textposition='outside',
            textfont=dict(color=TEXT, size=11),
            name='內在價值估算',
        ))

        iv_w = synthesis.get('iv_weighted')
        if iv_w:
            fig.add_hline(y=iv_w,
                          line=dict(color=COLOR_BLUE, width=2, dash='dash'),
                          annotation_text=f"  加權均值 {iv_w:,.1f}",
                          annotation_font=dict(color=COLOR_BLUE, size=12))

        if current_price:
            fig.add_hline(y=current_price,
                          line=dict(color=COLOR_YELLOW, width=2),
                          annotation_text=f"  目前股價 {current_price:,.1f}",
                          annotation_font=dict(color=COLOR_YELLOW, size=12))

        fig.update_layout(
            title={"text": "各估值方法彙整比較（括號內為加權比重）",
                   "font": {"color": TEXT, "size": 14}, "x": 0.02},
            paper_bgcolor=BG, plot_bgcolor=CARD,
            font={"color": TEXT}, height=380,
            margin=dict(t=55, b=60, l=60, r=20),
            xaxis=dict(showgrid=False, tickfont={"color": TEXT}, tickangle=-20),
            yaxis=dict(showgrid=True, gridcolor=GRID, tickfont={"color": TEXT}),
            showlegend=False,
        )
        return fig


def _empty_fig(title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text="資料不足，無法顯示圖表", x=0.5, y=0.5,
                       xref="paper", yref="paper",
                       showarrow=False, font={"color": GRID, "size": 16})
    fig.update_layout(
        title={"text": title, "font": {"color": TEXT, "size": 14}, "x": 0.02},
        paper_bgcolor=BG, plot_bgcolor=CARD,
        height=300, margin=dict(t=50, b=20, l=20, r=20)
    )
    return fig
