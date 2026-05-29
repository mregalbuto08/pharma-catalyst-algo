# PharmaCatalyst Algo

Sistema automatizzato di identificazione di opportunità di investimento nel settore farmaceutico/biotech, basato su eventi catalisti binari con data nota.

## Cosa fa

- **Scansione mensile** (primo lunedì del mese): analizza 800+ compagnie pharma small/mid cap su NYSE e Nasdaq, identifica quelle con PDUFA o Phase 3 readout nei prossimi 90 giorni, calcola l'Expected Value per ognuna
- **Monitoring giornaliero** (ogni mattina lun-sab): monitora le compagnie in watchlist, legge nuovi 8-K, Form 4 e news, aggiorna i punteggi
- **Report HTML** generato automaticamente e accessibile via GitHub Pages

## Costo totale: $0/mese

## Setup in 5 passi

### 1. Fork o clone del repository
```bash
git clone https://github.com/mregalbuto08/pharma-catalyst-algo
cd pharma-catalyst-algo
```

### 2. Aggiungi i Secrets su GitHub
Vai su: Settings → Secrets and variables → Actions → New repository secret

- `GROQ_API_KEY` — da console.groq.com (gratuito)
- `NEWS_API_KEY` — da newsapi.org (gratuito)

### 3. Abilita GitHub Pages
Vai su: Settings → Pages → Source → seleziona "GitHub Actions"

### 4. Esegui la prima scansione manualmente
Vai su: Actions → Monthly Scan → Run workflow

### 5. Accedi al sito
`https://mregalbuto08.github.io/pharma-catalyst-algo`

## Test in locale

```bash
pip install -r requirements.txt

# Inizializza database
python db/database.py

# Scansione manuale
GROQ_API_KEY=tua_key NEWS_API_KEY=tua_key python modules/scanner.py

# Monitoring manuale
GROQ_API_KEY=tua_key NEWS_API_KEY=tua_key python modules/monitor.py

# Genera report
python modules/report.py
```

## Struttura

```
pharma-catalyst-algo/
├── .github/workflows/
│   ├── monthly_scan.yml      # scansione mensile automatica
│   └── daily_monitor.yml     # monitoring giornaliero automatico
├── modules/
│   ├── scanner.py            # modulo scansione mensile
│   ├── monitor.py            # modulo monitoring giornaliero
│   ├── scoring.py            # scoring engine (EV calculation)
│   ├── data_collection.py    # raccolta dati (EDGAR, yfinance, ecc.)
│   ├── llm_analysis.py       # analisi LLM con Groq
│   └── report.py             # generazione report HTML
├── db/
│   └── database.py           # schema e connessione SQLite
├── web/
│   └── index.html            # report generato automaticamente
└── requirements.txt
```

## Disclaimer

Questo sistema è uno strumento di analisi, non un sistema di trading automatico. Non fornisce consulenza finanziaria. Le decisioni di investimento sono di esclusiva responsabilità dell'utente.
