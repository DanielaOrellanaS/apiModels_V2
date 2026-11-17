r"""
combinaciones.py -- ¿que combinaciones de indicadores funcionaron mejor?

La pregunta: encontrar reglas del tipo "cuando el RSI esta bajo Y el ADX alto,
suele ganar". Sin modelo y sin red: se mira cada indicador, se parte en tramos
y se cuenta el acierto real en cada uno.

EL PELIGRO, que es el mismo error del principio del proyecto:
Si se miran 19 indicadores x 4 tramos = 76 combinaciones simples, y ademas
todos los pares, son varios miles. Con esa cantidad de intentos, unas cuantas
van a parecer buenisimas por puro azar aunque no haya absolutamente nada.
Es la misma rifa que el barrido de 288 combinaciones de TP/SL.

POR ESO HAY TRES CONTROLES:

  1. Las combinaciones se BUSCAN solo en el tramo de entrenamiento, y despues
     se CONFIRMAN en los dos periodos que nunca se vieron. Una regla real
     funciona en los tres; una casualidad funciona solo donde se la encontro.

  2. Cada combinacion se compara contra el acierto general DE ESE MISMO
     PERIODO. Si en 2025 todo subio, cualquier regla de compra va a parecer
     buena: lo que importa es cuanto SUPERA al promedio de ese periodo.

  3. CONTROL DE AZAR: se repite toda la busqueda con las etiquetas mezcladas.
     Eso dice cuantas combinaciones "buenas" aparecen cuando no hay nada que
     encontrar. Si con datos reales aparecen 6 y con datos mezclados 5, no
     hay nada.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\combinaciones.py ^
        --train     datos\crudos\NAS100_TRAIN_2017-10-16_al_2024-01-21_D1.csv ^
        --holdout-a datos\crudos\NAS100_HOLDOUT_A_TPSL_2024-01-22_al_2025-05-26_D1.csv ^
        --holdout-b datos\crudos\NAS100_HOLDOUT_B_CONFIRM_2025-05-27_al_2026-09-28_D1.csv ^
        --lado BUY
"""
import argparse
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import cargar_csv_exportado, construir_features, etiquetar_tp_sl, FEATURE_LIST

TRAMOS = ["muy bajo", "bajo", "alto", "muy alto"]   # cuartiles
MIN_OPS = 40          # minimo de operaciones para tomar en cuenta una regla
MEJORA_MIN = 0.08     # tiene que superar al promedio por 8 puntos


def preparar(ruta, variables):
    f = construir_features(cargar_csv_exportado(ruta))
    return (f.replace([np.inf, -np.inf], np.nan)
             .dropna(subset=variables).reset_index(drop=True))


def etiquetar(f, k_tp, k_sl, horizonte, lado):
    atr = f["atr5"].values
    return etiquetar_tp_sl(f["high"].values, f["low"].values, f["close"].values,
                           k_tp * atr, k_sl * atr, horizonte, lado)[0]


def tramos_de(f, variables, cortes):
    """Convierte cada variable en su tramo (0..3) usando los cortes del
    entrenamiento. Es importante usar los MISMOS cortes en los tres periodos."""
    t = {}
    for v in variables:
        t[v] = np.digitize(f[v].values, cortes[v])
    return t


def buscar(tr, y, variables, base):
    """Devuelve las reglas que superan el promedio por MEJORA_MIN."""
    hall = []
    # una sola variable
    for v in variables:
        for k in range(4):
            m = (tr[v] == k) & (y != -1)
            if m.sum() < MIN_OPS:
                continue
            wr = y[m].mean()
            if wr - base >= MEJORA_MIN:
                hall.append((f"{v} {TRAMOS[k]}", [(v, k)], int(m.sum()), wr))
    # pares de variables
    for v1, v2 in itertools.combinations(variables, 2):
        for k1 in range(4):
            m1 = tr[v1] == k1
            if m1.sum() < MIN_OPS:
                continue
            for k2 in range(4):
                m = m1 & (tr[v2] == k2) & (y != -1)
                if m.sum() < MIN_OPS:
                    continue
                wr = y[m].mean()
                if wr - base >= MEJORA_MIN:
                    hall.append((f"{v1} {TRAMOS[k1]} Y {v2} {TRAMOS[k2]}",
                                 [(v1, k1), (v2, k2)], int(m.sum()), wr))
    hall.sort(key=lambda x: -x[3])
    return hall


