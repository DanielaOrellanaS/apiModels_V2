"""
api.py — servidor que responde a MetaTrader (NEO_MINIMAL_V1.mq4).

Contrato de request (GET /predict):
    symbol, fecha, c5, ema550, ema5200, macdLine5, signalLine5,
    adx5, diPlus5, diMinus5, r5, r15, m5, s5, m15, s15, atr5

Contrato de respuesta (JSON, 4 campos, nada más):
    {"valor_profit": float, "RESULTADO": "BUY"|"SELL"|"NADA",
     "tp": float, "sl": float}

    tp/sl vienen en unidades de precio (el EA los usa directo, ya no
    hardcodea TakeProfit/StopLoss por símbolo). Se sacan de la versión
    activa en registry.json — si el modelo cambia de TP/SL óptimo, el
    EA lo recibe solo, sin tocar el .mq4.

No hay estado entre requests de /predict. Cada request se resuelve solo
con lo que llega en esa foto + el modelo cargado.

--------------------------------------------------------------------
REGISTRO DE OPERACIONES CERRADAS (para el reporte de winrate en vivo)
--------------------------------------------------------------------
Esto SÍ tiene estado, a propósito: cada vez que NEO_MINIMAL_V1 cierra una
operación, llama a GET /registrar_cierre con el resultado real. Se guarda
en datos/operaciones/cierres.jsonl (un JSON por línea, se agrega, nunca se
sobreescribe). /reporte_winrate.html lee ese archivo cada vez que se abre
—en el navegador, sin guardar nada en memoria— así que siempre muestra el
estado real más reciente, sin exportar nada a mano desde MT4.
"""
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import joblib
import logging

from core import construir_features_fila, FEATURE_LIST
from registry import Registry

logging.basicConfig(level=logging.INFO, format='%(name)s:%(message)s')
logger = logging.getLogger('api')

app = FastAPI(title="ApiModels_v2", version="1.0.0")

_registry = Registry()
_modelos_cargados = {}  # symbol -> (dict con model, scaler, umbral, tp, sl, version_id)

CIERRES_PATH = Path("datos/operaciones/cierres.jsonl")

# Desde cuando cuentan los datos en la pestaña "Diario". Todo lo anterior se
# hizo con los modelos v1 y con tres bugs activos (features sobre vela sin
# cerrar, probabilidades infladas por class_weight, y re-entrada instantanea
# al cerrar una orden), asi que no es comparable. Para ver todo el historial:
# /reporte_winrate.html?diario_desde=2000-01-01
DIARIO_DESDE = "2026-09-04"   # activacion de los modelos v3
MESES = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
         7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}
PREDICCIONES_PATH = Path("datos/operaciones/predicciones.jsonl")

# Referencia de validar.py -- PF/WR/n confirmados contra miles de operaciones
# simuladas y contra el azar (p<0.05 en todos). Si un simbolo/lado no
# aparece aca, es porque no paso la validacion -- no se muestra referencia.
REFERENCIA = {
    ("NAS100", "BUY"):  dict(pct=52.5, pf=1.91, n=1879, p="0,0000"),
    ("NAS100", "SELL"): dict(pct=51.7, pf=1.79, n=2157, p="0,0000"),
    ("GER40",  "BUY"):  dict(pct=52.7, pf=2.00, n=2010, p="0,0000"),
    ("GER40",  "SELL"): dict(pct=42.0, pf=2.13, n=1706, p="0,0000"),
    ("US30",   "SELL"): dict(pct=39.6, pf=1.99, n=2007, p="0,0000"),
    ("BTCUSD", "BUY"):  dict(pct=52.9, pf=1.95, n=1476, p="0,0000"),
    ("BTCUSD", "SELL"): dict(pct=42.3, pf=1.51, n=1690, p="0,0000"),
}


