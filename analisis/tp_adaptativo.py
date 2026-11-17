r"""
tp_adaptativo.py -- usar la prediccion de volatilidad para ajustar el objetivo.

Lo que sabemos hasta ahora:
  - La DIRECCION no se predice: AUC 0.49-0.55 en los 5 simbolos.
  - La VOLATILIDAD si: AUC 0.67-0.75 en los 5.
  - Usar la volatilidad como filtro (operar solo en momentos movidos) NO
    sirve: mejora en unos simbolos y empeora en otros, o sea que captura la
    direccion que tuvo cada mercado en ese periodo, no una regla general.

Queda una aplicacion que NO depende de acertar la direccion: si el modelo de
volatilidad avisa que viene movimiento, poner el objetivo mas lejos; si avisa
calma, mas cerca. No cambia cuantas veces se acierta, cambia cuanto se gana
cuando se acierta.

Metodo, sin hacer trampa:
  1. El modelo de volatilidad se entrena en TRAIN.
  2. Las velas de HOLDOUT_A se parten en tres grupos segun la volatilidad
     prevista (baja, media, alta). Para cada grupo se ELIGE el k_tp que
     mejor rinde, dejando el k_sl del modelo direccional.
  3. Esa regla se aplica a HOLDOUT_B, que no se toco, y se compara contra
     usar el k_tp fijo de siempre.

Si el k_tp elegido crece con la volatilidad prevista, la idea tiene sentido.
Si el resultado en HOLDOUT_B no mejora, no sirve y se descarta.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\tp_adaptativo.py --symbol NAS100 --version v6_20260914 ^
        --train datos\crudos\NAS100_TRAIN_2025-10-09_al_2026-06-03_M5.csv ^
        --holdout-a datos\crudos\NAS100_HOLDOUT_A_TPSL_2026-06-04_al_2026-07-23_M5.csv ^
        --holdout-b datos\crudos\NAS100_HOLDOUT_B_CONFIRM_2026-07-24_al_2026-09-13_M5.csv ^
        --costo 0.85
"""
import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import (cargar_csv_exportado, construir_features, etiquetar_tp_sl,
                  FEATURE_LIST)
from registry import Registry

K_TP_CANDIDATOS = [2, 3, 4, 6, 8]
NOMBRES = ["volatilidad BAJA", "volatilidad MEDIA", "volatilidad ALTA"]


def etiqueta_vol(high, low, atr, h, k):
    s_hi, s_lo = pd.Series(high), pd.Series(low)
    fut_max = s_hi.iloc[::-1].rolling(h).max().iloc[::-1].shift(-1)
    fut_min = s_lo.iloc[::-1].rolling(h).min().iloc[::-1].shift(-1)
    rec = (fut_max - fut_min).values
    y = np.full(len(high), -1, dtype=np.int8)
    ok = ~np.isnan(rec) & (atr > 0)
    y[ok] = (rec[ok] >= k * atr[ok]).astype(np.int8)
    return y


