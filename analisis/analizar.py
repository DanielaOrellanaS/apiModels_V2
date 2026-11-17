r"""
analizar.py -- las tres preguntas del proyecto, en un solo archivo.

Cada seccion responde una pregunta distinta. Se piden con banderas:

  --edge    ¿El modelo tiene ventaja real, y su probabilidad dice la verdad?
            Mide contra el azar (k_sl/(k_tp+k_sl)) y contra un filtro
            aleatorio del mismo tamaño, y arma la tabla de calibracion.

  --meses   ¿Esa ventaja es estable, o vino de un bloque afortunado?
            Corre el mismo modelo mes por mes. Compara siempre contra el
            mismo mes SIN filtro, para descontar la direccion del mercado:
            en un random walk sin señal los meses ya dan 41%, 31%, 13% solos.

  --vivo    ¿Lo que le llega al modelo en vivo es lo mismo que en las pruebas?
            Compara las 15 variables Y la probabilidad, para la MISMA vela,
            contra el CSV. Asi se destapo que el EA leia una vela sin cerrar
            (el ATR llegaba al 93.5%).

Sin banderas corre las tres.

Uso, desde F:\ApiModels\apiModels_V2:

    py analisis\analizar.py --symbol NAS100 --version v3_20260904 --costo 0.85 ^
        --csv datos\crudos\NAS100_TRAIN_2025-10-02_al_2026-05-27_M5.csv ^
              datos\crudos\NAS100_HOLDOUT_A_TPSL_2026-05-28_al_2026-07-15_M5.csv ^
              datos\crudos\NAS100_HOLDOUT_B_CONFIRM_2026-07-16_al_2026-09-03_M5.csv

    py analisis\analizar.py --symbol NAS100 --version v3_20260904 --vivo ^
        --csv datos\crudos\NAS100_HOLDOUT_B_CONFIRM_2026-07-16_al_2026-09-03_M5.csv

--edge y --vivo usan un solo CSV: el que tenga HOLDOUT_B en el nombre, o el
ultimo de la lista. --meses usa todos los que le pases.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import (cargar_csv_exportado, construir_features, etiquetar_tp_sl,
                  FEATURE_LIST)
from registry import Registry

PREDICCIONES = Path("datos/operaciones/predicciones.jsonl")
BUCKETS = [(0.20, 0.30), (0.30, 0.40), (0.40, 0.50), (0.50, 0.60),
           (0.60, 0.70), (0.70, 0.80), (0.80, 1.01)]


# =====================================================================
# utilidades
# =====================================================================
def titulo(txt):
    print("\n" + "=" * 74)
    print(txt)
    print("=" * 74)


def elegir_csv(rutas):
    """Para --edge y --vivo: el HOLDOUT_B si esta, si no el ultimo."""
    for r in rutas:
        if "HOLDOUT_B" in r.upper():
            return r
    return rutas[-1]


def cargar(ruta):
    return construir_features(cargar_csv_exportado(ruta))


def pf(res, tp_arr, sl_arr, costo):
    g = tp_arr[res == 1].sum()
    p = sl_arr[res == 0].sum() + len(res) * costo
    return g / p if p > 0 else float("inf")


def resolver(high, low, tp_lvl, sl_lvl, lado, t):
    n = len(high)
    for k in range(t + 1, n):
        if lado == "BUY":
            if low[k] <= sl_lvl:
                return 0, k
            if high[k] >= tp_lvl:
                return 1, k
        else:
            if high[k] >= sl_lvl:
                return 0, k
            if low[k] <= tp_lvl:
                return 1, k
    return None, None


# =====================================================================
# --edge
# =====================================================================
def seccion_edge(paquete, feat, args, rng):
    titulo(f"[EDGE] ¿El modelo predice, y su probabilidad dice la verdad?")
    high, low = feat["high"].values, feat["low"].values
    close, atr = feat["close"].values, feat["atr5"].values
    n = len(feat)
    print(f"{n} barras, {feat['fecha'].min()} -> {feat['fecha'].max()}")

    for lado_key, m in paquete.items():
        lado = "BUY" if lado_key == "buy" else "SELL"
        k_tp, k_sl, umbral = m["k_tp"], m["k_sl"], m["umbral"]
        azar = k_sl / (k_tp + k_sl)
        tp_arr, sl_arr = k_tp * atr, k_sl * atr

        labels, _ = etiquetar_tp_sl(high, low, close, tp_arr, sl_arr,
                                    args.horizonte, lado)
        resuelto = labels != -1
        probs = m["modelo"].predict_proba(
            m["scaler"].transform(feat[FEATURE_LIST].values))[:, 1]
        opera = resuelto & (probs >= umbral)

        print(f"\n--- {lado}  k_tp={k_tp} k_sl={k_sl} umbral={umbral} ---")
        if opera.sum() == 0:
            print("    el modelo no opera ninguna barra de este CSV")
            continue

        wr_mod = labels[opera].mean()
        print(f"  1) VENTAJA")
        print(f"     WR sin ninguna señal (k_sl/(k_tp+k_sl)) : {azar:>7.1%}")
        print(f"     WR de todas las barras resueltas        : "
              f"{labels[resuelto].mean():>7.1%}")
        print(f"     WR del modelo (n={int(opera.sum())})".ljust(46)
              + f": {wr_mod:>7.1%}")

        idx = np.where(resuelto)[0]
        k = int(opera.sum())
        if 0 < k <= len(idx):
            boot = np.array([labels[rng.choice(idx, k, replace=False)].mean()
                             for _ in range(args.n_boot)])
            lo, hi = np.percentile(boot, [2.5, 97.5])
            veredicto = ("SIN VENTAJA" if lo <= wr_mod <= hi
                         else "supera al azar")
            print(f"     Filtro ALEATORIO del mismo tamaño       : "
                  f"{boot.mean():>7.1%}  IC95% [{lo:.1%}, {hi:.1%}] -> {veredicto}")
            print(f"     (ojo: las operaciones se solapan, asi que ese IC es")
            print(f"      mas angosto de lo que corresponde)")

        print(f"\n  2) CALIBRACION (¿el 70% que declara es un 70% real?)")
        print(f"     {'declarado':<14}{'n':>7}{'WR real':>10}{'brecha':>10}")
        for blo, bhi in BUCKETS:
            sel = resuelto & (probs >= blo) & (probs < bhi)
            if sel.sum() < 30:
                continue
            wr = labels[sel].mean()
            centro = (blo + min(bhi, 1.0)) / 2
            print(f"     {f'{blo:.0%}-{bhi:.0%}':<14}{int(sel.sum()):>7}"
                  f"{wr:>10.1%}{wr - centro:>+10.1%}")

        print(f"\n  3) POR BARRA vs SECUENCIAL (el EA opera de a una)")
        r_pb = labels[opera]
        print(f"     por barra    n={len(r_pb):<6} WR={r_pb.mean():.1%} "
              f"PF={pf(r_pb, tp_arr[opera], sl_arr[opera], args.costo):.3f}")
        res, tps, sls, t = [], [], [], 0
        sgn = 1 if lado == "BUY" else -1
        while t < n - 1:
            if probs[t] < umbral:
                t += 1
                continue
            tp_d, sl_d = k_tp * atr[t], k_sl * atr[t]
            r, kc = resolver(high, low,
                             close[t] + sgn * (tp_d + args.spread),
                             close[t] - sgn * (sl_d - args.spread), lado, t)
            if r is None:
                break
            res.append(r); tps.append(tp_d); sls.append(sl_d)
            t = kc + 1
        if res:
            res = np.array(res)
            print(f"     secuencial   n={len(res):<6} WR={res.mean():.1%} "
                  f"PF={pf(res, np.array(tps), np.array(sls), args.costo):.3f}"
                  f"   (spread en los niveles)")


# =====================================================================
# --meses
# =====================================================================
def seccion_meses(paquete, args):
    titulo("[MESES] ¿La ventaja es estable, o vino de un bloque afortunado?")

    partes, meses_train = [], set()
    for ruta in args.csv:
        f = cargar(ruta)
        if "_TRAIN_" in ruta.upper():
            meses_train |= set(
                pd.to_datetime(f["fecha"]).dt.to_period("M").astype(str))
        partes.append(f)

    feat = pd.concat(partes, ignore_index=True)
    feat = feat.drop_duplicates(subset="fecha").sort_values("fecha")
    feat = feat.reset_index(drop=True)

    mes = pd.to_datetime(feat["fecha"]).dt.to_period("M").astype(str)
    high, low = feat["high"].values, feat["low"].values
    close, atr = feat["close"].values, feat["atr5"].values
    print(f"{len(feat)} barras, {feat['fecha'].min()} -> {feat['fecha'].max()}")

    for lado_key, m in paquete.items():
        lado = "BUY" if lado_key == "buy" else "SELL"
        k_tp, k_sl, umbral = m["k_tp"], m["k_sl"], m["umbral"]
        azar = k_sl / (k_tp + k_sl)
        tp_arr, sl_arr = k_tp * atr, k_sl * atr

        labels, _ = etiquetar_tp_sl(high, low, close, tp_arr, sl_arr,
                                    args.horizonte, lado)
        probs = m["modelo"].predict_proba(
            m["scaler"].transform(feat[FEATURE_LIST].values))[:, 1]
        opera = (labels != -1) & (probs >= umbral)

        print(f"\n--- {lado}  k_tp={k_tp} k_sl={k_sl} umbral={umbral}   "
              f"(sin ventaja daria ~{azar:.0%}) ---")
        print(f"  {'mes':<10}{'origen':<9}{'n':>6}{'WR modelo':>11}"
              f"{'WR sin modelo':>15}{'VENTAJA':>10}{'PF':>8}")

        ventajas, filas = [], 0
        for mm in sorted(mes.unique()):
            sel = opera & (mes.values == mm)
            nn = int(sel.sum())
            if nn < args.min_ops:
                continue
            y = labels[sel]
            gan = tp_arr[sel][y == 1].sum()
            per = sl_arr[sel][y == 0].sum() + nn * args.costo
            base = (labels != -1) & (mes.values == mm)
            v = y.mean() - labels[base].mean()
            origen = "[TRAIN]" if mm in meses_train else "[FUERA]"
            if origen == "[FUERA]":
                ventajas.append(v)
            filas += 1
            print(f"  {mm:<10}{origen:<9}{nn:>6}{y.mean():>10.0%}"
                  f"{labels[base].mean():>14.0%}{v:>+10.0%}"
                  f"{(gan/per if per>0 else float('inf')):>8.2f}")

        if filas == 0:
            print("  (ningun mes con suficientes operaciones)")
            continue
        if len(ventajas) >= 2:
            e = np.array(ventajas)
            print(f"\n  Meses FUERA del entrenamiento: {len(e)}")
            print(f"    ventaja: peor {e.min():+.0%}  mejor {e.max():+.0%}  "
                  f"promedio {e.mean():+.0%}")
            print(f"    meses con ventaja NEGATIVA: {int((e < 0).sum())} de {len(e)}")
            if e.mean() > 0.10 and (e < 0).sum() == 0:
                print("    -> ESTABLE: supera a no-filtrar en todos los meses.")
            elif e.mean() > 0.05:
                print("    -> DEBIL: positiva en promedio, no en todos los meses.")
            else:
                print("    -> NO ESTABLE: no supera de forma consistente.")
        else:
            print(f"\n  Solo {len(ventajas)} mes fuera del entrenamiento: "
                  f"no alcanza para juzgar estabilidad.")


# =====================================================================
# --vivo
# =====================================================================
def piso_5min(dt):
    return dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)


def seccion_vivo(paquete, args):
    titulo("[VIVO] ¿Le llega al modelo lo mismo que en las pruebas?")

    if not PREDICCIONES.exists():
        print(f"No existe {PREDICCIONES}")
        return

    vivo, sin_feat = {}, 0
    for linea in open(PREDICCIONES, encoding="utf-8"):
        try:
            p = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if p.get("symbol", "").upper() != args.symbol.upper():
            continue
        if "features" not in p:
            sin_feat += 1
            continue
        try:
            f = datetime.strptime(str(p["fecha_vela"]).split("+")[0],
                                  "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
        vivo[piso_5min(f)] = p

    if not vivo:
        print(f"No hay predicciones de {args.symbol} con el campo 'features'.")
        print(f"Se guardan desde el 02-sep-2026. Sin ese campo: {sin_feat}.")
        return

    ruta = elegir_csv(args.csv)
    feat = cargar(ruta)
    idx = {f.to_pydatetime(): i for i, f in enumerate(feat["fecha"])}
    n_csv = len(feat)
    pares = []
    for f, p in sorted(vivo.items()):
        i = idx.get(f)
        if i is None:
            continue
        j = i + args.offset
        if 0 <= j < n_csv:
            pares.append((f, p, j))

    print(f"CSV usado: {Path(ruta).name}")
    if args.offset:
        print(f"offset = {args.offset} barras "
              f"({args.offset * 5} minutos respecto de la fecha guardada)")
    print(f"predicciones con features: {len(vivo)}   velas del CSV: {len(idx)}")
    print(f"velas en AMBOS: {len(pares)}")

    if len(pares) < 20:
        print("\nMuy pocas velas en comun para concluir.")
        print(f"  vivo va de   {min(vivo)} a {max(vivo)}")
        print(f"  el CSV va de {min(idx)} a {max(idx)}")
        print("Exportar un CSV que cubra las fechas del vivo con "
              "EXPORTAR_DATASETS_3PERIODOS_V3.mq4.")
        return

    print(f"\n  (a) Las 15 variables, en la misma vela")
    print(f"  {'variable':<16}{'mediana VIVO':>15}{'mediana CSV':>15}"
          f"{'ratio':>9}{'estado':>11}")
    sospechosas = []
    for nombre in FEATURE_LIST:
        v = np.array([p["features"][nombre] for _, p, _ in pares
                      if nombre in p["features"]], dtype=float)
        c = np.array([feat[nombre].values[i] for _, p, i in pares
                      if nombre in p["features"]], dtype=float)
        if len(v) < 20:
            print(f"  {nombre:<16}{'—':>15}{'—':>15}{'—':>9}{'sin datos':>11}")
            continue
        mv, mc = float(np.median(v)), float(np.median(c))
        disp = float(np.percentile(c, 75) - np.percentile(c, 25))
        # Umbral 2%: una variable que llega bien desvia ~0.5% de su propio
        # rango intercuartil. La dilucion del 7% que tenia el ATR daba 3.5%.
        rel = float(np.median(np.abs(v - c))) / disp if disp > 0 else 0.0
        estado = "REVISAR" if rel > 0.02 else "ok"
        if estado == "REVISAR":
            sospechosas.append((nombre, rel))
        ratio = f"{mv/mc:.3f}" if abs(mc) > 1e-9 else "n/a"
        print(f"  {nombre:<16}{mv:>15.6f}{mc:>15.6f}{ratio:>9}{estado:>11}")

    print()
    if sospechosas:
        print("  Variables que NO llegan iguales:")
        for nombre, r in sorted(sospechosas, key=lambda x: -x[1]):
            print(f"    {nombre:<16} desvia {r*100:.0f}% de su rango normal")
    else:
        print("  Las 15 variables llegan practicamente iguales al CSV.")

    print(f"\n  (b) La probabilidad, en la misma vela")
    print(f"  Se recalcula con el mismo .pkl desde las variables del CSV y se")
    print(f"  compara con la que el modelo devolvio en vivo.\n")
    for lado_key, m in paquete.items():
        lado = "BUY" if lado_key == "buy" else "SELL"
        sub = [(f, p, i) for f, p, i in pares if p.get("resultado") == lado]
        if len(sub) < 20:
            print(f"    {lado}: solo {len(sub)} predicciones — insuficiente")
            continue
        X = np.array([[feat[k].values[i] for k in FEATURE_LIST]
                      for _, _, i in sub], dtype=float)
        p_csv = m["modelo"].predict_proba(m["scaler"].transform(X))[:, 1]
        p_vivo = np.array([p["probabilidad"] for _, p, _ in sub], dtype=float)
        d = p_vivo - p_csv
        iguales = float((np.abs(d) < 0.01).mean())
        print(f"    --- {lado} (n={len(sub)}) ---")
        print(f"        prob VIVO mediana {np.median(p_vivo):.4f}   "
              f"prob CSV mediana {np.median(p_csv):.4f}")
        print(f"        diferencia mediana {np.median(d):+.4f}   "
              f"maxima {np.abs(d).max():.4f}")
        print(f"        coinciden (menos de 0.01): {iguales:.0%}")
        if iguales > 0.95:
            print("        -> IGUALES: las variables llegan bien. La caida en")
            print("           vivo NO esta aca; buscar en la ejecucion.")
        else:
            print("        -> DISTINTAS: el modelo recibe en vivo algo diferente")
            print("           de lo que hay en el CSV. Ahi esta el problema.")
        print()


# =====================================================================
def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--csv", required=True, nargs="+",
                    help="uno o varios CSV exportados")
    ap.add_argument("--edge", action="store_true")
    ap.add_argument("--meses", action="store_true")
    ap.add_argument("--vivo", action="store_true")
    ap.add_argument("--costo", type=float, default=0.0)
    ap.add_argument("--spread", type=float, default=0.0,
                    help="spread aplicado a los NIVELES de TP/SL, en --edge")
    ap.add_argument("--horizonte", type=int, default=288)
    ap.add_argument("--min-ops", type=int, default=10, dest="min_ops")
    ap.add_argument("--n-boot", type=int, default=500, dest="n_boot")
    ap.add_argument("--offset", type=int, default=0,
                    help="en --vivo: desplaza la vela del CSV en N barras. El EA "
                         "usa barra=1 (la vela ya cerrada) pero registra la hora "
                         "ACTUAL, asi que las variables son de la vela anterior a "
                         "la fecha guardada. Probar -1.")
    args = ap.parse_args()

    if not (args.edge or args.meses or args.vivo):
        args.edge = args.meses = args.vivo = True

    reg = Registry()
    entrada = reg._buscar(args.symbol.upper(), args.version)
    if entrada is None:
        raise SystemExit(f"No existe {args.symbol}/{args.version} en registry.json")
    paquete = joblib.load(entrada["archivo_modelo"])
    print(f"### {args.symbol.upper()} / {args.version} ###")

    if args.edge:
        seccion_edge(paquete, cargar(elegir_csv(args.csv)), args,
                     np.random.default_rng(0))
    if args.meses:
        seccion_meses(paquete, args)
    if args.vivo:
        seccion_vivo(paquete, args)


if __name__ == "__main__":
    main()
