"""
產業分析圖表模組
- 競爭定位矩陣（毛利率 vs 成長）
- 同業市值/營收比較
- SWOT 視覺化
- 競爭地位雷達圖
- 市場份額估算
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Dict, List, Optional

BG     = "#0e1117"
GRID   = "#1e2530"
TEXT   = "#dfe6e9"
FONT   = "Microsoft JhengHei, Arial"
SELF_C = "#ffa502"          # 主股：橘金
PEER_C = "#5352ed"          # 同業：藍紫
GREEN  = "#00b09b"
RED    = "#ff4757"
BLUE   = "#5352ed"
YELLOW = "#ffd700"

BASE = dict(
    paper_bgcolor=BG, plot_bgcolor=BG,
    font=dict(color=TEXT, family=FONT, size=11),
    margin=dict(l=10, r=10, t=45, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)


class IndustryChartBuilder:

    # ═══════════════════════════════════════════
    # 競爭定位矩陣：毛利率 vs 成長率（泡泡圖）
    # ═══════════════════════════════════════════
    def plot_competitive_matrix(self, company_data: Dict,
                                peer_data: List[Dict]) -> go.Figure:
        """
        X軸：Revenue Growth（成長性）
        Y軸：Gross Margin（獲利性）
        泡泡大小：市值
        """
        fig = go.Figure()

        all_items = []

        # 主股
        cd = company_data
        all_items.append({
            'name':    cd['name'][:10],
            'growth':  cd.get('revenue_cagr'),
            'margin':  cd.get('gross_margin'),
            'cap':     cd.get('market_cap'),
            'is_self': True,
        })

        # 同業
        for p in peer_data:
            rg = p.get('revenue_growth')
            all_items.append({
                'name':    p['name'][:10],
                'growth':  rg * 100 if rg else None,
                'margin':  p.get('gross_margin'),
                'cap':     p.get('market_cap'),
                'is_self': False,
            })

        # 泡泡大小縮放
        caps = [i['cap'] for i in all_items if i.get('cap')]
        max_cap = max(caps) if caps else 1
        def bubble_size(cap):
            if not cap: return 20
            return max(15, min(70, cap / max_cap * 70))

        for item in all_items:
            x = item.get('growth')
            y = item.get('margin')
            if x is None or y is None:
                continue
            color = SELF_C if item['is_self'] else PEER_C
            size  = bubble_size(item.get('cap'))

            fig.add_trace(go.Scatter(
                x=[x], y=[y],
                mode='markers+text',
                name=item['name'],
                text=[item['name']],
                textposition='top center',
                textfont=dict(size=10, color=color),
                marker=dict(
                    size=size,
                    color=color,
                    opacity=0.85,
                    line=dict(color='white', width=1.5),
                ),
                hovertemplate=(
                    f"<b>{item['name']}</b><br>"
                    f"成長率: %{{x:.1f}}%<br>"
                    f"毛利率: %{{y:.1f}}%<br>"
                    f"市值: {_fmt_cap(item.get('cap'))}<extra></extra>"
                ),
            ))

        # 四象限線（中位數）
        valid_x = [i['growth'] for i in all_items if i.get('growth') is not None]
        valid_y = [i['margin'] for i in all_items if i.get('margin') is not None]
        mid_x = np.median(valid_x) if valid_x else 10
        mid_y = np.median(valid_y) if valid_y else 30

        fig.add_vline(x=mid_x, line=dict(color='#444', width=1, dash='dot'))
        fig.add_hline(y=mid_y, line=dict(color='#444', width=1, dash='dot'))

        # 象限標籤
        x_range = [min(valid_x)-5, max(valid_x)+5] if valid_x else [-10, 50]
        y_range = [min(valid_y)-5, max(valid_y)+5] if valid_y else [0, 70]

        quadrant_labels = [
            (x_range[1]*0.85, y_range[1]*0.95, "🌟 明星", GREEN),
            (x_range[0]*0.5,  y_range[1]*0.95, "💰 金牛", YELLOW),
            (x_range[1]*0.85, y_range[0]*0.5,  "❓ 問題", RED),
            (x_range[0]*0.5,  y_range[0]*0.5,  "🐕 瘦狗", "#888"),
        ]
        for qx, qy, label, color in quadrant_labels:
            fig.add_annotation(
                x=qx, y=qy, text=label,
                showarrow=False,
                font=dict(size=12, color=color),
                opacity=0.5,
            )

        layout = BASE.copy()
        layout.update(
            title=dict(text="競爭定位矩陣（成長性 vs 獲利性）", font=dict(size=14)),
            xaxis=dict(title="營收成長率 (%)", gridcolor=GRID, zeroline=True,
                       zerolinecolor='#333'),
            yaxis=dict(title="毛利率 (%)", gridcolor=GRID, zeroline=False),
            showlegend=False,
            height=400,
        )
        fig.update_layout(**layout)
        return fig

    # ═══════════════════════════════════════════
    # 同業財務比較（分組橫條）
    # ═══════════════════════════════════════════
    def plot_peer_comparison_bars(self, company_data: Dict,
                                   peer_data: List[Dict]) -> go.Figure:
        all_items = [{'name': company_data['name'][:10], 'is_self': True, **company_data}]
        for p in peer_data:
            all_items.append({'is_self': False, **p})

        names = [i['name'] for i in all_items]

        metrics = [
            ('gross_margin', '毛利率 (%)',  GREEN),
            ('net_margin',   '淨利率 (%)',  BLUE),
            ('roe',          'ROE (%)',     YELLOW),
        ]

        fig = make_subplots(
            rows=1, cols=3,
            subplot_titles=[m[1] for m in metrics],
        )

        for col_idx, (key, label, color) in enumerate(metrics, start=1):
            vals = [i.get(key) for i in all_items]
            bar_colors = [SELF_C if i['is_self'] else color for i in all_items]
            text_vals  = [f"{v:.1f}%" if v is not None else "N/A" for v in vals]

            fig.add_trace(go.Bar(
                x=names, y=vals,
                name=label,
                marker_color=bar_colors,
                text=text_vals,
                textposition='outside',
                textfont=dict(size=9),
                showlegend=False,
                hovertemplate=f"{label}: %{{y:.1f}}%<extra></extra>",
            ), row=1, col=col_idx)

        layout = BASE.copy()
        layout.update(
            title=dict(text="同業財務指標比較", font=dict(size=14)),
            height=340,
        )
        for i in range(1, 4):
            fig.update_xaxes(showgrid=False, row=1, col=i, tickfont=dict(size=9))
            fig.update_yaxes(showgrid=True, gridcolor=GRID, row=1, col=i,
                             ticksuffix='%')
        fig.update_layout(**layout)
        return fig

    # ═══════════════════════════════════════════
    # 市場份額（水平條）
    # ═══════════════════════════════════════════
    def plot_market_share(self, share_data: List[Dict]) -> go.Figure:
        if not share_data:
            return None

        names  = [d['name'] for d in share_data]
        shares = [d.get('share_pct', 0) for d in share_data]
        colors = [SELF_C if d.get('is_self') else PEER_C for d in share_data]
        texts  = [f"{s:.1f}%" for s in shares]

        fig = go.Figure(go.Bar(
            x=shares,
            y=names,
            orientation='h',
            marker_color=colors,
            text=texts,
            textposition='outside',
            textfont=dict(size=11),
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        ))

        layout = BASE.copy()
        layout.update(
            title=dict(text="⚠️ 同業收入規模比較（估算，非實際市占）", font=dict(size=13)),
            xaxis=dict(title="相對收入比重 (%)", gridcolor=GRID),
            yaxis=dict(gridcolor=GRID),
            height=max(250, 60 * len(names)),
        )
        fig.update_layout(**layout)
        return fig

    # ═══════════════════════════════════════════
    # 競爭地位雷達圖
    # ═══════════════════════════════════════════
    def plot_positioning_radar(self, positioning: Dict, company_name: str) -> go.Figure:
        scores = positioning.get('scores', {})
        cats   = list(scores.keys())
        vals   = list(scores.values())

        if not cats:
            return go.Figure()

        cats_loop = cats + [cats[0]]
        vals_loop = vals + [vals[0]]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=vals_loop,
            theta=cats_loop,
            fill='toself',
            fillcolor=f"rgba(255,165,2,0.2)",
            line=dict(color=SELF_C, width=2.5),
            name=company_name[:12],
            marker=dict(size=8, color=SELF_C),
        ))

        # 同業均值（50分基準）
        base = [50] * len(cats_loop)
        fig.add_trace(go.Scatterpolar(
            r=base,
            theta=cats_loop,
            mode='lines',
            line=dict(color='#555', width=1.5, dash='dot'),
            name='同業均值基準',
        ))

        fig.update_layout(
            polar=dict(
                bgcolor=BG,
                radialaxis=dict(visible=True, range=[0, 100],
                                tickcolor=TEXT, gridcolor=GRID,
                                linecolor=GRID, color=TEXT, tickfont=dict(size=9)),
                angularaxis=dict(gridcolor=GRID, linecolor=GRID,
                                 color=TEXT, tickfont=dict(size=12)),
            ),
            paper_bgcolor=BG,
            font=dict(color=TEXT, family=FONT),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            title=dict(text=f"{company_name[:12]} 競爭地位五維評分", font=dict(size=14)),
            height=400,
            margin=dict(l=40, r=40, t=60, b=40),
        )
        return fig

    # ═══════════════════════════════════════════
    # SWOT 視覺化（四象限卡片）
    # ═══════════════════════════════════════════
    def build_swot_html(self, swot: Dict) -> str:
        """回傳 HTML 格式的 SWOT 四象限"""
        def make_list(items, icon):
            rows = ""
            for item in items:
                rows += f"<li style='margin:6px 0;line-height:1.6'>{icon} {item}</li>"
            return f"<ul style='padding-left:0;list-style:none;margin:0'>{rows}</ul>"

        quadrants = [
            ("S - 優勢", "Strengths", "#00b09b", "rgba(0,176,155,0.12)",
             swot.get('strengths', []), "✅"),
            ("W - 劣勢", "Weaknesses", "#ff4757", "rgba(255,71,87,0.12)",
             swot.get('weaknesses', []), "⚠️"),
            ("O - 機會", "Opportunities", "#5352ed", "rgba(83,82,237,0.12)",
             swot.get('opportunities', []), "🚀"),
            ("T - 威脅", "Threats", "#ffa502", "rgba(255,165,2,0.12)",
             swot.get('threats', []), "🔻"),
        ]

        html = """<div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;'>"""
        for title, _, color, bg, items, icon in quadrants:
            html += f"""
            <div style='background:{bg};border:1.5px solid {color};border-radius:10px;padding:16px'>
                <div style='font-size:1rem;font-weight:700;color:{color};
                            border-bottom:1px solid {color};padding-bottom:6px;margin-bottom:10px'>
                    {title}
                </div>
                {make_list(items, icon)}
            </div>"""
        html += "</div>"
        return html

    # ═══════════════════════════════════════════
    # 市場規模成長預測（簡單柱狀）
    # ═══════════════════════════════════════════
    def plot_market_size_bar(self, industry_info: Dict) -> go.Figure:
        now_str  = industry_info.get('market_size_now', '')
        fut_str  = industry_info.get('market_size_2028', '')
        cagr_str = industry_info.get('cagr', '')

        # 嘗試提取數字（簡單 parse USD xxxx 億/兆）
        import re
        def parse_usd(s):
            m = re.search(r'[\d,\.]+', s.replace(',', ''))
            if m:
                return float(m.group())
            return None

        now_val = parse_usd(now_str)
        fut_val = parse_usd(fut_str)

        if not now_val or not fut_val:
            return None

        unit = "兆" if "兆" in (now_str + fut_str) else "億"
        labels = ['現況（2024）', '預測（2028E）']
        values = [now_val, fut_val]
        colors = [BLUE, GREEN]
        texts  = [f"USD {now_val:.0f}{unit}", f"USD {fut_val:.0f}{unit}"]

        fig = go.Figure(go.Bar(
            x=labels, y=values,
            marker_color=colors,
            text=texts,
            textposition='outside',
            textfont=dict(size=13, color=TEXT),
            width=0.4,
        ))

        # CAGR 標注
        if cagr_str:
            fig.add_annotation(
                x=0.5, y=max(values) * 1.15,
                text=f"CAGR: {cagr_str}",
                showarrow=False,
                font=dict(size=14, color=YELLOW),
                xref='paper',
            )

        layout = BASE.copy()
        layout.update(
            title=dict(text=f"{industry_info.get('full_name','')} 市場規模預測", font=dict(size=14)),
            yaxis=dict(title=f"市場規模（USD {unit}）", gridcolor=GRID),
            xaxis=dict(showgrid=False),
            height=320,
            showlegend=False,
        )
        fig.update_layout(**layout)
        return fig

    # ═══════════════════════════════════════════
    # 同業市值比較（橫條）
    # ═══════════════════════════════════════════
    def plot_market_cap_comparison(self, company_data: Dict,
                                   peer_data: List[Dict]) -> go.Figure:
        items = [{'name': company_data['name'][:12],
                  'cap':  company_data.get('market_cap'), 'is_self': True}]
        for p in peer_data:
            items.append({'name': p['name'][:12], 'cap': p.get('market_cap'), 'is_self': False})
        items = sorted([i for i in items if i.get('cap')], key=lambda x: x['cap'], reverse=True)

        if not items:
            return go.Figure()   # 所有同業無市值資料時回傳空圖

        # 判斷是否為台股（市值為 TWD，單位: 億）
        max_cap = max(i['cap'] for i in items)
        is_tw_cap = max_cap > 1e10  # yfinance 台股 marketCap 以 TWD 報告，值通常 > 100億

        if is_tw_cap:
            caps  = [i['cap'] / 1e8 for i in items]  # TWD 億
            unit_lbl = "億台幣"
            fmt   = lambda c: f"{c:.0f}億"
            hover = "%{y}: %{x:.0f}億<extra></extra>"
            ax_title = "市值（億台幣）"
            title_str = "同業市值比較（億台幣）"
        else:
            caps  = [i['cap'] / 1e9 for i in items]  # USD Billion
            unit_lbl = "USD B"
            fmt   = lambda c: f"${c:.1f}B"
            hover = "%{y}: $%{x:.1f}B<extra></extra>"
            ax_title = "市值（十億美元）"
            title_str = "同業市值比較（USD Billion）"

        names  = [i['name'] for i in items]
        colors = [SELF_C if i['is_self'] else PEER_C for i in items]
        texts  = [fmt(c) for c in caps]

        fig = go.Figure(go.Bar(
            x=caps, y=names,
            orientation='h',
            marker_color=colors,
            text=texts,
            textposition='outside',
            textfont=dict(size=10),
            hovertemplate=hover,
        ))

        layout = BASE.copy()
        layout.update(
            title=dict(text=title_str, font=dict(size=13)),
            xaxis=dict(title=ax_title, gridcolor=GRID),
            yaxis=dict(gridcolor=GRID),
            height=max(280, 55 * len(items)),
            showlegend=False,
        )
        fig.update_layout(**layout)
        return fig


def _fmt_cap(v) -> str:
    if v is None: return "N/A"
    if v >= 1e12: return f"${v/1e12:.2f}T"
    if v >= 1e9:  return f"${v/1e9:.1f}B"
    if v >= 1e6:  return f"${v/1e6:.0f}M"
    return f"${v:.0f}"
