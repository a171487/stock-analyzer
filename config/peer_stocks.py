# 台股同業比較清單（依產業分類）
TAIWAN_INDUSTRY_PEERS = {
    "晶圓代工": {
        "stocks": ["2330.TW", "2303.TW", "3711.TW"],
        "names": {"2330.TW": "台積電", "2303.TW": "聯電", "3711.TW": "日月光投控"}
    },
    "IC設計": {
        "stocks": ["2454.TW", "3034.TW", "2408.TW", "6770.TW", "3443.TW"],
        "names": {"2454.TW": "聯發科", "3034.TW": "聯詠", "2408.TW": "南亞科", "6770.TW": "力積電", "3443.TW": "創意"}
    },
    "記憶體": {
        "stocks": ["3474.TW", "2344.TW", "4256.TW"],
        "names": {"3474.TW": "華亞科", "2344.TW": "華邦電", "4256.TW": "旺宏"}
    },
    "PCB": {
        "stocks": ["2382.TW", "3037.TW", "8046.TW", "3231.TW", "6269.TW"],
        "names": {"2382.TW": "廣達", "3037.TW": "欣興", "8046.TW": "南電", "3231.TW": "緯創", "6269.TW": "台郡"}
    },
    "散熱": {
        "stocks": ["3105.TW", "8499.TW", "3230.TW"],
        "names": {"3105.TW": "穩懋", "8499.TW": "通嘉", "3230.TW": "錡光"}
    },
    "光通訊": {
        "stocks": ["3406.TW", "3489.TW", "6541.TW", "4968.TW"],
        "names": {"3406.TW": "玉晶光", "3489.TW": "森霸", "6541.TW": "泰碩", "4968.TW": "立積"}
    },
    "低軌衛星": {
        "stocks": ["3617.TW", "6508.TW", "3499.TW"],
        "names": {"3617.TW": "碩天", "6508.TW": "介面", "3499.TW": "環旭電"}
    },
    "電力設備": {
        "stocks": ["1590.TW", "2308.TW", "1504.TW"],
        "names": {"1590.TW": "亞德客", "2308.TW": "台達電", "1504.TW": "東元"}
    },
    "金融-銀行": {
        "stocks": ["2882.TW", "2881.TW", "2884.TW", "2886.TW", "2891.TW"],
        "names": {"2882.TW": "國泰金", "2881.TW": "富邦金", "2884.TW": "玉山金", "2886.TW": "兆豐金", "2891.TW": "中信金"}
    },
    "CCL基板": {
        "stocks": ["8069.TW", "6274.TW", "3491.TW"],
        "names": {"8069.TW": "元太", "6274.TW": "台燿", "3491.TW": "昇貿"}
    },
    "伺服器/NB": {
        "stocks": ["2317.TW", "2382.TW", "3231.TW", "2356.TW"],
        "names": {"2317.TW": "鴻海", "2382.TW": "廣達", "3231.TW": "緯創", "2356.TW": "英業達"}
    },
}

# 美股同業清單
US_INDUSTRY_PEERS = {
    "Semiconductors": {
        "stocks": ["NVDA", "AMD", "INTC", "QCOM", "AVGO", "MU", "TSM"],
        "names": {"NVDA": "NVIDIA", "AMD": "AMD", "INTC": "Intel", "QCOM": "Qualcomm", "AVGO": "Broadcom", "MU": "Micron", "TSM": "TSMC"}
    },
    "Semiconductor Equipment & Materials": {
        "stocks": ["AMAT", "LRCX", "KLAC", "ASML", "ONTO"],
        "names": {"AMAT": "Applied Materials", "LRCX": "Lam Research", "KLAC": "KLA Corp", "ASML": "ASML", "ONTO": "Onto Innovation"}
    },
    "Technology": {
        "stocks": ["AAPL", "MSFT", "GOOGL", "META", "AMZN"],
        "names": {"AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet", "META": "Meta", "AMZN": "Amazon"}
    },
    "Electric Vehicles": {
        "stocks": ["TSLA", "RIVN", "GM", "F", "NIO"],
        "names": {"TSLA": "Tesla", "RIVN": "Rivian", "GM": "GM", "F": "Ford", "NIO": "NIO"}
    },
    "Financial Services": {
        "stocks": ["JPM", "BAC", "WFC", "GS", "MS"],
        "names": {"JPM": "JPMorgan", "BAC": "BofA", "WFC": "Wells Fargo", "GS": "Goldman", "MS": "Morgan Stanley"}
    },
}

# 台股代碼 → 產業對應（主要個股）
TAIWAN_STOCK_INDUSTRY_MAP = {
    "2330": "晶圓代工",  # 台積電
    "2303": "晶圓代工",  # 聯電
    "2454": "IC設計",    # 聯發科
    "3034": "IC設計",    # 聯詠
    "2408": "記憶體",    # 南亞科
    "2344": "記憶體",    # 華邦電
    "2382": "伺服器/NB", # 廣達
    "2317": "伺服器/NB", # 鴻海
    "3231": "伺服器/NB", # 緯創
    "2356": "伺服器/NB", # 英業達
    "3037": "PCB",       # 欣興
    "8046": "PCB",       # 南電
    "2308": "電力設備",  # 台達電
    "1590": "電力設備",  # 亞德客
    "2882": "金融-銀行", # 國泰金
    "2881": "金融-銀行", # 富邦金
    "2884": "金融-銀行", # 玉山金
    "3406": "光通訊",    # 玉晶光
    "4968": "光通訊",    # 立積
    "3617": "低軌衛星",  # 碩天
    "6508": "低軌衛星",  # 介面
    "8069": "CCL基板",   # 元太
}
