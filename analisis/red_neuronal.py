r"""
red_neuronal.py -- probar una red neuronal en NAS100, con los controles que
hacen falta para que el resultado signifique algo.

SOLO NAS100. Prueba OFFLINE: no necesita servidor ni endpoint.

Usa MLPClassifier de scikit-learn, que ya esta instalado. No hace falta PyTorch
ni instalar nada.

POR QUE HAY QUE SER CUIDADOSO ACA

Una red tiene miles de parametros. Con pocos casos independientes no aprende:
memoriza. Y como memoriza muy bien, muestra numeros excelentes en el
entrenamiento que despues no se repiten.

Cuantos casos independientes hay de verdad: en diario son 2313 velas, pero cada
operacion dura 10 dias y se pisan entre si, asi que quedan unos 230 casos
realmente distintos. En 5 minutos eran 67500 velas y tambien unos 230 casos.
Mas filas no es mas informacion cuando las operaciones se solapan.

Ya paso una vez en este proyecto: un LSTM mostraba rentabilidad de 5.01 contra
1.96 del modelo simple. Despues se descubrio que estaba aprovechando la fuga de
futuro de las variables de 15 minutos. Una red es una caja cerrada: ese error se
encontro porque el modelo era una regresion que se podia abrir y revisar.

LOS CONTROLES

  1. Comparar contra la regresion logistica, con las mismas variables y datos.
  2. Medir en DOS periodos que la red nunca vio, por separado.
  3. CONTROL DE MEMORIZACION: entrenar la MISMA red con las etiquetas mezcladas
     al azar. Si con etiquetas sin ningun sentido tambien saca buen resultado
     en el entrenamiento, queda demostrado que memoriza en vez de aprender.
     Este control es el que decide.
  4. Probar tres tamaños de red: si la mas grande anda mejor en entrenamiento
     y peor en prueba, es la firma de la memorizacion.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\red_neuronal.py ^
        --train     datos\crudos\NAS100_TRAIN_2017-10-16_al_2024-01-21_D1.csv ^
        --holdout-a datos\crudos\NAS100_HOLDOUT_A_TPSL_2024-01-22_al_2025-05-26_D1.csv ^
        --holdout-b datos\crudos\NAS100_HOLDOUT_B_CONFIRM_2025-05-27_al_2026-09-28_D1.csv

Para probar en 5 minutos en vez de diario:
    py analisis\red_neuronal.py --train ..._M5.csv --holdout-a ... --holdout-b ... ^
        --horizonte 288
"""
import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import cargar_csv_exportado, construir_features, etiquetar_tp_sl, FEATURE_LIST

warnings.filterwarnings("ignore", category=ConvergenceWarning)

REDES = [("red chica  (8)",      (8,)),
         ("red mediana (32,16)", (32, 16)),
         ("red grande (128,64)", (128, 64))]
SEMILLAS = 5          # cada red se entrena 5 veces: una sola corrida engaña


def preparar(ruta, sin_hora):
    f = construir_features(cargar_csv_exportado(ruta))
    return f.replace([np.inf, -np.inf], np.nan)


def etiquetar(f, k_tp, k_sl, horizonte, lado):
    atr = f["atr5"].values
    return etiquetar_tp_sl(f["high"].values, f["low"].values, f["close"].values,
                           k_tp * atr, k_sl * atr, horizonte, lado)[0]


