import json

def calcola_score_scientifico(catalyst_type, fda_designations, crl_precedente, llm_output):
    """
    Calcola lo score scientifico (0-100) basato su base rate per fase
    e aggiustamenti da designazioni FDA e analisi LLM.
    """
    base_rates = {
        "PDUFA": 75,
        "PHASE3_READOUT": 58
    }

    score = base_rates.get(catalyst_type, 50)
    designations = fda_designations.lower() if fda_designations else ""

    # Aggiustamenti regolatori
    if "breakthrough therapy" in designations:
        score += 12
    if "priority review" in designations:
        score += 10
    if "fast track" in designations:
        score += 6
    if "orphan drug" in designations:
        score += 4
    if crl_precedente:
        score -= 20

    # Aggiustamenti da LLM
    if llm_output.get("meccanismo_validato_da_approvati"):
        score += 12
    if llm_output.get("biomarker_selection"):
        score += 10
    if llm_output.get("management_tono") == "ottimista":
        score += 5
    elif llm_output.get("management_tono") == "cauto":
        score -= 3
    if llm_output.get("endpoint_tipo") == "oggettivo":
        score += 5
    elif llm_output.get("endpoint_tipo") == "soggettivo":
        score -= 6
    if llm_output.get("enrollment_status") == "in anticipo":
        score += 4
    elif llm_output.get("enrollment_status") == "in ritardo":
        score -= 8

    competitor_count = llm_output.get("competitor_approvati_stessa_indicazione", 0)
    if competitor_count == 0:
        score += 8
    elif competitor_count >= 3:
        score -= 5

    return min(max(int(score), 0), 100)


def calcola_score_movimento(financial_data, llm_output, news_volume):
    """
    Calcola lo score movimento (0-100) basato su dati finanziari,
    struttura pipeline e visibilità di mercato.
    """
    score = 50

    # Compressione del titolo dal 52wk high
    prezzo = financial_data.get("prezzo_attuale", 0)
    high_52 = financial_data.get("52wk_high", 0)
    if high_52 > 0 and prezzo > 0:
        compressione = (high_52 - prezzo) / high_52
        if compressione > 0.50:
            score += 20
        elif compressione > 0.30:
            score += 12
        elif compressione > 0.15:
            score += 6
        elif compressione < 0:
            score -= 15

    # Struttura pipeline
    pipeline_count = financial_data.get("pipeline_asset_count", 5)
    if pipeline_count == 1:
        score += 25
    elif pipeline_count == 2:
        score += 15
    elif pipeline_count >= 10:
        score -= 10

    # Float
    float_shares = financial_data.get("float_shares", 0)
    if float_shares > 0:
        if float_shares < 20_000_000:
            score += 15
        elif float_shares < 50_000_000:
            score += 8

    # Short interest
    short_pct = financial_data.get("short_percent_float", 0)
    if short_pct > 0.15:
        score += 12
    elif short_pct > 0.10:
        score += 6

    # Mercato addressable
    competitor_count = llm_output.get("competitor_approvati_stessa_indicazione", 0)
    if competitor_count == 0:
        score += 15
    elif competitor_count >= 5:
        score -= 15

    # Visibilita (sotto il radar e meglio)
    if news_volume < 10:
        score += 10
    elif news_volume > 100:
        score -= 10

    # Insider buying
    insider_net = financial_data.get("insider_net_30gg", 0)
    if insider_net > 0:
        score += 5

    # Gia prezzato?
    movimento_1mese = financial_data.get("movimento_1mese", 0)
    if movimento_1mese > 0.40:
        score -= 20
    elif movimento_1mese > 0.20:
        score -= 10

    # Diluizione recente
    if financial_data.get("diluizione_recente", False):
        score -= 10

    return min(max(int(score), 0), 100)


def calcola_ev(score_scientifico, score_movimento, catalyst_type):
    """
    Calcola l'Expected Value del trade.
    EV = (prob_successo * guadagno_atteso) - (prob_fallimento * perdita_attesa)
    """
    prob_successo = score_scientifico / 100
    prob_fallimento = 1 - prob_successo

    guadagno_base = {
        "PDUFA": 50,
        "PHASE3_READOUT": 80
    }
    perdita_attesa = {
        "PDUFA": 40,
        "PHASE3_READOUT": 55
    }

    guadagno_atteso = guadagno_base.get(catalyst_type, 50) * (score_movimento / 100)
    perdita = perdita_attesa.get(catalyst_type, 45)

    ev = (prob_successo * guadagno_atteso) - (prob_fallimento * perdita)
    return round(ev, 2)


def soglia_minima(catalyst_type):
    soglie = {
        "PDUFA": 20,
        "PHASE3_READOUT": 25
    }
    return soglie.get(catalyst_type, 20)


def supera_soglia(ev, catalyst_type):
    return ev >= soglia_minima(catalyst_type)


def calcola_timing(catalyst_date_str, date_reliability, red_flags=None):
    """
    Determina il timing di ingresso basato su affidabilita della data
    e segnali di mercato.
    """
    from datetime import datetime, date

    if red_flags is None:
        red_flags = []

    # Red flag override immediato
    if "slittamento_data" in red_flags:
        return "ESCI"
    if "insider_selling_massiccio" in red_flags:
        return "RIVALUTA"

    if not catalyst_date_str or date_reliability == "BASSA":
        return "EVITA"

    try:
        catalyst_date = datetime.strptime(catalyst_date_str, "%Y-%m-%d").date()
        oggi = date.today()
        settimane_al_catalista = (catalyst_date - oggi).days / 7
    except Exception:
        return "WATCHLIST"

    if date_reliability == "CERTA":
        if settimane_al_catalista <= 6:
            return "ENTRA ORA"
        else:
            return "WATCHLIST"
    elif date_reliability == "ALTA":
        return "WATCHLIST"
    else:
        return "WATCHLIST"
