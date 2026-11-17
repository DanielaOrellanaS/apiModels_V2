r"""
tres_clases.py -- el modelo decide COMPRAR, VENDER o NO OPERAR.

Es lo unico del plan del transformer que no estaba medido. El resto ya estaba:
la triple barrera es lo que hace etiquetar_tp_sl desde el principio, las
variables ya son relativas (rel_ema50, atr_rel, macd_rel), la vela de 15
minutos se arreglo el 9-sep, los holdouts ya son cronologicos y el costo ya
entra en todas las cuentas. Y comparar contra un baseline simple ya se hizo
con redes neuronales: ninguna le gano a la regresion.

QUE CAMBIA ACA

Hasta ahora se entrenaba un modelo por lado: uno decidia "¿conviene comprar?"
y otro "¿conviene vender?". Cada uno respondia si o no.

Aca hay un solo modelo con TRES respuestas posibles:
    COMPRAR   la vela habria ganado comprando
    VENDER    la vela habria ganado vendiendo
    NO OPERAR ninguna de las dos habria ganado

La idea del plan es que poder decir "no operar" es lo que mas ayuda a perder
poco. Y ademas solo se opera cuando la confianza supera un umbral, asi que el
modelo puede quedarse quieto casi siempre y actuar solo cuando esta seguro.

COMO SE MIDE

Se recorre el umbral de confianza de 0.40 a 0.90. Para cada valor:
    cuantas operaciones quedan, el acierto y la rentabilidad

y se compara contra DOS controles:
    operar todas las velas    la referencia honesta
    confianza al azar         mismas operaciones, pero elegidas al azar. Si el
                              modelo no le gana, su "confianza" no significa
                              nada y lo que se ve es el efecto de operar menos

Todo entrenado con el tramo mas viejo y medido en los dos periodos siguientes,
que el modelo no ve.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\tres_clases.py --costo 0.85 ^
        --train     datos\crudos\NAS100_TRAIN_2025-10-09_al_2026-06-03_M5.csv ^
        --holdout-a datos\crudos\NAS100_HOLDOUT_A_TPSL_2026-06-04_al_2026-07-23_M5.csv ^
        --holdout-b datos\crudos\NAS100_HOLDOUT_B_CONFIRM_2026-07-24_al_2026-09-13_M5.csv

Para velas diarias: agregar --horizonte 10
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import cargar_csv_exportado, construir_features, etiquetar_tp_sl, FEATURE_LIST

UMBRALES = [0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
NADA, COMPRAR, VENDER = 0, 1, 2


def preparar(ruta, variables):
    f = construir_features(cargar_csv_exportado(ruta))
    return (f.replace([np.inf, -np.inf], np.nan)
             .dropna(subset=variables).reset_index(drop=True))


def etiquetas_tres(f, k_tp, k_sl, horizonte):
    """0 = no operar, 1 = comprar, 2 = vender. Las dos no pueden ganar a la
    vez: si el precio llega al objetivo de compra, toca el stop de venta."""
    atr = f["atr5"].values
    hi, lo, cl = f["high"].values, f["low"].values, f["close"].values
    yb, _ = etiquetar_tp_sl(hi, lo, cl, k_tp * atr, k_sl * atr, horizonte, "BUY")
    ys, _ = etiquetar_tp_sl(hi, lo, cl, k_tp * atr, k_sl * atr, horizonte, "SELL")
    y = np.full(len(f), -1, dtype=int)
    ok = (yb != -1) & (ys != -1)
    y[ok] = NADA
    y[ok & (yb == 1)] = COMPRAR
    y[ok & (ys == 1)] = VENDER
    return y, yb, ys


def resultado(sel, lados, yb, ys, tp_arr, sl_arr, costo):
    """Resultado de operar las velas de `sel` en la direccion de `lados`."""
    n = int(sel.sum())
    if n == 0:
        return None
    gano = np.where(lados[sel] == COMPRAR, yb[sel] == 1, ys[sel] == 1)
    gan = tp_arr[sel][gano].sum()
    per = sl_arr[sel][~gano].sum() + n * costo
    return dict(n=n, wr=float(gano.mean()),
                pf=gan / per if per > 0 else float("inf"),
                total=float(gan - per))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--holdout-a", required=True, dest="ha")
    ap.add_argument("--holdout-b", required=True, dest="hb")
    ap.add_argument("--costo", type=float, default=0.0)
    ap.add_argument("--horizonte", type=int, default=288)
    ap.add_argument("--k-tp", type=float, default=2.0, dest="k_tp")
    ap.add_argument("--k-sl", type=float, default=1.0, dest="k_sl")
    args = ap.parse_args()

    diario = args.horizonte <= 30
    variables = [v for v in FEATURE_LIST if not (diario and v.startswith("hora_"))]
    f_tr, f_a, f_b = (preparar(r, variables) for r in (args.train, args.ha, args.hb))

    print("### Modelo de TRES CLASES: comprar, vender o no operar — NAS100 ###")
    for nom, f in (("entrenamiento", f_tr), ("HOLDOUT_A", f_a), ("HOLDOUT_B", f_b)):
        print(f"  {nom:<14}{len(f):>6} velas  {f['fecha'].iloc[0].date()} -> "
              f"{f['fecha'].iloc[-1].date()}")
    print(f"objetivo {args.k_tp} ATR, stop {args.k_sl} ATR, "
          f"horizonte {args.horizonte} velas, costo {args.costo}")

    y_tr, _, _ = etiquetas_tres(f_tr, args.k_tp, args.k_sl, args.horizonte)
    m = y_tr != -1
    X = f_tr[variables].values[m]
    sc = StandardScaler().fit(X)
    mod = LogisticRegression(max_iter=3000, multi_class="multinomial").fit(
        sc.transform(X), y_tr[m])

    rep = np.bincount(y_tr[m], minlength=3) / m.sum()
    print(f"\nreparto en el entrenamiento ({int(m.sum())} velas):")
    print(f"  no operar {rep[NADA]:.1%}   comprar {rep[COMPRAR]:.1%}   "
          f"vender {rep[VENDER]:.1%}")

    rng = np.random.default_rng(0)
    for nom, f in (("HOLDOUT_A", f_a), ("HOLDOUT_B", f_b)):
        y, yb, ys = etiquetas_tres(f, args.k_tp, args.k_sl, args.horizonte)
        ok = y != -1
        atr = f["atr5"].values
        tp_arr, sl_arr = args.k_tp * atr, args.k_sl * atr
        p = mod.predict_proba(sc.transform(f[variables].values))
        pred = p.argmax(axis=1)
        conf = p.max(axis=1)

        print("\n" + "=" * 74)
        print(f"{nom}   {f['fecha'].iloc[0].date()} -> {f['fecha'].iloc[-1].date()}")
        print("=" * 74)
        print(f"  {'':<30}{'n':>7}{'acierto':>9}{'PF':>8}{'total':>12}")

        # referencia 1: operar todas las velas, comprando siempre
        todas = ok.copy()
        lados_c = np.full(len(f), COMPRAR)
        r = resultado(todas, lados_c, yb, ys, tp_arr, sl_arr, args.costo)
        print(f"  {'REFERENCIA: comprar siempre':<30}{r['n']:>7}{r['wr']:>9.1%}"
              f"{r['pf']:>8.3f}{r['total']:>12,.0f}")

        for u in UMBRALES:
            sel = ok & (pred != NADA) & (conf >= u)
            r = resultado(sel, pred, yb, ys, tp_arr, sl_arr, args.costo)
            if r is None or r["n"] < 30:
                print(f"  {f'confianza >= {u:.2f}':<30}"
                      f"{int(sel.sum()):>7}   muestra insuficiente")
                continue
            # control: la misma cantidad de velas, elegidas al azar, con la
            # direccion que el modelo habria elegido
            idx = np.where(ok & (pred != NADA))[0]
            if len(idx) >= r["n"]:
                azar = np.zeros(len(f), bool)
                azar[rng.choice(idx, r["n"], replace=False)] = True
                ra = resultado(azar, pred, yb, ys, tp_arr, sl_arr, args.costo)
                ctrl = f"{ra['pf']:.3f}"
            else:
                ctrl = "-"
            marca = "  <-- gana y supera al control" if (
                r["pf"] > 1.0 and ctrl != "-" and r["pf"] > float(ctrl)) else ""
            print(f"  {f'confianza >= {u:.2f}':<30}{r['n']:>7}{r['wr']:>9.1%}"
                  f"{r['pf']:>8.3f}{r['total']:>12,.0f}"
                  f"   control azar {ctrl}{marca}")

    print("\n" + "=" * 74)
    print("Como leerlo:")
    print("  Subir el umbral opera menos veces. Eso solo por si mismo ya cambia")
    print("  los numeros, por eso esta el control: son las MISMAS operaciones en")
    print("  cantidad, pero elegidas al azar. Si el modelo no le gana, su")
    print("  confianza no informa nada y lo unico que hizo fue operar menos.")
    print("  Y tiene que dar PF mayor a 1 en LOS DOS periodos, no en uno.")


if __name__ == "__main__":
    main()
