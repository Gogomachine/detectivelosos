"""
AML news sources configuration.
RSS feeds, websites, and API endpoints for monitoring.
"""

# RSS feeds for AML/compliance news
RSS_FEEDS = [
    # AML-dedicated sources
    {
        "name": "FATF",
        "url": "https://www.fatf-gafi.org/en/rss.xml",
        "category": "regulation",
        "language": "en",
    },
    {
        "name": "ACAMS MoneyLaundering.com",
        "url": "https://www.moneylaundering.com/feed/",
        "category": "news",
        "language": "en",
    },
    {
        "name": "OCCRP",
        "url": "https://www.occrp.org/en/rss",
        "category": "investigations",
        "language": "en",
    },
    {
        "name": "FinCEN",
        "url": "https://www.fincen.gov/rss.xml",
        "category": "regulation",
        "language": "en",
    },
    {
        "name": "Compliance Week",
        "url": "https://www.complianceweek.com/rss",
        "category": "compliance",
        "language": "en",
    },
    {
        "name": "OFAC Sanctions",
        "url": "https://ofac.treasury.gov/rss.xml",
        "category": "sanctions",
        "language": "en",
    },
    {
        "name": "EU AML Authority",
        "url": "https://finance.ec.europa.eu/rss_en",
        "category": "regulation",
        "language": "en",
    },
    # Crypto / general sources (filtered by AML keywords)
    {
        "name": "CoinDesk",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss",
        "category": "crypto_aml",
        "language": "en",
    },
    {
        "name": "Cointelegraph Investigations",
        "url": "https://cointelegraph.com/rss/tag/investigation",
        "category": "investigations",
        "language": "en",
    },
    {
        "name": "Cointelegraph",
        "url": "https://cointelegraph.com/rss",
        "category": "crypto_aml",
        "language": "en",
    },
    {
        "name": "Forklog",
        "url": "https://forklog.com/feed/",
        "category": "crypto_aml",
        "language": "ru",
    },
    {
        "name": "Incrypted",
        "url": "https://incrypted.com/en/feed/",
        "category": "crypto_aml",
        "language": "en",
    },
    {
        "name": "ACAMS Today",
        "url": "https://www.acamstoday.org/feed/",
        "category": "compliance",
        "language": "en",
    },
]

# Web pages to scrape (when RSS is not available)
SCRAPE_SOURCES = [
    {
        "name": "Chainalysis Blog",
        "url": "https://www.chainalysis.com/blog/",
        "selector": "article",
        "category": "crypto_aml",
    },
    {
        "name": "Elliptic Blog",
        "url": "https://www.elliptic.co/blog",
        "selector": "article",
        "category": "crypto_aml",
    },
    {
        "name": "Basel AML Index",
        "url": "https://index.baselgovernance.org/news",
        "selector": ".news-item",
        "category": "rankings",
    },
    {
        "name": "TRM Labs Insights",
        "url": "https://www.trmlabs.com/category/insights",
        "selector": "article, .blog-post, .post-card, [class*='post'], [class*='card']",
        "category": "crypto_aml",
    },
    {
        "name": "Bitget News",
        "url": "https://www.bitget.com/ru/news",
        "selector": "article, a[class*='news'], a[class*='article'], [class*='newsItem'], [class*='card']",
        "category": "crypto_aml",
    },
    {
        "name": "ACAMS AML",
        "url": "https://www.acams.org/en/taxonomy/term/680",
        "selector": "article, .views-row, .node, [class*='article'], [class*='card']",
        "category": "news",
    },
    {
        "name": "Binance Square News",
        "url": "https://www.binance.com/en/square/news/all",
        "selector": "article, a[class*='news'], a[class*='article'], [class*='card'], [class*='feed']",
        "category": "crypto_aml",
    },
    {
        "name": "Rekt News",
        "url": "https://rekt.news/ru",
        "selector": "article, [class*='post'], [class*='card'], [class*='article']",
        "category": "investigations",
    },
    {
        "name": "PeckShield",
        "url": "https://peckshield.com/",
        "selector": "article, [class*='post'], [class*='card'], [class*='blog'], [class*='news']",
        "category": "crypto_aml",
    },
    {
        "name": "The Block",
        "url": "https://www.theblock.co/latest-crypto-news",
        "selector": "article, a[class*='article'], [class*='card'], [class*='story'], [class*='post']",
        "category": "crypto_aml",
    },
]

# Keywords for filtering relevant content (for general crypto sources)
AML_KEYWORDS = [
    # English
    "money laundering", "aml", "anti-money laundering", "kyc", "know your customer",
    "sanctions", "compliance", "fatf", "financial crime", "terrorist financing",
    "suspicious activity", "sar", "ctr", "beneficial ownership", "shell company",
    "offshore", "correspondent banking", "de-risking", "pep", "politically exposed",
    "transaction monitoring", "trade-based laundering", "hawala", "smurfing",
    "structuring", "placement", "layering", "integration", "predicate offence",
    "mutual evaluation", "fiu", "financial intelligence", "seized assets",
    "forfeiture", "confiscation", "cryptocurrency laundering", "mixer", "tumbler",
    "travel rule", "virtual asset", "vasp",
    # Crypto-specific AML keywords
    "hack", "hacked", "exploit", "breach", "stolen", "theft", "fraud",
    "investigation", "arrest", "indictment", "extradition", "seizure",
    "tornado cash", "lazarus", "north korea", "dprk",
    "chainalysis", "elliptic", "trm labs", "blockchain analytics",
    "rug pull", "scam", "ponzi", "phishing",
    "ofac", "treasury", "fincen", "sec enforcement",
    "darknet", "ransomware", "cybercrime",
    # Russian
    "отмывание денег", "подозрительная транзакция", "финмониторинг",
    "комплаенс", "санкции", "финансовое преступление", "бенефициарный владелец",
    "подставная компания", "легализация доходов", "противодействие отмыванию",
    "росфинмониторинг", "финансовая разведка",
    "взлом", "хакер", "украдено", "мошенничество", "расследование",
    "арест", "конфискация", "скам",
]

# Post categories and their emoji markers
POST_CATEGORIES = {
    "breaking": "🚨",
    "investigation": "🔍",
    "regulation": "📋",
    "sanctions": "⚖️",
    "crypto_aml": "🪙",
    "crypto_news": "💰",
    "digest": "📰",
    "fun_fact": "💡",
    "analytics": "📊",
    "opinion": "🎯",
    "combined": "🕵️",
}
