# company_data.py
# Complete lists of Nifty 50, Midcap, Smallcap companies

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


# ─────────────────────────────────────────────────────────────────────────────
# NIFTY 50 Companies (All 50)
# ─────────────────────────────────────────────────────────────────────────────

NIFTY_50 = {
    "ADANIENT"    : {"name": "Adani Enterprises",         "sector": "Conglomerate",    "index": "NIFTY 50"},
    "ADANIPORTS"  : {"name": "Adani Ports & SEZ",         "sector": "Infrastructure",  "index": "NIFTY 50"},
    "APOLLOHOSP"  : {"name": "Apollo Hospitals",          "sector": "Healthcare",      "index": "NIFTY 50"},
    "ASIANPAINT"  : {"name": "Asian Paints",              "sector": "Consumer Goods",  "index": "NIFTY 50"},
    "AXISBANK"    : {"name": "Axis Bank",                 "sector": "Banking",         "index": "NIFTY 50"},
    "BAJAJ-AUTO"  : {"name": "Bajaj Auto",                "sector": "Auto",            "index": "NIFTY 50"},
    "BAJFINANCE"  : {"name": "Bajaj Finance",             "sector": "Finance",         "index": "NIFTY 50"},
    "BAJAJFINSV"  : {"name": "Bajaj Finserv",             "sector": "Finance",         "index": "NIFTY 50"},
    "BPCL"        : {"name": "BPCL",                      "sector": "Energy",          "index": "NIFTY 50"},
    "BHARTIARTL"  : {"name": "Bharti Airtel",             "sector": "Telecom",         "index": "NIFTY 50"},
    "BRITANNIA"   : {"name": "Britannia Industries",      "sector": "FMCG",            "index": "NIFTY 50"},
    "CIPLA"       : {"name": "Cipla",                     "sector": "Pharma",          "index": "NIFTY 50"},
    "COALINDIA"   : {"name": "Coal India",                "sector": "Mining",          "index": "NIFTY 50"},
    "DIVISLAB"    : {"name": "Divi's Laboratories",       "sector": "Pharma",          "index": "NIFTY 50"},
    "DRREDDY"     : {"name": "Dr. Reddy's Laboratories",  "sector": "Pharma",          "index": "NIFTY 50"},
    "EICHERMOT"   : {"name": "Eicher Motors",             "sector": "Auto",            "index": "NIFTY 50"},
    "GRASIM"      : {"name": "Grasim Industries",         "sector": "Cement",          "index": "NIFTY 50"},
    "HCLTECH"     : {"name": "HCL Technologies",          "sector": "IT",              "index": "NIFTY 50"},
    "HDFCBANK"    : {"name": "HDFC Bank",                 "sector": "Banking",         "index": "NIFTY 50"},
    "HDFCLIFE"    : {"name": "HDFC Life Insurance",       "sector": "Insurance",       "index": "NIFTY 50"},
    "HEROMOTOCO"  : {"name": "Hero MotoCorp",             "sector": "Auto",            "index": "NIFTY 50"},
    "HINDALCO"    : {"name": "Hindalco Industries",       "sector": "Metals",          "index": "NIFTY 50"},
    "HINDUNILVR"  : {"name": "Hindustan Unilever",        "sector": "FMCG",            "index": "NIFTY 50"},
    "ICICIBANK"   : {"name": "ICICI Bank",                "sector": "Banking",         "index": "NIFTY 50"},
    "ITC"         : {"name": "ITC",                       "sector": "FMCG",            "index": "NIFTY 50"},
    "INDUSINDBK"  : {"name": "IndusInd Bank",             "sector": "Banking",         "index": "NIFTY 50"},
    "INFY"        : {"name": "Infosys",                   "sector": "IT",              "index": "NIFTY 50"},
    "JSWSTEEL"    : {"name": "JSW Steel",                 "sector": "Metals",          "index": "NIFTY 50"},
    "KOTAKBANK"   : {"name": "Kotak Mahindra Bank",       "sector": "Banking",         "index": "NIFTY 50"},
    "LT"          : {"name": "Larsen & Toubro",           "sector": "Infrastructure",  "index": "NIFTY 50"},
    "M&M"         : {"name": "Mahindra & Mahindra",       "sector": "Auto",            "index": "NIFTY 50"},
    "MARUTI"      : {"name": "Maruti Suzuki",             "sector": "Auto",            "index": "NIFTY 50"},
    "NESTLEIND"   : {"name": "Nestle India",              "sector": "FMCG",            "index": "NIFTY 50"},
    "NTPC"        : {"name": "NTPC",                      "sector": "Utilities",       "index": "NIFTY 50"},
    "ONGC"        : {"name": "ONGC",                      "sector": "Energy",          "index": "NIFTY 50"},
    "POWERGRID"   : {"name": "Power Grid Corporation",    "sector": "Utilities",       "index": "NIFTY 50"},
    "RELIANCE"    : {"name": "Reliance Industries",       "sector": "Energy",          "index": "NIFTY 50"},
    "SBILIFE"     : {"name": "SBI Life Insurance",        "sector": "Insurance",       "index": "NIFTY 50"},
    "SBIN"        : {"name": "State Bank of India",       "sector": "Banking",         "index": "NIFTY 50"},
    "SUNPHARMA"   : {"name": "Sun Pharmaceutical",        "sector": "Pharma",          "index": "NIFTY 50"},
    "TCS"         : {"name": "Tata Consultancy Services", "sector": "IT",              "index": "NIFTY 50"},
    "TATACONSUM"  : {"name": "Tata Consumer Products",    "sector": "FMCG",            "index": "NIFTY 50"},
    "TATAMOTORS"  : {"name": "Tata Motors",               "sector": "Auto",            "index": "NIFTY 50"},
    "TATASTEEL"   : {"name": "Tata Steel",                "sector": "Metals",          "index": "NIFTY 50"},
    "TECHM"       : {"name": "Tech Mahindra",             "sector": "IT",              "index": "NIFTY 50"},
    "TITAN"       : {"name": "Titan Company",             "sector": "Consumer Goods",  "index": "NIFTY 50"},
    "ULTRACEMCO"  : {"name": "UltraTech Cement",          "sector": "Cement",          "index": "NIFTY 50"},
    "UPL"         : {"name": "UPL",                       "sector": "Chemicals",       "index": "NIFTY 50"},
    "WIPRO"       : {"name": "Wipro",                     "sector": "IT",              "index": "NIFTY 50"},
    "ZOMATO"      : {"name": "Zomato",                    "sector": "Consumer Tech",   "index": "NIFTY 50"},
}

