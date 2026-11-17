r"""
nas100_diario.py -- modelo nuevo para NAS100 en velas diarias.

SOLO NAS100. Es una prueba OFFLINE sobre los CSV: no necesita servidor, ni
endpoint, ni que el EA consulte nada.

Que hace distinto a todo lo probado antes:

  No intenta predecir la direccion. Eso se midio en tres horizontes (5 min,
  1 hora y diario), en cinco mercados, con hasta 38 variables y nueve años de
  historial. El AUC siempre quedo entre 0.48 y 0.58, es decir, en el azar.

  En cambio usa lo unico que SI se predice: la volatilidad, que dio AUC 0.67 a
  0.75 en los cinco simbolos. Pero no la usa como filtro (eso ya fallo tres
  veces). La usa para decidir CUANTO arriesgar en cada operacion.

  La idea: arriesgar menos cuando se espera movimiento fuerte y mas cuando se
  espera calma. No cambia cuantas veces se acierta; cambia cuanto se gana y se
  pierde en cada caso. Es lo unico que apunta directamente a "perder menos",
  que es lo que se pidio.

  Y agrega un limite de perdida acumulada: si la racha negativa pasa de cierto
  porcentaje, se deja de operar por N dias. Eso no mejora el promedio, pero
  corta las rachas malas.

ENTRADAS (3 variantes fijadas de antemano, ninguna mas):
  E1  seguir la tendencia: comprar si el cierre esta sobre la media de 200 y
      la de 50 sobre la de 200; vender al reves.
  E2  retroceso: comprar la caida dentro de una subida (RSI bajo en tendencia
      alcista) y vender el rebote dentro de una bajada.
  E3  siempre comprado: la referencia honesta. El indice sube a largo plazo, y
      cualquier regla tiene que ganarle a esto para valer algo.

TAMAÑOS (3 variantes):
  fijo        el mismo en todas
  volatilidad inversamente proporcional a la volatilidad prevista
  al azar     CONTROL: el mismo reparto de tamaños, pero asignado al azar.
              Si el de volatilidad no le gana a este, no aporta nada.

PROTOCOLO: todo se entrena hasta 2024 y se mide por separado en los dos
periodos siguientes, que el modelo nunca vio.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\nas100_diario.py ^
        --train     datos\crudos\NAS100_TRAIN_2017-10-16_al_2024-01-21_D1.csv ^
        --holdout-a datos\crudos\NAS100_HOLDOUT_A_TPSL_2024-01-22_al_2025-05-26_D1.csv ^
        --holdout-b datos\crudos\NAS100_HOLDOUT_B_CONFIRM_2025-05-27_al_2026-09-28_D1.csv ^
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

from core import cargar_csv_exportado, construir_features, etiquetar_tp_sl, FEATURE_LIST

VARS = [v for v in FEATURE_LIST if v not in ("hora_sin", "hora_cos")]
K_TP, K_SL = 2.0, 1.0
HORIZONTE = 10          # dias para resolver la operacion
HORIZ_VOL = 5           # dias hacia adelante para la etiqueta de volatilidad
K_VOL = 3.0             # "movido" = recorre mas de 3 ATR en esos dias


def preparar(ruta):
    f = construir_features(cargar_csv_exportado(ruta))
    return f.replace([np.inf, -np.inf], np.nan).dropna(subset=VARS).reset_index(drop=True)


def etiqueta_vol(f):
    hi, lo = pd.Series(f["high"].values), pd.Series(f["low"].values)
    fmax = hi.iloc[::-1].rolling(HORIZ_VOL).max().iloc[::-1].shift(-1)
    fmin = lo.iloc[::-1].rolling(HORIZ_VOL).min().iloc[::-1].shift(-1)
    rec = (fmax - fmin).values
    atr = f["atr5"].values
    y = np.full(len(f), -1, dtype=int)
    ok = ~np.isnan(rec) & (atr > 0)
    y[ok] = (rec[ok] >= K_VOL * atr[ok]).astype(int)
    return y


def entradas(f):
    alc = (f["rel_ema200"].values < 0) & (f["rel_ema50_200"].values > 0)
    baj = (f["rel_ema200"].values > 0) & (f["rel_ema50_200"].values < 0)
    rsi = f["rsi5"].values
    n = len(f)
    return {
        "E1 tendencia":     (alc, baj),
        "E2 retroceso":     (alc & (rsi < 40), baj & (rsi > 60)),
        "E3 siempre compra": (np.ones(n, bool), np.zeros(n, bool)),
    }


def simular(f, compra, venta, tam, costo, tope_perdida, dias_pausa):
    """Una operacion por vez. Devuelve el resultado en unidades de riesgo:
    cada operacion arriesga `tam` veces el riesgo base, asi que el resultado
    es comparable entre politicas de tamaño."""
    atr = f["atr5"].values
    lab_c, vel_c = etiquetar_tp_sl(f["high"].values, f["low"].values,
                                   f["close"].values, K_TP * atr, K_SL * atr,
                                   HORIZONTE, "BUY")
    lab_v, vel_v = etiquetar_tp_sl(f["high"].values, f["low"].values,
                                   f["close"].values, K_TP * atr, K_SL * atr,
                                   HORIZONTE, "SELL")
    res, acum, pausa_hasta = [], 0.0, -1
    t, n = 0, len(f)
    while t < n - 1:
        if t <= pausa_hasta:
            t += 1
            continue
        if compra[t] and lab_c[t] != -1:
            lab, vel = lab_c[t], vel_c[t]
        elif venta[t] and lab_v[t] != -1:
            lab, vel = lab_v[t], vel_v[t]
        else:
            t += 1
            continue
        # el costo se expresa como fraccion del riesgo de esa operacion
        c = costo / (K_SL * atr[t]) if atr[t] > 0 else 0.0
        r = (K_TP / K_SL if lab == 1 else -1.0) * tam[t] - c * tam[t]
        res.append(r)
        acum = min(0.0, acum + r) if r < 0 else 0.0
        if tope_perdida > 0 and acum <= -tope_perdida:
            pausa_hasta = t + dias_pausa
            acum = 0.0
        t += max(1, int(vel)) + 1
    return np.array(res)


def resumen(r):
    if len(r) == 0:
        return None
    g, p = r[r > 0].sum(), -r[r < 0].sum()
    peor = 0.0
    acum = 0.0
    pico = 0.0
    for x in r:
        acum += x
        pico = max(pico, acum)
        peor = min(peor, acum - pico)
    return dict(n=len(r), wr=float((r > 0).mean()),
                pf=g / p if p > 0 else float("inf"),
                total=float(r.sum()), peor=peor)


def linea(nombre, d):
    if d is None:
        return f"    {nombre:<26}{'sin operaciones':>40}"
    return (f"    {nombre:<26}{d['n']:>6}{d['wr']:>9.1%}{d['pf']:>8.3f}"
            f"{d['total']:>10.1f}{d['peor']:>12.1f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--holdout-a", required=True, dest="ha")
    ap.add_argument("--holdout-b", required=True, dest="hb")
    ap.add_argument("--costo", type=float, default=0.0)
    ap.add_argument("--tope-perdida", type=float, default=6.0, dest="tope",
                    help="pausar tras perder esto en unidades de riesgo (0 = sin tope)")
    ap.add_argument("--dias-pausa", type=int, default=10, dest="pausa")
    args = ap.parse_args()

    f_tr, f_a, f_b = (preparar(r) for r in (args.train, args.ha, args.hb))
    print("### NAS100 diario — entrada simple + tamaño segun volatilidad ###")
    for nom, f in (("entrenamiento", f_tr), ("HOLDOUT_A", f_a), ("HOLDOUT_B", f_b)):
        print(f"  {nom:<14}{len(f):>5} velas  {f['fecha'].iloc[0].date()} -> "
              f"{f['fecha'].iloc[-1].date()}  precio {f['close'].iloc[0]:,.0f} -> "
              f"{f['close'].iloc[-1]:,.0f}")

    # modelo de volatilidad, entrenado SOLO con el tramo de entrenamiento
    y = etiqueta_vol(f_tr)
    m = y != -1
    sc = StandardScaler().fit(f_tr[VARS].values[m])
    mod = LogisticRegression(max_iter=2000).fit(sc.transform(f_tr[VARS].values[m]), y[m])
    print(f"\nmodelo de volatilidad: {int(m.sum())} dias, "
          f"{y[m].mean():.0%} con movimiento fuerte")
    print(f"objetivo {K_TP} ATR, stop {K_SL} ATR, horizonte {HORIZONTE} dias, "
          f"costo {args.costo}")
    print(f"tope de perdida: {args.tope} unidades, pausa {args.pausa} dias")
    print("\nEl resultado esta en UNIDADES DE RIESGO: +2 = gano el objetivo,")
    print("-1 = toco el stop. 'peor racha' es la mayor caida acumulada.")

    rng = np.random.default_rng(0)
    for nom, f in (("HOLDOUT_A", f_a), ("HOLDOUT_B", f_b)):
        p = mod.predict_proba(sc.transform(f[VARS].values))[:, 1]
        # tamaño inverso a la volatilidad prevista: 0.5x si viene movido, 1.5x si calma
        tam_vol = 1.5 - p
        tam_vol = np.clip(tam_vol / tam_vol.mean(), 0.4, 1.6)
        tam_fijo = np.ones(len(f))
        tam_azar = rng.permutation(tam_vol)

        print("\n" + "=" * 78)
        print(f"{nom}   {f['fecha'].iloc[0].date()} -> {f['fecha'].iloc[-1].date()}")
        print("=" * 78)
        print(f"    {'':<26}{'n':>6}{'acierto':>9}{'PF':>8}{'total':>10}"
              f"{'peor racha':>12}")
        for ent, (c, v) in entradas(f).items():
            print(f"  {ent}")
            for tnom, tam in (("tamaño fijo", tam_fijo),
                              ("tamaño x volatilidad", tam_vol),
                              ("CONTROL: tamaño al azar", tam_azar)):
                r = simular(f, c, v, tam, args.costo, args.tope, args.pausa)
                print(linea(tnom, resumen(r)))

    print("\n" + "=" * 78)
    print("Como leerlo:")
    print("  1. Comparar 'tamaño x volatilidad' contra 'CONTROL: tamaño al azar'.")
    print("     Si empatan, ajustar el tamaño segun la volatilidad no aporta nada")
    print("     y lo que se ve es el efecto de tener tamaños distintos, no de")
    print("     elegirlos bien.")
    print("  2. Comparar E1 y E2 contra E3 (siempre comprado). El indice sube a")
    print("     largo plazo: una regla que no le gana a estar comprado no sirve.")
    print("  3. Mirar la peor racha, no solo el total: es lo que mide 'perder menos'.")
    print("  4. Y tiene que cumplirse en LOS DOS periodos, no en uno.")


if __name__ == "__main__":
    main()
