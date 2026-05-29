import yfinance as yf
import requests
import time
import json
from datetime import datetime, timedelta

EDGAR_BASE = "https://efts.sec.gov/LATEST/search-index"
EDGAR_SUBMISSIONS = "https://data.sec.gov/submissions"
CLINICALTRIALS_BASE = "https://clinicaltrials.gov/api/v2/studies"

HEADERS = {
    "User-Agent": "PharmaAlgo/1.0 mregalbuto08@github.com"
}


def get_financial_data(ticker_str):
    """
    Recupera dati finanziari da yfinance con rate limiting.
    """
    try:
        time.sleep(2)
        ticker = yf.Ticker(ticker_str)
        info = ticker.info

        prezzo = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        high_52 = info.get("fiftyTwoWeekHigh", 0)
        low_52 = info.get("fiftyTwoWeekLow", 0)
        prezzo_30gg = None

        try:
            hist = ticker.history(period="1mo")
            if not hist.empty:
                prezzo_30gg = float(hist["Close"].iloc[0])
        except Exception:
            pass

        movimento_1mese = 0
        if prezzo_30gg and prezzo_30gg > 0 and prezzo > 0:
            movimento_1mese = (prezzo - prezzo_30gg) / prezzo_30gg

        return {
            "prezzo_attuale": prezzo,
            "52wk_high": high_52,
            "52wk_low": low_52,
            "market_cap": info.get("marketCap", 0),
            "float_shares": info.get("floatShares", 0),
            "short_interest": info.get("sharesShort", 0),
            "short_percent_float": info.get("shortPercentOfFloat", 0) or 0,
            "cash": info.get("totalCash", 0),
            "burn_rate": info.get("operatingCashflow", 0),
            "movimento_1mese": movimento_1mese,
            "diluizione_recente": False,
            "insider_net_30gg": 0,
            "pipeline_asset_count": 2
        }
    except Exception as e:
        print(f"Errore yfinance per {ticker_str}: {e}")
        return None


def get_edgar_cik(ticker_str):
    """
    Recupera il CIK da SEC EDGAR per un ticker.
    """
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        for key, val in data.items():
            if val.get("ticker", "").upper() == ticker_str.upper():
                return str(val["cik_str"]).zfill(10)
    except Exception as e:
        print(f"Errore CIK lookup per {ticker_str}: {e}")
    return None


def get_recent_8k(cik, days=1):
    """
    Recupera gli 8-K recenti per una compagnia da EDGAR.
    """
    try:
        url = f"{EDGAR_SUBMISSIONS}/CIK{cik}.json"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()

        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        accessions = filings.get("accessionNumber", [])
        descriptions = filings.get("primaryDocument", [])

        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        results = []

        for i, form in enumerate(forms):
            if form == "8-K" and dates[i] >= cutoff:
                accession = accessions[i].replace("-", "")
                doc = descriptions[i]
                url_doc = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{doc}"
                results.append({
                    "date": dates[i],
                    "accession": accessions[i],
                    "url": url_doc
                })

        return results
    except Exception as e:
        print(f"Errore 8-K lookup: {e}")
        return []


def get_form4_recent(cik, days=30):
    """
    Recupera i Form 4 recenti (insider transactions) da EDGAR.
    """
    try:
        url = f"{EDGAR_SUBMISSIONS}/CIK{cik}.json"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()

        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        accessions = filings.get("accessionNumber", [])

        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        results = []

        for i, form in enumerate(forms):
            if form == "4" and dates[i] >= cutoff:
                results.append({
                    "date": dates[i],
                    "accession": accessions[i]
                })

        return results
    except Exception as e:
        print(f"Errore Form4 lookup: {e}")
        return []