# ─────────────────────────────────────────────────────────────────────────────
# NIFTY MIDCAP 50 Companies
# ─────────────────────────────────────────────────────────────────────────────

NIFTY_MIDCAP = {
    "ABCAPITAL"   : {"name": "Aditya Birla Capital",      "sector": "Finance",         "index": "NIFTY MIDCAP"},
    "ABFRL"       : {"name": "Aditya Birla Fashion",      "sector": "Consumer Goods",  "index": "NIFTY MIDCAP"},
    "APLAPOLLO"   : {"name": "APL Apollo Tubes",          "sector": "Metals",          "index": "NIFTY MIDCAP"},
    "ASTRAL"      : {"name": "Astral",                    "sector": "Consumer Goods",  "index": "NIFTY MIDCAP"},
    "ATUL"        : {"name": "Atul",                      "sector": "Chemicals",       "index": "NIFTY MIDCAP"},
    "AUBANK"      : {"name": "AU Small Finance Bank",     "sector": "Banking",         "index": "NIFTY MIDCAP"},
    "BALKRISIND"  : {"name": "Balkrishna Industries",     "sector": "Auto",            "index": "NIFTY MIDCAP"},
    "BANDHANBNK"  : {"name": "Bandhan Bank",              "sector": "Banking",         "index": "NIFTY MIDCAP"},
    "BIOCON"      : {"name": "Biocon",                    "sector": "Pharma",          "index": "NIFTY MIDCAP"},
    "COFORGE"     : {"name": "Coforge",                   "sector": "IT",              "index": "NIFTY MIDCAP"},
    "CROMPTON"    : {"name": "Crompton Greaves Consumer", "sector": "Consumer Goods",  "index": "NIFTY MIDCAP"},
    "CUMMINSIND"  : {"name": "Cummins India",             "sector": "Industrial",      "index": "NIFTY MIDCAP"},
    "DELHIVERY"   : {"name": "Delhivery",                 "sector": "Logistics",       "index": "NIFTY MIDCAP"},
    "FEDERALBNK"  : {"name": "Federal Bank",              "sector": "Banking",         "index": "NIFTY MIDCAP"},
    "GMRINFRA"    : {"name": "GMR Airports Infrastructure","sector": "Infrastructure", "index": "NIFTY MIDCAP"},
    "GODREJPROP"  : {"name": "Godrej Properties",         "sector": "Real Estate",     "index": "NIFTY MIDCAP"},
    "HDFCAMC"     : {"name": "HDFC Asset Management",     "sector": "Finance",         "index": "NIFTY MIDCAP"},
    "IDFCFIRSTB"  : {"name": "IDFC First Bank",           "sector": "Banking",         "index": "NIFTY MIDCAP"},
    "INDHOTEL"    : {"name": "Indian Hotels",             "sector": "Hospitality",     "index": "NIFTY MIDCAP"},
    "INDUSTOWER"  : {"name": "Indus Towers",              "sector": "Telecom",         "index": "NIFTY MIDCAP"},
    "JKCEMENT"    : {"name": "JK Cement",                 "sector": "Cement",          "index": "NIFTY MIDCAP"},
    "JUBLFOOD"    : {"name": "Jubilant Foodworks",        "sector": "Consumer Tech",   "index": "NIFTY MIDCAP"},
    "KAJARIACER"  : {"name": "Kajaria Ceramics",          "sector": "Consumer Goods",  "index": "NIFTY MIDCAP"},
    "KPITTECH"    : {"name": "KPIT Technologies",         "sector": "IT",              "index": "NIFTY MIDCAP"},
    "LICHSGFIN"   : {"name": "LIC Housing Finance",       "sector": "Finance",         "index": "NIFTY MIDCAP"},
    "LUPIN"       : {"name": "Lupin",                     "sector": "Pharma",          "index": "NIFTY MIDCAP"},
    "MFSL"        : {"name": "Max Financial Services",    "sector": "Insurance",       "index": "NIFTY MIDCAP"},
    "MOTHERSON"   : {"name": "Samvardhana Motherson",     "sector": "Auto",            "index": "NIFTY MIDCAP"},
    "MPHASIS"     : {"name": "Mphasis",                   "sector": "IT",              "index": "NIFTY MIDCAP"},
    "NMDC"        : {"name": "NMDC",                      "sector": "Mining",          "index": "NIFTY MIDCAP"},
    "OBEROIRLTY"  : {"name": "Oberoi Realty",             "sector": "Real Estate",     "index": "NIFTY MIDCAP"},
    "OFSS"        : {"name": "Oracle Financial Services", "sector": "IT",              "index": "NIFTY MIDCAP"},
    "PAGEIND"     : {"name": "Page Industries",           "sector": "Consumer Goods",  "index": "NIFTY MIDCAP"},
    "PERSISTENT"  : {"name": "Persistent Systems",        "sector": "IT",              "index": "NIFTY MIDCAP"},
    "PIIND"       : {"name": "PI Industries",             "sector": "Chemicals",       "index": "NIFTY MIDCAP"},
    "PNB"         : {"name": "Punjab National Bank",      "sector": "Banking",         "index": "NIFTY MIDCAP"},
    "POLYCAB"     : {"name": "Polycab India",             "sector": "Industrial",      "index": "NIFTY MIDCAP"},
    "PRESTIGE"    : {"name": "Prestige Estates",          "sector": "Real Estate",     "index": "NIFTY MIDCAP"},
    "SBICARD"     : {"name": "SBI Cards",                 "sector": "Finance",         "index": "NIFTY MIDCAP"},
    "SJVN"        : {"name": "SJVN",                      "sector": "Utilities",       "index": "NIFTY MIDCAP"},
    "SUPREMEIND"  : {"name": "Supreme Industries",        "sector": "Consumer Goods",  "index": "NIFTY MIDCAP"},
    "TATACOMM"    : {"name": "Tata Communications",       "sector": "Telecom",         "index": "NIFTY MIDCAP"},
    "TORNTPHARM"  : {"name": "Torrent Pharmaceuticals",   "sector": "Pharma",          "index": "NIFTY MIDCAP"},
    "TRENT"       : {"name": "Trent",                     "sector": "Consumer Goods",  "index": "NIFTY MIDCAP"},
    "UNIONBANK"   : {"name": "Union Bank of India",       "sector": "Banking",         "index": "NIFTY MIDCAP"},
    "VOLTAS"      : {"name": "Voltas",                    "sector": "Consumer Goods",  "index": "NIFTY MIDCAP"},
    "ZYDUSLIFE"   : {"name": "Zydus Lifesciences",        "sector": "Pharma",          "index": "NIFTY MIDCAP"},
}

