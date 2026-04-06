"""
圖表建構模組
使用 Plotly 產生互動式財務圖表
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional

# 配色主題
COLOR_POSITIVE = "#00b09b"
COLOR_NEGATIVE = "#ff4757"
COLOR_NEUTRAL   = "#5352ed"
COLOR_ACCENT    = "#ffa502"
COLOR_GRAY      = "#a4b0be"
COLORS_MULTI    = ["#00b09b", "#5352ed", "#ffa502", "#ff4757", "#747d8c"]

BG_COLOR  = "#0e1117"
GRID_COLOR = "#2d3436"
TEXT_COLOR = "#dfe6e9"

CHART_LAYOUT = dict(
    paper_bgcolor=BG_COLOR,
    plot_bgcolor=BG_COLOR,
    font=dict(color=TEXT_COLOR, family="Microsoft JhengHei, Arial"),
    xaxis=dict(gridcolor=GRID_COLOR, showgrid=True),
    yaxis=dict(gridcolor=GRID_COLOR, showgrid=True),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    height=320,
)


class ChartBuilder:

    # ──────────────────────────────────────────
    # 營收趨勢
    # ──────────────────────────────────────────
    def plot_revenue_trend(self, data: Dict) -> go.Figure:
        """
        data = {
            'years': ['2021', '2022', '2023'],
            'revenue': [1000, 1200, 1500],      # 單位：原始數值
            'unit': 'B',                         # 顯示單位
            'currency': 'NT$'
        }
        """
        years   = data.get('years', [])
        revenue = data.get('revenue', [])
        unit    = data.get('unit', '')
        currency = data.get('currency', '')

        # 計算年增率
        yoy = [None]
        for i in range(1, len(revenue)):
            if revenue[i-1] and revenue[i-1] != 0:
                yoy.append((revenue[i] - revenue[i-1]) / abs(revenue[i-1]) * 100)
            else:
                yoy.append(None)

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # 柱狀圖：營收
        bar_colors = [COLOR_POSITIVE if r >= 0 else COLOR_NEGATIVE for r in revenue]
        fig.add_trace(
            go.Bar(
                x=years, y=revenue,
                name=f"營收 ({currency}{unit})",
                marker_color=bar_colors,
                opacity=0.85,
                text=[f"{v:.1f}" for v in revenue],
                textposition='outside',
                textfont=dict(size=11),
            ),
            secondary_y=False,
        )

        # 折線圖：年增率
        valid_yoy = [(y, v) for y, v in zip(years, yoy) if v is not None]
        if valid_yoy:
            yx, yv = zip(*valid_yoy)
            line_colors = [COLOR_POSITIVE if v >= 0 else COLOR_NEGATIVE for v in yv]
            fig.add_trace(
                go.Scatter(
                    x=list(yx), y=list(yv),
                    name="年增率 (%)",
                    mode='lines+markers+text',
                    line=dict(color=COLOR_ACCENT, width=2.5),
                    marker=dict(size=8, color=line_colors),
                    text=[f"{v:+.1f}%" for v in yv],
                    textposition='top center',
                    textfont=dict(size=10, color=COLOR_ACCENT),
                ),
                secondary_y=True,
            )

        layout = CHART_LAYOUT.copy()
        layout['title'] = dict(text="年度營收趨勢", font=dict(size=14))
        fig.update_layout(**layout)
        fig.update_yaxes(title_text=f"營收 ({currency}{unit})", secondary_y=False, gridcolor=GRID_COLOR)
        fig.update_yaxes(title_text="年增率 (%)", secondary_y=True, gridcolor=GRID_COLOR)

        return fig

    # ──────────────────────────────────────────
    # 毛利率 / 淨利率 / 營業利益率趨勢
    # ──────────────────────────────────────────
    def plot_margin_trend(self, data: Dict) -> go.Figure:
        """
        data = {
            'years': ['2021', '2022', '2023'],
            'gross_margin': [50, 52, 55],
            'operating_margin': [30, 32, 35],
            'net_margin': [25, 26, 28],
        }
        """
        years = data.get('years', [])

        fig = go.Figure()

        margin_series = [
            ('gross_margin',     '毛利率',     COLOR_POSITIVE),
            ('operating_margin', '營業利益率', COLOR_ACCENT),
            ('net_margin',       '淨利率',     COLOR_NEUTRAL),
        ]

        for key, label, color in margin_series:
            values = data.get(key, [])
            if values and any(v is not None for v in values):
                fig.add_trace(go.Scatter(
                    x=years, y=values,
                    name=label,
                    mode='lines+markers+text',
                    line=dict(color=color, width=2.5),
                    marker=dict(size=8),
                    text=[f"{v:.1f}%" if v is not None else "" for v in values],
                    textposition='top center',
                    textfont=dict(size=10),
                    fill='tozeroy',
                    fillcolor=f"rgba({self._hex_to_rgb(color)}, 0.08)",
                ))

        layout = CHART_LAYOUT.copy()
        layout['title'] = dict(text="獲利率趨勢 (%)", font=dict(size=14))
        layout['yaxis'] = dict(gridcolor=GRID_COLOR, showgrid=True, ticksuffix='%')
        fig.update_layout(**layout)
        return fig

    # ──────────────────────────────────────────
    # 現金流量
    # ──────────────────────────────────────────
    def plot_cashflow(self, data: Dict) -> go.Figure:
        """
        data = {
            'years': ['2021', '2022', '2023'],
            'operating_cf': [800, 900, 1100],
            'investing_cf': [-400, -500, -600],
            'free_cf': [400, 400, 500],
            'unit': 'B', 'currency': 'NT$'
        }
        """
        years = data.get('years', [])
        unit = data.get('unit', '')
        currency = data.get('currency', '')

        fig = go.Figure()

        cf_series = [
            ('operating_cf', '營業現金流',   COLOR_POSITIVE),
            ('investing_cf', '投資現金流',   COLOR_NEGATIVE),
            ('free_cf',      '自由現金流',   COLOR_ACCENT),
        ]

        for key, label, color in cf_series:
            values = data.get(key, [])
            if values and any(v is not None for v in values):
                if key == 'free_cf':
                    fig.add_trace(go.Scatter(
                        x=years, y=values,
                        name=label,
                        mode='lines+markers',
                        line=dict(color=color, width=3, dash='dot'),
                        marker=dict(size=9),
                    ))
                else:
                    fig.add_trace(go.Bar(
                        x=years, y=values,
                        name=label,
                        marker_color=color,
                        opacity=0.8,
                    ))

        layout = CHART_LAYOUT.copy()
        layout['title'] = dict(text=f"現金流量分析 ({currency}{unit})", font=dict(size=14))
        layout['barmode'] = 'group'
        fig.update_layout(**layout)
        return fig

    # ──────────────────────────────────────────
    # 估值比較（同業橫向比較）
    # ──────────────────────────────────────────
    def plot_valuation_comparison(self, stock_valuation: Dict, peer_data: List[Dict]) -> go.Figure:
        """
        stock_valuation = {'name': '台積電', 'pe': 25, 'pb': 7, 'ps': 10}
        peer_data = [{'name': '聯電', 'pe': 15, 'pb': 2.5, 'ps': 3}, ...]
        """
        all_data = [stock_valuation] + (peer_data or [])

        # 只顯示有效數據
        all_data = [d for d in all_data if d.get('name')]

        if not all_data:
            return go.Figure()

        metrics = [
            ('pe',  'P/E 本益比'),
            ('pb',  'P/B 股價淨值比'),
            ('ps',  'P/S 市銷率'),
        ]

        fig = make_subplots(
            rows=1, cols=3,
            subplot_titles=[m[1] for m in metrics],
        )

        for col_idx, (metric_key, metric_label) in enumerate(metrics, start=1):
            names  = [d['name'] for d in all_data]
            values = [d.get(metric_key) for d in all_data]

            # 顏色：第一個（主股）用accent色，其他用gray
            colors = [COLOR_ACCENT if i == 0 else COLOR_GRAY for i in range(len(names))]

            valid = [(n, v, c) for n, v, c in zip(names, values, colors) if v is not None]
            if not valid:
                continue
            vn, vv, vc = zip(*valid)

            fig.add_trace(
                go.Bar(
                    x=list(vn), y=list(vv),
                    marker_color=list(vc),
                    text=[f"{v:.1f}x" for v in vv],
                    textposition='outside',
                    textfont=dict(size=10),
                    showlegend=False,
                    name=metric_label,
                ),
                row=1, col=col_idx,
            )

        layout = CHART_LAYOUT.copy()
        layout['title'] = dict(text="估值同業比較", font=dict(size=14))
        layout['height'] = 360
        fig.update_layout(**layout)
        return fig

    # ──────────────────────────────────────────
    # 財務健康雷達圖
    # ──────────────────────────────────────────
    def plot_radar_chart(self, radar_scores: Dict, company_name: str = "") -> go.Figure:
        """
        radar_scores = {
            '成長力': 80,
            '獲利力': 75,
            '現金流': 70,
            '財務健全': 85,
            '估值合理': 60,
        }
        """
        categories = list(radar_scores.keys())
        values     = list(radar_scores.values())

        # 雷達圖需要首尾相接
        categories_loop = categories + [categories[0]]
        values_loop     = values + [values[0]]

        fig = go.Figure()

        # 填充區域
        fig.add_trace(go.Scatterpolar(
            r=values_loop,
            theta=categories_loop,
            fill='toself',
            fillcolor=f"rgba({self._hex_to_rgb(COLOR_POSITIVE)}, 0.25)",
            line=dict(color=COLOR_POSITIVE, width=2.5),
            name=company_name or "財務健康評分",
            marker=dict(size=8, color=COLOR_POSITIVE),
        ))

        # 基準線（60分）
        base = [60] * len(categories_loop)
        fig.add_trace(go.Scatterpolar(
            r=base,
            theta=categories_loop,
            mode='lines',
            line=dict(color=COLOR_GRAY, width=1.5, dash='dot'),
            name='基準線 (60)',
            showlegend=True,
        ))

        fig.update_layout(
            polar=dict(
                bgcolor=BG_COLOR,
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    ticksuffix='分',
                    gridcolor=GRID_COLOR,
                    linecolor=GRID_COLOR,
                    color=TEXT_COLOR,
                    tickfont=dict(size=9),
                ),
                angularaxis=dict(
                    gridcolor=GRID_COLOR,
                    linecolor=GRID_COLOR,
                    color=TEXT_COLOR,
                    tickfont=dict(size=12),
                ),
            ),
            paper_bgcolor=BG_COLOR,
            font=dict(color=TEXT_COLOR, family="Microsoft JhengHei, Arial"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            title=dict(text=f"{company_name} 財務健康五維評分", font=dict(size=14)),
            height=420,
            margin=dict(l=40, r=40, t=60, b=40),
        )
        return fig

    # ──────────────────────────────────────────
    # 負債比 / 流動比率 儀表板
    # ──────────────────────────────────────────
    def plot_debt_gauge(self, debt_ratio: float, current_ratio: float) -> go.Figure:
        fig = make_subplots(
            rows=1, cols=2,
            specs=[[{"type": "indicator"}, {"type": "indicator"}]],
            subplot_titles=["負債比率", "流動比率"],
        )

        # 負債比：越低越好 (0~100%)
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=debt_ratio,
            number=dict(suffix="%", font=dict(size=28, color=TEXT_COLOR)),
            gauge=dict(
                axis=dict(range=[0, 100], tickcolor=TEXT_COLOR),
                bar=dict(color=COLOR_NEGATIVE if debt_ratio > 60 else
                                COLOR_ACCENT if debt_ratio > 40 else COLOR_POSITIVE),
                steps=[
                    dict(range=[0, 40],  color="rgba(0,176,155,0.15)"),
                    dict(range=[40, 60], color="rgba(255,165,2,0.15)"),
                    dict(range=[60, 100],color="rgba(255,71,87,0.15)"),
                ],
                threshold=dict(line=dict(color="white", width=2), thickness=0.75, value=60),
            ),
        ), row=1, col=1)

        # 流動比率：越高越好 (0~3+)
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=current_ratio,
            number=dict(suffix="x", font=dict(size=28, color=TEXT_COLOR)),
            gauge=dict(
                axis=dict(range=[0, 4], tickcolor=TEXT_COLOR),
                bar=dict(color=COLOR_POSITIVE if current_ratio >= 2 else
                                COLOR_ACCENT if current_ratio >= 1 else COLOR_NEGATIVE),
                steps=[
                    dict(range=[0, 1],  color="rgba(255,71,87,0.15)"),
                    dict(range=[1, 2],  color="rgba(255,165,2,0.15)"),
                    dict(range=[2, 4],  color="rgba(0,176,155,0.15)"),
                ],
                threshold=dict(line=dict(color="white", width=2), thickness=0.75, value=2),
            ),
        ), row=1, col=2)

        fig.update_layout(
            paper_bgcolor=BG_COLOR,
            font=dict(color=TEXT_COLOR, family="Microsoft JhengHei, Arial"),
            height=260,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        return fig

    # ──────────────────────────────────────────
    # 輔助函式
    # ──────────────────────────────────────────
    @staticmethod
    def _hex_to_rgb(hex_color: str) -> str:
        """#rrggbb → 'r, g, b' 字串（供 rgba() 使用）"""
        h = hex_color.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"{r}, {g}, {b}"
