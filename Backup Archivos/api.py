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
import pandas as pd
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

# Capital de referencia para expresar los resultados en %. NO se usa el balance
# de la cuenta: es compartida con otras estrategias y recibio tres depositos de
# 10.000 el 07-sep-2026, asi que su balance no refleja lo que este sistema
# arriesga. 22.067 = balance del 07-sep menos esos depositos.
CAPITAL_REFERENCIA = 22067.0
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
    # Lista de variables CON LAS QUE SE ENTRENO esa version. No se usa
    # FEATURE_LIST global porque distintas versiones pueden tener listas
    # distintas: al sacar las 3 variables de M15 (que traian informacion del
    # futuro por como las exportaba el .mq4), los modelos nuevos usan 12 y los
    # viejos 15. Si se usara la global, los viejos se romperian al recargar.
    cache["features"] = activo.get("features") or FEATURE_LIST
    return cache



def _redondear_precio(x):
    """Redondea a ~6 cifras significativas en vez de a 2 decimales fijos.
    Con round(x, 2), en forex 2 * 0.00038 daba 0.0, y el EA descarta la orden
    si tp o sl valen 0 -- por eso GBPUSD nunca llego a abrir ninguna."""
    if x is None or x <= 0:
        return 0.0
    return round(float(x), max(2, 5 - int(math.floor(math.log10(abs(x))))))



_AVISADOS_EA_VIEJO = set()


def _parsear_fecha(txt):
    """La fecha que manda el EA -> Timestamp, para hora_sin/hora_cos."""
    try:
        return pd.Timestamp(str(txt).split("+")[0])
    except (ValueError, TypeError):
        return None


def _avisar_ea_viejo(symbol):
    """El EA no manda los campos de V5 (h5/l5/v5/v5ma20/c5d). core.py va a usar
    valores neutros y un modelo v5 va a predecir cualquier cosa. Se avisa una
    sola vez por simbolo para no llenar el log."""
    if symbol.upper() in _AVISADOS_EA_VIEJO:
        return
    _AVISADOS_EA_VIEJO.add(symbol.upper())
    logger.error(
        f"{symbol}: el EA no esta mandando los campos de V5 (h5, l5, v5, "
        f"v5ma20, c5d). Recompilar NEO_MINIMAL_V1.mq4 con F7. Hasta entonces "
        f"vol_rel, rango_rel, cierre_pos y ret1 salen neutros.")


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
    # V5: campos nuevos. Opcionales para no romper si el EA todavia no se
    # recompilo -- si no llegan, core.py usa neutros (vol_rel=1, ret1=0, etc.)
    # y el modelo v5 va a predecir mal. Ver el aviso en el log.
    h5: float = Query(None),
    l5: float = Query(None),
    v5: float = Query(None),
    v5ma20: float = Query(None),
    c5d: float = Query(None),
    todos_los_lados: bool = False,
):
    """todos_los_lados: normalmente se sirven SOLO los lados que validar.py
    aprobo. El entorno de prueba lo pone en True para poder medir los dos y
    ver cual anda mejor. Nunca deberia usarse en produccion: servir un lado
    que no paso la validacion es operar algo medido como sin ventaja."""
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
        # V5
        'h5': h5, 'l5': l5, 'v5': v5, 'v5ma20': v5ma20, 'c5d': c5d,
        'fecha': _parsear_fecha(fecha),
    }
    if h5 is None:
        _avisar_ea_viejo(symbol)
    x = construir_features_fila(fila)
    feats = cache.get("features") or FEATURE_LIST
    faltan = [f for f in feats if f not in x]
    if faltan:
        logger.error(f"{symbol}: el modelo {cache['version_id']} pide variables "
                     f"que core.py ya no calcula: {faltan}")
        return {"valor_profit": 0.0, "RESULTADO": "NADA", "tp": 0.0, "sl": 0.0}
    x_vec = [[x[f] for f in feats]]

    paquete = cache["paquete"]
    resultado = "NADA"
    valor_profit = 0.0
    mejor_prob = 0.0

    tp_out, sl_out = cache["tp"], cache["sl"]  # fallback si el paquete no trae k_tp/k_sl
    lados_aprobados = cache.get("lados_aprobados", [])

    for lado, modelo_lado in paquete.items():  # 'buy', 'sell'
        lado_mayus = "BUY" if lado == "buy" else "SELL"
        if lado_mayus not in lados_aprobados and not todos_los_lados:
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
  <button class="tab" id="tab-ganancia" onclick="verPanel('ganancia')">Ganancia</button>
  <button class="tab" id="tab-regla" onclick="verPanel('regla')">Regla diaria</button>
  <button class="tab" id="tab-prueba" onclick="verPanel('prueba')">Prueba M5</button>
  <button class="tab" id="tab-pdiario" onclick="verPanel('pdiario')">Diario M5</button>
  <button class="tab" id="tab-selectivo" onclick="verPanel('selectivo')">NEO Selectivo</button>
</div>
<main>
  <div class="panel activo" id="panel-resumen"><div class="grid">{''.join(tarjetas)}</div></div>
  <div class="panel" id="panel-diario"><iframe id="marco-diario" src="/reporte_diario_panel.html"></iframe></div>
  <div class="panel" id="panel-ganancia"><iframe id="marco-diario" src="/reporte_ganancia_panel.html"></iframe></div>
  <div class="panel" id="panel-regla"><iframe id="marco-diario" src="/regla_diaria_estado"></iframe></div>
  <div class="panel" id="panel-prueba"><iframe id="marco-diario" src="/prueba/reporte.html"></iframe></div>
  <div class="panel" id="panel-pdiario"><iframe id="marco-diario" src="/prueba/diario.html"></iframe></div>
  <div class="panel" id="panel-selectivo"><iframe id="marco-diario" src="/selectivo/reporte.html"></iframe></div>
