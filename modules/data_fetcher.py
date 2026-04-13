"""
資料擷取模組
支援台股（Yahoo Finance .TW / FinMind）與美股（Yahoo Finance）
"""

import re
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.peer_stocks import TAIWAN_STOCK_INDUSTRY_MAP, TAIWAN_INDUSTRY_PEERS, US_INDUSTRY_PEERS


def detect_stock_type(stock_input: str) -> str:
    """判斷是台股還是美股，回傳 'TW' 或 'US'"""
    stock_input = stock_input.strip().upper()
    # 已有 .TW 或 .TWO → 台股
    if stock_input.endswith('.TW') or stock_input.endswith('.TWO'):
        return 'TW'
    # 台股/ETF：4~6 碼數字，結尾可選一個英文字母（如 00631L、00632R、00981A）
    if re.match(r'^\d{4,6}[A-Z]?$', stock_input):
        return 'TW'
    return 'US'


class StockDataFetcher:
    """統一資料擷取介面，自動判斷台股/美股並切換資料來源"""

    FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"

    def __init__(self, stock_input: str, finmind_token: str = ""):
        self.original_input = stock_input.strip()
        self.stock_type = detect_stock_type(stock_input)
        self.finmind_token = finmind_token

        if self.stock_type == 'TW':
            raw = re.sub(r'\.TW[O]?$', '', stock_input.strip().upper())
            self.stock_id = raw          # 純代碼，如 "2330"
            self.ticker_symbol = f"{raw}.TW"
        else:
            self.stock_id = stock_input.strip().upper()
            self.ticker_symbol = self.stock_id

        self._yf_ticker = yf.Ticker(self.ticker_symbol)
        self._info_cache: Optional[Dict] = None
        self._fin_cache: Optional[pd.DataFrame] = None
        self._bs_cache: Optional[pd.DataFrame] = None
        self._cf_cache: Optional[pd.DataFrame] = None

    # ────────────────────────────────────────────
    # 基本驗證
    # ────────────────────────────────────────────
    def is_valid(self) -> bool:
        # 1. 先嘗試 fast_info（最快）
        try:
            fi = self._yf_ticker.fast_info
            price = getattr(fi, 'last_price', None) or getattr(fi, 'previous_close', None)
            if price and float(price) > 0:
                return True
        except Exception:
            pass

        # 2. 嘗試 info dict
        try:
            info = self.info
            if info and (info.get('regularMarketPrice') or info.get('currentPrice')
                         or info.get('previousClose') or info.get('longName')
                         or info.get('symbol') or info.get('shortName')):
                return True
        except Exception:
            pass

        # 3. 最終備援：抓近5天歷史股價確認是否存在
        try:
            hist = self._yf_ticker.history(period='5d')
            return hist is not None and not hist.empty
        except Exception:
            return False

    # ────────────────────────────────────────────
    # 公司基本資訊
    # ────────────────────────────────────────────
    @property
    def info(self) -> Dict[str, Any]:
        if self._info_cache is None:
            result = {}
            try:
                fi = self._yf_ticker.fast_info
                if fi is not None:
                    result.update({k: v for k, v in fi.__dict__.items() if v is not None})
            except Exception:
                pass
            try:
                raw = self._yf_ticker.info
                if raw and isinstance(raw, dict):
                    result.update(raw)
            except Exception:
                pass
            self._info_cache = result
        return self._info_cache or {}

    def get_company_name(self) -> str:
        name = self.info.get('longName') or self.info.get('shortName') or self.ticker_symbol
        return name

    def get_sector(self) -> str:
        return self.info.get('sector', '')

    def get_industry(self) -> str:
        return self.info.get('industry', '')

    def get_currency(self) -> str:
        return self.info.get('currency', 'TWD' if self.stock_type == 'TW' else 'USD')

    def get_current_price(self) -> Optional[float]:
        info = self.info
        return (info.get('currentPrice') or info.get('regularMarketPrice')
                or info.get('previousClose'))

    # ────────────────────────────────────────────
    # 財務報表（損益表）
    # ────────────────────────────────────────────
    def get_financials_3y(self) -> pd.DataFrame:
        """取得近3年年度損益表（yfinance 格式：列=項目, 欄=日期）"""
        if self._fin_cache is not None:
            return self._fin_cache

        try:
            fin = self._yf_ticker.financials
            if fin is not None and not fin.empty:
                self._fin_cache = fin.iloc[:, :4]  # 最多4年
                return self._fin_cache
        except Exception:
            pass

        # FinMind fallback for Taiwan stocks
        if self.stock_type == 'TW':
            self._fin_cache = self._finmind_income_statement()
            return self._fin_cache

        return pd.DataFrame()

    def _finmind_income_statement(self) -> pd.DataFrame:
        """從 FinMind 取得台股財務報表並轉換為 yfinance 格式"""
        try:
            params = {
                "dataset": "TaiwanStockFinancialStatements",
                "data_id": self.stock_id,
                "start_date": "2021-01-01",
            }
            if self.finmind_token:
                params["token"] = self.finmind_token

            resp = requests.get(self.FINMIND_URL, params=params, timeout=10)
            data = resp.json()

            if data.get('status') != 200 or not data.get('data'):
                return pd.DataFrame()

            df = pd.DataFrame(data['data'])
            df['date'] = pd.to_datetime(df['date'])

            # 每年取最後一季（年度累計）
            df['year'] = df['date'].dt.year
            pivot = df.pivot_table(index='type', columns='date', values='value', aggfunc='last')
            # 只保留年底的欄位
            annual_cols = [c for c in pivot.columns if c.month == 12]
            pivot = pivot[sorted(annual_cols, reverse=True)[:4]]

            # 對齊 yfinance 的欄位名稱
            rename_map = {
                'Revenue': 'Total Revenue',
                'GrossProfit': 'Gross Profit',
                'OperatingIncome': 'Operating Income',
                'NetIncome': 'Net Income',
                'EPS': 'Diluted EPS',
            }
            pivot.index = [rename_map.get(i, i) for i in pivot.index]
            return pivot

        except Exception:
            return pd.DataFrame()

    # ────────────────────────────────────────────
    # 資產負債表
    # ────────────────────────────────────────────
    def get_balance_sheet_3y(self) -> pd.DataFrame:
        if self._bs_cache is not None:
            return self._bs_cache
        try:
            bs = self._yf_ticker.balance_sheet
            if bs is not None and not bs.empty:
                self._bs_cache = bs.iloc[:, :4]
                return self._bs_cache
        except Exception:
            pass

        if self.stock_type == 'TW':
            self._bs_cache = self._finmind_balance_sheet()
            return self._bs_cache

        return pd.DataFrame()

    def _finmind_balance_sheet(self) -> pd.DataFrame:
        try:
            params = {
                "dataset": "TaiwanStockBalanceSheet",
                "data_id": self.stock_id,
                "start_date": "2021-01-01",
            }
            if self.finmind_token:
                params["token"] = self.finmind_token

            resp = requests.get(self.FINMIND_URL, params=params, timeout=10)
            data = resp.json()

            if data.get('status') != 200 or not data.get('data'):
                return pd.DataFrame()

            df = pd.DataFrame(data['data'])
            df['date'] = pd.to_datetime(df['date'])
            pivot = df.pivot_table(index='type', columns='date', values='value', aggfunc='last')
            annual_cols = [c for c in pivot.columns if c.month == 12]
            pivot = pivot[sorted(annual_cols, reverse=True)[:4]]

            rename_map = {
                'TotalAssets': 'Total Assets',
                'TotalLiabilities': 'Total Liabilities Net Minority Interest',
                'StockholdersEquity': 'Stockholders Equity',
                'CurrentAssets': 'Current Assets',
                'CurrentLiabilities': 'Current Liabilities',
                'LongTermDebt': 'Long Term Debt',
                'CashAndCashEquivalents': 'Cash And Cash Equivalents',
            }
            pivot.index = [rename_map.get(i, i) for i in pivot.index]
            return pivot

        except Exception:
            return pd.DataFrame()

    # ────────────────────────────────────────────
    # 現金流量表
    # ────────────────────────────────────────────
    def get_cashflow_3y(self) -> pd.DataFrame:
        if self._cf_cache is not None:
            return self._cf_cache
        try:
            cf = self._yf_ticker.cashflow
            if cf is not None and not cf.empty:
                self._cf_cache = cf.iloc[:, :4]
                return self._cf_cache
        except Exception:
            pass

        if self.stock_type == 'TW':
            self._cf_cache = self._finmind_cashflow()
            return self._cf_cache

        return pd.DataFrame()

    def _finmind_cashflow(self) -> pd.DataFrame:
        try:
            params = {
                "dataset": "TaiwanStockCashFlowsStatement",
                "data_id": self.stock_id,
                "start_date": "2021-01-01",
            }
            if self.finmind_token:
                params["token"] = self.finmind_token

            resp = requests.get(self.FINMIND_URL, params=params, timeout=10)
            data = resp.json()

            if data.get('status') != 200 or not data.get('data'):
                return pd.DataFrame()

            df = pd.DataFrame(data['data'])
            df['date'] = pd.to_datetime(df['date'])
            pivot = df.pivot_table(index='type', columns='date', values='value', aggfunc='last')
            annual_cols = [c for c in pivot.columns if c.month == 12]
            pivot = pivot[sorted(annual_cols, reverse=True)[:4]]

            rename_map = {
                'OperatingActivities': 'Operating Cash Flow',
                'InvestingActivities': 'Investing Cash Flow',
                'FinancingActivities': 'Financing Cash Flow',
                'FreeCashFlow': 'Free Cash Flow',
            }
            pivot.index = [rename_map.get(i, i) for i in pivot.index]
            return pivot

        except Exception:
            return pd.DataFrame()

    # ────────────────────────────────────────────
    # 估值指標
    # ────────────────────────────────────────────
    def get_valuation_metrics(self) -> Dict[str, Any]:
        info = self.info
        return {
            'pe_trailing': info.get('trailingPE'),
            'pe_forward':  info.get('forwardPE'),
            'pb_ratio':    info.get('priceToBook'),
            'ps_ratio':    info.get('priceToSalesTrailing12Months'),
            'ev_ebitda':   info.get('enterpriseToEbitda'),
            'market_cap':  info.get('marketCap'),
            'enterprise_value': info.get('enterpriseValue'),
            'dividend_yield': info.get('dividendYield'),
            'beta':        info.get('beta'),
            'current_price': self.get_current_price(),
            '52w_high':    info.get('fiftyTwoWeekHigh'),
            '52w_low':     info.get('fiftyTwoWeekLow'),
            'revenue_ttm': info.get('totalRevenue'),
            'eps_ttm':     info.get('trailingEps'),
            'roe':         info.get('returnOnEquity'),
            'roa':         info.get('returnOnAssets'),
        }

    # ────────────────────────────────────────────
    # 同業股票清單
    # ────────────────────────────────────────────
    def get_peer_tickers(self) -> List[str]:
        """回傳同業股票代碼清單（含自身）"""
        if self.stock_type == 'TW':
            industry = TAIWAN_STOCK_INDUSTRY_MAP.get(self.stock_id, '')
            if industry and industry in TAIWAN_INDUSTRY_PEERS:
                peers = TAIWAN_INDUSTRY_PEERS[industry]['stocks']
                return [p for p in peers if p != self.ticker_symbol][:4]
        else:
            sector   = self.get_sector()
            industry = self.get_industry()
            # 先用 industry 比對（更精準），再用 sector
            for search_str in [industry, sector]:
                if not search_str:
                    continue
                for key, val in US_INDUSTRY_PEERS.items():
                    if key.lower() in search_str.lower() or search_str.lower() in key.lower():
                        peers = [p for p in val['stocks'] if p != self.ticker_symbol][:4]
                        if peers:
                            return peers
        return []

    def get_peer_industry_name(self) -> str:
        """回傳所屬產業名稱"""
        if self.stock_type == 'TW':
            return TAIWAN_STOCK_INDUSTRY_MAP.get(self.stock_id, self.get_industry())
        return self.get_sector()

    # ────────────────────────────────────────────
    # 歷史股價
    # ────────────────────────────────────────────
    def get_historical_prices(self, period: str = "1y") -> pd.DataFrame:
        try:
            return self._yf_ticker.history(period=period)
        except Exception:
            return pd.DataFrame()

    # ────────────────────────────────────────────
    # 輔助工具
    # ────────────────────────────────────────────
    def safe_get_row(self, df: pd.DataFrame, keys: list) -> Optional[pd.Series]:
        """嘗試多個可能的列名稱，回傳第一個找到的列"""
        if df is None or df.empty:
            return None
        for key in keys:
            if key in df.index:
                return df.loc[key]
            # 部分比對
            matches = [i for i in df.index if key.lower() in i.lower()]
            if matches:
                return df.loc[matches[0]]
        return None

    def format_currency(self, value: float) -> str:
        """格式化金額顯示"""
        if self.stock_type == 'TW':
            # 台股財務單位通常是千元
            if abs(value) >= 1e9:
                return f"NT${value/1e9:.2f}B"
            elif abs(value) >= 1e6:
                return f"NT${value/1e6:.2f}M"
            elif abs(value) >= 1e3:
                return f"NT${value/1e3:.2f}K"
            return f"NT${value:.0f}"
        else:
            if abs(value) >= 1e12:
                return f"${value/1e12:.2f}T"
            elif abs(value) >= 1e9:
                return f"${value/1e9:.2f}B"
            elif abs(value) >= 1e6:
                return f"${value/1e6:.2f}M"
            return f"${value:.0f}"
