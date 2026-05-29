import os
import sys
import json
import time
from datetime import datetime, date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import get_connection, init_db
from modules.data_collection import (
    get_edgar_keyword_search,
    get_financial_data,
    get_edgar_cik,
    get_form4_recent,
    fetch_url_text
)
from modules.llm_analysis import analizza_compagnia
from modules.scoring import (
    calcola_score_scientifico,
    calcola_score_movimento,
    calcola_ev,
    supera_soglia,
    calcola_timing
)

# Keywords per trovare compagnie con catalisti imminenti
EDGAR_KEYWORDS = [
    "PDUFA target action date",
    "breakthrough therapy designation",
    "priority review",
    "NDA submission accepted",
    "BLA submission accepted",
    "phase 3 topline results",
    "phase 3 top-line results"
]

# Filtri market cap
MIN_MARKET_CAP = 100_000_000   # $100M
MAX_MARKET_CAP = 5_000_000_000  # $5B


def filtra_compagnia(ticker_str, financial_data):
    """
    Applica i filtri primari. Restituisce True se la compagnia passa.
    """
    if not financial_data:
        return False, "dati finanziari non disponibili"

    mc = financial_data.get("market_cap", 0)
    if mc < MIN_MARKET_CAP:
        return False, f"market cap troppo bassa: ${mc:,.0f}"
    if mc > MAX_MARKET_CAP:
        return False, f"market cap troppo alta: ${mc:,.0f}"

    movimento = financial_data.get("movimento_1mese", 0)
    if movimento > 0.50:
        return False, f"titolo gia salito +{movimento*100:.0f}% nell'ultimo mese"

    return True, "ok"