def _cargar_modelo(symbol):
    """Carga (con cache) el modelo activo de `symbol` según registry.json.
    Se re-lee el registry.json DEL DISCO en cada llamada (antes el comentario
    lo decía pero el código no lo hacía -- _registry vivía en memoria desde
    el arranque del servidor y nunca se refrescaba) -- así, si corrés
    validar.py de nuevo o activás una versión distinta, el servidor lo toma
    en la siguiente consulta, sin reiniciar. El modelo en sí (el .pkl) sí se
    cachea por version_id, para no releer ese archivo pesado en cada request."""
    _registry._cargar()
    activo = _registry.activo(symbol)
    if activo is None:
        return None

    version_id = activo["version_id"]
    cache = _modelos_cargados.get(symbol)
    if cache is None or cache["version_id"] != version_id:
        ruta = Path(activo["archivo_modelo"])
        if not ruta.exists():
            logger.error(f"{symbol}: registry apunta a {ruta} pero no existe.")
            return None
        paquete = joblib.load(ruta)  # dict: {'buy': {...}, 'sell': {...}} -- ver entrenar.py
        cache = {"version_id": version_id, "paquete": paquete}
        _modelos_cargados[symbol] = cache
        logger.info(f"{symbol}: cargado modelo {version_id} desde disco")

    # tp/sl/lados_aprobados SI pueden cambiar sin que cambie version_id
    # (ej. corriste validar.py de nuevo sobre la misma version) -- se
    # actualizan en cada request, no se cachean.
    cache["tp"] = activo["tp"]
    cache["sl"] = activo["sl"]
    cache["lados_aprobados"] = activo.get("lados_aprobados", [])
    return cache



def _redondear_precio(x):
    """Redondea a ~6 cifras significativas en vez de a 2 decimales fijos.
    Con round(x, 2), en forex 2 * 0.00038 daba 0.0, y el EA descarta la orden
    si tp o sl valen 0 -- por eso GBPUSD nunca llego a abrir ninguna."""
    if x is None or x <= 0:
        return 0.0
    return round(float(x), max(2, 5 - int(math.floor(math.log10(abs(x))))))