def get_edgar_keyword_search(keywords, days=30):
    """
    Cerca negli 8-K recenti per keywords specifiche.
    Restituisce lista di compagnie con filing rilevanti.
    """
    results = []
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    for keyword in keywords:
        try:
            params = {
                "q": f'"{keyword}"',
                "dateRange": "custom",
                "startdt": cutoff,
                "enddt": datetime.now().strftime("%Y-%m-%d"),
                "forms": "8-K"
            }
            resp = requests.get(
                "https://efts.sec.gov/LATEST/search-index",
                params=params,
                headers=HEADERS,
                timeout=15
            )
            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])

            for hit in hits:
                source = hit.get("_source", {})
                results.append({
                    "keyword": keyword,
                    "ticker": source.get("display_names", [{}])[0].get("ticker", ""),
                    "company": source.get("entity_name", ""),
                    "date": source.get("file_date", ""),
                    "accession": source.get("accession_no", ""),
                    "description": source.get("period_of_report", "")
                })
            time.sleep(1)
        except Exception as e:
            print(f"Errore EDGAR search per '{keyword}': {e}")

    return results


def get_clinicaltrials(days_ahead=90):
    """
    Recupera trial Phase 3 con completion date nei prossimi N giorni.
    """
    from datetime import date, timedelta

    today = date.today()
    future = today + timedelta(days=days_ahead)

    params = {
        "query.term": "cancer OR rare disease OR autoimmune OR neurological OR dermatology OR ophthalmology",
        "filter.overallStatus": "ACTIVE_NOT_RECRUITING,COMPLETED",
        "filter.phase": "PHASE3",
        "filter.studyType": "INTERVENTIONAL",
        "postFilter.primaryCompletionDate": f"RANGE[{today.strftime('%Y-%m-%d')},{future.strftime('%Y-%m-%d')}]",
        "fields": "NCTId,BriefTitle,Condition,InterventionName,LeadSponsorName,PrimaryCompletionDate,EnrollmentCount,Phase,OverallStatus",
        "pageSize": 100
    }

    try:
        resp = requests.get(CLINICALTRIALS_BASE, params=params, timeout=15)
        data = resp.json()
        studies = data.get("studies", [])
        results = []

        for study in studies:
            proto = study.get("protocolSection", {})
            id_module = proto.get("identificationModule", {})
            status_module = proto.get("statusModule", {})
            conditions = proto.get("conditionsModule", {})
            interventions = proto.get("armsInterventionsModule", {})
            sponsor = proto.get("sponsorCollaboratorsModule", {})
            enrollment = proto.get("designModule", {})

            interventions_list = interventions.get("interventions", [])
            drug_names = [i.get("name", "") for i in interventions_list if i.get("type") == "DRUG"]

            results.append({
                "nct": id_module.get("nctId", ""),
                "title": id_module.get("briefTitle", ""),
                "conditions": conditions.get("conditions", []),
                "drugs": drug_names,
                "sponsor": sponsor.get("leadSponsor", {}).get("name", ""),
                "completion_date": status_module.get("primaryCompletionDateStruct", {}).get("date", ""),
                "enrollment": enrollment.get("enrollmentInfo", {}).get("count", 0)
            })

        return results
    except Exception as e:
        print(f"Errore clinicaltrials: {e}")
        return []


def fetch_url_text(url, max_chars=3000):
    """
    Fetch di una pagina web, restituisce testo pulito.
    """
    try:
        from bs4 import BeautifulSoup
        resp = requests.get(url, headers={
            **HEADERS,
            "User-Agent": "Mozilla/5.0 (compatible; PharmaAlgo/1.0)"
        }, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text[:max_chars]
    except Exception as e:
        print(f"Errore fetch {url}: {e}")
        return ""


def get_news(api_key, tickers, days=1):
    """
    Recupera news per una lista di ticker con una singola chiamata API
    usando query aggregate per risparmiare richieste.
    """
    from newsapi import NewsApiClient

    if not tickers:
        return {}

    newsapi = NewsApiClient(api_key=api_key)
    query = " OR ".join(tickers[:10])

    from datetime import date, timedelta
    from_date = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        articles = newsapi.get_everything(
            q=query,
            from_param=from_date,
            language="en",
            sort_by="publishedAt",
            page_size=100
        )
        results = {ticker: [] for ticker in tickers}
        for article in articles.get("articles", []):
            title = article.get("title", "").upper()
            for ticker in tickers:
                if ticker.upper() in title:
                    results[ticker].append({
                        "title": article.get("title"),
                        "description": article.get("description"),
                        "url": article.get("url"),
                        "publishedAt": article.get("publishedAt")
                    })
        return results
    except Exception as e:
        print(f"Errore NewsAPI: {e}")
        return {ticker: [] for ticker in tickers}