def run_monthly_scan():
    """
    Scansione mensile completa.
    Cerca nuove compagnie con catalisti imminenti e le salva nel database.
    """
    print(f"\n{'='*60}")
    print(f"SCANSIONE MENSILE — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    init_db()
    conn = get_connection()

    # Step 1: cerca compagnie con eventi rilevanti su EDGAR
    print("Step 1: Ricerca su EDGAR...")
    edgar_results = get_edgar_keyword_search(EDGAR_KEYWORDS, days=35)
    print(f"  Trovati {len(edgar_results)} filing rilevanti")

    # Deduplica per ticker
    seen_tickers = set()
    candidates = []
    for result in edgar_results:
        ticker = result.get("ticker", "").strip().upper()
        if ticker and ticker not in seen_tickers and len(ticker) <= 5:
            seen_tickers.add(ticker)
            candidates.append(result)

    print(f"  Ticker unici: {len(candidates)}")

    # Step 2: applica filtri primari
    print("\nStep 2: Filtri primari...")
    passed = []
    for candidate in candidates:
        ticker = candidate["ticker"]
        print(f"  Checking {ticker}...", end=" ")

        financial_data = get_financial_data(ticker)
        ok, reason = filtra_compagnia(ticker, financial_data)

        if ok:
            candidate["financial_data"] = financial_data
            passed.append(candidate)
            print(f"PASSA")
        else:
            print(f"esclusa: {reason}")

    print(f"\n  Compagnie che passano i filtri: {len(passed)}")

    # Step 3: analisi approfondita e scoring
    print("\nStep 3: Analisi e scoring...")
    opportunita = []

    for candidate in passed:
        ticker = candidate["ticker"]
        company = candidate.get("company", ticker)
        financial_data = candidate["financial_data"]

        print(f"\n  Analizzando {ticker} ({company})...")

        # Estrai informazioni dal filing
        keyword = candidate.get("keyword", "")
        catalyst_type = "PDUFA" if "PDUFA" in keyword.upper() else "PHASE3_READOUT"
        fda_designations = keyword if "breakthrough" in keyword.lower() or "priority" in keyword.lower() else ""

        # Raccoglie testi per LLM
        texts = []
        accession_url = f"https://www.sec.gov/Archives/edgar/data/"
        try:
            cik = get_edgar_cik(ticker)
            if cik:
                recent_8k = []
                from modules.data_collection import get_recent_8k
                recent_8k = get_recent_8k(cik, days=35)
                for filing in recent_8k[:2]:
                    text = fetch_url_text(filing["url"])
                    if text:
                        texts.append(text)
                time.sleep(1)
        except Exception as e:
            print(f"    Errore fetch documenti: {e}")

        # Analisi LLM
        llm_output = analizza_compagnia(
            company=company,
            drug="farmaco principale",
            indication="indicazione principale",
            texts=texts
        )

        # Calcola news volume (placeholder, viene aggiornato nel monitoring)
        news_volume = 5

        # Scoring
        score_sci = calcola_score_scientifico(
            catalyst_type=catalyst_type,
            fda_designations=fda_designations,
            crl_precedente=False,
            llm_output=llm_output
        )

        score_mov = calcola_score_movimento(
            financial_data=financial_data,
            llm_output=llm_output,
            news_volume=news_volume
        )

        ev = calcola_ev(score_sci, score_mov, catalyst_type)

        if not supera_soglia(ev, catalyst_type):
            print(f"    EV {ev:.1f}% sotto soglia, scartata")
            continue

        timing = calcola_timing(
            catalyst_date_str=None,
            date_reliability="ALTA",
            red_flags=llm_output.get("red_flags", [])
        )

        print(f"    Score sci: {score_sci} | Score mov: {score_mov} | EV: {ev:.1f}% | Timing: {timing}")

        # Salva nel database
        try:
            c = conn.cursor()

            # Upsert company
            c.execute("""
                INSERT OR REPLACE INTO companies
                (ticker, name, market_cap, cash, burn_rate, float_shares, short_interest, short_percent_float, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                ticker,
                company,
                financial_data.get("market_cap", 0),
                financial_data.get("cash", 0),
                financial_data.get("burn_rate", 0),
                financial_data.get("float_shares", 0),
                financial_data.get("short_interest", 0),
                financial_data.get("short_percent_float", 0)
            ))

            company_id = c.execute("SELECT id FROM companies WHERE ticker = ?", (ticker,)).fetchone()[0]

            # Inserisci catalyst
            c.execute("""
                INSERT INTO catalysts
                (company_id, drug_name, indication, catalyst_type, catalyst_date, date_reliability, fda_designations)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                llm_output.get("sommario_tesi", "")[:100],
                ", ".join(llm_output.get("segnali_positivi", []))[:200],
                catalyst_type,
                None,
                "ALTA",
                fda_designations
            ))

            catalyst_id = c.lastrowid

            # Inserisci score
            c.execute("""
                INSERT INTO scores
                (catalyst_id, score_date, score_scientifico, score_movimento, ev_stimato, timing, llm_output, segnali_positivi, rischi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                catalyst_id,
                date.today().isoformat(),
                score_sci,
                score_mov,
                ev,
                timing,
                json.dumps(llm_output),
                json.dumps(llm_output.get("segnali_positivi", [])),
                json.dumps(llm_output.get("red_flags", []))
            ))

            # Aggiungi a watchlist
            c.execute("""
                INSERT OR IGNORE INTO watchlist (catalyst_id, status)
                VALUES (?, 'WATCHLIST')
            """, (catalyst_id,))

            conn.commit()
            opportunita.append(ticker)

        except Exception as e:
            print(f"    Errore salvataggio DB: {e}")
            conn.rollback()

    conn.close()

    print(f"\n{'='*60}")
    print(f"SCANSIONE COMPLETATA")
    print(f"Nuove opportunita aggiunte: {len(opportunita)}")
    if opportunita:
        print(f"Ticker: {', '.join(opportunita)}")
    else:
        print("Nessuna opportunita sopra soglia questa scansione.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run_monthly_scan()
