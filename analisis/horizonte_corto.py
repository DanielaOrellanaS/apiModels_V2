r"""
horizonte_corto.py -- ¿y si las operaciones duraran horas en vez de un dia?

EL PROBLEMA QUE ATACA

Todo lo medido en este proyecto uso un horizonte de 288 velas: un dia entero
para que la operacion se resuelva. Eso nunca se cuestiono, y es la raiz del
problema que vinimos repitiendo durante semanas.

Con 45.843 velas de entrenamiento y operaciones que duran un dia, las
operaciones se pisan entre si y los casos REALMENTE independientes son unos
160. Con ese numero no hay modelo que aprenda nada: ni una regresion ni una
red. Se midio: con 230 casos y variables generadas al azar, una red neuronal
llega a 1,000 de AUC en entrenamiento y 0,42 en prueba.

Bajando el horizonte a 24 velas (dos horas), esos casos pasan a ser unos 1.900.
Doce veces mas. Y la pregunta cambia a una mas razonable para un sistema de 5
minutos: no "¿llega al objetivo en algun momento del dia?" sino "¿llega en las
proximas dos horas?".

QUE MIDE

  [A] DIRECCION PURA. ¿El precio va a estar mas arriba dentro de N velas?
      Sin objetivo, sin stop, sin caminos: solo el signo del movimiento. Es el
      diagnostico mas limpio que existe, porque saca del medio toda la
      maquinaria de TP/SL. Si esto da 0,50 en todos los horizontes, la
      respuesta es definitiva.

  [B] LA PREGUNTA OPERATIVA. ¿Llega al objetivo antes que al stop, dentro de N
      velas? Objetivo 2 ATR y stop 1 ATR, fijos, sin barrer combinaciones.

DOS CONTROLES QUE NO SE PUEDEN OMITIR

  1. AUC sobre casos INDEPENDIENTES. Ademas del AUC sobre todas las filas, se
     mide sobre un submuestreo que toma una fila cada `horizonte`, de modo que
     ninguna operacion se pise con la siguiente. Si los dos numeros difieren
     mucho, el solapamiento estaba inflando la confianza del primero.

  2. PERMUTACION. Se entrena el mismo modelo con las etiquetas mezcladas al
     azar y se mide cuanto AUC sale por pura casualidad. Con muestras chicas
     ese numero sube bastante, y sin tenerlo a la vista es facil confundir
     ruido con señal.

COMO LEERLO

El numero que decide es el AUC sobre casos independientes, comparado contra su
control de permutacion. Si en algun horizonte corto supera al control con
claridad en los DOS periodos, hay algo que no habiamos visto. Si todos quedan
pegados al control, el horizonte no era el problema y la respuesta esta
cerrada.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\horizonte_corto.py ^
        --train     datos\crudos\NAS100_TRAIN_2025-10-09_al_2026-06-03_M5.csv ^
        --holdout-a datos\crudos\NAS100_HOLDOUT_A_TPSL_2026-06-04_al_2026-07-23_M5.csv ^
        --holdout-b datos\crudos\NAS100_HOLDOUT_B_CONFIRM_2026-07-24_al_2026-09-13_M5.csv

Por defecto prueba 12, 24, 36 y 72 velas. Para incluir el horizonte actual de
288 como referencia, agregar: --horizontes 12,24,36,72,288
(tarda bastante mas, porque etiquetar con horizonte largo es lento)
"""
import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import (cargar_csv_exportado, construir_features, etiquetar_tp_sl,
                  FEATURE_LIST)

warnings.filterwarnings("ignore", category=ConvergenceWarning)

K_TP, K_SL = 2.0, 1.0
N_PERM = 150
MIN_PRUEBA = 60          # casos independientes minimos para tomar en serio un AUC


def preparar(ruta):
    f = construir_features(cargar_csv_exportado(ruta))
    return (f.replace([np.inf, -np.inf], np.nan)
             .dropna(subset=FEATURE_LIST).reset_index(drop=True))


def auc_de(X_tr, y_tr, X_ho, y_ho):
    if len(np.unique(y_tr)) < 2 or len(np.unique(y_ho)) < 2:
        return float("nan")
    sc = StandardScaler().fit(X_tr)
    m = LogisticRegression(max_iter=2000).fit(sc.transform(X_tr), y_tr)
    return roc_auc_score(y_ho, m.predict_proba(sc.transform(X_ho))[:, 1])


def evaluar(X_tr, y_tr, datos, horizonte, rng):
    """Devuelve, por periodo: AUC sobre todas las filas, AUC sobre casos
    independientes, y el control de permutacion sobre esos casos."""
    m_tr = y_tr != -1
    if m_tr.sum() < 300:
        return None
    Xt, yt = X_tr[m_tr], y_tr[m_tr]
    salida = {}
    for nombre, (X_ho, y_ho) in datos.items():
        m_ho = y_ho != -1
        if m_ho.sum() < 50:
            salida[nombre] = None
            continue
        Xh, yh = X_ho[m_ho], y_ho[m_ho]
        auc_todas = auc_de(Xt, yt, Xh, yh)

        # una fila cada `horizonte`: ninguna operacion se pisa con la siguiente
        idx = np.arange(0, len(yh), horizonte)
        Xi, yi = Xh[idx], yh[idx]
        auc_indep = auc_de(Xt, yt, Xi, yi)

        nulos = []
        for _ in range(N_PERM):
            a = auc_de(Xt, rng.permutation(yt), Xi, yi)
            if not np.isnan(a):
                nulos.append(a)
        p95 = float(np.percentile(nulos, 95)) if nulos else float("nan")

        salida[nombre] = dict(n=int(m_ho.sum()), n_indep=len(idx),
                              auc=auc_todas, auc_indep=auc_indep, p95=p95)
    salida["_train"] = dict(n=int(m_tr.sum()),
                            n_indep=int(m_tr.sum() / horizonte),
                            pct_pos=float(yt.mean()))
    return salida


