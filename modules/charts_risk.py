"""
Feature 4: Risk Signal Detection - Chart Builder
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

BG = "#0e1117"
CARD = "#1a1d2e"
TEXT = "#e0e0e0"
GRID = "#2a2d3e"

COLOR_GREEN = "#00c896"
COLOR_YELLOW = "#f0c040"
COLOR_ORANGE = "#ff8c00"
COLOR_RED = "#ff4444"
COLOR_BLUE = "#4a9eff"
COLOR_PURPLE = "#9b59b6"


def _risk_color(score: float) -> str:
    if score < 25:
        return COLOR_GREEN
    elif score < 50:
        return COLOR_YELLOW
    elif score < 75:
        return COLOR_ORANGE
    else:
        return COLOR_RED


def _risk_label(score: float) -> str:
    if score < 25:
        return "無明顯風險"
    elif score < 50:
        return "低風險"
    elif score < 75:
        return "中等風險"
    else:
        return "高風險"


class RiskChartBuilder:

    def plot_overall_gauge(self, overall: dict) -> go.Figure:
        score = overall.get("score", 0)
        label = overall.get("level", "")
        color = _risk_color(score)

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            title={"text": f"整體風險評分<br><span style='font-size:16px;color:{color}'>{label}</span>",
                   "font": {"color": TEXT, "size": 17}},
            number={"font": {"color": color, "size": 48}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": GRID,
                         "tickfont": {"color": TEXT}},
                "bar": {"color": color, "thickness": 0.3},
                "bgcolor": CARD,
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 25],  "color": "#003322"},
                    {"range": [25, 50], "color": "#332800"},
                    {"range": [50, 75], "color": "#331400"},
                    {"range": [75, 100],"color": "#330000"},
                ],
                "threshold": {
                    "line": {"color": "white", "width": 3},
                    "thickness": 0.75,
                    "value": score
                }
            }
        ))
        fig.update_layout(
            paper_bgcolor=BG, plot_bgcolor=BG,
            font={"color": TEXT},
            height=300,
            margin=dict(t=60, b=20, l=30, r=30)
        )
        return fig

    def plot_signal_heatmap(self, signals: dict) -> go.Figure:
        """6-signal color-coded horizontal bar heatmap."""
        # signal keys as stored in feature4_risk.py
        signal_keys = ["ar_revenue", "inventory", "cashflow_quality",
                       "debt_structure", "special_items", "insider_activity"]
        signal_names = {
            "ar_revenue":       "應收帳款異常",
            "inventory":        "存貨風險",
            "cashflow_quality": "現金流品質",
            "debt_structure":   "債務壓力",
            "special_items":    "特殊項目",
            "insider_activity": "內部人持股",
        }

        labels, scores, colors, summaries = [], [], [], []
        for k in signal_keys:
            sig = signals.get(k, {})
            s = sig.get("risk_score", 0) or 0
            flags = sig.get("flags", [])
            summary = flags[0] if flags else "N/A"
            # truncate long summaries
            if len(summary) > 30:
                summary = summary[:30] + "…"
            labels.append(signal_names.get(k, k))
            scores.append(s)
            colors.append(_risk_color(s))
            summaries.append(summary)

        fig = go.Figure()
        for lbl, score, color, summary in zip(labels, scores, colors, summaries):
            fig.add_trace(go.Bar(
                x=[score],
                y=[lbl],
                orientation="h",
                marker_color=color,
                marker_opacity=0.85,
                text=f"  {score:.0f}  {summary}",
                textposition="inside",
                textfont={"color": "white", "size": 11},
                hovertemplate=f"<b>{lbl}</b><br>風險分數: {score:.0f}<br>{summary}<extra></extra>",
                showlegend=False,
            ))

        fig.update_layout(
            title={"text": "風險信號總覽", "font": {"color": TEXT, "size": 16}, "x": 0.02},
            paper_bgcolor=BG, plot_bgcolor=CARD,
            font={"color": TEXT},
            height=320,
            margin=dict(t=50, b=20, l=10, r=10),
            xaxis=dict(range=[0, 100], showgrid=False, title="風險分數 (0-100)",
                       tickfont={"color": TEXT}, title_font={"color": TEXT}),
            yaxis=dict(showgrid=False, tickfont={"color": TEXT}),
        )
        for x0, x1, color in [(0, 25, "rgba(0,200,150,0.05)"),
                               (25, 50, "rgba(240,192,64,0.05)"),
                               (50, 75, "rgba(255,140,0,0.05)"),
                               (75, 100, "rgba(255,68,68,0.05)")]:
            fig.add_vrect(x0=x0, x1=x1, fillcolor=color, layer="below", line_width=0)
        return fig

    def plot_ar_revenue(self, ar_data: dict, year_labels: list) -> go.Figure:
        """AR growth vs Revenue growth trend."""
        details = ar_data.get("details", {})
        ar_growth  = details.get("ar_growth", []) or []
        rev_growth = details.get("rev_growth", []) or []
        dso_list   = details.get("dso", []) or []

        # filter out None
        def clean(lst):
            return [v for v in lst if v is not None]

        if not clean(ar_growth) and not clean(rev_growth):
            return _empty_fig("應收帳款 vs 營收成長率 (資料不足)")

        fig = make_subplots(rows=2, cols=1,
                            subplot_titles=("應收帳款 vs 營收 YoY成長率 (%)", "應收帳款周轉天數 (DSO)"),
                            vertical_spacing=0.18,
                            row_heights=[0.6, 0.4])

        if ar_growth:
            yr = year_labels[-len(ar_growth):] if year_labels else list(range(len(ar_growth)))
            fig.add_trace(go.Scatter(x=yr, y=ar_growth,
                                     name="AR成長率", line=dict(color=COLOR_RED, width=2),
                                     mode="lines+markers"), row=1, col=1)
        if rev_growth:
            yr = year_labels[-len(rev_growth):] if year_labels else list(range(len(rev_growth)))
            fig.add_trace(go.Scatter(x=yr, y=rev_growth,
                                     name="營收成長率", line=dict(color=COLOR_BLUE, width=2),
                                     mode="lines+markers"), row=1, col=1)

        if dso_list:
            valid_dso = [v for v in dso_list if v is not None]
            if valid_dso:
                yr = year_labels[-len(dso_list):] if year_labels else list(range(len(dso_list)))
                fig.add_trace(go.Bar(x=yr, y=dso_list, name="DSO(天)",
                                     marker_color=COLOR_ORANGE, opacity=0.7), row=2, col=1)

        _apply_dark(fig, height=420)
        return fig

    def plot_inventory(self, inv_data: dict, year_labels: list) -> go.Figure:
        """Inventory turnover and DIO trend."""
        details  = inv_data.get("details", {})
        turnover = details.get("turnover", []) or []
        dio_list = details.get("dio", []) or []

        if not any(v is not None for v in turnover) and not any(v is not None for v in dio_list):
            return _empty_fig("存貨周轉率趨勢 (資料不足)")

        fig = make_subplots(rows=2, cols=1,
                            subplot_titles=("存貨周轉率 (次/年)", "存貨周轉天數 (DIO)"),
                            vertical_spacing=0.18,
                            row_heights=[0.5, 0.5])

        if turnover:
            yr = year_labels[-len(turnover):] if year_labels else list(range(len(turnover)))
            fig.add_trace(go.Scatter(x=yr, y=turnover, name="周轉率",
                                     line=dict(color=COLOR_GREEN, width=2),
                                     mode="lines+markers"), row=1, col=1)

        if dio_list:
            yr = year_labels[-len(dio_list):] if year_labels else list(range(len(dio_list)))
            fig.add_trace(go.Bar(x=yr, y=dio_list, name="DIO(天)",
                                 marker_color=COLOR_PURPLE, opacity=0.75), row=2, col=1)

        _apply_dark(fig, height=400)
        return fig

    def plot_cfo_vs_ni(self, cfo_data: dict, year_labels: list) -> go.Figure:
        """CFO vs Net Income grouped bar chart."""
        details  = cfo_data.get("details", {})
        cfo_list = details.get("cfo", []) or []
        ni_list  = details.get("net_income", []) or []

        if not any(v is not None for v in cfo_list) and not any(v is not None for v in ni_list):
            return _empty_fig("營業現金流 vs 淨利 (資料不足)")

        n = max(len(cfo_list), len(ni_list), 1)
        yr = year_labels[-n:] if year_labels else list(range(n))

        fig = go.Figure()
        if ni_list:
            fig.add_trace(go.Bar(name="淨利 (NI)",
                                 x=yr[-len(ni_list):],
                                 y=[v / 1e8 if v is not None else None for v in ni_list],
                                 marker_color=COLOR_BLUE, opacity=0.8))
        if cfo_list:
            fig.add_trace(go.Bar(name="營業現金流 (CFO)",
                                 x=yr[-len(cfo_list):],
                                 y=[v / 1e8 if v is not None else None for v in cfo_list],
                                 marker_color=COLOR_GREEN, opacity=0.8))

        fig.update_layout(
            title={"text": "營業現金流 vs 淨利 (億元)", "font": {"color": TEXT, "size": 15}, "x": 0.02},
            barmode="group",
            paper_bgcolor=BG, plot_bgcolor=CARD,
            font={"color": TEXT}, height=350,
            margin=dict(t=50, b=40, l=60, r=20),
            legend=dict(bgcolor=CARD, bordercolor=GRID, borderwidth=1),
            xaxis=dict(showgrid=False, tickfont={"color": TEXT}),
            yaxis=dict(showgrid=True, gridcolor=GRID, tickfont={"color": TEXT},
                       title="億元", title_font={"color": TEXT}),
        )
        return fig

    def plot_debt_trend(self, debt_data: dict, year_labels: list) -> go.Figure:
        """Debt ratio and current ratio trend."""
        details     = debt_data.get("details", {})
        debt_ratios = details.get("debt_ratio", []) or []
        cur_ratios  = details.get("current_ratio", []) or []

        if not any(v is not None for v in debt_ratios) and not any(v is not None for v in cur_ratios):
            return _empty_fig("債務趨勢 (資料不足)")

        fig = make_subplots(rows=2, cols=1,
                            subplot_titles=("負債比率 (%)", "流動比率"),
                            vertical_spacing=0.18,
                            row_heights=[0.5, 0.5])

        if debt_ratios:
            yr = year_labels[-len(debt_ratios):] if year_labels else list(range(len(debt_ratios)))
            fig.add_trace(go.Scatter(
                x=yr, y=debt_ratios,
                name="負債比率", line=dict(color=COLOR_RED, width=2),
                mode="lines+markers+text",
                text=[f"{v:.1f}%" if v is not None else "" for v in debt_ratios],
                textposition="top center", textfont={"color": TEXT, "size": 10}),
                row=1, col=1)
            fig.add_hline(y=60, line_dash="dash", line_color=COLOR_ORANGE,
                          annotation_text="警戒線 60%",
                          annotation_font_color=COLOR_ORANGE, row=1, col=1)

        if cur_ratios:
            yr = year_labels[-len(cur_ratios):] if year_labels else list(range(len(cur_ratios)))
            fig.add_trace(go.Scatter(
                x=yr, y=cur_ratios,
                name="流動比率", line=dict(color=COLOR_BLUE, width=2),
                mode="lines+markers"), row=2, col=1)
            fig.add_hline(y=1.0, line_dash="dash", line_color=COLOR_YELLOW,
                          annotation_text="警戒線 1.0x",
                          annotation_font_color=COLOR_YELLOW, row=2, col=1)

        _apply_dark(fig, height=420)
        return fig

    def plot_m_f_score(self, m_score: dict, f_score: dict) -> go.Figure:
        """Beneish M-Score and Piotroski F-Score side-by-side indicators."""
        fig = make_subplots(rows=1, cols=2,
                            subplot_titles=("Beneish M-Score (財報操縱偵測)",
                                            "Piotroski F-Score (財務強度)"),
                            specs=[[{"type": "indicator"}, {"type": "indicator"}]])

        # ── M-Score ──
        m_val = m_score.get("score")   # float, e.g. -2.1
        if m_val is not None:
            m_color = COLOR_RED if m_val > -1.78 else COLOR_GREEN
            warn = "⚠️ 警示" if m_val > -1.78 else "✅ 正常"
            fig.add_trace(go.Indicator(
                mode="number",
                value=round(m_val, 2),
                title={"text": f"M = {m_val:.2f}<br><span style='font-size:12px;color:{m_color}'>{warn}</span>",
                       "font": {"color": m_color, "size": 14}},
                number={"font": {"color": m_color, "size": 40}, "valueformat": ".2f"},
            ), row=1, col=1)
        else:
            fig.add_trace(go.Indicator(
                mode="number", value=0,
                title={"text": "M-Score<br>資料不足", "font": {"color": TEXT}},
                number={"font": {"color": GRID}}
            ), row=1, col=1)

        # ── F-Score ──
        f_val = f_score.get("score")   # int 0-9
        if f_val is not None:
            if f_val >= 7:
                f_color, f_label = COLOR_GREEN, "強健"
            elif f_val >= 4:
                f_color, f_label = COLOR_YELLOW, "普通"
            else:
                f_color, f_label = COLOR_RED, "偏弱"

            fig.add_trace(go.Indicator(
                mode="number",
                value=f_val,
                title={"text": f"F-Score (滿分9)<br><span style='font-size:12px;color:{f_color}'>{f_label}</span>",
                       "font": {"color": f_color, "size": 14}},
                number={"font": {"color": f_color, "size": 48},
                        "suffix": " / 9"},
            ), row=1, col=2)
        else:
            fig.add_trace(go.Indicator(
                mode="number", value=0,
                title={"text": "F-Score<br>資料不足", "font": {"color": TEXT}},
                number={"font": {"color": GRID}}
            ), row=1, col=2)

        fig.update_layout(
            paper_bgcolor=BG, plot_bgcolor=BG,
            font={"color": TEXT}, height=260,
            margin=dict(t=60, b=20, l=20, r=20),
        )
        return fig

    def plot_insider_activity(self, insider_data: dict, year_labels: list) -> go.Figure:
        """Insider / institutional activity chart."""
        dtype = insider_data.get("type", "")
        is_tw = dtype.startswith("TW")
        details = insider_data.get("details", {})

        if is_tw:
            # dates / ratio from details
            dates = details.get("dates", [])
            ratio = details.get("ratio", [])
            if not ratio:
                return _empty_fig("外資持股比率 (資料不足)")

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates if dates else list(range(len(ratio))),
                y=ratio,
                mode="lines+markers",
                line=dict(color=COLOR_BLUE, width=2),
                fill="tozeroy",
                fillcolor="rgba(74,158,255,0.15)",
                name="外資持股%"
            ))
            ratio_first = details.get("ratio_first", 0)
            ratio_last  = details.get("ratio_last", 0)
            fig.update_layout(
                title={"text": f"外資持股比率趨勢 (%) — 目前 {ratio_last:.1f}%",
                       "font": {"color": TEXT, "size": 14}, "x": 0.02},
                paper_bgcolor=BG, plot_bgcolor=CARD,
                font={"color": TEXT}, height=300,
                margin=dict(t=50, b=40, l=60, r=20),
                xaxis=dict(showgrid=False, tickfont={"color": TEXT}),
                yaxis=dict(showgrid=True, gridcolor=GRID, tickfont={"color": TEXT},
                           title="%", title_font={"color": TEXT})
            )
            return fig
        else:
            buy_shares  = details.get("buy_shares", 0)
            sell_shares = details.get("sell_shares", 0)
            if buy_shares == 0 and sell_shares == 0:
                return _empty_fig("內部人交易 (資料不足)")

            fig = go.Figure(go.Bar(
                x=["買入(股)", "賣出(股)"],
                y=[buy_shares, sell_shares],
                marker_color=[COLOR_GREEN, COLOR_RED],
                text=[f"{buy_shares:,}", f"{sell_shares:,}"],
                textposition="auto",
                textfont={"color": "white"}
            ))
            fig.update_layout(
                title={"text": "近期內部人交易股數 (近6個月)",
                       "font": {"color": TEXT, "size": 14}, "x": 0.02},
                paper_bgcolor=BG, plot_bgcolor=CARD,
                font={"color": TEXT}, height=300,
                margin=dict(t=50, b=40, l=60, r=20),
                xaxis=dict(showgrid=False, tickfont={"color": TEXT}),
                yaxis=dict(showgrid=True, gridcolor=GRID, tickfont={"color": TEXT},
                           title="股數", title_font={"color": TEXT})
            )
            return fig

    def plot_altman_z(self, debt_data: dict) -> go.Figure:
        """Altman Z-Score gauge."""
        details = debt_data.get("details", {})
        z = details.get("z_score")
        if z is None:
            return _empty_fig("Altman Z-Score (資料不足)")

        if z > 2.99:
            color, label = COLOR_GREEN, "安全區"
        elif z > 1.81:
            color, label = COLOR_YELLOW, "灰色地帶"
        else:
            color, label = COLOR_RED, "困境區"

        z_display = min(max(z, 0), 6)

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=z_display,
            title={"text": f"Altman Z-Score<br><span style='font-size:14px;color:{color}'>{label}</span>",
                   "font": {"color": TEXT, "size": 14}},
            number={"font": {"color": color, "size": 38}, "valueformat": ".2f"},
            gauge={
                "axis": {"range": [0, 6],
                         "tickvals": [0, 1.81, 2.99, 6],
                         "ticktext": ["0", "1.81", "2.99", "6"],
                         "tickfont": {"color": TEXT}},
                "bar": {"color": color, "thickness": 0.3},
                "bgcolor": CARD, "borderwidth": 0,
                "steps": [
                    {"range": [0, 1.81],    "color": "#330000"},
                    {"range": [1.81, 2.99], "color": "#332800"},
                    {"range": [2.99, 6],    "color": "#003322"},
                ],
            }
        ))
        fig.update_layout(
            paper_bgcolor=BG, plot_bgcolor=BG,
            font={"color": TEXT}, height=280,
            margin=dict(t=60, b=20, l=30, r=30)
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


def _apply_dark(fig: go.Figure, height: int = 400):
    fig.update_layout(
        paper_bgcolor=BG, plot_bgcolor=CARD,
        font={"color": TEXT}, height=height,
        margin=dict(t=50, b=40, l=60, r=20),
        legend=dict(bgcolor=CARD, bordercolor=GRID, borderwidth=1),
    )
    fig.update_xaxes(showgrid=False, tickfont={"color": TEXT})
    fig.update_yaxes(showgrid=True, gridcolor=GRID, tickfont={"color": TEXT})
    for ann in fig.layout.annotations:
        ann.font.color = TEXT
