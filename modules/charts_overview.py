"""
股票快速概覽：技術指標圖表與訊號判斷
- 布林通道 (Bollinger Bands)
- 移動平均線 (MA 5/10/20/60/120/240)
- MACD
- KD 隨機指標
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Tuple, Dict, Optional

BG     = "#0e1117"
CARD   = "#1a1d2e"
TEXT   = "#e0e0e0"
GRID   = "#2a2d3e"
GREEN  = "#00c896"
RED    = "#ff4444"
YELLOW = "#f0c040"
BLUE   = "#4a9eff"
ORANGE = "#ff8c00"


# ══════════════════════════════════════════
# 技術指標計算
# ══════════════════════════════════════════

def _ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()


def _bollinger(close: pd.Series, period=20, nstd=2):
    """回傳 (upper, mid, lower)"""
    mid   = close.rolling(period).mean()
    sigma = close.rolling(period).std(ddof=0)
    return mid + nstd * sigma, mid, mid - nstd * sigma


def _macd(close: pd.Series):
    """回傳 (macd_line, signal_line, histogram)"""
    macd_line = _ema(close, 12) - _ema(close, 26)
    sig_line  = _ema(macd_line, 9)
    return macd_line, sig_line, macd_line - sig_line


def _kd(high: pd.Series, low: pd.Series, close: pd.Series, period=9):
    """台式 KD：RSV 以指數平滑 1/3 權重計算 K、D"""
    ll  = low.rolling(period).min()
    hh  = high.rolling(period).max()
    rng = hh - ll
    rsv = np.where(rng > 0, (close - ll) / rng * 100, 50.0)

    k_arr = np.full(len(close), 50.0)
    d_arr = np.full(len(close), 50.0)
    for i in range(1, len(close)):
        r = rsv[i] if not np.isnan(rsv[i]) else 50.0
        k_arr[i] = k_arr[i-1] * 2/3 + r * 1/3
        d_arr[i] = d_arr[i-1] * 2/3 + k_arr[i] * 1/3

    return (pd.Series(k_arr, index=close.index),
            pd.Series(d_arr, index=close.index))


# ══════════════════════════════════════════
# 訊號判斷
# ══════════════════════════════════════════

def get_bb_signal(hist: pd.DataFrame) -> Tuple[str, str, str]:
    """回傳 (訊號名稱, 說明文字, 顏色)"""
    close = hist['Close'].dropna()
    upper, mid, lower = _bollinger(close)

    valid = mid.dropna()
    if len(valid) < 6:
        return "資料不足", "無法判斷布林通道", "#aaa"

    u5 = upper.iloc[-6:].values
    m5 = mid.iloc[-6:].values
    l5 = lower.iloc[-6:].values
    c5 = close.iloc[-6:].values

    # 帶寬趨勢
    w5 = (u5 - l5) / np.where(m5 != 0, m5, 1)
    width_chg = (w5[-1] - w5[0]) / max(abs(w5[0]), 0.001)

    # 中軌方向
    mid_chg = (m5[-1] - m5[0]) / max(abs(m5[0]), 0.001)

    # 股價在帶中的位置 (0=下軌, 1=上軌)
    band_rng = u5[-1] - l5[-1]
    pos = (c5[-1] - l5[-1]) / band_rng if band_rng > 0 else 0.5

    if width_chg > 0.08:                     # 帶寬擴張
        if pos >= 0.65:
            return "三線張口向上", "波動擴大，股價突破上軌 → 強勢多頭", GREEN
        else:
            return "三線張口向下", "波動擴大，股價跌破下軌 → 空頭訊號", RED
    elif width_chg < -0.08:                  # 帶寬收窄
        return "三線收口", "波動收斂，蓄積能量，即將出現方向性突破", YELLOW
    elif abs(mid_chg) < 0.003:               # 中軌走平
        return "三線走平", "趨勢不明，價格橫向整理，等待突破方向", "#a4b0be"
    elif mid_chg > 0.003:
        return "三線向上", "中軌上揚，多頭趨勢發展中", GREEN
    else:
        return "三線向下", "中軌下彎，空頭趨勢發展中", RED


def get_ma_status(hist: pd.DataFrame) -> Dict:
    """回傳均線多空狀態"""
    close = hist['Close'].dropna()
    price = float(close.iloc[-1])

    ma_defs = [
        ('週線 (5日)',    5),
        ('雙週 (10日)', 10),
        ('月線 (20日)', 20),
        ('季線 (60日)', 60),
        ('半年 (120日)', 120),
        ('年線 (240日)', 240),
    ]

    result = {}
    for name, period in ma_defs:
        if len(close) >= period:
            val = float(close.rolling(period).mean().iloc[-1])
            result[name] = {
                'value':    round(val, 2),
                'above':    price > val,
                'diff_pct': round((price - val) / val * 100, 1),
            }
        else:
            result[name] = None

    above_cnt  = sum(1 for v in result.values() if v and v['above'])
    valid_cnt  = sum(1 for v in result.values() if v is not None)

    if valid_cnt == 0:
        summary, color = "資料不足", "#aaa"
    elif above_cnt == valid_cnt:
        summary, color = f"站上全部 {valid_cnt} 條均線（多頭強勢）", GREEN
    elif above_cnt >= round(valid_cnt * 0.67):
        summary, color = f"站上 {above_cnt}/{valid_cnt} 條均線（偏多）", "#5cb85c"
    elif above_cnt >= round(valid_cnt * 0.34):
        summary, color = f"均線多空交錯 {above_cnt}/{valid_cnt}（盤整）", YELLOW
    elif above_cnt > 0:
        summary, color = f"站上 {above_cnt}/{valid_cnt} 條均線（偏空）", ORANGE
    else:
        summary, color = f"跌破全部 {valid_cnt} 條均線（空頭弱勢）", RED

    return {
        'mas':         result,
        'price':       price,
        'above_count': above_cnt,
        'total':       valid_cnt,
        'summary':     summary,
        'color':       color,
    }


def get_macd_signal(hist: pd.DataFrame) -> Tuple[str, str, str]:
    close = hist['Close'].dropna()
    if len(close) < 35:
        return "資料不足", "無法計算 MACD（至少需35筆資料）", "#aaa"

    _, _, histo = _macd(close)
    h0, h1, h2 = float(histo.iloc[-1]), float(histo.iloc[-2]), float(histo.iloc[-3])

    if h1 <= 0 < h0:
        return "負值轉正", "MACD 柱狀由負轉正 → 多頭反轉訊號", GREEN
    elif h1 >= 0 > h0:
        return "正值轉負", "MACD 柱狀由正轉負 → 空頭反轉訊號", RED
    elif h0 > 0 and h0 >= h1:
        return "正值向上", "MACD 正值持續放大 → 多頭趨勢強勁", GREEN
    elif h0 > 0 and h0 < h1:
        return "正值縮小", "MACD 正值但柱狀縮短 → 多頭動能減弱，留意", YELLOW
    elif h0 < 0 and h0 <= h1:
        return "負值向下", "MACD 負值持續擴大 → 空頭趨勢強勁", RED
    else:
        return "負值縮小", "MACD 負值但柱狀縮短 → 空頭動能減弱，可能反彈", ORANGE


def get_kd_signal(hist: pd.DataFrame) -> Tuple[str, str, str]:
    if len(hist) < 15:
        return "資料不足", "無法計算 KD（至少需15筆資料）", "#aaa"

    k, d = _kd(hist['High'], hist['Low'], hist['Close'])
    kv, dv   = float(k.iloc[-1]), float(d.iloc[-1])
    kp, dp   = float(k.iloc[-2]), float(d.iloc[-2])

    golden = kp <= dp and kv > dv
    death  = kp >= dp and kv < dv

    if kv >= 80:
        return f"超買區 (K={kv:.0f})", f"KD 進入超買區（>80），留意拉回風險", ORANGE
    elif kv <= 20:
        return f"超賣區 (K={kv:.0f})", f"KD 進入超賣區（<20），可能出現反彈", BLUE
    elif golden:
        return f"黃金交叉 (K={kv:.0f})", "K 線由下向上穿越 D 線 → 短線偏多", GREEN
    elif death:
        return f"死亡交叉 (K={kv:.0f})", "K 線由上向下穿越 D 線 → 短線偏空", RED
    elif kv > dv:
        return f"K 在 D 上方 (K={kv:.0f})", "K > D，短線偏多格局", "#5cb85c"
    else:
        return f"K 在 D 下方 (K={kv:.0f})", "K < D，短線偏空格局", ORANGE


# ══════════════════════════════════════════
# 圖表繪製
# ══════════════════════════════════════════

def _base_layout(title: str, sig_name: str, sig_color: str, height=380) -> dict:
    return dict(
        title=dict(
            text=f"{title}  ·  <span style='color:{sig_color}'>{sig_name}</span>",
            font=dict(color=TEXT, size=15), x=0.02,
        ),
        paper_bgcolor=BG, plot_bgcolor=CARD,
        font=dict(color=TEXT),
        height=height,
        margin=dict(t=55, b=40, l=60, r=20),
        hovermode='x unified',
        legend=dict(bgcolor=CARD, bordercolor=GRID, borderwidth=1,
                    font=dict(color=TEXT), orientation='h',
                    yanchor='bottom', y=1.02, xanchor='right', x=1),
    )


def plot_bollinger_chart(hist: pd.DataFrame, signal: Tuple) -> go.Figure:
    close = hist['Close']
    upper, mid, lower = _bollinger(close)
    dates = hist.index
    sig_name, _, sig_color = signal

    fig = go.Figure()

    # Bollinger fill
    fig.add_trace(go.Scatter(
        x=list(dates) + list(dates[::-1]),
        y=list(upper.ffill()) + list(lower.ffill()[::-1]),
        fill='toself', fillcolor='rgba(74,158,255,0.07)',
        line=dict(color='rgba(0,0,0,0)'), showlegend=False, hoverinfo='skip',
    ))
    fig.add_trace(go.Scatter(x=dates, y=upper, name='上軌',
        line=dict(color='rgba(74,158,255,0.55)', width=1, dash='dot'),
        hovertemplate='上軌:%{y:,.2f}<extra></extra>'))
    fig.add_trace(go.Scatter(x=dates, y=mid, name='中軌(20MA)',
        line=dict(color='rgba(240,192,64,0.85)', width=1.5),
        hovertemplate='中軌:%{y:,.2f}<extra></extra>'))
    fig.add_trace(go.Scatter(x=dates, y=lower, name='下軌',
        line=dict(color='rgba(74,158,255,0.55)', width=1, dash='dot'),
        hovertemplate='下軌:%{y:,.2f}<extra></extra>'))
    fig.add_trace(go.Scatter(x=dates, y=close, name='收盤價',
        line=dict(color='#e0e0e0', width=2),
        hovertemplate='%{x|%Y-%m-%d}  收盤:%{y:,.2f}<extra></extra>'))

    fig.update_layout(**_base_layout("布林通道", sig_name, sig_color))
    fig.update_xaxes(showgrid=False, tickfont=dict(color=TEXT), rangeslider=dict(visible=False))
    fig.update_yaxes(showgrid=True, gridcolor=GRID, tickfont=dict(color=TEXT))
    return fig


def plot_ma_chart(hist: pd.DataFrame, ma_status: Dict) -> go.Figure:
    close = hist['Close']
    dates = hist.index
    summary = ma_status.get('summary', '')
    color   = ma_status.get('color', TEXT)

    ma_configs = [
        ('週(5)',    5,   '#ff6b6b'),
        ('雙週(10)', 10,  '#ffa502'),
        ('月(20)',   20,  '#ffdd59'),
        ('季(60)',   60,  '#7bed9f'),
        ('半年(120)',120, '#70a1ff'),
        ('年(240)',  240, '#a29bfe'),
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=close, name='收盤價',
        line=dict(color='#e0e0e0', width=2),
        hovertemplate='%{x|%Y-%m-%d}  收盤:%{y:,.2f}<extra></extra>'))

    for label, period, clr in ma_configs:
        if len(close) >= period:
            ma = close.rolling(period).mean()
            fig.add_trace(go.Scatter(x=dates, y=ma, name=label,
                line=dict(color=clr, width=1.2),
                hovertemplate=f'{label}:%{{y:,.2f}}<extra></extra>'))

    fig.update_layout(**_base_layout("移動平均線", summary, color))
    fig.update_xaxes(showgrid=False, tickfont=dict(color=TEXT), rangeslider=dict(visible=False))
    fig.update_yaxes(showgrid=True, gridcolor=GRID, tickfont=dict(color=TEXT))
    return fig


def plot_macd_chart(hist: pd.DataFrame, signal: Tuple) -> go.Figure:
    close = hist['Close'].dropna()
    dates = close.index
    macd_line, sig_line, histo = _macd(close)
    sig_name, _, sig_color = signal

    bar_colors = [GREEN if v >= 0 else RED for v in histo]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.55, 0.45], vertical_spacing=0.05)

    # Price
    fig.add_trace(go.Scatter(x=dates, y=close, name='收盤',
        line=dict(color='#e0e0e0', width=1.5), showlegend=False,
        hovertemplate='%{x|%Y-%m-%d}  %{y:,.2f}<extra></extra>'), row=1, col=1)

    # Histogram
    fig.add_trace(go.Bar(x=dates, y=histo, name='柱狀',
        marker_color=bar_colors, marker_opacity=0.75, showlegend=False), row=2, col=1)

    # MACD & Signal lines
    fig.add_trace(go.Scatter(x=dates, y=macd_line, name='MACD',
        line=dict(color=BLUE, width=1.5)), row=2, col=1)
    fig.add_trace(go.Scatter(x=dates, y=sig_line, name='Signal',
        line=dict(color=ORANGE, width=1.5)), row=2, col=1)

    layout = _base_layout("MACD", sig_name, sig_color, height=420)
    layout['legend']['orientation'] = 'v'
    layout['legend'].pop('yanchor', None)
    layout['legend'].pop('y', None)
    layout['legend'].pop('xanchor', None)
    layout['legend'].pop('x', None)
    fig.update_layout(**layout)
    fig.update_xaxes(showgrid=False, tickfont=dict(color=TEXT))
    fig.update_yaxes(showgrid=True, gridcolor=GRID, tickfont=dict(color=TEXT))
    return fig


def plot_kd_chart(hist: pd.DataFrame, signal: Tuple) -> go.Figure:
    k, d  = _kd(hist['High'], hist['Low'], hist['Close'])
    close = hist['Close']
    dates = hist.index
    sig_name, _, sig_color = signal

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.55, 0.45], vertical_spacing=0.05)

    # Price
    fig.add_trace(go.Scatter(x=dates, y=close, name='收盤',
        line=dict(color='#e0e0e0', width=1.5), showlegend=False,
        hovertemplate='%{x|%Y-%m-%d}  %{y:,.2f}<extra></extra>'), row=1, col=1)

    # Overbought / Oversold zones
    fig.add_hrect(y0=80, y1=100, fillcolor='rgba(255,68,68,0.07)',
                  line_width=0, row=2, col=1)
    fig.add_hrect(y0=0, y1=20, fillcolor='rgba(74,158,255,0.07)',
                  line_width=0, row=2, col=1)

    fig.add_trace(go.Scatter(x=dates, y=k, name='K',
        line=dict(color=BLUE, width=1.8),
        hovertemplate='K:%{y:.1f}<extra></extra>'), row=2, col=1)
    fig.add_trace(go.Scatter(x=dates, y=d, name='D',
        line=dict(color=ORANGE, width=1.8),
        hovertemplate='D:%{y:.1f}<extra></extra>'), row=2, col=1)

    fig.add_hline(y=80, line=dict(color=RED,   width=1, dash='dot'), row=2, col=1)
    fig.add_hline(y=20, line=dict(color=GREEN, width=1, dash='dot'), row=2, col=1)

    layout = _base_layout("KD 隨機指標", sig_name, sig_color, height=420)
    layout['legend']['orientation'] = 'v'
    layout['legend'].pop('yanchor', None)
    layout['legend'].pop('y', None)
    layout['legend'].pop('xanchor', None)
    layout['legend'].pop('x', None)
    fig.update_layout(**layout)
    fig.update_xaxes(showgrid=False, tickfont=dict(color=TEXT))
    fig.update_yaxes(showgrid=True, gridcolor=GRID, tickfont=dict(color=TEXT))
    fig.update_yaxes(range=[0, 100], row=2, col=1)
    return fig
