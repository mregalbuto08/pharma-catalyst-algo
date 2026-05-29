import os
import sys
import json
import time
from datetime import datetime, date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import get_connection
from modules.data_collection import (
    get_financial_data,
    get_edgar_cik,
    get_recent_8k,
    get_form4_recent,
    get_news,
    fetch_url_text
)
from modules.llm_analysis import analizza_documento_monitor
from modules.scoring import calcola_timing

NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")


def get_watchlist_active():
    """
    Recupera tutte le compagnie in watchlist o posizione aperta.
    """
    conn = get_connection()
    c = conn.cursor()
    rows = c.execute("""
        SELECT
            w.id as watchlist_id,
            w.status,
            w.entry_price,
            w.stop_price,
            w.target_parziale,
            w.target_finale,
            c.ticker,
            c.name,
            c.cik,
            cat.id as catalyst_id,
            cat.drug_name,
            cat.indication,
            cat.catalyst_type,
            cat.catalyst_date,
            cat.date_reliability,
            cat.fda_designations,
            s.score_scientifico,
            s.score_movimento,
            s.ev_stimato,
            s.timing,
            s.segnali_positivi,
            s.rischi
        FROM watchlist w
        JOIN catalysts cat ON w.catalyst_id = cat.id
        JOIN companies c ON cat.company_id = c.id
        LEFT JOIN scores s ON s.catalyst_id = cat.id
        WHERE w.status IN ('WATCHLIST', 'POSIZIONE_APERTA')
        ORDER BY s.ev_stimato DESC
    """).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def aggiorna_score_movimento(catalyst_id, financial_data):
    """
    Aggiorna lo score movimento con dati finanziari freschi.
    """
    from modules.scoring import calcola_score_movimento, calcola_ev
    conn = get_connection()
    c = conn.cursor()

    row = c.execute("""
        SELECT score_scientifico, llm_output, catalyst_type
        FROM scores s
        JOIN catalysts cat ON s.catalyst_id = cat.id
        WHERE s.catalyst_id = ?
        ORDER BY s.created_at DESC LIMIT 1
    """, (catalyst_id,)).fetchone()

    if not row:
        conn.close()
        return

    llm_output = json.loads(row["llm_output"]) if row["llm_output"] else {}
    score_sci = row["score_scientifico"]
    catalyst_type = row["catalyst_type"]

    score_mov = calcola_score_movimento(financial_data, llm_output, 5)
    ev = calcola_ev(score_sci, score_mov, catalyst_type)

    c.execute("""
        UPDATE scores SET score_movimento = ?, ev_stimato = ?
        WHERE catalyst_id = ?
    """, (score_mov, ev, catalyst_id))
    conn.commit()
    conn.close()


def salva_aggiornamento(catalyst_id, trigger_type, descrizione, azione, ev_precedente, ev_aggiornato):
    """
    Salva un aggiornamento giornaliero nel database.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO daily_updates
        (catalyst_id, update_date, trigger_type, descrizione, azione_suggerita, ev_precedente, ev_aggiornato)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        catalyst_id,
        date.today().isoformat(),
        trigger_type,
        descrizione,
        azione,
        ev_precedente,
        ev_aggiornato
    ))
    conn.commit()
    conn.close()


def aggiorna_timing_watchlist(watchlist_id, nuovo_status):
    """
    Aggiorna lo status nella watchlist.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE watchlist SET status = ? WHERE id = ?", (nuovo_status, watchlist_id))
    conn.commit()
    conn.close()


