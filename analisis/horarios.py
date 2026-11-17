r"""
horarios.py -- que horas conviene bloquear, y si bloquearlas sirve de algo.

De todo lo probado, el horario es lo unico que dio un patron CONSISTENTE
entre simbolos. Las horas muertas casi coinciden en los cinco:

    NAS100  17h (2%)  5h (3%)  18h (6%)  4h (7%)
    US30    18h (4%)  17h (4%)  4h (8%)  5h (9%)
    GER40   18h (1%)  4h (5%)  11h (5%)  5h (7%)
    GBPUSD  18h (0%)  5h (1%)  6h (4%)   4h (4%)

Cuatro mercados independientes coincidiendo no es casualidad.

"Hora muerta" = hora en la que el precio rara vez recorre k veces el ATR
dentro del horizonte. Ojo: es RELATIVO al ATR del momento, no movimiento
absoluto. Una hora puede tener ATR alto y aun asi contar como muerta, si el
precio se queda quieto respecto de lo que su propia volatilidad sugeriria.
Para un objetivo que es multiplo de ATR, eso es justamente lo que importa:
si el precio no recorre lo suficiente, la operacion se arrastra y termina en
el stop.

El script hace dos cosas:
  [A] Calcula el % de velas movidas por hora usando TODO el historial que le
      pases, y propone que horas bloquear.
  [B] Mide, en HOLDOUT, que le pasa al modelo direccional si NO opera en esas
      horas. Si el PF no mejora, no vale la pena tocar el EA.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\horarios.py --symbol NAS100 --version v6_20260914 --costo 0.85 ^
        --csv datos\crudos\NAS100_TRAIN_2025-10-09_al_2026-06-03_M5.csv ^
              datos\crudos\NAS100_HOLDOUT_A_TPSL_2026-06-04_al_2026-07-23_M5.csv ^
        --holdout datos\crudos\NAS100_HOLDOUT_B_CONFIRM_2026-07-24_al_2026-09-13_M5.csv
"""
import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import (cargar_csv_exportado, construir_features, etiquetar_tp_sl,
                  FEATURE_LIST)
from registry import Registry