</main>
<script>
function verPanel(cual) {{
  for (const p of ['resumen','diario','ganancia','regla','prueba','pdiario','selectivo']) {{
    document.getElementById('panel-'+p).classList.toggle('activo', p===cual);
    document.getElementById('tab-'+p).classList.toggle('activa', p===cual);
  }}
  // el auto-refresh de 60s recargaria la pagina y volveria a Resumen; se corta
  // al entrar en Diario para no sacar al usuario de donde estaba mirando.
  if (cual !== 'resumen') {{
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
    acum = [0.0, 0]
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
                       f'<span class="p">{prof:+,.2f}</span>'
                       f'<span class="r">{prof/CAPITAL_REFERENCIA*100:+.2f}%</span>'
                       f'</td>')
        if tot_n == 0:
            continue
        pct_tot = tot_g / tot_n * 100
        acum[0] += tot_prof; acum[1] += tot_n
        filas.append(
            f'<tr><th class="lbl">{sym}<span>{lado}</span></th>'
            + "".join(tds)
            + f'<td class="tot" style="{estilo(pct_tot, tot_n)}">'
              f'<b>{pct_tot:.0f}%</b><span class="n">n={tot_n}</span>'
              f'<span class="p">{tot_prof:+,.2f}</span>'
              f'<span class="r">{tot_prof/CAPITAL_REFERENCIA*100:+.2f}%</span>'
              f'</td></tr>')

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
  td .r {{ display:block; font-size:9px; opacity:.9; font-weight:700; }}
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
    <b>resultado en USD</b> · <b>% del capital</b>, de ese dia.<br>
    <b>Acumulado: {acum[0]:+,.2f} USD = {acum[0]/CAPITAL_REFERENCIA*100:+.2f}%</b>
    sobre un capital de referencia de {CAPITAL_REFERENCIA:,.0f} USD,
    en {acum[1]} operaciones.<br>
    El capital de referencia NO es el balance de la cuenta: esa cuenta es
    compartida con otras estrategias y recibio 30.000 de deposito el 07-sep.<br>
    Las celdas con menos de {MIN_PARA_COLOR} operaciones van en gris: con tan pocas,
    el winrate no significa nada todavia.
  </div>
</body></html>"""


@app.get("/reporte_ganancia_panel.html", response_class=HTMLResponse)
def reporte_ganancia_panel(desde: str = Query(None, description="YYYY-MM-DD")):
    """Pestaña "Ganancia": solo el % del capital, por dia y por simbolo/lado.
    Misma informacion que "Diario" pero con una sola cifra por celda, que es
    lo que se puede comparar de forma directa contra el tablero del jefe.

    El % se calcula sobre CAPITAL_REFERENCIA, no sobre el balance: esa cuenta
    es compartida con otras estrategias y recibio 30.000 de deposito el
    07-sep-2026."""
    corte = desde if isinstance(desde, str) and desde else DIARIO_DESDE
    cierres = [c for c in _leer_cierres()
               if str(c.get("fecha_cierre", ""))[:10] >= corte]
    if not cierres:
        return ('<!DOCTYPE html><html><head><meta charset="UTF-8"></head>'
                '<body style="font-family:-apple-system,Segoe UI,Calibri,sans-serif;'
                f'padding:40px;color:#68697A">Sin operaciones desde el {corte}.'
                '</body></html>')

    celdas, dias, claves = {}, set(), set()
    for c in cierres:
        dia = str(c.get("fecha_cierre", ""))[:10]
        if len(dia) != 10:
            continue
        lado = "Compra" if str(c.get("tipo", "")).lower().startswith("b") else "Venta"
        k = (c["symbol"].upper(), lado)
        celdas.setdefault((k, dia), []).append(c)
        dias.add(dia); claves.add(k)
    dias, claves = sorted(dias), sorted(claves)

    # mismos tramos que usa el tablero del jefe
    def estilo(p):
        if p > 5:    return "background:#1B7F4B;color:#FFFFFF"
        if p > 1:    return "background:#63B37F;color:#FFFFFF"
        if p > 0:    return "background:#D8EFE0;color:#1B5E37"
        if p == 0:   return "background:#F7F7FA;color:#8A8C9E"
        if p > -1:   return "background:#FBE3DC;color:#8A3524"
        if p > -5:   return "background:#E8907A;color:#FFFFFF"
        return "background:#C0392B;color:#FFFFFF"

    filas = []
    acum = [0.0, 0]
    for k in claves:
        sym, lado = k
        tds, tot = [], 0.0
        tot_n = 0
        for d in dias:
            ops = celdas.get((k, d), [])
            if not ops:
                tds.append('<td class="vacia">—</td>')
                continue
            prof = sum(float(o.get("profit", 0) or 0) for o in ops)
            tot += prof; tot_n += len(ops)
            p = prof / CAPITAL_REFERENCIA * 100
            tds.append(f'<td style="{estilo(p)}">{p:+.2f}%</td>')
        if tot_n == 0:
            continue
        acum[0] += tot; acum[1] += tot_n
        pt = tot / CAPITAL_REFERENCIA * 100
        filas.append(f'<tr><th class="lbl">{sym}<span>{lado}</span></th>'
                     + "".join(tds)
                     + f'<td class="tot" style="{estilo(pt)}">{pt:+.2f}%</td></tr>')

    enc = "".join(f'<th>{d[8:10]}-{MESES[int(d[5:7])]}</th>' for d in dias)
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    pa = acum[0] / CAPITAL_REFERENCIA * 100

    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<style>
  body {{ font-family:-apple-system,'Segoe UI',Calibri,sans-serif; margin:0;
         padding:0; color:#3A3A3A; background:transparent; }}
  .cab {{ background:linear-gradient(135deg,#141B4D,#1E2761); color:white;
          padding:22px 26px; border-radius:14px 14px 0 0; }}
  .cab h2 {{ margin:0; font-size:19px; font-weight:700; }}
  .cab p {{ margin:6px 0 0; font-size:11.5px; opacity:.75; }}
  .ley {{ font-size:10.5px; color:#68697A; padding:10px 4px 8px; }}
  .ley i {{ display:inline-block; width:11px; height:11px; border-radius:3px;
            margin:0 4px 0 12px; vertical-align:-1px; }}
  .caja {{ overflow-x:auto; background:white; border-radius:0 0 14px 14px;
           box-shadow:0 4px 18px rgba(30,39,97,.09); }}
  table {{ border-collapse:collapse; font-size:11.5px; white-space:nowrap;
           width:100%; }}
  th, td {{ padding:9px 11px; text-align:center; border:1px solid #EDEEF5;
            font-weight:600; }}
  thead th {{ background:#2B3573; color:white; font-size:10px; font-weight:600; }}
  thead th.total {{ background:#141B4D; }}
  th.lbl {{ background:#F0F1F7; color:#1E2761; text-align:left; font-weight:700;
            position:sticky; left:0; z-index:2; min-width:112px; }}
  th.lbl span {{ display:block; font-weight:400; font-size:10px; color:#68697A; }}
  thead th.lbl {{ background:#2B3573; color:white; }}
  td.tot {{ font-weight:800; border-left:3px solid #141B4D; }}
  td.vacia {{ color:#D2D4E0; background:#FBFBFD; }}
  .pie {{ font-size:10.5px; color:#68697A; padding:12px 4px 0; line-height:1.6; }}
</style></head><body>
  <div class="cab">
    <h2>Ganancia — % del capital por dia y por par</h2>
    <p>Desde el {corte} · {acum[1]} operaciones · {len(dias)} dias ·
    calculado en vivo el {ahora}</p>
  </div>
  <div class="ley">
    <i style="background:#1B7F4B"></i>&gt;5%
    <i style="background:#63B37F"></i>1 a 5%
    <i style="background:#D8EFE0"></i>0 a 1%
    <i style="background:#FBE3DC"></i>0 a -1%
    <i style="background:#E8907A"></i>-1 a -5%
    <i style="background:#C0392B"></i>&lt;-5%
    <i style="background:#FBFBFD;border:1px solid #EDEEF5"></i>sin operaciones
  </div>
  <div class="caja"><table>
    <thead><tr><th class="lbl">Simbolo / Lado</th>{enc}
      <th class="total">TOTAL</th></tr></thead>
    <tbody>{''.join(filas)}</tbody>
  </table></div>
  <div class="pie">
    <b>Acumulado: {pa:+.2f}%</b> ({acum[0]:+,.2f} USD) sobre un capital de
    referencia de {CAPITAL_REFERENCIA:,.0f} USD.<br>
    El capital de referencia NO es el balance de la cuenta: esa cuenta es
    compartida con otras estrategias y recibio 30.000 de deposito el 07-sep.
  </div>
</body></html>"""


# =======================================================================
# REGLA DIARIA (en prueba) -- NAS100
#
# No usa ningun modelo. Es una regla de dos condiciones que salio de la
# busqueda de combinaciones y sobrevivio a la validacion en dos periodos
# que nunca vio:
#
#   COMPRA cuando, en el grafico DIARIO:
#       rel_ema50_200 = ema50/ema200 - 1  esta en su tramo "alto"
#       Y adx5 (ADX 14) esta en su tramo "alto"
#
#   entrenamiento  74 ops  acierto 54% (promedio 36%)  PF 2.30
#   HOLDOUT_A      34 ops  acierto 68% (promedio 32%)  PF 3.95
#   HOLDOUT_B      34 ops  acierto 47% (promedio 31%)  PF 1.50
#
# Los cortes de los tramos salen de regla_diaria.json, que genera
# analisis/generar_regla.py a partir del archivo de entrenamiento. Si ese
# archivo no esta, el endpoint devuelve NADA en vez de inventar valores.
#
# OJO: el EA tiene que mandar los indicadores del grafico DIARIO, no del de
# 5 minutos. Con valores de M5 la regla no significa nada.
# =======================================================================

REGLA_PATH = Path("regla_diaria.json")
REGLA_LOG = Path("datos/operaciones/regla_diaria.jsonl")
_regla_cache = {"mtime": None, "datos": None}


def _leer_regla():
    """Se relee sola si cambia el archivo, sin reiniciar el servidor."""
    if not REGLA_PATH.exists():
        return None
    mt = REGLA_PATH.stat().st_mtime
    if _regla_cache["mtime"] != mt:
        try:
            _regla_cache["datos"] = json.loads(REGLA_PATH.read_text(encoding="utf-8"))
            _regla_cache["mtime"] = mt
            logger.info(f"regla_diaria.json cargado "
                        f"({_regla_cache['datos'].get('symbol')})")
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"regla_diaria.json ilegible: {e}")
            return None
    return _regla_cache["datos"]


@app.get("/regla_diaria")
def regla_diaria(
    symbol: str = Query(...),
    fecha: str = Query(...),
    c5: float = Query(..., description="cierre de la vela DIARIA ya cerrada"),
    ema550: float = Query(..., description="EMA 50 del grafico DIARIO"),
    ema5200: float = Query(..., description="EMA 200 del grafico DIARIO"),
    adx5: float = Query(..., description="ADX 14 del grafico DIARIO"),
    atr5: float = Query(..., description="ATR 14 del grafico DIARIO"),
):
    """Evalua la regla y devuelve BUY o NADA, con objetivo y stop.

    Sirve para las dos cosas: el EA la consulta para operar, y queda
    registrada en datos/operaciones/regla_diaria.jsonl para poder revisar
    despues cuantas veces se activo y con que valores."""
    r = _leer_regla()
    fuera = dict(RESULTADO="NADA", tp=0.0, sl=0.0, activa=False)

    if r is None:
        return dict(fuera, motivo="falta regla_diaria.json "
                                  "(generarlo con analisis/generar_regla.py)")
    if symbol.upper() != r["symbol"]:
        return dict(fuera, motivo=f"la regla es solo para {r['symbol']}")
    if ema5200 == 0 or atr5 <= 0:
        return dict(fuera, motivo="ema200 o atr invalidos")

    valores = {"rel_ema50_200": ema550 / ema5200 - 1, "adx5": adx5}
    detalle, todas = {}, True
    for c in r["condiciones"]:
        v = valores[c["variable"]]
        ok = c["desde"] <= v < c["hasta"]
        todas = todas and ok
        detalle[c["variable"]] = dict(valor=round(float(v), 6),
                                      desde=c["desde"], hasta=c["hasta"], ok=ok)

    resultado = r["lado"] if todas else "NADA"
    tp = _redondear_precio(r["k_tp"] * atr5) if todas else 0.0
    sl = _redondear_precio(r["k_sl"] * atr5) if todas else 0.0

    registro = dict(symbol=symbol.upper(), fecha_vela=fecha, resultado=resultado,
                    activa=todas, tp=tp, sl=sl, atr=round(atr5, 6),
                    condiciones=detalle,
                    registrado_en=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    try:
        REGLA_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(REGLA_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.error(f"no se pudo escribir {REGLA_LOG}: {e}")

    logger.info(f"REGLA {symbol.upper()} {fecha}  {resultado}  "
                f"rel_ema50_200={valores['rel_ema50_200']:.5f} "
                f"adx={adx5:.2f}  tp={tp} sl={sl}")
    return dict(RESULTADO=resultado, tp=tp, sl=sl, activa=todas,
                condiciones=detalle)


@app.get("/regla_diaria_estado", response_class=HTMLResponse)
def regla_diaria_estado():
    """Pagina de monitoreo: que dice la regla, como viene y sus resultados
    de validacion. Se calcula en vivo en cada visita."""
    r = _leer_regla()
    if r is None:
        return ("<!DOCTYPE html><html><head><meta charset='UTF-8'></head><body "
                "style=\"font-family:-apple-system,Segoe UI,Calibri,sans-serif;"
                "padding:40px;color:#68697A\">No existe <code>regla_diaria.json</code>."
                " Generalo con <code>py analisis\\generar_regla.py</code>.</body></html>")

    consultas = []
    if REGLA_LOG.exists():
        for linea in open(REGLA_LOG, encoding="utf-8"):
            try:
                consultas.append(json.loads(linea))
            except json.JSONDecodeError:
                continue
    activas = [c for c in consultas if c.get("activa")]
    ultima = consultas[-1] if consultas else None

    v = r["resultados_validacion"]
    filas_val = "".join(
        f"<tr><td>{k.replace('_', ' ')}</td><td>{d['n']}</td>"
        f"<td>{d['acierto']:.0%}</td><td>{d['promedio']:.0%}</td>"
        f"<td>{d['pf']:.2f}</td></tr>" for k, d in v.items())

    if ultima:
        det = ultima["condiciones"]
        filas_ult = "".join(
            f"<tr><td>{n}</td><td>{d['valor']}</td>"
            f"<td>{d['desde']:.5f} a {d['hasta']:.5f}</td>"
            f"<td>{'SI' if d['ok'] else 'no'}</td></tr>" for n, d in det.items())
        cab_ult = (f"Ultima consulta: {ultima['fecha_vela']} — "
                   f"<b>{ultima['resultado']}</b>")
    else:
        filas_ult = "<tr><td colspan=4>todavia no hubo consultas</td></tr>"
        cab_ult = "Todavia no hubo consultas"

    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>Regla diaria</title><style>
 body{{font-family:-apple-system,'Segoe UI',Calibri,sans-serif;margin:0;
      padding:24px;color:#3A3A3A;background:#F4F5FA}}
 .c{{max-width:900px;margin:0 auto}}
 .cab{{background:linear-gradient(135deg,#141B4D,#1E2761);color:#fff;
      padding:22px 26px;border-radius:14px}}
 .cab h2{{margin:0;font-size:19px}} .cab p{{margin:6px 0 0;font-size:12px;opacity:.8}}
 .caja{{background:#fff;border-radius:14px;padding:18px 22px;margin-top:16px;
       box-shadow:0 4px 18px rgba(30,39,97,.08)}}
 h3{{font-size:14px;margin:0 0 10px;color:#1E2761}}
 table{{border-collapse:collapse;width:100%;font-size:12.5px}}
 th,td{{padding:7px 10px;text-align:left;border-bottom:1px solid #EDEEF5}}
 th{{color:#68697A;font-weight:600;font-size:11px}}
 .av{{background:#FFF6DE;border-left:4px solid #F2B134;padding:12px 16px;
     font-size:12px;border-radius:0 8px 8px 0;margin-top:16px;line-height:1.6}}
</style></head><body><div class="c">
 <div class="cab"><h2>Regla diaria — {r['symbol']} {r['timeframe']}</h2>
  <p>{cab_ult} · {len(consultas)} consultas, {len(activas)} con la regla activa</p></div>
 <div class="caja"><h3>Estado de las condiciones</h3>
  <table><tr><th>variable</th><th>valor</th><th>tramo requerido</th><th>cumple</th></tr>
  {filas_ult}</table></div>
 <div class="caja"><h3>Resultados de la validacion</h3>
  <table><tr><th>periodo</th><th>operaciones</th><th>acierto</th>
  <th>promedio del periodo</th><th>rentabilidad</th></tr>{filas_val}</table></div>
 <div class="caja"><h3>Como se entreno</h3>
  <table>
   <tr><td>archivo</td><td>{r['entrenado_con']}</td></tr>
   <tr><td>periodo</td><td>{r['desde']} a {r['hasta']}</td></tr>
   <tr><td>objetivo / stop</td><td>{r['k_tp']} ATR / {r['k_sl']} ATR,
       {r['horizonte_dias']} dias</td></tr>
  </table></div>
 <div class="av"><b>En prueba.</b> {r['aviso']}</div>
 <div class="caja" style="font-size:12px;color:#68697A">
  Todo esto en JSON: <a href="/regla_diaria.json">/regla_diaria.json</a>
 </div>
</div></body></html>"""


@app.get("/regla_diaria.json")
def regla_diaria_json(consultas: int = 20):
    """Todo el estado de la regla diaria en JSON, para poder consumirlo desde
    otro programa o guardarlo como reporte.

    Trae la definicion de la regla, sus resultados de validacion, un resumen de
    las consultas que hizo el EA y las ultimas `consultas` en detalle."""
    r = _leer_regla()
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if r is None:
        return dict(generado_en=ahora, hay_regla=False,
                    motivo="falta regla_diaria.json; generarlo con "
                           "analisis/generar_regla.py")

    hist = []
    if REGLA_LOG.exists():
        for linea in open(REGLA_LOG, encoding="utf-8"):
            try:
                hist.append(json.loads(linea))
            except json.JSONDecodeError:
                continue

    activas = [c for c in hist if c.get("activa")]
    dias = sorted({str(c.get("fecha_vela", ""))[:10] for c in hist if c.get("fecha_vela")})

    # cuantas veces se cumplio cada condicion por separado: si una nunca se
    # cumple, el cuello de botella esta ahi
    por_condicion = {}
    for c in hist:
        for nombre, d in (c.get("condiciones") or {}).items():
            e = por_condicion.setdefault(nombre, {"cumple": 0, "total": 0})
            e["total"] += 1
            e["cumple"] += int(bool(d.get("ok")))

    return dict(
        generado_en=ahora,
        hay_regla=True,
        regla=dict(
            symbol=r["symbol"], timeframe=r["timeframe"], lado=r["lado"],
            k_tp=r["k_tp"], k_sl=r["k_sl"], horizonte_dias=r["horizonte_dias"],
            condiciones=r["condiciones"],
        ),
        entrenamiento=dict(
            archivo=r["entrenado_con"], desde=r["desde"], hasta=r["hasta"],
            velas=r["velas_entrenamiento"], generado_en=r["generado_en"],
        ),
        validacion=r["resultados_validacion"],
        actividad=dict(
            consultas=len(hist),
            veces_activa=len(activas),
            dias_distintos=len(dias),
            primer_dia=dias[0] if dias else None,
            ultimo_dia=dias[-1] if dias else None,
            por_condicion={k: dict(v, pct=round(v["cumple"] / v["total"], 4))
                           for k, v in por_condicion.items() if v["total"]},
        ),
        ultima=hist[-1] if hist else None,
        ultimas_consultas=hist[-int(consultas):] if int(consultas) > 0 else [],
        aviso=r["aviso"],
    )


# =======================================================================
# ENTORNO DE PRUEBA -- NAS100 en 5 minutos, separado de todo lo demas
#
# Mismo modelo y misma logica que /predict, pero con sus propios archivos y
# su propia pantalla, para que los resultados NO se mezclen con los del
# sistema que ya venia corriendo.
#
#   prueba/predict           igual que /predict, solo NAS100
#   prueba/registrar_cierre  igual que /registrar_cierre, archivo aparte
#   prueba/reporte.html      pantalla propia
#   prueba/resumen.json      lo mismo en JSON
#
# Recordatorio: el modelo de 5 minutos no tiene ventaja demostrada (AUC
# promedio 0,497 sobre un año de datos limpios). Esto existe para MEDIR en
# un entorno aislado, no porque se espere que gane.
# =======================================================================

PRUEBA_SIMBOLOS = ["NAS100", "BTCUSD"]
PRUEBA_SIMBOLO = PRUEBA_SIMBOLOS[0]   # compatibilidad
PRUEBA_PRED_PATH = Path("datos/operaciones/prueba_predicciones.jsonl")
PRUEBA_CIERRES_PATH = Path("datos/operaciones/prueba_cierres.jsonl")
PRUEBA_DESDE = "2026-09-30"   # fecha de arranque del entorno de prueba

# El entorno corre en OTRA cuenta, con su propio capital. No se usa
# CAPITAL_REFERENCIA (22.067), que es el del sistema de siempre.
CAPITAL_PRUEBA = 47330.0

# Operaciones a dejar FUERA del calculo, por ticket.
# 258152884: salio con 2.80 lotes por un error de configuracion, cuando el
# resto va con 0.10. Peso 28 veces mas que las demas y dio +49.00, que era
# practicamente todo el resultado acumulado. Dejarla adentro hace parecer que
# el sistema gana cuando en realidad esta en cero.
PRUEBA_EXCLUIR_TICKETS = [258152884]

# Factor que se le aplica al OBJETIVO en el entorno de prueba. El stop no se
# toca. En 1.0 se usa el objetivo tal cual lo devuelve el modelo.
#
# POR QUE EXISTE: el modelo v6 de NAS100 venta usa objetivo 8 ATR contra stop
# 3 ATR. Con un ATR de 20 puntos el objetivo queda a 160: la operacion espera
# horas un movimiento que rara vez llega, y el acierto cae al 27%.
#
# LA CUENTA QUE HAY QUE TENER EN CUENTA: el acierto necesario para no perder
# es k_sl / (k_tp + k_sl). Para NAS100 venta, con el stop fijo en 3 ATR:
#
#     factor 1.00 -> objetivo 8 ATR -> hace falta 27%   (el modelo da 26.7%)
#     factor 0.75 -> objetivo 6 ATR -> hace falta 33%
#     factor 0.50 -> objetivo 4 ATR -> hace falta 43%
#     factor 0.25 -> objetivo 2 ATR -> hace falta 60%
#
# Recortar el objetivo sube el acierto, porque el precio llega mas seguido.
# Pero si no sube HASTA el nuevo umbral, se pierde mas rapido que antes.
#
# Se arranca en 0.75 y no en 0.50 a proposito: con 0.50 habria que pasar de
# 26.7% a 43%, que son 16 puntos de mejora. Con 0.75 hacen falta 6, que es
# mucho mas alcanzable, y las operaciones igual cierran bastante antes.
# Si en unas semanas el acierto queda comodo por encima de 33%, ahi si tiene
# sentido bajar a 0.50 y ver si aguanta el 43%. Al reves no sirve: arrancando
# en 0.50, si pierde no se sabe si fue el recorte o el modelo.
# El factor va POR SIMBOLO, porque cada uno tiene su propia combinacion de
# objetivo y stop y el mismo recorte les hace cosas distintas:
#
#   NAS100 venta   objetivo 8 / stop 3 -> hace falta 27%. Con 0.75 -> 33%.
#                  El modelo daba 26.7%, asi que 27% era inalcanzable y el
#                  recorte tiene sentido.
#
#   BTCUSD compra  objetivo 6 / stop 3 -> hace falta 33%, y el modelo da 34.6%
#   BTCUSD venta   objetivo 2 / stop 2 -> hace falta 50%, y el modelo da 50.9%
#                  Los dos estan JUSTO al filo. Con 0.75 los umbrales subirian
#                  a 40% y 57%, y quedarian claramente por debajo. Por eso
#                  BTCUSD arranca sin recorte.
FACTOR_TP_POR_SIMBOLO = {"NAS100": 0.75, "BTCUSD": 1.0}
FACTOR_TP_PRUEBA = 0.75   # usado si el simbolo no esta en la tabla de arriba


def _factor_tp(symbol):
    return FACTOR_TP_POR_SIMBOLO.get(symbol.upper(), FACTOR_TP_PRUEBA)


def _leer_jsonl(ruta):
    filas = []
    if ruta.exists():
        for linea in open(ruta, encoding="utf-8"):
            try:
                filas.append(json.loads(linea))
            except json.JSONDecodeError:
                continue
    return filas


@app.get("/prueba/predict")
def prueba_predict(
    symbol: str = Query(...), fecha: str = Query(...), c5: float = Query(...),
    ema550: float = Query(...), ema5200: float = Query(...),
    macdLine5: float = Query(...), signalLine5: float = Query(...),
    adx5: float = Query(...), diPlus5: float = Query(...),
    diMinus5: float = Query(...), r5: float = Query(...), r15: float = Query(...),
    m5: float = Query(...), s5: float = Query(...), m15: float = Query(...),
    s15: float = Query(...), atr5: float = Query(...),
    h5: float = Query(None), l5: float = Query(None), v5: float = Query(None),
    v5ma20: float = Query(None), c5d: float = Query(None),
    todos_los_lados: bool = True,
    factor_tp: float = None,
):
    """Reusa /predict tal cual -- misma logica, mismo modelo -- y ademas deja
    su propio registro. No se duplica el codigo del modelo a proposito: si se
    duplicara, los dos podrian empezar a diferir sin que nadie lo note."""
    if symbol.upper() not in PRUEBA_SIMBOLOS:
        logger.info(f"prueba/predict rechazado: {symbol} "
                    f"(solo {', '.join(PRUEBA_SIMBOLOS)})")
        return {"valor_profit": 0.0, "RESULTADO": "NADA", "tp": 0.0, "sl": 0.0,
                "motivo": f"el entorno de prueba es solo para "
                          f"{', '.join(PRUEBA_SIMBOLOS)}"}

    r = predict(symbol=symbol, fecha=fecha, c5=c5, ema550=ema550, ema5200=ema5200,
                macdLine5=macdLine5, signalLine5=signalLine5, adx5=adx5,
                diPlus5=diPlus5, diMinus5=diMinus5, r5=r5, r15=r15, m5=m5, s5=s5,
                m15=m15, s15=s15, atr5=atr5, h5=h5, l5=l5, v5=v5, v5ma20=v5ma20,
                c5d=c5d, todos_los_lados=todos_los_lados)

    # recorte del objetivo: solo el tp, el stop queda como lo dio el modelo
    f = _factor_tp(symbol) if factor_tp is None else float(factor_tp)
    tp_original = r.get("tp", 0.0)
    if f != 1.0 and tp_original:
        r = dict(r, tp=_redondear_precio(tp_original * f), tp_sin_recorte=tp_original,
                 factor_tp=f)
        logger.info(f"PRUEBA {symbol.upper()} recorte x{f}: {tp_original} -> {r['tp']} "
                    f"(stop {r.get('sl')} sin cambios)")
    try:
        PRUEBA_PRED_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PRUEBA_PRED_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(
                symbol=symbol.upper(), fecha_vela=fecha,
                resultado=r.get("RESULTADO"), prob=r.get("valor_profit"),
                tp=r.get("tp"), sl=r.get("sl"), atr=round(atr5, 6),
                tp_sin_recorte=r.get("tp_sin_recorte"), factor_tp=r.get("factor_tp"),
                registrado_en=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ), ensure_ascii=False) + "\n")
    except OSError as e:
        logger.error(f"no se pudo escribir {PRUEBA_PRED_PATH}: {e}")
    return r


@app.get("/prueba/registrar_cierre")
def prueba_registrar_cierre(
    ticket: int = Query(...), symbol: str = Query(...), tipo: str = Query(...),
    fecha_apertura: str = Query(...), precio_apertura: float = Query(...),
    fecha_cierre: str = Query(...), precio_cierre: float = Query(...),
    sl: float = 0.0, tp: float = 0.0, profit: float = 0.0,
):
    """Mismo formato que /registrar_cierre pero en su propio archivo.

    Los tres ultimos van con valor por defecto simple y no con Query(), para
    que la funcion tambien se pueda llamar directamente desde un script de
    prueba sin que FastAPI resuelva los parametros."""
    PRUEBA_CIERRES_PATH.parent.mkdir(parents=True, exist_ok=True)
    for c in _leer_jsonl(PRUEBA_CIERRES_PATH):
        if c.get("ticket") == ticket:
            return {"ok": True, "duplicado": True}

    signo = 1 if tipo.upper() == "BUY" else -1
    registro = dict(
        ticket=ticket, symbol=symbol.upper(), tipo=tipo.upper(),
        fecha_apertura=fecha_apertura, precio_apertura=precio_apertura,
        fecha_cierre=fecha_cierre, precio_cierre=precio_cierre,
        sl=sl, tp=tp, profit=profit,
        puntos=signo * (precio_cierre - precio_apertura),
        registrado_en=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    with open(PRUEBA_CIERRES_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(registro, ensure_ascii=False) + "\n")
    logger.info(f"PRUEBA cierre #{ticket} {tipo.upper()} profit={profit}")
    return {"ok": True}


def _prueba_umbrales(preds):
    """Acierto que hace falta en cada simbolo y lado para no perder.

    Sale de la relacion REAL entre objetivo y stop que devolvio la API, no de
    la que tiene el modelo: con el recorte del objetivo y los minimos que
    impone el broker, la relacion que termina operando puede ser otra.

    La cuenta es: stop / (objetivo + stop). Si el objetivo esta al doble del
    stop, cada acierto paga dos y cada fallo cuesta uno, asi que alcanza con
    acertar un tercio de las veces para quedar en cero."""
    razon = {}
    for p_ in preds:
        if p_.get("resultado") not in ("BUY", "SELL"):
            continue
        tp_, sl_ = p_.get("tp") or 0, p_.get("sl") or 0
        if tp_ > 0 and sl_ > 0:
            k = (str(p_.get("symbol", "")).upper(),
                 "Compra" if p_["resultado"] == "BUY" else "Venta")
            razon.setdefault(k, []).append(tp_ / sl_)
    out = {}
    for k, v in razon.items():
        r_ = sorted(v)[len(v) // 2]          # mediana
        out[k] = dict(razon=r_, umbral=1.0 / (r_ + 1.0))
    return out


def _prueba_resumen():
    todos = _leer_jsonl(PRUEBA_CIERRES_PATH)
    cierres = [c for c in todos if c.get("ticket") not in PRUEBA_EXCLUIR_TICKETS]
    preds = _leer_jsonl(PRUEBA_PRED_PATH)
    por_lado, por_dia, por_simbolo = {}, {}, {}
    for c in cierres:
        lado = "Compra" if str(c.get("tipo", "")).upper() == "BUY" else "Venta"
        sim = str(c.get("symbol", "")).upper()
        gano = float(c.get("puntos", 0) or 0) > 0
        prof = float(c.get("profit", 0) or 0)
        for clave, d in ((f"{sim} {lado}", por_lado),
                         (str(c.get("fecha_cierre", ""))[:10], por_dia),
                         (sim, por_simbolo)):
            e = d.setdefault(clave, {"n": 0, "ganadas": 0, "usd": 0.0})
            e["n"] += 1; e["ganadas"] += int(gano); e["usd"] += prof
    total = {"n": len(cierres),
             "ganadas": sum(1 for c in cierres
                            if float(c.get("puntos", 0) or 0) > 0),
             "usd": sum(float(c.get("profit", 0) or 0) for c in cierres)}
    señales = sum(1 for p in preds if p.get("resultado") in ("BUY", "SELL"))
    return dict(cierres=cierres, por_lado=por_lado, por_dia=por_dia,
                por_simbolo=por_simbolo, total=total, consultas=len(preds),
                señales=señales, umbrales=_prueba_umbrales(preds),
                excluidos=len(todos) - len(cierres))


@app.get("/prueba/resumen.json")
def prueba_resumen_json():
    r = _prueba_resumen()
    r.pop("cierres")
    return dict(generado_en=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                symbols=PRUEBA_SIMBOLOS, desde=PRUEBA_DESDE,
                factor_tp=FACTOR_TP_POR_SIMBOLO,
                capital_referencia=CAPITAL_PRUEBA,
                tickets_excluidos=PRUEBA_EXCLUIR_TICKETS,
                pct_capital=round(r["total"]["usd"] / CAPITAL_PRUEBA * 100, 4),
                **r)


@app.get("/prueba/reporte.html", response_class=HTMLResponse)
def prueba_reporte():
    r = _prueba_resumen()
    t = r["total"]
    wr = (t["ganadas"] / t["n"] * 100) if t["n"] else 0.0
    pct = t["usd"] / CAPITAL_REFERENCIA * 100 if CAPITAL_REFERENCIA else 0.0

    def color(u):
        return "#1B7F4B" if u > 0 else ("#C0392B" if u < 0 else "#8A8C9E")

    filas_sim = "".join(
        f"<tr><td>{k}</td><td>{d['n']}</td>"
        f"<td>{d['ganadas'] / d['n']:.0%}</td>"
        f"<td style='color:{color(d['usd'])}'>{d['usd']:+,.2f}</td></tr>"
        for k, d in sorted(r["por_simbolo"].items())) or \
        "<tr><td colspan=4>todavia no hay operaciones cerradas</td></tr>"

    filas_lado = "".join(
        f"<tr><td>{k}</td><td>{d['n']}</td>"
        f"<td>{d['ganadas'] / d['n']:.0%}</td>"
        f"<td style='color:{color(d['usd'])}'>{d['usd']:+,.2f}</td>"
        f"<td style='color:{color(d['usd'])}'>"
        f"{d['usd'] / CAPITAL_REFERENCIA * 100:+.2f}%</td></tr>"
        for k, d in sorted(r["por_lado"].items())) or \
        "<tr><td colspan=5>todavia no hay operaciones cerradas</td></tr>"

    filas_dia = "".join(
        f"<tr><td>{k}</td><td>{d['n']}</td>"
        f"<td>{d['ganadas'] / d['n']:.0%}</td>"
        f"<td style='color:{color(d['usd'])}'>{d['usd']:+,.2f}</td></tr>"
        for k, d in sorted(r["por_dia"].items(), reverse=True)[:20]) or \
        "<tr><td colspan=4>sin dias registrados</td></tr>"

    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>Prueba M5</title><style>
 body{{font-family:-apple-system,'Segoe UI',Calibri,sans-serif;margin:0;
      padding:24px;color:#3A3A3A;background:#F4F5FA}}
 .c{{max-width:900px;margin:0 auto}}
 .cab{{background:linear-gradient(135deg,#4A1B4D,#6B2761);color:#fff;
      padding:22px 26px;border-radius:14px}}
 .cab h2{{margin:0;font-size:19px}} .cab p{{margin:6px 0 0;font-size:12px;opacity:.8}}
 .caja{{background:#fff;border-radius:14px;padding:18px 22px;margin-top:16px;
       box-shadow:0 4px 18px rgba(30,39,97,.08)}}
 h3{{font-size:14px;margin:0 0 10px;color:#4A1B4D}}
 table{{border-collapse:collapse;width:100%;font-size:12.5px}}
 th,td{{padding:7px 10px;text-align:left;border-bottom:1px solid #EDEEF5}}
 th{{color:#68697A;font-weight:600;font-size:11px}}
 .big{{font-size:26px;font-weight:800}}
 .av{{background:#FFF6DE;border-left:4px solid #F2B134;padding:12px 16px;
     font-size:12px;border-radius:0 8px 8px 0;margin-top:16px;line-height:1.6}}
</style></head><body><div class="c">
 <div class="cab"><h2>Entorno de prueba — {' y '.join(PRUEBA_SIMBOLOS)} en 5 minutos</h2>
  <p>Separado del sistema principal · desde el {PRUEBA_DESDE} ·
  actualizado el {ahora}</p></div>
 <div class="caja"><h3>Resultado acumulado</h3>
  <div class="big" style="color:{color(t['usd'])}">{t['usd']:+,.2f} USD
   &nbsp;<span style="font-size:16px">({pct:+.2f}%)</span></div>
  <p style="font-size:12px;color:#68697A;margin:8px 0 0">
   {t['n']} operaciones cerradas · acierto {wr:.1f}% ·
   {r['consultas']} consultas, {r['señales']} con señal ·
   sobre un capital de referencia de {CAPITAL_REFERENCIA:,.0f} USD</p></div>
 <div class="caja"><h3>Por simbolo</h3>
  <table><tr><th>simbolo</th><th>operaciones</th><th>acierto</th><th>USD</th></tr>
  {filas_sim}</table></div>
 <div class="caja"><h3>Por simbolo y lado</h3>
  <table><tr><th>lado</th><th>operaciones</th><th>acierto</th><th>USD</th>
  <th>% del capital</th></tr>{filas_lado}</table></div>
 <div class="caja"><h3>Ultimos dias</h3>
  <table><tr><th>dia</th><th>operaciones</th><th>acierto</th><th>USD</th></tr>
  {filas_dia}</table></div>
 <div class="caja"><h3>Recorte del objetivo</h3>
  <p style="font-size:12.5px;line-height:1.7;margin:0">
   El objetivo se esta recortando a <b>{FACTOR_TP_PRUEBA:g}</b> veces lo que
   devuelve el modelo. El stop no se toca.<br>
   El acierto necesario para no perder es <b>stop / (objetivo + stop)</b>.
   El recorte va por simbolo: {', '.join(f'{k} x{v:g}' for k, v in FACTOR_TP_POR_SIMBOLO.items())}.<br>
   El acierto necesario para no perder es <b>stop / (objetivo + stop)</b>:<br>
   <b>NAS100 venta</b> sin recorte era 8/3 y hacia falta 27%; con 0,75 queda
   6/3 y hace falta <b>33%</b>. El modelo venia dando 26,7%.<br>
   <b>BTCUSD</b> va sin recorte: compra 6/3 necesita 33% y el modelo da 34,6%;
   venta 2/2 necesita 50% y da 50,9%. Los dos estan al filo, asi que recortar
   los dejaria claramente por debajo.<br>
   <b>Comparar el acierto de cada fila contra su umbral es lo que decide.</b>
   </p></div>
 <div class="av"><b>Esto es una medicion, no una estrategia.</b>
  El modelo de 5 minutos no tiene ventaja demostrada: se midio siete veces, en
  cinco mercados, con un año de datos limpios y hasta 38 variables, y el AUC
  promedio dio 0,497, que es exactamente una moneda. Este entorno existe para
  medir en aislado con lote minimo.</div>
 <div class="caja" style="font-size:12px;color:#68697A">
  Lo mismo en JSON: <a href="/prueba/resumen.json">/prueba/resumen.json</a></div>
</div></body></html>"""


@app.get("/prueba/diario.html", response_class=HTMLResponse)
def prueba_diario():
    """Winrate DIA POR DIA del entorno de prueba, por simbolo y lado.

    Mismo formato que la pestaña Diario del sistema principal, con una
    diferencia: el COLOR no sale del winrate crudo sino de compararlo contra
    el acierto que esa fila necesita para no perder.

    El motivo es que el winrate solo no dice si se esta ganando. Si el
    objetivo esta a 1,45 veces el stop, con 41% ya se empata; con 48% se gana
    bien. Pero si objetivo y stop estan a la misma distancia, hace falta 50%
    y ese mismo 48% pierde. Pintar por el numero crudo hace que las dos cosas
    se vean iguales, que es justamente lo que confunde al leer la tabla.

    Asi, una celda verde significa 'esta ganando' y una roja 'esta perdiendo',
    que es la pregunta que la tabla tiene que responder."""
    r = _prueba_resumen()
    cierres = r["cierres"]
    if not cierres:
        return ('<!DOCTYPE html><html><head><meta charset="UTF-8"></head>'
                '<body style="font-family:-apple-system,Segoe UI,Calibri,sans-serif;'
                f'padding:40px;color:#68697A">Todavia no hay operaciones cerradas '
                f'en el entorno de prueba.</body></html>')

    um = r["umbrales"]
    celdas, dias, claves = {}, set(), set()
    for c in cierres:
        dia = str(c.get("fecha_cierre", ""))[:10]
        if len(dia) != 10:
            continue
        lado = "Compra" if str(c.get("tipo", "")).upper() == "BUY" else "Venta"
        k = (str(c["symbol"]).upper(), lado)
        celdas.setdefault((k, dia), []).append(c)
        dias.add(dia); claves.add(k)
    dias, claves = sorted(dias), sorted(claves)

    # Con menos de 3 operaciones el winrate no significa nada: 0% de una sola
    # operacion se veria igual de rojo que 0% de veinte. Esas celdas van gris.
    MIN_PARA_COLOR = 3

    def estilo(pct, n, umbral):
        """pct y umbral en porcentaje. El color sale de la DIFERENCIA."""
        if n < MIN_PARA_COLOR or umbral is None:
            return "background:#F4F5FA;color:#8A8C9E"
        d = pct - umbral
        if d >= 10:  return "background:#1B7F4B;color:#FFFFFF"
        if d >= 3:   return "background:#4FA97B;color:#FFFFFF"
        if d >= -3:  return "background:#F2B134;color:#3A3A3A"
        if d >= -10: return "background:#E08A3C;color:#FFFFFF"
        return "background:#C0392B;color:#FFFFFF"

    filas = []
    acum_usd, acum_n = 0.0, 0
    por_dia_usd = {d: 0.0 for d in dias}
    por_dia_n = {d: 0 for d in dias}
    por_dia_g = {d: 0 for d in dias}

    for k in claves:
        sym, lado = k
        u = um.get(k)
        umbral = u["umbral"] * 100 if u else None
        tds = []
        tot_n = tot_g = 0
        tot_prof = 0.0
        for d in dias:
            ops = celdas.get((k, d), [])
            if not ops:
                tds.append('<td class="vacia">—</td>')
                continue
            n = len(ops)
            g = sum(1 for o in ops if float(o.get("puntos", 0) or 0) > 0)
            prof = sum(float(o.get("profit", 0) or 0) for o in ops)
            tot_n += n; tot_g += g; tot_prof += prof
            por_dia_usd[d] += prof; por_dia_n[d] += n; por_dia_g[d] += g
            pct = g / n * 100
            tds.append(f'<td style="{estilo(pct, n, umbral)}"><b>{pct:.0f}%</b>'
                       f'<span class="n">n={n}</span>'
                       f'<span class="p">{prof:+,.2f}</span></td>')
        if tot_n == 0:
            continue
        acum_usd += tot_prof; acum_n += tot_n
        pct_tot = tot_g / tot_n * 100
        etq_um = (f'<span>necesita {umbral:.0f}%</span>' if umbral is not None
                  else '<span>sin referencia</span>')
        filas.append(
            f'<tr><th class="lbl">{sym} {lado}{etq_um}</th>' + "".join(tds)
            + f'<td class="tot" style="{estilo(pct_tot, tot_n, umbral)}">'
              f'<b>{pct_tot:.0f}%</b><span class="n">n={tot_n}</span>'
              f'<span class="p">{tot_prof:+,.2f}</span></td></tr>')

    # fila de cierre: el resultado de cada dia sumando todo
    tds_dia = []
    for d in dias:
        n = por_dia_n[d]
        if n == 0:
            tds_dia.append('<td class="vacia">—</td>')
            continue
        usd = por_dia_usd[d]
        col = "#1B7F4B" if usd > 0 else ("#C0392B" if usd < 0 else "#8A8C9E")
        tds_dia.append(f'<td class="dia"><b>{por_dia_g[d]/n*100:.0f}%</b>'
                       f'<span class="n">n={n}</span>'
                       f'<span class="p" style="color:{col}">{usd:+,.2f}</span></td>')
    col_t = "#1B7F4B" if acum_usd > 0 else ("#C0392B" if acum_usd < 0 else "#8A8C9E")
    fila_dia = (f'<tr><th class="lbl">TODO JUNTO<span>el dia completo</span></th>'
                + "".join(tds_dia)
                + f'<td class="tot dia"><b>{acum_usd:+,.2f}</b>'
                  f'<span class="n">n={acum_n}</span>'
                  f'<span class="p" style="color:{col_t}">'
                  f'{acum_usd/CAPITAL_PRUEBA*100:+.2f}%</span></td></tr>')

    enc = "".join(f'<th>{d[8:10]}-{MESES[int(d[5:7])]}</th>' for d in dias)
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    nota_exc = (f" · {r['excluidos']} operacion excluida por tamaño erroneo"
                if r.get("excluidos") else "")

    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<style>
  body {{ font-family:-apple-system,'Segoe UI',Calibri,sans-serif; margin:0;
         padding:0; color:#3A3A3A; background:transparent; }}
  .cab {{ background:linear-gradient(135deg,#4A1B4D,#6B2761); color:white;
          padding:22px 26px; border-radius:14px 14px 0 0; }}
  .cab h2 {{ margin:0; font-size:19px; font-weight:700; }}
  .cab p {{ margin:6px 0 0; font-size:11.5px; opacity:.78; }}
  .ley {{ font-size:10.5px; color:#68697A; padding:10px 4px 8px; line-height:1.8; }}
  .ley i {{ display:inline-block; width:11px; height:11px; border-radius:3px;
            margin:0 4px 0 12px; vertical-align:-1px; }}
  .caja {{ overflow-x:auto; background:white; border-radius:0 0 14px 14px;
           box-shadow:0 4px 18px rgba(74,27,77,.09); }}
  table {{ border-collapse:collapse; font-size:11.5px; white-space:nowrap;
           width:100%; }}
  th, td {{ padding:8px 10px; text-align:center; border:1px solid #EDEEF5; }}
  thead th {{ background:#4A1B4D; color:white; font-size:10px; font-weight:600; }}
  thead th.total {{ background:#2E0F30; }}
  th.lbl {{ background:#F6F1F7; color:#4A1B4D; text-align:left; font-weight:700;
            position:sticky; left:0; z-index:2; min-width:132px; }}
  th.lbl span {{ display:block; font-weight:400; font-size:10px; color:#8A6B8C; }}
  thead th.lbl {{ background:#4A1B4D; color:white; }}
  td b {{ font-size:13px; }}
  td .n {{ display:block; font-size:9px; opacity:.75; }}
  td .p {{ display:block; font-size:9.5px; font-weight:700; }}
  td.tot {{ border-left:3px solid #2E0F30; }}
  td.vacia {{ color:#D2D4E0; background:#FBFBFD; }}
  td.dia {{ background:#F6F1F7; color:#4A1B4D; }}
  tr:last-child th.lbl {{ background:#EDE3EF; }}
  .pie {{ font-size:11px; color:#68697A; padding:12px 4px 0; line-height:1.7; }}
</style></head><body>
  <div class="cab">
    <h2>Diario de la prueba — winrate por simbolo y lado, dia por dia</h2>
    <p>Desde el {PRUEBA_DESDE} · {acum_n} operaciones · {len(dias)} dias ·
    calculado en vivo el {ahora}{nota_exc}</p>
  </div>
  <div class="ley">
    El numero grande es el <b>winrate del dia</b>. Debajo van las operaciones y
    el resultado en dolares.<br>
    El <b>color</b> compara ese winrate contra el que esa fila necesita para no
    perder (figura al lado del nombre):
    <i style="background:#1B7F4B"></i>10 puntos o mas por encima
    <i style="background:#4FA97B"></i>por encima
    <i style="background:#F2B134"></i>en el limite
    <i style="background:#E08A3C"></i>por debajo
    <i style="background:#C0392B"></i>10 puntos o mas por debajo
    <i style="background:#F4F5FA;border:1px solid #EDEEF5"></i>menos de 3 operaciones
  </div>
  <div class="caja"><table>
    <thead><tr><th class="lbl">Simbolo / Lado</th>{enc}
      <th class="total">TOTAL</th></tr></thead>
    <tbody>{''.join(filas)}{fila_dia}</tbody>
  </table></div>
  <div class="pie">
    <b>Por que el color no sale del winrate solo.</b> Un 44% puede estar ganando
    o perdiendo segun cuanto se cobre al acertar. Si el objetivo esta a 1,45
    veces el stop, con 41% ya se empata. Si objetivo y stop estan a la misma
    distancia, hace falta 50%. Por eso cada fila trae su propio numero y el
    color sale de la diferencia: <b>verde es ganando, rojo es perdiendo</b>.<br>
    Capital de esta cuenta: {CAPITAL_PRUEBA:,.0f} USD.
  </div>
</body></html>"""


# =======================================================================
# NEO_SELECTIVO -- pestaña propia (agregado el 30-oct-2026)
#
# NEO_SELECTIVO reporta sus cierres a /selectivo/registrar_cierre, que escribe
# en SU PROPIO archivo. Hace falta porque cierres.jsonl y prueba_cierres.jsonl
# no guardan el magic number: si dos EAs operan el mismo simbolo, sus
# operaciones quedan mezcladas y no hay forma de separarlas despues.
#
#   selectivo/registrar_cierre   lo llama NEO_SELECTIVO al cerrar una operacion
#   selectivo/reporte.html       la pestaña "NEO Selectivo"
#   selectivo/resumen.json       lo mismo en JSON
#
# El veredicto de cada pata sigue la regla fijada ANTES de ver datos nuevos:
# no se juzga hasta tener SEL_N_MIN operaciones, y despues se mantiene solo si
# p < SEL_ALFA (permutacion de signos sobre R, unilateral). Con 6 patas
# prendidas, alfa = 0.05 / 6. Si cambia la cantidad de patas, cambiar SEL_ALFA
# y SEL_N_MIN a la vez.
#
# R = resultado en puntos / distancia al stop. No depende del lote, que es lo
# que hace que el USD enganie: con lote fijo y stop variable, unas pocas
# operaciones de stop ancho dominan el total en dolares.
# =======================================================================

SEL_CIERRES_PATH = Path("datos/operaciones/selectivo_cierres.jsonl")
SEL_DESDE = "2026-10-25"      # dia en que se prendio NEO_SELECTIVO
SEL_N_MIN = 440               # operaciones por pata antes de dar veredicto
SEL_ALFA = 0.05 / 6           # umbral de p por pata (correccion por 6 patas)
CAPITAL_SELECTIVO = 0.0       # capital de la cuenta; si es > 0 se muestra el % tambien


@app.get("/selectivo/registrar_cierre")
def selectivo_registrar_cierre(
    ticket: int = Query(...), symbol: str = Query(...), tipo: str = Query(...),
    fecha_apertura: str = Query(...), precio_apertura: float = Query(...),
    fecha_cierre: str = Query(...), precio_cierre: float = Query(...),
    sl: float = 0.0, tp: float = 0.0, profit: float = 0.0,
):
    """Mismo formato que /registrar_cierre, en el archivo de NEO_SELECTIVO."""
    SEL_CIERRES_PATH.parent.mkdir(parents=True, exist_ok=True)
    for c in _leer_jsonl(SEL_CIERRES_PATH):
        if c.get("ticket") == ticket:
            return {"ok": True, "duplicado": True}

    signo = 1 if tipo.upper() == "BUY" else -1
    registro = dict(
        ticket=ticket, symbol=symbol.upper(), tipo=tipo.upper(),
        fecha_apertura=fecha_apertura, precio_apertura=precio_apertura,
        fecha_cierre=fecha_cierre, precio_cierre=precio_cierre,
        sl=sl, tp=tp, profit=profit,
        puntos=signo * (precio_cierre - precio_apertura),
        registrado_en=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    with open(SEL_CIERRES_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(registro, ensure_ascii=False) + "\n")
    logger.info(f"SELECTIVO cierre #{ticket} {symbol.upper()} {tipo.upper()} profit={profit}")
    return {"ok": True, "duplicado": False}


def _sel_cierres():
    """Cierres de NEO_SELECTIVO, sin tickets repetidos, desde SEL_DESDE, con R y
    razon objetivo/stop calculados."""
    vistos, out = set(), []
    for c in _leer_jsonl(SEL_CIERRES_PATH):
        t = c.get("ticket")
        if t in vistos:
            continue
        vistos.add(t)
        if str(c.get("fecha_apertura", ""))[:10] < SEL_DESDE:
            continue
        try:
            e = float(c["precio_apertura"])
            s = float(c.get("sl") or 0)
            tp = float(c.get("tp") or 0)
            pts = float(c.get("puntos") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        dist = abs(e - s)
        c = dict(c)
        c["R"] = pts / dist if (dist > 0 and s > 0) else None
        c["rr"] = abs(tp - e) / dist if (dist > 0 and s > 0 and tp > 0) else None
        out.append(c)
    return out


def _sel_p_permutacion(R):
    """p unilateral: que tan seguido un R medio igual o mayor sale con el signo
    de cada operacion al azar (sin ventaja). Semilla fija: la misma pagina da el
    mismo p cada vez."""
    import numpy as np
    r = np.asarray(R, dtype=float)
    sorteos = int(max(500, min(5000, 2_000_000 // max(len(r), 1))))
    rng = np.random.default_rng(11)
    signos = rng.choice([-1.0, 1.0], size=(sorteos, len(r)))
    return float(((signos * np.abs(r)).mean(axis=1) >= r.mean()).mean())


def _sel_resumen():
    cierres = _sel_cierres()
    grupos = {}
    for c in cierres:
        lado = "Compra" if str(c.get("tipo", "")).upper() == "BUY" else "Venta"
        grupos.setdefault((str(c.get("symbol", "")).upper(), lado), []).append(c)

    patas = []
    for (sim, lado), ops in sorted(grupos.items()):
        n = len(ops)
        g = sum(1 for o in ops if float(o.get("puntos", 0) or 0) > 0)
        usd = sum(float(o.get("profit", 0) or 0) for o in ops)
        Rs = [o["R"] for o in ops if o["R"] is not None]
        rrs = sorted(o["rr"] for o in ops if o["rr"] is not None)
        necesita = (100.0 / (rrs[len(rrs) // 2] + 1.0)) if rrs else None
        r_medio = (sum(Rs) / len(Rs)) if Rs else None
        p = veredicto = None
        if len(Rs) >= SEL_N_MIN:
            p = _sel_p_permutacion(Rs)
            veredicto = "MANTENER" if p < SEL_ALFA else "DESCARTAR"
        patas.append(dict(symbol=sim, lado=lado, n=n, ganadas=g,
                          winrate=g / n * 100, necesita=necesita, usd=usd,
                          r_medio=r_medio, p=p, veredicto=veredicto,
                          avance=min(n / SEL_N_MIN, 1.0)))

    Rtot = [c["R"] for c in cierres if c["R"] is not None]
    total = dict(n=len(cierres),
                 ganadas=sum(1 for c in cierres if float(c.get("puntos", 0) or 0) > 0),
                 usd=sum(float(c.get("profit", 0) or 0) for c in cierres),
                 r_medio=(sum(Rtot) / len(Rtot)) if Rtot else None)
    return dict(cierres=cierres, patas=patas, total=total)


@app.get("/selectivo/resumen.json")
def selectivo_resumen_json():
    r = _sel_resumen()
    r.pop("cierres")
    return dict(generado_en=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                desde=SEL_DESDE, n_min=SEL_N_MIN, alfa=round(SEL_ALFA, 6), **r)


_SEL_CSS = """
 body{font-family:-apple-system,'Segoe UI',Calibri,sans-serif;margin:0;padding:24px;
      color:#3A3A3A;background:#F4F5FA}
 .c{max-width:1100px;margin:0 auto}
 .cab{background:linear-gradient(135deg,#0F4C5C,#16697A);color:#fff;padding:22px 26px;
      border-radius:14px}
 .cab h2{margin:0;font-size:19px} .cab p{margin:6px 0 0;font-size:12px;opacity:.8}
 .caja{background:#fff;border-radius:14px;padding:18px 22px;margin-top:16px;
       box-shadow:0 4px 18px rgba(15,76,92,.09);overflow-x:auto}
 h3{font-size:14px;margin:0 0 10px;color:#0F4C5C}
 table{border-collapse:collapse;width:100%;font-size:12.5px}
 th,td{padding:7px 10px;text-align:left;border-bottom:1px solid #EDEEF5}
 th{color:#68697A;font-weight:600;font-size:11px}
 .big{font-size:26px;font-weight:800}
 .av{background:#FFF6DE;border-left:4px solid #F2B134;padding:12px 16px;font-size:12px;
     border-radius:0 8px 8px 0;margin-top:16px;line-height:1.6}
 .barra{display:inline-block;width:90px;height:8px;background:#EDEEF5;border-radius:4px;
        vertical-align:middle;margin-right:6px;overflow:hidden}
 .barra i{display:block;height:100%;background:#16697A}
 table.g{white-space:nowrap;font-size:11.5px}
 table.g th,table.g td{text-align:center;border:1px solid #EDEEF5}
 table.g thead th{background:#0F4C5C;color:#fff;font-size:10px}
 table.g th.lbl{background:#EAF3F5;color:#0F4C5C;text-align:left;font-weight:700;
                position:sticky;left:0;min-width:132px}
 table.g thead th.lbl{background:#0F4C5C;color:#fff}
 table.g th.lbl span{display:block;font-weight:400;font-size:10px;color:#5B8A94}
 table.g td b{font-size:13px}
 table.g td .n{display:block;font-size:9px;opacity:.75}
 table.g td .p{display:block;font-size:9.5px;font-weight:700}
 table.g td.vacia{color:#D2D4E0;background:#FBFBFD}
 table.g td.tot{border-left:3px solid #0F4C5C}
 table.g td.dia{background:#EAF3F5;color:#0F4C5C}
 .ley{font-size:10.5px;color:#68697A;padding:0 0 8px;line-height:1.8}
 .ley i{display:inline-block;width:11px;height:11px;border-radius:3px;margin:0 4px 0 12px;
        vertical-align:-1px}
"""


def _sel_color(u):
    return "#1B7F4B" if u > 0 else ("#C0392B" if u < 0 else "#8A8C9E")


def _sel_estilo(pct, n, umbral):
    """Color de una celda: winrate contra el que esa pata necesita para no
    perder. Con menos de 3 operaciones el winrate no significa nada: gris."""
    if n < 3 or umbral is None:
        return "background:#F4F5FA;color:#8A8C9E"
    d = pct - umbral
    if d >= 10:
        return "background:#1B7F4B;color:#FFFFFF"
    if d >= 3:
        return "background:#4FA97B;color:#FFFFFF"
    if d >= -3:
        return "background:#F2B134;color:#3A3A3A"
    if d >= -10:
        return "background:#E08A3C;color:#FFFFFF"
    return "background:#C0392B;color:#FFFFFF"


@app.get("/selectivo/reporte.html", response_class=HTMLResponse)
def selectivo_reporte():
    r = _sel_resumen()
    t, patas, cierres = r["total"], r["patas"], r["cierres"]
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")

    if not cierres:
        return (f'<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><style>{_SEL_CSS}'
                f'</style></head><body><div class="c"><div class="cab"><h2>NEO Selectivo</h2>'
                f'<p>desde el {SEL_DESDE}</p></div><div class="caja">Todavia no hay operaciones '
                f'cerradas reportadas a /selectivo/registrar_cierre.</div></div></body></html>')

    wr = t["ganadas"] / t["n"] * 100 if t["n"] else 0.0
    pct_cap = (f' &nbsp;<span style="font-size:16px">({t["usd"] / CAPITAL_SELECTIVO * 100:+.2f}%)</span>'
               if CAPITAL_SELECTIVO > 0 else "")
    r_txt = f"{t['r_medio']:+.3f}" if t["r_medio"] is not None else "—"

    umbral_de = {(p_["symbol"], p_["lado"]): p_["necesita"] for p_ in patas}

    filas_patas = []
    for p_ in patas:
        nec = f"{p_['necesita']:.0f}%" if p_["necesita"] is not None else "—"
        rm = f"{p_['r_medio']:+.3f}" if p_["r_medio"] is not None else "—"
        if p_["veredicto"] is None:
            ver = f"sin veredicto — faltan {max(SEL_N_MIN - p_['n'], 0)} operaciones"
        else:
            col = "#1B7F4B" if p_["veredicto"] == "MANTENER" else "#C0392B"
            ver = f"<b style='color:{col}'>{p_['veredicto']}</b> (p={p_['p']:.4f}, umbral {SEL_ALFA:.4f})"
        filas_patas.append(
            f"<tr><td><b>{p_['symbol']} {p_['lado']}</b></td><td>{p_['n']}</td>"
            f"<td>{p_['winrate']:.0f}%</td><td>{nec}</td><td>{rm}</td>"
            f"<td style='color:{_sel_color(p_['usd'])}'>{p_['usd']:+,.2f}</td>"
            f"<td><span class='barra'><i style='width:{p_['avance'] * 100:.0f}%'></i></span>"
            f"{p_['n']}/{SEL_N_MIN}</td><td>{ver}</td></tr>")

    # ---- diario: patas en filas, dias en columnas ----
    celdas, dias = {}, set()
    for c in cierres:
        dia = str(c.get("fecha_cierre", ""))[:10]
        if len(dia) != 10:
            continue
        lado = "Compra" if str(c.get("tipo", "")).upper() == "BUY" else "Venta"
        celdas.setdefault(((str(c["symbol"]).upper(), lado), dia), []).append(c)
        dias.add(dia)
    dias = sorted(dias)
    filas_g = []
    por_dia = {d: [0, 0, 0.0] for d in dias}          # n, ganadas, usd
    for p_ in patas:
        k = (p_["symbol"], p_["lado"])
        umbral = umbral_de.get(k)
        tds, tn, tg, tu = [], 0, 0, 0.0
        for d in dias:
            ops = celdas.get((k, d), [])
            if not ops:
                tds.append('<td class="vacia">—</td>')
                continue
            n = len(ops)
            g = sum(1 for o in ops if float(o.get("puntos", 0) or 0) > 0)
            u = sum(float(o.get("profit", 0) or 0) for o in ops)
            tn += n; tg += g; tu += u
            por_dia[d][0] += n; por_dia[d][1] += g; por_dia[d][2] += u
            tds.append(f'<td style="{_sel_estilo(g / n * 100, n, umbral)}"><b>{g / n * 100:.0f}%</b>'
                       f'<span class="n">n={n}</span><span class="p">{u:+,.2f}</span></td>')
        etq = f"necesita {umbral:.0f}%" if umbral is not None else "sin referencia"
        filas_g.append(
            f'<tr><th class="lbl">{k[0]} {k[1]}<span>{etq}</span></th>' + "".join(tds)
            + f'<td class="tot" style="{_sel_estilo(tg / tn * 100, tn, umbral)}"><b>{tg / tn * 100:.0f}%</b>'
              f'<span class="n">n={tn}</span><span class="p">{tu:+,.2f}</span></td></tr>')

    tds_dia = []
    for d in dias:
        n, g, u = por_dia[d]
        tds_dia.append(f'<td class="dia"><b>{g / n * 100:.0f}%</b><span class="n">n={n}</span>'
                       f'<span class="p" style="color:{_sel_color(u)}">{u:+,.2f}</span></td>' if n
                       else '<td class="vacia">—</td>')
    fila_dia = ('<tr><th class="lbl">TODO JUNTO<span>el dia completo</span></th>' + "".join(tds_dia)
                + f'<td class="tot dia"><b>{t["usd"]:+,.2f}</b><span class="n">n={t["n"]}</span></td></tr>')
    enc = "".join(f"<th>{d[8:10]}-{MESES[int(d[5:7])]}</th>" for d in dias)

    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>NEO Selectivo</title>
<style>{_SEL_CSS}</style></head><body><div class="c">
 <div class="cab"><h2>NEO Selectivo — resultado por simbolo y lado</h2>
  <p>Solo las operaciones de NEO_SELECTIVO · desde el {SEL_DESDE} · actualizado el {ahora}</p></div>
 <div class="caja"><h3>Resultado acumulado</h3>
  <div class="big" style="color:{_sel_color(t['usd'])}">{t['usd']:+,.2f} USD{pct_cap}</div>
  <p style="font-size:12px;color:#68697A;margin:8px 0 0">{t['n']} operaciones cerradas ·
   acierto {wr:.1f}% · R medio {r_txt}</p></div>
 <div class="caja"><h3>Por pata (simbolo y lado)</h3>
  <table><tr><th>pata</th><th>operaciones</th><th>acierto</th><th>necesita</th><th>R medio</th>
  <th>USD</th><th>avance al veredicto</th><th>veredicto</th></tr>{''.join(filas_patas)}</table>
  <p style="font-size:11px;color:#68697A;margin:10px 0 0;line-height:1.6">
   <b>necesita</b> = acierto minimo para no perder, segun la relacion objetivo/stop real de esa pata.
   <b>R medio</b> = resultado promedio medido en multiplos del stop; no depende del lote.
   El veredicto no se da hasta {SEL_N_MIN} operaciones por pata (umbral de p = {SEL_ALFA:.4f}).</p></div>
 <div class="caja"><h3>Dia por dia</h3>
  <div class="ley">El numero grande es el winrate del dia; debajo, operaciones y USD. Color contra lo que la
   pata necesita para no perder:
   <i style="background:#1B7F4B"></i>10 o mas por encima <i style="background:#4FA97B"></i>por encima
   <i style="background:#F2B134"></i>en el limite <i style="background:#E08A3C"></i>por debajo
   <i style="background:#C0392B"></i>10 o mas por debajo
   <i style="background:#F4F5FA;border:1px solid #EDEEF5"></i>menos de 3 operaciones</div>
  <table class="g"><thead><tr><th class="lbl">Simbolo / Lado</th>{enc}<th>TOTAL</th></tr></thead>
  <tbody>{''.join(filas_g)}{fila_dia}</tbody></table></div>
 <div class="av"><b>Esto mide, no demuestra.</b> Un dia o una semana buenos no distinguen una ventaja de una
  racha: con el R historico de US30 (-0,06 por operacion), un dia de 24 operaciones con R medio de +0,31 sale
  en ~9% de los dias. El modelo detras tiene AUC ~0,5 en direccion. Las patas que no cumplian el criterio de
  seleccion (US30, GER40, GBPUSD) se prendieron por pedido. Decidir solo con el veredicto de arriba; no subir
  el lote ni cambiar la tabla por un dia.</div>
 <div class="caja" style="font-size:12px;color:#68697A">
  Lo mismo en JSON: <a href="/selectivo/resumen.json">/selectivo/resumen.json</a></div>
</div></body></html>"""
