"""
產業知識庫
涵蓋台股主要產業與美股主要板塊
資料基準：2025 年 Q1，中長期展望至 2028-2030
"""

INDUSTRY_KNOWLEDGE = {

    # ════════════════════════════════════════
    # 台股產業
    # ════════════════════════════════════════

    "晶圓代工": {
        "full_name": "晶圓代工（IC Foundry）",
        "market_size_now":  "約 USD 1,350 億（2024）",
        "market_size_2028": "約 USD 2,100 億（2028E）",
        "cagr":    "10～13%（2024-2028）",
        "key_themes": [
            "AI 加速器（GPU/TPU/自研 ASIC）帶動先進製程需求爆發",
            "CoWoS / SoIC 先進封裝成全球算力瓶頸",
            "地緣政治驅動晶圓廠「去中心化」：美、日、歐補貼建廠",
            "HPC（高效能運算）與 AI 推論端持續放量",
            "2nm / 1.6nm 節點進入量產競賽",
        ],
        "strengths_template": [
            "先進製程技術壁壘極高，領先同業 1-2 個節點",
            "規模效應顯著，高資本支出形成難以複製的護城河",
            "客戶高度黏著（fabless 轉換成本極高）",
            "與 ASML、AMAT 等設備商深度戰略合作",
        ],
        "weaknesses_template": [
            "資本支出龐大（每年數千億台幣），景氣反轉時折舊壓力沉重",
            "高度依賴少數頂級客戶（Apple、NVIDIA、AMD），客戶集中風險",
            "台灣地緣政治風險為長期折價因素",
        ],
        "catalysts": [
            "AI 推論端 Edge AI 裝置普及帶動消費性電子復甦",
            "車用半導體自駕/ADAS 需求長線確定性高",
            "美國 N2 廠（Arizona）量產帶來美系客戶轉單效益",
            "先進封裝（CoWoS）產能擴充解除 AI 算力瓶頸",
            "SoIC 3D 堆疊技術商業化創造新市場",
        ],
        "risks": [
            "中美科技戰升溫，出口管制（EAR）範圍持續擴大",
            "Intel Foundry（IFS）/ Samsung 18A 技術進展追趕",
            "全球景氣下行導致消費性電子需求大幅萎縮",
            "兩岸關係緊張造成地緣政治溢價波動",
            "先進製程良率爬坡不如預期",
        ],
        "policy": [
            "美國 CHIPS 法案：520 億美元補貼本土晶圓製造（含稅抵免）",
            "日本 METI：補貼 JASM 一/二期、Rapidus 2nm 計畫",
            "歐洲 Chips Act：目標 2030 年占全球晶片產量 20%",
            "台灣國發基金：支持在地研發與人才培育",
            "中國「大基金三期」：加速半導體自主化替代",
        ],
        "global_peers": ["TSM（台積電）", "Samsung Foundry", "Intel IFS", "GlobalFoundries (GFS)", "UMC（聯電 2303）"],
        "tw_ticker_leader": "2330",
    },

    "IC設計": {
        "full_name": "IC 設計（Fabless）",
        "market_size_now":  "約 USD 1,850 億（2024）",
        "market_size_2028": "約 USD 3,200 億（2028E）",
        "cagr":    "14～18%（2024-2028）",
        "key_themes": [
            "AI 晶片設計需求：NPU/GPU/自研 ASIC 全面爆發",
            "智慧型手機 AP 整合 AI 引擎進入換機週期",
            "車載 SoC 進入高速成長期（ADAS L2/L3）",
            "WiFi 7 / 5G 毫米波連線晶片滲透率提升",
            "Edge AI 推論晶片走向輕量化與低功耗",
        ],
        "strengths_template": [
            "輕資產商業模式，毛利率結構優於製造業",
            "技術創新速度快，應用場景廣泛",
            "台灣在通訊、影像、電源管理 IC 具全球領導地位",
        ],
        "weaknesses_template": [
            "高度依賴台積電等外部代工，製程產能受制於人",
            "研發費用率高，獲利彈性受景氣影響大",
            "中國山寨競爭對中低階產品毛利構成壓力",
        ],
        "catalysts": [
            "生成式 AI 終端（AI PC / AI Phone）換機潮",
            "車載 MCU/SoC 長期訂單能見度高",
            "AR/VR 裝置普及帶動顯示驅動 IC / 感測器需求",
            "電動車電源管理 IC（PMIC）需求倍增",
        ],
        "risks": [
            "IC 設計景氣循環性強，客戶庫存去化週期長",
            "美中出口管制影響中國市場業務",
            "先進製程競爭激烈，研發費用持續攀升",
            "NVIDIA / AMD 布局 AI 專屬晶片擠壓中階市場",
        ],
        "policy": [
            "台灣智慧晶片發展方案：支持 AI 晶片設計人才",
            "美國 EDA 工具出口限制衝擊中國 IC 設計廠",
            "中國「芯片替代」政策加速國產 IC 滲透率",
        ],
        "global_peers": ["NVIDIA (NVDA)", "Qualcomm (QCOM)", "AMD", "MediaTek（聯發科 2454）", "Marvell (MRVL)"],
        "tw_ticker_leader": "2454",
    },

    "記憶體": {
        "full_name": "記憶體（DRAM / NAND Flash）",
        "market_size_now":  "約 USD 1,250 億（2024）",
        "market_size_2028": "約 USD 2,000 億（2028E）",
        "cagr":    "12～16%（2024-2028）",
        "key_themes": [
            "HBM（高頻寬記憶體）隨 AI GPU 需求急速增長",
            "DDR5 / LPDDR5X 換代推升 ASP（平均售價）",
            "NAND Flash 企業級 SSD 需求強勁（AI 資料中心）",
            "記憶體週期觸底，進入新一輪上升週期",
        ],
        "strengths_template": [
            "HBM 技術門檻極高，具備先發優勢廠商受益巨大",
            "景氣觸底後 ASP 反彈彈性強",
        ],
        "weaknesses_template": [
            "週期性強烈，供過於求時獲利快速惡化",
            "資本支出極為龐大，財務槓桿風險高",
            "台廠在 HBM 技術落後三星/SK 海力士",
        ],
        "catalysts": [
            "AI 伺服器 HBM 需求持續超供，ASP 易漲難跌",
            "PC / 手機換機潮刺激 DRAM / NAND 需求",
            "車用記憶體（功能安全規格）長線穩定訂單",
        ],
        "risks": [
            "三星激進擴產造成供過於求，ASP 急跌",
            "中國 CXMT（長鑫存儲）技術追趕衝擊中低階市場",
            "景氣反轉時存貨跌價損失侵蝕獲利",
        ],
        "policy": [
            "美國限制先進記憶體（HBM）對中出口",
            "韓國政府補貼三星/SK 海力士保持技術領先",
        ],
        "global_peers": ["Samsung (005930.KS)", "SK Hynix (000660.KS)", "Micron (MU)", "Nanya（南亞科 2408）", "Winbond（華邦電 2344）"],
        "tw_ticker_leader": "3474",
    },

    "PCB": {
        "full_name": "印刷電路板（PCB / ABF 載板）",
        "market_size_now":  "約 USD 760 億（2024）",
        "market_size_2028": "約 USD 1,100 億（2028E）",
        "cagr":    "8～11%（2024-2028）",
        "key_themes": [
            "ABF 載板（AI GPU / HPC 封裝基板）需求爆發且供給緊張",
            "高速高頻材料（高 Tg / 低 Dk）在 AI 伺服器中普及",
            "HDI / SLP 隨智慧型手機輕薄化持續升級",
            "車用 PCB 因電動化、智慧化快速增長",
        ],
        "strengths_template": [
            "ABF 載板技術門檻高，良率與材料研發壁壘明顯",
            "台廠在 PCB 全球市占率穩居前三，客戶關係穩固",
        ],
        "weaknesses_template": [
            "ABF 載板擴產週期長（3-4年），錯過景氣高峰損失大",
            "消費性 PCB 受景氣波動影響，庫存調整時利用率下滑",
        ],
        "catalysts": [
            "AI 伺服器 ABF 載板長期供不應求，ASP 持續上漲",
            "車用 PCB 每台車板材用量持續增加",
            "次世代通訊（WiFi7 / 5G RedCap）刺激換代需求",
        ],
        "risks": [
            "中國 PCB 廠低價競爭壓縮中低階利潤",
            "擴產投資集中，景氣反轉時折舊沉重",
            "原材料（銅箔/CCL）價格波動侵蝕毛利",
        ],
        "policy": [
            "台灣 PCB 公會推動產業升級，補助先進材料研發",
            "美國 IPC 標準升級帶動高階 PCB 需求",
        ],
        "global_peers": ["Tripod（健鼎 3044）", "Unimicron（欣興 3037）", "Nan Ya PCB（南電 8046）", "TTM Technologies (TTMI)", "AT&S (ATS)"],
        "tw_ticker_leader": "3037",
    },

    "散熱": {
        "full_name": "散熱解決方案（Thermal Management）",
        "market_size_now":  "約 USD 150 億（2024）",
        "market_size_2028": "約 USD 280 億（2028E）",
        "cagr":    "16～20%（2024-2028）",
        "key_themes": [
            "AI GPU 熱設計功耗（TDP）突破 1000W，散熱需求質變",
            "液冷（浸沒式/冷板式）取代傳統風冷成主流",
            "冷板（Cold Plate）、CDU（製冷配液機組）需求急增",
            "AI 伺服器每台散熱成本從百元增至數千美元",
        ],
        "strengths_template": [
            "液冷技術門檻高，具備設計能力的廠商稀缺",
            "與 NVIDIA / AMD 深度共同設計，切入難被替代",
            "台灣散熱廠客戶關係橫跨 Google / Microsoft / Meta",
        ],
        "weaknesses_template": [
            "產品規格隨客戶訂製，標準化程度低、換線成本高",
            "液冷材料（特殊合金/工作液）供應鏈尚未成熟",
        ],
        "catalysts": [
            "GB200 / B300 等新一代 AI 加速器熱密度再翻倍",
            "超大規模資料中心（Hyperscaler）全面液冷化",
            "浸沒式液冷進入 ODM 伺服器量產階段",
        ],
        "risks": [
            "客戶自製（Insource）散熱模組降低外部採購比重",
            "中國散熱廠低成本切入，壓縮中階產品利潤",
            "液冷標準尚未統一，技術路線選錯風險",
        ],
        "policy": [
            "IEA 要求資料中心提高 PUE，驅動液冷滲透率",
            "台灣政府鼓勵節能散熱技術研發補助",
        ],
        "global_peers": ["Vertiv (VRT)", "Modine (MOD)", "Acer ITS", "雙鴻（3324）", "奇鋐（3017）"],
        "tw_ticker_leader": "3105",
    },

    "光通訊": {
        "full_name": "光通訊元件（Optical Communication）",
        "market_size_now":  "約 USD 180 億（2024）",
        "market_size_2028": "約 USD 380 億（2028E）",
        "cagr":    "20～25%（2024-2028）",
        "key_themes": [
            "AI 資料中心內部互連頻寬需求推升光模組規格（400G→800G→1.6T）",
            "CPO（共封裝光學）技術推進，光電整合加速",
            "矽光子（Silicon Photonics）降低成本、提升整合度",
            "低軌衛星星鏈地面站及星間鏈路光通訊元件需求",
        ],
        "strengths_template": [
            "精密光學元件製造壁壘高，台廠在 VCSEL / 鏡頭良率領先",
            "與 Lumentum / II-VI 等國際大廠深度合作",
        ],
        "weaknesses_template": [
            "光模組製造高度勞力密集，自動化程度提升是課題",
            "規格迭代快，研發費用率偏高",
        ],
        "catalysts": [
            "800G / 1.6T 光模組在 AI 叢集大規模部署",
            "CPO 技術量產帶動新一代元件需求",
            "Starlink 規模擴大帶動光通訊衛星需求",
        ],
        "risks": [
            "中國廠商（中際旭創等）低價競爭壓縮毛利",
            "CPO 普及後部分傳統光模組需求受壓制",
            "客戶庫存調整造成短期訂單波動",
        ],
        "policy": [
            "美國限制對中出口高端光模組（BIS 規定）",
            "歐盟 5G 安全規範排除中國設備，間接利好台廠",
        ],
        "global_peers": ["Lumentum (LITE)", "Coherent (COHR)", "II-VI", "中際旭創 (300308.SZ)", "InnoLight"],
        "tw_ticker_leader": "3406",
    },

    "低軌衛星": {
        "full_name": "低軌衛星（LEO Satellite）生態系",
        "market_size_now":  "約 USD 90 億（2024）",
        "market_size_2028": "約 USD 400 億（2028E）",
        "cagr":    "45～55%（2024-2028）",
        "key_themes": [
            "SpaceX Starlink 持續擴張，帶動地面站及終端設備需求",
            "Amazon Kuiper、OneWeb 等競爭者加速部署",
            "LEO 衛星軍事通訊需求（烏俄衝突後備受重視）",
            "台廠在射頻元件（PA/LNA）、毫米波天線模組具競爭力",
        ],
        "strengths_template": [
            "相位陣列天線（Phased Array）元件需求高度集中於少數台廠",
            "毫米波 RF 元件製造技術壁壘高，新進者門檻極高",
        ],
        "weaknesses_template": [
            "客戶集中於 SpaceX 單一大客戶，議價能力受限",
            "衛星計畫時間表不確定性高，訂單能見度短",
        ],
        "catalysts": [
            "Starlink Gen3 / Kuiper 量產帶動天線模組大量出貨",
            "各國軍方採購 LEO 通訊系統推升軍規規格元件",
            "台灣政府推動低軌衛星本土化供應鏈",
        ],
        "risks": [
            "SpaceX 自製關鍵元件（垂直整合）降低外購比重",
            "衛星發射計畫延遲導致訂單遞延",
            "地緣政治影響衛星許可證核發",
        ],
        "policy": [
            "台灣 NCC 推動低軌衛星頻譜管理與本土化政策",
            "美國 FCC 快速核准 SpaceX / Amazon 衛星計畫",
            "軍事通訊規格認證（MIL-SPEC）門檻高，利好現有供應商",
        ],
        "global_peers": ["SpaceX（私有）", "Amazon Kuiper（私有）", "Viasat (VSAT)", "SES (SESG.PA)", "台廠：碩天、介面"],
        "tw_ticker_leader": "3617",
    },

    "電力設備": {
        "full_name": "電力設備與自動化（Power Equipment）",
        "market_size_now":  "約 USD 1,100 億（2024）",
        "market_size_2028": "約 USD 1,700 億（2028E）",
        "cagr":    "11～14%（2024-2028）",
        "key_themes": [
            "AI 資料中心電力基礎建設需求（UPS/PDU/電網升級）",
            "電動車充電基礎建設全球爆發",
            "工廠自動化（工業 4.0）帶動驅動器/控制器需求",
            "再生能源（風力/太陽能）帶動電力轉換設備",
            "電網現代化（Smart Grid）長期投資週期",
        ],
        "strengths_template": [
            "工業自動化領域有定價權，毛利率穩定且高",
            "台達電等龍頭品牌在亞洲、歐洲均有直銷通路",
            "電源管理技術積累深厚，轉型 AI 電源需求快速",
        ],
        "weaknesses_template": [
            "部分產品受中國競爭者低價壓力（傳統電源）",
            "工廠自動化訂單具長週期特性，短期業績波動",
        ],
        "catalysts": [
            "AI 資料中心電力密度提升，帶動高功率 UPS/電源供應需求",
            "電動車充電樁（EVSE）全球布建加速",
            "工業電動化：馬達驅動器、伺服系統需求強勁",
        ],
        "risks": [
            "原物料（銅、稀土）成本上漲侵蝕毛利",
            "中美貿易戰關稅影響出口利潤",
            "全球資本支出收縮時工業訂單延遲",
        ],
        "policy": [
            "美國 IRA（通膨削減法案）：電動車/再生能源補貼",
            "歐盟 Green Deal：2035 年禁售燃油車，帶動電動化",
            "台灣離岸風電政策驅動變壓器/電纜需求",
        ],
        "global_peers": ["Eaton (ETN)", "ABB (ABBN.SW)", "Schneider Electric (SU.PA)", "台達電（2308）", "亞德客（1590）"],
        "tw_ticker_leader": "2308",
    },

    "CCL基板": {
        "full_name": "覆銅板（CCL）/ 高頻高速材料",
        "market_size_now":  "約 USD 120 億（2024）",
        "market_size_2028": "約 USD 200 億（2028E）",
        "cagr":    "13～17%（2024-2028）",
        "key_themes": [
            "AI 伺服器高速傳輸要求（低損耗 CCL）帶動材料升級",
            "5G / WiFi 7 高頻規格提升對低 Dk / 低 Df 材料需求",
            "ABF 基板材料缺口推升高端 CCL 議價空間",
        ],
        "strengths_template": [
            "高頻高速 CCL 技術壁壘高，日、台廠主導市場",
            "與 PCB 廠深度綁定，客戶轉換成本高",
        ],
        "weaknesses_template": [
            "傳統 FR4 CCL 市場受中國廠商競爭壓縮",
            "研發週期長（新材料認證 2-3 年），獲利回收慢",
        ],
        "catalysts": [
            "AI 高速傳輸標準（224G SerDes）推升材料規格需求",
            "車用電子 CCL 需求隨電動車滲透率提升",
        ],
        "risks": [
            "玻纖布、電子級銅箔等上游原材料漲價",
            "需求高度集中於少數 PCB/ABF 載板廠",
        ],
        "policy": ["PCB 產業政策連動，同步受益於台灣 PCB 升級方案"],
        "global_peers": ["Panasonic（松下）", "Rogers (ROG)", "台燿（6274）", "生益電子（600183.SS）"],
        "tw_ticker_leader": "8069",
    },

    "伺服器/NB": {
        "full_name": "伺服器 / 筆電 ODM（Server & Notebook ODM）",
        "market_size_now":  "約 USD 2,000 億（2024，含AI伺服器）",
        "market_size_2028": "約 USD 3,800 億（2028E）",
        "cagr":    "17～22%（AI Server部分，2024-2028）",
        "key_themes": [
            "AI 伺服器（GPU Cluster）出貨成為主要成長引擎",
            "液冷伺服器、高功率供電（48V）成為新標準",
            "ODM 廠承接 Hyperscaler 白牌設計需求大增",
            "筆電進入 AI PC 換機週期（NPU 整合）",
        ],
        "strengths_template": [
            "台灣 ODM 廠在快速交貨、彈性產能上具競爭優勢",
            "與 NVIDIA / AMD 生態系深度整合，GB200 NVL 優先供應",
        ],
        "weaknesses_template": [
            "毛利率偏薄（代工模式），受原物料及匯率波動影響大",
            "AI 伺服器零組件採購（HBM/CoWoS）受客戶管控",
        ],
        "catalysts": [
            "GB200 / B300 等新一代 AI 伺服器量產出貨",
            "AI PC（Copilot+）換機週期 2025-2026 年放量",
            "Hyperscaler 資本支出持續上修",
        ],
        "risks": [
            "AI 伺服器毛利率偏低（相較記憶體/GPU），獲利提升有限",
            "中國 AI 算力限制可能衝擊部分出口訂單",
            "供應鏈中 CoWoS / HBM 零件供應緊張影響出貨",
        ],
        "policy": [
            "美國 BIS 對中 AI 晶片/伺服器出口管制（A100/H100 禁令延伸）",
            "台灣政府鼓勵 AI 資料中心落地（電力/土地優惠）",
        ],
        "global_peers": ["鴻海（2317）", "廣達（2382）", "緯創（3231）", "Super Micro (SMCI)", "Dell (DELL)"],
        "tw_ticker_leader": "2317",
    },

    "金融-銀行": {
        "full_name": "金融控股 / 商業銀行",
        "market_size_now":  "台灣銀行業總資產 約 NTD 70 兆（2024）",
        "market_size_2028": "穩定成長，CAGR 約 4-6%",
        "cagr":    "4～6%（2024-2028）",
        "key_themes": [
            "台灣壽險資產海外配置比重高，匯率波動影響獲利",
            "升息週期利差（NIM）擴大，銀行業利潤改善",
            "數位金融加速（Open Banking / 純網銀）",
            "財富管理（WM）手收貢獻度持續提升",
            "FSCMA 資本要求（IFRS 17）下壽險體質分化",
        ],
        "strengths_template": [
            "大型金控品牌信譽強，存款基礎穩定",
            "海外布局（東南亞）提供長期成長動能",
        ],
        "weaknesses_template": [
            "台灣本地市場競爭激烈，利差偏低",
            "壽險業受匯率及股市波動影響大",
        ],
        "catalysts": [
            "AI 財富管理顧問降低服務成本、提升手收",
            "東南亞分支機構受惠於當地經濟成長",
            "股市熱絡帶動財富管理及手續費收入",
        ],
        "risks": [
            "降息週期壓縮利差（NIM）",
            "中國房地產暴露風險（金融業共同議題）",
            "台幣升值侵蝕海外資產帳面獲利",
        ],
        "policy": [
            "金管會：壽險業資本適足率（RBC）強化要求",
            "央行升降息政策直接影響利差收益",
            "開放純網銀競爭（PURE Play FinTech）",
        ],
        "global_peers": ["JP Morgan (JPM)", "HSBC (HSBA.L)", "DBS Group (D05.SI)", "國泰金（2882）", "富邦金（2881）"],
        "tw_ticker_leader": "2882",
    },

    # ════════════════════════════════════════
    # 美股產業
    # ════════════════════════════════════════

    "Semiconductors": {
        "full_name": "半導體（美股）",
        "market_size_now":  "約 USD 6,200 億（2024）",
        "market_size_2028": "約 USD 1.0 兆（2028E）",
        "cagr":    "12～15%（2024-2028）",
        "key_themes": [
            "AI 加速器（NVIDIA H100/B200/GB200）市場持續擴張",
            "先進封裝（CoWoS/SoIC）成為 AI 算力關鍵瓶頸",
            "客製化 ASIC 晶片（Broadcom/Marvell 協助設計）快速崛起",
            "車載半導體（ADC/MCU/SoC）受益自動駕駛需求",
            "量子運算/光子晶片長線技術投資",
        ],
        "strengths_template": [
            "美系半導體廠在 EDA 工具、IP 核心具有全球壟斷地位",
            "NVIDIA 在 AI 訓練推論生態系建立極高轉換成本",
        ],
        "weaknesses_template": [
            "高度依賴台積電先進製程代工，供應鏈集中風險",
            "AI 晶片估值倍數偏高，對成長預期敏感",
        ],
        "catalysts": [
            "Blackwell / Rubin 架構更新持續推高 ASP",
            "自訓練 AI 模型（Agentic AI）帶動推論端需求",
            "邊緣 AI（Edge AI）裝置普及創造億級晶片市場",
        ],
        "risks": [
            "美中出口管制升級影響中國市場收入",
            "AI 資本支出泡沫疑慮，Hyperscaler 收縮開支",
            "ARM / RISC-V 架構挑戰 x86 生態系",
        ],
        "policy": [
            "美國 CHIPS & Science Act：527 億補貼本土半導體",
            "BIS 出口管制：H100/A100/B200 禁止對中出貨",
            "TSMC / Samsung / Intel 美國建廠稅抵免",
        ],
        "global_peers": ["NVIDIA (NVDA)", "AMD (AMD)", "Intel (INTC)", "Qualcomm (QCOM)", "Broadcom (AVGO)"],
        "tw_ticker_leader": "2330",
    },

    "Technology": {
        "full_name": "科技（美股 Big Tech）",
        "market_size_now":  "Mag 7 合計市值逾 USD 15 兆（2024）",
        "market_size_2028": "持續增長，AI 商業化為核心",
        "cagr":    "12～18%（各公司差異大）",
        "key_themes": [
            "生成式 AI（ChatGPT/Gemini/Claude）商業化加速",
            "雲端三巨頭（AWS/Azure/GCP）AI 基礎建設競賽",
            "廣告科技結合 AI 精準行銷效益提升",
            "AI Agent / Agentic Workflow 企業應用普及",
            "量子運算商業化時程提前（Google/IBM/Microsoft）",
        ],
        "strengths_template": [
            "平台效應與網路效應構成極深護城河",
            "AI 訓練資料量與算力規模遠超競爭者",
            "雲端業務黏著度高，企業轉換成本大",
        ],
        "weaknesses_template": [
            "監管風險（反壟斷調查）在歐美持續升溫",
            "AI 研發資本支出龐大，短期 ROI 不確定",
        ],
        "catalysts": [
            "生成式 AI 訂閱制（Copilot/Gemini Pro）滲透率提升",
            "AI 廣告投放效率改善，帶動 CPM/CPC 上漲",
            "量子運算實際應用案例突破（化學/金融/物流）",
        ],
        "risks": [
            "反壟斷訴訟：DOJ 對 Google 廣告/搜尋市場裁定",
            "AI 生成內容版權爭議（訓練資料授權問題）",
            "消費者隱私法規（GDPR/CCPA）衝擊廣告收入",
        ],
        "policy": [
            "歐盟 AI Act：高風險 AI 系統嚴格監管",
            "美國 EO on AI Safety：模型安全評估要求",
            "反壟斷執法：Google / Apple / Meta 持續面臨訴訟",
        ],
        "global_peers": ["Apple (AAPL)", "Microsoft (MSFT)", "Google (GOOGL)", "Meta (META)", "Amazon (AMZN)"],
        "tw_ticker_leader": None,
    },

    "Electric Vehicles": {
        "full_name": "電動車（EV）",
        "market_size_now":  "約 USD 5,000 億（2024）",
        "market_size_2028": "約 USD 1.1 兆（2028E）",
        "cagr":    "20～25%（2024-2028）",
        "key_themes": [
            "全固態電池技術突破時間表提前至 2027-2028",
            "800V 高壓平台普及加速充電速度",
            "自動駕駛 FSD / Autopilot 商業化進程",
            "中國 EV 廠（比亞迪/蔚來）價格戰衝擊全球市場",
            "EV 銷量成長放緩，混合動力（HEV）需求超預期",
        ],
        "strengths_template": [
            "Tesla FSD 自動駕駛數據資產難以複製",
            "品牌溢價與 Supercharger 充電網絡壁壘",
        ],
        "weaknesses_template": [
            "純電銷量成長放緩，消費者充電焦慮未完全解除",
            "中國競爭者（BYD）成本優勢明顯",
        ],
        "catalysts": [
            "Robotaxi 商業化（Cybercab）帶動新收入來源",
            "全固態電池量產突破提升能量密度、降低成本",
            "歐盟 EV 補貼政策延續刺激需求",
        ],
        "risks": [
            "中國 EV 價格戰輸出全球，壓縮各地車廠利潤",
            "充電基礎建設速度跟不上銷量成長",
            "政治因素：美國 EV 稅抵免政策可能被削減",
        ],
        "policy": [
            "美國 IRA：EV 購車最高 7,500 美元稅抵免",
            "歐盟 2035 年禁售燃油車（含部分豁免）",
            "中國 NEV 積分政策推動電動化",
        ],
        "global_peers": ["Tesla (TSLA)", "BYD (1211.HK)", "Rivian (RIVN)", "GM (GM)", "Ford (F)"],
        "tw_ticker_leader": None,
    },

    "Financial Services": {
        "full_name": "金融服務（美股）",
        "market_size_now":  "美國銀行業總資產逾 USD 24 兆（2024）",
        "market_size_2028": "穩定增長 4-7%",
        "cagr":    "4～7%（2024-2028）",
        "key_themes": [
            "AI 驅動的財富管理與風控自動化",
            "降息週期對銀行 NIM 的壓力測試",
            "加密貨幣監管明朗化（比特幣 ETF 通過）",
            "私募信貸（Private Credit）快速崛起",
            "FinTech 挑戰傳統銀行支付與存款業務",
        ],
        "strengths_template": [
            "資本充足率強、品牌公信力高",
            "AI 風控系統降低不良貸款率",
        ],
        "weaknesses_template": [
            "降息環境壓縮 NIM，利息收入下降",
            "監管資本要求提升（Basel III 終局）增加成本",
        ],
        "catalysts": [
            "AI 財富管理顧問降低人力成本、提升 AUM",
            "私募信貸市場擴張帶來手收機會",
            "併購交易復甦帶動 IB 業務回暖",
        ],
        "risks": [
            "商業房地產（CRE）貸款損失擴大",
            "降息過快壓縮利差，存款成本黏性高",
            "金融科技（Stripe / Robinhood）瓜分年輕客群",
        ],
        "policy": [
            "Fed 降息路徑：影響 NIM 與資產定價",
            "Basel III 終局規則：提高資本緩衝要求",
            "CFPB 消費者保護法規：限制手續費收取",
        ],
        "global_peers": ["JPMorgan (JPM)", "Bank of America (BAC)", "Goldman Sachs (GS)", "Morgan Stanley (MS)", "Citigroup (C)"],
        "tw_ticker_leader": "2882",
    },

    "Semiconductor Equipment & Materials": {
        "full_name": "半導體設備與材料",
        "market_size_now":  "約 USD 1,100 億（2024）",
        "market_size_2028": "約 USD 1,800 億（2028E）",
        "cagr":    "12～15%（2024-2028）",
        "key_themes": [
            "EUV / High-NA EUV 設備進入量產（ASML 壟斷）",
            "ALD / CVD 等薄膜設備隨先進節點持續升級",
            "AI 驅動晶圓廠擴產，整體設備市場穩定成長",
            "半導體材料：超純化學品、特殊氣體需求增長",
        ],
        "strengths_template": [
            "ASML EUV 設備全球壟斷，定價能力極強",
            "設備裝機後維護合約創造穩定經常性收入",
        ],
        "weaknesses_template": [
            "資本密集型產業，客戶資本支出週期影響訂單",
            "出口管制限制對中國的設備銷售",
        ],
        "catalysts": [
            "High-NA EUV 進入量產（Intel / TSMC 2025-2026）",
            "Middle East / 東南亞晶圓廠建設潮帶動設備需求",
        ],
        "risks": [
            "美國對中半導體設備出口管制持續擴大",
            "晶圓廠資本支出縮減（景氣下行）",
        ],
        "policy": [
            "美日荷三國聯合半導體設備出口管制",
            "中國自製設備追趕（中微、北方華創）",
        ],
        "global_peers": ["ASML (ASML)", "Applied Materials (AMAT)", "Lam Research (LRCX)", "KLA (KLAC)", "Tokyo Electron (8035.T)"],
        "tw_ticker_leader": None,
    },

    # ════════════════════════════════════════
    # 補充台股產業
    # ════════════════════════════════════════

    "消費電子": {
        "full_name": "消費電子 / 系統品牌（Consumer Electronics）",
        "market_size_now":  "約 USD 1,100 億（2024，含 PC/平板/周邊）",
        "market_size_2028": "約 USD 1,350 億（2028E）",
        "cagr":    "4～6%（2024-2028）",
        "key_themes": [
            "AI PC / AI 筆電換機週期：NPU 整合帶動新一輪替換需求",
            "ASUS / 技嘉電競品牌溢價持續提升毛利",
            "車用電子（研華）IIoT 工業電腦高速成長",
            "AR/VR 頭戴裝置帶動顯示驅動 IC（聯詠）需求",
        ],
        "strengths_template": [
            "台灣 ODM/OEM 生態系完善，整合供應鏈優勢",
            "品牌廠（ASUS）在電競高端市場具定價能力",
            "工業電腦（研華）在製造業數位化具領先地位",
        ],
        "weaknesses_template": [
            "消費電子景氣周期性強，庫存調整時間長達 4-6 季",
            "中國白牌競品持續壓縮 PC/平板市場空間",
            "PC 市場成長有限，需靠 AI 功能差異化拉動溢價",
        ],
        "catalysts": [
            "AI PC 換機週期啟動（Windows 10 EOL + Copilot+ 功能普及）",
            "工業電腦滲透 AI 視覺、協作機器人應用",
            "電競外設（顯示器、耳機）持續擴大品牌高毛利比重",
        ],
        "risks": [
            "全球景氣衰退造成消費性需求萎縮",
            "供應鏈庫存水位失控（2022 年教訓重演）",
            "中美貿易戰關稅影響出口成本",
        ],
        "policy": [
            "美國 AI PC 補貼政策（CHIPS & Science Act 教育領域）",
            "歐盟《網路韌性法》對消費電子強制資安認證",
            "台灣工業局智慧製造補貼推動工業電腦需求",
        ],
        "global_peers": ["HP (HPQ)", "Dell (DELL)", "Lenovo (0992.HK)", "ASUS (2357.TW)", "Acer (2353.TW)"],
        "tw_ticker_leader": "2357",
    },

    "電信": {
        "full_name": "台灣電信服務（Telecom Services）",
        "market_size_now":  "台灣電信市場約 NT$3,000 億（2024）",
        "market_size_2028": "約 NT$3,500 億（2028E）",
        "cagr":    "3～5%（2024-2028）",
        "key_themes": [
            "5G 企業專網（Enterprise 5G）推動 B2B 收入成長",
            "AI 資料中心需求帶動骨幹頻寬與機房租賃業務",
            "固網寬頻 FTTH 滲透率持續提升",
            "OTT 視訊服務（myVideo / friDay）帶來附加營收",
            "物聯網（IoT）連線數快速增長",
        ],
        "strengths_template": [
            "台灣市場寡占結構（三大電信佔 90% 以上市佔），競爭趨緩",
            "穩定的現金流與高股息殖利率（4-6%）吸引長線投資人",
            "5G 頻譜佈建完成，進入收割期",
        ],
        "weaknesses_template": [
            "台灣市場飽和，ARPU（每用戶平均收入）成長有限",
            "資本支出（頻譜費、建設費）高，自由現金流壓力大",
            "OTT 競爭分食語音/SMS 傳統收入",
        ],
        "catalysts": [
            "企業 5G 專網商機：工廠、港口、醫院智慧化需求",
            "AI 機房建置帶動雲端網路頻寬業務",
            "低軌衛星（Starlink）合作布局偏遠地區覆蓋",
        ],
        "risks": [
            "價格戰重啟（MVNO 或政策介入）壓縮 ARPU",
            "5G 企業應用落地速度低於預期",
            "低軌衛星直連手機技術成熟後衝擊傳統基地台業務",
        ],
        "policy": [
            "NCC 開放 MVNO（行動虛擬網路業者）競爭格局改變",
            "政府推動數位部5G專頻政策，協助企業導入",
            "大陸資本禁止入股台灣電信業",
        ],
        "global_peers": ["中華電信 (2412.TW)", "遠傳電信 (4904.TW)", "台灣大哥大 (3045.TW)", "NTT (9432.T)", "SK Telecom (SKM)"],
        "tw_ticker_leader": "2412",
    },

    "鋼鐵/原料": {
        "full_name": "鋼鐵 / 石化原料（Steel & Petrochemicals）",
        "market_size_now":  "台灣石化產業產值約 NT$2.5 兆（2024）",
        "market_size_2028": "整體穩定，綠色轉型帶來新商機",
        "cagr":    "2～4%（2024-2028）",
        "key_themes": [
            "碳中和壓力：鋼廠轉型電爐煉鋼（EAF），減少高爐依賴",
            "台塑集團石化轉型：輕量化材料、生質塑料",
            "基礎設施投資（綠能、半導體廠房）支撐鋼鐵需求",
            "中國鋼鐵產能過剩持續壓制全球鋼價",
        ],
        "strengths_template": [
            "中鋼在台灣鋼材市場具主導地位，具一定定價能力",
            "台塑集團垂直整合完整，上下游協同效益強",
            "穩定配息，現金流量充足（低成長防禦型",
        ],
        "weaknesses_template": [
            "高度受國際鐵礦石、石油原料價格波動影響",
            "中國過剩產能出口衝擊亞洲鋼價",
            "石化業碳排放高，面對碳稅/碳邊境調整機制（CBAM）壓力",
        ],
        "catalysts": [
            "綠能設施（風電樁、太陽能架台）用鋼需求成長",
            "AI 資料中心建設帶動建築鋼材需求",
            "台塑生質塑料（PLA）替代石化塑料商機",
        ],
        "risks": [
            "中國經濟放緩造成原物料需求下滑",
            "歐盟 CBAM 碳邊境稅提高出口成本",
            "俄烏戰爭緩和後鋼材供給回升壓制鋼價",
        ],
        "policy": [
            "台灣 2050 碳中和目標：要求高碳排產業提出轉型計畫",
            "歐盟碳邊境調整機制（CBAM）2026 年全面施行",
            "政府基礎建設計畫（前瞻計畫）支撐鋼材需求",
        ],
        "global_peers": ["Posco (PKX)", "ArcelorMittal (MT)", "Nippon Steel (5401.T)", "中鋼 (2002.TW)", "台塑 (1301.TW)"],
        "tw_ticker_leader": "2002",
    },

    "零售/食品": {
        "full_name": "零售通路 / 食品飲料（Retail & Food）",
        "market_size_now":  "台灣便利商店產值約 NT$4,000 億（2024）",
        "market_size_2028": "約 NT$4,800 億（2028E）",
        "cagr":    "4～6%（2024-2028）",
        "key_themes": [
            "便利商店智慧化：AI 選品、自動結帳（無人店）普及",
            "台灣即食/冷凍食品需求持續增長（少子化單人戶）",
            "海外擴張：統一超（7-ELEVEN）在台灣市場深度開發",
            "外食化趨勢加速，鮮食與熱食佔比提升",
            "電商食品宅配（統一、全家自有會員平台）",
        ],
        "strengths_template": [
            "統一超便利商店台灣市佔率超過 50%，寡占優勢明顯",
            "高密度門市布局形成難以複製的物流與品牌壁壘",
            "穩定消費者需求，景氣衰退時具防禦性",
        ],
        "weaknesses_template": [
            "台灣實體通路市場趨近飽和，新店效益遞減",
            "勞動成本持續上升（基本工資調漲）壓縮利潤",
            "電商食品外送平台競食線下來客數",
        ],
        "catalysts": [
            "AI 智慧門市降低人力成本，提升鮮食周轉率",
            "會員制訂閱服務增加黏性與每次消費金額",
            "海外（菲律賓、馬來西亞）擴店帶動EPS成長",
        ],
        "risks": [
            "通膨造成食材成本上升，壓縮鮮食毛利",
            "外送平台（foodpanda/Uber Eats）競爭加劇",
            "消費者行為改變（宅配直送興起）",
        ],
        "policy": [
            "食品安全法規趨嚴：鮮食標示、食品添加物限制",
            "基本工資每年調漲 3-5%，影響零售人力成本",
            "環保包材強制規範（限塑政策）增加成本",
        ],
        "global_peers": ["7-Eleven (SE.JP)", "FamilyMart (8028.T)", "Lawson (2651.T)", "統一超 (2912.TW)", "全家 (5903.TW)"],
        "tw_ticker_leader": "2912",
    },
}

