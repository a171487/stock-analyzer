"""
功能一：全面財務健康檢查
- 3年營收成長率、毛利率、淨利率趨勢
- 現金流狀況與負債比
- 同業比較
- 估值合理性（P/E、P/B、P/S）
- 投資風險等級評估
"""

import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional, Any, Tuple
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.data_fetcher import StockDataFetcher


def _safe_float(val) -> Optional[float]:
    try:
        v = float(val)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


class FinancialHealthChecker:
    """執行完整的財務健康分析，並輸出圖表資料與文字報告"""

    def __init__(self, fetcher: StockDataFetcher):
        self.fetcher = fetcher

    # ══════════════════════════════════════════
    # 主入口
    # ══════════════════════════════════════════
    def run_full_analysis(self) -> Dict:
        fin = self.fetcher.get_financials_3y()
        bs  = self.fetcher.get_balance_sheet_3y()
        cf  = self.fetcher.get_cashflow_3y()
        val = self.fetcher.get_valuation_metrics()

        revenue_data   = self._build_revenue_data(fin)
        margin_data    = self._build_margin_data(fin)
        cashflow_data  = self._build_cashflow_data(cf)
        valuation_data = self._build_valuation_data(val)
        debt_data      = self._build_debt_data(bs, fin)
        peer_data      = self._fetch_peer_data()

        key_metrics = self._calc_key_metrics(fin, bs, cf, val, revenue_data, margin_data)
        radar_scores, risk_score, risk_level = self._calc_risk(key_metrics, val)
        analysis = self._generate_analysis(key_metrics, revenue_data, margin_data,
                                           cashflow_data, debt_data, valuation_data,
                                           peer_data, risk_score, risk_level)

        return {
            'key_metrics':    key_metrics,
            'revenue_data':   revenue_data,
            'margin_data':    margin_data,
            'cashflow_data':  cashflow_data,
            'valuation_data': valuation_data,
            'debt_data':      debt_data,
            'peer_data':      peer_data,
            'analysis':       analysis,
            'risk_score':     risk_score,
            'risk_level':     risk_level,
            'radar_scores':   radar_scores,
        }

    # ══════════════════════════════════════════
    # 資料整理
    # ══════════════════════════════════════════
    def _get_sorted_years(self, df: pd.DataFrame) -> List[str]:
        """取得年份字串清單（由舊到新）"""
        if df is None or df.empty:
            return []
        cols = sorted(df.columns, reverse=False)  # 舊→新
        return [str(c.year) if hasattr(c, 'year') else str(c) for c in cols]

    def _extract_series(self, df: pd.DataFrame, keys: List[str]) -> List[Optional[float]]:
        """從 DataFrame 擷取指定列（嘗試多個鍵），回傳由舊到新的數列"""
        if df is None or df.empty:
            return []
        row = self.fetcher.safe_get_row(df, keys)
        if row is None:
            return []
        cols = sorted(row.index, reverse=False)
        return [_safe_float(row[c]) for c in cols]

    def _scale(self, values: List[Optional[float]]) -> Tuple[List[Optional[float]], str]:
        """自動選擇顯示單位（T/B/M/K）"""
        valid = [v for v in values if v is not None]
        if not valid:
            return values, ''
        max_v = max(abs(v) for v in valid)
        if max_v >= 1e12:
            return [v/1e12 if v else v for v in values], 'T'
        if max_v >= 1e9:
            return [v/1e9 if v else v for v in values], 'B'
        if max_v >= 1e6:
            return [v/1e6 if v else v for v in values], 'M'
        if max_v >= 1e3:
            return [v/1e3 if v else v for v in values], 'K'
        return values, ''

    # ── 營收 ──
    def _build_revenue_data(self, fin: pd.DataFrame) -> Dict:
        years = self._get_sorted_years(fin)
        revenue = self._extract_series(fin, ['Total Revenue', 'Revenue', 'TotalRevenue'])
        scaled, unit = self._scale(revenue)
        return {
            'years': years[-4:],
            'revenue': scaled[-4:],
            'unit': unit,
            'currency': 'NT$' if self.fetcher.stock_type == 'TW' else '$',
        }

    # ── 獲利率 ──
    def _build_margin_data(self, fin: pd.DataFrame) -> Dict:
        years = self._get_sorted_years(fin)

        revenue = self._extract_series(fin, ['Total Revenue', 'Revenue'])
        gross   = self._extract_series(fin, ['Gross Profit', 'GrossProfit'])
        op_inc  = self._extract_series(fin, ['Operating Income', 'EBIT'])
        net_inc = self._extract_series(fin, ['Net Income', 'NetIncome', 'Net Income Common Stockholders'])

        def pct(numerator, denominator):
            result = []
            for n, d in zip(numerator, denominator):
                if n is not None and d and d != 0:
                    result.append(n / d * 100)
                else:
                    result.append(None)
            return result

        n = min(len(revenue), len(gross), len(op_inc), len(net_inc), len(years))
        return {
            'years':            years[-n:],
            'gross_margin':     pct(gross, revenue)[-n:],
            'operating_margin': pct(op_inc, revenue)[-n:],
            'net_margin':       pct(net_inc, revenue)[-n:],
        }

    # ── 現金流 ──
    def _build_cashflow_data(self, cf: pd.DataFrame) -> Dict:
        years = self._get_sorted_years(cf)
        op_cf  = self._extract_series(cf, ['Operating Cash Flow', 'Cash Flow From Continuing Operating Activities', 'OperatingActivities'])
        inv_cf = self._extract_series(cf, ['Investing Cash Flow', 'Cash Flow From Continuing Investing Activities', 'InvestingActivities'])
        fcf    = self._extract_series(cf, ['Free Cash Flow', 'FreeCashFlow'])

        # 若無 FCF 直接計算
        if not fcf and op_cf:
            capex = self._extract_series(cf, ['Capital Expenditure', 'Purchase Of Property Plant And Equipment'])
            if capex:
                n = min(len(op_cf), len(capex))
                fcf = [(o + c if o is not None and c is not None else None)
                       for o, c in zip(op_cf[:n], capex[:n])]

        all_vals = op_cf + inv_cf + (fcf or [])
        _, unit = self._scale([v for v in all_vals if v is not None])

        def scale_list(lst):
            divisor = {'T': 1e12, 'B': 1e9, 'M': 1e6, 'K': 1e3}.get(unit, 1)
            return [v/divisor if v is not None else None for v in lst]

        n = min(len(years), len(op_cf) if op_cf else 0, 4) if op_cf else len(years)
        return {
            'years':        years[-n:],
            'operating_cf': scale_list(op_cf[-n:]) if op_cf else [],
            'investing_cf': scale_list(inv_cf[-n:]) if inv_cf else [],
            'free_cf':      scale_list(fcf[-n:]) if fcf else [],
            'unit':     unit,
            'currency': 'NT$' if self.fetcher.stock_type == 'TW' else '$',
        }

    # ── 估值 ──
    def _build_valuation_data(self, val: Dict) -> Dict:
        name = self.fetcher.get_company_name()
        return {
            'name': name[:8],
            'pe':   _safe_float(val.get('pe_trailing') or val.get('pe_forward')),
            'pb':   _safe_float(val.get('pb_ratio')),
            'ps':   _safe_float(val.get('ps_ratio')),
        }

    # ── 負債 ──
    def _build_debt_data(self, bs: pd.DataFrame, fin: pd.DataFrame) -> Dict:
        total_assets = self._extract_series(bs, ['Total Assets', 'TotalAssets'])
        total_liab   = self._extract_series(bs, [
            'Total Liabilities Net Minority Interest',
            'Total Liab', 'TotalLiabilities', 'Total Liabilities'
        ])
        current_assets = self._extract_series(bs, ['Current Assets', 'Total Current Assets'])
        current_liab   = self._extract_series(bs, ['Current Liabilities', 'Total Current Liabilities'])
        long_debt      = self._extract_series(bs, ['Long Term Debt', 'LongTermDebt'])
        net_income     = self._extract_series(fin, ['Net Income', 'NetIncome'])

        years = self._get_sorted_years(bs)

        # 計算比率（取最新一期）
        def latest(lst): return lst[-1] if lst else None

        la = latest(total_assets)
        ll = latest(total_liab)
        ca = latest(current_assets)
        cl = latest(current_liab)
        ld = latest(long_debt)

        debt_ratio    = (ll / la * 100) if la and ll else None
        current_ratio = (ca / cl) if ca and cl and cl != 0 else None
        debt_to_equity = None
        if ll is not None and la and ll:
            equity = la - ll
            debt_to_equity = (ld / equity) if equity and equity != 0 and ld else None

        return {
            'years':         years[-4:],
            'total_assets':  total_assets[-4:],
            'total_liab':    total_liab[-4:],
            'debt_ratio':    debt_ratio,
            'current_ratio': current_ratio,
            'debt_to_equity': debt_to_equity,
            'long_debt':     latest(long_debt),
        }

    # ══════════════════════════════════════════
    # 核心指標計算
    # ══════════════════════════════════════════
    def _calc_key_metrics(self, fin, bs, cf, val, revenue_data, margin_data) -> Dict:
        # ── 營收 CAGR ──
        rev = [v for v in revenue_data.get('revenue', []) if v is not None]
        revenue_cagr = None
        if len(rev) >= 2:
            years_n = len(rev) - 1
            if rev[0] and rev[0] != 0:
                revenue_cagr = ((rev[-1] / rev[0]) ** (1 / years_n) - 1) * 100

        # ── 最新毛利率 / 淨利率 / 營業利益率 ──
        def latest_valid(lst):
            for v in reversed(lst):
                if v is not None:
                    return v
            return None

        latest_gm  = latest_valid(margin_data.get('gross_margin', []))
        latest_om  = latest_valid(margin_data.get('operating_margin', []))
        latest_nm  = latest_valid(margin_data.get('net_margin', []))

        # ── 估值 ──
        pe = _safe_float(val.get('pe_trailing') or val.get('pe_forward'))
        pb = _safe_float(val.get('pb_ratio'))
        ps = _safe_float(val.get('ps_ratio'))

        # ── 負債比 ──
        bs_data = self._build_debt_data(bs, fin)
        debt_ratio    = bs_data.get('debt_ratio')
        current_ratio = bs_data.get('current_ratio')

        # ── 自由現金流 ──
        cf_data = self._build_cashflow_data(cf)
        fcf_list = [v for v in cf_data.get('free_cf', []) if v is not None]
        latest_fcf = fcf_list[-1] if fcf_list else None
        fcf_positive = sum(1 for v in fcf_list if v and v > 0)

        # ── ROE / ROA ──
        roe = _safe_float(val.get('roe'))
        roa = _safe_float(val.get('roa'))
        if roe is not None: roe *= 100
        if roa is not None: roa *= 100

        return {
            'revenue_cagr_3y':     revenue_cagr,
            'latest_gross_margin': latest_gm,
            'latest_op_margin':    latest_om,
            'latest_net_margin':   latest_nm,
            'pe_ratio':            pe,
            'pb_ratio':            pb,
            'ps_ratio':            ps,
            'debt_ratio':          debt_ratio,
            'current_ratio':       current_ratio,
            'debt_to_equity':      bs_data.get('debt_to_equity'),
            'latest_fcf':          latest_fcf,
            'fcf_positive_years':  fcf_positive,
            'roe':                 roe,
            'roa':                 roa,
            'beta':                _safe_float(val.get('beta')),
            'dividend_yield':      _safe_float(val.get('dividend_yield')),
            'current_price':       _safe_float(val.get('current_price')),
            '52w_high':            _safe_float(val.get('52w_high')),
            '52w_low':             _safe_float(val.get('52w_low')),
        }

    # ══════════════════════════════════════════
    # 同業資料
    # ══════════════════════════════════════════
    def _fetch_peer_data(self) -> List[Dict]:
        peers = self.fetcher.get_peer_tickers()
        result = []
        for p in peers[:4]:
            try:
                t = yf.Ticker(p)
                info = t.fast_info if hasattr(t, 'fast_info') else {}
                full_info = t.info or {}
                merged = {**(info.__dict__ if hasattr(info, '__dict__') else {}), **full_info}

                name = merged.get('longName') or merged.get('shortName') or p
                pe   = _safe_float(merged.get('trailingPE') or merged.get('forwardPE'))
                pb   = _safe_float(merged.get('priceToBook'))
                ps   = _safe_float(merged.get('priceToSalesTrailing12Months'))
                gm   = _safe_float(merged.get('grossMargins'))
                nm   = _safe_float(merged.get('profitMargins'))
                roe  = _safe_float(merged.get('returnOnEquity'))

                result.append({
                    'ticker': p,
                    'name':   name[:8],
                    'pe':  pe,
                    'pb':  pb,
                    'ps':  ps,
                    'gross_margin': gm * 100 if gm else None,
                    'net_margin':   nm * 100 if nm else None,
                    'roe':          roe * 100 if roe else None,
                })
            except Exception:
                continue
        return result

    # ══════════════════════════════════════════
    # 風險評分
    # ══════════════════════════════════════════
    def _calc_risk(self, m: Dict, val: Dict) -> Tuple[Dict, int, str]:
        scores = {}

        # 1. 成長力 (0-100)
        cagr = m.get('revenue_cagr_3y')
        if cagr is not None:
            if cagr >= 20:   scores['成長力'] = 95
            elif cagr >= 10: scores['成長力'] = 80
            elif cagr >= 5:  scores['成長力'] = 65
            elif cagr >= 0:  scores['成長力'] = 50
            else:            scores['成長力'] = 25
        else:
            scores['成長力'] = 50

        # 2. 獲利力 (0-100)
        gm = m.get('latest_gross_margin')
        nm = m.get('latest_net_margin')
        g_score = 50
        if gm is not None:
            if gm >= 50:   g_score = 95
            elif gm >= 35: g_score = 80
            elif gm >= 20: g_score = 65
            elif gm >= 10: g_score = 50
            else:          g_score = 30
        if nm is not None:
            n_bonus = 0
            if nm >= 20:   n_bonus = 15
            elif nm >= 10: n_bonus = 8
            elif nm >= 5:  n_bonus = 3
            elif nm < 0:   n_bonus = -20
            g_score = min(100, max(0, g_score + n_bonus))
        scores['獲利力'] = g_score

        # 3. 現金流 (0-100)
        fcf_yrs = m.get('fcf_positive_years', 0)
        if fcf_yrs >= 3:   scores['現金流'] = 90
        elif fcf_yrs >= 2: scores['現金流'] = 70
        elif fcf_yrs >= 1: scores['現金流'] = 50
        else:              scores['現金流'] = 30

        # 4. 財務健全 (0-100)
        dr = m.get('debt_ratio')
        cr = m.get('current_ratio')
        d_score = 60
        if dr is not None:
            if dr <= 30:   d_score = 95
            elif dr <= 50: d_score = 75
            elif dr <= 70: d_score = 50
            else:          d_score = 25
        if cr is not None:
            if cr >= 2:    d_score = min(100, d_score + 10)
            elif cr >= 1:  pass
            else:          d_score = max(0, d_score - 20)
        scores['財務健全'] = d_score

        # 5. 估值合理 (0-100)
        pe = m.get('pe_ratio')
        pb = m.get('pb_ratio')
        v_score = 60
        if pe is not None:
            if pe < 0:     v_score = 30   # 虧損
            elif pe <= 15: v_score = 90
            elif pe <= 25: v_score = 75
            elif pe <= 40: v_score = 55
            else:          v_score = 35
        if pb is not None:
            if pb < 1:     v_score = min(100, v_score + 10)
            elif pb > 10:  v_score = max(0, v_score - 15)
        scores['估值合理'] = v_score

        total = int(np.mean(list(scores.values())))

        if total >= 80:    level = "優質"
        elif total >= 65:  level = "良好"
        elif total >= 50:  level = "普通"
        elif total >= 35:  level = "偏高風險"
        else:              level = "高風險"

        return scores, total, level

    # ══════════════════════════════════════════
    # 文字分析生成（專業分析師語言）
    # ══════════════════════════════════════════
    def _generate_analysis(self, m, rev_data, margin_data, cf_data,
                            debt_data, val_data, peer_data,
                            risk_score, risk_level) -> Dict[str, str]:
        name   = self.fetcher.get_company_name()
        ticker = self.fetcher.ticker_symbol
        ccy    = 'NT$' if self.fetcher.stock_type == 'TW' else '$'

        # ── 1. 營收與獲利 ──
        cagr = m.get('revenue_cagr_3y')
        gm   = m.get('latest_gross_margin')
        nm   = m.get('latest_net_margin')
        om   = m.get('latest_op_margin')

        rev_txt = ""
        if cagr is not None:
            trend = "強勁成長" if cagr > 15 else "穩健成長" if cagr > 5 else "溫和成長" if cagr > 0 else "下滑"
            rev_txt += f"**{name}** 過去三年營收年複合成長率（CAGR）為 **{cagr:+.1f}%**，整體呈現{trend}態勢。\n\n"
        else:
            rev_txt += f"**{name}** 的完整年度營收資料暫時無法取得。\n\n"

        if gm is not None:
            gm_eval = "極高" if gm > 50 else "高" if gm > 35 else "中等" if gm > 20 else "偏低"
            rev_txt += f"- **毛利率**：{gm:.1f}%（{gm_eval}），"
            if gm > 40:
                rev_txt += "顯示公司具備強大的定價能力或技術壁壘。\n"
            elif gm > 20:
                rev_txt += "在業界屬中等水準，維持一定的競爭力。\n"
            else:
                rev_txt += "偏低，需關注成本控制及產品組合改善空間。\n"

        if om is not None:
            rev_txt += f"- **營業利益率**：{om:.1f}%，"
            rev_txt += "費用控管良好。\n" if om > 15 else "仍有費用優化空間。\n"

        if nm is not None:
            rev_txt += f"- **淨利率**：{nm:.1f}%，"
            if nm > 20:
                rev_txt += "獲利能力卓越，本業與業外收益均表現穩定。\n"
            elif nm > 5:
                rev_txt += "獲利穩健，財務轉化效率良好。\n"
            elif nm > 0:
                rev_txt += "薄利多銷模式，需持續觀察改善趨勢。\n"
            else:
                rev_txt += "⚠️ 目前處於虧損狀態，需密切追蹤轉虧為盈時程。\n"

        # ── 2. 現金流與負債 ──
        dr = m.get('debt_ratio')
        cr = m.get('current_ratio')
        fcf_yrs = m.get('fcf_positive_years', 0)
        dte = m.get('debt_to_equity')

        cf_txt = ""
        if fcf_yrs >= 3:
            cf_txt += "✅ **自由現金流連續正值**：近3年持續產生正自由現金流，顯示公司本業賺錢能力強，不依賴外部資金即可支應營運與資本支出。\n\n"
        elif fcf_yrs >= 1:
            cf_txt += f"⚠️ 自由現金流在分析期間有 {fcf_yrs} 年為正值，需注意現金流穩定性。\n\n"
        else:
            cf_txt += "❌ 近年自由現金流為負，公司需外部融資支撐擴張，若為高速成長期屬正常，但需追蹤改善時程。\n\n"

        if dr is not None:
            dr_eval = "偏低（財務穩健）" if dr < 40 else "中等" if dr < 60 else "偏高（需注意）"
            cf_txt += f"- **負債比率**：{dr:.1f}%（{dr_eval}）\n"
        if cr is not None:
            cr_eval = "流動性充足" if cr >= 2 else "尚可" if cr >= 1 else "⚠️ 短期流動性偏緊"
            cf_txt += f"- **流動比率**：{cr:.2f}x（{cr_eval}，一般認為 ≥ 2 為健康）\n"
        if dte is not None:
            cf_txt += f"- **長期負債/股東權益**：{dte:.2f}x（越低代表財務槓桿越保守）\n"

        # ── 3. 估值分析 ──
        pe = m.get('pe_ratio')
        pb = m.get('pb_ratio')
        ps = m.get('ps_ratio')

        val_txt = f"以下為 **{name}** 目前市場給予的估值倍數：\n\n"

        if pe is not None and pe > 0:
            if pe < 15:
                pe_eval = "✅ 低估值，具吸引力"
            elif pe < 25:
                pe_eval = "合理估值"
            elif pe < 40:
                pe_eval = "⚠️ 估值偏高，反映市場成長期待"
            else:
                pe_eval = "❌ 估值極高，具投機成分"
            val_txt += f"| **P/E（本益比）** | {pe:.1f}x | {pe_eval} |\n"
        elif pe is not None and pe <= 0:
            val_txt += f"| **P/E（本益比）** | N/A | 目前虧損，P/E 無意義 |\n"

        val_txt = "| 指標 | 數值 | 評估 |\n|---|---|---|\n" + val_txt.split("\n\n", 1)[1]
        val_txt = f"以下為 **{name}** 目前市場給予的估值倍數：\n\n| 指標 | 數值 | 評估 |\n|---|---|---|\n"

        if pe is not None and pe > 0:
            pe_eval = "✅ 便宜" if pe < 15 else "合理" if pe < 25 else "⚠️ 偏貴" if pe < 40 else "❌ 極貴"
            val_txt += f"| P/E 本益比 | {pe:.1f}x | {pe_eval} |\n"
        if pb is not None:
            pb_eval = "✅ 低於淨值，潛力股" if pb < 1 else "合理" if pb < 3 else "⚠️ 偏高" if pb < 10 else "❌ 極高"
            val_txt += f"| P/B 股價淨值比 | {pb:.1f}x | {pb_eval} |\n"
        if ps is not None:
            ps_eval = "✅ 低" if ps < 2 else "合理" if ps < 5 else "⚠️ 偏高" if ps < 10 else "❌ 極高"
            val_txt += f"| P/S 市銷率 | {ps:.1f}x | {ps_eval} |\n"

        val_txt += "\n> 📌 **提醒**：估值高低需搭配成長率判斷，高速成長股的高估值可能合理，停滯型企業的高估值則風險較大。\n"

        # ── 4. 同業比較 ──
        peer_txt = ""
        if peer_data:
            peer_txt = f"與同業相比，**{name}** 的表現如下：\n\n| 公司 | P/E | P/B | 毛利率 | 淨利率 |\n|---|---|---|---|---|\n"
            me = {
                'name': name[:8],
                'pe':   pe,
                'pb':   pb,
                'gross_margin': m.get('latest_gross_margin'),
                'net_margin':   m.get('latest_net_margin'),
            }
            for d in [me] + peer_data:
                n  = d.get('name', '-')
                p  = f"{d['pe']:.1f}x" if d.get('pe') else '-'
                b  = f"{d['pb']:.1f}x" if d.get('pb') else '-'
                g  = f"{d['gross_margin']:.1f}%" if d.get('gross_margin') else '-'
                nm_ = f"{d['net_margin']:.1f}%" if d.get('net_margin') else '-'
                bold = "**" if d['name'] == me['name'] else ""
                peer_txt += f"| {bold}{n}{bold} | {p} | {b} | {g} | {nm_} |\n"

            peer_txt += "\n**同業優劣勢分析**：\n"
            if gm is not None:
                peer_gms = [d.get('gross_margin') for d in peer_data if d.get('gross_margin')]
                if peer_gms:
                    avg_gm = np.mean(peer_gms)
                    if gm > avg_gm + 5:
                        peer_txt += f"- ✅ 毛利率高於同業均值 {avg_gm:.1f}%，競爭優勢明顯\n"
                    elif gm < avg_gm - 5:
                        peer_txt += f"- ⚠️ 毛利率低於同業均值 {avg_gm:.1f}%，成本結構需改善\n"
                    else:
                        peer_txt += f"- ➡️ 毛利率與同業均值（{avg_gm:.1f}%）相近\n"
        else:
            peer_txt = "同業比較資料目前無法自動取得，建議手動對照競品公司。"

        # ── 5. 投資風險評估 ──
        emoji_map = {"優質": "🟢", "良好": "🔵", "普通": "🟡", "偏高風險": "🟠", "高風險": "🔴"}
        emoji = emoji_map.get(risk_level, "⚪")

        risk_txt = f"## {emoji} 投資風險等級：{risk_level}（綜合評分 {risk_score}/100）\n\n"
        risk_txt += "### 各維度評估\n\n"

        if cagr is not None:
            risk_txt += f"**📈 成長力**：營收CAGR {cagr:+.1f}%，"
            risk_txt += "成長動能強勁 ✅\n" if cagr > 10 else "成長穩健 ✅\n" if cagr > 0 else "成長趨緩，需追蹤 ⚠️\n"

        if gm is not None:
            risk_txt += f"**💰 獲利力**：毛利率 {gm:.1f}%，"
            risk_txt += "護城河優勢明顯 ✅\n" if gm > 40 else "獲利尚可 ✅\n" if gm > 20 else "獲利偏弱 ⚠️\n"

        if dr is not None:
            risk_txt += f"**🏦 財務健全**：負債比 {dr:.1f}%，"
            risk_txt += "財務穩健 ✅\n" if dr < 50 else "財務槓桿偏高 ⚠️\n"

        risk_txt += f"**💵 現金流**：近期自由現金流 "
        risk_txt += "持續正值，財務自給自足 ✅\n" if fcf_yrs >= 3 else f"有{fcf_yrs}年為正，需持續觀察 ⚠️\n"

        if pe is not None:
            risk_txt += f"**📊 估值**：P/E {pe:.1f}x，"
            risk_txt += "估值合理 ✅\n" if pe < 25 else "估值偏高，需等待回調機會 ⚠️\n"

        risk_txt += "\n### 💡 給一般投資人的建議\n\n"
        if risk_level == "優質":
            risk_txt += "此股票基本面優異，適合長期持有或定期定額投入。建議在市場回檔時分批布局，降低進場成本。"
        elif risk_level == "良好":
            risk_txt += "基本面良好，具備長期投資價值。建議搭配技術面尋找適當買點，注意市場情緒對估值的影響。"
        elif risk_level == "普通":
            risk_txt += "基本面普通，並非市場中的頂尖選手。建議與更優質的同業比較後再做決策，或等待業績改善訊號。"
        elif risk_level == "偏高風險":
            risk_txt += "存在一定財務或估值風險，建議進階投資人才考慮，並嚴格控制部位大小（建議不超過投資組合的5%）。"
        else:
            risk_txt += "⚠️ 高風險標的，財務結構或獲利能力存在明顯隱憂。建議一般投資人迴避，等待公司明顯改善後再評估。"

        risk_txt += "\n\n> ⚠️ **免責聲明**：本分析僅供參考，不構成投資建議。投資有風險，請自行評估後決策。"

        return {
            'revenue_profit': rev_txt,
            'cashflow_debt':  cf_txt,
            'valuation':      val_txt,
            'peer_comparison': peer_txt,
            'risk_assessment': risk_txt,
        }
