"""
build_site.py — inmo.heuristika.pro
Lee datos.json (generado por indices.py) y escribe index.html: un sitio
estático y autocontenido, con la marca Heuristika, pensado para equipos
comerciales inmobiliarios (indicadores del día, calculadora de dividendo
hipotecario, titulares y un mini-diagnóstico comercial que enlaza de
vuelta a heuristika.pro).

Uso local:
    python3 indices.py
    python3 build_site.py
    open index.html
"""

import json
from datetime import datetime

with open("datos.json", "r", encoding="utf-8") as f:
    DATA = json.load(f)


def fmt(valor, unidad, key=None):
    if unidad == "Porcentaje":
        return f"{valor:.2f}%"
    if unidad == "Dólar":
        return f"US$ {valor:,.2f}".replace(",", ".")
    if key == "uf":
        return f"${valor:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    return f"${valor:,.0f}".replace(",", ".")


def fecha_legible(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%d-%m-%Y")
    except Exception:
        return iso or "—"


def fecha_hora_legible(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%d-%m-%Y a las %H:%M")
    except Exception:
        return iso or "—"


macro = DATA.get("macro", {})
tasa_hip = DATA.get("tasa_hipotecaria")
titulares = DATA.get("titulares", [])
dato_remarcable = DATA.get("dato_remarcable")

# ---------------------------------------------------------------------------
# KPIs del resumen: UF, dólar, TPM, tasa hipotecaria promedio
# ---------------------------------------------------------------------------

KPI_ORDEN = [("uf", "UF"), ("dolar", "Dólar obs."), ("tpm", "TPM")]

kpi_cards = ""
for key, label in KPI_ORDEN:
    d = macro.get(key)
    if not d:
        continue
    kpi_cards += f"""
    <div class="kpi">
      <div class="kpi-label">{label}</div>
      <div class="kpi-val">{fmt(d['valor'], d['unidad'], key)}</div>
      <div class="kpi-fecha">{fecha_legible(d['fecha'])}</div>
    </div>"""

if tasa_hip:
    kpi_cards += f"""
    <div class="kpi">
      <div class="kpi-label">Tasa hipotecaria prom.</div>
      <div class="kpi-val">{fmt(tasa_hip['valor'], tasa_hip['unidad'])}</div>
      <div class="kpi-fecha">{fecha_legible(tasa_hip['fecha'])}</div>
    </div>"""
else:
    kpi_cards += """
    <div class="kpi kpi-empty">
      <div class="kpi-label">Tasa hipotecaria prom.</div>
      <div class="kpi-val">—</div>
      <div class="kpi-fecha">Sin datos (revisa CMF_API_KEY)</div>
    </div>"""

# ---------------------------------------------------------------------------
# Dato remarcable
# ---------------------------------------------------------------------------

if dato_remarcable:
    signo = "+" if dato_remarcable["cambio_pct"] >= 0 else ""
    dato_remarcable_html = f"""
    <div class="highlight-box">
      <div class="highlight-tag">Lo más inusual hoy</div>
      <div class="highlight-text">
        El movimiento más fuera de lo común fue en <strong>{dato_remarcable['nombre']}</strong>,
        con un cambio de <strong>{signo}{dato_remarcable['cambio_pct']}%</strong> respecto a su
        punto anterior ({fecha_legible(dato_remarcable['fecha'])}).
      </div>
    </div>"""
else:
    dato_remarcable_html = """
    <div class="highlight-box highlight-empty">
      <div class="highlight-tag">Lo más inusual hoy</div>
      <div class="highlight-text">
        Todavía estamos construyendo el historial de este tablero — vuelve en unos días
        para ver qué indicador se mueve más de lo esperado.
      </div>
    </div>"""

# ---------------------------------------------------------------------------
# Titulares
# ---------------------------------------------------------------------------

if titulares:
    titulares_html = ""
    for t in titulares:
        titulares_html += f"""
        <li class="titular">
          <a href="{t['link']}" target="_blank" rel="noopener">{t['titulo']}</a>
          <span class="titular-fuente">{t['fuente']}</span>
        </li>"""
else:
    titulares_html = '<li class="titular-empty">Sin titulares disponibles por ahora.</li>'

# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

cargado_en = fecha_hora_legible(DATA.get("generado", ""))

HTML = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tablero Inmobiliario · Heuristika</title>
<style>
  :root{{
    --bg:#0b0d10; --card:#14171b; --line:#242830; --text:#eef0f2;
    --muted:#8a8f98; --orange:#e2792f;
  }}
  *{{box-sizing:border-box;}}
  body{{
    margin:0; background:var(--bg); color:var(--text);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    padding:32px 24px 60px;
  }}
  .wrap{{max-width:1000px; margin:0 auto;}}

  .header{{position:relative; display:flex; align-items:center; justify-content:center; margin-bottom:6px;}}
  .header-title{{text-align:center;}}
  .page-title{{font-size:24px; font-weight:700; letter-spacing:.01em;}}
  .page-title .flag{{font-size:20px;}}
  .header-logo{{position:absolute; right:0; top:0; display:flex; flex-direction:column; align-items:flex-end; gap:2px;}}
  .brand-mark{{flex-shrink:0;}}
  .brand-name{{font-size:11px; font-weight:600; letter-spacing:.08em; color:var(--muted);}}
  .brand-name .k{{color:var(--orange);}}
  .brand-tagline{{
    font-size:11px; color:var(--muted); letter-spacing:.12em; text-transform:uppercase;
    display:flex; align-items:center; justify-content:center; gap:10px; margin:14px 0 6px;
  }}
  .brand-tagline .dash{{display:inline-block; width:22px; height:1px; background:var(--orange);}}
  .update-note{{font-size:11px; color:var(--muted); line-height:1.6; margin-bottom:28px; text-align:center;}}

  h1{{font-size:14px; font-weight:600; color:var(--muted); text-transform:uppercase;
     letter-spacing:.08em; margin:0 0 4px;}}
  .section-sub{{font-size:12px; color:var(--muted); margin:0 0 18px;}}
  .section{{padding:32px 0; border-top:1px solid var(--line);}}
  .section:first-of-type{{border-top:none; padding-top:0;}}

  .subhead-box{{
    border:1px solid var(--orange); border-radius:8px; padding:8px 14px; margin:0 0 16px;
    font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:var(--orange);
    display:inline-block;
    background:linear-gradient(135deg, rgba(226,121,47,.10), rgba(226,121,47,0));
  }}

  .kpis{{display:flex; gap:12px; flex-wrap:wrap;}}
  .kpi{{
    flex:1 1 150px; background:var(--card); border:1px solid var(--line);
    border-radius:10px; padding:16px 18px;
  }}
  .kpi-empty{{opacity:.6;}}
  .kpi-label{{font-size:11px; color:var(--muted); margin-bottom:6px;}}
  .kpi-val{{font-size:20px; font-weight:700; font-variant-numeric:tabular-nums;}}
  .kpi-fecha{{font-size:10px; color:var(--muted); margin-top:6px;}}

  .highlight-box{{
    border:1px solid var(--orange); border-radius:10px; padding:18px 22px; margin-top:20px;
    background:linear-gradient(135deg, rgba(226,121,47,.10), rgba(226,121,47,0));
  }}
  .highlight-empty{{border-color:var(--line); background:none;}}
  .highlight-tag{{font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:var(--orange); margin-bottom:8px; font-weight:700;}}
  .highlight-text{{font-size:13px; color:var(--text); line-height:1.6;}}

  .calc-box{{background:var(--card); border:1px solid var(--line); border-radius:10px; padding:22px;}}
  .calc-grid{{display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px; margin-bottom:18px;}}
  .calc-field label{{display:block; font-size:11px; color:var(--muted); margin-bottom:6px;}}
  .calc-field input{{
    width:100%; background:var(--bg); border:1px solid var(--line); border-radius:6px;
    color:var(--text); padding:8px 10px; font-size:14px; font-family:inherit;
  }}
  .calc-btn{{
    background:var(--orange); color:#0b0d10; border:none; border-radius:20px;
    padding:10px 22px; font-size:13px; font-weight:700; cursor:pointer;
  }}
  .calc-btn:hover{{opacity:.9;}}
  .calc-resultado{{margin-top:18px; display:none;}}
  .calc-resultado.show{{display:block;}}
  .calc-resultado-val{{font-size:26px; font-weight:700; color:var(--orange);}}
  .calc-resultado-sub{{font-size:12px; color:var(--muted); margin-top:6px;}}
  .calc-nota{{font-size:11px; color:var(--muted); margin-top:14px; line-height:1.6;}}

  .titulares-list{{list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:10px;}}
  .titular{{background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px 16px; display:flex; justify-content:space-between; align-items:center; gap:14px; flex-wrap:wrap;}}
  .titular a{{color:var(--text); text-decoration:none; font-size:13px; flex:1 1 auto;}}
  .titular a:hover{{color:var(--orange);}}
  .titular-fuente{{font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; white-space:nowrap;}}
  .titular-empty{{color:var(--muted); font-size:12px; font-style:italic;}}

  .diag-box{{background:var(--card); border:1px solid var(--line); border-radius:10px; padding:22px;}}
  .diag-q{{margin-bottom:16px;}}
  .diag-q-text{{font-size:13px; margin-bottom:8px;}}
  .diag-opts{{display:flex; gap:8px; flex-wrap:wrap;}}
  .diag-opt{{
    background:var(--bg); border:1px solid var(--line); border-radius:20px;
    padding:6px 14px; font-size:12px; color:var(--text); cursor:pointer;
  }}
  .diag-opt.selected{{border-color:var(--orange); color:var(--orange); font-weight:600;}}
  .diag-resultado{{margin-top:20px; padding-top:18px; border-top:1px solid var(--line); display:none;}}
  .diag-resultado.show{{display:block;}}
  .diag-nivel{{font-size:18px; font-weight:700; color:var(--orange); margin-bottom:8px;}}
  .diag-texto{{font-size:13px; color:var(--text); line-height:1.6; margin-bottom:16px;}}
  .diag-cta{{
    display:inline-block; background:var(--orange); color:#0b0d10; text-decoration:none;
    border-radius:20px; padding:10px 22px; font-size:13px; font-weight:700;
  }}

  .footer{{margin-top:36px; font-size:11px; color:var(--muted); line-height:1.6;}}
  .footer a{{color:var(--orange); text-decoration:none;}}

  @media (max-width: 480px){{
    body{{padding:20px 14px 44px;}}
    .header{{flex-direction:column; align-items:center; gap:10px;}}
    .header-logo{{position:static; align-items:center;}}
    .page-title{{font-size:19px;}}
    .calc-grid{{grid-template-columns:1fr;}}
  }}
</style>
</head>
<body>
<div class="wrap">

  <div class="header">
    <div class="header-title">
      <div class="page-title">Tablero Inmobiliario <span class="flag">🇨🇱</span></div>
    </div>
    <div class="header-logo">
      <svg class="brand-mark" width="40" height="40" viewBox="0 0 112 120" xmlns="http://www.w3.org/2000/svg">
        <rect x="20" y="8"  width="22" height="40" rx="3" fill="#eef0f2"/>
        <rect x="20" y="72" width="22" height="40" rx="3" fill="#eef0f2"/>
        <rect x="68" y="8"  width="22" height="40" rx="3" fill="#eef0f2"/>
        <path d="M68,72 H90 V112 Q68,112 68,90 Z" fill="#eef0f2"/>
        <rect x="2"  y="48" width="16" height="16" rx="2" fill="#8a8f98"/>
        <rect x="48" y="48" width="16" height="16" rx="2" fill="#e2792f"/>
        <rect x="94" y="48" width="16" height="16" rx="2" fill="#8a8f98"/>
      </svg>
      <div class="brand-name">HEURISTI<span class="k">K</span>A</div>
    </div>
  </div>
  <div class="brand-tagline"><span class="dash"></span>Capacidad Humana Amplificada<span class="dash"></span></div>
  <div class="update-note">La información que estás viendo fue cargada el {cargado_en}.</div>

  <section id="resumen" class="section">
    <h1>Indicadores del día</h1>
    <div class="section-sub">UF, dólar, TPM y tasa hipotecaria promedio, para tener el contexto a mano en cada conversación de venta.</div>
    <div class="kpis">{kpi_cards}</div>
    {dato_remarcable_html}
  </section>

  <section id="calculadora" class="section">
    <div class="subhead-box">Calculadora</div>
    <h1>Dividendo hipotecario</h1>
    <div class="section-sub">Simula el dividendo mensual de un crédito hipotecario con el sistema francés (cuota fija).</div>
    <div class="calc-box">
      <div class="calc-grid">
        <div class="calc-field">
          <label for="calc-monto">Monto a financiar (UF)</label>
          <input type="number" id="calc-monto" placeholder="ej. 3000" min="0" step="1">
        </div>
        <div class="calc-field">
          <label for="calc-tasa">Tasa anual / CAE (%)</label>
          <input type="number" id="calc-tasa" placeholder="ej. 4.8" min="0" step="0.01">
        </div>
        <div class="calc-field">
          <label for="calc-plazo">Plazo (años)</label>
          <input type="number" id="calc-plazo" placeholder="ej. 20" min="1" step="1">
        </div>
      </div>
      <button class="calc-btn" onclick="calcularDividendo()">Calcular dividendo</button>
      <div class="calc-resultado" id="calc-resultado">
        <div class="calc-resultado-val" id="calc-resultado-uf"></div>
        <div class="calc-resultado-sub" id="calc-resultado-clp"></div>
      </div>
      <div class="calc-nota">
        Cálculo referencial con el método francés (cuota fija). No incluye seguros, comisiones
        ni gastos operacionales del crédito — úsalo como estimación conversacional, no como
        oferta formal.
      </div>
    </div>
  </section>

  <section id="titulares" class="section">
    <div class="subhead-box">Prensa</div>
    <h1>Titulares del día</h1>
    <div class="section-sub">Economía, finanzas e inmobiliario — filtrado de Diario Financiero, Cooperativa y BioBioChile.</div>
    <ul class="titulares-list">{titulares_html}
    </ul>
  </section>

  <section id="diagnostico" class="section">
    <div class="subhead-box">Diagnóstico</div>
    <h1>¿Dónde se te está escapando la venta?</h1>
    <div class="section-sub">6 preguntas rápidas sobre el proceso comercial de tu equipo.</div>
    <div class="diag-box" id="diag-box">
      <div class="diag-q" data-peso="2">
        <div class="diag-q-text">1. ¿Tu equipo sigue un proceso de venta estandarizado?</div>
        <div class="diag-opts">
          <span class="diag-opt" data-val="0">Sí, siempre</span>
          <span class="diag-opt" data-val="1">A veces</span>
          <span class="diag-opt" data-val="2">Cada uno vende a su manera</span>
        </div>
      </div>
      <div class="diag-q" data-peso="2">
        <div class="diag-q-text">2. ¿Sabes en qué etapa está cada negocio de tu equipo, hoy mismo?</div>
        <div class="diag-opts">
          <span class="diag-opt" data-val="0">Sí, con datos actualizados</span>
          <span class="diag-opt" data-val="1">Más o menos</span>
          <span class="diag-opt" data-val="2">No, la verdad no</span>
        </div>
      </div>
      <div class="diag-q" data-peso="1.5">
        <div class="diag-q-text">3. ¿Los leads se contactan en menos de una hora?</div>
        <div class="diag-opts">
          <span class="diag-opt" data-val="0">Casi siempre</span>
          <span class="diag-opt" data-val="1">A veces se demoran</span>
          <span class="diag-opt" data-val="2">Se pierden en el camino</span>
        </div>
      </div>
      <div class="diag-q" data-peso="1.5">
        <div class="diag-q-text">4. ¿El desempeño del equipo depende del talento individual más que de un sistema?</div>
        <div class="diag-opts">
          <span class="diag-opt" data-val="0">No, el sistema funciona solo</span>
          <span class="diag-opt" data-val="1">Un poco de ambos</span>
          <span class="diag-opt" data-val="2">Sí, totalmente</span>
        </div>
      </div>
      <div class="diag-q" data-peso="1.5">
        <div class="diag-q-text">5. ¿Hay alguien liderando el área comercial con metodología, a tiempo completo o fraccionado?</div>
        <div class="diag-opts">
          <span class="diag-opt" data-val="0">Sí</span>
          <span class="diag-opt" data-val="1">Parcialmente</span>
          <span class="diag-opt" data-val="2">No</span>
        </div>
      </div>
      <div class="diag-q" data-peso="1.5">
        <div class="diag-q-text">6. ¿Miden resultados con métricas concretas (no solo capacitaciones)?</div>
        <div class="diag-opts">
          <span class="diag-opt" data-val="0">Sí</span>
          <span class="diag-opt" data-val="1">Algunas</span>
          <span class="diag-opt" data-val="2">No</span>
        </div>
      </div>

      <button class="calc-btn" onclick="calcularDiagnostico()">Ver resultado</button>

      <div class="diag-resultado" id="diag-resultado">
        <div class="diag-nivel" id="diag-nivel"></div>
        <div class="diag-texto" id="diag-texto"></div>
        <a class="diag-cta" href="https://www.heuristika.pro/" target="_blank" rel="noopener">Agenda una conversación de 20 min</a>
      </div>
    </div>
  </section>

  <div class="footer">
    Fuentes: <a href="https://mindicador.cl" target="_blank">mindicador.cl</a> (Banco Central de Chile),
    <a href="https://api.cmfchile.cl" target="_blank">CMF Bancos</a>,
    <a href="https://www.df.cl" target="_blank">Diario Financiero</a>,
    <a href="https://www.cooperativa.cl" target="_blank">Cooperativa</a> y
    <a href="https://www.biobiochile.cl" target="_blank">BioBioChile</a>.
    Un desarrollo de <a href="https://www.heuristika.pro" target="_blank">Heuristika</a> — Liderazgo Comercial
    Externo para Inmobiliarias. Información con fines informativos, no constituye asesoría ni
    recomendación financiera.
  </div>

</div>

<script>
function calcularDividendo() {{
  const monto = parseFloat(document.getElementById('calc-monto').value);
  const tasaAnual = parseFloat(document.getElementById('calc-tasa').value);
  const anios = parseFloat(document.getElementById('calc-plazo').value);
  const resultadoBox = document.getElementById('calc-resultado');

  if (!monto || !tasaAnual || !anios || monto <= 0 || anios <= 0) {{
    resultadoBox.classList.remove('show');
    return;
  }}

  const n = anios * 12;
  const iMensual = (tasaAnual / 100) / 12;
  let dividendoUF;
  if (iMensual === 0) {{
    dividendoUF = monto / n;
  }} else {{
    dividendoUF = monto * (iMensual * Math.pow(1 + iMensual, n)) / (Math.pow(1 + iMensual, n) - 1);
  }}

  const ufHoy = {json.dumps(macro.get('uf', {}).get('valor'))};
  document.getElementById('calc-resultado-uf').textContent =
    'UF ' + dividendoUF.toFixed(2) + ' / mes';

  if (ufHoy) {{
    const clp = dividendoUF * ufHoy;
    document.getElementById('calc-resultado-clp').textContent =
      '≈ $' + Math.round(clp).toLocaleString('es-CL') + ' al valor de la UF de hoy';
  }} else {{
    document.getElementById('calc-resultado-clp').textContent = '';
  }}

  resultadoBox.classList.add('show');
}}

document.querySelectorAll('.diag-q').forEach(function(q) {{
  q.querySelectorAll('.diag-opt').forEach(function(opt) {{
    opt.addEventListener('click', function() {{
      q.querySelectorAll('.diag-opt').forEach(function(o) {{ o.classList.remove('selected'); }});
      opt.classList.add('selected');
    }});
  }});
}});

function calcularDiagnostico() {{
  const preguntas = document.querySelectorAll('.diag-q');
  let total = 0;
  let maxTotal = 0;
  let respondidas = 0;

  preguntas.forEach(function(q) {{
    const peso = parseFloat(q.dataset.peso);
    maxTotal += 2 * peso;
    const sel = q.querySelector('.diag-opt.selected');
    if (sel) {{
      total += parseFloat(sel.dataset.val) * peso;
      respondidas++;
    }}
  }});

  if (respondidas < preguntas.length) {{
    alert('Responde las ' + preguntas.length + ' preguntas para ver tu resultado.');
    return;
  }}

  const pct = total / maxTotal;
  let nivel, texto;
  if (pct >= 0.6) {{
    nivel = 'Fuga de resultados: alta';
    texto = 'Tu equipo probablemente está dejando ventas sobre la mesa por falta de proceso y seguimiento. Vale la pena conversar 20 minutos sobre dónde exactamente se está perdiendo.';
  }} else if (pct >= 0.3) {{
    nivel = 'Fuga de resultados: media';
    texto = 'Hay partes del proceso que funcionan y otras que dependen demasiado del talento individual. Con ajustes puntuales el equipo puede rendir bastante más.';
  }} else {{
    nivel = 'Fuga de resultados: baja';
    texto = 'Tu equipo tiene una base sólida. Igual vale la pena una mirada externa para encontrar el siguiente salto de conversión.';
  }}

  document.getElementById('diag-nivel').textContent = nivel;
  document.getElementById('diag-texto').textContent = texto;
  document.getElementById('diag-resultado').classList.add('show');
}}
</script>

</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(HTML)

print("OK -> index.html")