def entrenar_red(X, y, capas, semilla):
    return MLPClassifier(hidden_layer_sizes=capas, max_iter=600,
                         early_stopping=True, n_iter_no_change=20,
                         random_state=semilla).fit(X, y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--holdout-a", required=True, dest="ha")
    ap.add_argument("--holdout-b", required=True, dest="hb")
    ap.add_argument("--horizonte", type=int, default=10)
    ap.add_argument("--k-tp", type=float, default=2.0, dest="k_tp")
    ap.add_argument("--k-sl", type=float, default=1.0, dest="k_sl")
    ap.add_argument("--lado", default="BUY", choices=["BUY", "SELL"])
    args = ap.parse_args()

    diario = args.horizonte <= 30
    variables = [v for v in FEATURE_LIST if not (diario and v.startswith("hora_"))]

    fs = [preparar(r, diario) for r in (args.train, args.ha, args.hb)]
    fs = [f.dropna(subset=variables).reset_index(drop=True) for f in fs]
    f_tr, f_a, f_b = fs

    print(f"### Red neuronal en NAS100 — lado {args.lado} ###")
    for nom, f in (("entrenamiento", f_tr), ("HOLDOUT_A", f_a), ("HOLDOUT_B", f_b)):
        print(f"  {nom:<14}{len(f):>6} velas  {f['fecha'].iloc[0].date()} -> "
              f"{f['fecha'].iloc[-1].date()}")
    print(f"{len(variables)} variables, objetivo {args.k_tp} ATR, "
          f"stop {args.k_sl} ATR, horizonte {args.horizonte}")

    y_tr = etiquetar(f_tr, args.k_tp, args.k_sl, args.horizonte, args.lado)
    m = y_tr != -1
    X_tr = f_tr[variables].values[m]
    y_tr = y_tr[m]
    sc = StandardScaler().fit(X_tr)
    Xs = sc.transform(X_tr)
    indep = len(X_tr) / max(1, args.horizonte)
    print(f"\n{len(X_tr)} operaciones de entrenamiento, pero como cada una dura")
    print(f"{args.horizonte} velas y se pisan entre si, los casos realmente")
    print(f"independientes son unos {indep:.0f}.")

    datos = {}
    for nom, f in (("HOLDOUT_A", f_a), ("HOLDOUT_B", f_b)):
        y = etiquetar(f, args.k_tp, args.k_sl, args.horizonte, args.lado)
        mk = y != -1
        datos[nom] = (sc.transform(f[variables].values[mk]), y[mk])

    print("\n" + "=" * 74)
    print("RESULTADOS (AUC; 0.50 = tirar una moneda)")
    print("=" * 74)
    print(f"  {'modelo':<24}{'entren.':>9}{'HOLDOUT_A':>12}{'HOLDOUT_B':>12}")

    # referencia: la regresion de siempre
    reg = LogisticRegression(max_iter=2000).fit(Xs, y_tr)
    fila = [roc_auc_score(y_tr, reg.predict_proba(Xs)[:, 1])]
    for nom in ("HOLDOUT_A", "HOLDOUT_B"):
        X, y = datos[nom]
        fila.append(roc_auc_score(y, reg.predict_proba(X)[:, 1]))
    print(f"  {'regresion logistica':<24}{fila[0]:>9.3f}{fila[1]:>12.3f}{fila[2]:>12.3f}")

    for nombre, capas in REDES:
        ent, aa, bb = [], [], []
        for s in range(SEMILLAS):
            red = entrenar_red(Xs, y_tr, capas, s)
            ent.append(roc_auc_score(y_tr, red.predict_proba(Xs)[:, 1]))
            for lista, nom in ((aa, "HOLDOUT_A"), (bb, "HOLDOUT_B")):
                X, y = datos[nom]
                lista.append(roc_auc_score(y, red.predict_proba(X)[:, 1]))
        print(f"  {nombre:<24}{np.mean(ent):>9.3f}{np.mean(aa):>12.3f}"
              f"{np.mean(bb):>12.3f}")

    # ---------------- control de memorizacion ----------------
    print("\n" + "=" * 74)
    print("CONTROL DE MEMORIZACION")
    print("=" * 74)
    print("  Se entrena la MISMA red con las etiquetas MEZCLADAS AL AZAR. Con")
    print("  etiquetas sin ningun sentido, un modelo que aprende deberia quedar")
    print("  en 0.50 tambien en el entrenamiento. Si sube, esta memorizando.\n")
    print(f"  {'modelo':<24}{'entren.':>9}{'HOLDOUT_A':>12}")
    rng = np.random.default_rng(0)
    y_falso = rng.permutation(y_tr)
    reg_f = LogisticRegression(max_iter=2000).fit(Xs, y_falso)
    Xa, ya = datos["HOLDOUT_A"]
    print(f"  {'regresion logistica':<24}"
          f"{roc_auc_score(y_falso, reg_f.predict_proba(Xs)[:, 1]):>9.3f}"
          f"{roc_auc_score(ya, reg_f.predict_proba(Xa)[:, 1]):>12.3f}")
    for nombre, capas in REDES:
        ent, aa = [], []
        for s in range(SEMILLAS):
            red = entrenar_red(Xs, y_falso, capas, s)
            ent.append(roc_auc_score(y_falso, red.predict_proba(Xs)[:, 1]))
            aa.append(roc_auc_score(ya, red.predict_proba(Xa)[:, 1]))
        print(f"  {nombre:<24}{np.mean(ent):>9.3f}{np.mean(aa):>12.3f}")

    print("\n" + "=" * 74)
    print("Como leerlo:")
    print("  - Si en el CONTROL las redes sacan bastante mas de 0.50 en el")
    print("    entrenamiento, estan memorizando: cualquier buen numero suyo en")
    print("    la tabla de arriba hay que mirarlo con la misma desconfianza.")
    print("  - Si las redes no le ganan a la regresion en HOLDOUT_A y HOLDOUT_B")
    print("    a la vez, no aportan nada y ademas son imposibles de auditar.")
    print("  - Si la red grande anda mejor en entrenamiento y peor en prueba que")
    print("    la chica, es la firma clasica de la memorizacion.")


if __name__ == "__main__":
    main()
