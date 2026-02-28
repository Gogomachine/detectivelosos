"""
AML news sources configuration.
RSS feeds, websites, and API endpoints for monitoring.
"""

# RSS feeds for AML/compliance news
RSS_FEEDS = [
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
    {
        "name": "CoinDesk",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss",
        "category": "crypto_aml",
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
]

# Twitter/X accounts to monitor for AML news
TWITTER_ACCOUNTS = [
    # Regulators
    {"username": "FinCENgov", "category": "regulation"},
    {"username": "FATFNews", "category": "regulation"},
    {"username": "OFACsanctions", "category": "sanctions"},
    {"username": "TheJusticeDept", "category": "regulation"},
    # AML industry
    {"username": "ACAMSorg", "category": "compliance"},
    {"username": "ComplianceWeek", "category": "compliance"},
    # Crypto AML / blockchain analytics
    {"username": "chainalysis", "category": "crypto_aml"},
    {"username": "elliptic", "category": "crypto_aml"},
    {"username": "TRM_Labs", "category": "crypto_aml"},
    # Investigative journalists & orgs
    {"username": "ICIJorg", "category": "investigations"},
    {"username": "OCCRP", "category": "investigations"},
    # Sanctions & treasury
    {"username": "USTreasury", "category": "sanctions"},
    {"username": "EU_Commission", "category": "sanctions"},
]

# Keywords for filtering relevant content
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
    # Russian
    "отмывание денег", "подозрительная транзакция", "финмониторинг",
    "комплаенс", "санкции", "финансовое преступление", "бенефициарный владелец",
    "подставная компания", "легализация доходов", "противодействие отмыванию",
    "росфинмониторинг", "финансовая разведка",
]

# Post categories and their emoji markers
POST_CATEGORIES = {
    "breaking": "🚨",
    "investigation": "🔍",
    "regulation": "📋",
    "sanctions": "⚖️",
    "crypto_aml": "🪙",
    "digest": "📰",
    "fun_fact": "💡",
    "analytics": "📊",
    "opinion": "🎯",
}
