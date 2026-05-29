import os
import sys
import json
from datetime import datetime, date, timedelta

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
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f0f2f5; color: #1d1d1f; }}
  .nav {{ background: white; padding: 14px 28px; border-bottom: 1px solid #e5e5e5; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
  .logo {{ font-size: 17px; font-weight: 700; letter-spacing: -0.3px; }}
  .logo span {{ color: #1D9E75; }}
  .nav-right {{ font-size: 12px; color: #8e8e93; }}
  .main {{ max-width: 1100px; margin: 0 auto; padding: 24px 16px; }}
  .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }}
  .metric {{ background: white; border-radius: 14px; padding: 18px 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
  .metric-label {{ font-size: 12px; color: #8e8e93; margin-bottom: 6px; font-weight: 500; }}
  .metric-value {{ font-size: 26px; font-weight: 700; letter-spacing: -0.5px; }}
  .metric-sub {{ font-size: 12px; color: #aeaeb2; margin-top: 3px; }}
  .green {{ color: #1D9E75; }}
  .red {{ color: #D85A30; }}
  .amber {{ color: #EF9F27; }}
  .section {{ margin-bottom: 28px; }}
  .section-title {{ font-size: 11px; font-weight: 700; color: #8e8e93; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 12px; padding-left: 2px; }}
  .card {{ background: white; border-radius: 16px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); overflow: hidden; border: 1px solid #f0f0f0; }}
  .card-header {{ padding: 18px 20px 16px; border-bottom: 1px solid #f5f5f5; display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }}
  .card-header-left {{ flex: 1; }}
  .card-header-right {{ display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }}
  .ticker {{ font-size: 20px; font-weight: 700; letter-spacing: -0.5px; }}
  .company-name {{ font-size: 13px; color: #6e6e73; margin-top: 2px; }}
  .drug-info {{ font-size: 13px; color: #3a3a3c; margin-top: 4px; font-weight: 500; }}
  .badge {{ font-size: 11px; padding: 3px 10px; border-radius: 20px; font-weight: 600; white-space: nowrap; }}
  .badge-green {{ background: #e1f5ee; color: #0f6e56; }}
  .badge-amber {{ background: #faeeda; color: #854f0b; }}
  .badge-red {{ background: #faece7; color: #993c1d; }}
  .badge-blue {{ background: #e6f1fb; color: #185fa5; }}
  .badge-gray {{ background: #f0f0f0; color: #555; }}
  .ev-value {{ font-size: 18px; font-weight: 700; }}
  .card-body {{ padding: 18px 20px; }}
  .card-section {{ margin-bottom: 20px; }}
  .card-section:last-child {{ margin-bottom: 0; }}
  .card-section-title {{ font-size: 11px; font-weight: 700; color: #aeaeb2; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 10px; }}
  .fields-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
  .fields-grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
  .field {{ background: #f9f9fb; border-radius: 10px; padding: 10px 12px; }}
  .field-label {{ font-size: 11px; color: #8e8e93; margin-bottom: 4px; font-weight: 500; }}
  .field-value {{ font-size: 14px; font-weight: 600; color: #1d1d1f; }}
  .score-section {{ display: flex; flex-direction: column; gap: 8px; }}
  .score-row {{ display: flex; align-items: center; gap: 10px; }}
  .score-label {{ font-size: 12px; color: #6e6e73; width: 80px; font-weight: 500; }}
  .score-bar-bg {{ flex: 1; height: 6px; background: #f0f0f0; border-radius: 3px; overflow: hidden; }}
  .score-bar-fill {{ height: 100%; border-radius: 3px; }}
  .score-val {{ font-size: 13px; font-weight: 700; width: 32px; text-align: right; }}
  .tags {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .tag {{ font-size: 12px; padding: 4px 10px; border-radius: 6px; font-weight: 500; }}
  .tag-pos {{ background: #eaf3de; color: #2d5a0e; }}
  .tag-neg {{ background: #fde8e8; color: #8b1a1a; }}
  .price-block {{ display: flex; align-items: baseline; gap: 8px; margin-bottom: 4px; }}
  .price-big {{ font-size: 28px; font-weight: 700; letter-spacing: -1px; }}
  .price-change {{ font-size: 14px; font-weight: 600; }}
  .price-meta {{ font-size: 12px; color: #8e8e93; }}
  .levels-row {{ display: flex; gap: 10px; margin-top: 12px; }}
  .level-box {{ flex: 1; background: #f9f9fb; border-radius: 10px; padding: 10px 12px; text-align: center; }}
  .level-label {{ font-size: 10px; color: #8e8e93; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; margin-bottom: 4px; }}
  .level-value {{ font-size: 15px; font-weight: 700; }}
  .level-value.stop {{ color: #D85A30; }}
  .level-value.target {{ color: #1D9E75; }}
  .level-pct {{ font-size: 11px; color: #8e8e93; margin-top: 2px; }}
  .log-item {{ display: flex; align-items: flex-start; gap: 10px; padding: 8px 0; border-bottom: 1px solid #f5f5f5; }}
  .log-item:last-child {{ border-bottom: none; }}
  .log-dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; }}
  .log-text {{ font-size: 13px; color: #3a3a3c; line-height: 1.5; }}
  .log-date {{ font-size: 11px; color: #8e8e93; margin-top: 2px; }}
  .alert-box {{ background: #fff8e6; border: 1px solid #ffe082; border-radius: 12px; padding: 14px 16px; margin-bottom: 20px; }}
  .alert-title {{ font-size: 13px; font-weight: 700; color: #b45309; margin-bottom: 8px; }}
  .alert-item {{ font-size: 13px; color: #78350f; padding: 4px 0; }}
  .wait-box {{ background: white; border-radius: 16px; padding: 48px 32px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
  .wait-title {{ font-size: 20px; font-weight: 700; margin-bottom: 10px; }}
  .wait-sub {{ font-size: 14px; color: #6e6e73; line-height: 1.6; }}
  .divider {{ border: none; border-top: 1px solid #f0f0f0; margin: 16px 0; }}
  .footer {{ text-align: center; font-size: 12px; color: #aeaeb2; padding: 32px 0 16px; }}
  @media (max-width: 700px) {{
    .metrics {{ grid-template-columns: repeat(2, 1fr); }}
    .fields-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .fields-grid-3 {{ grid-template-columns: repeat(2, 1fr); }}
    .levels-row {{ flex-wrap: wrap; }}
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
      <div class="metric-sub">sopra soglia EV</div>
    </div>
    <div class="metric">
      <div class="metric-label">Azioni richieste</div>
      <div class="metric-value {color_azioni}">{n_azioni}</div>
      <div class="metric-sub">oggi</div>
    </div>
    <div class="metric">
      <div class="metric-label">In watchlist</div>
      <div class="metric-value">{n_watchlist}</div>
      <div class="metric-sub">da monitorare</div>
    </div>
    <div class="metric">
      <div class="metric-label">EV medio</div>
      <div class="metric-value green">+{ev_medio:.1f}%</div>
      <div class="metric-sub">expected value</div>
    </div>
  </div>
  {alert_section}
  {opportunita_section}
  <div class="footer">PharmaCatalyst · Aggiornato automaticamente ogni mattina · Non e consulenza finanziaria</div>
</div>
</body>
</html>"""


def get_financial_data_full(ticker_str):
    try:
        import time
        time.sleep(1)
        t = yf.Ticker(ticker_str)
        info = t.info
        prezzo = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        high_52 = info.get("fiftyTwoWeekHigh", 0)
        low_52 = info.get("fiftyTwoWeekLow", 0)
        prev_close = info.get("previousClose", 0)
        change_pct = ((prezzo - prev_close) / prev_close * 100) if prev_close else 0
        return {
            "prezzo": prezzo,
            "change_pct": change_pct,
            "high_52": high_52,
            "low_52": low_52,
            "market_cap": info.get("marketCap", 0),
            "float_shares": info.get("floatShares", 0),
            "short_percent": info.get("shortPercentOfFloat", 0) or 0,
            "cash": info.get("totalCash", 0),
            "volume": info.get("volume", 0),
            "avg_volume": info.get("averageVolume", 0),
        }
    except Exception as e:
        print(f"Errore yfinance {ticker_str}: {e}")
        return {}


def get_recent_updates(catalyst_id, days=7):
    conn = get_connection()
    c = conn.cursor()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = c.execute("""
        SELECT update_date, trigger_type, descrizione, azione_suggerita
        FROM daily_updates
        WHERE catalyst_id = ? AND update_date >= ?
        ORDER BY update_date DESC LIMIT 10
    """, (catalyst_id, cutoff)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def format_number(n):
    if not n: return "N/D"
    if n >= 1_000_000_000: return f"${n/1_000_000_000:.1f}B"
    if n >= 1_000_000: return f"${n/1_000_000:.0f}M"
    return f"${n:,.0f}"


def format_shares(n):
    if not n: return "N/D"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    return f"{n:,.0f}"


def genera_report():
    conn = get_connection()
    c = conn.cursor()
    rows = c.execute("""
        SELECT c.ticker, c.name, c.market_cap, c.cash, c.float_shares,
               c.short_interest, c.short_percent_float,
               cat.id as catalyst_id, cat.drug_name, cat.indication,
               cat.catalyst_type, cat.catalyst_date, cat.date_reliability, cat.fda_designations,
               s.score_scientifico, s.score_movimento, s.ev_stimato, s.timing,
               s.segnali_positivi, s.rischi,
               w.id as watchlist_id, w.status, w.entry_price, w.stop_price,
               w.target_parziale, w.target_finale, w.note
        FROM watchlist w
        JOIN catalysts cat ON w.catalyst_id = cat.id
        JOIN companies c ON cat.company_id = c.id
        LEFT JOIN scores s ON s.catalyst_id = cat.id
        WHERE w.status IN ('WATCHLIST', 'POSIZIONE_APERTA')
        ORDER BY s.ev_stimato DESC
    """).fetchall()

    today = date.today().isoformat()
    updates_today = c.execute("""
        SELECT catalyst_id, trigger_type, descrizione, azione_suggerita
        FROM daily_updates WHERE update_date = ? AND azione_suggerita NOT IN ('TIENI', 'routine')
        ORDER BY created_at DESC
    """, (today,)).fetchall()
    conn.close()

    updates_map = {u["catalyst_id"]: dict(u) for u in updates_today}
    opportunita_html = ""
    n_azioni = 0
    n_watchlist = 0
    ev_totale = 0
    alert_items = []

    if not rows:
        opportunita_html = """<div class="wait-box">
          <div class="wait-title">Nessuna opportunita sopra soglia</div>
          <div class="wait-sub">Il sistema non ha trovato trade che rispettano i criteri minimi.<br>La prossima scansione completa e il primo lunedi del mese.</div>
        </div>"""
    else:
        for row in rows:
            row = dict(row)
            ticker = row["ticker"]
            ev = row["ev_stimato"] or 0
            score_sci = row["score_scientifico"] or 0
            score_mov = row["score_movimento"] or 0
            timing = row["timing"] or "WATCHLIST"
            status = row["status"]
            catalyst_id = row["catalyst_id"]
            ev_totale += ev

            if timing == "ENTRA ORA":
                n_azioni += 1
                timing_badge = '<span class="badge badge-green">ENTRA ORA</span>'
            elif status == "POSIZIONE_APERTA":
                n_azioni += 1
                timing_badge = '<span class="badge badge-gray">POSIZIONE APERTA</span>'
            else:
                n_watchlist += 1
                timing_badge = '<span class="badge badge-blue">WATCHLIST</span>'

            cat_badge = '<span class="badge badge-green">PDUFA</span>' if row["catalyst_type"] == "PDUFA" else '<span class="badge badge-amber">Phase 3</span>'
            ev_color = "green" if ev >= 25 else "amber"

            fd = get_financial_data_full(ticker)
            prezzo = fd.get("prezzo", 0)
            change_pct = fd.get("change_pct", 0)
            change_color = "green" if change_pct >= 0 else "red"
            change_str = f'<span class="price-change {change_color}">{change_pct:+.2f}%</span>'

            entry = row.get("entry_price")
            pnl_html = ""
            if entry and prezzo:
                pnl = (prezzo - entry) / entry * 100
                pnl_html = f'<span style="font-size:13px;font-weight:600;color:{"#1D9E75" if pnl >= 0 else "#D85A30"}">P&L: {pnl:+.1f}%</span>'

            stop = row.get("stop_price", 0)
            target1 = row.get("target_parziale", 0)
            target2 = row.get("target_finale", 0)
            stop_pct = ((stop - prezzo) / prezzo * 100) if stop and prezzo else 0
            t1_pct = ((target1 - prezzo) / prezzo * 100) if target1 and prezzo else 0
            t2_pct = ((target2 - prezzo) / prezzo * 100) if target2 and prezzo else 0

            levels_html = f"""<div class="levels-row">
              <div class="level-box"><div class="level-label">Stop Loss</div><div class="level-value stop">${stop:.2f}</div><div class="level-pct">{stop_pct:.1f}%</div></div>
              <div class="level-box"><div class="level-label">Target 1 (meta)</div><div class="level-value target">${target1:.2f}</div><div class="level-pct">+{t1_pct:.1f}%</div></div>
              <div class="level-box"><div class="level-label">Target 2 (resto)</div><div class="level-value target">${target2:.2f}</div><div class="level-pct">+{t2_pct:.1f}%</div></div>
              <div class="level-box"><div class="level-label">Entry Price</div><div class="level-value">${entry:.2f}</div><div class="level-pct">{pnl_html}</div></div>
            </div>""" if entry else ""

            try:
                segnali = json.loads(row["segnali_positivi"] or "[]")
                rischi = json.loads(row["rischi"] or "[]")
            except Exception:
                segnali = []
                rischi = []

            tags_html = "".join([f'<span class="tag tag-pos">checkmark {s}</span>' for s in segnali])
            tags_html += "".join([f'<span class="tag tag-neg">warning {r}</span>' for r in rischi])

            recent_updates = get_recent_updates(catalyst_id, days=7)
            log_html = ""
            if recent_updates:
                for upd in recent_updates[:5]:
                    dot_color = "#1D9E75" if upd["azione_suggerita"] == "ENTRA ORA" else "#D85A30" if upd["azione_suggerita"] == "ESCI" else "#EF9F27" if upd["azione_suggerita"] == "RIVALUTA" else "#aeaeb2"
                    log_html += f'<div class="log-item"><div class="log-dot" style="background:{dot_color}"></div><div><div class="log-text">{upd["descrizione"]}</div><div class="log-date">{upd["update_date"]} · {upd["azione_suggerita"]}</div></div></div>'
            else:
                log_html = '<div style="font-size:13px;color:#8e8e93;padding:8px 0">Nessun aggiornamento recente.</div>'

            upd_oggi = updates_map.get(catalyst_id)
            alert_oggi_html = ""
            if upd_oggi:
                alert_items.append(f"{ticker}: {upd_oggi['descrizione']} -> {upd_oggi['azione_suggerita']}")
                alert_oggi_html = f'<div style="background:#fff8e6;border:1px solid #ffe082;border-radius:8px;padding:10px 12px;margin-top:12px"><span style="font-size:12px;font-weight:700;color:#b45309">AGGIORNAMENTO OGGI:</span><span style="font-size:13px;color:#78350f;margin-left:6px">{upd_oggi["descrizione"]}</span><span style="font-size:12px;font-weight:700;color:#b45309;margin-left:8px">-> {upd_oggi["azione_suggerita"]}</span></div>'

            fda_html = ""
            if row.get("fda_designations"):
                for d in row["fda_designations"].split(","):
                    d = d.strip()
                    if d:
                        fda_html += f'<span class="badge badge-green" style="margin-right:4px">{d.title()}</span>'

            cat_date_str = row.get("catalyst_date") or "Da confermare"
            reliability = row.get("date_reliability") or ""
            high_52 = fd.get("high_52", 0)
            dist_high = ((high_52 - prezzo) / high_52 * 100) if high_52 and prezzo else 0

            opportunita_html += f"""<div class="card">
              <div class="card-header">
                <div class="card-header-left">
                  <div class="ticker">{ticker}</div>
                  <div class="company-name">{row['name'] or ticker}</div>
                  <div class="drug-info">{row['drug_name'] or 'Farmaco principale'} · {row['indication'] or 'Indicazione'}</div>
                </div>
                <div class="card-header-right">{cat_badge}{timing_badge}<div class="ev-value {ev_color}">EV +{ev:.1f}%</div></div>
              </div>
              <div class="card-body">
                <div class="card-section">
                  <div class="card-section-title">Prezzo e livelli</div>
                  <div class="price-block"><div class="price-big">${prezzo:.2f}</div>{change_str}</div>
                  <div class="price-meta">52wk: ${fd.get('low_52',0):.2f} — ${high_52:.2f} · -{dist_high:.1f}% dal picco</div>
                  {levels_html}
                </div>
                <hr class="divider">
                <div class="card-section">
                  <div class="card-section-title">Dati compagnia</div>
                  <div class="fields-grid">
                    <div class="field"><div class="field-label">Market Cap</div><div class="field-value">{format_number(fd.get('market_cap', row.get('market_cap', 0)))}</div></div>
                    <div class="field"><div class="field-label">Cash</div><div class="field-value green">{format_number(fd.get('cash', row.get('cash', 0)))}</div></div>
                    <div class="field"><div class="field-label">Float</div><div class="field-value">{format_shares(fd.get('float_shares', row.get('float_shares', 0)))}</div></div>
                    <div class="field"><div class="field-label">Short Interest</div><div class="field-value amber">{(fd.get('short_percent', row.get('short_percent_float', 0)) or 0)*100:.1f}%</div></div>
                  </div>
                </div>
                <hr class="divider">
                <div class="card-section">
                  <div class="card-section-title">Catalista e status regolatorio</div>
                  <div class="fields-grid-3">
                    <div class="field"><div class="field-label">Tipo</div><div class="field-value">{row['catalyst_type'] or 'N/D'}</div></div>
                    <div class="field"><div class="field-label">Data</div><div class="field-value">{cat_date_str}</div></div>
                    <div class="field"><div class="field-label">Affidabilita</div><div class="field-value {'green' if reliability == 'CERTA' else 'amber'}">{reliability or 'N/D'}</div></div>
                  </div>
                  {f'<div style="margin-top:10px">{fda_html}</div>' if fda_html else ''}
                </div>
                <hr class="divider">
                <div class="card-section">
                  <div class="card-section-title">Score</div>
                  <div class="score-section">
                    <div class="score-row"><span class="score-label">Scientifico</span><div class="score-bar-bg"><div class="score-bar-fill" style="width:{score_sci}%;background:#1D9E75"></div></div><span class="score-val" style="color:#1D9E75">{score_sci}</span></div>
                    <div class="score-row"><span class="score-label">Movimento</span><div class="score-bar-bg"><div class="score-bar-fill" style="width:{score_mov}%;background:#378ADD"></div></div><span class="score-val" style="color:#378ADD">{score_mov}</span></div>
                    <div class="score-row"><span class="score-label">EV stimato</span><div class="score-bar-bg"><div class="score-bar-fill" style="width:{min(ev*1.5,100):.0f}%;background:#EF9F27"></div></div><span class="score-val" style="color:#EF9F27">+{ev:.0f}%</span></div>
                  </div>
                </div>
                <hr class="divider">
                <div class="card-section">
                  <div class="card-section-title">Segnali e rischi</div>
                  <div class="tags">{tags_html}</div>
                </div>
                <hr class="divider">
                <div class="card-section">
                  <div class="card-section-title">Log aggiornamenti (ultimi 7 giorni)</div>
                  {log_html}
                </div>
                {alert_oggi_html}
              </div>
            </div>"""

    alert_section = ""
    if alert_items:
        items_html = "".join([f'<div class="alert-item">{item}</div>' for item in alert_items])
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
        opportunita_section=f'<div class="section"><div class="section-title">Opportunita attive</div>{opportunita_html}</div>' if opportunita_html else ""
    )

    output_dir = "web"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "index.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Report generato: {output_path}")
    return output_path


if __name__ == "__main__":
    genera_report()
