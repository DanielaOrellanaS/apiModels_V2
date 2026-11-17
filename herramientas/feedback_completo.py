r"""
feedback_completo.py — un solo lugar para las 3 preguntas de feedback:

  A) CALIBRACIÓN: cuando la API dice "70% de confianza", ¿gana cerca del
     70% de las veces en la realidad?
  B) RECONCILIACIÓN DE EJECUCIÓN: ¿lo que se operó en MT4 coincide con lo
     que la API pidió? (detecta órdenes huérfanas y señales perdidas)
  C) VERDAD DEL PRECIO (opcional, necesita --precio-dir): para CADA señal,
     haya operado o no, ¿el precio real después tocó el TP antes que el SL?

Uso:
    py feedback_completo.py --historial datos\logs\historial_NEO_MINIMAL_2026-08-18.csv

    (con la parte C tambien, si tenes precio exportado con EXPORTAR_PRECIO_SIMPLE.mq4)
    py feedback_completo.py --historial datos\logs\historial_....csv --precio-dir datos\precios\

Genera reportes\feedback.html -- un solo archivo, para abrir con doble clic
o con el .bat.

Requiere que api.py haya estado logueando predicciones (desde que se agregó
ese cambio) -- no reconstruye nada de antes.
"""
import argparse
import glob
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

PREDICCIONES_PATH = Path("datos/operaciones/predicciones.jsonl")
CIERRES_PATH = Path("datos/operaciones/cierres.jsonl")

BUCKETS = [(0.60, 0.65), (0.65, 0.70), (0.70, 0.75), (0.75, 0.80), (0.80, 1.01)]
HORIZONTE_VELAS = 288

NAVY, MIDNIGHT, GOLD, ICE = "#1E2761", "#161B45", "#F2B134", "#CADCFC"
GREEN, RED, GRAY, LIGHTBG = "#1E8F5F", "#B03A2E", "#68697A", "#F6F7FC"


# ------------------------------------------------------------------ utils
def cargar_jsonl(path):
    if not path.exists():
        return []
    filas = []
    with open(path, encoding="utf-8") as f:
        for linea in f:
            try:
                filas.append(json.loads(linea))
            except json.JSONDecodeError:
                continue
    return filas


def parsear_fecha(s):
    try:
        return datetime.strptime(s.split("+")[0], "%Y-%m-%dT%H:%M:%S")
    except (ValueError, AttributeError):
        return None


# ------------------------------------------------------- A) calibracion
def analizar_calibracion(predicciones, cierres, tolerancia_min):
    preds_por_clave = {}
    for p in predicciones:
        if p["resultado"] not in ("BUY", "SELL"):
            continue
        fecha = parsear_fecha(p["fecha_vela"])
        if fecha is None:
            continue
        clave = (p["symbol"], p["resultado"])
        preds_por_clave.setdefault(clave, []).append((fecha, p["probabilidad"]))
    for clave in preds_por_clave:
        preds_por_clave[clave].sort(key=lambda x: x[0])

    emparejados = []
    for c in cierres:
        clave = (c["symbol"], c["tipo"])
        fecha_apertura = parsear_fecha(c["fecha_apertura"])
        if fecha_apertura is None or clave not in preds_por_clave:
            continue
        mejor, mejor_delta = None, None
        for fecha_pred, prob in preds_por_clave[clave]:
            delta = abs((fecha_pred - fecha_apertura).total_seconds()) / 60
            if delta <= tolerancia_min and (mejor_delta is None or delta < mejor_delta):
                mejor, mejor_delta = prob, delta
        if mejor is not None:
            emparejados.append((mejor, c["puntos"] > 0))

    filas = []
    for lo, hi in BUCKETS:
        en_rango = [g for p, g in emparejados if lo <= p < hi]
        n = len(en_rango)
        if n == 0:
            filas.append(dict(rango=f"{lo:.0%}-{hi:.0%}", n=0, ganadas=0, wr_real=None, calibrado=None))
            continue
        ganadas = sum(en_rango)
        wr_real = ganadas / n
        calibrado = (lo - 0.1) <= wr_real <= (hi + 0.1)
        filas.append(dict(rango=f"{lo:.0%}-{hi:.0%}", n=n, ganadas=ganadas, wr_real=wr_real, calibrado=calibrado))

    return filas, len(emparejados)


