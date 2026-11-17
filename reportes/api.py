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
PREDICCIONES_PATH = Path("datos/operaciones/predicciones.jsonl")

# Referencia de validar.py -- PF/WR/n confirmados contra miles de operaciones
# simuladas y contra el azar (p<0.05 en todos). Si un simbolo/lado no
# aparece aca, es porque no paso la validacion -- no se muestra referencia.
REFERENCIA = {
    ("NAS100", "BUY"):  dict(pct=8.4,  pf=1.68, n=992,  p="0,0000"),
    ("NAS100", "SELL"): dict(pct=47.9, pf=1.96, n=2061, p="0,0000"),
    ("GER40",  "BUY"):  dict(pct=52.6, pf=1.97, n=2026, p="0,0000"),
    ("GER40",  "SELL"): dict(pct=42.9, pf=2.22, n=1670, p="0,0000"),
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
                tp_out = round(modelo_lado["k_tp"] * atr5, 2)
                sl_out = round(modelo_lado["k_sl"] * atr5, 2)

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
    margen = 1.645 * se * 100
    lo, hi = ref["pct"] - margen, ref["pct"] + margen
    return "dentro" if lo <= pct_real <= hi else "fuera"


@app.get("/reporte_winrate")
def reporte_winrate():
    """Winrate real en vivo, por simbolo y lado, calculado en el momento a
    partir de datos/operaciones/cierres.jsonl -- lo que NEO_MINIMAL_V1 ya
    reporto. Nada de esto viene de un CSV exportado a mano."""
    filas = _leer_cierres()
    ahora = datetime.now(timezone.utc)
    simbolos = sorted({"NAS100", "GER40", "US30", "BTCUSD"})

    resultado = {"generado_en": ahora.isoformat(timespec="seconds"), "simbolos": {}}
    for symbol in simbolos:
        activo = _registry.activo(symbol)
        dias_activo = None
        if activo and activo.get("activado_en"):
            try:
                dt_act = datetime.fromisoformat(activo["activado_en"])
                dias_activo = (ahora - dt_act).days
            except ValueError:
                pass

        lados = {}
        for tipo in ("BUY", "SELL"):
            sub = [r for r in filas if r["symbol"] == symbol and r["tipo"] == tipo]
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
        resultado["simbolos"][symbol] = dict(dias_activo=dias_activo, lados=lados)

    return resultado


@app.get("/reporte_winrate.html", response_class=HTMLResponse)
def reporte_winrate_html():
    """La misma info que /reporte_winrate, pero para abrir directo en el
    navegador. Guardá esta URL como favorito: cada vez que la abrís, se
    recalcula con lo último que haya en cierres.jsonl -- en vivo."""
    data = reporte_winrate()
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
                               f'<td colspan="5" class="sin-datos">sin operaciones todavía</td></tr>')
                continue
            pct_txt = f"{d['pct']:.1f}%".replace(".", ",")
            if d["referencia"]:
                ref_txt = f"esperado: {d['referencia']['pct']:.1f}%".replace(".", ",")
                ref_detalle = f"validado con {d['referencia']['n']:,} operaciones simuladas, p={d['referencia']['p']}".replace(",", ".", 1)
            else:
                ref_txt, ref_detalle = "sin validar", "este lado no pasó la validación estadística"
            label, color = BADGES[d["estado"]]
            puntos_color = GREEN if d["puntos"] >= 0 else RED
            puntos_txt = f"{d['puntos']:+.2f}".replace(".", ",")
            profit_color = GREEN if d["profit"] >= 0 else RED
            profit_txt = f"{d['profit']:+.2f}".replace(".", ",")
            filas_html += f"""
            <tr>
                <td class="lado">{lado_txt}</td>
                <td class="num">{d['n']}</td>
                <td class="num">{d['ganadas']}</td>
                <td class="num pct">{pct_txt}<span class="ref">{ref_txt}</span></td>
                <td class="num" style="color:{puntos_color}">{puntos_txt} pts<span class="ref">precio puro</span></td>
                <td class="num" style="color:{profit_color}">{profit_txt}<span class="ref">real, con spread/swap</span></td>
            </tr>
            <tr class="fila-badge"><td colspan="6">
                <span class="badge" style="background:{color}22;color:{color};border:1px solid {color}55">{label}</span>
                <span class="detalle-ref">{ref_detalle}</span>
            </td></tr>"""
        tarjetas.append(f"""
        <div class="tarjeta">
            <div class="tarjeta-header"><h2>{symbol}</h2><span class="dias">{dias}</span></div>
            <table><thead><tr><th>Lado</th><th>Operac.</th><th>Ganó</th><th>% Real</th><th>Puntos</th><th>Resultado real</th></tr></thead>
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
</style></head><body>
<header><h1>Reporte de modelos — en vivo</h1>
<p>Actualizado: {data['generado_en'][:19].replace('T',' ')} UTC · se refresca solo cada 60s</p></header>
<div class="aviso"><b>% Real</b> es lo que ya cerró de verdad, reportado directo por el EA al cerrar cada operación —
no un archivo exportado a mano. Al lado, <b>esperado</b> es lo validado con miles de operaciones simuladas antes de activar el modelo.</div>
<main><div class="grid">{''.join(tarjetas)}</div></main>
</body></html>"""
    return html
