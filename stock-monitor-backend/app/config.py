"""
商品配置和常量
移植自 stock-monitor/js/popup.js 中的 PRODUCTS 数组
"""

PRODUCTS = [
    # Muses 系列
    {"item_code": "item5457", "name": "Muses Fillo", "series": "Muses",
     "url": "https://daimaoh.co.jp/item5457.html"},
    {"item_code": "item5458", "name": "Muses Kokalo", "series": "Muses",
     "url": "https://daimaoh.co.jp/item5458.html"},
    {"item_code": "item5456", "name": "Muses Arkhe", "series": "Muses",
     "url": "https://daimaoh.co.jp/item5456.html"},
    # Venus 系列
    {"item_code": "item1663", "name": "Venus Real", "series": "Venus",
     "url": "https://daimaoh.co.jp/item1663.html"},
    {"item_code": "item1608", "name": "Venus Clone", "series": "Venus",
     "url": "https://daimaoh.co.jp/item1608.html"},
    {"item_code": "item1662", "name": "Venus Cross", "series": "Venus",
     "url": "https://daimaoh.co.jp/item1662.html"},
    # Virgo 系列
    {"item_code": "item12261", "name": "Virgo Phantasma", "series": "Virgo",
     "url": "https://daimaoh.co.jp/item12261.html"},
    {"item_code": "item12262", "name": "Virgo Veritas", "series": "Virgo",
     "url": "https://daimaoh.co.jp/item12262.html"},
    {"item_code": "item12263", "name": "Virgo Liber", "series": "Virgo",
     "url": "https://daimaoh.co.jp/item12263.html"},
    # Lilith 系列
    {"item_code": "item2285", "name": "Lilith Spiral-wave", "series": "Lilith",
     "url": "https://daimaoh.co.jp/item2285.html"},
    {"item_code": "item2286", "name": "Lilith Spiral-dots", "series": "Lilith",
     "url": "https://daimaoh.co.jp/item2286.html"},
    {"item_code": "item2287", "name": "Lilith Uterus", "series": "Lilith",
     "url": "https://daimaoh.co.jp/item2287.html"},
    # 其他
    {"item_code": "item1824", "name": "Quty Tits", "series": "Other",
     "url": "https://daimaoh.co.jp/item1824.html"},
    {"item_code": "item3420", "name": "TSUBO2.0 type.B", "series": "Other",
     "url": "https://daimaoh.co.jp/item3420.html"},
]

# 每个页面的抓取超时（秒）
SCRAPE_TIMEOUT = 30

# 商品之间的礼貌延迟（秒）
SCRAPE_DELAY = 2

# 失败重试次数
MAX_RETRIES = 1

# 数据库文件路径
DATABASE_URL = "sqlite:///data/stock_monitor.db"

# 定时检查时间（日本时间）
SCHEDULE_HOUR = 12
SCHEDULE_MINUTE = 0
TIMEZONE = "Asia/Tokyo"