# ------------------------------------------------- B) reconciliacion
def analizar_reconciliacion(predicciones, ordenes_df, tolerancia_min):
    preds_por_clave = {}
    for p in predicciones:
        fecha = parsear_fecha(p["fecha_vela"])
        if fecha is None:
            continue
        clave = (p["symbol"], p["resultado"])
        preds_por_clave.setdefault(clave, []).append(fecha)

    huerfanas = []
    if ordenes_df is not None:
        for _, orden in ordenes_df.iterrows():
            clave = (orden['simbolo'], orden['tipo'])
            candidatas = preds_por_clave.get(clave, [])
            tiene_match = any(
                abs((fp - orden['fecha_apertura']).total_seconds()) / 60 <= tolerancia_min
                for fp in candidatas
            )
            if not tiene_match:
                huerfanas.append(dict(ticket=orden['ticket'], simbolo=orden['simbolo'],
                                       tipo=orden['tipo'], fecha=str(orden['fecha_apertura']),
                                       profit=orden['profit']))

    perdidas = []
    if ordenes_df is not None:
        ordenes_por_clave = {}
        for _, orden in ordenes_df.iterrows():
            clave = (orden['simbolo'], orden['tipo'])
            ordenes_por_clave.setdefault(clave, []).append(orden['fecha_apertura'])
        for p in predicciones:
            if p["resultado"] not in ("BUY", "SELL"):
                continue
            fecha = parsear_fecha(p["fecha_vela"])
            if fecha is None:
                continue
            clave = (p["symbol"], p["resultado"])
            candidatas = ordenes_por_clave.get(clave, [])
            tiene_match = any(abs((fo - fecha).total_seconds()) / 60 <= tolerancia_min for fo in candidatas)
            if not tiene_match:
                perdidas.append(dict(simbolo=p["symbol"], tipo=p["resultado"],
                                      fecha=p["fecha_vela"], prob=p["probabilidad"]))

    return huerfanas, perdidas


# ------------------------------------------------------- C) verdad del precio
def cargar_precios(precio_dir, symbol):
    patron = os.path.join(precio_dir, f"{symbol}_PRECIO_*.csv")
    archivos = glob.glob(patron)
    if not archivos:
        return None
    dfs = []
    for a in archivos:
        df = pd.read_csv(a, sep=';')
        df.columns = [c.strip().lower() for c in df.columns]
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        dfs.append(df)
    precios = pd.concat(dfs).dropna(subset=['fecha']).drop_duplicates('fecha').sort_values('fecha').reset_index(drop=True)
    return precios


def resultado_real_de_precio(precios, fecha_señal, direccion, tp, sl, horizonte=HORIZONTE_VELAS):
    if precios is None or len(precios) == 0:
        return None
    idx = precios['fecha'].searchsorted(fecha_señal, side='right')
    if idx >= len(precios):
        return None
    entrada = precios['close'].iloc[max(idx - 1, 0)]
    ventana = precios.iloc[idx:idx + horizonte]
    if len(ventana) == 0:
        return None

    if direccion == "BUY":
        tp_precio, sl_precio = entrada + tp, entrada - sl
        for _, fila in ventana.iterrows():
            if fila['low'] <= sl_precio:
                return False
            if fila['high'] >= tp_precio:
                return True
    else:
        tp_precio, sl_precio = entrada - tp, entrada + sl
        for _, fila in ventana.iterrows():
            if fila['high'] >= sl_precio:
                return False
            if fila['low'] <= tp_precio:
                return True
    return None  # nunca se resolvio dentro del horizonte


def analizar_verdad_precio(predicciones, precio_dir):
    if not precio_dir:
        return None

    por_simbolo = {}
    for p in predicciones:
        if p["resultado"] not in ("BUY", "SELL"):
            continue
        por_simbolo.setdefault(p["symbol"], []).append(p)

    resultados = {}
    for symbol, preds in por_simbolo.items():
        precios = cargar_precios(precio_dir, symbol)
        if precios is None:
            resultados[symbol] = dict(sin_precio=True)
            continue

        aciertos, total_resuelto, sin_resolver = 0, 0, 0
        for p in preds:
            fecha = parsear_fecha(p["fecha_vela"])
            if fecha is None:
                continue
            r = resultado_real_de_precio(precios, fecha, p["resultado"], p["tp"], p["sl"])
            if r is None:
                sin_resolver += 1
                continue
            total_resuelto += 1
            if r:
                aciertos += 1

        resultados[symbol] = dict(
            sin_precio=False, n=len(preds), resueltos=total_resuelto,
            sin_resolver=sin_resolver, aciertos=aciertos,
            pct_acierto=(aciertos / total_resuelto * 100) if total_resuelto else None,
        )
    return resultados


