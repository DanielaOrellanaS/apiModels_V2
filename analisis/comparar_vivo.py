r"""
comparar_features.py -- SOLO LEE. No modifica nada.

Compara, PARA LA MISMA VELA (misma fecha y hora), lo que el EA le mando al
modelo en vivo contra lo que dice el CSV exportado. Al ser la misma vela,
cualquier diferencia no puede venir del mercado: solo del camino.

Hace dos cosas:

  [A] Las 15 variables, una por una. Es la misma prueba que con el ATR, que
      dio 0.935 y destapo que el EA leia una vela sin cerrar.

  [B] La PROBABILIDAD. Se recalcula con el mismo .pkl a partir de las
      variables del CSV, y se compara contra la que el modelo devolvio en
      vivo para esa misma vela. Si dan distinto, la entrada al modelo es
      distinta y ahi esta el problema. Si dan igual, las variables llegan
      bien y hay que buscar en otro lado (ejecucion, spread, slippage).

Requiere que api.py venga guardando el campo "features" en predicciones.jsonl
(se agrego el 02-sep-2026).

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\comparar_features.py --symbol NAS100 --version v3_20260904 ^
        --csv datos\crudos\NAS100_HOLDOUT_B_CONFIRM_2026-07-16_al_2026-09-03_M5.csv
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import cargar_csv_exportado, construir_features, FEATURE_LIST
from registry import Registry

PREDICCIONES = Path("datos/operaciones/predicciones.jsonl")


def piso_5min(dt):
    return dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--csv", required=True)
    args = ap.parse_args()
    symbol = args.symbol.upper()

    if not PREDICCIONES.exists():
        raise SystemExit(f"No existe {PREDICCIONES}")

    # ---------- vivo ----------
    vivo, sin_features = {}, 0
    for linea in open(PREDICCIONES, encoding="utf-8"):
        try:
            p = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if p.get("symbol", "").upper() != symbol:
            continue
        if "features" not in p:
            sin_features += 1
            continue
        try:
            f = datetime.strptime(str(p["fecha_vela"]).split("+")[0],
                                  "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
        vivo[piso_5min(f)] = p

    if not vivo:
        raise SystemExit(
            f"No hay predicciones de {symbol} con el campo 'features'.\n"
            f"Se guardan desde el 02-sep-2026. Sin features: {sin_features}.")

    # ---------- csv ----------
    feat = construir_features(cargar_csv_exportado(args.csv))
    idx = {f.to_pydatetime(): i for i, f in enumerate(feat["fecha"])}

    pares = [(f, p, idx[f]) for f, p in sorted(vivo.items()) if f in idx]

    print(f"=== {symbol} / {args.version} — vivo vs CSV, misma vela ===")
    print(f"predicciones con features: {len(vivo)}   velas del CSV: {len(idx)}")
    print(f"velas en AMBOS: {len(pares)}\n")

    if len(pares) < 20:
        print("Muy pocas velas en comun para concluir.")
        if vivo:
            print(f"  vivo va de   {min(vivo)} a {max(vivo)}")
        print(f"  el CSV va de {min(idx)} a {max(idx)}")
        print("\nHace falta exportar un CSV que cubra las fechas del vivo, con")
        print("EXPORTAR_DATASETS_3PERIODOS_V3.mq4 sobre el grafico del simbolo.")
        return

    # ================= [A] las 15 variables =================
    print("=" * 74)
    print("[A] Las 15 variables, en la misma vela")
    print("=" * 74)
    print(f"{'variable':<16}{'mediana VIVO':>16}{'mediana CSV':>16}"
          f"{'ratio':>10}{'estado':>14}")

    sospechosas = []
    for f_name in FEATURE_LIST:
        v = np.array([p["features"][f_name] for _, p, _ in pares
                      if f_name in p["features"]], dtype=float)
        c = np.array([feat[f_name].values[i] for _, p, i in pares
                      if f_name in p["features"]], dtype=float)
        if len(v) < 20:
            print(f"{f_name:<16}{'—':>16}{'—':>16}{'—':>10}{'sin datos':>14}")
            continue

        mv, mc = float(np.median(v)), float(np.median(c))
        # las variables que cruzan por cero no admiten ratio: se compara la
        # diferencia tipica contra la dispersion propia de la variable
        disp = float(np.percentile(c, 75) - np.percentile(c, 25))
        dif_tipica = float(np.median(np.abs(v - c)))

        # Umbral 2%: una variable que llega bien desvia ~0.5% de su propio
        # rango intercuartil (redondeo del log). La dilucion del 7% que tenia
        # el ATR daba 3.5%. Con 10% no se habria detectado.
        rel = dif_tipica / disp if disp > 0 else 0.0
        if rel > 0.02:
            estado = "REVISAR"
            sospechosas.append((f_name, rel))
        else:
            estado = "ok"

        ratio = f"{mv/mc:.3f}" if abs(mc) > 1e-9 else "n/a"
        print(f"{f_name:<16}{mv:>16.6f}{mc:>16.6f}{ratio:>10}{estado:>14}")

    print()
    if sospechosas:
        print("Variables que NO llegan igual (diferencia tipica vs su propia "
              "dispersion):")
        for n, r in sorted(sospechosas, key=lambda x: -x[1]):
            print(f"    {n:<16} desvia {r*100:.0f}% de su rango normal")
    else:
        print("Las 15 variables llegan practicamente iguales al CSV.")

    # ================= [B] la probabilidad =================
    reg = Registry()
    entrada = reg._buscar(symbol, args.version)
    if entrada is None:
        print(f"\nNo existe {symbol}/{args.version} en registry.json — "
              f"se omite la parte [B].")
        return
    paquete = joblib.load(entrada["archivo_modelo"])

    print()
    print("=" * 74)
    print("[B] La probabilidad, en la misma vela")
    print("=" * 74)
    print("Se recalcula con el mismo .pkl usando las variables del CSV, y se")
    print("compara contra la que el modelo devolvio en vivo.\n")

    for lado_key, m in paquete.items():
        lado = "BUY" if lado_key == "buy" else "SELL"
        sub = [(f, p, i) for f, p, i in pares if p.get("resultado") == lado]
        if len(sub) < 20:
            print(f"  {lado}: solo {len(sub)} predicciones — muestra insuficiente")
            continue

        X = np.array([[feat[k].values[i] for k in FEATURE_LIST]
                      for _, _, i in sub], dtype=float)
        p_csv = m["modelo"].predict_proba(m["scaler"].transform(X))[:, 1]
        p_vivo = np.array([p["probabilidad"] for _, p, _ in sub], dtype=float)
        dif = p_vivo - p_csv

        print(f"  --- {lado} (n={len(sub)}) ---")
        print(f"      prob VIVO  mediana {np.median(p_vivo):.4f}")
        print(f"      prob CSV   mediana {np.median(p_csv):.4f}")
        print(f"      diferencia mediana {np.median(dif):+.4f}   "
              f"maxima {np.abs(dif).max():.4f}")
        iguales = float((np.abs(dif) < 0.01).mean())
        print(f"      predicciones que coinciden (menos de 0.01): {iguales:.0%}")
        if iguales > 0.95:
            print("      -> IDENTICAS: las variables llegan bien. El problema de")
            print("         la caida en vivo NO esta aca; buscar en la ejecucion.")
        else:
            print("      -> DISTINTAS: el modelo recibe en vivo algo diferente de")
            print("         lo que hay en el CSV. Ahi esta el problema.")
        print()


if __name__ == "__main__":
    main()