# ─────────────────────────────────────────────────────────────────────────────
# NIFTY SMALLCAP Companies (Selected 50)
# ─────────────────────────────────────────────────────────────────────────────

NIFTY_SMALLCAP = {
    "AFFLE"       : {"name": "Affle India",               "sector": "Consumer Tech",   "index": "NIFTY SMALLCAP"},
    "AJANTPHARM"  : {"name": "Ajanta Pharma",             "sector": "Pharma",          "index": "NIFTY SMALLCAP"},
    "ANGELONE"    : {"name": "Angel One",                 "sector": "Finance",         "index": "NIFTY SMALLCAP"},
    "APTUS"       : {"name": "Aptus Value Housing",       "sector": "Finance",         "index": "NIFTY SMALLCAP"},
    "ARVINDFASN"  : {"name": "Arvind Fashions",           "sector": "Consumer Goods",  "index": "NIFTY SMALLCAP"},
    "BBOX"        : {"name": "Black Box",                 "sector": "IT",              "index": "NIFTY SMALLCAP"},
    "BIKAJI"      : {"name": "Bikaji Foods",              "sector": "FMCG",            "index": "NIFTY SMALLCAP"},
    "BLUEDART"    : {"name": "Blue Dart Express",         "sector": "Logistics",       "index": "NIFTY SMALLCAP"},
    "CAMPUS"      : {"name": "Campus Activewear",         "sector": "Consumer Goods",  "index": "NIFTY SMALLCAP"},
    "CARTRADE"    : {"name": "CarTrade Tech",             "sector": "Consumer Tech",   "index": "NIFTY SMALLCAP"},
    "CERA"        : {"name": "Cera Sanitaryware",         "sector": "Consumer Goods",  "index": "NIFTY SMALLCAP"},
    "CLEAN"       : {"name": "Clean Science Technology",  "sector": "Chemicals",       "index": "NIFTY SMALLCAP"},
    "CONCORDBIO"  : {"name": "Concord Biotech",           "sector": "Pharma",          "index": "NIFTY SMALLCAP"},
    "DEEPAKNTR"   : {"name": "Deepak Nitrite",            "sector": "Chemicals",       "index": "NIFTY SMALLCAP"},
    "DOMS"        : {"name": "DOMS Industries",           "sector": "Consumer Goods",  "index": "NIFTY SMALLCAP"},
    "ELGIEQUIP"   : {"name": "Elgi Equipments",          "sector": "Industrial",      "index": "NIFTY SMALLCAP"},
    "EMAMILTD"    : {"name": "Emami",                     "sector": "FMCG",            "index": "NIFTY SMALLCAP"},
    "EPIGRAL"     : {"name": "Epigral",                   "sector": "Chemicals",       "index": "NIFTY SMALLCAP"},
    "EQUITASBNK"  : {"name": "Equitas Small Finance Bank","sector": "Banking",         "index": "NIFTY SMALLCAP"},
    "ESTER"       : {"name": "Ester Industries",          "sector": "Chemicals",       "index": "NIFTY SMALLCAP"},
    "FINEORG"     : {"name": "Fine Organic Industries",   "sector": "Chemicals",       "index": "NIFTY SMALLCAP"},
    "FLAIR"       : {"name": "Flair Writing",             "sector": "Consumer Goods",  "index": "NIFTY SMALLCAP"},
    "GALAXYSURF"  : {"name": "Galaxy Surfactants",        "sector": "Chemicals",       "index": "NIFTY SMALLCAP"},
    "GHCL"        : {"name": "GHCL",                      "sector": "Chemicals",       "index": "NIFTY SMALLCAP"},
    "GODIGIT"     : {"name": "Go Digit Insurance",        "sector": "Insurance",       "index": "NIFTY SMALLCAP"},
    "HAPPYFORGE"  : {"name": "Happy Forgings",            "sector": "Industrial",      "index": "NIFTY SMALLCAP"},
    "IIFL"        : {"name": "IIFL Finance",              "sector": "Finance",         "index": "NIFTY SMALLCAP"},
    "JYOTHYLAB"   : {"name": "Jyothy Labs",               "sector": "FMCG",            "index": "NIFTY SMALLCAP"},
    "KFINTECH"    : {"name": "KFin Technologies",         "sector": "Finance",         "index": "NIFTY SMALLCAP"},
    "KIOCL"       : {"name": "KIOCL",                     "sector": "Mining",          "index": "NIFTY SMALLCAP"},
    "LATENTVIEW"  : {"name": "LatentView Analytics",      "sector": "IT",              "index": "NIFTY SMALLCAP"},
    "MAZDOCK"     : {"name": "Mazagon Dock Shipbuilders", "sector": "Defence",         "index": "NIFTY SMALLCAP"},
    "MEDANTA"     : {"name": "Global Health (Medanta)",   "sector": "Healthcare",      "index": "NIFTY SMALLCAP"},
    "METROBRAND"  : {"name": "Metro Brands",              "sector": "Consumer Goods",  "index": "NIFTY SMALLCAP"},
    "NAVINFLUOR"  : {"name": "Navin Fluorine",            "sector": "Chemicals",       "index": "NIFTY SMALLCAP"},
    "NUVAMA"      : {"name": "Nuvama Wealth Management",  "sector": "Finance",         "index": "NIFTY SMALLCAP"},
    "PPLPHARMA"   : {"name": "Piramal Pharma",            "sector": "Pharma",          "index": "NIFTY SMALLCAP"},
    "PRINCEPIPE"  : {"name": "Prince Pipes & Fittings",   "sector": "Consumer Goods",  "index": "NIFTY SMALLCAP"},
    "RADIOCITY"   : {"name": "Music Broadcast",           "sector": "Media",           "index": "NIFTY SMALLCAP"},
    "RKFORGE"     : {"name": "Ramkrishna Forgings",       "sector": "Industrial",      "index": "NIFTY SMALLCAP"},
    "RPGLIFE"     : {"name": "RPG Life Sciences",         "sector": "Pharma",          "index": "NIFTY SMALLCAP"},
    "SAFARI"      : {"name": "Safari Industries",         "sector": "Consumer Goods",  "index": "NIFTY SMALLCAP"},
    "SENCO"       : {"name": "Senco Gold",                "sector": "Consumer Goods",  "index": "NIFTY SMALLCAP"},
    "SHYAMMETL"   : {"name": "Shyam Metalics",           "sector": "Metals",          "index": "NIFTY SMALLCAP"},
    "SIGNATURE"   : {"name": "Signatureglobal India",     "sector": "Real Estate",     "index": "NIFTY SMALLCAP"},
    "SUVENPHAR"   : {"name": "Suven Pharmaceuticals",     "sector": "Pharma",          "index": "NIFTY SMALLCAP"},
    "TCNSBRANDS"  : {"name": "TCNS Clothing",             "sector": "Consumer Goods",  "index": "NIFTY SMALLCAP"},
    "TIINDIA"     : {"name": "Tube Investments",          "sector": "Industrial",      "index": "NIFTY SMALLCAP"},
    "VAIBHAVGBL"  : {"name": "Vaibhav Global",            "sector": "Consumer Goods",  "index": "NIFTY SMALLCAP"},
    "VGUARD"      : {"name": "V-Guard Industries",        "sector": "Consumer Goods",  "index": "NIFTY SMALLCAP"},
}

# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

ALL_COMPANIES = {**NIFTY_50, **NIFTY_MIDCAP, **NIFTY_SMALLCAP}

def get_all_sectors() -> list:
    sectors = sorted(set(v["sector"] for v in ALL_COMPANIES.values()))
    return sectors

def get_companies_by_index(index: str) -> dict:
    mapping = {
        "nifty50"   : NIFTY_50,
        "midcap"    : NIFTY_MIDCAP,
        "smallcap"  : NIFTY_SMALLCAP,
        "all"       : ALL_COMPANIES,
    }
    return mapping.get(index.lower(), {})

def get_companies_by_sector(sector: str) -> dict:
    return {
        sym: info for sym, info in ALL_COMPANIES.items()
        if info["sector"].lower() == sector.lower()
    }

def symbol_to_info(symbol: str) -> dict:
    return ALL_COMPANIES.get(symbol.upper(), {
        "name": symbol, "sector": "Unknown", "index": "Unknown"
    })