def etiqueta_vol(high, low, atr, h, k):
    s_hi, s_lo = pd.Series(high), pd.Series(low)
    fut_max = s_hi.iloc[::-1].rolling(h).max().iloc[::-1].shift(-1)
    fut_min = s_lo.iloc[::-1].rolling(h).min().iloc[::-1].shift(-1)
    rec = (fut_max - fut_min).values
    y = np.full(len(high), -1, dtype=np.int8)
    ok = ~np.isnan(rec) & (atr > 0)
    y[ok] = (rec[ok] >= k * atr[ok]).astype(np.int8)
    return y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--version", default=None,
                    help="modelo direccional, para la parte [B]")
    ap.add_argument("--csv", required=True, nargs="+",
                    help="CSVs para CALCULAR las horas (TRAIN y HOLDOUT_A)")
    ap.add_argument("--holdout", default=None,
                    help="HOLDOUT_B, para MEDIR el efecto. Nunca se usa en [A]")
    ap.add_argument("--costo", type=float, default=0.0)
    ap.add_argument("--horizonte", type=int, default=288)
    ap.add_argument("--horizonte-vol", type=int, default=24, dest="hvol")
    ap.add_argument("--k", type=float, default=6.0)
    ap.add_argument("--umbral-muerta", type=float, default=0.5,
                    dest="umbral_muerta",
                    help="hora muerta = menos de esta fraccion del promedio diario")
    args = ap.parse_args()

    symbol = args.symbol.upper()
    print(f"### {symbol} — horas muertas ###\n")

    # ---------------- [A] ----------------
    partes = [construir_features(cargar_csv_exportado(r)) for r in args.csv]
    feat = pd.concat(partes, ignore_index=True)
    feat = feat.drop_duplicates(subset="fecha").sort_values("fecha")
    feat = feat.reset_index(drop=True)
    print(f"[A] Calculado con {len(feat)} barras  "
          f"{feat['fecha'].min()} -> {feat['fecha'].max()}")
    print("    (TRAIN y HOLDOUT_A; HOLDOUT_B queda fuera a proposito)\n")

    y = etiqueta_vol(feat['high'].values, feat['low'].values,
                     feat['atr5'].values, args.hvol, args.k)
    horas = pd.to_datetime(feat['fecha']).dt.hour.values
    atr = feat['atr5'].values
    ok = y != -1
    base = y[ok].mean()
    corte = base * args.umbral_muerta

    print(f"  {'hora':>5}{'velas':>8}{'% movidas':>12}{'ATR medio':>12}  estado")
    muertas = []
    for h in range(24):
        s = ok & (horas == h)
        if s.sum() < 100:
            continue
        pct = y[s].mean()
        if pct < corte:
            estado = "MUERTA"
            muertas.append(h)
        elif pct > base * 1.25:
            estado = "activa"
        else:
            estado = ""
        print(f"  {h:>5}{int(s.sum()):>8}{pct:>11.1%}{atr[s].mean():>12.2f}  {estado}")

    print(f"\n  promedio del dia: {base:.1%}   "
          f"corte para 'muerta': {corte:.1%}")
    print(f"  HORAS A BLOQUEAR: {','.join(str(h) for h in muertas) or '(ninguna)'}")

    if not args.holdout or not args.version:
        print("\n  (sin --holdout y --version no se puede medir el efecto)")
        return

    # ---------------- [B] ----------------
    print("\n" + "=" * 70)
    print("[B] ¿Bloquear esas horas mejora al modelo? (medido en HOLDOUT_B)")
    print("=" * 70)

    reg = Registry()
    entrada = reg._buscar(symbol, args.version)
    if entrada is None:
        print(f"  No existe {symbol}/{args.version} en registry.json")
        return
    paquete = joblib.load(entrada["archivo_modelo"])

    f_b = construir_features(cargar_csv_exportado(args.holdout))
    hb = pd.to_datetime(f_b['fecha']).dt.hour.values
    bloqueada = np.isin(hb, muertas)
    high, low = f_b['high'].values, f_b['low'].values
    close, atr_b = f_b['close'].values, f_b['atr5'].values

    for lado_key, m in paquete.items():
        lado = "BUY" if lado_key == "buy" else "SELL"
        k_tp, k_sl, umbral = m["k_tp"], m["k_sl"], m["umbral"]
        tp_arr, sl_arr = k_tp * atr_b, k_sl * atr_b
        labels, _ = etiquetar_tp_sl(high, low, close, tp_arr, sl_arr,
                                    args.horizonte, lado)
        probs = m["modelo"].predict_proba(
            m["scaler"].transform(f_b[FEATURE_LIST].values))[:, 1]
        opera = (labels != -1) & (probs >= umbral)

        print(f"\n  --- {lado} (k_tp={k_tp} k_sl={k_sl}) ---")
        print(f"      {'':<22}{'n':>7}{'winrate':>10}{'PF':>9}")
        for nombre, sel in (("todas las horas", opera),
                            ("sin las muertas", opera & ~bloqueada)):
            n = int(sel.sum())
            if n == 0:
                print(f"      {nombre:<22}{'sin operaciones':>26}")
                continue
            yv = labels[sel]
            gan = tp_arr[sel][yv == 1].sum()
            per = sl_arr[sel][yv == 0].sum() + n * args.costo
            pf = gan / per if per > 0 else float("inf")
            print(f"      {nombre:<22}{n:>7}{yv.mean():>10.1%}{pf:>9.3f}")

    print("\n" + "=" * 70)
    print("Como leerlo: si el PF 'sin las muertas' no sube, bloquear horas no")
    print("aporta y no vale la pena tocar el EA. Y aunque suba, un PF por")
    print("debajo de 1.0 sigue perdiendo plata.")


if __name__ == "__main__":
    main()
