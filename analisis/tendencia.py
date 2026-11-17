r"""
tendencia.py -- prueba de la propuesta: entrada simple de tendencia + filtro
de volatilidad, en lugar del modelo de direccion.

La propuesta dice:
  - dejar de usar el modelo de direccion (AUC 0.49-0.55, no predice)
  - entrar con una regla simple y mecanica, por ejemplo seguir la tendencia
  - usar el modelo de volatilidad (AUC 0.67-0.75) como filtro, excluyendo los
    momentos de movimiento extremo

Este script la mide tal cual, antes de tocar el EA.

REGLAS (fijadas ANTES de ver resultados, para no elegir la que tuvo suerte):
  Tendencia alcista = precio por encima de la EMA200 y EMA50 por encima de la
  EMA200. Bajista = lo contrario.
    R1  tendencia pura: operar a favor de la tendencia en cualquier vela.
    R2  tendencia + cruce del MACD: entrar cuando el histograma cruza cero a
        favor de la tendencia.
    R3  tendencia + retroceso: en tendencia alcista comprar cuando el RSI(5)
        baja de 35; en bajista vender cuando sube de 65.

  Objetivo 2 ATR, stop 1 ATR, en todas. Fijo, sin barrido.

FILTROS de volatilidad (modelo entrenado solo en TRAIN):
    sin filtro
    sin extremos : no operar en el 10% de velas con mas movimiento previsto
                   (lo que propone la otra sugerencia)
    sin calma    : no operar en el 20% con menos movimiento previsto
                   (la hipotesis contraria: con objetivo en ATR y spread fijo,
                   el costo pesa MAS cuando hay poco movimiento)

REFERENCIA: operar TODAS las velas en esa direccion, sin regla. Una regla que
no supere eso no aporta nada.

Todo se mide en HOLDOUT_B, que ningun modelo ni regla vio. Se informa el PF
por vela (como validar.py) y el PF SECUENCIAL (una operacion por vez, que es
como opera el EA de verdad).

CRITERIO DE EXITO: la misma regla y el mismo filtro tienen que dar PF
secuencial por encima de 1 en al menos 4 de los 5 simbolos. Si no, se
descarta, igual que todo lo anterior.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\tendencia.py --symbol US30 --costo 1.95 ^
        --train   datos\crudos\US30_TRAIN_2025-10-09_al_2026-06-03_M5.csv ^
        --holdout datos\crudos\US30_HOLDOUT_B_CONFIRM_2026-07-24_al_2026-09-13_M5.csv
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

K_TP, K_SL = 2.0, 1.0


def etiqueta_vol(high, low, atr, h=24, k=6.0):
    s_hi, s_lo = pd.Series(high), pd.Series(low)
    fut_max = s_hi.iloc[::-1].rolling(h).max().iloc[::-1].shift(-1)
    fut_min = s_lo.iloc[::-1].rolling(h).min().iloc[::-1].shift(-1)
    rec = (fut_max - fut_min).values
    y = np.full(len(high), -1, dtype=np.int8)
    ok = ~np.isnan(rec) & (atr > 0)
    y[ok] = (rec[ok] >= k * atr[ok]).astype(np.int8)
    return y


def reglas(f):
    """Devuelve {nombre: (mascara_compra, mascara_venta)}."""
    alcista = (f["rel_ema200"].values < 0) & (f["rel_ema50_200"].values > 0)
    bajista = (f["rel_ema200"].values > 0) & (f["rel_ema50_200"].values < 0)
    h = f["macd_hist_rel"].values
    h_prev = np.r_[np.nan, h[:-1]]
    cruce_up = (h_prev <= 0) & (h > 0)
    cruce_dn = (h_prev >= 0) & (h < 0)
    rsi = f["rsi5"].values
    return {
        "R1 tendencia pura":        (alcista, bajista),
        "R2 tendencia + cruce MACD": (alcista & cruce_up, bajista & cruce_dn),
        "R3 tendencia + retroceso":  (alcista & (rsi < 35), bajista & (rsi > 65)),
    }


def medir(mask, labels, velas, tp_arr, sl_arr, costo):
    """PF por vela y PF secuencial (una operacion por vez)."""
    ok = mask & (labels != -1)
    n = int(ok.sum())
    if n < 30:
        return None
    y = labels[ok]
    gan = tp_arr[ok][y == 1].sum()
    per = sl_arr[ok][y == 0].sum() + n * costo
    pf = gan / per if per > 0 else float("inf")

    g2 = p2 = 0.0
    n2 = 0
    t, N = 0, len(labels)
    while t < N:
        if ok[t]:
            n2 += 1
            if labels[t] == 1:
                g2 += tp_arr[t]
            else:
                p2 += sl_arr[t]
            p2 += costo
            t += max(1, int(velas[t])) + 1
        else:
            t += 1
    pf2 = g2 / p2 if p2 > 0 else float("inf")
    return dict(n=n, wr=float(y.mean()), pf=pf, n2=n2, pf2=pf2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--train", required=True)
    ap.add_argument("--holdout", required=True)
    ap.add_argument("--costo", type=float, default=0.0)
    ap.add_argument("--horizonte", type=int, default=288)
    args = ap.parse_args()

    print(f"### {args.symbol.upper()} — tendencia simple + filtro de volatilidad ###")
    print(f"objetivo {K_TP} ATR, stop {K_SL} ATR, costo {args.costo}\n")

    f_tr = construir_features(cargar_csv_exportado(args.train))
    f_ho = construir_features(cargar_csv_exportado(args.holdout))

    # --- modelo de volatilidad, entrenado solo en TRAIN ---
    y_tr = etiqueta_vol(f_tr["high"].values, f_tr["low"].values, f_tr["atr5"].values)
    m = y_tr != -1
    sc = StandardScaler().fit(f_tr[FEATURE_LIST].values[m])
    mv = LogisticRegression(max_iter=1000).fit(
        sc.transform(f_tr[FEATURE_LIST].values[m]), y_tr[m])
    pv_tr = mv.predict_proba(sc.transform(f_tr[FEATURE_LIST].values))[:, 1]
    pv_ho = mv.predict_proba(sc.transform(f_ho[FEATURE_LIST].values))[:, 1]
    corte_alto = np.percentile(pv_tr, 90)   # cortes fijados en TRAIN
    corte_bajo = np.percentile(pv_tr, 20)
    filtros = {
        "sin filtro":   np.ones(len(f_ho), bool),
        "sin extremos": pv_ho < corte_alto,
        "sin calma":    pv_ho > corte_bajo,
    }

    high, low = f_ho["high"].values, f_ho["low"].values
    close, atr = f_ho["close"].values, f_ho["atr5"].values
    tp_arr, sl_arr = K_TP * atr, K_SL * atr
    R = reglas(f_ho)
    print(f"HOLDOUT {len(f_ho)} barras  {f_ho['fecha'].min()} -> {f_ho['fecha'].max()}\n")

    resumen = []
    for i_lado, lado in enumerate(("BUY", "SELL")):
        labels, velas = etiquetar_tp_sl(high, low, close, tp_arr, sl_arr,
                                        args.horizonte, lado)
        print("=" * 78)
        print(f"{'COMPRA' if lado == 'BUY' else 'VENTA'}")
        print("=" * 78)
        print(f"  {'regla':<27}{'filtro':<14}{'n':>6}{'acierto':>9}"
              f"{'PF vela':>9}{'n sec':>7}{'PF sec':>8}")
        ref = medir(np.ones(len(f_ho), bool), labels, velas, tp_arr, sl_arr, args.costo)
        print(f"  {'REFERENCIA: todas las velas':<41}{ref['n']:>6}{ref['wr']:>9.1%}"
              f"{ref['pf']:>9.3f}{ref['n2']:>7}{ref['pf2']:>8.3f}")
        for nombre, masks in R.items():
            for fn, fm in filtros.items():
                r = medir(masks[i_lado] & fm, labels, velas, tp_arr, sl_arr, args.costo)
                if r is None:
                    print(f"  {nombre:<27}{fn:<14}{'(menos de 30 operaciones)':>39}")
                    continue
                marca = "  <-- supera 1 y a la referencia" if (
                    r["pf2"] > 1.0 and r["pf2"] > ref["pf2"]) else ""
                print(f"  {nombre:<27}{fn:<14}{r['n']:>6}{r['wr']:>9.1%}"
                      f"{r['pf']:>9.3f}{r['n2']:>7}{r['pf2']:>8.3f}{marca}")
                resumen.append((lado, nombre, fn, r["pf2"], ref["pf2"]))
        print()

    print("=" * 78)
    print("RESUMEN para comparar entre simbolos (PF secuencial):")
    for lado, nombre, fn, pf2, rf in resumen:
        estado = "GANA" if pf2 > 1 else "pierde"
        print(f"  {lado:<5}{nombre:<27}{fn:<14}{pf2:>7.3f}  {estado}"
              f"{'  (mejor que operar siempre)' if pf2 > rf else ''}")
    print("\nCriterio: una combinacion regla+filtro vale solo si GANA en al menos")
    print("4 de los 5 simbolos. Si gana en uno o dos, es azar.")


if __name__ == "__main__":
    main()
