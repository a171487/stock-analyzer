"""
功能二：技術面走勢分析
- 支撐位 / 阻力位
- RSI、MACD、均線、KD、布林通道
- 成交量分析
- 法人籌碼動向（台股）
- 短中長期走勢預測
- 進場點與停損位建議
"""

import numpy as np
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.data_fetcher import StockDataFetcher

FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"


# ════════════════════════════════════════════════════════
# 指標計算
# ════════════════════════════════════════════════════════
def calc_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    delta = closes.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_g = gain.ewm(com=period - 1, adjust=False).mean()
    avg_l = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_g / avg_l.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def calc_macd(closes: pd.Series, fast=12, slow=26, signal=9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    ema_f   = closes.ewm(span=fast,   adjust=False).mean()
    ema_s   = closes.ewm(span=slow,   adjust=False).mean()
    macd    = ema_f - ema_s
    sig     = macd.ewm(span=signal,   adjust=False).mean()
    hist    = macd - sig
    return macd, sig, hist


def calc_kd(hist_df: pd.DataFrame, k_period=9, slowing=3, d_period=3) -> Tuple[pd.Series, pd.Series]:
    low_min  = hist_df['Low'].rolling(k_period).min()
    high_max = hist_df['High'].rolling(k_period).max()
    denom = (high_max - low_min).replace(0, np.nan)
    raw_k = 100 * (hist_df['Close'] - low_min) / denom
    k = raw_k.ewm(span=slowing, adjust=False).mean()
    d = k.ewm(span=d_period,  adjust=False).mean()
    return k, d


def calc_bb(closes: pd.Series, period=20, std_dev=2.0) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    ma    = closes.rolling(period).mean()
    std   = closes.rolling(period).std()
    upper = ma + std_dev * std
    lower = ma - std_dev * std
    pct_b = (closes - lower) / (upper - lower).replace(0, np.nan)
    return ma, upper, lower, pct_b


def calc_ma(closes: pd.Series, periods: List[int]) -> Dict[int, pd.Series]:
    return {p: closes.rolling(p).mean() for p in periods}


def calc_atr(hist_df: pd.DataFrame, period=14) -> pd.Series:
    tr = pd.concat([
        hist_df['High'] - hist_df['Low'],
        (hist_df['High'] - hist_df['Close'].shift()).abs(),
        (hist_df['Low']  - hist_df['Close'].shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


# ════════════════════════════════════════════════════════
# 支撐 / 阻力
# ════════════════════════════════════════════════════════
def find_pivot_points(hist_df: pd.DataFrame, window: int = 5) -> Dict[str, List[float]]:
    """用 pivot high/low 找支撐阻力"""
    highs, lows = [], []
    n = len(hist_df)
    for i in range(window, n - window):
        seg_h = hist_df['High'].iloc[i - window: i + window + 1]
        seg_l = hist_df['Low'].iloc[i  - window: i + window + 1]
        if hist_df['High'].iloc[i] == seg_h.max():
            highs.append(float(hist_df['High'].iloc[i]))
        if hist_df['Low'].iloc[i] == seg_l.min():
            lows.append(float(hist_df['Low'].iloc[i]))
    return {'pivot_highs': sorted(set(highs)), 'pivot_lows': sorted(set(lows))}


def cluster_levels(levels: List[float], tol_pct: float = 0.02) -> List[float]:
    """將相近的支撐/阻力合併成一個價位"""
    if not levels:
        return []
    sorted_lvl = sorted(levels)
    clusters = [[sorted_lvl[0]]]
    for v in sorted_lvl[1:]:
        if v <= clusters[-1][-1] * (1 + tol_pct):
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return [np.mean(c) for c in clusters]


# ════════════════════════════════════════════════════════
# 主分析類別
# ════════════════════════════════════════════════════════
class TechnicalAnalyzer:

    MA_PERIODS = [5, 20, 60, 120, 240]

    def __init__(self, fetcher: StockDataFetcher, finmind_token: str = ""):
        self.fetcher       = fetcher
        self.finmind_token = finmind_token

    # ──────────────────────────────────────────
    # 主入口
    # ──────────────────────────────────────────
    def run_full_analysis(self) -> Dict:
        hist = self._get_price_history()
        if hist.empty or len(hist) < 30:
            return {'error': '歷史價格資料不足（至少需要30個交易日）'}

        ind   = self._calc_all_indicators(hist)
        sr    = self._find_sr_levels(hist, ind)
        inst  = self._get_institutional_data()
        pat   = self._identify_pattern(hist, ind)
        sugg  = self._generate_suggestions(hist, ind, sr, pat)
        text  = self._generate_analysis(hist, ind, sr, inst, pat, sugg)

        return {
            'hist':          hist,
            'indicators':    ind,
            'sr_levels':     sr,
            'institutional': inst,
            'pattern':       pat,
            'suggestions':   sugg,
            'analysis':      text,
        }

    # ──────────────────────────────────────────
    # 歷史價格
    # ──────────────────────────────────────────
    def _get_price_history(self) -> pd.DataFrame:
        try:
            hist = self.fetcher.get_historical_prices(period="2y")
            if hist is None or hist.empty:
                hist = self.fetcher.get_historical_prices(period="1y")
            if hist is not None and not hist.empty:
                hist = hist.dropna(subset=['Close'])
                # 保留最近 500 個交易日即可
                return hist.tail(500)
        except Exception:
            pass
        return pd.DataFrame()

    # ──────────────────────────────────────────
    # 所有技術指標
    # ──────────────────────────────────────────
    def _calc_all_indicators(self, hist: pd.DataFrame) -> Dict:
        c = hist['Close']
        v = hist['Volume']

        # 移動平均
        ma = calc_ma(c, self.MA_PERIODS)

        # RSI
        rsi14 = calc_rsi(c, 14)

        # MACD
        macd, macd_sig, macd_hist = calc_macd(c)

        # KD
        k, d = calc_kd(hist)

        # 布林通道
        bb_ma, bb_upper, bb_lower, bb_pct = calc_bb(c)

        # ATR（衡量波動）
        atr = calc_atr(hist)

        # 成交量相對強度
        vol_ma20 = v.rolling(20).mean()

        return {
            'close':      c,
            'volume':     v,
            'ma':         ma,
            'rsi':        rsi14,
            'macd':       macd,
            'macd_sig':   macd_sig,
            'macd_hist':  macd_hist,
            'k':          k,
            'd':          d,
            'bb_ma':      bb_ma,
            'bb_upper':   bb_upper,
            'bb_lower':   bb_lower,
            'bb_pct':     bb_pct,
            'atr':        atr,
            'vol_ma20':   vol_ma20,
        }

    # ──────────────────────────────────────────
    # 支撐 / 阻力
    # ──────────────────────────────────────────
    def _find_sr_levels(self, hist: pd.DataFrame, ind: Dict) -> Dict:
        price = float(ind['close'].iloc[-1])

        # pivot 方法（近 120 天）
        recent = hist.tail(120)
        pivots = find_pivot_points(recent, window=4)
        all_highs = cluster_levels(pivots['pivot_highs'], 0.025)
        all_lows  = cluster_levels(pivots['pivot_lows'],  0.025)

        # 加入均線位
        for p in [20, 60]:
            ma_val = ind['ma'].get(p)
            if ma_val is not None:
                v = float(ma_val.iloc[-1])
                if not np.isnan(v):
                    if v > price:
                        all_highs.append(v)
                    else:
                        all_lows.append(v)

        # 布林通道
        bb_upper = float(ind['bb_upper'].iloc[-1])
        bb_lower = float(ind['bb_lower'].iloc[-1])

        # 52 週高低點
        w52_high = float(hist['High'].tail(252).max())
        w52_low  = float(hist['Low'].tail(252).min())

        # 最近 20 日高低
        recent_high = float(hist['High'].tail(20).max())
        recent_low  = float(hist['Low'].tail(20).min())

        # 最終壓力 / 支撐清單（在當前股價上下）
        resistances = sorted(set(
            [r for r in all_highs if r > price * 1.005] +
            ([bb_upper] if bb_upper > price else []) +
            ([recent_high] if recent_high > price else [])
        ))[:4]

        supports = sorted(set(
            [s for s in all_lows if s < price * 0.995] +
            ([bb_lower] if bb_lower < price else []) +
            ([recent_low] if recent_low < price else [])
        ), reverse=True)[:4]

        return {
            'price':       price,
            'resistances': resistances,
            'supports':    supports,
            'bb_upper':    bb_upper,
            'bb_lower':    bb_lower,
            'w52_high':    w52_high,
            'w52_low':     w52_low,
        }

    # ──────────────────────────────────────────
    # 法人籌碼資料
    # ──────────────────────────────────────────
    def _get_institutional_data(self) -> Dict:
        if self.fetcher.stock_type == 'TW':
            return self._get_tw_institutional()
        else:
            return self._get_us_institutional()

    def _get_tw_institutional(self) -> Dict:
        """FinMind：台股三大法人買賣超（近 60 日）
        dataset: TaiwanStockInstitutionalInvestorsBuySell
        name 欄位: Foreign_Investor, Foreign_Dealer_Self,
                   Investment_Trust, Dealer_self, Dealer_Hedging
        """
        try:
            start = (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d')
            params = {
                "dataset":    "TaiwanStockInstitutionalInvestorsBuySell",
                "data_id":    self.fetcher.stock_id,
                "start_date": start,
            }
            if self.finmind_token:
                params["token"] = self.finmind_token

            resp = requests.get(FINMIND_URL, params=params, timeout=10)
            data = resp.json()

            if data.get('status') != 200 or not data.get('data'):
                return {'available': False, 'reason': 'FinMind 無資料（可能需要 token）'}

            df = pd.DataFrame(data['data'])
            df['date'] = pd.to_datetime(df['date'])
            df['net']  = df['buy'].astype(float) - df['sell'].astype(float)

            # 按日期+法人 pivot
            piv = df.pivot_table(index='date', columns='name', values='net', aggfunc='sum').fillna(0)

            # 合併外資（Foreign_Investor + Foreign_Dealer_Self）
            foreign_cols = [c for c in piv.columns if 'Foreign_Investor' in c or 'Foreign_Dealer' in c]
            trust_cols   = [c for c in piv.columns if 'Investment_Trust' in c]
            dealer_cols  = [c for c in piv.columns if 'Dealer' in c and c not in foreign_cols]

            piv['外資'] = piv[foreign_cols].sum(axis=1) if foreign_cols else 0
            piv['投信'] = piv[trust_cols].sum(axis=1)   if trust_cols   else 0
            piv['自營'] = piv[dealer_cols].sum(axis=1)  if dealer_cols  else 0

            piv = piv.sort_index()
            dates = piv.index.strftime('%m/%d').tolist()

            # 單位：股 → 張（÷1000）
            f_net = (piv['外資'] / 1000).round(0).values.tolist()
            t_net = (piv['投信'] / 1000).round(0).values.tolist()
            d_net = (piv['自營'] / 1000).round(0).values.tolist()

            n20 = min(20, len(f_net))

            return {
                'available':   True,
                'dates':       dates,
                'foreign_net': f_net,
                'trust_net':   t_net,
                'dealer_net':  d_net,
                'foreign_cum': float(sum(f_net[-n20:])),
                'trust_cum':   float(sum(t_net[-n20:])),
                'dealer_cum':  float(sum(d_net[-n20:])),
                'total_cum':   float(sum(
                    [f + t + d for f, t, d in
                     zip(f_net[-n20:], t_net[-n20:], d_net[-n20:])]
                )),
            }
        except Exception as e:
            return {'available': False, 'reason': str(e)}

    def _get_us_institutional(self) -> Dict:
        """美股：yfinance institutional holders"""
        try:
            yf_ticker = self.fetcher._yf_ticker
            inst_info = self.fetcher.info

            return {
                'available':         True,
                'type':              'US',
                'inst_own_pct':      inst_info.get('institutionsPercentHeld'),
                'insider_own_pct':   inst_info.get('insidersPercentHeld'),
                'short_ratio':       inst_info.get('shortRatio'),
                'short_pct_float':   inst_info.get('shortPercentOfFloat'),
                'shares_short':      inst_info.get('sharesShort'),
                'held_by_insiders':  inst_info.get('heldPercentInsiders'),
                'held_by_institutions': inst_info.get('heldPercentInstitutions'),
            }
        except Exception:
            return {'available': False, 'reason': '無法取得美股法人資料'}

    # ──────────────────────────────────────────
    # 技術形態識別
    # ──────────────────────────────────────────
    def _identify_pattern(self, hist: pd.DataFrame, ind: Dict) -> Dict:
        c   = ind['close']
        ma  = ind['ma']
        rsi = ind['rsi']
        k   = ind['k']
        d   = ind['d']
        macd     = ind['macd']
        macd_sig = ind['macd_sig']
        macd_h   = ind['macd_hist']
        bb_pct   = ind['bb_pct']
        vol      = ind['volume']
        vol_ma20 = ind['vol_ma20']

        price   = float(c.iloc[-1])
        results = {}

        # ── 1. 大趨勢（均線多空排列）──
        ma5  = float(ma[5].iloc[-1])   if not ma[5].isna().iloc[-1]  else None
        ma20 = float(ma[20].iloc[-1])  if not ma[20].isna().iloc[-1] else None
        ma60 = float(ma[60].iloc[-1])  if not ma[60].isna().iloc[-1] else None
        ma120= float(ma[120].iloc[-1]) if len(ma[120].dropna()) > 0   else None
        ma240= float(ma[240].iloc[-1]) if len(ma[240].dropna()) > 0   else None

        if all(v is not None for v in [ma5, ma20, ma60]):
            if ma5 > ma20 > ma60:
                results['ma_arrangement'] = ('多頭排列', '📈', 'bullish')
            elif ma5 < ma20 < ma60:
                results['ma_arrangement'] = ('空頭排列', '📉', 'bearish')
            else:
                results['ma_arrangement'] = ('均線糾纏（盤整）', '↔️', 'neutral')
        else:
            results['ma_arrangement'] = ('資料不足', '❓', 'neutral')

        # ── 2. 黃金/死亡交叉 ──
        if ma20 is not None and ma60 is not None:
            # 回看 5 日內的交叉
            recent_ma20 = ma[20].tail(5)
            recent_ma60 = ma[60].tail(5)
            diffs = recent_ma20 - recent_ma60
            cross = None
            for i in range(1, len(diffs)):
                if diffs.iloc[i-1] < 0 and diffs.iloc[i] >= 0:
                    cross = 'golden'
                elif diffs.iloc[i-1] > 0 and diffs.iloc[i] <= 0:
                    cross = 'death'
            results['ma_cross'] = cross
        else:
            results['ma_cross'] = None

        # ── 3. RSI 狀態 ──
        rsi_now = float(rsi.iloc[-1]) if not rsi.isna().iloc[-1] else 50
        results['rsi_value'] = rsi_now
        if rsi_now >= 80:
            results['rsi_signal'] = ('強力超買', '🔴', 'sell')
        elif rsi_now >= 70:
            results['rsi_signal'] = ('超買區', '🟠', 'caution')
        elif rsi_now <= 20:
            results['rsi_signal'] = ('強力超賣', '🟢', 'buy')
        elif rsi_now <= 30:
            results['rsi_signal'] = ('超賣區', '🟢', 'buy')
        elif 45 <= rsi_now <= 55:
            results['rsi_signal'] = ('中性', '⚪', 'neutral')
        elif rsi_now > 55:
            results['rsi_signal'] = ('多方偏強', '🔵', 'bullish')
        else:
            results['rsi_signal'] = ('空方偏弱', '🟡', 'bearish')

        # RSI 背離偵測（近 20 日）
        rsi_div = self._detect_rsi_divergence(c.tail(20), rsi.tail(20))
        results['rsi_divergence'] = rsi_div

        # ── 4. MACD 狀態 ──
        macd_now = float(macd.iloc[-1])
        sig_now  = float(macd_sig.iloc[-1])
        hist_now = float(macd_h.iloc[-1])
        hist_prev= float(macd_h.iloc[-2])

        results['macd_values'] = (round(macd_now, 4), round(sig_now, 4), round(hist_now, 4))

        if macd_now > sig_now and hist_now > 0 and hist_now > hist_prev:
            results['macd_signal'] = ('強力多頭', '🟢', 'buy')
        elif macd_now > sig_now and hist_now > 0:
            results['macd_signal'] = ('多頭（動能持穩）', '🔵', 'bullish')
        elif macd_now > sig_now and hist_now < 0:
            results['macd_signal'] = ('多頭（動能減弱）', '🟡', 'caution')
        elif macd_now < sig_now and hist_now < 0 and hist_now < hist_prev:
            results['macd_signal'] = ('強力空頭', '🔴', 'sell')
        elif macd_now < sig_now and hist_now < 0:
            results['macd_signal'] = ('空頭（動能持穩）', '🟠', 'bearish')
        else:
            results['macd_signal'] = ('空頭（動能減弱）', '🟡', 'caution')

        # 近期 MACD 交叉
        macd_diff = macd - macd_sig
        macd_cross = None
        for i in range(1, min(6, len(macd_diff))):
            if macd_diff.iloc[-i-1] < 0 and macd_diff.iloc[-i] >= 0:
                macd_cross = f'多頭交叉（{i}日前）'
                break
            elif macd_diff.iloc[-i-1] > 0 and macd_diff.iloc[-i] <= 0:
                macd_cross = f'空頭交叉（{i}日前）'
                break
        results['macd_cross'] = macd_cross

        # ── 5. KD 狀態 ──
        k_now = float(k.iloc[-1]) if not k.isna().iloc[-1] else 50
        d_now = float(d.iloc[-1]) if not d.isna().iloc[-1] else 50
        results['kd_values'] = (round(k_now, 1), round(d_now, 1))

        if k_now >= 80:
            results['kd_signal'] = ('超買（K≥80）', '🔴', 'caution')
        elif k_now <= 20:
            results['kd_signal'] = ('超賣（K≤20）', '🟢', 'buy')
        elif k_now > d_now:
            results['kd_signal'] = ('K在D之上（多頭）', '🔵', 'bullish')
        else:
            results['kd_signal'] = ('K在D之下（空頭）', '🟠', 'bearish')

        # KD 黃金/死亡交叉（近5日）
        kd_cross = None
        k_arr = k.tail(5).values
        d_arr = d.tail(5).values
        for i in range(1, len(k_arr)):
            if k_arr[i-1] < d_arr[i-1] and k_arr[i] >= d_arr[i]:
                kd_cross = '黃金交叉（KD）'
                break
            elif k_arr[i-1] > d_arr[i-1] and k_arr[i] <= d_arr[i]:
                kd_cross = '死亡交叉（KD）'
                break
        results['kd_cross'] = kd_cross

        # ── 6. 布林通道位置 ──
        bb_pct_now = float(bb_pct.iloc[-1]) if not bb_pct.isna().iloc[-1] else 0.5
        results['bb_pct'] = bb_pct_now
        bb_upper_now = float(ind['bb_upper'].iloc[-1])
        bb_lower_now = float(ind['bb_lower'].iloc[-1])
        bb_width = (bb_upper_now - bb_lower_now) / float(ind['bb_ma'].iloc[-1]) * 100

        if bb_pct_now >= 1.0:
            results['bb_signal'] = ('突破上軌', '🔴', 'overbought')
        elif bb_pct_now <= 0.0:
            results['bb_signal'] = ('跌破下軌', '🟢', 'oversold')
        elif bb_pct_now >= 0.8:
            results['bb_signal'] = ('接近上軌', '🟠', 'caution')
        elif bb_pct_now <= 0.2:
            results['bb_signal'] = ('接近下軌', '🔵', 'bullish')
        else:
            results['bb_signal'] = ('通道中段', '⚪', 'neutral')

        results['bb_width'] = round(bb_width, 2)
        results['bb_squeeze'] = bb_width < 5.0   # 布林收縮

        # ── 7. 成交量狀態 ──
        vol_now  = float(vol.iloc[-1])
        vol_avg  = float(vol_ma20.iloc[-1]) if not vol_ma20.isna().iloc[-1] else vol_now
        vol_ratio = vol_now / vol_avg if vol_avg > 0 else 1.0
        results['vol_ratio']  = round(vol_ratio, 2)

        # 近5日量能趨勢
        vol5      = vol.tail(5).mean()
        vol5_prev = vol.tail(10).head(5).mean()
        vol_trend = 'rising' if vol5 > vol5_prev * 1.1 else 'falling' if vol5 < vol5_prev * 0.9 else 'stable'
        results['vol_trend'] = vol_trend

        # 量價配合
        price_5d_chg = (float(c.iloc[-1]) - float(c.iloc[-6])) / float(c.iloc[-6]) * 100
        if price_5d_chg > 1 and vol_trend == 'rising':
            results['vol_price'] = ('量增價漲（健康上漲）', '🟢', 'bullish')
        elif price_5d_chg > 1 and vol_trend == 'falling':
            results['vol_price'] = ('量縮價漲（上漲乏力）', '🟡', 'caution')
        elif price_5d_chg < -1 and vol_trend == 'rising':
            results['vol_price'] = ('量增價跌（恐慌下殺）', '🔴', 'bearish')
        elif price_5d_chg < -1 and vol_trend == 'falling':
            results['vol_price'] = ('量縮價跌（緩步整理）', '🟡', 'neutral')
        else:
            results['vol_price'] = ('量價無明顯訊號', '⚪', 'neutral')

        # ── 8. 綜合形態評估 ──
        results['overall'] = self._calc_overall_signal(results)

        return results

    def _detect_rsi_divergence(self, closes: pd.Series, rsi: pd.Series) -> Optional[str]:
        """簡易 RSI 背離偵測"""
        if len(closes) < 10:
            return None
        mid = len(closes) // 2
        p1_price = float(closes.iloc[:mid].max())
        p2_price = float(closes.iloc[mid:].max())
        p1_rsi   = float(rsi.iloc[:mid].max())
        p2_rsi   = float(rsi.iloc[mid:].max())

        # 頂背離：股價創新高但RSI未創新高
        if p2_price > p1_price * 1.02 and p2_rsi < p1_rsi * 0.97:
            return '頂背離（股價新高但RSI未跟進，注意反轉）'

        p1_price_l = float(closes.iloc[:mid].min())
        p2_price_l = float(closes.iloc[mid:].min())
        p1_rsi_l   = float(rsi.iloc[:mid].min())
        p2_rsi_l   = float(rsi.iloc[mid:].min())

        # 底背離：股價創新低但RSI未創新低
        if p2_price_l < p1_price_l * 0.98 and p2_rsi_l > p1_rsi_l * 1.03:
            return '底背離（股價新低但RSI止跌，留意反彈）'

        return None

    def _calc_overall_signal(self, pat: Dict) -> Dict:
        """彙整所有指標，給出綜合多空訊號（-2到+2）"""
        score = 0
        signals = []

        ma_arr = pat.get('ma_arrangement', ('', '', 'neutral'))
        if ma_arr[2] == 'bullish':   score += 2; signals.append('均線多頭排列')
        elif ma_arr[2] == 'bearish': score -= 2; signals.append('均線空頭排列')

        cross = pat.get('ma_cross')
        if cross == 'golden': score += 2; signals.append('MA20/60 黃金交叉')
        elif cross == 'death': score -= 2; signals.append('MA20/60 死亡交叉')

        rsi_sig = pat.get('rsi_signal', ('', '', 'neutral'))
        if rsi_sig[2] == 'buy':      score += 1; signals.append('RSI 超賣反彈機會')
        elif rsi_sig[2] == 'sell':   score -= 1; signals.append('RSI 超買風險')
        elif rsi_sig[2] == 'bullish':score += 1

        macd_sig = pat.get('macd_signal', ('', '', 'neutral'))
        if macd_sig[2] == 'buy':     score += 2; signals.append('MACD 強力多頭')
        elif macd_sig[2] == 'bullish':score += 1
        elif macd_sig[2] == 'sell':  score -= 2; signals.append('MACD 強力空頭')
        elif macd_sig[2] == 'bearish':score -= 1

        kd_sig = pat.get('kd_signal', ('', '', 'neutral'))
        if kd_sig[2] == 'buy':      score += 1; signals.append('KD 超賣')
        elif kd_sig[2] == 'bullish':score += 1
        elif kd_sig[2] == 'bearish':score -= 1

        vp = pat.get('vol_price', ('', '', 'neutral'))
        if vp[2] == 'bullish': score += 1; signals.append('量增價漲')
        elif vp[2] == 'bearish':score -= 1; signals.append('量增價跌')

        kd_cross = pat.get('kd_cross')
        if kd_cross and '黃金' in kd_cross:  score += 1; signals.append(kd_cross)
        elif kd_cross and '死亡' in kd_cross: score -= 1; signals.append(kd_cross)

        # 分數 → 強弱
        if score >= 4:
            label, color = '強烈做多訊號', '#00b09b'
        elif score >= 2:
            label, color = '偏多，可留意買點', '#5cb85c'
        elif score >= 0:
            label, color = '中性偏多，觀望為主', '#ffa502'
        elif score >= -2:
            label, color = '偏空，謹慎操作', '#e67e22'
        else:
            label, color = '強烈偏空，避免追高', '#ff4757'

        return {
            'score':   score,
            'label':   label,
            'color':   color,
            'signals': signals,
        }

    # ──────────────────────────────────────────
    # 進場點與停損建議
    # ──────────────────────────────────────────
    def _generate_suggestions(self, hist: pd.DataFrame, ind: Dict,
                               sr: Dict, pat: Dict) -> Dict:
        price  = sr['price']
        atr    = float(ind['atr'].iloc[-1])
        supp   = sr['supports']
        resist = sr['resistances']
        overall_score = pat.get('overall', {}).get('score', 0)

        # 進場參考
        if overall_score >= 2:
            entry_note = '目前技術面偏多，可考慮在支撐位附近分批進場'
            entry_range = (
                round(supp[0] * 0.995, 2) if supp else round(price * 0.97, 2),
                round(price * 1.01, 2)
            )
        elif overall_score <= -2:
            entry_note = '技術面偏弱，建議等待跌深後出現反彈訊號再進場'
            entry_range = (
                round(supp[-1] * 0.98, 2) if supp else round(price * 0.90, 2),
                round(supp[0] * 0.99, 2)  if supp else round(price * 0.95, 2)
            )
        else:
            entry_note = '目前技術面中性，建議等待更明確的多空訊號出現'
            entry_range = (
                round((supp[0] if supp else price * 0.95), 2),
                round(price * 1.005, 2)
            )

        # 停損位（以 ATR 的 1.5 倍 + 最近支撐）
        atr_stop = round(price - atr * 1.5, 2)
        supp_stop = round(supp[0] * 0.97, 2) if supp else round(price * 0.93, 2)
        stop_loss = max(atr_stop, supp_stop)     # 取較高者（更保守停損）

        # 目標位
        if resist:
            target1 = round(resist[0], 2)
            target2 = round(resist[1], 2) if len(resist) > 1 else round(resist[0] * 1.05, 2)
        else:
            target1 = round(price * 1.05, 2)
            target2 = round(price * 1.10, 2)

        # 風險報酬比
        risk   = price - stop_loss
        reward = target1 - price
        rr     = round(reward / risk, 2) if risk > 0 else 0

        return {
            'entry_note':  entry_note,
            'entry_range': entry_range,
            'stop_loss':   round(stop_loss, 2),
            'stop_pct':    round((price - stop_loss) / price * 100, 1),
            'target1':     target1,
            'target2':     target2,
            'rr_ratio':    rr,
            'atr':         round(atr, 2),
            'atr_pct':     round(atr / price * 100, 2),
        }

    # ──────────────────────────────────────────
    # 文字分析
    # ──────────────────────────────────────────
    def _generate_analysis(self, hist, ind, sr, inst, pat, sugg) -> Dict[str, str]:
        name  = self.fetcher.get_company_name()
        price = sr['price']
        ccy   = '' if self.fetcher.stock_type == 'TW' else '$'

        # ── 1. 支撐阻力 ──
        resist = sr.get('resistances', [])
        supp   = sr.get('supports', [])
        sr_txt = f"**{name}** 目前股價：**{ccy}{price:,.2f}**\n\n"
        sr_txt += "**📍 近期壓力位（阻力）**\n"
        if resist:
            for i, r in enumerate(resist[:3], 1):
                pct = (r - price) / price * 100
                sr_txt += f"- 壓力{i}：**{ccy}{r:,.2f}**（距現價 +{pct:.1f}%）\n"
        else:
            sr_txt += "- 目前接近或超過近期高點，無明顯壓力\n"

        sr_txt += "\n**📍 近期支撐位**\n"
        if supp:
            for i, s in enumerate(supp[:3], 1):
                pct = (s - price) / price * 100
                sr_txt += f"- 支撐{i}：**{ccy}{s:,.2f}**（距現價 {pct:.1f}%）\n"
        else:
            sr_txt += "- 目前接近或低於近期低點，支撐有限\n"

        sr_txt += f"\n📊 52週高點：{ccy}{sr['w52_high']:,.2f} | 52週低點：{ccy}{sr['w52_low']:,.2f}\n"
        sr_txt += f"🔵 布林上軌：{ccy}{sr['bb_upper']:,.2f} | 布林下軌：{ccy}{sr['bb_lower']:,.2f}"

        # ── 2. 技術指標 ──
        rsi_v  = pat.get('rsi_value', 50)
        kd_v   = pat.get('kd_values', (50, 50))
        macd_v = pat.get('macd_values', (0, 0, 0))
        bb_w   = pat.get('bb_width', 0)

        ind_txt = f"| 指標 | 數值 | 訊號 | 解讀 |\n|---|---|---|---|\n"
        rsi_s = pat.get('rsi_signal', ('N/A', '', 'neutral'))
        ind_txt += f"| RSI(14) | {rsi_v:.1f} | {rsi_s[1]} {rsi_s[0]} | "
        if rsi_v > 70: ind_txt += "超買區，短期需注意回落風險 |\n"
        elif rsi_v < 30: ind_txt += "超賣區，反彈機率上升 |\n"
        else: ind_txt += f"目前在中性區間，趨勢參考均線 |\n"

        macd_s = pat.get('macd_signal', ('N/A', '', 'neutral'))
        ind_txt += f"| MACD | {macd_v[0]:.3f}/{macd_v[1]:.3f} | {macd_s[1]} {macd_s[0]} | "
        ind_txt += "MACD在訊號線之上，多方占優 |\n" if macd_v[0] > macd_v[1] else "MACD在訊號線之下，空方占優 |\n"

        kd_s = pat.get('kd_signal', ('N/A', '', 'neutral'))
        ind_txt += f"| KD(9,3,3) | K={kd_v[0]}/D={kd_v[1]} | {kd_s[1]} {kd_s[0]} | "
        if kd_v[0] > 80: ind_txt += "KD超買，留意高檔整理 |\n"
        elif kd_v[0] < 20: ind_txt += "KD超賣，注意短期反彈 |\n"
        elif kd_v[0] > kd_v[1]: ind_txt += "K高於D，短線偏多 |\n"
        else: ind_txt += "K低於D，短線偏空 |\n"

        bb_s = pat.get('bb_signal', ('N/A', '', 'neutral'))
        bb_p = pat.get('bb_pct', 0.5)
        ind_txt += f"| 布林通道 | %B={bb_p:.2f} | {bb_s[1]} {bb_s[0]} | "
        ind_txt += f"帶寬{bb_w:.1f}%，{'📦 布林收縮（注意即將變盤）' if pat.get('bb_squeeze') else '正常波動'} |\n"

        ma_arr = pat.get('ma_arrangement', ('N/A', '', 'neutral'))
        ind_txt += f"| 均線排列 | — | {ma_arr[1]} {ma_arr[0]} | "
        if ma_arr[2] == 'bullish': ind_txt += "MA5>MA20>MA60，多頭格局確立 |\n"
        elif ma_arr[2] == 'bearish': ind_txt += "MA5<MA20<MA60，空頭格局持續 |\n"
        else: ind_txt += "均線纏繞，方向待確認 |\n"

        cross = pat.get('ma_cross')
        if cross:
            ind_txt += f"\n> 🚨 **近期訊號**：{ma_arr[1]} MA20/60 {'黃金交叉' if cross=='golden' else '死亡交叉'}，{'多頭啟動信號' if cross=='golden' else '空頭確認信號'}\n"
        if pat.get('kd_cross'):
            ind_txt += f"> 🚨 **KD交叉**：{pat['kd_cross']}\n"
        if pat.get('macd_cross'):
            ind_txt += f"> 🚨 **MACD**：{pat['macd_cross']}\n"
        if pat.get('rsi_divergence'):
            ind_txt += f"> ⚠️ **RSI背離警示**：{pat['rsi_divergence']}\n"

        # ── 3. 成交量 ──
        vol_r = pat.get('vol_ratio', 1.0)
        vp    = pat.get('vol_price', ('N/A', '', 'neutral'))
        vt    = pat.get('vol_trend', 'stable')

        vol_txt = f"**成交量分析：{vp[1]} {vp[0]}**\n\n"
        vol_txt += f"- 今日量能為20日均量的 **{vol_r:.2f}倍**（{'爆量' if vol_r > 2 else '放量' if vol_r > 1.3 else '縮量' if vol_r < 0.7 else '正常量'}）\n"
        vol_txt += f"- 近5日量能趨勢：**{'放大' if vt=='rising' else '縮減' if vt=='falling' else '持平'}**\n\n"

        if vp[2] == 'bullish':
            vol_txt += "✅ 量增價漲是最健康的上漲模式，顯示有資金積極買入，多方主導。\n"
        elif vp[2] == 'bearish':
            vol_txt += "⚠️ 量增價跌代表主力在高檔出貨或恐慌拋售，需謹慎。\n"
        elif vp[0] == '量縮價漲（上漲乏力）':
            vol_txt += "⚠️ 量縮漲勢說明市場買氣不足，上漲持續性存疑，注意逢高減碼。\n"
        else:
            vol_txt += "量縮整理通常是正常修正，若在支撐區量縮止跌，反而是偏正面訊號。\n"

        # 台股加入法人資料
        if inst.get('available') and inst.get('type') != 'US':
            fc = inst.get('foreign_cum', 0)
            tc = inst.get('trust_cum', 0)
            dc = inst.get('dealer_cum', 0)
            tot = inst.get('total_cum', 0)
            vol_txt += f"\n**三大法人近20日累計（張）**\n"
            vol_txt += f"| 法人 | 買賣超 |\n|---|---|\n"
            vol_txt += f"| 外資 | {'🟢 +' if fc>0 else '🔴 '}{fc:,.0f} |\n"
            vol_txt += f"| 投信 | {'🟢 +' if tc>0 else '🔴 '}{tc:,.0f} |\n"
            vol_txt += f"| 自營商 | {'🟢 +' if dc>0 else '🔴 '}{dc:,.0f} |\n"
            vol_txt += f"| **合計** | {'🟢 +' if tot>0 else '🔴 '}**{tot:,.0f}** |\n"
            vol_txt += "\n" + ("✅ 三大法人合計買超，籌碼集中，為正面訊號。\n" if tot > 0
                               else "⚠️ 三大法人合計賣超，籌碼鬆動，需注意。\n")
        elif inst.get('available') and inst.get('type') == 'US':
            io  = inst.get('held_by_institutions')
            ins = inst.get('held_by_insiders')
            sr_ = inst.get('short_ratio')
            sf  = inst.get('short_pct_float')
            vol_txt += "\n**美股法人持股**\n"
            if io:  vol_txt += f"- 機構持股比率：**{io*100:.1f}%**\n"
            if ins: vol_txt += f"- 內部人持股：**{ins*100:.1f}%**\n"
            if sr_: vol_txt += f"- 空頭回補天數（Short Ratio）：**{sr_:.1f}天**\n"
            if sf:  vol_txt += f"- 空頭比率（Short Float）：**{sf*100:.1f}%**\n"
            if sf and sf > 0.15:
                vol_txt += "> ⚠️ 空頭比率偏高，若觸發軋空可能急漲，但也反映市場對該股的疑慮。\n"

        # ── 4. 走勢預測 ──
        overall = pat.get('overall', {})
        score   = overall.get('score', 0)
        label   = overall.get('label', '')
        sigs    = overall.get('signals', [])

        forecast_txt = f"### 綜合技術評分：**{score:+d}分** — {label}\n\n"
        if sigs:
            forecast_txt += "**支撐本次判斷的關鍵訊號：**\n"
            for s in sigs:
                forecast_txt += f"- ✔️ {s}\n"
            forecast_txt += "\n"

        forecast_txt += "| 期間 | 預測方向 | 關鍵觀察 |\n|---|---|---|\n"
        # 短期（1-2週）
        if score >= 2:
            st = "📈 偏多"; st_note = "突破近期壓力位有望加速"
        elif score <= -2:
            st = "📉 偏空"; st_note = "跌破支撐需警惕加速下殺"
        else:
            st = "↔️ 震盪"; st_note = "等待方向選擇，量能是關鍵"
        forecast_txt += f"| 短期（1-2週） | {st} | {st_note} |\n"

        # 中期（1-3個月）
        ma_arr_dir = pat.get('ma_arrangement', ('', '', 'neutral'))[2]
        if ma_arr_dir == 'bullish':
            mt = "📈 趨勢偏多"; mt_note = "MA多頭排列，逢拉回可布局"
        elif ma_arr_dir == 'bearish':
            mt = "📉 趨勢偏空"; mt_note = "MA空頭排列，反彈不追高"
        else:
            mt = "↔️ 方向未明"; mt_note = "觀察MA是否整理完畢後再進場"
        forecast_txt += f"| 中期（1-3月） | {mt} | {mt_note} |\n"

        # 長期
        ma240 = ind['ma'].get(240)
        if ma240 is not None and not ma240.isna().iloc[-1]:
            ma240_val = float(ma240.iloc[-1])
            if price > ma240_val:
                lt = "📈 長線偏多"; lt_note = f"股價高於年線({ccy}{ma240_val:,.1f})，長線趨勢向上"
            else:
                lt = "📉 長線偏空"; lt_note = f"股價低於年線({ccy}{ma240_val:,.1f})，長線結構待修復"
        else:
            lt = "📊 資料不足"; lt_note = "長線判斷需更長時間資料"
        forecast_txt += f"| 長期（半年+） | {lt} | {lt_note} |\n"

        # ── 5. 進場停損 ──
        trade_txt = f"### ⚠️ 以下僅供參考，非投資建議\n\n"
        trade_txt += f"**{sugg['entry_note']}**\n\n"
        trade_txt += f"| 項目 | 數值 |\n|---|---|\n"
        trade_txt += f"| 目前股價 | {ccy}{price:,.2f} |\n"
        trade_txt += f"| 參考進場區間 | {ccy}{sugg['entry_range'][0]:,.2f} ~ {ccy}{sugg['entry_range'][1]:,.2f} |\n"
        trade_txt += f"| 建議停損位 | {ccy}{sugg['stop_loss']:,.2f}（約 -{sugg['stop_pct']}%） |\n"
        trade_txt += f"| 第一目標 | {ccy}{sugg['target1']:,.2f} |\n"
        trade_txt += f"| 第二目標 | {ccy}{sugg['target2']:,.2f} |\n"
        trade_txt += f"| 風險報酬比 | {sugg['rr_ratio']}:1 |\n"
        trade_txt += f"| ATR（日波動） | {ccy}{sugg['atr']:,.2f}（{sugg['atr_pct']}%） |\n\n"

        rr = sugg['rr_ratio']
        if rr >= 2:
            trade_txt += "✅ 風險報酬比≥2:1，進場條件相對合理。\n"
        elif rr >= 1:
            trade_txt += "⚠️ 風險報酬比介於1-2倍，勝率需更高才能長期盈利。\n"
        else:
            trade_txt += "❌ 目前風險報酬比偏低，建議等待更好的進場時機。\n"

        trade_txt += "\n> 💡 **操作建議**：任何技術訊號皆非100%準確，建議搭配基本面與市場情緒判斷，並嚴格執行停損計畫。"

        return {
            'support_resistance': sr_txt,
            'indicators':         ind_txt,
            'volume_institutional': vol_txt,
            'forecast':           forecast_txt,
            'entry_stoploss':     trade_txt,
        }