def run_daily_monitor():
    """
    Monitoring giornaliero di tutte le compagnie in watchlist.
    """
    print(f"\n{'='*60}")
    print(f"MONITORING GIORNALIERO — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    watchlist = get_watchlist_active()

    if not watchlist:
        print("Nessuna compagnia in watchlist. In attesa della prossima scansione mensile.")
        return []

    print(f"Compagnie monitorate: {len(watchlist)}")
    tickers = [item["ticker"] for item in watchlist]

    # Fetch news aggregate (una sola chiamata API per tutti i ticker)
    print("\nRecupero news aggregate...")
    news_data = get_news(NEWS_API_KEY, tickers, days=1)

    aggiornamenti = []

    for item in watchlist:
        ticker = item["ticker"]
        company = item["name"] or ticker
        drug = item["drug_name"] or "farmaco principale"
        catalyst_id = item["catalyst_id"]
        watchlist_id = item["watchlist_id"]
        ev_precedente = item["ev_stimato"] or 0

        print(f"\n  Monitoring {ticker}...")

        trigger_trovati = []

        # 1. Aggiorna dati finanziari
        financial_data = get_financial_data(ticker)
        if financial_data:
            aggiorna_score_movimento(catalyst_id, financial_data)
            prezzo = financial_data.get("prezzo_attuale", 0)
            entry = item.get("entry_price")
            if entry and entry > 0:
                pnl = (prezzo - entry) / entry * 100
                print(f"    Prezzo: ${prezzo:.2f} | P&L: {pnl:+.1f}%")
            else:
                print(f"    Prezzo: ${prezzo:.2f}")

        # 2. Controlla nuovi 8-K
        cik = item.get("cik")
        if not cik:
            cik = get_edgar_cik(ticker)
            if cik:
                conn = get_connection()
                conn.execute("UPDATE companies SET cik = ? WHERE ticker = ?", (cik, ticker))
                conn.commit()
                conn.close()

        if cik:
            nuovi_8k = get_recent_8k(cik, days=1)
            for filing in nuovi_8k:
                print(f"    Nuovo 8-K trovato: {filing['date']}")
                text = fetch_url_text(filing["url"])
                if text:
                    analisi = analizza_documento_monitor(company, ticker, drug, text)
                    if analisi.get("impatta_tesi"):
                        trigger_trovati.append(analisi)
                        print(f"    TRIGGER: {analisi['tipo_trigger']} | {analisi['direzione']} | Azione: {analisi['azione_suggerita']}")
                time.sleep(1)

            # 3. Controlla nuovi Form 4
            form4s = get_form4_recent(cik, days=1)
            if form4s:
                print(f"    Form 4 trovati: {len(form4s)}")
                trigger_trovati.append({
                    "impatta_tesi": True,
                    "direzione": "positivo",
                    "tipo_trigger": "insider_buying",
                    "descrizione": f"{len(form4s)} transazione insider nelle ultime 24 ore",
                    "azione_suggerita": "RIVALUTA"
                })

        # 4. Analizza news
        ticker_news = news_data.get(ticker, [])
        if ticker_news:
            print(f"    News trovate: {len(ticker_news)}")
            for article in ticker_news[:2]:
                text = f"{article.get('title', '')} {article.get('description', '')}"
                analisi = analizza_documento_monitor(company, ticker, drug, text)
                if analisi.get("impatta_tesi"):
                    trigger_trovati.append(analisi)
                    print(f"    NEWS TRIGGER: {analisi['descrizione']}")

        # 5. Determina azione finale
        if trigger_trovati:
            azioni_priorita = ["ESCI", "ENTRA ORA", "RIVALUTA", "WATCHLIST", "TIENI"]
            azione_finale = "TIENI"
            for priorita in azioni_priorita:
                if any(t.get("azione_suggerita") == priorita for t in trigger_trovati):
                    azione_finale = priorita
                    break

            descrizione = "; ".join([t.get("descrizione", "") for t in trigger_trovati if t.get("impatta_tesi")])

            salva_aggiornamento(
                catalyst_id=catalyst_id,
                trigger_type=trigger_trovati[0].get("tipo_trigger", "altro"),
                descrizione=descrizione,
                azione=azione_finale,
                ev_precedente=ev_precedente,
                ev_aggiornato=ev_precedente
            )

            if azione_finale == "ENTRA ORA":
                aggiorna_timing_watchlist(watchlist_id, "WATCHLIST")

            aggiornamenti.append({
                "ticker": ticker,
                "azione": azione_finale,
                "descrizione": descrizione,
                "trigger_count": len(trigger_trovati)
            })
            print(f"    AZIONE FINALE: {azione_finale}")
        else:
            print(f"    Nessun cambiamento rilevante.")
            salva_aggiornamento(
                catalyst_id=catalyst_id,
                trigger_type="routine",
                descrizione="Nessun cambiamento rilevante.",
                azione="TIENI",
                ev_precedente=ev_precedente,
                ev_aggiornato=ev_precedente
            )

        time.sleep(2)

    print(f"\n{'='*60}")
    print(f"MONITORING COMPLETATO")
    print(f"Trigger trovati: {len(aggiornamenti)}")
    print(f"{'='*60}\n")

    return aggiornamenti


if __name__ == "__main__":
    run_daily_monitor()
