"""
技術面圖表模組
- K線 + 布林通道 + 均線 + 成交量（主圖）
- RSI 子圖
- MACD 子圖
- KD 子圖
- 三大法人買賣超（台股）
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional

# ── 配色主題 ──
BG        = "#0e1117"
GRID      = "#1e2530"
TEXT      = "#dfe6e9"
FONT      = "Microsoft JhengHei, Arial"

UP_COLOR    = "#ef5350"   # 台灣：紅漲
DOWN_COLOR  = "#26a69a"   # 台灣：綠跌
UP_FILL     = "rgba(239,83,80,0.15)"
DOWN_FILL   = "rgba(38,166,154,0.15)"

MA_COLORS = {
    5:   "#ffd700",   # 金
    20:  "#00b0ff",   # 藍
    60:  "#ff6f00",   # 橘
    120: "#ab47bc",   # 紫
    240: "#ef5350",   # 紅
}

BB_COLOR  = "#5c6bc0"
RSI_COLOR = "#00e5ff"
MACD_COLOR= "#00b09b"
SIG_COLOR = "#ffa502"
HIST_POS  = "rgba(0,176,155,0.6)"
HIST_NEG  = "rgba(255,71,87,0.6)"
K_COLOR   = "#f48fb1"
D_COLOR   = "#80deea"

LAYOUT_BASE = dict(
    paper_bgcolor=BG,
    plot_bgcolor=BG,
    font=dict(color=TEXT, family=FONT, size=11),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h",
                yanchor="bottom", y=1.01, xanchor="left", x=0),
    hovermode="x unified",
)


class TechnicalChartBuilder:

    # ═══════════════════════════════════════════════════
    # 主圖：K線 + 布林 + 均線 + 成交量 + RSI + MACD + KD
    # ═══════════════════════════════════════════════════
    def plot_full_chart(self, hist: pd.DataFrame, ind: Dict,
                        sr: Dict, is_tw: bool = True) -> go.Figure:
        """四欄 subplot：[K+BB+MA] [Volume] [RSI] [MACD] [KD]"""

        rows    = 5
        heights = [0.44, 0.10, 0.15, 0.16, 0.15]

        fig = make_subplots(
            rows=rows, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.012,
            row_heights=heights,
            subplot_titles=("", "", "RSI(14)", "MACD(12,26,9)", "KD(9,3,3)"),
        )

        dates = hist.index

        # ── 1. K線（含 MA 與布林通道）──
        self._add_candlestick(fig, hist, is_tw, row=1)
        self._add_ma_lines(fig, dates, ind['ma'], row=1)
        self._add_bollinger(fig, dates, ind, row=1)
        self._add_sr_lines(fig, sr, row=1)

        # ── 2. 成交量 ──
        self._add_volume(fig, hist, is_tw, row=2)

        # ── 3. RSI ──
        self._add_rsi(fig, dates, ind['rsi'], row=3)

        # ── 4. MACD ──
        self._add_macd(fig, dates, ind, row=4)

        # ── 5. KD ──
        self._add_kd(fig, dates, ind, row=5)

        # ── 版面 ──
        layout = LAYOUT_BASE.copy()
        layout.update(
            height=820,
            title=dict(text="技術分析總覽", font=dict(size=15)),
            xaxis5=dict(
                rangeslider=dict(visible=False),
                type='category',
                showticklabels=True,
                gridcolor=GRID,
            ),
        )
        fig.update_layout(**layout)

        # 所有子圖 x/y 軸共同樣式
        for i in range(1, rows + 1):
            fig.update_xaxes(showgrid=True, gridcolor=GRID, row=i, col=1,
                             showticklabels=(i == rows),
                             rangeslider_visible=False,
                             type='category')
            fig.update_yaxes(showgrid=True, gridcolor=GRID, row=i, col=1,
                             side='right')

        return fig

    # ────────────────────────────────────
    # K線
    # ────────────────────────────────────
    def _add_candlestick(self, fig, hist, is_tw, row):
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close'],
            name="K線",
            increasing_line_color=UP_COLOR,
            decreasing_line_color=DOWN_COLOR,
            increasing_fillcolor=UP_COLOR,
            decreasing_fillcolor=DOWN_COLOR,
            showlegend=False,
            whiskerwidth=0.3,
        ), row=row, col=1)

    # ────────────────────────────────────
    # 均線
    # ────────────────────────────────────
    def _add_ma_lines(self, fig, dates, ma_dict: Dict, row):
        labels = {5: 'MA5', 20: 'MA20', 60: 'MA60', 120: 'MA120', 240: 'MA240'}
        for period, series in ma_dict.items():
            if series.dropna().empty:
                continue
            fig.add_trace(go.Scatter(
                x=dates,
                y=series,
                name=labels.get(period, f'MA{period}'),
                mode='lines',
                line=dict(color=MA_COLORS.get(period, '#ffffff'),
                          width=1.2 if period <= 20 else 1.8,
                          dash='dot' if period >= 120 else 'solid'),
                opacity=0.9,
                hovertemplate=f"{labels.get(period)}=%{{y:.2f}}<extra></extra>",
            ), row=row, col=1)

    # ────────────────────────────────────
    # 布林通道
    # ────────────────────────────────────
    def _add_bollinger(self, fig, dates, ind: Dict, row):
        bb_upper = ind['bb_upper']
        bb_lower = ind['bb_lower']
        bb_ma    = ind['bb_ma']

        # 上軌
        fig.add_trace(go.Scatter(
            x=dates, y=bb_upper,
            name='BB 上軌', mode='lines',
            line=dict(color=BB_COLOR, width=1, dash='dash'),
            opacity=0.7, showlegend=True,
            hovertemplate="BB上=%{y:.2f}<extra></extra>",
        ), row=row, col=1)

        # 下軌 + 填充區域
        fig.add_trace(go.Scatter(
            x=dates, y=bb_lower,
            name='BB 下軌', mode='lines',
            line=dict(color=BB_COLOR, width=1, dash='dash'),
            opacity=0.7,
            fill='tonexty',
            fillcolor='rgba(92,107,192,0.06)',
            hovertemplate="BB下=%{y:.2f}<extra></extra>",
        ), row=row, col=1)

    # ────────────────────────────────────
    # 支撐 / 阻力水平線
    # ────────────────────────────────────
    def _add_sr_lines(self, fig, sr: Dict, row):
        for i, r in enumerate(sr.get('resistances', [])[:3]):
            fig.add_hline(
                y=r, row=row, col=1,
                line=dict(color="rgba(255,71,87,0.55)", width=1, dash="dot"),
                annotation_text=f"壓 {r:,.1f}",
                annotation_position="right",
                annotation_font=dict(color="#ff4757", size=10),
            )
        for i, s in enumerate(sr.get('supports', [])[:3]):
            fig.add_hline(
                y=s, row=row, col=1,
                line=dict(color="rgba(0,176,155,0.55)", width=1, dash="dot"),
                annotation_text=f"撐 {s:,.1f}",
                annotation_position="right",
                annotation_font=dict(color="#00b09b", size=10),
            )

    # ────────────────────────────────────
    # 成交量
    # ────────────────────────────────────
    def _add_volume(self, fig, hist, is_tw, row):
        colors = [
            UP_COLOR if c >= o else DOWN_COLOR
            for c, o in zip(hist['Close'], hist['Open'])
        ]
        fig.add_trace(go.Bar(
            x=hist.index,
            y=hist['Volume'],
            name='成交量',
            marker_color=colors,
            opacity=0.75,
            showlegend=False,
            hovertemplate="量=%{y:,.0f}<extra></extra>",
        ), row=row, col=1)

        # 20日均量線
        vol_ma = hist['Volume'].rolling(20).mean()
        fig.add_trace(go.Scatter(
            x=hist.index, y=vol_ma,
            name='Vol MA20',
            mode='lines',
            line=dict(color='#ffeb3b', width=1.2),
            showlegend=False,
            hovertemplate="均量=%{y:,.0f}<extra></extra>",
        ), row=row, col=1)

    # ────────────────────────────────────
    # RSI
    # ────────────────────────────────────
    def _add_rsi(self, fig, dates, rsi: pd.Series, row):
        fig.add_trace(go.Scatter(
            x=dates, y=rsi,
            name='RSI', mode='lines',
            line=dict(color=RSI_COLOR, width=1.5),
            hovertemplate="RSI=%{y:.1f}<extra></extra>",
        ), row=row, col=1)

        # 超買/超賣線
        for level, color, label in [(70, '#ff4757', '超買'), (30, '#00b09b', '超賣'), (50, '#666', '')]:
            fig.add_hline(y=level, row=row, col=1,
                          line=dict(color=color, width=0.8, dash='dot'),
                          annotation_text=label,
                          annotation_position="right",
                          annotation_font=dict(size=9, color=color))

        # RSI 超買填色
        fig.add_trace(go.Scatter(
            x=dates, y=rsi.where(rsi >= 70),
            fill='tozeroy', fillcolor='rgba(255,71,87,0.12)',
            mode='none', showlegend=False, hoverinfo='skip',
        ), row=row, col=1)
        fig.add_trace(go.Scatter(
            x=dates, y=rsi.where(rsi <= 30),
            fill='tozeroy', fillcolor='rgba(0,176,155,0.15)',
            mode='none', showlegend=False, hoverinfo='skip',
        ), row=row, col=1)

        fig.update_yaxes(range=[0, 100], row=row, col=1)

    # ────────────────────────────────────
    # MACD
    # ────────────────────────────────────
    def _add_macd(self, fig, dates, ind: Dict, row):
        macd_h  = ind['macd_hist']
        hist_colors = [HIST_POS if v >= 0 else HIST_NEG for v in macd_h]

        fig.add_trace(go.Bar(
            x=dates, y=macd_h,
            name='MACD 柱', marker_color=hist_colors,
            opacity=0.7, showlegend=False,
            hovertemplate="Hist=%{y:.4f}<extra></extra>",
        ), row=row, col=1)

        fig.add_trace(go.Scatter(
            x=dates, y=ind['macd'],
            name='MACD', mode='lines',
            line=dict(color=MACD_COLOR, width=1.5),
            hovertemplate="MACD=%{y:.4f}<extra></extra>",
        ), row=row, col=1)

        fig.add_trace(go.Scatter(
            x=dates, y=ind['macd_sig'],
            name='Signal', mode='lines',
            line=dict(color=SIG_COLOR, width=1.5),
            hovertemplate="Signal=%{y:.4f}<extra></extra>",
        ), row=row, col=1)

        fig.add_hline(y=0, row=row, col=1,
                      line=dict(color='#444', width=0.8))

    # ────────────────────────────────────
    # KD
    # ────────────────────────────────────
    def _add_kd(self, fig, dates, ind: Dict, row):
        fig.add_trace(go.Scatter(
            x=dates, y=ind['k'],
            name='K', mode='lines',
            line=dict(color=K_COLOR, width=1.5),
            hovertemplate="K=%{y:.1f}<extra></extra>",
        ), row=row, col=1)

        fig.add_trace(go.Scatter(
            x=dates, y=ind['d'],
            name='D', mode='lines',
            line=dict(color=D_COLOR, width=1.5),
            hovertemplate="D=%{y:.1f}<extra></extra>",
        ), row=row, col=1)

        for level, color in [(80, '#ff4757'), (20, '#00b09b'), (50, '#444')]:
            fig.add_hline(y=level, row=row, col=1,
                          line=dict(color=color, width=0.8, dash='dot'))

        fig.update_yaxes(range=[0, 100], row=row, col=1)

    # ═══════════════════════════════════════════════════
    # 三大法人買賣超（台股）
    # ═══════════════════════════════════════════════════
    def plot_institutional_tw(self, inst: Dict) -> go.Figure:
        if not inst.get('available') or inst.get('type') == 'US':
            return None

        dates      = inst.get('dates', [])
        foreign    = inst.get('foreign_net', [])
        trust      = inst.get('trust_net', [])
        dealer     = inst.get('dealer_net', [])
        # 每日合計
        total = [f + t + d for f, t, d in zip(foreign, trust, dealer)]

        n = min(len(dates), 40)   # 最近 40 個交易日

        def bar_colors(vals):
            return ['rgba(239,83,80,0.75)' if v >= 0 else 'rgba(38,166,154,0.75)'
                    for v in vals]

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=("三大法人個別買賣超（近40日）", "三大法人合計"),
            row_heights=[0.6, 0.4],
        )

        for name, vals, color in [
            ('外資', foreign[-n:], '#5352ed'),
            ('投信', trust[-n:],   '#00b09b'),
            ('自營', dealer[-n:],  '#ffa502'),
        ]:
            fig.add_trace(go.Bar(
                x=dates[-n:], y=vals,
                name=name,
                marker_color=color,
                opacity=0.8,
            ), row=1, col=1)

        # 合計（彩色）
        tot_colors = bar_colors(total[-n:])
        fig.add_trace(go.Bar(
            x=dates[-n:], y=total[-n:],
            name='三大法人合計',
            marker_color=tot_colors,
            showlegend=False,
        ), row=2, col=1)

        # 零線
        fig.add_hline(y=0, row=1, col=1, line=dict(color='#555', width=0.8))
        fig.add_hline(y=0, row=2, col=1, line=dict(color='#555', width=0.8))

        layout = LAYOUT_BASE.copy()
        layout.update(
            height=420,
            barmode='relative',
            title=dict(text="三大法人買賣超（張）", font=dict(size=14)),
        )
        fig.update_layout(**layout)
        for i in [1, 2]:
            fig.update_xaxes(showgrid=True, gridcolor=GRID, row=i, col=1)
            fig.update_yaxes(showgrid=True, gridcolor=GRID, row=i, col=1, side='right')
        return fig

    # ═══════════════════════════════════════════════════
    # 技術指標快速儀表板（RSI / KD / MACD 量表）
    # ═══════════════════════════════════════════════════
    def plot_indicator_gauges(self, pat: Dict) -> go.Figure:
        rsi_v = pat.get('rsi_value', 50)
        kd_v  = pat.get('kd_values', (50, 50))
        k_v   = kd_v[0]

        fig = make_subplots(
            rows=1, cols=3,
            specs=[[{"type": "indicator"}] * 3],
            subplot_titles=["RSI(14)", "K值", "MACD 方向"],
        )

        # RSI 儀表
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=rsi_v,
            number=dict(font=dict(size=26, color=TEXT)),
            gauge=dict(
                axis=dict(range=[0, 100], tickcolor=TEXT),
                bar=dict(color='#ff4757' if rsi_v > 70 else '#00b09b' if rsi_v < 30 else '#5352ed'),
                steps=[
                    dict(range=[0, 30],  color="rgba(0,176,155,0.15)"),
                    dict(range=[30, 70], color="rgba(83,82,237,0.08)"),
                    dict(range=[70, 100],color="rgba(255,71,87,0.15)"),
                ],
                threshold=dict(line=dict(color="white", width=2), thickness=0.75,
                               value=70 if rsi_v > 50 else 30),
            ),
        ), row=1, col=1)

        # K值 儀表
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=k_v,
            number=dict(font=dict(size=26, color=TEXT)),
            gauge=dict(
                axis=dict(range=[0, 100], tickcolor=TEXT),
                bar=dict(color='#ff4757' if k_v > 80 else '#00b09b' if k_v < 20 else '#ffa502'),
                steps=[
                    dict(range=[0, 20],  color="rgba(0,176,155,0.15)"),
                    dict(range=[20, 80], color="rgba(255,165,2,0.05)"),
                    dict(range=[80, 100],color="rgba(255,71,87,0.15)"),
                ],
            ),
        ), row=1, col=2)

        # MACD 方向（以 MACD hist 正負表示多空）
        macd_v = pat.get('macd_values', (0, 0, 0))
        hist_v = macd_v[2]
        macd_display = min(max(hist_v * 100, -50), 50) + 50   # 映射到 0~100

        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=macd_display,
            number=dict(font=dict(size=26, color=TEXT),
                        suffix=" (" + ("多" if hist_v >= 0 else "空") + ")"),
            gauge=dict(
                axis=dict(range=[0, 100], tickvals=[0, 50, 100],
                          ticktext=['空', '中', '多'], tickcolor=TEXT),
                bar=dict(color='#00b09b' if hist_v >= 0 else '#ff4757'),
                steps=[
                    dict(range=[0, 50],  color="rgba(255,71,87,0.12)"),
                    dict(range=[50, 100],color="rgba(0,176,155,0.12)"),
                ],
                threshold=dict(line=dict(color="white", width=2), thickness=0.75, value=50),
            ),
        ), row=1, col=3)

        layout = LAYOUT_BASE.copy()
        layout.update(height=230, margin=dict(l=10, r=10, t=50, b=10))
        fig.update_layout(**layout)
        return fig

    # ═══════════════════════════════════════════════════
    # 近期價格走勢（簡版，近60日收盤+MA）
    # ═══════════════════════════════════════════════════
    def plot_price_mini(self, hist: pd.DataFrame, ind: Dict) -> go.Figure:
        recent = hist.tail(60)
        fig = go.Figure()

        close = recent['Close']
        color = UP_COLOR if float(close.iloc[-1]) >= float(close.iloc[0]) else DOWN_COLOR

        fig.add_trace(go.Scatter(
            x=recent.index, y=close,
            mode='lines',
            line=dict(color=color, width=2),
            fill='tozeroy',
            fillcolor=f"rgba({_hex_to_rgb(color)},0.08)",
            name='收盤價',
        ))

        layout = LAYOUT_BASE.copy()
        layout.update(height=180, margin=dict(l=5, r=5, t=10, b=5))
        layout.update(xaxis=dict(showticklabels=False, showgrid=False),
                      yaxis=dict(showgrid=False, side='right'))
        fig.update_layout(**layout)
        return fig


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip('#')
    return f"{int(h[0:2],16)}, {int(h[2:4],16)}, {int(h[4:6],16)}"
