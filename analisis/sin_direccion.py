r"""
sin_direccion.py -- aprovechar lo unico que SI se predice.

Resumen de lo medido hasta ahora:
  - DIRECCION   AUC 0.49-0.55 en los 5 simbolos -> no se predice.
  - VOLATILIDAD AUC 0.67-0.75 en los 5 simbolos -> si se predice.
  - Usarla como filtro: no sirve (ayuda en unos simbolos, arruina en otros).
  - Usarla para mover el objetivo: no sirve (el patron sale invertido).

Queda una idea que NO necesita acertar la direccion: abrir compra Y venta a
la vez, con el objetivo mas lejos que el stop, en los momentos donde se
prevee movimiento fuerte.

Como termina cada par de operaciones (nunca pueden ganar las dos):
  - el precio se va para un lado y sigue -> una toca TP, la otra SL
        resultado = k_tp - k_sl (en ATR), menos 2 costos
  - el precio va y vuelve (mercado lateral) -> las dos tocan SL
        resultado = -2 * k_sl, menos 2 costos

O sea: gana cuando hay movimiento sostenido y pierde cuando el precio zigzaguea.
Que es exactamente lo que el modelo de volatilidad predice con AUC 0.70.

[A] Prueba de la idea, con y sin filtro de volatilidad.
[B] Tabla por hora del dia: en que horas hay movimiento aprovechable.
    Esto sirve como regla simple aunque todo lo demas se descarte.

El modelo de volatilidad se entrena en TRAIN y se evalua en HOLDOUT_B.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\sin_direccion.py --symbol NAS100 ^
        --train datos\crudos\NAS100_TRAIN_2025-10-09_al_2026-06-03_M5.csv ^
        --holdout datos\crudos\NAS100_HOLDOUT_B_CONFIRM_2026-07-24_al_2026-09-13_M5.csv ^
        --costo 0.85
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import (cargar_csv_exportado, construir_features, etiquetar_tp_sl,
                  FEATURE_LIST)

COMBOS = [(2, 1), (3, 1), (4, 1), (3, 1.5), (4, 2), (6, 2), (8, 3)]


def etiqueta_vol(high, low, atr, h, k):
    s_hi, s_lo = pd.Series(high), pd.Series(low)
    fut_max = s_hi.iloc[::-1].rolling(h).max().iloc[::-1].shift(-1)
    fut_min = s_lo.iloc[::-1].rolling(h).min().iloc[::-1].shift(-1)
    rec = (fut_max - fut_min).values
    y = np.full(len(high), -1, dtype=np.int8)
    ok = ~np.isnan(rec) & (atr > 0)
    y[ok] = (rec[ok] >= k * atr[ok]).astype(np.int8)
    return y


def resultado_par(lab_buy, lab_sell, tp_arr, sl_arr, costo, mask):
    """Resultado neto de abrir compra Y venta a la vez, en unidades de precio.
    Solo cuentan las filas donde AMBAS se resolvieron."""
    ok = mask & (lab_buy != -1) & (lab_sell != -1)
    n = int(ok.sum())
    if n == 0:
        return None
    gano_una = (lab_buy[ok] == 1) | (lab_sell[ok] == 1)
    neto = np.where(gano_una,
                    tp_arr[ok] - sl_arr[ok],
                    -2 * sl_arr[ok]) - 2 * costo
    return dict(n=n, pct_movio=float(gano_una.mean()),
                neto_total=float(neto.sum()),
                neto_medio=float(neto.mean()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--train", required=True)
    ap.add_argument("--holdout", required=True)
    ap.add_argument("--costo", type=float, default=0.0)
    ap.add_argument("--horizonte", type=int, default=288)
    ap.add_argument("--horizonte-vol", type=int, default=24, dest="hvol")
    ap.add_argument("--k", type=float, default=6.0)
    args = ap.parse_args()

    print(f"### {args.symbol.upper()} — operar sin predecir la direccion ###\n")

    f_tr = construir_features(cargar_csv_exportado(args.train))
    f_ho = construir_features(cargar_csv_exportado(args.holdout))

    # modelo de volatilidad, entrenado SOLO en TRAIN
    y_tr = etiqueta_vol(f_tr['high'].values, f_tr['low'].values,
                        f_tr['atr5'].values, args.hvol, args.k)
    m = y_tr != -1
    sc = StandardScaler().fit(f_tr[FEATURE_LIST].values[m])
    mod = LogisticRegression(max_iter=1000).fit(
        sc.transform(f_tr[FEATURE_LIST].values[m]), y_tr[m])
    p_vol = mod.predict_proba(sc.transform(f_ho[FEATURE_LIST].values))[:, 1]

    high, low = f_ho['high'].values, f_ho['low'].values
    close, atr = f_ho['close'].values, f_ho['atr5'].values
    n_ho = len(f_ho)
    print(f"HOLDOUT {n_ho} barras  {f_ho['fecha'].min()} -> {f_ho['fecha'].max()}")
    print(f"costo por operacion: {args.costo} (se paga DOS veces por par)\n")

    # ================= [A] =================
    print("=" * 76)
    print("[A] Abrir compra Y venta a la vez, en cada combinacion de objetivo/stop")
    print("=" * 76)
    print(f"  {'k_tp/k_sl':<12}{'filtro':<22}{'n':>7}{'% se movio':>12}"
          f"{'neto medio':>13}{'neto total':>13}")

    c70 = np.percentile(p_vol, 70)
    c90 = np.percentile(p_vol, 90)
    mejor = None
    for k_tp, k_sl in COMBOS:
        tp_arr, sl_arr = k_tp * atr, k_sl * atr
        lb, _ = etiquetar_tp_sl(high, low, close, tp_arr, sl_arr,
                                args.horizonte, 'BUY')
        ls, _ = etiquetar_tp_sl(high, low, close, tp_arr, sl_arr,
                                args.horizonte, 'SELL')
        for nombre, mask in (("todas las velas", np.ones(n_ho, bool)),
                             ("30% mas movido", p_vol >= c70),
                             ("10% mas movido", p_vol >= c90)):
            r = resultado_par(lb, ls, tp_arr, sl_arr, args.costo, mask)
            if r is None or r["n"] < 50:
                continue
            print(f"  {f'{k_tp}/{k_sl}':<12}{nombre:<22}{r['n']:>7}"
                  f"{r['pct_movio']:>11.1%}{r['neto_medio']:>13.2f}"
                  f"{r['neto_total']:>13,.0f}")
            if mejor is None or r["neto_medio"] > mejor[0]:
                mejor = (r["neto_medio"], k_tp, k_sl, nombre, r)
        print()

    if mejor:
        nm, k_tp, k_sl, filtro, r = mejor
        print(f"  MEJOR: k_tp={k_tp} k_sl={k_sl}, {filtro}")
        print(f"         {r['n']} pares, se movio el {r['pct_movio']:.1%}, "
              f"neto medio {nm:+.2f} por par")
        # punto de equilibrio: que % de veces tiene que moverse
        ganancia = k_tp - k_sl
        perdida = 2 * k_sl
        p_eq = (perdida + 2 * args.costo / atr.mean()) / (ganancia + perdida)
        print(f"         Para empatar hace falta que se mueva el {p_eq:.1%} "
              f"de las veces.")
        if nm > 0:
            print("         -> DA POSITIVO. Verificar en otros simbolos antes de creerlo.")
        else:
            print("         -> Da negativo: el movimiento no alcanza a cubrir el")
            print("            doble costo mas las veces que el precio zigzaguea.")

    # ================= [B] =================
    print("\n" + "=" * 76)
    print("[B] Tabla por hora del dia — donde esta el movimiento")
    print("=" * 76)
    y_ho = etiqueta_vol(high, low, atr, args.hvol, args.k)
    horas = pd.to_datetime(f_ho['fecha']).dt.hour.values
    ok = y_ho != -1
    print(f"  {'hora':>5}{'velas':>8}{'% movidas':>12}{'ATR medio':>12}")
    base = y_ho[ok].mean()
    filas = []
    for h in range(24):
        s = ok & (horas == h)
        if s.sum() < 50:
            continue
        pct = y_ho[s].mean()
        filas.append((h, int(s.sum()), pct, float(atr[s].mean())))
        marca = "  <<" if pct > base * 1.25 else ("  --" if pct < base * 0.75 else "")
        print(f"  {h:>5}{int(s.sum()):>8}{pct:>11.1%}{atr[s].mean():>12.2f}{marca}")
    print(f"\n  promedio del dia: {base:.1%}")
    if filas:
        top = sorted(filas, key=lambda x: -x[2])[:4]
        flo = sorted(filas, key=lambda x: x[2])[:4]
        print(f"  horas con MAS movimiento : "
              f"{', '.join(f'{h}h ({p:.0%})' for h, _, p, _ in top)}")
        print(f"  horas con MENOS          : "
              f"{', '.join(f'{h}h ({p:.0%})' for h, _, p, _ in flo)}")
    print("\n  (hora del servidor del broker, no la local)")


if __name__ == "__main__":
    main()
