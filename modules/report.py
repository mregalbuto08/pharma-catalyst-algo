import os
import sys
import json
from datetime import datetime, date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import get_connection
import yfinance as yf

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PharmaCatalyst — {data}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f7; color: #1d1d1f; }}
  .nav {{ background: white; padding: 14px 24px; border-bottom: 1px solid #e5e5e5; display: flex; align-items: center; justify-content: space-between; }}
  .logo {{ font-size: 16px; font-weight: 600; }}
  .logo span {{ color: #1D9E75; }}
  .nav-right {{ font-size: 13px; color: #6e6e73; }}
  .main {{ max-width: 960px; margin: 0 auto; padding: 24px 16px; }}
  .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }}
  .metric {{ background: white; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  .metric-label {{ font-size: 12px; color: #6e6e73; margin-bottom: 6px; }}
  .metric-value {{ font-size: 24px; font-weight: 600; }}
  .metric-value.green {{ color: #1D9E75; }}
  .metric-value.red {{ color: #D85A30; }}
  .section-title {{ font-size: 11px; font-weight: 600; color: #6e6e73; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }}
  .card {{ background: white; border-radius: 12px; padding: 18px 20px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); border-left: 3px solid transparent; }}
  .card.action {{ border-left-color: #D85A30; }}
  .card.entra {{ border-left-color: #1D9E75; }}
  .card.watch {{ border-left-color: #378ADD; }}
  .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }}
  .ticker {{ font-size: 16px; font-weight: 600; }}
  .company {{ font-size: 13px; color: #6e6e73; margin-top: 2px; }}
  .badges {{ display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }}
  .badge {{ font-size: 11px; padding: 3px 9px; border-radius: 20px; font-weight: 500; }}
  .badge-green {{ background: #e1f5ee; color: #0f6e56; }}
  .badge-amber {{ background: #faeeda; color: #854f0b; }}
  .badge-blue {{ background: #e6f1fb; color: #185fa5; }}
  .badge-red {{ background: #faece7; color: #993c1d; }}
  .badge-gray {{ background: #f0f0f0; color: #555; }}
  .ev {{ font-size: 15px; font-weight: 600; color: #1D9E75; }}
  .ev.warn {{ color: #EF9F27; }}
  .fields {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px; }}
  .field-label {{ font-size: 11px; color: #8e8e93; margin-bottom: 2px; }}
  .field-value {{ font-size: 13px; font-weight: 500; }}
  .bar-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }}
  .bar-label {{ font-size: 11px; color: #8e8e93; width: 56px; }}
  .bar-bg {{ flex: 1; height: 4px; background: #f0f0f0; border-radius: 2px; }}
  .bar-fill {{ height: 100%; border-radius: 2px; }}
  .bar-val {{ font-size: 11px; font-weight: 500; width: 28px; text-align: right; color: #555; }}
  .tags {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }}
  .tag {{ font-size: 11px; padding: 2px 8px; border-radius: 4px; }}
  .tag-pos {{ background: #eaf3de; color: #3b6d11; }}
  .tag-neg {{ background: #fcebeb; color: #a32d2d; }}
  .alert-box {{ background: #fff8e1; border: 1px solid #ffe082; border-radius: 10px; padding: 14px 16px; margin-bottom: 24px; }}
  .alert-title {{ font-size: 13px; font-weight: 600; color: #e65100; margin-bottom: 8px; }}
  .alert-item {{ font-size: 13px; color: #555; padding: 4px 0; border-bottom: 1px solid #fff3cd; }}
  .alert-item:last-child {{ border-bottom: none; }}
  .wait-box {{ background: white; border-radius: 12px; padding: 32px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  .wait-title {{ font-size: 18px; font-weight: 600; color: #1d1d1f; margin-bottom: 8px; }}
  .wait-sub {{ font-size: 14px; color: #6e6e73; }}
  .footer {{ text-align: center; font-size: 11px; color: #8e8e93; padding: 24px 0; }}
  @media (max-width: 600px) {{
    .metrics {{ grid-template-columns: repeat(2, 1fr); }}
    .fields {{ grid-template-columns: repeat(2, 1fr); }}
  }}
</style>
</head>
<body>
<nav class="nav">
  <div class="logo">Pharma<span>Catalyst</span></div>
  <div class="nav-right">Aggiornato {ora} · {data}</div>
</nav>
<div class="main">

  <div class="metrics">
    <div class="metric">
      <div class="metric-label">Opportunita attive</div>
      <div class="metric-value {color_opp}">{n_opportunita}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Azioni richieste</div>
      <div class="metric-value {color_azioni}">{n_azioni}</div>
    </div>
    <div class="metric">
      <div class="metric-label">In watchlist</div>
      <div class="metric-value">{n_watchlist}</div>
    </div>
    <div class="metric">
      <div class="metric-label">EV medio</div>
      <div class="metric-value green">+{ev_medio:.1f}%</div>
    </div>
  </div>

  {alert_section}

  {opportunita_section}

  <div class="footer">
    PharmaCatalyst · Aggiornato automaticamente ogni mattina · Non e consulenza finanziaria
  </div>
</div>
</body>
</html>"""

CARD_TEMPLATE = """<div class="card {card_class}">
  <div class="card-header">
    <div>
      <div class="ticker">{ticker} <span style="font-size:13px;font-weight:400;color:#8e8e93">· {company}</span></div>
      <div class="company">{drug} · {indication}</div>
    </div>
    <div class="badges">
      <span class="badge {badge_cat}">{categoria}</span>
      <span class="ev {ev_class}">EV {ev:+.1f}%</span>
      <span class="badge {badge_timing}">{timing}</span>
    </div>
  </div>
  <div class="fields">
    <div><div class="field-label">Fase</div><div class="field-value">{catalyst_type}</div></div>
    <div><div class="field-label">Data catalista</div><div class="field-value">{catalyst_date} · {date_reliability}</div></div>
    <div><div class="field-label">Prezzo attuale</div><div class="field-value">{prezzo} {pnl_str}</div></div>
  </div>
  <div class="bar-row">
    <span class="bar-label">Scientifico</span>
    <div class="bar-bg"><div class="bar-fill" style="width:{score_sci}%;background:#1D9E75;"></div></div>
    <span class="bar-val">{score_sci}</span>
  </div>
  <div class="bar-row">
    <span class="bar-label">Movimento</span>
    <div class="bar-bg"><div class="bar-fill" style="width:{score_mov}%;background:#378ADD;"></div></div>
    <span class="bar-val">{score_mov}</span>
  </div>
  {aggiornamento}
  <div class="tags">
    {tags_pos}
    {tags_neg}
  </div>
</div>"""


def get_prezzo_attuale(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return info.get("currentPrice") or info.get("regularMarketPrice", 0)
    except Exception:
        return 0


def genera_report():
    """
    Genera il file HTML del report giornaliero.
    """
    conn = get_connection()
    c = conn.cursor()

    # Recupera opportunita attive
    rows = c.execute("""
        SELECT
            c.ticker, c.name,
            cat.drug_name, cat.indication, cat.catalyst_type,
            cat.catalyst_date, cat.date_reliability, cat.fda_designations,
            s.score_scientifico, s.score_movimento, s.ev_stimato, s.timing,
            s.segnali_positivi, s.rischi,
            w.status, w.entry_price, w.stop_price, w.target_parziale, w.target_finale,
            cat.id as catalyst_id
        FROM watchlist w
        JOIN catalysts cat ON w.catalyst_id = cat.id
        JOIN companies c ON cat.company_id = c.id
        LEFT JOIN scores s ON s.catalyst_id = cat.id
        WHERE w.status IN ('WATCHLIST', 'POSIZIONE_APERTA')
        ORDER BY s.ev_stimato DESC
    """).fetchall()

    # Recupera aggiornamenti di oggi
    today = date.today().isoformat()
    updates = c.execute("""
        SELECT catalyst_id, trigger_type, descrizione, azione_suggerita
        FROM daily_updates
        WHERE update_date = ? AND azione_suggerita != 'TIENI'
        ORDER BY created_at DESC
    """, (today,)).fetchall()

    conn.close()

    opportunita_html = ""
    n_azioni = 0
    n_watchlist = 0
    ev_totale = 0
    alert_items = []

    updates_map = {}
    for upd in updates:
        updates_map[upd["catalyst_id"]] = upd

    if not rows:
        opportunita_html = """
        <div class="wait-box">
          <div class="wait-title">Nessuna opportunita sopra soglia</div>
          <div class="wait-sub">Il sistema non ha trovato trade che rispettano i criteri minimi.<br>Aspetta la prossima scansione mensile.</div>
        </div>"""
    else:
        for row in rows:
            row = dict(row)
            ticker = row["ticker"]
            timing = row["timing"] or "WATCHLIST"
            ev = row["ev_stimato"] or 0
            score_sci = row["score_scientifico"] or 0
            score_mov = row["score_movimento"] or 0
            status = row["status"]

            ev_totale += ev

            if timing == "ENTRA ORA":
                n_azioni += 1
                card_class = "entra"
                badge_timing = "badge-green"
            elif status == "POSIZIONE_APERTA":
                n_azioni += 1
                card_class = "action"
                badge_timing = "badge-gray"
            else:
                n_watchlist += 1
                card_class = "watch"
                badge_timing = "badge-blue"

            # Badge categoria
            if row["catalyst_type"] == "PDUFA":
                badge_cat = "badge-green"
                categoria = "PDUFA"
            else:
                badge_cat = "badge-amber"
                categoria = "Phase 3"

            # Prezzo e P&L
            prezzo = get_prezzo_attuale(ticker)
            prezzo_str = f"${prezzo:.2f}" if prezzo else "N/D"
            pnl_str = ""
            if row.get("entry_price") and prezzo:
                pnl = (prezzo - row["entry_price"]) / row["entry_price"] * 100
                color = "green" if pnl >= 0 else "red"
                pnl_str = f'<span style="color:{"#1D9E75" if pnl >= 0 else "#D85A30"}">({pnl:+.1f}%)</span>'

            # EV class
            ev_class = "" if ev >= 25 else "warn"

            # Tags
            try:
                segnali = json.loads(row["segnali_positivi"] or "[]")
                rischi = json.loads(row["rischi"] or "[]")
            except Exception:
                segnali = []
                rischi = []

            tags_pos = " ".join([f'<span class="tag tag-pos">{s}</span>' for s in segnali[:3]])
            tags_neg = " ".join([f'<span class="tag tag-neg">{r}</span>' for r in rischi[:2]])

            # Aggiornamento di oggi
            upd = updates_map.get(row["catalyst_id"])
            aggiornamento_html = ""
            if upd:
                color_map = {"positivo": "#1D9E75", "negativo": "#D85A30", "neutro": "#6e6e73"}
                aggiornamento_html = f'<div style="font-size:12px;color:{color_map.get("neutro","#555")};margin-top:8px;padding:6px 8px;background:#f9f9f9;border-radius:6px">📌 {upd["descrizione"]}</div>'
                if upd["azione_suggerita"] not in ["TIENI", "WATCHLIST"]:
                    alert_items.append(f"{ticker}: {upd['descrizione']} → {upd['azione_suggerita']}")

            opportunita_html += CARD_TEMPLATE.format(
                card_class=card_class,
                ticker=ticker,
                company=row["name"] or ticker,
                drug=row["drug_name"] or "Farmaco principale",
                indication=row["indication"] or "Indicazione principale",
                badge_cat=badge_cat,
                categoria=categoria,
                ev=ev,
                ev_class=ev_class,
                badge_timing=badge_timing,
                timing=timing,
                catalyst_type=row["catalyst_type"] or "N/D",
                catalyst_date=row["catalyst_date"] or "Da confermare",
                date_reliability=row["date_reliability"] or "MEDIA",
                prezzo=prezzo_str,
                pnl_str=pnl_str,
                score_sci=score_sci,
                score_mov=score_mov,
                aggiornamento=aggiornamento_html,
                tags_pos=tags_pos,
                tags_neg=tags_neg
            )

    # Alert section
    alert_section = ""
    if alert_items:
        items_html = "".join([f'<div class="alert-item">⚠️ {item}</div>' for item in alert_items])
        alert_section = f'<div class="alert-box"><div class="alert-title">Azioni richieste oggi</div>{items_html}</div>'

    n_opportunita = len(rows)
    ev_medio = ev_totale / n_opportunita if n_opportunita > 0 else 0

    html = HTML_TEMPLATE.format(
        data=date.today().strftime("%d %b %Y"),
        ora=datetime.now().strftime("%H:%M"),
        n_opportunita=n_opportunita,
        color_opp="green" if n_opportunita > 0 else "",
        n_azioni=n_azioni,
        color_azioni="red" if n_azioni > 0 else "",
        n_watchlist=n_watchlist,
        ev_medio=ev_medio,
        alert_section=alert_section,
        opportunita_section=f'<div class="section-title">Opportunita attive</div>{opportunita_html}' if opportunita_html else ""
    )

    # Salva il file HTML
    output_dir = "web"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "index.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Report generato: {output_path}")
    return output_path


if __name__ == "__main__":
    genera_report()