def imprimir(titulo, res):
    print(f"\n  {titulo}")
    if res is None:
        print("    datos insuficientes")
        return
    t = res["_train"]
    print(f"    entrenamiento: {t['n']} operaciones, pero solo ~{t['n_indep']} "
          f"independientes ({t['pct_pos']:.0%} positivas)")
    print(f"    {'periodo':<12}{'n':>7}{'indep':>7}{'AUC':>8}"
          f"{'AUC indep':>11}{'azar':>8}")
    for nombre in ("HOLDOUT_A", "HOLDOUT_B"):
        d = res.get(nombre)
        if d is None:
            print(f"    {nombre:<12}{'sin datos suficientes':>33}")
            continue
        marca = ""
        if not np.isnan(d["auc_indep"]) and not np.isnan(d["p95"]):
            if d["auc_indep"] > d["p95"]:
                marca = "  <-- supera al azar"
        aviso = "  (pocos casos)" if d["n_indep"] < MIN_PRUEBA else ""
        print(f"    {nombre:<12}{d['n']:>7}{d['n_indep']:>7}{d['auc']:>8.3f}"
              f"{d['auc_indep']:>11.3f}{d['p95']:>8.3f}{marca}{aviso}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--holdout-a", required=True, dest="ha")
    ap.add_argument("--holdout-b", required=True, dest="hb")
    ap.add_argument("--horizontes", default="12,24,36,72",
                    help="velas, separadas por coma. 12=1h, 24=2h, 72=6h, 288=1dia")
    ap.add_argument("--lado", default="BUY", choices=["BUY", "SELL"])
    args = ap.parse_args()

    horizontes = [int(h) for h in args.horizontes.split(",")]
    f_tr, f_a, f_b = (preparar(r) for r in (args.train, args.ha, args.hb))

    print("### ¿Y si las operaciones duraran horas en vez de un dia? ###")
    for nom, f in (("entrenamiento", f_tr), ("HOLDOUT_A", f_a), ("HOLDOUT_B", f_b)):
        print(f"  {nom:<14}{len(f):>7} velas  {f['fecha'].iloc[0].date()} -> "
              f"{f['fecha'].iloc[-1].date()}")
    print(f"\nhorizontes a probar: "
          f"{', '.join(f'{h} velas ({h*5//60}h{h*5%60:02d})' for h in horizontes)}")
    print(f"lado: {args.lado}   |   objetivo {K_TP} ATR, stop {K_SL} ATR en la parte [B]")

    X_tr = f_tr[FEATURE_LIST].values
    datos_X = {"HOLDOUT_A": f_a[FEATURE_LIST].values,
               "HOLDOUT_B": f_b[FEATURE_LIST].values}
    rng = np.random.default_rng(0)

    # ---------------- [A] direccion pura ----------------
    print("\n" + "=" * 74)
    print("[A] DIRECCION PURA — ¿el precio va a estar mas arriba en N velas?")
    print("=" * 74)
    print("  Sin objetivo ni stop: solo el signo del movimiento. Es el")
    print("  diagnostico mas limpio, porque saca del medio toda la mecanica")
    print("  de TP/SL y la eleccion de combinaciones.")

    for h in horizontes:
        def etiq_dir(f):
            c = f["close"].values
            y = np.full(len(c), -1, dtype=np.int8)
            fut = np.r_[c[h:], np.full(h, np.nan)]
            ok = ~np.isnan(fut)
            y[ok] = (fut[ok] > c[ok]).astype(np.int8)
            return y
        res = evaluar(X_tr, etiq_dir(f_tr),
                      {k: (datos_X[k], etiq_dir(f))
                       for k, f in (("HOLDOUT_A", f_a), ("HOLDOUT_B", f_b))},
                      h, rng)
        imprimir(f"horizonte {h} velas ({h*5//60}h{h*5%60:02d})", res)

    # ---------------- [B] la pregunta operativa ----------------
    print("\n" + "=" * 74)
    print(f"[B] LA PREGUNTA OPERATIVA — ¿llega a {K_TP} ATR antes que a "
          f"{K_SL} ATR, dentro de N velas?")
    print("=" * 74)

    for h in horizontes:
        def etiq_tpsl(f):
            atr = f["atr5"].values
            return etiquetar_tp_sl(f["high"].values, f["low"].values,
                                   f["close"].values, K_TP * atr, K_SL * atr,
                                   h, args.lado)[0]
        res = evaluar(X_tr, etiq_tpsl(f_tr),
                      {k: (datos_X[k], etiq_tpsl(f))
                       for k, f in (("HOLDOUT_A", f_a), ("HOLDOUT_B", f_b))},
                      h, rng)
        imprimir(f"horizonte {h} velas ({h*5//60}h{h*5%60:02d})", res)

    print("\n" + "=" * 74)
    print("Como leerlo:")
    print("  La columna que decide es 'AUC indep': el AUC medido sobre casos que")
    print("  NO se pisan entre si. La columna 'AUC' usa todas las filas y por el")
    print("  solapamiento aparenta mas precision de la que tiene.")
    print("  'azar' es hasta donde llega el AUC con las etiquetas mezcladas, con")
    print("  esa misma cantidad de casos. La señal tiene que superarlo.")
    print()
    print("  Para que el horizonte corto sea la respuesta, hace falta que algun")
    print("  horizonte supere al azar en LOS DOS periodos. Si todos quedan")
    print("  pegados al control, el horizonte no era el problema.")


if __name__ == "__main__":
    main()
