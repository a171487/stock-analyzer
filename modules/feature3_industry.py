"""
功能三：產業競爭地位與未來發展前景分析
- 產業成長性 & 市場規模
- 公司核心競爭優劣勢（SWOT）
- 競爭對手比較
- 政策 & 技術變革影響
- 風險 & 成長催化劑
- AI 生成完整分析報告（Claude API）
"""

import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional, Any
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.data_fetcher import StockDataFetcher
from config.industry_knowledge import (
    INDUSTRY_KNOWLEDGE,
    TW_STOCK_TO_INDUSTRY_KEY,
    US_SECTOR_TO_INDUSTRY_KEY,
    US_INDUSTRY_TO_KEY,
)


def _safe_float(v) -> Optional[float]:
    try:
        f = float(v)
        return f if np.isfinite(f) else None
    except (TypeError, ValueError):
        return None

def _pct(v) -> str:
    if v is None: return "N/A"
    return f"{v*100:.1f}%" if abs(v) < 10 else f"{v:.1f}%"

def _fmt_cap(v) -> str:
    if v is None: return "N/A"
    if v >= 1e12: return f"${v/1e12:.2f}T"
    if v >= 1e9:  return f"${v/1e9:.1f}B"
    if v >= 1e6:  return f"${v/1e6:.0f}M"
    return f"${v:.0f}"


