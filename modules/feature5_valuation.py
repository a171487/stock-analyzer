"""
功能五：內在價值估算（價值投資分析師視角）
- DCF 現金流折現模型（多情境）
- DDM 股息折現模型（適用配息股）
- 歷史估值區間分析（P/E P/B P/S 帶狀圖）
- 同業估值比較
- 安全邊際計算
- 敏感度分析（WACC × 成長率矩陣）
"""

import numpy as np
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.data_fetcher import StockDataFetcher

FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"


def _sf(v) -> Optional[float]:
    try:
        f = float(v)
        return f if np.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _cagr(start, end, years) -> Optional[float]:
    if start and end and years > 0 and start > 0 and end > 0:
        return (end / start) ** (1 / years) - 1
    return None


class ValuationAnalyzer:
    """價值投資估值引擎"""

    # ── 市場常數 ──
    RF_RATE_US = 0.045   # 美國無風險利率（10Y 公債）
    RF_RATE_TW = 0.015   # 台灣無風險利率
    ERP_US     = 0.055   # 美股風險溢酬
    ERP_TW     = 0.060   # 台股風險溢酬
    TAX_RATE   = 0.20    # 預設稅率

    def __init__(self, fetcher: StockDataFetcher):
        self.fetcher   = fetcher
        self._ticker   = fetcher._yf_ticker
        self.is_tw     = fetcher.stock_type == 'TW'
        self.rf        = self.RF_RATE_TW if self.is_tw else self.RF_RATE_US
        self.erp       = self.ERP_TW    if self.is_tw else self.ERP_US

    # ══════════════════════════════════════════
    # 主入口
    # ══════════════════════════════════════════
    def run_full_analysis(self) -> Dict:
        fin  = self.fetcher.get_financials_3y()
        bs   = self.fetcher.get_balance_sheet_3y()
        cf   = self.fetcher.get_cashflow_3y()
        val  = self.fetcher.get_valuation_metrics()
        hist = self.fetcher.get_historical_prices(period='5y')

        wacc_result = self._calc_wacc(fin, bs, val)
        dcf_result  = self._calc_dcf(fin, bs, cf, val, wacc_result)
        ddm_result  = self._calc_ddm(val, fin, bs)
        hist_val    = self._calc_historical_bands(hist, fin, val)
        peer_val    = self._calc_peer_valuation(val)
        sensitivity = self._calc_sensitivity(dcf_result, wacc_result)
        synthesis   = self._synthesize(dcf_result, ddm_result, hist_val,
                                        peer_val, val, wacc_result)

        return {
            'wacc':       wacc_result,
            'dcf':        dcf_result,
            'ddm':        ddm_result,
            'hist_val':   hist_val,
            'peer_val':   peer_val,
            'sensitivity': sensitivity,
            'synthesis':  synthesis,
            'current_price': _sf(val.get('current_price')),
            'val_metrics': val,
        }

    # ══════════════════════════════════════════
    # WACC 計算
    # ══════════════════════════════════════════
    def _calc_wacc(self, fin, bs, val) -> Dict:
        try:
            info = self._ticker.info or {}
        except Exception:
            info = {}

        beta = _sf(info.get('beta')) or 1.0
        beta = max(0.3, min(beta, 3.0))   # 合理範圍限制

        # Cost of Equity (CAPM)
        ke = self.rf + beta * self.erp

        # Cost of Debt
        int_exp = self._latest_val(fin, ['Interest Expense',
                                          'Interest Expense Non Operating'])
        lt_debt = self._latest_val(bs,  ['Long Term Debt',
                                          'Long Term Debt And Capital Lease Obligation'])
        st_debt = self._latest_val(bs,  ['Current Debt',
                                          'Short Term Debt', 'Short Long Term Debt'])

        total_debt = (lt_debt or 0) + (st_debt or 0)
        kd_pretax  = abs(int_exp) / total_debt if (int_exp and total_debt and total_debt > 0) else 0.04
        kd         = kd_pretax * (1 - self.TAX_RATE)

        # Weights
        mkt_cap = _sf(val.get('market_cap')) or 0
        denom   = mkt_cap + total_debt
        we = mkt_cap / denom if denom > 0 else 0.8
        wd = total_debt / denom if denom > 0 else 0.2

        wacc = we * ke + wd * kd

        # Clamp to sensible range
        wacc = max(0.05, min(wacc, 0.20))

        return {
            'wacc':       round(wacc, 4),
            'ke':         round(ke, 4),
            'kd':         round(kd, 4),
            'beta':       round(beta, 2),
            'we':         round(we, 3),
            'wd':         round(wd, 3),
            'total_debt': total_debt,
            'mkt_cap':    mkt_cap,
        }

    # ══════════════════════════════════════════
    # DCF 模型
    # ══════════════════════════════════════════
    def _calc_dcf(self, fin, bs, cf, val, wacc_result) -> Dict:
        fcf_list = self._vals(cf, ['Free Cash Flow'])
        if not fcf_list:
            # Fallback: CFO - CapEx
            cfo  = self._vals(cf, ['Operating Cash Flow',
                                    'Cash Flow From Continuing Operating Activities'])
            capx = self._vals(cf, ['Capital Expenditure'])
            if cfo and capx:
                n = min(len(cfo), len(capx))
                fcf_list = [c + (x or 0) for c, x in zip(cfo[:n], capx[:n])]
                # CapEx is negative in yfinance; CFO + CapEx = FCF

        if not fcf_list:
            return {'available': False, 'message': 'FCF 資料不足，無法計算 DCF'}

        valid_fcf = [v for v in fcf_list if v is not None and v != 0]
        if not valid_fcf:
            return {'available': False, 'message': 'FCF 皆為零或空值'}

        fcf_latest = valid_fcf[-1]
        fcf_base   = fcf_latest

        # ── 若最新FCF為負（重資本支出年份），用最近正值或營收代理 ──
        if fcf_base <= 0:
            positive_fcf = [v for v in valid_fcf if v > 0]
            if positive_fcf:
                fcf_base = positive_fcf[-1]   # 最近正值FCF年份
            else:
                # 以營收 × 典型FCF利潤率推算（保守15%）
                rev = self._latest_val(fin, ['Total Revenue', 'Revenue', 'Operating Revenue'])
                if rev and rev > 0:
                    fcf_base = rev * 0.15
                else:
                    return {'available': False, 'message': 'FCF 持續為負且無法取得營收資料'}

        # FCF CAGR（歷史）
        if len(valid_fcf) >= 2:
            hist_cagr = _cagr(abs(valid_fcf[0]), abs(valid_fcf[-1]), len(valid_fcf) - 1)
            if hist_cagr and fcf_latest < 0:
                hist_cagr = None   # 負 FCF 成長率無意義
        else:
            hist_cagr = None

        # 成長率假設
        rev_cagr = self._calc_rev_cagr(fin)

        g_bull = min(0.20, max(hist_cagr or 0, rev_cagr or 0) * 1.2 + 0.05)
        g_base = min(0.12, (hist_cagr or rev_cagr or 0.05) * 0.8 + 0.02)
        g_bear = min(0.05, max(0, (hist_cagr or rev_cagr or 0.02) * 0.4))

        wacc     = wacc_result['wacc']
        g_term   = 0.025    # 永續成長率（接近 GDP）

        scenarios = {}
        for label, g_proj in [('樂觀', g_bull), ('基本', g_base), ('悲觀', g_bear)]:
            pv_fcfs, fcf_t = [], fcf_base
            for t in range(1, 11):
                # 前5年用 g_proj，後5年線性收斂到 g_term
                if t <= 5:
                    g = g_proj
                else:
                    g = g_proj + (g_term - g_proj) * (t - 5) / 5
                fcf_t = fcf_t * (1 + g)
                pv    = fcf_t / ((1 + wacc) ** t)
                pv_fcfs.append({'year': t, 'fcf': fcf_t, 'pv': pv, 'g': g})

            # Terminal value (Gordon Growth)
            fcf_11   = pv_fcfs[-1]['fcf'] * (1 + g_term)
            tv       = fcf_11 / (wacc - g_term) if wacc > g_term else fcf_11 / 0.01
            pv_tv    = tv / ((1 + wacc) ** 10)

            sum_pv   = sum(p['pv'] for p in pv_fcfs)
            equity_v = sum_pv + pv_tv

            # Add cash, subtract debt
            cash  = self._latest_val(bs, ['Cash And Cash Equivalents',
                                           'Cash Cash Equivalents And Short Term Investments']) or 0
            debt  = wacc_result['total_debt'] or 0
            equity_v = equity_v + cash - debt

            shares = _sf((self._ticker.info or {}).get('sharesOutstanding')) or 1
            iv_per_share = equity_v / shares if shares > 0 else None

            scenarios[label] = {
                'g_proj':       round(g_proj * 100, 1),
                'pv_fcfs':      pv_fcfs,
                'pv_tv':        pv_tv,
                'sum_pv_fcfs':  sum_pv,
                'equity_value': equity_v,
                'iv_per_share': iv_per_share,
            }

        return {
            'available':   True,
            'wacc':        wacc,
            'g_term':      g_term,
            'fcf_latest':  fcf_latest,
            'fcf_list':    fcf_list,
            'hist_cagr':   hist_cagr,
            'rev_cagr':    rev_cagr,
            'scenarios':   scenarios,
            'base_iv':     scenarios['基本']['iv_per_share'],
        }

    # ══════════════════════════════════════════
    # DDM 股息折現模型
    # ══════════════════════════════════════════
    def _calc_ddm(self, val, fin, bs) -> Dict:
        try:
            info = self._ticker.info or {}
        except Exception:
            info = {}
        div_y  = _sf(info.get('dividendYield'))
        price  = _sf(val.get('current_price'))

        if not div_y or not price or div_y < 0.001:
            return {'available': False, 'message': '公司目前不配息或股息殖利率過低，不適用 DDM'}

        dps = div_y * price   # Dividend Per Share (TTM)

        # Sustainable growth rate: g = ROE × b (b = retention ratio)
        ni    = self._latest_val(fin, ['Net Income', 'Net Income Common Stockholders'])
        eq    = self._latest_val(bs,  ['Total Equity Gross Minority Interest',
                                        'Stockholders Equity'])
        roe   = ni / eq if (ni and eq and eq > 0) else None

        payout = _sf(info.get('payoutRatio'))
        b      = 1 - payout if payout and 0 < payout < 1 else 0.5
        g_ddm  = roe * b if roe and roe > 0 else 0.04

        # 合理範圍
        g_ddm = max(0.0, min(g_ddm, 0.08))

        ke = self.rf + (_sf(info.get('beta')) or 1.0) * self.erp

        # Gordon Growth Model: P = D1 / (Ke - g)
        if ke <= g_ddm:
            return {'available': False, 'message': f'Ke({ke:.2%}) ≤ g({g_ddm:.2%})，DDM 無法成立'}

        d1       = dps * (1 + g_ddm)
        iv_ddm   = d1 / (ke - g_ddm)

        # 敏感度（不同成長假設）
        ddm_scenarios = {}
        for label, g in [('樂觀', g_ddm + 0.02), ('基本', g_ddm), ('悲觀', max(0, g_ddm - 0.02))]:
            if ke > g:
                d1s = dps * (1 + g)
                ddm_scenarios[label] = {
                    'g':  round(g * 100, 1),
                    'iv': round(d1s / (ke - g), 2)
                }

        return {
            'available':    True,
            'dps':          round(dps, 4),
            'div_yield':    round(div_y * 100, 2),
            'g_ddm':        round(g_ddm * 100, 2),
            'ke':           round(ke * 100, 2),
            'roe':          round(roe * 100, 2) if roe else None,
            'payout':       round(payout * 100, 2) if payout else None,
            'iv_ddm':       round(iv_ddm, 2),
            'scenarios':    ddm_scenarios,
        }

    # ══════════════════════════════════════════
    # 歷史估值區間
    # ══════════════════════════════════════════
    def _calc_historical_bands(self, hist: pd.DataFrame, fin, val) -> Dict:
        if hist is None or hist.empty:
            return {'available': False}

        price = hist['Close']
        result = {'available': True}

        # ── P/E 帶 ──
        eps_list = self._eps_history()
        if eps_list:
            pe_hist = []
            for date, p in price.items():
                # 找最近的 EPS
                yr = date.year if hasattr(date, 'year') else int(str(date)[:4])
                eps = next((e['eps'] for e in reversed(eps_list) if e['year'] <= yr), None)
                if eps and eps > 0:
                    pe_hist.append(p / eps)
            if pe_hist:
                result['pe'] = {
                    'current': _sf(val.get('pe_ratio')),
                    'hist_5y': pe_hist,
                    'min':    round(min(pe_hist), 1),
                    'max':    round(max(pe_hist), 1),
                    'avg':    round(np.mean(pe_hist), 1),
                    'p25':    round(np.percentile(pe_hist, 25), 1),
                    'p75':    round(np.percentile(pe_hist, 75), 1),
                    'eps_latest': eps_list[-1]['eps'] if eps_list else None,
                }

        # ── P/B 帶 ──
        pb_current = _sf(val.get('pb_ratio'))
        result['pb'] = {
            'current': pb_current,
        }

        # ── P/S 帶 ──
        ps_current = _sf(val.get('ps_ratio'))
        result['ps'] = {
            'current': ps_current,
        }

        # ── 近5年 P/E 帶：用 EPS × P/E 倍數畫價格帶 ──
        eps_ttm = self._latest_val(fin, ['Diluted EPS', 'Basic EPS'])
        if eps_ttm and result.get('pe'):
            pe_data = result['pe']
            avg_pe  = pe_data['avg']
            p25_pe  = pe_data['p25']
            p75_pe  = pe_data['p75']
            result['price_bands'] = {
                'dates':    [str(d)[:10] for d in price.index],
                'price':    price.tolist(),
                'fair_band_low':  eps_ttm * p25_pe,
                'fair_band_high': eps_ttm * p75_pe,
                'avg_band':       eps_ttm * avg_pe,
                'eps_ttm':        eps_ttm,
            }

        return result

    def _eps_history(self) -> List[Dict]:
        """從 yfinance 取得近3年 EPS（含 FinMind 台股備援）"""
        try:
            fin = self.fetcher.get_financials_3y()  # 含 FinMind fallback
            if fin is None or fin.empty:
                return []

            # 優先：直接讀 EPS 列
            eps_row = None
            for key in ['Diluted EPS', 'Basic EPS', 'EPS']:
                if key in fin.index:
                    eps_row = fin.loc[key]
                    break

            result = []
            if eps_row is not None:
                for col in sorted(fin.columns):
                    v = _sf(eps_row.get(col))
                    if v is not None:
                        yr = col.year if hasattr(col, 'year') else int(str(col)[:4])
                        result.append({'year': yr, 'eps': v})
                if result:
                    return sorted(result, key=lambda x: x['year'])

            # 備援：Net Income ÷ 在外流通股數（台股常見）
            ni_row = None
            for key in ['Net Income', 'Net Income Common Stockholders', 'Net Income Continuous Operations']:
                if key in fin.index:
                    ni_row = fin.loc[key]
                    break
            if ni_row is None:
                return []
            shares = _sf((self._ticker.info or {}).get('sharesOutstanding'))
            if not shares or shares <= 0:
                return []
            for col in sorted(fin.columns):
                v = _sf(ni_row.get(col))
                if v is not None:
                    yr = col.year if hasattr(col, 'year') else int(str(col)[:4])
                    result.append({'year': yr, 'eps': v / shares})
            return sorted(result, key=lambda x: x['year'])
        except Exception:
            return []

    # ══════════════════════════════════════════
    # 同業估值比較
    # ══════════════════════════════════════════
    def _calc_peer_valuation(self, val) -> Dict:
        peers = self.fetcher.get_peer_tickers()
        if not peers:
            return {'available': False, 'message': '無同業資料'}

        peer_data = []
        for tk in peers[:8]:   # 最多比較8家
            try:
                info = yf.Ticker(tk).info
                pe  = _sf(info.get('trailingPE') or info.get('forwardPE'))
                pb  = _sf(info.get('priceToBook'))
                ps  = _sf(info.get('priceToSalesTrailing12Months'))
                evebitda = _sf(info.get('enterpriseToEbitda'))
                dy  = _sf(info.get('dividendYield'))
                mc  = _sf(info.get('marketCap'))
                name = info.get('shortName') or info.get('longName') or tk
                peer_data.append({
                    'ticker': tk,
                    'name':   name[:15],
                    'pe':     pe,
                    'pb':     pb,
                    'ps':     ps,
                    'ev_ebitda': evebitda,
                    'div_yield': round(dy * 100, 2) if dy else None,
                    'mkt_cap':  mc,
                })
            except Exception:
                pass

        if not peer_data:
            return {'available': False, 'message': '同業資料取得失敗'}

        # 計算同業中位數
        def peer_median(key):
            vals = [p[key] for p in peer_data if p.get(key) is not None]
            return round(np.median(vals), 2) if vals else None

        # 目標公司本身
        subject = {
            'ticker':    self.fetcher.ticker_symbol,
            'name':      self.fetcher.get_company_name()[:15],
            'pe':        _sf(val.get('pe_ratio')),
            'pb':        _sf(val.get('pb_ratio')),
            'ps':        _sf(val.get('ps_ratio')),
            'ev_ebitda': _sf(val.get('ev_ebitda')),
            'div_yield': None,
            'mkt_cap':   _sf(val.get('market_cap')),
        }
        try:
            dy = _sf((self._ticker.info or {}).get('dividendYield'))
            subject['div_yield'] = round(dy * 100, 2) if dy else None
        except Exception:
            pass

        medians = {
            'pe':        peer_median('pe'),
            'pb':        peer_median('pb'),
            'ps':        peer_median('ps'),
            'ev_ebitda': peer_median('ev_ebitda'),
        }

        # 相對估值：用同業中位數 P/E 推算合理股價
        price = _sf(val.get('current_price'))
        # 優先從 trailingEps/info 取 EPS（最快），再從財報（含 FinMind fallback）
        eps_ttm = None
        if price:
            eps_ttm = _sf((self._ticker.info or {}).get('trailingEps'))
            if not eps_ttm:
                fin_df  = self.fetcher.get_financials_3y()
                eps_ttm = self._latest_val(fin_df, ['Diluted EPS', 'Basic EPS', 'EPS'])

        peer_iv = None
        if medians['pe'] and eps_ttm and eps_ttm > 0:
            peer_iv = medians['pe'] * eps_ttm

        return {
            'available':   True,
            'subject':     subject,
            'peers':       peer_data,
            'medians':     medians,
            'peer_iv':     peer_iv,
        }

    # ══════════════════════════════════════════
    # 敏感度矩陣（WACC × 成長率）
    # ══════════════════════════════════════════
    def _calc_sensitivity(self, dcf_result: Dict, wacc_result: Dict) -> Dict:
        if not dcf_result.get('available'):
            return {'available': False}

        fcf_base = dcf_result['fcf_latest']
        shares   = _sf((self._ticker.info or {}).get('sharesOutstanding')) or 1

        wacc_center = wacc_result['wacc']
        g_center    = 0.07   # 基礎投影成長率

        wacc_range = [wacc_center - 0.02, wacc_center - 0.01,
                      wacc_center, wacc_center + 0.01, wacc_center + 0.02]
        g_range    = [0.02, 0.04, 0.06, 0.08, 0.10, 0.12]

        matrix = []
        for g in g_range:
            row = []
            for w in wacc_range:
                if w <= 0.025:   # 避免分母為零
                    row.append(None)
                    continue
                pv = 0
                fcf_t = fcf_base
                for t in range(1, 11):
                    grate = g if t <= 5 else g + (0.025 - g) * (t - 5) / 5
                    fcf_t = fcf_t * (1 + grate)
                    pv   += fcf_t / ((1 + w) ** t)
                g_t  = 0.025
                fcf_11 = fcf_t * (1 + g_t)
                tv   = fcf_11 / (w - g_t) if w > g_t else fcf_11 / 0.01
                pv  += tv / ((1 + w) ** 10)
                iv   = pv / shares if shares > 0 else None
                row.append(round(iv, 1) if iv else None)
            matrix.append(row)

        return {
            'available':   True,
            'wacc_labels': [f"{w*100:.1f}%" for w in wacc_range],
            'g_labels':    [f"{g*100:.0f}%" for g in g_range],
            'matrix':      matrix,
            'wacc_center': round(wacc_center * 100, 1),
        }

    # ══════════════════════════════════════════
    # 綜合估值與安全邊際
    # ══════════════════════════════════════════
    def _synthesize(self, dcf, ddm, hist_val, peer_val, val, wacc_result) -> Dict:
        price = _sf(val.get('current_price'))
        estimates = []

        # DCF 基本情境
        if dcf.get('available') and dcf.get('scenarios', {}).get('基本', {}).get('iv_per_share'):
            iv = dcf['scenarios']['基本']['iv_per_share']
            if iv and iv > 0:
                estimates.append({'method': 'DCF 基本情境', 'iv': iv, 'weight': 0.40})
        if dcf.get('available') and dcf.get('scenarios', {}).get('樂觀', {}).get('iv_per_share'):
            iv = dcf['scenarios']['樂觀']['iv_per_share']
            if iv and iv > 0:
                estimates.append({'method': 'DCF 樂觀情境', 'iv': iv, 'weight': 0.15})
        if dcf.get('available') and dcf.get('scenarios', {}).get('悲觀', {}).get('iv_per_share'):
            iv = dcf['scenarios']['悲觀']['iv_per_share']
            if iv and iv > 0:
                estimates.append({'method': 'DCF 悲觀情境', 'iv': iv, 'weight': 0.10})

        # DDM
        if ddm.get('available') and ddm.get('iv_ddm'):
            iv = ddm['iv_ddm']
            if iv and iv > 0:
                estimates.append({'method': 'DDM 股息折現', 'iv': iv, 'weight': 0.20})

        # 同業相對估值
        if peer_val.get('available') and peer_val.get('peer_iv'):
            iv = peer_val['peer_iv']
            if iv and iv > 0:
                estimates.append({'method': '同業 P/E 相對估值', 'iv': iv, 'weight': 0.15})

        # 歷史 P/E 均值估值
        if hist_val.get('available') and hist_val.get('pe', {}).get('avg') and hist_val.get('pe', {}).get('eps_latest'):
            avg_pe = hist_val['pe']['avg']
            eps    = hist_val['pe']['eps_latest']
            if avg_pe and eps and eps > 0 and avg_pe > 0:
                iv = avg_pe * eps
                estimates.append({'method': '歷史均值 P/E', 'iv': iv, 'weight': 0.15})

        # ── 備援：P/B 帳面價值法（當其他方法皆失效時使用）──
        if not estimates:
            try:
                info = self._ticker.info or {}
                bvps = _sf(info.get('bookValue'))
                pb   = _sf(val.get('pb_ratio')) or _sf(info.get('priceToBook'))
                # 以合理 P/B（歷史中位數或1.2×帳面）推算
                if bvps and bvps > 0:
                    # 取同業或歷史中位 P/B；若 peer_val 有數據優先用之
                    med_pb = (peer_val.get('medians', {}).get('pb')
                              if peer_val.get('available') else None)
                    target_pb = med_pb if med_pb and 0.5 < med_pb < 20 else (pb * 0.85 if pb and pb > 0 else 1.5)
                    iv = bvps * target_pb
                    if iv > 0:
                        estimates.append({'method': '帳面價值 P/B 法', 'iv': iv, 'weight': 1.0})
            except Exception:
                pass

        if not estimates or not price:
            return {
                'available': False,
                'message':   '可用估值方法不足，請確認財務資料完整性',
            }

        # 加權平均
        total_w = sum(e['weight'] for e in estimates)
        iv_weighted = sum(e['iv'] * e['weight'] for e in estimates) / total_w

        # 估值範圍
        iv_values = [e['iv'] for e in estimates]
        iv_low  = min(iv_values)
        iv_high = max(iv_values)

        # 安全邊際
        mos = (iv_weighted - price) / iv_weighted * 100 if iv_weighted > 0 else None

        # 投資結論
        if mos is not None:
            if mos >= 30:
                verdict = "顯著低估"
                color   = "#00c896"
                advice  = "目前股價提供充裕安全邊際，具備長線買入吸引力"
            elif mos >= 15:
                verdict = "略有低估"
                color   = "#5cb85c"
                advice  = "股價低於合理估值，可考慮分批布局"
            elif mos >= -10:
                verdict = "合理定價"
                color   = "#f0c040"
                advice  = "股價接近內在價值，持有為宜，等待更佳進場機會"
            elif mos >= -25:
                verdict = "略有高估"
                color   = "#ff8c00"
                advice  = "股價已超出合理估值範圍，需審慎評估"
            else:
                verdict = "明顯高估"
                color   = "#ff4444"
                advice  = "股價顯著超出各方法估值，投資風險偏高"
        else:
            verdict = "無法判斷"
            color   = "#aaa"
            advice  = "估值資料不足"

        return {
            'available':      True,
            'estimates':      estimates,
            'iv_weighted':    round(iv_weighted, 2),
            'iv_low':         round(iv_low, 2),
            'iv_high':        round(iv_high, 2),
            'current_price':  price,
            'mos':            round(mos, 1) if mos is not None else None,
            'verdict':        verdict,
            'color':          color,
            'advice':         advice,
        }

    # ══════════════════════════════════════════
    # 工具方法
    # ══════════════════════════════════════════
    def _vals(self, df, keys) -> List[Optional[float]]:
        if df is None or df.empty:
            return []
        row = self.fetcher.safe_get_row(df, keys)
        if row is None:
            return []
        cols = sorted(df.columns)
        return [_sf(row[c]) for c in cols]

    def _latest_val(self, df, keys) -> Optional[float]:
        vals = self._vals(df, keys)
        return next((v for v in reversed(vals) if v is not None), None)

    def _calc_rev_cagr(self, fin) -> Optional[float]:
        rev = self._vals(fin, ['Total Revenue', 'Revenue', 'Operating Revenue'])
        valid = [v for v in rev if v and v > 0]
        if len(valid) >= 2:
            return _cagr(valid[0], valid[-1], len(valid) - 1)
        return None

    def get_info(self) -> Dict:
        try:
            return self._ticker.info or {}
        except Exception:
            return {}

    # ══════════════════════════════════════════
    # 文字分析報告
    # ══════════════════════════════════════════
    def generate_template_report(self, result: Dict) -> str:
        syn   = result.get('synthesis', {})
        dcf   = result.get('dcf', {})
        ddm   = result.get('ddm', {})
        peer  = result.get('peer_val', {})
        wacc  = result.get('wacc', {})
        price = result.get('current_price')
        name  = self.fetcher.get_company_name()
        tk    = self.fetcher.ticker_symbol

        if not syn.get('available'):
            return f"## {name} 估值分析\n\n資料不足，無法完成完整估值。"

        iv   = syn.get('iv_weighted', 0)
        mos  = syn.get('mos', 0)
        verd = syn.get('verdict', '—')
        adv  = syn.get('advice', '')

        # DCF section
        dcf_text = ""
        if dcf.get('available'):
            w   = dcf['wacc'] * 100
            gt  = dcf['g_term'] * 100
            sc  = dcf.get('scenarios', {})
            dcf_text = f"""
### 🔢 DCF 現金流折現模型

**模型假設：**
- 折現率 (WACC)：**{w:.1f}%**（Beta={wacc.get('beta', '—')}, Ke={wacc.get('ke', 0)*100:.1f}%, Kd={wacc.get('kd', 0)*100:.1f}%）
- 永續成長率：**{gt:.1f}%**（接近長期 GDP 成長）
- 投影期間：10 年

**三情境估值：**

| 情境 | 投影成長率 | 每股內在價值 |
|------|-----------|-------------|"""
            for lbl in ['樂觀', '基本', '悲觀']:
                s = sc.get(lbl, {})
                g = s.get('g_proj', '—')
                iv_s = s.get('iv_per_share')
                iv_str = f"{iv_s:,.1f}" if iv_s and iv_s > 0 else 'N/A（FCF 為負）'
                currency = '' if self.is_tw else '$'
                dcf_text += f"\n| {lbl} | {g}% | {currency}{iv_str} |"

            dcf_text += f"""

**FCF 分析：** 最新年度自由現金流為 {(lambda v, tw: f"NT${v/1e8:.1f}億" if tw else (f"${v/1e9:.2f}B" if abs(v)>=1e9 else f"${v/1e6:.0f}M"))(dcf.get('fcf_latest',0), self.is_tw)}，
歷史 CAGR 約 {(dcf.get('hist_cagr') or 0)*100:.1f}%，
營收 CAGR 約 {(dcf.get('rev_cagr') or 0)*100:.1f}%。
"""

        # DDM section
        ddm_text = ""
        if ddm.get('available'):
            ddm_text = f"""
### 💰 DDM 股息折現模型

**模型假設：**
- 近期 DPS（年化）：**{ddm.get('dps', 0):.4f}**
- 股息殖利率：**{ddm.get('div_yield', 0):.2f}%**
- 永續股息成長率 (g)：**{ddm.get('g_ddm', 0):.2f}%**（ROE × 保留盈餘率）
- 股東必要報酬率 (Ke)：**{ddm.get('ke', 0):.2f}%**

**DDM 估算合理股價：{ddm.get('iv_ddm', 0):,.2f}**（基本情境）

"""

        # Peer section
        peer_text = ""
        if peer.get('available'):
            med = peer.get('medians', {})
            subj = peer.get('subject', {})
            currency = '' if self.is_tw else '$'
            peer_text = f"""
### 🏭 同業相對估值比較

| 指標 | {name[:12]} | 同業中位數 | 評估 |
|------|--------|----------|------|
| P/E  | {subj.get('pe') or 'N/A':.1f if subj.get('pe') else 'N/A'} | {med.get('pe') or 'N/A':.1f if med.get('pe') else 'N/A'} | {'偏高' if (subj.get('pe') or 0) > (med.get('pe') or 999) else '偏低/合理'} |
| P/B  | {subj.get('pb') or 'N/A':.2f if subj.get('pb') else 'N/A'} | {med.get('pb') or 'N/A':.2f if med.get('pb') else 'N/A'} | {'偏高' if (subj.get('pb') or 0) > (med.get('pb') or 999) else '偏低/合理'} |
| P/S  | {subj.get('ps') or 'N/A':.2f if subj.get('ps') else 'N/A'} | {med.get('ps') or 'N/A':.2f if med.get('ps') else 'N/A'} | {'偏高' if (subj.get('ps') or 0) > (med.get('ps') or 999) else '偏低/合理'} |
"""
            if peer.get('peer_iv'):
                peer_text += f"\n**依同業中位數 P/E 推算合理股價：{currency}{peer['peer_iv']:,.1f}**\n"

        # Synthesis
        currency = '' if self.is_tw else '$'
        mos_str = f"{mos:+.1f}%" if mos is not None else "N/A"
        syn_text = f"""
### 🎯 綜合估值結論

**加權平均內在價值：{currency}{iv:,.1f}**
**目前股價：{currency}{price:,.1f}**
**安全邊際：{mos_str}**
**投資判斷：{verd}**

{adv}

**各方法估值彙整：**

| 估值方法 | 合理股價 | 權重 |
|---------|---------|------|"""
        for e in syn.get('estimates', []):
            syn_text += f"\n| {e['method']} | {currency}{e['iv']:,.1f} | {e['weight']*100:.0f}% |"

        syn_text += f"""

**風險提示：**
- DCF 模型對成長率與折現率假設高度敏感，±1% 變化可造成估值大幅波動
- 本估值基於過去財務數據推算，未來業績不保證重演
- 市場情緒、產業景氣、黑天鵝事件均非量化模型能捕捉
- **本報告僅供研究參考，不構成投資建議**
"""

        full_report = f"## 📊 {name}（{tk}）內在價值評估報告\n\n"
        full_report += f"> 估值日期：{datetime.now().strftime('%Y-%m-%d')}  ·  目前股價：{currency}{price:,.1f}\n\n"
        full_report += dcf_text + ddm_text + peer_text + syn_text

        return full_report

    def generate_ai_report(self, result: Dict, api_key: str) -> Optional[str]:
        try:
            import anthropic
            syn   = result.get('synthesis', {})
            dcf   = result.get('dcf', {})
            ddm   = result.get('ddm', {})
            peer  = result.get('peer_val', {})
            name  = self.fetcher.get_company_name()
            tk    = self.fetcher.ticker_symbol
            price = result.get('current_price', 0)
            currency = 'TWD' if self.is_tw else 'USD'

            prompt = f"""你是一位資深價值投資分析師。請根據以下量化估值數據，為 {name}（{tk}）撰寫一份完整的內在價值評估報告（繁體中文，約 1500 字）。

**基本資訊：**
- 目前股價：{price:,.2f} {currency}
- 綜合估值結論：{syn.get('verdict', 'N/A')}
- 加權內在價值：{syn.get('iv_weighted', 0):,.2f} {currency}
- 安全邊際：{syn.get('mos', 'N/A')}%

**DCF 模型：**
- WACC：{result.get('wacc', {}).get('wacc', 0)*100:.1f}%
- 三情境 IV：{[f"{k}: {v.get('iv_per_share', 0):,.0f}" for k, v in dcf.get('scenarios', {}).items() if v.get('iv_per_share')]}

**DDM 模型：** {'適用，IV=' + str(ddm.get('iv_ddm', 0)) if ddm.get('available') else '不適用（不配息）'}

**同業估值：**
- 同業中位數 P/E：{peer.get('medians', {}).get('pe', 'N/A')}
- 同業中位數 P/B：{peer.get('medians', {}).get('pb', 'N/A')}

報告請包含以下章節：
1. 執行摘要（結論與投資評級）
2. DCF 估值分析（假設說明、各情境解讀）
3. 相對估值分析（與同業比較）
4. 歷史估值位階（目前處於歷史高/中/低位）
5. 安全邊際與風險（加碼條件、減碼條件）
6. 價值投資者觀點（長期持有論點）"""

            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2500,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text
        except Exception as e:
            return None
