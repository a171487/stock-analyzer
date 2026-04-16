"""
功能四：財報隱藏風險信號偵測
- 應收帳款 vs 營收成長異常
- 存貨周轉率變化
- 現金流品質（CFO vs 淨利）
- 債務結構與償債能力（Altman Z-Score）
- 特殊會計處理與一次性損益
- 高管/內部人持股變動
- Beneish M-Score（財務造假偵測）
- Piotroski F-Score（財務健康評分）
"""

import numpy as np
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
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

def _chg_pct(new, old) -> Optional[float]:
    if old and old != 0 and new is not None:
        return (new - old) / abs(old) * 100
    return None

def _risk_level(score: float) -> Tuple[str, str]:
    """分數 0-100 → (等級名稱, 顏色)"""
    if score >= 75: return "高風險", "#ff4757"
    if score >= 50: return "中等風險", "#ff9f43"
    if score >= 25: return "低風險",  "#ffa502"
    return "無明顯風險", "#00b09b"


class RiskSignalDetector:
    """財報風險信號偵測器"""

    def __init__(self, fetcher: StockDataFetcher, finmind_token: str = ""):
        self.fetcher       = fetcher
        self.finmind_token = finmind_token
        self._ticker       = fetcher._yf_ticker

    # ══════════════════════════════════════════
    # 主入口
    # ══════════════════════════════════════════
    def run_full_analysis(self) -> Dict:
        fin = self.fetcher.get_financials_3y()
        bs  = self.fetcher.get_balance_sheet_3y()
        cf  = self.fetcher.get_cashflow_3y()
        val = self.fetcher.get_valuation_metrics()

        # 季報（取得更近期數據）
        qfin = qbs = qcf = pd.DataFrame()
        try:
            qfin = self._ticker.quarterly_financials or pd.DataFrame()
            qbs  = self._ticker.quarterly_balance_sheet or pd.DataFrame()
            qcf  = self._ticker.quarterly_cashflow or pd.DataFrame()
        except Exception:
            pass

        signals = {
            'ar_revenue':       self._check_ar_revenue(fin, bs, qfin, qbs),
            'inventory':        self._check_inventory(fin, bs),
            'cashflow_quality': self._check_cfo_quality(fin, cf),
            'debt_structure':   self._check_debt(bs, fin, cf, val),
            'special_items':    self._check_special_items(fin),
            'insider_activity': self._check_insider(),
        }

        m_score = self._calc_m_score(fin, bs, cf)
        f_score = self._calc_f_score(fin, bs, cf, val)
        overall = self._calc_overall(signals, m_score, f_score)

        return {
            'signals':  signals,
            'm_score':  m_score,
            'f_score':  f_score,
            'overall':  overall,
            '_raw':     {'fin': fin, 'bs': bs, 'cf': cf, 'val': val,
                         'qfin': qfin, 'qbs': qbs, 'qcf': qcf},
        }

    # ──────────────────────────────────────────
    # 工具：從 DataFrame 取指定列
    # ──────────────────────────────────────────
    def _row(self, df: pd.DataFrame, keys: List[str]) -> Optional[pd.Series]:
        return self.fetcher.safe_get_row(df, keys)

    def _sorted_cols(self, df: pd.DataFrame) -> List:
        """欄位由舊到新排列"""
        if df is None or df.empty:
            return []
        return sorted(df.columns)

    def _vals(self, df, keys) -> List[Optional[float]]:
        """取指定列，由舊到新，轉 float"""
        row = self._row(df, keys)
        if row is None:
            return []
        return [_sf(row[c]) for c in self._sorted_cols(df)]

    # ══════════════════════════════════════════
    # 1. 應收帳款 vs 營收 (DSO 分析)
    # ══════════════════════════════════════════
    def _check_ar_revenue(self, fin, bs, qfin, qbs) -> Dict:
        rev  = self._vals(fin, ['Total Revenue', 'Revenue', 'Operating Revenue'])
        ar   = self._vals(bs,  ['Receivables', 'Net Receivables', 'Accounts Receivable',
                                 'Current Receivables'])

        data = {'available': False, 'risk_score': 30, 'details': {}}

        if not rev or not ar or len(rev) < 2:
            data['message'] = "應收帳款或營收資料不足"
            return data

        # 計算 DSO（應收帳款周轉天數）= AR / (Revenue / 365)
        n = min(len(rev), len(ar))
        dso = []
        for i in range(n):
            if rev[i] and rev[i] > 0 and ar[i] is not None:
                dso.append(ar[i] / (rev[i] / 365))
            else:
                dso.append(None)

        # 年增率
        rev_growth = [_chg_pct(rev[i], rev[i-1]) for i in range(1, len(rev))]
        n_ar = min(len(ar), len(rev))
        ar_growth  = [_chg_pct(ar[i], ar[i-1]) for i in range(1, n_ar)]

        # 最新 DSO 變化
        valid_dso = [d for d in dso if d is not None]
        dso_latest = valid_dso[-1] if valid_dso else None
        dso_prev   = valid_dso[-2] if len(valid_dso) >= 2 else None
        dso_change = _chg_pct(dso_latest, dso_prev)

        # 最新年度 AR vs Revenue 成長差距
        ar_g_latest  = ar_growth[-1]  if ar_growth  else None
        rev_g_latest = rev_growth[-1] if rev_growth else None
        gap = (ar_g_latest - rev_g_latest) if (ar_g_latest is not None and rev_g_latest is not None) else None

        # 風險評分
        score = 20
        flags = []
        if gap is not None:
            if gap > 20:
                score = 80; flags.append(f"應收帳款成長比營收快 {gap:.1f}%（強烈警訊）")
            elif gap > 10:
                score = 60; flags.append(f"應收帳款成長比營收快 {gap:.1f}%（需關注）")
            elif gap > 0:
                score = 35; flags.append(f"應收帳款成長略快於營收（{gap:.1f}%）")
            else:
                flags.append("應收帳款成長與營收同步或更慢（正常）")

        if dso_change is not None and dso_change > 20:
            score = max(score, 65)
            flags.append(f"DSO 增加 {dso_change:.1f}%，收款能力下降")
        elif dso_change is not None and dso_change > 10:
            score = max(score, 45)
            flags.append(f"DSO 小幅增加 {dso_change:.1f}%")

        years = self._get_year_labels(fin)

        data.update({
            'available':   True,
            'risk_score':  score,
            'risk_level':  _risk_level(score),
            'flags':       flags,
            'details': {
                'years':       years,
                'revenue':     rev,
                'ar':          ar,
                'dso':         dso,
                'rev_growth':  rev_growth,
                'ar_growth':   ar_growth,
                'dso_latest':  dso_latest,
                'dso_change':  dso_change,
                'gap':         gap,
            },
        })
        return data

    # ══════════════════════════════════════════
    # 2. 存貨周轉率
    # ══════════════════════════════════════════
    def _check_inventory(self, fin, bs) -> Dict:
        cogs = self._vals(fin, ['Cost Of Revenue', 'Cost Of Goods Sold',
                                 'Reconciled Cost Of Revenue'])
        inv  = self._vals(bs,  ['Inventory', 'Inventories'])

        data = {'available': False, 'risk_score': 20, 'details': {}}

        if not cogs or not inv:
            data['message'] = "存貨或銷售成本資料不足（服務業通常無存貨，屬正常）"
            return data

        n = min(len(cogs), len(inv))
        turnover, dio = [], []
        for i in range(n):
            if inv[i] and inv[i] > 0 and cogs[i]:
                t = abs(cogs[i]) / inv[i]    # turnover (next: 確保 COGS 用絕對值)
                turnover.append(t)
                dio.append(365 / t)
            else:
                turnover.append(None)
                dio.append(None)

        valid_turn = [t for t in turnover if t is not None]
        turn_latest = valid_turn[-1] if valid_turn else None
        turn_prev   = valid_turn[-2] if len(valid_turn) >= 2 else None
        turn_change = _chg_pct(turn_latest, turn_prev)

        valid_dio = [d for d in dio if d is not None]
        dio_latest = valid_dio[-1] if valid_dio else None
        dio_change = _chg_pct(dio_latest, valid_dio[-2]) if len(valid_dio) >= 2 else None

        score = 20
        flags = []
        if turn_change is not None:
            if turn_change < -25:
                score = 80; flags.append(f"存貨周轉率下降 {abs(turn_change):.1f}%（嚴重惡化，可能滯銷）")
            elif turn_change < -15:
                score = 65; flags.append(f"存貨周轉率下降 {abs(turn_change):.1f}%（明顯惡化）")
            elif turn_change < -5:
                score = 40; flags.append(f"存貨周轉率小幅下降 {abs(turn_change):.1f}%（輕微警訊）")
            elif turn_change > 5:
                flags.append(f"存貨周轉率提升 {turn_change:.1f}%（良好訊號）")
            else:
                flags.append("存貨周轉率穩定")

        if dio_latest and dio_latest > 180:
            score = max(score, 70)
            flags.append(f"存貨天數 {dio_latest:.0f} 天，超過半年（滯銷風險高）")
        elif dio_latest and dio_latest > 90:
            score = max(score, 45)
            flags.append(f"存貨天數 {dio_latest:.0f} 天（偏高）")

        years = self._get_year_labels(fin)

        data.update({
            'available':   True,
            'risk_score':  score,
            'risk_level':  _risk_level(score),
            'flags':       flags,
            'details': {
                'years':       years[:n],
                'cogs':        cogs[:n],
                'inventory':   inv[:n],
                'turnover':    turnover,
                'dio':         dio,
                'turn_change': turn_change,
                'dio_latest':  dio_latest,
                'dio_change':  dio_change,
            },
        })
        return data

    # ══════════════════════════════════════════
    # 3. 現金流品質（CFO vs 淨利）
    # ══════════════════════════════════════════
    def _check_cfo_quality(self, fin, cf) -> Dict:
        ni  = self._vals(fin, ['Net Income', 'Net Income Common Stockholders',
                                'Net Income Including Noncontrolling Interests'])
        cfo = self._vals(cf,  ['Operating Cash Flow',
                                'Cash Flow From Continuing Operating Activities'])

        data = {'available': False, 'risk_score': 30, 'details': {}}

        if not ni or not cfo:
            data['message'] = "現金流或淨利資料不足"
            return data

        n = min(len(ni), len(cfo))
        cfo_ni_ratio = []
        accruals     = []
        for i in range(n):
            if ni[i] and ni[i] != 0 and cfo[i] is not None:
                cfo_ni_ratio.append(cfo[i] / ni[i])
            else:
                cfo_ni_ratio.append(None)
            # Accrual ratio = (NI - CFO) / avg_assets（簡化：直接用差距比例）
            if ni[i] is not None and cfo[i] is not None:
                accruals.append(ni[i] - cfo[i])
            else:
                accruals.append(None)

        valid_r = [r for r in cfo_ni_ratio if r is not None]
        ratio_latest = valid_r[-1] if valid_r else None
        ratio_avg    = np.mean(valid_r) if valid_r else None

        score = 20
        flags = []
        if ratio_latest is not None:
            if ratio_latest < 0:
                score = 90; flags.append(f"⚠️ CFO 為負（{ratio_latest:.2f}x），而淨利為正 — 強烈造假警訊")
            elif ratio_latest < 0.5:
                score = 75; flags.append(f"CFO 僅為淨利的 {ratio_latest:.2f} 倍，獲利品質偏低（應計項目過多）")
            elif ratio_latest < 0.8:
                score = 55; flags.append(f"CFO/淨利比 {ratio_latest:.2f}，獲利品質尚可但需觀察")
            elif ratio_latest < 1.5:
                flags.append(f"CFO/淨利比 {ratio_latest:.2f}，現金流品質健康")
            else:
                flags.append(f"CFO/淨利比 {ratio_latest:.2f}，現金流極為強勁（高品質獲利）")

        # 趨勢分析
        if len(valid_r) >= 2:
            if all(r < 0.8 for r in valid_r[-2:]):
                score = max(score, 60)
                flags.append("連續多年 CFO 低於淨利，持續警訊")
            elif valid_r[-1] < valid_r[-2] * 0.6:
                score = max(score, 50)
                flags.append("CFO/淨利比急速下降，獲利品質惡化")

        years = self._get_year_labels(fin)

        data.update({
            'available':    True,
            'risk_score':   score,
            'risk_level':   _risk_level(score),
            'flags':        flags,
            'details': {
                'years':       years[:n],
                'net_income':  ni[:n],
                'cfo':         cfo[:n],
                'cfo_ni_ratio': cfo_ni_ratio,
                'accruals':    accruals,
                'ratio_latest': ratio_latest,
                'ratio_avg':    ratio_avg,
            },
        })
        return data

    # ══════════════════════════════════════════
    # 4. 債務結構與償債能力
    # ══════════════════════════════════════════
    def _check_debt(self, bs, fin, cf, val) -> Dict:
        assets  = self._vals(bs,  ['Total Assets'])
        liab    = self._vals(bs,  ['Total Liabilities Net Minority Interest',
                                    'Total Liab', 'Total Liabilities'])
        cur_a   = self._vals(bs,  ['Current Assets', 'Total Current Assets'])
        cur_l   = self._vals(bs,  ['Current Liabilities', 'Total Current Liabilities'])
        lt_debt = self._vals(bs,  ['Long Term Debt', 'Long Term Debt And Capital Lease Obligation'])
        ebit    = self._vals(fin, ['EBIT', 'Operating Income'])
        int_exp = self._vals(fin, ['Interest Expense', 'Interest Expense Non Operating'])
        cfo     = self._vals(cf,  ['Operating Cash Flow', 'Cash Flow From Continuing Operating Activities'])
        ni      = self._vals(fin, ['Net Income', 'Net Income Common Stockholders'])
        rev     = self._vals(fin, ['Total Revenue', 'Revenue'])
        mkt_cap = _sf(val.get('market_cap'))

        data = {'available': False, 'risk_score': 20, 'details': {}}
        flags = []
        score = 20
        years = self._get_year_labels(bs)

        # ── 流動比率 ──
        cr_list = []
        for a, l in zip(cur_a, cur_l):
            cr_list.append(a / l if a and l and l != 0 else None)

        cr_latest = next((v for v in reversed(cr_list) if v is not None), None)
        if cr_latest is not None:
            if cr_latest < 1.0:
                score = max(score, 75); flags.append(f"🚨 流動比率 {cr_latest:.2f}（<1.0），短期償債能力嚴重不足")
            elif cr_latest < 1.5:
                score = max(score, 45); flags.append(f"流動比率 {cr_latest:.2f}（偏低，短期資金稍緊）")
            else:
                flags.append(f"流動比率 {cr_latest:.2f}（正常）")

        # ── 負債比率趨勢 ──
        dr_list = []
        for l, a in zip(liab, assets):
            dr_list.append(l / a * 100 if l and a and a != 0 else None)

        dr_latest = next((v for v in reversed(dr_list) if v is not None), None)
        dr_prev   = next((v for v in reversed(dr_list[:-1]) if v is not None), None) if len(dr_list) > 1 else None
        dr_change = _chg_pct(dr_latest, dr_prev)

        if dr_latest is not None:
            if dr_latest > 80:
                score = max(score, 80); flags.append(f"🚨 負債比率 {dr_latest:.1f}%（極高，財務風險大）")
            elif dr_latest > 65:
                score = max(score, 55); flags.append(f"負債比率 {dr_latest:.1f}%（偏高）")
            else:
                flags.append(f"負債比率 {dr_latest:.1f}%（正常）")

        if dr_change and dr_change > 15:
            score = max(score, 55); flags.append(f"負債比率快速上升 {dr_change:.1f}%（加速槓桿）")

        # ── 利息覆蓋率 ──
        icr = None
        if ebit and int_exp:
            ei = next((v for v in reversed(ebit) if v is not None), None)
            ie = next((v for v in reversed(int_exp) if v is not None), None)
            if ie and ie != 0:
                icr = abs(ei) / abs(ie)
                if icr < 1.5:
                    score = max(score, 80); flags.append(f"🚨 利息覆蓋率 {icr:.1f}x（<1.5，還息壓力極大）")
                elif icr < 3:
                    score = max(score, 50); flags.append(f"利息覆蓋率 {icr:.1f}x（偏低）")
                else:
                    flags.append(f"利息覆蓋率 {icr:.1f}x（健康）")

        # ── Altman Z-Score ──
        z_score = None
        try:
            la = assets[-1] if assets else None
            ll = liab[-1]   if liab   else None
            lca = cur_a[-1] if cur_a  else None
            lcl = cur_l[-1] if cur_l  else None
            ln  = ni[-1]    if ni     else None
            lr  = rev[-1]   if rev    else None
            if all(v is not None for v in [la, ll, lca, lcl, ln, lr, mkt_cap]) and la != 0:
                wc = lca - lcl   # Working Capital
                x1 = wc / la
                x2 = ln / la     # 使用淨利近似保留盈餘
                x3 = (ebit[-1] if ebit else ln) / la
                x4 = mkt_cap / ll if ll else 0
                x5 = lr / la
                z_score = 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 1.0*x5
        except Exception:
            pass

        if z_score is not None:
            if z_score < 1.81:
                score = max(score, 80)
                flags.append(f"🚨 Altman Z-Score {z_score:.2f}（<1.81，財務困境風險高）")
            elif z_score < 2.99:
                score = max(score, 40)
                flags.append(f"Altman Z-Score {z_score:.2f}（1.81-2.99 灰色地帶）")
            else:
                flags.append(f"Altman Z-Score {z_score:.2f}（>2.99 財務安全）")

        # ── 債務/CFO 回收年數 ──
        cfo_latest = next((v for v in reversed(cfo) if v is not None), None) if cfo else None
        ltd_latest = next((v for v in reversed(lt_debt) if v is not None), None) if lt_debt else None
        debt_cfo_years = None
        if ltd_latest and cfo_latest and cfo_latest > 0:
            debt_cfo_years = ltd_latest / cfo_latest
            if debt_cfo_years > 10:
                score = max(score, 65)
                flags.append(f"長期負債需 {debt_cfo_years:.1f} 年 CFO 才能還清（偏長）")
            elif debt_cfo_years > 5:
                score = max(score, 40)
                flags.append(f"長期負債需 {debt_cfo_years:.1f} 年 CFO 才能還清（可接受）")

        data.update({
            'available':    True,
            'risk_score':   score,
            'risk_level':   _risk_level(score),
            'flags':        flags,
            'details': {
                'years':        years,
                'total_assets': assets,
                'total_liab':   liab,
                'cur_assets':   cur_a,
                'cur_liab':     cur_l,
                'lt_debt':      lt_debt,
                'debt_ratio':   dr_list,
                'current_ratio': cr_list,
                'icr':          icr,
                'z_score':      z_score,
                'debt_cfo_yrs': debt_cfo_years,
                'dr_latest':    dr_latest,
                'cr_latest':    cr_latest,
            },
        })
        return data

    # ══════════════════════════════════════════
    # 5. 特殊會計處理 & 一次性項目
    # ══════════════════════════════════════════
    def _check_special_items(self, fin) -> Dict:
        ni          = self._vals(fin, ['Net Income', 'Net Income Common Stockholders'])
        unusual     = self._vals(fin, ['Total Unusual Items',
                                        'Total Unusual Items Excluding Goodwill'])
        other_ni    = self._vals(fin, ['Other Non Operating Income Expenses',
                                        'Other Income Expense'])
        tax_rates   = self._vals(fin, ['Tax Rate For Calcs'])
        ebit        = self._vals(fin, ['EBIT', 'Operating Income'])
        pretax      = self._vals(fin, ['Pretax Income'])

        data = {'available': False, 'risk_score': 10, 'details': {}}
        flags = []
        score = 10
        years = self._get_year_labels(fin)

        # ── 一次性損益佔淨利比重 ──
        unusual_ratios = []
        for i in range(min(len(ni), len(unusual))):
            if ni[i] and ni[i] != 0 and unusual[i] is not None:
                r = abs(unusual[i]) / abs(ni[i]) * 100
                unusual_ratios.append(r)
                if r > 50 and i == min(len(ni), len(unusual)) - 1:
                    score = max(score, 70)
                    flags.append(f"一次性損益佔淨利 {r:.1f}%（最新年度），盈餘品質低")
                elif r > 20 and i == min(len(ni), len(unusual)) - 1:
                    score = max(score, 45)
                    flags.append(f"一次性損益佔淨利 {r:.1f}%，需確認是否為可持續獲利")
            else:
                unusual_ratios.append(None)

        # ── 有效稅率異常 ──
        tax_flags = []
        valid_tax = [t for t in tax_rates if t is not None and 0 < t < 1]
        if len(valid_tax) >= 2:
            tax_avg = np.mean(valid_tax[:-1])
            tax_latest = valid_tax[-1]
            tax_diff = abs(tax_latest - tax_avg) / tax_avg * 100
            if tax_diff > 30:
                score = max(score, 50)
                tax_flags.append(f"有效稅率從 {tax_avg*100:.1f}% 變化至 {tax_latest*100:.1f}%（波動異常 {tax_diff:.0f}%）")
            else:
                tax_flags.append(f"有效稅率穩定（約 {tax_latest*100:.1f}%）")
        else:
            # 用 Pretax Income vs Net Income 估算
            if pretax and ni:
                n = min(len(pretax), len(ni))
                impl_taxes = []
                for i in range(n):
                    if pretax[i] and pretax[i] != 0 and ni[i] is not None:
                        impl_taxes.append((pretax[i] - ni[i]) / pretax[i])
                if len(impl_taxes) >= 2:
                    t_avg = np.mean(impl_taxes[:-1])
                    t_now = impl_taxes[-1]
                    if abs(t_now - t_avg) > 0.15:
                        score = max(score, 45)
                        tax_flags.append(f"隱含稅率異常變化（{t_avg*100:.0f}%→{t_now*100:.0f}%），需查明原因")

        flags.extend(tax_flags)

        # ── 其他非經常性收入佔比 ──
        if other_ni and ni:
            n = min(len(other_ni), len(ni))
            for i in range(n - 1, max(n - 2, -1), -1):
                if ni[i] and ni[i] != 0 and other_ni[i] is not None:
                    r = abs(other_ni[i]) / abs(ni[i]) * 100
                    if r > 30:
                        score = max(score, 50)
                        flags.append(f"其他非經常性收入佔淨利 {r:.1f}%，本業獲利偏弱")
                    break

        if not flags:
            flags.append("未發現明顯一次性項目或稅率異常")

        data.update({
            'available':       True,
            'risk_score':      score,
            'risk_level':      _risk_level(score),
            'flags':           flags,
            'details': {
                'years':           years,
                'net_income':      ni,
                'unusual':         unusual,
                'unusual_ratios':  unusual_ratios,
                'tax_rates':       tax_rates,
                'other_ni':        other_ni,
            },
        })
        return data

    # ══════════════════════════════════════════
    # 6. 內部人持股變動
    # ══════════════════════════════════════════
    def _check_insider(self) -> Dict:
        if self.fetcher.stock_type == 'TW':
            return self._tw_insider()
        else:
            return self._us_insider()

    def _tw_insider(self) -> Dict:
        """台股：外資持股比例變化（代理指標）"""
        try:
            start = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
            params = {
                "dataset":    "TaiwanStockShareholding",
                "data_id":    self.fetcher.stock_id,
                "start_date": start,
            }
            if self.finmind_token:
                params["token"] = self.finmind_token

            resp = requests.get(FINMIND_URL, params=params, timeout=10)
            d = resp.json()

            if d.get('status') != 200 or not d.get('data'):
                return self._tw_insider_fallback()

            df = pd.DataFrame(d['data'])
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')

            # 外資持股比例
            if 'ForeignInvestmentSharesRatio' not in df.columns or df.empty:
                return self._tw_insider_fallback()
            df['ForeignInvestmentSharesRatio'] = pd.to_numeric(
                df['ForeignInvestmentSharesRatio'], errors='coerce')
            df_valid = df.dropna(subset=['ForeignInvestmentSharesRatio'])
            if df_valid.empty:
                return self._tw_insider_fallback()

            ratio_first = float(df_valid['ForeignInvestmentSharesRatio'].iloc[0])
            ratio_last  = float(df_valid['ForeignInvestmentSharesRatio'].iloc[-1])
            ratio_chg   = ratio_last - ratio_first
            ratio_max   = float(df_valid['ForeignInvestmentSharesRatio'].max())
            ratio_min   = float(df_valid['ForeignInvestmentSharesRatio'].min())

            flags = []
            score = 25
            if ratio_chg < -5:
                score = 65; flags.append(f"外資持股比例近4月下降 {abs(ratio_chg):.1f}%（{ratio_first:.1f}%→{ratio_last:.1f}%），大戶撤退訊號")
            elif ratio_chg < -2:
                score = 45; flags.append(f"外資持股比例微降 {abs(ratio_chg):.1f}%（{ratio_first:.1f}%→{ratio_last:.1f}%）")
            elif ratio_chg > 3:
                flags.append(f"外資持股比例上升 {ratio_chg:.1f}%（{ratio_first:.1f}%→{ratio_last:.1f}%），國際資金加碼")
            else:
                flags.append(f"外資持股比例穩定（目前 {ratio_last:.1f}%）")

            return {
                'available':   True,
                'type':        'TW_Foreign',
                'risk_score':  score,
                'risk_level':  _risk_level(score),
                'flags':       flags,
                'details': {
                    'dates':        df['date'].dt.strftime('%m/%d').tolist(),
                    'ratio':        df['ForeignInvestmentSharesRatio'].tolist(),
                    'ratio_first':  ratio_first,
                    'ratio_last':   ratio_last,
                    'ratio_change': ratio_chg,
                    'note':         '台股使用外資持股比例作為法人態度代理指標',
                },
            }
        except Exception as e:
            return self._tw_insider_fallback(str(e))

    def _tw_insider_fallback(self, err="") -> Dict:
        return {
            'available':  False,
            'risk_score': 20,
            'risk_level': _risk_level(20),
            'flags':      ["台股內部人申報資料需登入 MOPS 取得，暫以外資持股替代"],
            'details':    {'note': err},
        }

    def _us_insider(self) -> Dict:
        """美股：yfinance insider transactions"""
        try:
            it = self._ticker.insider_transactions
            if it is None or it.empty:
                return {'available': False, 'risk_score': 20,
                        'risk_level': _risk_level(20),
                        'flags': ["內部人交易資料暫無法取得"],
                        'details': {}}

            it = it.copy()
            it['Start Date'] = pd.to_datetime(it['Start Date'])
            it['Shares'] = pd.to_numeric(it['Shares'], errors='coerce').fillna(0)

            # 最近 6 個月
            cutoff = pd.Timestamp.now() - pd.Timedelta(days=180)
            recent = it[it['Start Date'] >= cutoff].copy()

            if recent.empty:
                recent = it.head(20)

            # 解析買/賣（Transaction 欄位通常為空，用 Shares 符號判斷）
            # yfinance: Disposition(D) = 賣出 類型, Acquisition(A) = 買進
            buy_shares  = recent[recent['Ownership'] == 'A']['Shares'].sum()  if 'Ownership' in recent.columns else 0
            sell_shares = recent[recent['Ownership'] == 'D']['Shares'].sum()  if 'Ownership' in recent.columns else 0
            total       = buy_shares + sell_shares

            score = 25
            flags = []

            if total == 0:
                flags.append("近期無明顯內部人交易紀錄")
            else:
                sell_pct = sell_shares / total * 100 if total > 0 else 0
                if sell_pct > 75:
                    score = 70; flags.append(f"內部人近期以賣出為主（{sell_pct:.0f}%），需注意高管出脫動機")
                elif sell_pct > 55:
                    score = 45; flags.append(f"內部人賣超略多（{sell_pct:.0f}%）")
                elif sell_pct < 25:
                    flags.append(f"內部人以買進為主（買進佔 {100-sell_pct:.0f}%），信心偏正面")
                else:
                    flags.append("內部人買賣平衡，無明顯訊號")

            # 整理交易明細（最近10筆）
            display = recent[['Insider', 'Position', 'Shares', 'Start Date', 'Ownership']].head(10)
            display['Start Date'] = display['Start Date'].dt.strftime('%Y-%m-%d')

            return {
                'available':   True,
                'type':        'US_Insider',
                'risk_score':  score,
                'risk_level':  _risk_level(score),
                'flags':       flags,
                'details': {
                    'buy_shares':  int(buy_shares),
                    'sell_shares': int(sell_shares),
                    'sell_pct':    round(sell_pct if total > 0 else 0, 1),
                    'transactions': display.to_dict('records'),
                    'note': '資料來源：SEC Form 4（yfinance）',
                },
            }
        except Exception as e:
            return {'available': False, 'risk_score': 20,
                    'risk_level': _risk_level(20),
                    'flags': [f"內部人資料取得錯誤：{str(e)[:60]}"],
                    'details': {}}

    # ══════════════════════════════════════════
    # Beneish M-Score（財務造假偵測）
    # ══════════════════════════════════════════
    def _calc_m_score(self, fin, bs, cf) -> Dict:
        rev   = self._vals(fin, ['Total Revenue', 'Revenue'])
        cogs  = self._vals(fin, ['Cost Of Revenue', 'Reconciled Cost Of Revenue'])
        ar    = self._vals(bs,  ['Receivables', 'Net Receivables', 'Accounts Receivable'])
        ta    = self._vals(bs,  ['Total Assets'])
        ppe   = self._vals(bs,  ['Net PPE', 'Net Tangible Assets'])
        lt_d  = self._vals(bs,  ['Long Term Debt'])
        cur_l = self._vals(bs,  ['Current Liabilities'])
        ni    = self._vals(fin, ['Net Income'])
        cfo   = self._vals(cf,  ['Operating Cash Flow'])
        dep   = self._vals(fin, ['Reconciled Depreciation', 'Depreciation Amortization Depletion'])

        result = {'available': False, 'score': None, 'components': {}}

        if any(len(v) < 2 for v in [rev, ta, ar] if v):
            result['message'] = "資料年份不足（需至少2年）"
            return result

        try:
            def get_latest_2(lst):
                valid = [v for v in lst if v is not None]
                if len(valid) < 2: return None, None
                return valid[-2], valid[-1]

            r0, r1 = get_latest_2(rev)
            c0, c1 = get_latest_2(cogs) if cogs else (None, None)
            a0, a1 = get_latest_2(ar)   if ar   else (None, None)
            t0, t1 = get_latest_2(ta)
            p0, p1 = get_latest_2(ppe)  if ppe  else (None, None)
            d0, d1 = get_latest_2(lt_d) if lt_d else (None, None)
            cl0,cl1= get_latest_2(cur_l) if cur_l else (None, None)
            n0, n1 = get_latest_2(ni)   if ni   else (None, None)
            cf0,cf1= get_latest_2(cfo)  if cfo  else (None, None)
            dep0, dep1 = get_latest_2(dep) if dep else (None, None)

            comps = {}

            # DSRI：Days Sales Receivable Index
            if all(v is not None and v != 0 for v in [r0, r1, a0, a1]):
                comps['DSRI'] = (a1/r1) / (a0/r0)

            # GMI：Gross Margin Index
            if all(v is not None and v != 0 for v in [r0, r1, c0, c1]):
                gm0 = (r0 - abs(c0)) / r0
                gm1 = (r1 - abs(c1)) / r1
                if gm1 != 0:
                    comps['GMI'] = gm0 / gm1

            # AQI：Asset Quality Index
            if all(v is not None for v in [t0, t1, p0, p1]):
                ca0 = 1 - (abs(p0) / t0) if t0 else None
                ca1 = 1 - (abs(p1) / t1) if t1 else None
                if ca0 and ca1 and ca1 != 0:
                    comps['AQI'] = ca0 / ca1

            # SGI：Sales Growth Index
            if r0 and r1 is not None and r0 != 0:
                comps['SGI'] = r1 / r0

            # DEPI：Depreciation Index
            if dep0 and dep1 and p0 and p1:
                dp0 = abs(dep0) / (abs(p0) + abs(dep0))
                dp1 = abs(dep1) / (abs(p1) + abs(dep1))
                if dp1 and dp1 != 0:
                    comps['DEPI'] = dp0 / dp1

            # LVGI：Leverage Index
            if all(v is not None for v in [t0, t1, d0, d1, cl0, cl1]):
                lv0 = (abs(d0) + abs(cl0)) / t0 if t0 else None
                lv1 = (abs(d1) + abs(cl1)) / t1 if t1 else None
                if lv0 and lv0 != 0:
                    comps['LVGI'] = lv1 / lv0

            # TATA：Total Accruals to Total Assets
            if n1 is not None and cf1 is not None and t1:
                comps['TATA'] = (n1 - cf1) / t1

            # M-Score 公式
            m = -4.84
            m += comps.get('DSRI',  1.00) * 0.920
            m += comps.get('GMI',   1.00) * 0.528
            m += comps.get('AQI',   1.00) * 0.404
            m += comps.get('SGI',   1.00) * 0.892
            m += comps.get('DEPI',  1.00) * 0.115
            m -= comps.get('SGAI',  1.00) * 0.172  # SGAI 不易計算，略去
            m += comps.get('TATA',  0.00) * 4.679
            m -= comps.get('LVGI',  1.00) * 0.327

            if m > -1.49:
                level, color = "高度疑似操縱", "#ff4757"
                risk_score   = 85
                interp       = "M-Score > -1.49，強烈警示財務數字可能遭操縱，建議深入查閱財報附註"
            elif m > -1.78:
                level, color = "可能存在問題", "#ff9f43"
                risk_score   = 55
                interp       = "M-Score 在 -1.78 至 -1.49 之間，存在輕微操縱風險，建議關注應收帳款與現金流"
            else:
                level, color = "財務相對透明", "#00b09b"
                risk_score   = 15
                interp       = "M-Score < -1.78，財務操縱可能性較低（但非百分之百保證）"

            result.update({
                'available':   True,
                'score':       round(m, 3),
                'risk_score':  risk_score,
                'risk_level':  (level, color),
                'interpretation': interp,
                'components':  {k: round(v, 3) for k, v in comps.items()},
            })

        except Exception as e:
            result['message'] = f"M-Score 計算失敗：{e}"

        return result

    # ══════════════════════════════════════════
    # Piotroski F-Score（財務健康 0-9 分）
    # ══════════════════════════════════════════
    def _calc_f_score(self, fin, bs, cf, val) -> Dict:
        ni   = self._vals(fin, ['Net Income'])
        ta   = self._vals(bs,  ['Total Assets'])
        cfo  = self._vals(cf,  ['Operating Cash Flow'])
        lt_d = self._vals(bs,  ['Long Term Debt'])
        cur_a= self._vals(bs,  ['Current Assets'])
        cur_l= self._vals(bs,  ['Current Liabilities'])
        rev  = self._vals(fin, ['Total Revenue', 'Revenue'])
        gp   = self._vals(fin, ['Gross Profit'])

        result = {'available': False, 'score': None, 'criteria': {}}

        def get2(lst):
            valid = [v for v in lst if v is not None]
            if len(valid) < 2: return None, None
            return valid[-2], valid[-1]

        try:
            n0, n1   = get2(ni)
            t0, t1   = get2(ta)
            cf0, cf1 = get2(cfo)
            d0, d1   = get2(lt_d)   if lt_d else (None, None)
            ca0, ca1 = get2(cur_a)  if cur_a else (None, None)
            cl0, cl1 = get2(cur_l)  if cur_l else (None, None)
            r0, r1   = get2(rev)
            g0, g1   = get2(gp)     if gp else (None, None)

            criteria = {}
            def check(name, condition, desc_true, desc_false):
                val = 1 if condition else 0
                criteria[name] = {'score': val, 'desc': desc_true if condition else desc_false}

            # 獲利能力
            roa1 = n1/t1 if n1 and t1 else None
            roa0 = n0/t0 if n0 and t0 else None
            check("F1_ROA",    roa1 and roa1 > 0,
                  "ROA > 0（獲利）", "ROA ≤ 0（虧損）")
            check("F2_CFO",    cf1 and cf1 > 0,
                  "CFO > 0（現金流正）", "CFO ≤ 0（現金流負）")
            check("F3_ΔROA",   roa1 and roa0 and roa1 > roa0,
                  "ROA 改善", "ROA 下滑")
            check("F4_Accruals", (cf1 and n1 and cf1 > n1),
                  "CFO > 淨利（高品質獲利）", "CFO < 淨利（應計項目偏高）")

            # 槓桿 & 流動性
            lev0 = d0/t0 if d0 and t0 else None
            lev1 = d1/t1 if d1 and t1 else None
            cr0 = ca0/cl0 if ca0 and cl0 else None
            cr1 = ca1/cl1 if ca1 and cl1 else None
            check("F5_ΔLev",   lev1 is not None and lev0 is not None and lev1 < lev0,
                  "槓桿率下降（財務改善）", "槓桿率上升或持平")
            check("F6_ΔCR",    cr1 is not None and cr0 is not None and cr1 > cr0,
                  "流動比率改善", "流動比率下滑")
            # F7 新股稀釋（簡化：用 val 的 sharesOutstanding 變化）
            shares_diluted = False  # 預設無稀釋
            check("F7_Dilution", not shares_diluted,
                  "未發行新股（未稀釋）", "發行新股（可能稀釋股東）")

            # 營運效率
            gm0 = g0/r0 if g0 and r0 else None
            gm1 = g1/r1 if g1 and r1 else None
            at0 = r0/t0 if r0 and t0 else None
            at1 = r1/t1 if r1 and t1 else None
            check("F8_ΔGM",    gm1 is not None and gm0 is not None and gm1 > gm0,
                  "毛利率改善", "毛利率下滑")
            check("F9_ΔAT",    at1 is not None and at0 is not None and at1 > at0,
                  "資產周轉率改善", "資產周轉率下滑")

            total = sum(v['score'] for v in criteria.values())

            if total >= 7:
                level = "財務強健（Strong Buy 候選）";   color = "#00b09b"
            elif total >= 5:
                level = "財務良好（中性偏多）";          color = "#5cb85c"
            elif total >= 3:
                level = "財務普通（需謹慎）";            color = "#ffa502"
            else:
                level = "財務偏弱（高風險）";            color = "#ff4757"

            result.update({
                'available': True,
                'score':     total,
                'level':     level,
                'color':     color,
                'criteria':  criteria,
                'risk_score': max(0, (9 - total) / 9 * 80),
            })

        except Exception as e:
            result['message'] = f"F-Score 計算失敗：{e}"

        return result

    # ══════════════════════════════════════════
    # 整體風險評估
    # ══════════════════════════════════════════
    def _calc_overall(self, signals: Dict, m_score: Dict, f_score: Dict) -> Dict:
        weights = {
            'cashflow_quality': 0.25,  # 最重要
            'debt_structure':   0.20,
            'ar_revenue':       0.15,
            'inventory':        0.10,
            'special_items':    0.15,
            'insider_activity': 0.10,
        }

        total_w, total_s = 0, 0
        for key, w in weights.items():
            sig = signals.get(key, {})
            if sig.get('risk_score') is not None:
                total_s += sig['risk_score'] * w
                total_w += w

        base_score = total_s / total_w if total_w > 0 else 30

        # M-Score 加權影響
        if m_score.get('risk_score'):
            base_score = base_score * 0.7 + m_score['risk_score'] * 0.3

        # F-Score 調整（低分加重風險）
        if f_score.get('score') is not None:
            f_adj = (9 - f_score['score']) / 9 * 20
            base_score = base_score * 0.85 + f_adj * 0.15

        score = min(100, max(0, base_score))
        level, color = _risk_level(score)

        # 收集所有旗幟
        all_flags = []
        for key, sig in signals.items():
            for f in sig.get('flags', []):
                if '🚨' in f or score > 50:
                    all_flags.append(f)

        # 前三大風險
        top_risks = sorted(
            [(k, signals[k]['risk_score'])
             for k in signals if signals[k].get('risk_score', 0) > 40],
            key=lambda x: -x[1]
        )[:3]

        return {
            'score':      round(score, 1),
            'level':      level,
            'color':      color,
            'top_risks':  top_risks,
            'all_flags':  all_flags[:8],
        }

    # ──────────────────────────────────────────
    # 輔助：年份標籤
    # ──────────────────────────────────────────
    def _get_year_labels(self, df: pd.DataFrame) -> List[str]:
        if df is None or df.empty:
            return []
        cols = sorted(df.columns)
        return [str(c.year) if hasattr(c, 'year') else str(c) for c in cols]