class IndustryAnalyzer:

    def __init__(self, fetcher: StockDataFetcher):
        self.fetcher = fetcher

    # ══════════════════════════════════════════
    # 主入口
    # ══════════════════════════════════════════
    def run_full_analysis(self) -> Dict:
        # 1. 取得公司資料
        company_data = self._get_company_data()

        # 2. 找到對應的產業知識
        industry_key  = self._resolve_industry_key()
        industry_info = INDUSTRY_KNOWLEDGE.get(industry_key, {})

        # 3. 取得同業比較資料
        peer_data = self._fetch_peer_comparison()

        # 4. 建立 SWOT
        swot = self._build_swot(company_data, industry_info, peer_data)

        # 5. 競爭地位評估
        positioning = self._calc_positioning(company_data, peer_data)

        # 6. 市場份額估算（以收入比較）
        market_share = self._estimate_market_share(company_data, peer_data)

        return {
            'company_data':  company_data,
            'industry_key':  industry_key,
            'industry_info': industry_info,
            'peer_data':     peer_data,
            'swot':          swot,
            'positioning':   positioning,
            'market_share':  market_share,
        }

    # ──────────────────────────────────────────
    # 產業 Key 識別
    # ──────────────────────────────────────────
    def _resolve_industry_key(self) -> str:
        if self.fetcher.stock_type == 'TW':
            key = TW_STOCK_TO_INDUSTRY_KEY.get(self.fetcher.stock_id)
            if key:
                return key

        # 嘗試用 yfinance industry 欄位
        yf_industry = self.fetcher.get_industry()
        yf_sector   = self.fetcher.get_sector()

        for src in [yf_industry, yf_sector]:
            if not src:
                continue
            for k in INDUSTRY_KNOWLEDGE:
                if k.lower() in src.lower() or src.lower() in k.lower():
                    return k
            # 查 US 對照表
            key = US_INDUSTRY_TO_KEY.get(src) or US_SECTOR_TO_INDUSTRY_KEY.get(src)
            if key:
                return key

        # 找不到就用通用 key
        return yf_sector or "Technology"

    # ──────────────────────────────────────────
    # 公司基本財務資料
    # ──────────────────────────────────────────
    def _get_company_data(self) -> Dict:
        info = self.fetcher.info
        fin  = self.fetcher.get_financials_3y()
        bs   = self.fetcher.get_balance_sheet_3y()

        # Revenue CAGR
        rev_series = self.fetcher.safe_get_row(fin, ['Total Revenue', 'Revenue', 'Operating Revenue'])
        revenue_cagr = None
        revenues = []
        if rev_series is not None:
            vals = [_safe_float(v) for v in sorted(
                zip(rev_series.index, rev_series.values), key=lambda x: x[0]
            )]
            revenues = [v for v in vals if v is not None]
            if len(revenues) >= 2 and revenues[0] and revenues[0] != 0:
                n = len(revenues) - 1
                revenue_cagr = ((revenues[-1] / revenues[0]) ** (1/n) - 1) * 100

        gross  = _safe_float(info.get('grossMargins'))
        net    = _safe_float(info.get('profitMargins'))
        roe    = _safe_float(info.get('returnOnEquity'))
        roa    = _safe_float(info.get('returnOnAssets'))

        return {
            'name':         self.fetcher.get_company_name(),
            'ticker':       self.fetcher.ticker_symbol,
            'sector':       self.fetcher.get_sector(),
            'industry':     self.fetcher.get_industry(),
            'market_cap':   _safe_float(info.get('marketCap')),
            'revenue_ttm':  _safe_float(info.get('totalRevenue')),
            'revenue_cagr': revenue_cagr,
            'gross_margin': gross * 100 if gross else None,
            'net_margin':   net * 100 if net else None,
            'roe':          roe * 100 if roe else None,
            'roa':          roa * 100 if roa else None,
            'pe_ratio':     _safe_float(info.get('trailingPE') or info.get('forwardPE')),
            'pb_ratio':     _safe_float(info.get('priceToBook')),
            'debt_to_equity': _safe_float(info.get('debtToEquity')),
            'current_ratio':  _safe_float(info.get('currentRatio')),
            'beta':           _safe_float(info.get('beta')),
            'employees':      info.get('fullTimeEmployees'),
            'description':    info.get('longBusinessSummary', ''),
            'revenues_hist':  revenues,
        }

    # ──────────────────────────────────────────
    # 同業比較
    # ──────────────────────────────────────────
    def _fetch_peer_comparison(self) -> List[Dict]:
        peers = self.fetcher.get_peer_tickers()
        result = []
        for p in peers[:5]:
            try:
                t = yf.Ticker(p)
                info = t.info or {}
                gm  = _safe_float(info.get('grossMargins'))
                nm  = _safe_float(info.get('profitMargins'))
                roe = _safe_float(info.get('returnOnEquity'))
                rev = _safe_float(info.get('totalRevenue'))
                result.append({
                    'ticker':       p,
                    'name':         (info.get('longName') or info.get('shortName') or p)[:12],
                    'market_cap':   _safe_float(info.get('marketCap')),
                    'revenue':      rev,
                    'gross_margin': gm * 100 if gm else None,
                    'net_margin':   nm * 100 if nm else None,
                    'roe':          roe * 100 if roe else None,
                    'pe_ratio':     _safe_float(info.get('trailingPE') or info.get('forwardPE')),
                    'pb_ratio':     _safe_float(info.get('priceToBook')),
                    'revenue_growth': _safe_float(info.get('revenueGrowth')),
                    'beta':         _safe_float(info.get('beta')),
                })
            except Exception:
                continue
        return result

    # ──────────────────────────────────────────
    # SWOT 分析
    # ──────────────────────────────────────────
    def _build_swot(self, cd: Dict, ki: Dict, peers: List[Dict]) -> Dict:
        gm  = cd.get('gross_margin')
        nm  = cd.get('net_margin')
        roe = cd.get('roe')
        cagr = cd.get('revenue_cagr')
        dr  = cd.get('debt_to_equity')
        cr  = cd.get('current_ratio')

        peer_gms = [p['gross_margin'] for p in peers if p.get('gross_margin')]
        peer_nms = [p['net_margin']   for p in peers if p.get('net_margin')]
        avg_gm   = np.mean(peer_gms) if peer_gms else None
        avg_nm   = np.mean(peer_nms) if peer_nms else None

        strengths, weaknesses = [], []

        # 從知識庫取底稿
        strengths  += ki.get('strengths_template', [])
        weaknesses += ki.get('weaknesses_template', [])

        # 根據財務數據補充
        if gm is not None:
            if avg_gm and gm > avg_gm + 8:
                strengths.append(f"毛利率 {gm:.1f}% 顯著高於同業均值 {avg_gm:.1f}%，定價能力領先")
            elif avg_gm and gm < avg_gm - 8:
                weaknesses.append(f"毛利率 {gm:.1f}% 低於同業均值 {avg_gm:.1f}%，產品競爭力待加強")

        if roe is not None:
            if roe > 20:
                strengths.append(f"ROE 高達 {roe:.1f}%，股東權益回報能力卓越")
            elif roe < 8:
                weaknesses.append(f"ROE 僅 {roe:.1f}%，資本運用效率偏低")

        if cagr is not None:
            if cagr > 20:
                strengths.append(f"近3年營收 CAGR {cagr:.1f}%，成長動能強勁")
            elif cagr < 0:
                weaknesses.append(f"近3年營收 CAGR {cagr:.1f}%，業績呈現衰退")

        if dr is not None:
            if dr < 30:
                strengths.append(f"負債股東權益比 {dr:.0f}%，財務結構保守穩健")
            elif dr > 100:
                weaknesses.append(f"負債股東權益比 {dr:.0f}%，財務槓桿偏高需注意")

        opportunities = ki.get('catalysts', [])
        threats       = ki.get('risks', [])

        return {
            'strengths':     strengths[:5],
            'weaknesses':    weaknesses[:4],
            'opportunities': opportunities[:5],
            'threats':       threats[:5],
        }

    # ──────────────────────────────────────────
    # 競爭地位評估（雷達分數）
    # ──────────────────────────────────────────
    def _calc_positioning(self, cd: Dict, peers: List[Dict]) -> Dict:
        def rank_score(val, peer_vals, higher_is_better=True):
            """在同業中排名轉為 0-100 分"""
            if val is None or not peer_vals:
                return 50
            all_vals = sorted([v for v in peer_vals + [val] if v is not None])
            if not all_vals:
                return 50
            idx = all_vals.index(val) if val in all_vals else len(all_vals) // 2
            pct = idx / max(len(all_vals) - 1, 1) * 100
            return pct if higher_is_better else 100 - pct

        peer_gm  = [p['gross_margin'] for p in peers if p.get('gross_margin')]
        peer_nm  = [p['net_margin']   for p in peers if p.get('net_margin')]
        peer_roe = [p['roe']          for p in peers if p.get('roe')]
        peer_cap = [p['market_cap']   for p in peers if p.get('market_cap')]
        peer_pe  = [p['pe_ratio']     for p in peers if p.get('pe_ratio') and p['pe_ratio'] > 0]
        peer_gr  = [p.get('revenue_growth') for p in peers
                    if p.get('revenue_growth') is not None]

        scores = {
            '獲利能力': int(rank_score(cd.get('gross_margin'), peer_gm)),
            '成長動能': int(rank_score(
                cd.get('revenue_cagr'), [g*100 if g else None for g in peer_gr])),
            '規模地位': int(rank_score(cd.get('market_cap'), peer_cap)),
            '股東回報': int(rank_score(cd.get('roe'), peer_roe)),
            '估值合理': int(rank_score(cd.get('pe_ratio'), peer_pe, higher_is_better=False)),
        }
        overall = int(np.mean(list(scores.values())))
        return {'scores': scores, 'overall': overall}

    # ──────────────────────────────────────────
    # 市場份額估算
    # ──────────────────────────────────────────
    def _estimate_market_share(self, cd: Dict, peers: List[Dict]) -> List[Dict]:
        my_rev = cd.get('revenue_ttm')
        if not my_rev:
            return []

        items = [{'name': cd['name'][:10], 'revenue': my_rev, 'is_self': True}]
        for p in peers:
            if p.get('revenue'):
                items.append({'name': p['name'][:10], 'revenue': p['revenue'], 'is_self': False})

        total = sum(i['revenue'] for i in items)
        if total <= 0:
            return []

        for i in items:
            i['share_pct'] = i['revenue'] / total * 100

        return sorted(items, key=lambda x: x['revenue'], reverse=True)

    # ══════════════════════════════════════════
    # Claude API 生成報告
    # ══════════════════════════════════════════
    def generate_ai_report(self, analysis: Dict, api_key: str) -> str:
        """呼叫 Claude API 生成完整的產業分析報告"""
        try:
            import anthropic
            cd   = analysis['company_data']
            ki   = analysis['industry_info']
            swot = analysis['swot']
            peers = analysis['peer_data']

            # 建立同業比較表
            peer_rows = ""
            for p in peers[:5]:
                gm  = f"{p['gross_margin']:.1f}%" if p.get('gross_margin') else 'N/A'
                nm  = f"{p['net_margin']:.1f}%"   if p.get('net_margin')   else 'N/A'
                cap = _fmt_cap(p.get('market_cap'))
                pe  = f"{p['pe_ratio']:.1f}x"     if p.get('pe_ratio')     else 'N/A'
                peer_rows += f"| {p['name']} | {cap} | {gm} | {nm} | {pe} |\n"

            my_gm  = f"{cd['gross_margin']:.1f}%" if cd.get('gross_margin') else 'N/A'
            my_nm  = f"{cd['net_margin']:.1f}%"   if cd.get('net_margin')   else 'N/A'
            my_pe  = f"{cd['pe_ratio']:.1f}x"     if cd.get('pe_ratio')     else 'N/A'
            my_cap = _fmt_cap(cd.get('market_cap'))
            my_row = (
                f"| **{cd['name'][:12]}（本股）** "
                f"| **{my_cap}** "
                f"| **{my_gm}** "
                f"| **{my_nm}** "
                f"| **{my_pe}** |\n"
            )

            peer_table = (
                f"| 公司 | 市值 | 毛利率 | 淨利率 | P/E |\n"
                f"|---|---|---|---|---|\n"
                f"{my_row}{peer_rows}"
            )

            # 產業背景摘要
            industry_ctx = f"""
產業名稱：{ki.get('full_name', analysis['industry_key'])}
市場規模（2024）：{ki.get('market_size_now', 'N/A')}
市場規模（2028E）：{ki.get('market_size_2028', 'N/A')}
預估 CAGR：{ki.get('cagr', 'N/A')}

關鍵趨勢：
{chr(10).join(f'- {t}' for t in ki.get('key_themes', []))}

主要成長催化劑：
{chr(10).join(f'- {c}' for c in ki.get('catalysts', []))}

主要風險：
{chr(10).join(f'- {r}' for r in ki.get('risks', []))}

政策影響：
{chr(10).join(f'- {p}' for p in ki.get('policy', []))}
""".strip()

            swot_ctx = f"""
優勢：{', '.join(swot['strengths'][:4])}
劣勢：{', '.join(swot['weaknesses'][:3])}
機會：{', '.join(swot['opportunities'][:4])}
威脅：{', '.join(swot['threats'][:4])}
"""
            company_ctx = f"""
公司：{cd['name']} ({cd['ticker']})
所屬產業：{cd.get('industry', cd.get('sector', 'N/A'))}
市值：{_fmt_cap(cd.get('market_cap'))}
近3年營收CAGR：{f"{cd['revenue_cagr']:.1f}%" if cd.get('revenue_cagr') else 'N/A'}
毛利率：{f"{cd['gross_margin']:.1f}%" if cd.get('gross_margin') else 'N/A'}
淨利率：{f"{cd['net_margin']:.1f}%" if cd.get('net_margin') else 'N/A'}
ROE：{f"{cd['roe']:.1f}%" if cd.get('roe') else 'N/A'}
本益比(P/E)：{f"{cd['pe_ratio']:.1f}x" if cd.get('pe_ratio') else 'N/A'}
負債/股東權益：{f"{cd['debt_to_equity']:.1f}%" if cd.get('debt_to_equity') else 'N/A'}
""".strip()

            prompt = f"""你是一位擁有 20 年經驗的資深產業分析師，專精台灣及全球科技、半導體與金融產業研究。

請根據以下資料，為 **{cd['name']}（{cd['ticker']}）** 撰寫一份完整的產業競爭分析報告。

---
## 公司財務摘要
{company_ctx}

## 同業比較數據
{peer_table}

## SWOT 摘要
{swot_ctx}

## 產業背景知識
{industry_ctx}

---

## 報告要求

請依以下架構撰寫，每個章節務必結合上方提供的真實數據：

### 一、產業成長性與市場規模預測
- 引用具體市場規模與 CAGR 數字
- 說明主要驅動力（AI、EV、5G 等）
- 短期（1-2年）vs 長期（3-5年）展望

### 二、公司核心競爭優勢（護城河分析）
- 結合財務數據說明優勢（如毛利率高於同業代表...）
- 點出 2-3 個最關鍵的競爭壁壘

### 三、主要劣勢與弱點
- 客觀指出財務或業務上的弱點
- 與同業相比的不足之處

### 四、主要競爭對手比較
- 引用同業比較表的數字
- 說明在市場上的相對地位

### 五、影響股價的產業政策與技術變革
- 近期最重要的政策（補貼/管制）
- 可能改變產業格局的技術突破

### 六、未來 3-5 年潛在風險與成長催化劑
- 各列出 3-4 點，並說明對股價的可能影響

### 七、投資啟示與產業競爭地位評分
- 給出明確的投資策略建議（長線/短線/觀察）
- 最後給出「產業競爭地位評分」：X/10 分，並說明評分理由

---

**格式要求**：
- 使用繁體中文，語氣專業但易懂
- 重要數字與結論請**加粗**
- 每章節 150-250 字，整體篇幅 1800-2500 字
- 語氣像在向機構投資人做報告簡報
"""

            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text

        except ImportError:
            return self._template_report(analysis)
        except Exception as e:
            return f"⚠️ Claude API 呼叫失敗：{e}\n\n" + self._template_report(analysis)

    # ══════════════════════════════════════════
    # 模板分析（無 API Key 時使用）
    # ══════════════════════════════════════════
    def _template_report(self, analysis: Dict) -> str:
        cd   = analysis['company_data']
        ki   = analysis['industry_info']
        swot = analysis['swot']
        peers = analysis['peer_data']
        pos  = analysis['positioning']

        name   = cd['name']
        ticker = cd['ticker']
        ind    = ki.get('full_name', analysis['industry_key'])

        report = f"# {name}（{ticker}）產業競爭分析報告\n\n"

        # 一、產業展望
        report += f"## 一、產業成長性與市場規模預測\n\n"
        report += f"**{name}** 所屬的 **{ind}** 產業，"
        report += f"2024 年全球市場規模達 **{ki.get('market_size_now','N/A')}**，"
        report += f"預計至 2028 年成長至 **{ki.get('market_size_2028','N/A')}**，"
        report += f"年複合成長率（CAGR）約 **{ki.get('cagr','N/A')}**。\n\n"
        report += "**關鍵成長驅動力：**\n"
        for t in ki.get('key_themes', [])[:4]:
            report += f"- {t}\n"
        report += "\n"

        # 二、競爭優勢
        report += "## 二、公司核心競爭優勢\n\n"
        for s in swot['strengths'][:4]:
            report += f"✅ {s}\n\n"

        # 三、劣勢
        report += "## 三、主要劣勢與弱點\n\n"
        for w in swot['weaknesses'][:3]:
            report += f"⚠️ {w}\n\n"

        # 四、同業比較
        report += "## 四、主要競爭對手比較\n\n"
        if peers:
            report += f"| 公司 | 市值 | 毛利率 | 淨利率 | P/E |\n|---|---|---|---|---|\n"
            my_gm = f"{cd['gross_margin']:.1f}%" if cd.get('gross_margin') else 'N/A'
            my_nm = f"{cd['net_margin']:.1f}%"   if cd.get('net_margin')   else 'N/A'
            my_pe = f"{cd['pe_ratio']:.1f}x"     if cd.get('pe_ratio')     else 'N/A'
            report += f"| **{name[:10]}（本股）** | **{_fmt_cap(cd.get('market_cap'))}** | **{my_gm}** | **{my_nm}** | **{my_pe}** |\n"
            for p in peers[:4]:
                gm  = f"{p['gross_margin']:.1f}%" if p.get('gross_margin') else 'N/A'
                nm  = f"{p['net_margin']:.1f}%"   if p.get('net_margin')   else 'N/A'
                pe  = f"{p['pe_ratio']:.1f}x"     if p.get('pe_ratio')     else 'N/A'
                cap = _fmt_cap(p.get('market_cap'))
                report += f"| {p['name']} | {cap} | {gm} | {nm} | {pe} |\n"

            # 比較結論
            peer_gms = [p['gross_margin'] for p in peers if p.get('gross_margin')]
            if peer_gms and cd.get('gross_margin'):
                avg = np.mean(peer_gms)
                if cd['gross_margin'] > avg + 5:
                    report += f"\n> ✅ 毛利率高於同業均值 {avg:.1f}%，競爭護城河明顯。\n"
                elif cd['gross_margin'] < avg - 5:
                    report += f"\n> ⚠️ 毛利率低於同業均值 {avg:.1f}%，成本競爭力需提升。\n"
                else:
                    report += f"\n> ➡️ 毛利率與同業均值（{avg:.1f}%）相近，中等競爭地位。\n"
        else:
            report += "同業比較資料暫無法取得。\n"
        report += "\n"

        # 五、政策與技術
        report += "## 五、影響股價的產業政策與技術變革\n\n"
        report += "**政策面：**\n"
        for p in ki.get('policy', [])[:3]:
            report += f"- {p}\n"
        report += "\n**技術變革：**\n"
        for t in ki.get('key_themes', [])[:3]:
            report += f"- {t}\n"
        report += "\n"

        # 六、風險與催化劑
        report += "## 六、未來 3-5 年風險與成長催化劑\n\n"
        report += "**🔺 成長催化劑（Upside Catalysts）**\n"
        for c in swot['opportunities'][:4]:
            report += f"- {c}\n"
        report += "\n**🔻 潛在風險（Downside Risks）**\n"
        for r in swot['threats'][:4]:
            report += f"- {r}\n"
        report += "\n"

        # 七、投資啟示
        overall = pos.get('overall', 50)
        report += f"## 七、投資啟示\n\n"
        if overall >= 70:
            stance = "✅ **長線偏多**：公司在同業中競爭地位強，具備護城河優勢"
        elif overall >= 50:
            stance = "➡️ **中性觀察**：競爭地位中等，等待業績進一步確認"
        else:
            stance = "⚠️ **謹慎看待**：相較同業競爭力偏弱，建議等待轉折訊號"
        report += f"{stance}。\n\n"

        # 評分
        score = round(overall / 10, 1)
        report += f"**🏆 產業競爭地位評分：{score}/10**\n\n"
        report += "| 評估維度 | 分數（/100）|\n|---|---|\n"
        for k, v in pos['scores'].items():
            bar = "▓" * (v // 10) + "░" * (10 - v // 10)
            report += f"| {k} | {bar} {v} |\n"

        report += "\n\n> 💡 **提示**：設定 Claude API Key 後，可獲得 AI 生成的完整深度分析報告（2000字+）\n"
        report += "> ⚠️ 本報告僅供參考，不構成投資建議。\n"

        return report
