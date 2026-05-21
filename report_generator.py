"""
report_generator.py
Generates a professional forensic HTML report from extracted artifacts.
"""

import json
import os
from datetime import datetime
from pathlib import Path


class ReportGenerator:
    def __init__(self, output_dir: str, device_info: dict, results: dict, custody: dict):
        self.output_dir = Path(output_dir)
        self.device_info = device_info
        self.results = results
        self.custody = custody

    def generate(self) -> str:
        report_path = self.output_dir / "forensic_report.html"
        html = self._build_html()
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html)
        return str(report_path)

    # ------------------------------------------------------------------ helpers
    def _count(self, key):
        v = self.results.get(key, [])
        return len(v) if isinstance(v, list) else len(v.get("records", []))

    def _rows(self, key):
        v = self.results.get(key, [])
        return v if isinstance(v, list) else v.get("records", [])

    def _table(self, key, cols):
        rows = self._rows(key)
        if not rows:
            return '<p class="empty">No records found.</p>'
        headers = "".join(f"<th>{c.replace('_',' ').title()}</th>" for c in cols)
        body = ""
        for r in rows[:200]:
            cells = "".join(f"<td>{str(r.get(c,''))[:120]}</td>" for c in cols)
            body += f"<tr>{cells}</tr>"
        return f"""
        <div class="table-wrap">
          <table>
            <thead><tr>{headers}</tr></thead>
            <tbody>{body}</tbody>
          </table>
        </div>"""

    def _gps_points(self):
        """Collect all GPS points from photos and locations."""
        points = []
        for p in self._rows("Photos & EXIF"):
            if p.get("has_gps"):
                points.append({"lat": p["latitude"], "lng": p["longitude"], "label": p.get("filename","Photo"), "type":"photo"})
        for l in self._rows("Location History"):
            points.append({"lat": l["latitude"], "lng": l["longitude"], "label": l.get("type","Location"), "type":"location"})
        return points

    # ------------------------------------------------------------------ HTML
    def _build_html(self):
        gps = json.dumps(self._gps_points())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        d = self.device_info
        c = self.custody

        sms_table      = self._table("SMS / iMessage",   ["contact","direction","service","date","text"])
        calls_table    = self._table("Call Logs",         ["number","direction","type","duration","answered","date"])
        contacts_table = self._table("Contacts",          ["name","organization","phones","emails"])
        safari_table   = self._table("Safari History",    ["title","domain","url","visited"])
        photos_table   = self._table("Photos & EXIF",     ["filename","kind","date","camera","latitude","longitude"])
        apps_table     = self._table("Installed Apps",    ["name","bundle_id","category"])
        loc_table      = self._table("Location History",  ["type","latitude","longitude","date"])

        # Deleted SMS recovery data
        del_data          = self.results.get("Deleted SMS", {})
        del_records       = del_data.get("records", [])
        deleted_count     = len(del_records)
        deleted_technique = del_data.get("technique", "Not run")
        deleted_pages     = del_data.get("pages_scanned", 0)
        deleted_wal       = del_data.get("wal_scanned", 0)

        if del_records:
            hdrs = "".join("<th>" + col + "</th>" for col in ["Status","Date","Contact","Direction","Text","Method"])
            body = ""
            for r in del_records[:200]:
                status  = str(r.get("status",""))
                date    = str(r.get("date",""))
                contact = str(r.get("contact",""))
                direc   = str(r.get("direction",""))
                text    = str(r.get("text",""))[:120]
                method  = str(r.get("method",""))
                tr_style = 'background:rgba(255,107,53,0.06)'
                td_style1 = 'color:#ff6b35;font-size:11px'
                td_style2 = 'font-size:11px;color:var(--muted)'
                body += (
                    '<tr style="' + tr_style + '">'
                    '<td style="' + td_style1 + '">' + status  + "</td>"
                    "<td>" + date    + "</td>"
                    "<td>" + contact + "</td>"
                    "<td>" + direc   + "</td>"
                    "<td>" + text    + "</td>"
                    '<td style="' + td_style2 + '">' + method + "</td>"
                    "</tr>"
                )
            tw = 'table-wrap'
            deleted_table = '<div class="' + tw + '"><table><thead><tr>' + hdrs + '</tr></thead><tbody>' + body + '</tbody></table></div>'
        else:
            ep = 'empty'
            deleted_table = '<p class="' + ep + '">No deleted fragments recovered. Normal if iOS has already overwritten freed pages.</p>'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>iOS Forensic Report — {c.get('case_number','')}</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap" rel="stylesheet"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"/>
