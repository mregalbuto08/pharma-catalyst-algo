import os
import json
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SCAN_PROMPT = """Sei un analista farmaceutico esperto. Analizza i seguenti testi su {company} e il farmaco {drug} per {indication}.

TESTI:
{texts}

Rispondi SOLO in JSON valido, senza testo aggiuntivo, con questa struttura esatta:

{{
  "meccanismo_validato_da_approvati": true o false,
  "competitor_approvati_stessa_indicazione": numero intero 0-10,
  "management_tono": "ottimista" o "neutro" o "cauto",
  "endpoint_tipo": "oggettivo" o "soggettivo" o "misto",
  "biomarker_selection": true o false,
  "enrollment_status": "in anticipo" o "in linea" o "in ritardo" o "completato" o "sconosciuto",
  "data_readout_confermata": "Q3 2026" oppure null,
  "red_flags": [],
  "segnali_positivi": [],
  "sommario_tesi": "2-3 frasi sulla tesi di investimento"
}}"""


MONITOR_PROMPT = """Sei un analista farmaceutico esperto. Analizza questo documento recente su {company} ({ticker}), farmaco {drug}.

DOCUMENTO:
{text}

Determina se questo documento cambia la tesi di investimento.
Rispondi SOLO in JSON valido, senza testo aggiuntivo:

{{
  "impatta_tesi": true o false,
  "direzione": "positivo" o "negativo" o "neutro",
  "tipo_trigger": "data_confermata" o "insider_buying" o "insider_selling" o "designazione_fda" o "slittamento_data" o "diluizione" o "competitor_news" o "altro",
  "descrizione": "una frase che descrive cosa e cambiato",
  "azione_suggerita": "ENTRA ORA" o "WATCHLIST" o "TIENI" o "ESCI" o "RIVALUTA"
}}"""


def analizza_compagnia(company, drug, indication, texts):
    """
    Analisi LLM completa per la scansione mensile.
    Restituisce dizionario JSON o valori di default se fallisce.
    """
    default = {
        "meccanismo_validato_da_approvati": False,
        "competitor_approvati_stessa_indicazione": 2,
        "management_tono": "neutro",
        "endpoint_tipo": "oggettivo",
        "biomarker_selection": False,
        "enrollment_status": "sconosciuto",
        "data_readout_confermata": None,
        "red_flags": [],
        "segnali_positivi": [],
        "sommario_tesi": "Dati insufficienti per analisi completa."
    }

    if not texts:
        return default

    combined = "\n\n---\n\n".join(texts)[:4000]
    prompt = SCAN_PROMPT.format(
        company=company,
        drug=drug,
        indication=indication,
        texts=combined
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=800
        )
        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print(f"Errore LLM analisi compagnia {company}: {e}")
        return default


def analizza_documento_monitor(company, ticker, drug, text):
    """
    Analisi LLM di un singolo documento per il monitoring giornaliero.
    """
    default = {
        "impatta_tesi": False,
        "direzione": "neutro",
        "tipo_trigger": "altro",
        "descrizione": "Nessun cambiamento rilevante.",
        "azione_suggerita": "TIENI"
    }

    if not text or len(text) < 50:
        return default

    prompt = MONITOR_PROMPT.format(
        company=company,
        ticker=ticker,
        drug=drug,
        text=text[:3000]
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300
        )
        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print(f"Errore LLM monitor {ticker}: {e}")
        return default
