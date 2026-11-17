r"""
diario.py -- probar NAS100 en velas DIARIAS.

Por que diario y no 5 minutos: en 5 minutos se midio siete veces, con un año
de datos limpios y hasta 38 variables, y el promedio dio 0.497. Exactamente
una moneda. No es que falte una variable: es el horizonte donde mas ruido hay
y donde compiten sistemas con datos e infraestructura que no tenemos. Ademas
el costo pesa muchisimo mas: 0.85 de spread contra un objetivo de 20 puntos es
mucho; contra uno de 400, casi nada.

Este script mide tres cosas, en este orden:

  [A] ¿Alcanzan los datos? Con velas diarias hay pocas. Si el tramo de prueba
      queda por debajo de 100 operaciones, cualquier resultado es ruido y el
      script lo dice antes de mostrar nada mas.

  [B] ¿Se predice la DIRECCION en diario? Mismo metodo de siempre: entrenar
      con el 70% mas viejo y medir el AUC sobre el ultimo 15%, que no se ve.

  [C] ¿Se predice si el dia va a TENER TENDENCIA o ir de lado? Es una pregunta
      distinta y mas facil. No dice hacia donde, pero si se puede anticipar,
      sirve para elegir entre operar a favor de la tendencia o esperar.

  Y un control de permutacion: se repite la medicion con las etiquetas
  mezcladas al azar, para ver cuanto AUC sale por pura casualidad con esta
  cantidad de datos. Con muestras chicas ese numero es alto, y sin el es facil
  confundir ruido con señal.

DATOS: exportar NAS100 en diario con EXPORTAR_DATASETS_MULTI_TF.mq4 usando
    InpTF = 1440    (diario)
    InpTFSup = 10080 (semanal)
Antes conviene abrir el grafico en D1 y apretar Inicio varias veces para que
MetaTrader descargue todo el historial que tenga.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\diario.py --csv datos\crudos\NAS100_TRAIN_..._D1.csv
    py analisis\diario.py --csv ... --horizonte 10 --k-tp 2 --k-sl 1
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

# la hora del dia no significa nada en velas diarias: todas son la misma
VARS = [v for v in FEATURE_LIST if v not in ("hora_sin", "hora_cos")]
MIN_PRUEBA = 100          # operaciones minimas en el tramo de prueba
N_PERMUTACIONES = 200


def auc_de(X_tr, y_tr, X_ho, y_ho):
    sc = StandardScaler().fit(X_tr)
    m = LogisticRegression(max_iter=2000).fit(sc.transform(X_tr), y_tr)
    return roc_auc_score(y_ho, m.predict_proba(sc.transform(X_ho))[:, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--horizonte", type=int, default=10,
                    help="velas diarias para resolver la operacion (10 = 2 semanas)")
    ap.add_argument("--k-tp", type=float, default=2.0, dest="k_tp")
    ap.add_argument("--k-sl", type=float, default=1.0, dest="k_sl")
    args = ap.parse_args()

    f = construir_features(cargar_csv_exportado(args.csv))
    f = f.replace([np.inf, -np.inf], np.nan).dropna(subset=VARS).reset_index(drop=True)
    n = len(f)
    i1, i2 = int(n * 0.70), int(n * 0.85)

    print(f"### NAS100 en velas DIARIAS — {Path(args.csv).name} ###")
    print(f"{n} velas   {f['fecha'].iloc[0].date()} -> {f['fecha'].iloc[-1].date()}")
    print(f"objetivo {args.k_tp} ATR, stop {args.k_sl} ATR, "
          f"horizonte {args.horizonte} dias\n")

    # ---------------- [A] ----------------
    print("=" * 70)
    print("[A] ¿Alcanzan los datos?")
    print("=" * 70)
    print(f"  entrenamiento : {i1} velas")
    print(f"  ajuste        : {i2-i1} velas")
    print(f"  prueba final  : {n-i2} velas")
    anios = (f['fecha'].iloc[-1] - f['fecha'].iloc[0]).days / 365.25
    print(f"  cubre {anios:.1f} años")
    if n < 500:
        print(f"\n  AVISO: {n} velas diarias son pocas. Con menos de ~500 el tramo")
        print("  de prueba queda tan chico que cualquier resultado es ruido.")
        print("  Conviene descargar mas historial (F2 -> NAS100 -> Daily -> Download)")
        print("  antes de sacar conclusiones de lo que sigue.")

    high, low = f["high"].values, f["low"].values
    close, atr = f["close"].values, f["atr5"].values
    rng = np.random.default_rng(0)

    # ---------------- [B] ----------------
    print("\n" + "=" * 70)
    print("[B] ¿Se predice la DIRECCION en diario?")
    print("=" * 70)
    for lado in ("BUY", "SELL"):
        labels, _ = etiquetar_tp_sl(high, low, close, args.k_tp * atr,
                                    args.k_sl * atr, args.horizonte, lado)
        tr, ho = slice(0, i1), slice(i2, n)
        ytr, yho = labels[tr], labels[ho]
        mtr, mho = ytr != -1, yho != -1
        nombre = "COMPRA" if lado == "BUY" else "VENTA"
        if mho.sum() < 30 or mtr.sum() < 100:
            print(f"  {nombre}: solo {int(mho.sum())} operaciones en el tramo de "
                  f"prueba. Muestra insuficiente.")
            continue
        Xtr, Xho = f[VARS].values[tr][mtr], f[VARS].values[ho][mho]
        auc = auc_de(Xtr, ytr[mtr], Xho, yho[mho])

        # control: mismas variables, etiquetas mezcladas
        nulos = []
        for _ in range(N_PERMUTACIONES):
            yp = rng.permutation(ytr[mtr])
            try:
                nulos.append(auc_de(Xtr, yp, Xho, yho[mho]))
            except ValueError:
                pass
        nulos = np.array(nulos)
        p95 = np.percentile(nulos, 95)
        print(f"  {nombre}: AUC = {auc:.3f}   "
              f"({int(mtr.sum())} operaciones para entrenar, "
              f"{int(mho.sum())} para probar)")
        print(f"    con etiquetas al azar se llega a {p95:.3f} en el 5% de los casos")
        if int(mho.sum()) < MIN_PRUEBA:
            print(f"    AVISO: menos de {MIN_PRUEBA} operaciones de prueba, "
                  f"el resultado es poco confiable")
        print(f"    -> {'supera al azar' if auc > p95 else 'NO supera al azar'}")

    # ---------------- [C] ----------------
    print("\n" + "=" * 70)
    print("[C] ¿Se predice si el dia va a tener TENDENCIA o ir de lado?")
    print("=" * 70)
    print("  'con tendencia' = el cierre queda en el tercio alto o bajo del")
    print("  recorrido del dia siguiente; 'de lado' = queda en el medio.")
    rango = high - low
    pos = np.where(rango > 0, (close - low) / rango, 0.5)
    y = np.full(n, -1, dtype=int)
    sig = np.r_[pos[1:], np.nan]
    ok = ~np.isnan(sig)
    y[ok] = ((sig[ok] > 0.7) | (sig[ok] < 0.3)).astype(int)
    tr, ho = slice(0, i1), slice(i2, n)
    mtr, mho = y[tr] != -1, y[ho] != -1
    if mho.sum() < 30:
        print("  muestra insuficiente")
    else:
        Xtr, Xho = f[VARS].values[tr][mtr], f[VARS].values[ho][mho]
        ytr, yho = y[tr][mtr], y[ho][mho]
        if len(np.unique(yho)) < 2:
            print("  todas las etiquetas iguales en el tramo de prueba")
        else:
            auc = auc_de(Xtr, ytr, Xho, yho)
            nulos = np.array([auc_de(Xtr, rng.permutation(ytr), Xho, yho)
                              for _ in range(N_PERMUTACIONES)])
            p95 = np.percentile(nulos, 95)
            print(f"  AUC = {auc:.3f}   (dias con tendencia: {ytr.mean():.0%} "
                  f"del entrenamiento)")
            print(f"  con etiquetas al azar se llega a {p95:.3f}")
            print(f"  -> {'supera al azar' if auc > p95 else 'NO supera al azar'}")

    print("\n" + "=" * 70)
    print("Como leerlo:")
    print("  El numero que importa es si el AUC supera al del control con")
    print("  etiquetas mezcladas. Con pocas velas ese control sube mucho: un AUC")
    print("  de 0.60 con 80 operaciones puede ser puro azar, mientras que 0.56")
    print("  con 500 puede ser real. Por eso se informan los dos.")


if __name__ == "__main__":
    main()