@app.get("/predict")
def predict(
    symbol: str = Query(...),
    fecha: str = Query(...),
    c5: float = Query(...),
    ema550: float = Query(...),
    ema5200: float = Query(...),
    macdLine5: float = Query(...),
    signalLine5: float = Query(...),
    adx5: float = Query(...),
    diPlus5: float = Query(...),
    diMinus5: float = Query(...),
    r5: float = Query(...),
    r15: float = Query(...),
    m5: float = Query(...),
    s5: float = Query(...),
    m15: float = Query(...),
    s15: float = Query(...),
    atr5: float = Query(...),
):
    cache = _cargar_modelo(symbol)
    if cache is None:
        # Sin modelo activo para este simbolo: NADA, no romper el EA.
        return {"valor_profit": 0.0, "RESULTADO": "NADA", "tp": 0.0, "sl": 0.0}

    fila = {
        'close': c5, 'ema550': ema550, 'ema5200': ema5200,
        'macdLine5': macdLine5, 'signalLine5': signalLine5,
        'adx5': adx5, 'diPlus5': diPlus5, 'diMinus5': diMinus5,
        'r5': r5, 'r15': r15, 'm5': m5, 's5': s5, 'm15': m15, 's15': s15,
        'atr5': atr5,
    }
    x = construir_features_fila(fila)
    x_vec = [[x[f] for f in FEATURE_LIST]]

    paquete = cache["paquete"]
    resultado = "NADA"
    valor_profit = 0.0
    mejor_prob = 0.0

    tp_out, sl_out = cache["tp"], cache["sl"]  # fallback si el paquete no trae k_tp/k_sl
    lados_aprobados = cache.get("lados_aprobados", [])

    for lado, modelo_lado in paquete.items():  # 'buy', 'sell'
        lado_mayus = "BUY" if lado == "buy" else "SELL"
        if lado_mayus not in lados_aprobados:
            continue  # este lado esta en el .pkl pero validar.py no lo aprobo -- no se sirve
        scaler = modelo_lado["scaler"]
        modelo = modelo_lado["modelo"]
        umbral = modelo_lado["umbral"]
        prob = modelo.predict_proba(scaler.transform(x_vec))[0, 1]
        if prob > umbral and prob > mejor_prob:
            mejor_prob = prob
            valor_profit = float(prob)
            resultado = "BUY" if lado == "buy" else "SELL"
            # tp/sl reales de ESTE momento, no el valor fijo del registry --
            # eso volvería a saturarse con el tiempo, mismo problema que ya
            # arreglamos en las features (ver core.py).
            if "k_tp" in modelo_lado and "k_sl" in modelo_lado:
                tp_out = _redondear_precio(modelo_lado["k_tp"] * atr5)
                sl_out = _redondear_precio(modelo_lado["k_sl"] * atr5)

    logger.info(f"{symbol} {fecha}  RESULTADO={resultado}  prob={mejor_prob:.4f}  "
                f"tp={tp_out} sl={sl_out}  version={cache['version_id']}")

    # Guardar la predicción, para poder comparar despues contra el resultado
    # real (cierres.jsonl) y armar el feedback de calibracion: cuando el
    # modelo dice "70% de confianza", ¿gana realmente cerca del 70% de las
    # veces? Se guarda SIEMPRE, incluido NADA -- para poder ver el
    # comportamiento completo, no solo lo que termino en operacion.
    try:
        PREDICCIONES_PATH.parent.mkdir(parents=True, exist_ok=True)
        registro = dict(
            symbol=symbol.upper(), fecha_vela=fecha, resultado=resultado,
            probabilidad=round(mejor_prob, 4), tp=tp_out, sl=sl_out,
            atr5=round(atr5, 6),  # para poder comparar contra el atr5 aproximado del TRAIN
            features={k: round(float(v), 8) for k, v in x.items()},
            version_id=cache["version_id"],
            registrado_en=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        with open(PREDICCIONES_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"no se pudo guardar la prediccion para feedback: {e}")

    return {
        "valor_profit": valor_profit,
        "RESULTADO": resultado,
        "tp": tp_out,
        "sl": sl_out,
    }


@app.get("/estado")
def estado():
    """Chequeo rapido de que versiones estan activas. Util para debug, no lo
    usa el EA."""
    return _registry.data["activos"]


# =======================================================================
# Registro de cierres reales (lo llama NEO_MINIMAL_V1 cuando cierra algo)
# =======================================================================
@app.get("/registrar_cierre")
def registrar_cierre(
    ticket: int = Query(...),
    symbol: str = Query(...),
    tipo: str = Query(...),          # BUY o SELL
    fecha_apertura: str = Query(...),
    precio_apertura: float = Query(...),
    fecha_cierre: str = Query(...),
    precio_cierre: float = Query(...),
    sl: float = Query(0.0),
    tp: float = Query(0.0),
    profit: float = Query(0.0),
):
    CIERRES_PATH.parent.mkdir(parents=True, exist_ok=True)

    # de-duplicar: si ese ticket ya esta registrado, no se vuelve a escribir
    # (el EA puede reintentar el aviso si no confirma bien la respuesta)
    if CIERRES_PATH.exists():
        with open(CIERRES_PATH, encoding="utf-8") as f:
            for linea in f:
                try:
                    if json.loads(linea).get("ticket") == ticket:
                        return {"ok": True, "duplicado": True}
                except json.JSONDecodeError:
                    continue

    signo = 1 if tipo.upper() == "BUY" else -1
    puntos = signo * (precio_cierre - precio_apertura)

    registro = dict(
        ticket=ticket, symbol=symbol.upper(), tipo=tipo.upper(),
        fecha_apertura=fecha_apertura, precio_apertura=precio_apertura,
        fecha_cierre=fecha_cierre, precio_cierre=precio_cierre,
        sl=sl, tp=tp, profit=profit, puntos=puntos,
        registrado_en=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    with open(CIERRES_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")

    logger.info(f"cierre registrado: {symbol} {tipo} ticket={ticket} puntos={puntos:.2f}")
    return {"ok": True, "duplicado": False}


def parsear_fecha_cierre(s):
    """Parsea fecha_cierre tal como la manda NEO_MINIMAL_V1 (ISO, sin
    timezone) -- devuelve None si no se puede, para no romper el filtro."""
    if not s:
        return None
    try:
        return datetime.strptime(s.split("+")[0], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def _leer_cierres():
    if not CIERRES_PATH.exists():
        return []
    vistos, filas = set(), []
    with open(CIERRES_PATH, encoding="utf-8") as f:
        for linea in f:
            try:
                r = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if r["ticket"] in vistos:
                continue
            vistos.add(r["ticket"])
            filas.append(r)
    return filas


def _evaluar(pct_real, n_real, ref):
    if ref is None or n_real == 0:
        return "sin_referencia"
    if n_real < 20:
        return "muestra_chica"
    p = ref["pct"] / 100
    se = math.sqrt(p * (1 - p) / n_real)
    margen = 1.96 * se * 100   # bilateral al 95%. Antes 1.645, que es el z
    # de UNA cola al 90%: usado como banda bilateral daba ~80% de cobertura
    # real, o sea 1 de cada 5 simbolo/lado salia "FUERA DEL RANGO" por azar.
    lo, hi = ref["pct"] - margen, ref["pct"] + margen
    return "dentro" if lo <= pct_real <= hi else "fuera"


@app.get("/reporte_winrate")
def reporte_winrate(desde: str = Query(None, description="YYYY-MM-DD para filtrar, o 'activacion' para usar la fecha de activación de cada símbolo")):
    """Winrate real en vivo, por simbolo y lado, calculado en el momento a
    partir de datos/operaciones/cierres.jsonl -- lo que NEO_MINIMAL_V1 ya
    reporto. Nada de esto viene de un CSV exportado a mano.

    --desde=YYYY-MM-DD: solo cuenta operaciones cerradas desde esa fecha en
    adelante, para TODOS los simbolos por igual.
    --desde=activacion: cada simbolo se filtra desde SU PROPIA fecha de
    activacion (registry.json) -- asi, si reentrenaste GER40 hoy y NAS100
    hace 3 semanas, cada uno se compara solo contra su propio historial
    post-cambio, sin mezclar operaciones de antes y despues del arreglo.
    """
    filas = _leer_cierres()
    ahora = datetime.now(timezone.utc)
    simbolos = sorted({"NAS100", "GER40", "US30", "BTCUSD"})

    resultado = {"generado_en": ahora.isoformat(timespec="seconds"), "filtro_desde": desde, "simbolos": {}}
    for symbol in simbolos:
        activo = _registry.activo(symbol)
        dias_activo = None
        fecha_corte = None
        dt_act = None
        if activo and activo.get("activado_en"):
            try:
                dt_act = datetime.fromisoformat(activo["activado_en"])
                dt_act_aware = dt_act if dt_act.tzinfo else dt_act.replace(tzinfo=timezone.utc)
                dias_activo = (ahora - dt_act_aware).days
            except ValueError:
                dt_act = None

            if desde == "activacion" and dt_act is not None:
                fecha_corte = dt_act.replace(tzinfo=None)
            elif desde:
                try:
                    fecha_corte = datetime.strptime(desde, "%Y-%m-%d")
                except ValueError:
                    fecha_corte = None

        filas_symbol = filas
        if fecha_corte is not None:
            filas_symbol = [
                r for r in filas
                if (parsear_fecha_cierre(r.get("fecha_cierre")) or datetime.min) >= fecha_corte
            ]

        lados = {}
        for tipo in ("BUY", "SELL"):
            sub = [r for r in filas_symbol if r["symbol"] == symbol and r["tipo"] == tipo]
            n = len(sub)
            ganadas = sum(1 for r in sub if r["puntos"] > 0)
            pct = (ganadas / n * 100) if n else None
            puntos_total = sum(r["puntos"] for r in sub)
            profit_total = sum(r.get("profit", 0.0) for r in sub)
            ref = REFERENCIA.get((symbol, tipo))
            lados[tipo] = dict(
                n=n, ganadas=ganadas, pct=pct,
                puntos=round(puntos_total, 2), profit=round(profit_total, 2),
                referencia=ref, estado=_evaluar(pct, n, ref) if pct is not None else "sin_datos",
            )
        resultado["simbolos"][symbol] = dict(dias_activo=dias_activo, filtrado_desde=str(fecha_corte) if fecha_corte else None, lados=lados)

    return resultado


@app.get("/reporte_winrate.html", response_class=HTMLResponse)
def reporte_winrate_html(desde: str = Query(None, description="YYYY-MM-DD, o 'activacion'")):
    """La misma info que /reporte_winrate, pero para abrir directo en el
    navegador. Guardá esta URL como favorito: cada vez que la abrís, se
    recalcula con lo último que haya en cierres.jsonl -- en vivo.

    Ejemplos:
      /reporte_winrate.html                    -> todo el historial
      /reporte_winrate.html?desde=2026-08-24    -> solo desde esa fecha
      /reporte_winrate.html?desde=activacion    -> cada simbolo, desde SU
                                                    propia fecha de activacion
    """
    data = reporte_winrate(desde=desde)
    NAVY, MIDNIGHT, GOLD, ICE = "#1E2761", "#161B45", "#F2B134", "#CADCFC"
    GREEN, RED, GRAY, LIGHTBG = "#1E8F5F", "#B03A2E", "#68697A", "#F6F7FC"
    BADGES = {
        "dentro": ("DENTRO DE LO ESPERADO", GREEN),
        "fuera": ("FUERA DEL RANGO ESPERADO — REVISAR", RED),
        "muestra_chica": ("MUESTRA MUY CHICA PARA JUZGAR", GOLD),
        "sin_referencia": ("SIN REFERENCIA VALIDADA", GRAY),
        "sin_datos": (None, None),
    }

    tarjetas = []
    for symbol, info in data["simbolos"].items():
        dias = f"{info['dias_activo']} días en demo" if info["dias_activo"] is not None else "no activo"
        filas_html = ""
        for lado_txt, tipo in [("Compra", "BUY"), ("Venta", "SELL")]:
            d = info["lados"][tipo]
            if d["n"] == 0:
                filas_html += (f'<tr><td class="lado">{lado_txt}</td>'
                               f'<td colspan="4" class="sin-datos">sin operaciones todavía</td></tr>')
                continue
            perdidas = d["n"] - d["ganadas"]
            pct_txt = f"{d['pct']:.1f}%".replace(".", ",")
            pct_color = GREEN if d["pct"] >= 50 else (GOLD if d["pct"] >= 30 else RED)
            filas_html += f"""
            <tr>
                <td class="lado">{lado_txt}</td>
                <td class="num">{d['n']}</td>
                <td class="num" style="color:{GREEN}">{d['ganadas']}</td>
                <td class="num" style="color:{RED}">{perdidas}</td>
                <td class="num pct" style="color:{pct_color}">{pct_txt}</td>
            </tr>"""
        tarjetas.append(f"""
        <div class="tarjeta">
            <div class="tarjeta-header"><h2>{symbol}</h2><span class="dias">{dias}</span></div>
            <table><thead><tr><th>Lado</th><th>Operac.</th><th>Ganó</th><th>Perdió</th><th>Winrate</th></tr></thead>
            <tbody>{filas_html}</tbody></table>
        </div>""")

    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta http-equiv="refresh" content="60">
<title>Reporte de modelos — en vivo</title>
<style>
  :root {{ --navy:{NAVY}; --midnight:{MIDNIGHT}; --gold:{GOLD}; --ice:{ICE}; --green:{GREEN}; --red:{RED}; --gray:{GRAY}; --lightbg:{LIGHTBG}; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family:-apple-system,"Segoe UI",Calibri,sans-serif; background:var(--lightbg); color:#26263A; }}
  header {{ background:linear-gradient(135deg,var(--midnight),var(--navy)); color:white; padding:36px 32px 28px; }}
  header h1 {{ margin:0 0 6px; font-size:26px; font-weight:800; }}
  header p {{ margin:0; color:var(--ice); font-size:13px; }}
  .aviso {{ max-width:1300px; margin:-16px auto 0; background:white; border-radius:12px; box-shadow:0 8px 30px rgba(30,39,97,.12); padding:16px 22px; font-size:13px; line-height:1.5; position:relative; z-index:2; }}
  main {{ max-width:1300px; margin:24px auto 50px; padding:0 24px; }}
  .grid {{ display:grid; grid-template-columns:1fr; gap:20px; }}
  @media (max-width:760px) {{ .grid {{ grid-template-columns:1fr; }} }}
  .tarjeta {{ background:white; border-radius:14px; overflow:hidden; box-shadow:0 4px 18px rgba(30,39,97,.08); }}
  .tarjeta-header {{ background:var(--navy); color:white; padding:14px 18px; display:flex; justify-content:space-between; align-items:center; }}
  .tarjeta-header h2 {{ margin:0; font-size:18px; font-weight:800; }}
  .tarjeta-header .dias {{ font-size:11px; color:var(--ice); background:rgba(255,255,255,.12); padding:4px 10px; border-radius:12px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  thead th {{ text-align:left; padding:9px 12px; background:var(--lightbg); color:var(--gray); font-size:10px; text-transform:uppercase; letter-spacing:.5px; }}
  tbody td {{ padding:9px 12px; border-top:1px solid #eee; }}
  td.lado {{ font-weight:700; color:var(--navy); }}
  td.num {{ text-align:right; }}
  td.pct {{ font-weight:800; }}
  .ref {{ display:block; font-weight:400; font-size:10px; color:var(--gray); }}
  .sin-datos {{ color:var(--gray); font-style:italic; text-align:center; }}
  tr.fila-badge td {{ border-top:none; padding:0 12px 10px; }}
  .badge {{ display:inline-block; padding:3px 9px; border-radius:20px; font-size:10px; font-weight:800; }}
  .detalle-ref {{ font-size:10.5px; color:var(--gray); margin-left:6px; }}
  .tabs {{ max-width:1300px; margin:20px auto 0; padding:0 24px; display:flex; gap:8px; }}
  .tab {{ padding:10px 22px; border:none; border-radius:10px 10px 0 0; background:#E4E7F4; color:var(--gray);
          font-size:13px; font-weight:700; cursor:pointer; font-family:inherit; }}
  .tab.activa {{ background:white; color:var(--navy); box-shadow:0 -3px 10px rgba(30,39,97,.07); }}
  .panel {{ display:none; }}
  .panel.activo {{ display:block; }}
  #marco-diario {{ width:100%; height:78vh; border:none; background:white; border-radius:14px;
                   box-shadow:0 4px 18px rgba(30,39,97,.08); }}
</style></head><body>
<header><h1>Reporte de modelos — en vivo</h1>
<p>Actualizado: {data['generado_en'][:19].replace('T',' ')} UTC · se refresca solo cada 60s
{f' · <b>filtrado desde: {desde}</b> (cada símbolo desde su propia activación)' if desde == 'activacion' else (f' · <b>filtrado desde: {desde}</b>' if desde else ' · mostrando todo el historial')}</p></header>
<div class="aviso">Datos reales, reportados directo por el EA al cerrar cada operación — no un archivo exportado a mano.</div>
<div class="tabs">
  <button class="tab activa" id="tab-resumen" onclick="verPanel('resumen')">Resumen</button>
  <button class="tab" id="tab-diario" onclick="verPanel('diario')">Diario</button>
</div>
<main>
  <div class="panel activo" id="panel-resumen"><div class="grid">{''.join(tarjetas)}</div></div>
  <div class="panel" id="panel-diario"><iframe id="marco-diario" src="/reporte_diario_panel.html"></iframe></div>
</main>
<script>
function verPanel(cual) {{
  for (const p of ['resumen','diario']) {{
    document.getElementById('panel-'+p).classList.toggle('activo', p===cual);
    document.getElementById('tab-'+p).classList.toggle('activa', p===cual);
  }}
  // el auto-refresh de 60s recargaria la pagina y volveria a Resumen; se corta
  // al entrar en Diario para no sacar al usuario de donde estaba mirando.
  if (cual === 'diario') {{
    const meta = document.querySelector('meta[http-equiv="refresh"]');
    if (meta) meta.remove();
  }}
}}
</script>
</body></html>"""
    return html


@app.get("/reporte_diario_panel.html", response_class=HTMLResponse)
def reporte_diario_panel(desde: str = Query(None, description="YYYY-MM-DD")):
    """Tabla de winrate DIA POR DIA, calculada en vivo desde cierres.jsonl en
    cada visita -- igual que la pestaña Resumen. No lee ningun archivo
    generado a mano: no hay que correr ningun comando para actualizarla.

    Por defecto arranca en DIARIO_DESDE (activacion de los modelos v3). Lo
    anterior se hizo con otros modelos y con bugs que ya se corrigieron."""
    corte = desde if isinstance(desde, str) and desde else DIARIO_DESDE
    cierres = [c for c in _leer_cierres()
               if str(c.get("fecha_cierre", ""))[:10] >= corte]
    if not cierres:
        return ('<!DOCTYPE html><html><head><meta charset="UTF-8"></head>'
                '<body style="font-family:-apple-system,Segoe UI,Calibri,sans-serif;'
                f'padding:40px;color:#68697A">Todavia no hay operaciones cerradas '
                f'desde el {corte}.</body></html>')

    celdas, dias, claves = {}, set(), set()
    for c in cierres:
        dia = str(c.get("fecha_cierre", ""))[:10]
        if len(dia) != 10:
            continue
        lado = "Compra" if str(c.get("tipo", "")).lower().startswith("b") else "Venta"
        k = (c["symbol"].upper(), lado)
        celdas.setdefault((k, dia), []).append(c)
        dias.add(dia)
        claves.add(k)

    dias = sorted(dias)
    claves = sorted(claves)

    # Con menos de 3 operaciones el winrate no significa nada: 0% de 1 sola
    # operacion se veria igual de rojo que 0% de 20. Esas celdas van en gris.
    MIN_PARA_COLOR = 3

    def estilo(pct, n):
        if n < MIN_PARA_COLOR:
            return "background:#F4F5FA;color:#8A8C9E"
        if pct >= 60: return "background:#1B7F4B;color:#FFFFFF"
        if pct >= 50: return "background:#4FA97B;color:#FFFFFF"
        if pct >= 40: return "background:#F2B134;color:#3A3A3A"
        if pct >= 30: return "background:#E08A3C;color:#FFFFFF"
        return "background:#C0392B;color:#FFFFFF"

    filas = []
    for k in claves:
        sym, lado = k
        tds = []
        tot_n = tot_g = 0
        tot_prof = 0.0
        for d in dias:
            ops = celdas.get((k, d), [])
            if not ops:
                tds.append('<td class="vacia">—</td>')
                continue
            n = len(ops)
            g = sum(1 for o in ops if o.get("puntos", 0) > 0)
            prof = sum(float(o.get("profit", 0) or 0) for o in ops)
            tot_n += n; tot_g += g; tot_prof += prof
            pct = g / n * 100
            tds.append(f'<td style="{estilo(pct, n)}"><b>{pct:.0f}%</b>'
                       f'<span class="n">n={n}</span>'
                       f'<span class="p">{prof:+,.2f}</span></td>')
        if tot_n == 0:
            continue
        pct_tot = tot_g / tot_n * 100
        filas.append(
            f'<tr><th class="lbl">{sym}<span>{lado}</span></th>'
            + "".join(tds)
            + f'<td class="tot" style="{estilo(pct_tot, tot_n)}">'
              f'<b>{pct_tot:.0f}%</b><span class="n">n={tot_n}</span>'
              f'<span class="p">{tot_prof:+,.2f}</span></td></tr>')

    encabezados = "".join(f'<th>{d[8:10]}-{MESES[int(d[5:7])]}</th>' for d in dias)
    total_ops = sum(len(v) for v in celdas.values())
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")

    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<style>
  body {{ font-family:-apple-system,'Segoe UI',Calibri,sans-serif; margin:0;
         padding:0; color:#3A3A3A; background:transparent; }}
  .cab {{ background:linear-gradient(135deg,#141B4D,#1E2761); color:white;
          padding:22px 26px; border-radius:14px 14px 0 0; }}
  .cab h2 {{ margin:0; font-size:19px; font-weight:700; }}
  .cab p {{ margin:6px 0 0; font-size:11.5px; opacity:.75; }}
  .caja {{ overflow-x:auto; background:white; border-radius:0 0 14px 14px;
           box-shadow:0 4px 18px rgba(30,39,97,.09); }}
  table {{ border-collapse:collapse; font-size:11px; white-space:nowrap; width:100%; }}
  th, td {{ padding:7px 10px; text-align:center; border:1px solid #EDEEF5; }}
  thead th {{ background:#2B3573; color:white; font-size:10px; font-weight:600;
              letter-spacing:.4px; }}
  thead th.total {{ background:#141B4D; }}
  th.lbl {{ background:#F0F1F7; color:#1E2761; text-align:left; font-weight:700;
            position:sticky; left:0; z-index:2; min-width:112px; }}
  th.lbl span {{ display:block; font-weight:400; font-size:10px; color:#68697A; }}
  thead th.lbl {{ background:#2B3573; color:white; }}
  td.tot {{ font-weight:800; border-left:3px solid #141B4D; }}
  td b {{ display:block; font-size:12.5px; }}
  td .n {{ display:block; font-size:9px; opacity:.8; }}
  td .p {{ display:block; font-size:9px; opacity:.8; }}
  td.vacia {{ color:#D2D4E0; background:#FBFBFD; }}
  .pie {{ font-size:10.5px; color:#68697A; padding:12px 4px 0; line-height:1.6; }}
</style></head><body>
  <div class="cab">
    <h2>Reporte diario — winrate por simbolo/lado, dia por dia</h2>
    <p>Desde el {corte} (activacion de los modelos v3) · {total_ops} operaciones ·
    {len(dias)} dias con datos · calculado en vivo el {ahora}</p>
  </div>
  <div class="caja"><table>
    <thead><tr><th class="lbl">Simbolo / Lado</th>{encabezados}
      <th class="total">TOTAL</th></tr></thead>
    <tbody>{''.join(filas)}</tbody>
  </table></div>
  <div class="pie">
    Cada celda: <b>winrate</b> · <b>n</b> = operaciones cerradas ·
    <b>resultado en USD</b> de ese dia.<br>
    Las celdas con menos de {MIN_PARA_COLOR} operaciones van en gris: con tan pocas,
    el winrate no significa nada todavia.
  </div>
</body></html>"""