def aplicar(regla, tr, y):
    m = np.ones(len(y), bool)
    for v, k in regla:
        m &= tr[v] == k
    m &= y != -1
    if m.sum() == 0:
        return 0, float("nan")
    return int(m.sum()), float(y[m].mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--holdout-a", required=True, dest="ha")
    ap.add_argument("--holdout-b", required=True, dest="hb")
    ap.add_argument("--lado", default="BUY", choices=["BUY", "SELL"])
    ap.add_argument("--horizonte", type=int, default=10)
    ap.add_argument("--k-tp", type=float, default=2.0, dest="k_tp")
    ap.add_argument("--k-sl", type=float, default=1.0, dest="k_sl")
    args = ap.parse_args()

    diario = args.horizonte <= 30
    variables = [v for v in FEATURE_LIST if not (diario and v.startswith("hora_"))]
    f_tr, f_a, f_b = (preparar(r, variables) for r in (args.train, args.ha, args.hb))

    print(f"### Combinaciones de indicadores — NAS100 {args.lado} ###")
    print(f"  entrenamiento {len(f_tr)} velas  {f_tr['fecha'].iloc[0].date()} -> "
          f"{f_tr['fecha'].iloc[-1].date()}")
    print(f"  HOLDOUT_A     {len(f_a)} velas  {f_a['fecha'].iloc[0].date()} -> "
          f"{f_a['fecha'].iloc[-1].date()}")
    print(f"  HOLDOUT_B     {len(f_b)} velas  {f_b['fecha'].iloc[0].date()} -> "
          f"{f_b['fecha'].iloc[-1].date()}")

    # los cortes salen del entrenamiento y se usan igual en los tres periodos
    cortes = {v: np.percentile(f_tr[v].values, [25, 50, 75]) for v in variables}
    t_tr, t_a, t_b = (tramos_de(f, variables, cortes) for f in (f_tr, f_a, f_b))
    y_tr = etiquetar(f_tr, args.k_tp, args.k_sl, args.horizonte, args.lado)
    y_a = etiquetar(f_a, args.k_tp, args.k_sl, args.horizonte, args.lado)
    y_b = etiquetar(f_b, args.k_tp, args.k_sl, args.horizonte, args.lado)

    base_tr = y_tr[y_tr != -1].mean()
    base_a = y_a[y_a != -1].mean()
    base_b = y_b[y_b != -1].mean()
    print(f"\nAcierto general (sin ninguna regla):")
    print(f"  entrenamiento {base_tr:.1%}   HOLDOUT_A {base_a:.1%}   "
          f"HOLDOUT_B {base_b:.1%}")
    print(f"\nSe buscan reglas con al menos {MIN_OPS} operaciones que superen el")
    print(f"promedio de su periodo por {MEJORA_MIN:.0%} o mas.")

    hall = buscar(t_tr, y_tr, variables, base_tr)
    print(f"\n{'='*78}")
    print(f"REGLAS ENCONTRADAS EN EL ENTRENAMIENTO: {len(hall)}")
    print(f"{'='*78}")
    if not hall:
        print("  Ninguna combinacion supera el promedio por el margen pedido.")
        return

    print(f"  {'regla':<44}{'n':>5}{'entren.':>9}{'HOL_A':>8}{'HOL_B':>8}{'':>5}")
    confirmadas = 0
    for nombre, regla, n, wr in hall[:25]:
        na, wa = aplicar(regla, t_a, y_a)
        nb, wb = aplicar(regla, t_b, y_b)
        ok = (na >= 15 and nb >= 15 and
              wa - base_a >= MEJORA_MIN / 2 and wb - base_b >= MEJORA_MIN / 2)
        if ok:
            confirmadas += 1
        sa = f"{wa:.0%}" if na >= 15 else f"n={na}"
        sb = f"{wb:.0%}" if nb >= 15 else f"n={nb}"
        print(f"  {nombre[:43]:<44}{n:>5}{wr:>9.0%}{sa:>8}{sb:>8}"
              f"{'  SI' if ok else '':>5}")
    if len(hall) > 25:
        print(f"  ... y {len(hall)-25} mas")

    print(f"\n  Confirmadas en los DOS periodos nuevos: {confirmadas} de {len(hall)}")

    # ---------------- control ----------------
    print(f"\n{'='*78}")
    print("CONTROL: la misma busqueda con las etiquetas MEZCLADAS AL AZAR")
    print(f"{'='*78}")
    rng = np.random.default_rng(0)
    conteos = []
    for i in range(5):
        yf = y_tr.copy()
        m = yf != -1
        yf[m] = rng.permutation(yf[m])
        conteos.append(len(buscar(t_tr, yf, variables, base_tr)))
    print(f"  Con datos SIN ninguna relacion aparecen, en promedio, "
          f"{np.mean(conteos):.0f} reglas")
    print(f"  que parecen buenas (5 pruebas: {conteos}).")
    print(f"  Con los datos reales aparecieron {len(hall)}.")
    print()
    if len(hall) <= np.mean(conteos) * 1.3:
        print("  -> Aparecen tantas como por azar. Las reglas encontradas son")
        print("     casualidades de la busqueda, no patrones reales.")
    else:
        print("  -> Aparecen bastantes mas que por azar. Mirar cuales quedaron")
        print("     confirmadas en los dos periodos nuevos.")
    print()
    print("Lo que decide es la columna de la derecha: una regla vale solo si")
    print("tambien supera al promedio en HOLDOUT_A y HOLDOUT_B. Si ninguna lo")
    print("hace, lo que se encontro fue ruido del periodo de entrenamiento.")


if __name__ == "__main__":
    main()
