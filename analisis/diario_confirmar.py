r"""
diario_confirmar.py -- confirmar (o descartar) el resultado de la venta en diario.

Que aparecio: entrenando con 2017-2022 y midiendo sobre 2022-2024, la VENTA en
velas diarias dio AUC 0.667 contra un control de 0.638. Es el primer resultado
direccional del proyecto que supera a su control.

Por que no alcanza:
  - el margen es de menos de 3 centesimas
  - la compra dio 0.538 contra 0.592, o sea NO da
  - y sobre todo: el tramo de prueba era 2022-2024, que incluye la caida grande
    de 2022. Un modelo que aprendio a vender, midiendo sobre un tramo bajista,
    va a lucir bien aunque no sepa nada.

Este script entrena con TODO el archivo TRAIN (2017-2024) y mide por separado
sobre dos periodos que nunca vio y que fueron de mercado subiendo:
    HOLDOUT_A  2024-01 a 2025-05
    HOLDOUT_B  2025-05 a hoy

Si la venta funciona tambien ahi, el resultado es real. Si solo funciona en
2022-2024, era el mercado y no el modelo.

Ademas del AUC mide la RENTABILIDAD, porque un AUC de 0.667 puede no alcanzar
para ganar dinero despues de pagar el spread. Y compara contra operar todas
las velas, que es la referencia honesta.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\diario_confirmar.py ^
        --train    datos\crudos\NAS100_TRAIN_2017-10-16_al_2024-01-21_D1.csv ^
        --holdout-a datos\crudos\NAS100_HOLDOUT_A_TPSL_2024-01-22_al_2025-05-26_D1.csv ^
        --holdout-b datos\crudos\NAS100_HOLDOUT_B_CONFIRM_2025-05-27_al_2026-09-28_D1.csv ^
        --costo 0.85
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import cargar_csv_exportado, construir_features, etiquetar_tp_sl, FEATURE_LIST

VARS = [v for v in FEATURE_LIST if v not in ("hora_sin", "hora_cos")]
N_PERM = 300


def preparar(ruta):
    f = construir_features(cargar_csv_exportado(ruta))
    return f.replace([np.inf, -np.inf], np.nan).dropna(subset=VARS).reset_index(drop=True)


def etiquetar(f, k_tp, k_sl, horizonte, lado):
    atr = f["atr5"].values
    return etiquetar_tp_sl(f["high"].values, f["low"].values, f["close"].values,
                           k_tp * atr, k_sl * atr, horizonte, lado)[0]


def pf(y, tp, sl, costo):
    n = len(y)
    if n == 0:
        return float("nan"), 0, float("nan")
    gan = tp[y == 1].sum()
    per = sl[y == 0].sum() + n * costo
    return (gan / per if per > 0 else float("inf")), n, float((y == 1).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--holdout-a", required=True, dest="ha")
    ap.add_argument("--holdout-b", required=True, dest="hb")
    ap.add_argument("--costo", type=float, default=0.0)
    ap.add_argument("--horizonte", type=int, default=10)
    ap.add_argument("--k-tp", type=float, default=2.0, dest="k_tp")
    ap.add_argument("--k-sl", type=float, default=1.0, dest="k_sl")
    ap.add_argument("--umbral", type=float, default=0.55,
                    help="probabilidad minima para operar, fijada de antemano")
    args = ap.parse_args()

    f_tr, f_a, f_b = (preparar(r) for r in (args.train, args.ha, args.hb))
    print("### NAS100 diario — confirmacion en periodos nunca vistos ###")
    for nom, f in (("entrenamiento", f_tr), ("HOLDOUT_A", f_a), ("HOLDOUT_B", f_b)):
        print(f"  {nom:<14}{len(f):>5} velas   "
              f"{f['fecha'].iloc[0].date()} -> {f['fecha'].iloc[-1].date()}   "
              f"precio {f['close'].iloc[0]:,.0f} -> {f['close'].iloc[-1]:,.0f}")
    print(f"\nobjetivo {args.k_tp} ATR, stop {args.k_sl} ATR, "
          f"horizonte {args.horizonte} dias, umbral {args.umbral}, costo {args.costo}")

    rng = np.random.default_rng(0)
    for lado in ("SELL", "BUY"):
        nombre = "VENTA" if lado == "SELL" else "COMPRA"
        y_tr = etiquetar(f_tr, args.k_tp, args.k_sl, args.horizonte, lado)
        m = y_tr != -1
        X_tr = f_tr[VARS].values[m]
        sc = StandardScaler().fit(X_tr)
        mod = LogisticRegression(max_iter=2000).fit(sc.transform(X_tr), y_tr[m])

        print("\n" + "=" * 72)
        print(f"{nombre}   ({int(m.sum())} operaciones de entrenamiento, "
              f"{y_tr[m].mean():.0%} ganadoras)")
        print("=" * 72)
        print(f"  {'periodo':<14}{'n':>5}{'AUC':>8}{'azar':>8}"
              f"{'n opera':>9}{'acierto':>9}{'PF':>8}{'PF todas':>10}")

        for nom, f in (("HOLDOUT_A", f_a), ("HOLDOUT_B", f_b)):
            y = etiquetar(f, args.k_tp, args.k_sl, args.horizonte, lado)
            mk = y != -1
            if mk.sum() < 40 or len(np.unique(y[mk])) < 2:
                print(f"  {nom:<14}{int(mk.sum()):>5}   muestra insuficiente")
                continue
            X = f[VARS].values[mk]
            p = mod.predict_proba(sc.transform(X))[:, 1]
            auc = roc_auc_score(y[mk], p)
            # control: el mismo modelo sobre etiquetas mezcladas
            nul = np.array([roc_auc_score(rng.permutation(y[mk]), p)
                            for _ in range(N_PERM)])
            p95 = np.percentile(nul, 95)

            atr = f["atr5"].values[mk]
            tp_a, sl_a = args.k_tp * atr, args.k_sl * atr
            opera = p >= args.umbral
            pf_op, n_op, wr = pf(y[mk][opera], tp_a[opera], sl_a[opera], args.costo)
            pf_todas, _, _ = pf(y[mk], tp_a, sl_a, args.costo)

            marca = "  <-- supera al azar" if auc > p95 else ""
            print(f"  {nom:<14}{int(mk.sum()):>5}{auc:>8.3f}{p95:>8.3f}"
                  f"{n_op:>9}{wr:>9.1%}{pf_op:>8.3f}{pf_todas:>10.3f}{marca}")

    print("\n" + "=" * 72)
    print("Como leerlo:")
    print("  Para creer el resultado de la venta hacen falta TRES cosas a la vez:")
    print("    1. que el AUC supere al del azar en los DOS periodos, no en uno")
    print("    2. que el PF del modelo supere 1")
    print("    3. que el PF del modelo supere al de operar TODAS las velas")
    print("  La tercera es la mas importante: si operar siempre rinde igual, el")
    print("  modelo no aporta nada y lo que se esta midiendo es el mercado.")


if __name__ == "__main__":
    main()