# ------------------------------------------------------------------ HTML
def render_html(calib_filas, n_emparejados_calib, huerfanas, perdidas, n_predicciones,
                 verdad_precio, fecha_gen):
    def badge(texto, color):
        return f'<span class="badge" style="background:{color}22;color:{color};border:1px solid {color}55">{texto}</span>'

    # --- seccion A ---
    filas_calib_html = ""
    for f in calib_filas:
        if f["n"] == 0:
            filas_calib_html += f'<tr><td>{f["rango"]}</td><td colspan="3" class="sin-datos">sin señales en este rango todavía</td></tr>'
            continue
        wr_txt = f'{f["wr_real"]:.1%}'.replace(".", ",")
        est = badge("CALIBRADO", GREEN) if f["calibrado"] else badge("REVISAR", RED)
        filas_calib_html += f'<tr><td>{f["rango"]}</td><td class="num">{f["n"]}</td><td class="num">{f["ganadas"]}</td><td class="num">{wr_txt}</td><td>{est}</td></tr>'

    # --- seccion B ---
    huerfanas_html = ""
    if huerfanas:
        for h in huerfanas:
            huerfanas_html += f'<tr><td>{h["ticket"]}</td><td>{h["simbolo"]}</td><td>{h["tipo"]}</td><td>{h["fecha"]}</td><td class="num">{h["profit"]}</td></tr>'
    else:
        huerfanas_html = '<tr><td colspan="5" class="sin-datos">ninguna — todo lo que se operó tiene una predicción que lo respalda</td></tr>'

    perdidas_html = ""
    if perdidas:
        for p in perdidas[:20]:
            prob_txt = f'{p["prob"]:.0%}'.replace(".", ",")
            perdidas_html += f'<tr><td>{p["simbolo"]}</td><td>{p["tipo"]}</td><td>{p["fecha"]}</td><td class="num">{prob_txt}</td></tr>'
        extra = f'<tr><td colspan="4" class="sin-datos">... y {len(perdidas)-20} más</td></tr>' if len(perdidas) > 20 else ""
        perdidas_html += extra
    else:
        perdidas_html = '<tr><td colspan="4" class="sin-datos">ninguna — toda señal se ejecutó</td></tr>'

    # --- seccion C ---
    verdad_html = ""
    if verdad_precio is None:
        verdad_html = '<p class="sin-datos">No se pasó --precio-dir, esta sección se salteó. Exportá precio real con EXPORTAR_PRECIO_SIMPLE.mq4 para activarla.</p>'
    else:
        filas = ""
        for symbol, r in verdad_precio.items():
            if r.get("sin_precio"):
                filas += f'<tr><td>{symbol}</td><td colspan="4" class="sin-datos">sin archivo de precio para este símbolo</td></tr>'
                continue
            pct_txt = f'{r["pct_acierto"]:.1f}%'.replace(".", ",") if r["pct_acierto"] is not None else "—"
            filas += (f'<tr><td>{symbol}</td><td class="num">{r["n"]}</td>'
                      f'<td class="num">{r["resueltos"]}</td><td class="num">{r["sin_resolver"]}</td>'
                      f'<td class="num">{pct_txt}</td></tr>')
        verdad_html = f"""
        <table>
          <thead><tr><th>Símbolo</th><th>Señales</th><th>Resueltas</th><th>Sin resolver</th><th>% que tocó TP primero</th></tr></thead>
          <tbody>{filas}</tbody>
        </table>"""

    huerfanas_alerta = "" if not huerfanas else f'<div class="alerta-roja"><b>⚠ {len(huerfanas)} orden(es) huérfana(s) detectada(s)</b> — revisar YA, puede ser el mismo tipo de bug que tenía el sistema viejo (Neo_OSC operando sin pasar por el modelo).</div>'

    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>Feedback — calibración, ejecución y verdad del precio</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family:-apple-system,"Segoe UI",Calibri,sans-serif; background:{LIGHTBG}; color:#26263A; }}
  header {{ background:linear-gradient(135deg,{MIDNIGHT},{NAVY}); color:white; padding:36px 32px 28px; }}
  header h1 {{ margin:0 0 6px; font-size:26px; font-weight:800; }}
  header p {{ margin:0; color:{ICE}; font-size:13px; }}
  main {{ max-width:1200px; margin:24px auto 50px; padding:0 24px; }}
  section {{ background:white; border-radius:14px; padding:22px 24px; margin-bottom:24px; box-shadow:0 4px 18px rgba(30,39,97,.08); }}
  section h2 {{ color:{NAVY}; font-size:18px; margin:0 0 4px; }}
  section .desc {{ color:{GRAY}; font-size:12.5px; margin:0 0 16px; }}
  table {{ width:100%; border-collapse:collapse; font-size:12.5px; }}
  thead th {{ text-align:left; padding:9px 12px; background:{LIGHTBG}; color:{GRAY}; font-size:10px; text-transform:uppercase; letter-spacing:.5px; }}
  tbody td {{ padding:8px 12px; border-top:1px solid #eee; }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .sin-datos {{ color:{GRAY}; font-style:italic; text-align:center; }}
  .badge {{ display:inline-block; padding:3px 9px; border-radius:20px; font-size:10px; font-weight:800; }}
  .alerta-roja {{ background:#FDE8E4; color:#6B241C; border-radius:8px; padding:12px 16px; margin-bottom:14px; font-size:12.5px; }}
  .nota {{ background:#FDF3E7; color:#5A4326; border-radius:8px; padding:12px 16px; margin-top:14px; font-size:11.5px; line-height:1.5; }}
</style></head><body>
<header>
  <h1>Feedback del modelo</h1>
  <p>Generado {fecha_gen} — calibración de confianza, reconciliación de ejecución, y verdad del precio real</p>
</header>
<main>

<section>
  <h2>A. Calibración — ¿la confianza que dice la API tiene sentido?</h2>
  <p class="desc">Cuando la API dice "70-75% de confianza", ¿realmente gana cerca del 70-75% de las veces? Basado en {n_emparejados_calib} operaciones reales emparejadas con su predicción.</p>
  <table>
    <thead><tr><th>Rango de confianza</th><th>Señales</th><th>Ganó</th><th>Winrate real</th><th>Estado</th></tr></thead>
    <tbody>{filas_calib_html}</tbody>
  </table>
</section>

<section>
  <h2>B. Reconciliación — ¿lo que se operó coincide con lo que pidió la API?</h2>
  <p class="desc">Contrastado contra {n_predicciones} predicciones guardadas.</p>
  {huerfanas_alerta}
  <p style="font-size:12.5px;font-weight:700;color:{NAVY};margin-bottom:8px">Órdenes huérfanas (se operó sin que la API lo pidiera)</p>
  <table>
    <thead><tr><th>Ticket</th><th>Símbolo</th><th>Tipo</th><th>Fecha</th><th>Profit</th></tr></thead>
    <tbody>{huerfanas_html}</tbody>
  </table>
  <p style="font-size:12.5px;font-weight:700;color:{NAVY};margin:16px 0 8px">Señales sin ejecutar (la API lo pidió, no se operó)</p>
  <table>
    <thead><tr><th>Símbolo</th><th>Tipo</th><th>Fecha</th><th>Confianza</th></tr></thead>
    <tbody>{perdidas_html}</tbody>
  </table>
  <div class="nota">Una señal sin ejecutar no es necesariamente un error — puede ser que ya hubiera una orden abierta de ese símbolo (una por vez, por diseño). Si el número es alto en proporción al total, ahí sí vale la pena revisar el log de Experts.</div>
</section>

<section>
  <h2>C. Verdad del precio — ¿qué hizo el precio realmente después de cada señal?</h2>
  <p class="desc">Independiente de si se operó o no: mirando el precio real que vino después, ¿tocó primero el TP o el SL?</p>
  {verdad_html}
</section>

</main>
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--historial", default=None, help="CSV de EXPORTAR_HISTORIAL_NEO_MINIMAL.mq4 (para la parte B)")
    ap.add_argument("--precio-dir", default=None, dest="precio_dir",
                     help="carpeta con CSVs de EXPORTAR_PRECIO_SIMPLE.mq4, nombrados SYMBOL_PRECIO_*.csv (para la parte C)")
    ap.add_argument("--tolerancia-min", type=float, default=10, dest="tolerancia_min")
    ap.add_argument("--salida", default="reportes/feedback.html")
    args = ap.parse_args()

    predicciones = cargar_jsonl(PREDICCIONES_PATH)
    cierres = cargar_jsonl(CIERRES_PATH)
    print(f"Predicciones guardadas: {len(predicciones)}  |  Cierres reales: {len(cierres)}")

    if not predicciones:
        print("\nNo hay predicciones guardadas todavía. Esto se llena solo, de acá en adelante, "
              "con cada consulta que haga NEO_MINIMAL_V1 desde que se actualizó api.py.")
        return

    ordenes_df = None
    if args.historial:
        ordenes_df = pd.read_csv(args.historial, sep=';')
        ordenes_df['fecha_apertura'] = pd.to_datetime(ordenes_df['fecha_apertura'], format='%Y.%m.%d %H:%M:%S')

    calib_filas, n_emparejados = analizar_calibracion(predicciones, cierres, args.tolerancia_min)
    huerfanas, perdidas = analizar_reconciliacion(predicciones, ordenes_df, args.tolerancia_min)
    verdad_precio = analizar_verdad_precio(predicciones, args.precio_dir)

    print(f"\nCalibración: {n_emparejados} operaciones emparejadas")
    print(f"Reconciliación: {len(huerfanas)} huérfanas, {len(perdidas)} señales sin ejecutar")
    if verdad_precio:
        print(f"Verdad del precio: {len(verdad_precio)} símbolos analizados")

    html = render_html(calib_filas, n_emparejados, huerfanas, perdidas, len(predicciones),
                        verdad_precio, datetime.now().strftime("%d/%m/%Y %H:%M"))
    os.makedirs(os.path.dirname(args.salida), exist_ok=True)
    with open(args.salida, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nReporte generado: {args.salida}")


if __name__ == "__main__":
    main()