<style>
  :root {{
    --bg: #0a0e14;
    --surface: #111820;
    --surface2: #1a2332;
    --border: #1e3a5f;
    --accent: #00d4ff;
    --accent2: #ff6b35;
    --green: #39ff14;
    --red: #ff3366;
    --text: #c8d8e8;
    --muted: #5a7a9a;
    --font-mono: 'IBM Plex Mono', monospace;
    --font-sans: 'IBM Plex Sans', sans-serif;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:var(--bg); color:var(--text); font-family:var(--font-sans); font-size:14px; line-height:1.6; }}

  /* HEADER */
  header {{ background:linear-gradient(135deg,#0a1628 0%,#0d2044 50%,#0a1628 100%);
    border-bottom:2px solid var(--accent); padding:40px; position:relative; overflow:hidden; }}
  header::before {{ content:''; position:absolute; top:0;left:0;right:0;bottom:0;
    background:repeating-linear-gradient(0deg,transparent,transparent 40px,rgba(0,212,255,0.03) 40px,rgba(0,212,255,0.03) 41px),
               repeating-linear-gradient(90deg,transparent,transparent 40px,rgba(0,212,255,0.03) 40px,rgba(0,212,255,0.03) 41px);
    pointer-events:none; }}
  .header-top {{ display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:20px; }}
  .brand {{ display:flex; align-items:center; gap:16px; }}
  .brand-icon {{ width:56px; height:56px; background:var(--accent); border-radius:12px; display:flex;
    align-items:center; justify-content:center; font-size:28px; }}
  .brand-text h1 {{ font-size:22px; font-weight:700; color:#fff; letter-spacing:1px; }}
  .brand-text p {{ color:var(--accent); font-family:var(--font-mono); font-size:12px; letter-spacing:2px; }}
  .case-badge {{ background:rgba(0,212,255,0.1); border:1px solid var(--accent); border-radius:8px;
    padding:12px 20px; text-align:right; }}
  .case-badge .case-num {{ font-family:var(--font-mono); font-size:20px; color:var(--accent); font-weight:600; }}
  .case-badge .case-date {{ font-size:11px; color:var(--muted); margin-top:4px; }}

  .device-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-top:28px; }}
  .device-item {{ background:rgba(0,0,0,0.3); border:1px solid var(--border); border-radius:8px; padding:12px 16px; }}
  .device-item label {{ font-size:10px; color:var(--muted); letter-spacing:1.5px; text-transform:uppercase; display:block; }}
  .device-item span {{ font-family:var(--font-mono); font-size:13px; color:#fff; display:block; margin-top:4px; }}

  /* NAV */
  nav {{ background:var(--surface); border-bottom:1px solid var(--border); padding:0 40px;
    display:flex; gap:0; overflow-x:auto; position:sticky; top:0; z-index:100; }}
  nav a {{ color:var(--muted); text-decoration:none; padding:14px 18px; font-size:12px;
    letter-spacing:1px; text-transform:uppercase; border-bottom:2px solid transparent;
    white-space:nowrap; transition:all .2s; }}
  nav a:hover, nav a.active {{ color:var(--accent); border-bottom-color:var(--accent); }}

  /* MAIN */
  main {{ max-width:1400px; margin:0 auto; padding:32px 40px; }}

  /* STAT CARDS */
  .stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:16px; margin-bottom:40px; }}
  .stat {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:20px;
    text-align:center; transition:border-color .2s; }}
  .stat:hover {{ border-color:var(--accent); }}
  .stat .num {{ font-family:var(--font-mono); font-size:32px; font-weight:600; color:var(--accent); }}
  .stat .lbl {{ font-size:11px; color:var(--muted); margin-top:6px; text-transform:uppercase; letter-spacing:1px; }}

  /* SECTIONS */
  .section {{ margin-bottom:48px; }}
  .section-header {{ display:flex; align-items:center; gap:12px; margin-bottom:20px;
    border-bottom:1px solid var(--border); padding-bottom:12px; }}
  .section-icon {{ font-size:20px; }}
  .section-title {{ font-size:18px; font-weight:600; color:#fff; }}
  .section-count {{ background:var(--accent); color:#000; font-family:var(--font-mono);
    font-size:11px; font-weight:600; padding:3px 10px; border-radius:20px; margin-left:auto; }}

  /* CHAIN OF CUSTODY */
  .custody-box {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:24px; }}
  .custody-row {{ display:flex; gap:16px; margin-bottom:12px; flex-wrap:wrap; }}
  .custody-field {{ flex:1; min-width:200px; }}
  .custody-field label {{ font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:1.5px; }}
  .custody-field .val {{ font-family:var(--font-mono); font-size:12px; color:var(--text); margin-top:4px; word-break:break-all; }}
  .integrity-ok {{ color:var(--green); font-weight:600; }}
  .integrity-fail {{ color:var(--red); font-weight:600; }}

  /* TABLES */
  .table-wrap {{ overflow-x:auto; border-radius:8px; border:1px solid var(--border); }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  thead {{ background:var(--surface2); }}
  th {{ padding:10px 14px; text-align:left; font-size:10px; text-transform:uppercase;
    letter-spacing:1.5px; color:var(--muted); font-weight:600; border-bottom:1px solid var(--border); }}
  td {{ padding:9px 14px; border-bottom:1px solid rgba(30,58,95,0.5); color:var(--text); }}
  tr:last-child td {{ border-bottom:none; }}
  tr:hover td {{ background:rgba(0,212,255,0.04); }}

  /* MAP */
  #map {{ height:480px; border-radius:10px; border:1px solid var(--border); }}

  .empty {{ color:var(--muted); font-style:italic; padding:20px; text-align:center; }}

  /* FOOTER */
  footer {{ text-align:center; padding:32px; color:var(--muted); font-size:12px;
    border-top:1px solid var(--border); font-family:var(--font-mono); }}
</style>
</head>
<body>

<header>
  <div class="header-top">
    <div class="brand">
      <div class="brand-icon">🔍</div>
      <div class="brand-text">
        <h1>iOS ARTIFACT ANALYZER</h1>
        <p>DIGITAL FORENSICS EXAMINATION REPORT</p>
      </div>
    </div>
    <div class="case-badge">
      <div class="case-num">{c.get('case_number','')}</div>
      <div class="case-date">Generated: {now}</div>
    </div>
  </div>
  <div class="device-grid">
    <div class="device-item"><label>Device</label><span>{d.get('device_name','Unknown')}</span></div>
    <div class="device-item"><label>iOS Version</label><span>{d.get('ios_version','Unknown')}</span></div>
    <div class="device-item"><label>Serial Number</label><span>{d.get('serial_number','Unknown')}</span></div>
    <div class="device-item"><label>IMEI</label><span>{d.get('imei','Unknown')}</span></div>
    <div class="device-item"><label>Phone Number</label><span>{d.get('phone_number','Unknown')}</span></div>
    <div class="device-item"><label>Backup Date</label><span>{d.get('backup_date','Unknown')}</span></div>
  </div>
</header>

<nav>
  <a href="#overview" class="active">Overview</a>
  <a href="#custody">Chain of Custody</a>
  <a href="#sms">SMS</a>
  <a href="#deleted-sms" style="color:#ff6b35">🗑 Deleted SMS</a>
  <a href="#calls">Calls</a>
  <a href="#contacts">Contacts</a>
  <a href="#safari">Safari</a>
  <a href="#photos">Photos</a>
  <a href="#apps">Apps</a>
  <a href="#locations">Locations</a>
  <a href="#map">GPS Map</a>
</nav>

<main>

  <!-- OVERVIEW -->
  <div id="overview" class="section">
    <div class="section-header">
      <span class="section-icon">📊</span>
      <span class="section-title">Artifact Summary</span>
    </div>
    <div class="stats">
      <div class="stat"><div class="num">{self._count('SMS / iMessage')}</div><div class="lbl">SMS / iMessage</div></div>
      <div class="stat"><div class="num">{len(self.results.get('Deleted SMS',{}).get('records',[]))}</div><div class="lbl" style="color:var(--accent2)">Deleted SMS Recovered</div></div>
      <div class="stat"><div class="num">{self._count('Call Logs')}</div><div class="lbl">Call Records</div></div>
      <div class="stat"><div class="num">{self._count('Contacts')}</div><div class="lbl">Contacts</div></div>
      <div class="stat"><div class="num">{self._count('Safari History')}</div><div class="lbl">Browser History</div></div>
      <div class="stat"><div class="num">{self._count('Photos & EXIF')}</div><div class="lbl">Photo Records</div></div>
      <div class="stat"><div class="num">{self._count('Installed Apps')}</div><div class="lbl">Apps Installed</div></div>
      <div class="stat"><div class="num">{self._count('Location History')}</div><div class="lbl">Location Points</div></div>
    </div>
  </div>

  <!-- CHAIN OF CUSTODY -->
  <div id="custody" class="section">
    <div class="section-header">
      <span class="section-icon">🔐</span>
      <span class="section-title">Chain of Custody</span>
    </div>
    <div class="custody-box">
      <div class="custody-row">
        <div class="custody-field"><label>Case Number</label><div class="val">{c.get('case_number','')}</div></div>
        <div class="custody-field"><label>Examiner</label><div class="val">{c.get('examiner','')}</div></div>
        <div class="custody-field"><label>Analysis Start</label><div class="val">{c.get('start_time','')}</div></div>
      </div>
      <div class="custody-row">
        <div class="custody-field"><label>Pre-Analysis SHA-256</label><div class="val">{c.get('pre_hash','')}</div></div>
        <div class="custody-field"><label>Post-Analysis SHA-256</label><div class="val">{c.get('post_hash','')}</div></div>
      </div>
      <div class="custody-row">
        <div class="custody-field"><label>Integrity Status</label>
          <div class="val {'integrity-ok' if 'VERIFIED' in c.get('integrity','') else 'integrity-fail'}">{c.get('integrity','')}</div>
        </div>
      </div>
    </div>
  </div>

  <!-- SMS -->
  <div id="sms" class="section">
    <div class="section-header">
      <span class="section-icon">💬</span>
      <span class="section-title">SMS / iMessage</span>
      <span class="section-count">{self._count('SMS / iMessage')} records</span>
    </div>
    {sms_table}
  </div>

  <!-- DELETED SMS -->
  <div id="deleted-sms" class="section">
    <div class="section-header">
      <span class="section-icon">🗑</span>
      <span class="section-title" style="color:var(--accent2)">Deleted SMS Recovery</span>
      <span class="section-count" style="background:var(--accent2)">{deleted_count} fragments</span>
    </div>
    <div style="background:rgba(255,107,53,0.08);border:1px solid rgba(255,107,53,0.3);border-radius:8px;padding:16px;margin-bottom:20px;font-size:13px;line-height:1.7;">
      <strong style="color:var(--accent2)">Forensic Technique Used:</strong> {deleted_technique}<br>
      <strong style="color:var(--accent2)">Pages Scanned:</strong> {deleted_pages} freelist pages &nbsp;|&nbsp;
      <strong style="color:var(--accent2)">WAL Frames:</strong> {deleted_wal}<br>
      <span style="color:var(--muted);font-size:12px;">
        ⚠ Recovered fragments may be partial or incomplete. Text is carved from SQLite unallocated space —
        timestamp and contact info may not always be recoverable. These are forensic artefacts, not guaranteed complete messages.
      </span>
    </div>
    {deleted_table}
  </div>

  <!-- CALLS -->
  <div id="calls" class="section">
    <div class="section-header">
      <span class="section-icon">📞</span>
      <span class="section-title">Call Logs</span>
      <span class="section-count">{self._count('Call Logs')} records</span>
    </div>
    {calls_table}
  </div>

  <!-- CONTACTS -->
  <div id="contacts" class="section">
    <div class="section-header">
      <span class="section-icon">👤</span>
      <span class="section-title">Contacts</span>
      <span class="section-count">{self._count('Contacts')} records</span>
    </div>
    {contacts_table}
  </div>

  <!-- SAFARI -->
  <div id="safari" class="section">
    <div class="section-header">
      <span class="section-icon">🌐</span>
      <span class="section-title">Safari Browsing History</span>
      <span class="section-count">{self._count('Safari History')} records</span>
    </div>
    {safari_table}
  </div>

  <!-- PHOTOS -->
  <div id="photos" class="section">
    <div class="section-header">
      <span class="section-icon">📸</span>
      <span class="section-title">Photos & EXIF Metadata</span>
      <span class="section-count">{self._count('Photos & EXIF')} records</span>
    </div>
    {photos_table}
  </div>

  <!-- APPS -->
  <div id="apps" class="section">
    <div class="section-header">
      <span class="section-icon">📱</span>
      <span class="section-title">Installed Applications</span>
      <span class="section-count">{self._count('Installed Apps')} apps</span>
    </div>
    {apps_table}
  </div>

  <!-- LOCATIONS -->
  <div id="locations" class="section">
    <div class="section-header">
      <span class="section-icon">📍</span>
      <span class="section-title">Location History</span>
      <span class="section-count">{self._count('Location History')} points</span>
    </div>
    {loc_table}
  </div>

  <!-- MAP -->
  <div id="map-section" class="section">
    <div class="section-header">
      <span class="section-icon">🗺️</span>
      <span class="section-title">GPS Map</span>
      <span class="section-count">All geo-tagged artifacts</span>
    </div>
    <div id="map"></div>
  </div>

</main>

<footer>
  iOS Artifact Analyzer v1.0 &nbsp;|&nbsp; {c.get('case_number','')} &nbsp;|&nbsp;
  Report generated {now} &nbsp;|&nbsp; FOR ACADEMIC / AUTHORIZED USE ONLY
</footer>

<script>
// Map
const points = {gps};
const map = L.map('map', {{
  center: points.length ? [points[0].lat, points[0].lng] : [0,0],
  zoom: points.length ? 10 : 2
}});
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  attribution: '© OpenStreetMap contributors'
}}).addTo(map);

const photoIcon = L.divIcon({{className:'', html:'<div style="font-size:18px">📸</div>', iconAnchor:[9,9]}});
const locIcon = L.divIcon({{className:'', html:'<div style="font-size:18px">📍</div>', iconAnchor:[9,9]}});

points.forEach(p => {{
  L.marker([p.lat, p.lng], {{icon: p.type==='photo' ? photoIcon : locIcon}})
   .addTo(map)
   .bindPopup(`<b>${{p.label}}</b><br>${{p.lat}}, ${{p.lng}}`);
}});

// Nav active state
const sections = document.querySelectorAll('[id]');
const navLinks = document.querySelectorAll('nav a');
window.addEventListener('scroll', () => {{
  let current = '';
  sections.forEach(s => {{ if (window.scrollY >= s.offsetTop - 80) current = s.id; }});
  navLinks.forEach(a => {{
    a.classList.remove('active');
    if (a.getAttribute('href') === '#' + current) a.classList.add('active');
  }});
}});
</script>
</body>
</html>"""