def pf_de(labels, mask, tp_arr, sl_arr, costo):
    n = int(mask.sum())
    if n == 0:
        return 0.0, 0, 0.0
    y = labels[mask]
    gan = tp_arr[mask][y == 1].sum()
    per = sl_arr[mask][y == 0].sum() + n * costo
    pf = gan / per if per > 0 else float("inf")
    return pf, n, float(y.mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--train", required=True)
    ap.add_argument("--holdout-a", required=True, dest="ha")
    ap.add_argument("--holdout-b", required=True, dest="hb")
    ap.add_argument("--costo", type=float, default=0.0)
    ap.add_argument("--horizonte", type=int, default=288)
    ap.add_argument("--horizonte-vol", type=int, default=24, dest="hvol")
    ap.add_argument("--k", type=float, default=6.0)
    args = ap.parse_args()

    symbol = args.symbol.upper()
    reg = Registry()
    entrada = reg._buscar(symbol, args.version)
    if entrada is None:
        raise SystemExit(f"No existe {symbol}/{args.version} en registry.json")
    paquete = joblib.load(entrada["archivo_modelo"])

    print(f"### {symbol} / {args.version} — objetivo adaptado a la volatilidad ###")

    f_tr = construir_features(cargar_csv_exportado(args.train))
    f_a = construir_features(cargar_csv_exportado(args.ha))
    f_b = construir_features(cargar_csv_exportado(args.hb))

    # --- modelo de volatilidad, entrenado SOLO en TRAIN ---
    y_tr = etiqueta_vol(f_tr['high'].values, f_tr['low'].values,
                        f_tr['atr5'].values, args.hvol, args.k)
    m = y_tr != -1
    sc = StandardScaler().fit(f_tr[FEATURE_LIST].values[m])
    mod_vol = LogisticRegression(max_iter=1000).fit(
        sc.transform(f_tr[FEATURE_LIST].values[m]), y_tr[m])
    pv_a = mod_vol.predict_proba(sc.transform(f_a[FEATURE_LIST].values))[:, 1]
    pv_b = mod_vol.predict_proba(sc.transform(f_b[FEATURE_LIST].values))[:, 1]
    print(f"modelo de volatilidad entrenado en TRAIN ({int(m.sum())} filas)\n")

    for lado_key, mod in paquete.items():
        lado = "BUY" if lado_key == "buy" else "SELL"
        k_tp_fijo, k_sl, umbral = mod["k_tp"], mod["k_sl"], mod["umbral"]
        print("=" * 72)
        print(f"{lado}   k_sl={k_sl} (fijo)   umbral={umbral}   "
              f"k_tp actual={k_tp_fijo}")
        print("=" * 72)

        # ---------- 1. elegir k_tp por grupo, en HOLDOUT_A ----------
        pd_a = mod["modelo"].predict_proba(
            mod["scaler"].transform(f_a[FEATURE_LIST].values))[:, 1]
        opera_a = pd_a >= umbral
        if opera_a.sum() < 150:
            print(f"  solo {int(opera_a.sum())} señales en HOLDOUT_A, "
                  f"muestra insuficiente\n")
            continue

        c1, c2 = np.percentile(pv_a[opera_a], [33, 66])
        grupos_a = [opera_a & (pv_a < c1),
                    opera_a & (pv_a >= c1) & (pv_a < c2),
                    opera_a & (pv_a >= c2)]

        labs_a = {}
        for ktp in K_TP_CANDIDATOS:
            labs_a[ktp], _ = etiquetar_tp_sl(
                f_a['high'].values, f_a['low'].values, f_a['close'].values,
                ktp * f_a['atr5'].values, k_sl * f_a['atr5'].values,
                args.horizonte, lado)

        print("\n  ELECCION en HOLDOUT_A (PF por k_tp):")
        print(f"  {'grupo':<20}" + "".join(f"{'k_tp='+str(k):>10}"
                                           for k in K_TP_CANDIDATOS)
              + f"{'elegido':>10}")
        elegidos = []
        for g, nom in zip(grupos_a, NOMBRES):
            fila, mejor, mejor_pf = "", None, -1
            for ktp in K_TP_CANDIDATOS:
                sel = g & (labs_a[ktp] != -1)
                pf, n, _ = pf_de(labs_a[ktp], sel, ktp * f_a['atr5'].values,
                                 k_sl * f_a['atr5'].values, args.costo)
                fila += f"{pf:>10.2f}"
                if n >= 30 and pf > mejor_pf:
                    mejor_pf, mejor = pf, ktp
            elegidos.append(mejor if mejor else k_tp_fijo)
            print(f"  {nom:<20}{fila}{str(elegidos[-1]):>10}")

        if elegidos[0] == elegidos[1] == elegidos[2]:
            print("\n  El mismo k_tp gana en los tres grupos -> adaptar no aporta.")

        # ---------- 2. aplicar en HOLDOUT_B ----------
        pd_b = mod["modelo"].predict_proba(
            mod["scaler"].transform(f_b[FEATURE_LIST].values))[:, 1]
        opera_b = pd_b >= umbral
        grupos_b = [opera_b & (pv_b < c1),
                    opera_b & (pv_b >= c1) & (pv_b < c2),
                    opera_b & (pv_b >= c2)]

        atr_b = f_b['atr5'].values
        sl_b = k_sl * atr_b
        labs_b = {}
        for ktp in set(elegidos + [k_tp_fijo]):
            labs_b[ktp], _ = etiquetar_tp_sl(
                f_b['high'].values, f_b['low'].values, f_b['close'].values,
                ktp * atr_b, sl_b, args.horizonte, lado)

        print("\n  RESULTADO en HOLDOUT_B (nunca tocado):")
        print(f"  {'':<20}{'n':>7}{'winrate':>10}{'PF':>9}")

        # fijo
        sel_fijo = opera_b & (labs_b[k_tp_fijo] != -1)
        pf_f, n_f, wr_f = pf_de(labs_b[k_tp_fijo], sel_fijo,
                                k_tp_fijo * atr_b, sl_b, args.costo)
        print(f"  {'k_tp fijo ('+str(k_tp_fijo)+')':<20}{n_f:>7}{wr_f:>10.1%}{pf_f:>9.3f}")

        # adaptativo
        gan = per = 0.0
        n_ad = ac = 0
        for g, ktp in zip(grupos_b, elegidos):
            sel = g & (labs_b[ktp] != -1)
            if sel.sum() == 0:
                continue
            y = labs_b[ktp][sel]
            gan += (ktp * atr_b)[sel][y == 1].sum()
            per += sl_b[sel][y == 0].sum() + int(sel.sum()) * args.costo
            n_ad += int(sel.sum()); ac += int((y == 1).sum())
        pf_ad = gan / per if per > 0 else float("inf")
        print(f"  {'k_tp adaptativo':<20}{n_ad:>7}"
              f"{(ac/n_ad if n_ad else 0):>10.1%}{pf_ad:>9.3f}")

        dif = pf_ad - pf_f
        print(f"\n  Diferencia de PF: {dif:+.3f}", end="  ")
        if pf_ad > 1.0 and dif > 0.05:
            print("-> el adaptativo mejora Y es rentable.")
        elif dif > 0.05:
            print("-> mejora, pero el PF sigue por debajo de 1: igual pierde.")
        else:
            print("-> no mejora.")
        print()

    print("=" * 72)
    print("Como leerlo:")
    print("  El k_tp elegido deberia CRECER de volatilidad BAJA a ALTA. Si no")
    print("  crece, la idea no tiene sustento y el resto es ruido.")
    print("  Y el PF del adaptativo tiene que superar 1.0, no solo al fijo:")
    print("  perder menos sigue siendo perder.")


if __name__ == "__main__":
    main()