# ── 台股代碼 → 知識庫 Key 對照 ──
TW_STOCK_TO_INDUSTRY_KEY = {
    "2330": "晶圓代工",
    "2303": "晶圓代工",
    "3711": "晶圓代工",
    "2454": "IC設計",
    "3034": "IC設計",
    "6770": "IC設計",
    "3443": "IC設計",
    "2408": "記憶體",
    "2344": "記憶體",
    "3474": "記憶體",
    "3037": "PCB",
    "8046": "PCB",
    "3231": "伺服器/NB",
    "2382": "伺服器/NB",
    "2317": "伺服器/NB",
    "2356": "伺服器/NB",
    "2308": "電力設備",
    "1590": "電力設備",
    "2882": "金融-銀行",
    "2881": "金融-銀行",
    "2884": "金融-銀行",
    "2886": "金融-銀行",
    "2891": "金融-銀行",
    "3406": "光通訊",
    "4968": "光通訊",
    "3489": "光通訊",
    "3617": "低軌衛星",
    "6508": "低軌衛星",
    "8069": "CCL基板",
    "6274": "CCL基板",
    "3105": "散熱",
    "3324": "散熱",
    "3017": "散熱",
    # 消費電子
    "2357": "消費電子",
    "2395": "消費電子",
    "2379": "消費電子",
    # 電信
    "4904": "電信",
    "2412": "電信",
    "3045": "電信",
    # 鋼鐵/原料
    "2002": "鋼鐵/原料",
    "1301": "鋼鐵/原料",
    "1303": "鋼鐵/原料",
    # 零售/食品
    "2912": "零售/食品",
    "1216": "零售/食品",
    "2903": "零售/食品",  # 遠百
    "1104": "鋼鐵/原料",  # 環泥
    # 消費電子（補充）
    "6239": "消費電子",   # 力成
    "2353": "消費電子",   # 宏碁
    # 金融（補充）
    "2885": "金融-銀行",  # 元大金
    "2887": "金融-銀行",  # 中壽（掛金融控股）
    "5880": "金融-銀行",  # 合庫金
    "2888": "金融-銀行",  # 新光金
    "2883": "金融-銀行",  # 開發金
    "6005": "金融-銀行",  # 群益
    "5876": "金融-銀行",  # 上海商銀
}

# ── 美股 sector → 知識庫 Key 對照 ──
US_SECTOR_TO_INDUSTRY_KEY = {
    "Technology":                          "Technology",
    "Semiconductors":                      "Semiconductors",
    "Semiconductor Equipment & Materials": "Semiconductor Equipment & Materials",
    "Consumer Cyclical":                   "Electric Vehicles",
    "Financial Services":                  "Financial Services",
    "Communication Services":             "Technology",
}

# ── 美股 industry（更細分）→ 知識庫 Key ──
US_INDUSTRY_TO_KEY = {
    "Semiconductors": "Semiconductors",
    "Semiconductor Equipment & Materials": "Semiconductor Equipment & Materials",
    "Consumer Electronics": "Technology",
    "Internet Content & Information": "Technology",
    "Software—Application": "Technology",
    "Software—Infrastructure": "Technology",
    "Auto Manufacturers": "Electric Vehicles",
    "Banks—Diversified": "Financial Services",
    "Capital Markets": "Financial Services",
    "Insurance—Life": "Financial Services",
}
