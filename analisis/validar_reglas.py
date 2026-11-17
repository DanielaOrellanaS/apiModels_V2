r"""
validar_reglas.py -- medir en serio las reglas que sobrevivieron.

Sirve para los dos plazos. Se elige con --plazo:

  --plazo diario  (por defecto)  horizonte 10 velas diarias
  --plazo m5                     horizonte 288 velas de 5 minutos

Cada plazo trae sus propias reglas, las que quedaron confirmadas en los dos
periodos nuevos al correr combinaciones.py.

De la busqueda de combinaciones salieron 340 reglas que en el entrenamiento
superaban al promedio. Al confirmarlas en los dos periodos nuevos quedaron 3:

  COMPRA  rel_ema50_200 alto      Y  adx5 alto
  COMPRA  rel_ema50 bajo          Y  rango_rel alto
  VENTA   rel_ema50 alto          Y  rel_ema50_200 muy alto

Pero eso todavia no alcanza. El control mostro que del RUIDO salen unas 114
reglas que parecen buenas en compra y 68 en venta. Si de 114 reglas de ruido se
filtra por dos periodos, es esperable que alguna pase igual. Asi que hay que
medir estas tres por separado y con mas exigencia.

Que mide, para cada regla y cada periodo:
  - cuantas operaciones exactamente (no vale con 20)
  - el acierto y cuanto supera al promedio de ESE periodo
  - la RENTABILIDAD con el costo del spread, que es lo que define si se gana
  - un intervalo de confianza del acierto, para ver si el margen es real o
    entra dentro de lo que varia por azar con esa cantidad de operaciones
  - un control de permutacion ESPECIFICO de esa regla: se mezclan las
    etiquetas y se mide cuanto acierto alcanza la misma regla por casualidad

Y un resumen final con las condiciones que tiene que cumplir para tomarla en
serio.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\validar_reglas.py ^
        --train     datos\crudos\NAS100_TRAIN_2017-10-16_al_2024-01-21_D1.csv ^
        --holdout-a datos\crudos\NAS100_HOLDOUT_A_TPSL_2024-01-22_al_2025-05-26_D1.csv ^
        --holdout-b datos\crudos\NAS100_HOLDOUT_B_CONFIRM_2025-05-27_al_2026-09-28_D1.csv ^
        --costo 0.85
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import cargar_csv_exportado, construir_features, etiquetar_tp_sl, FEATURE_LIST

TRAMOS = {"muy bajo": 0, "bajo": 1, "alto": 2, "muy alto": 3}
N_PERM = 2000
MIN_OPS = 25          # menos que esto, no se puede concluir nada

# --- reglas de VELAS DIARIAS (de combinaciones.py --horizonte 10) ---
REGLAS_DIARIO = [
    ("BUY",  [("rel_ema50_200", "alto"), ("adx5", "alto")]),
    ("BUY",  [("rel_ema50", "bajo"), ("rango_rel", "alto")]),
    ("SELL", [("rel_ema50", "alto"), ("rel_ema50_200", "muy alto")]),
]

# --- reglas de VELAS DE 5 MINUTOS (de combinaciones.py --horizonte 288) ---
# Las dos que quedaron confirmadas en los dos periodos nuevos, de 6 encontradas.
# El control mostro que del ruido salen 1 o 2, asi que 6 es bastante mas que
# por azar. Pero hay dos motivos para desconfiar y por eso se miden aca:
#   - la primera salta de 39% a 75% entre un periodo y el otro
#   - con horizonte de 288 velas cada operacion dura un dia entero y se pisa
#     con las vecinas, asi que 220 operaciones son unos 30-40 dias distintos
REGLAS_M5 = [
    ("BUY", [("rel_ema200", "muy bajo"), ("macd_rel", "muy bajo")]),
    ("BUY", [("rsi15", "bajo"), ("stoch_m15", "muy alto")]),
]


def preparar(ruta, variables):
    f = construir_features(cargar_csv_exportado(ruta))
    return (f.replace([np.inf, -np.inf], np.nan)
             .dropna(subset=variables).reset_index(drop=True))


def etiquetar(f, k_tp, k_sl, horizonte, lado):
    atr = f["atr5"].values
    return etiquetar_tp_sl(f["high"].values, f["low"].values, f["close"].values,
                           k_tp * atr, k_sl * atr, horizonte, lado)[0]


def mascara(f, regla, cortes):
    m = np.ones(len(f), bool)
    for var, tramo in regla:
        m &= np.digitize(f[var].values, cortes[var]) == TRAMOS[tramo]
    return m


def medir(f, m, y, k_tp, k_sl, costo, rng):
    ok = m & (y != -1)
    n = int(ok.sum())
    if n == 0:
        return None
    yv = y[ok]
    atr = f["atr5"].values[ok]
    gan = (k_tp * atr)[yv == 1].sum()
    per = (k_sl * atr)[yv == 0].sum() + n * costo
    wr = float(yv.mean())
    # intervalo del acierto por remuestreo
    boot = np.array([rng.choice(yv, n, replace=True).mean() for _ in range(1000)])
    # control: la misma cantidad de operaciones tomadas al azar del periodo
    todas = y[y != -1]
    nulo = np.array([rng.choice(todas, n, replace=False).mean()
                     for _ in range(N_PERM)]) if n <= len(todas) else np.array([np.nan])
    return dict(n=n, wr=wr, pf=gan / per if per > 0 else float("inf"),
                lo=float(np.percentile(boot, 2.5)),
                hi=float(np.percentile(boot, 97.5)),
                base=float(todas.mean()),
                p95=float(np.nanpercentile(nulo, 95)),
                p=float(np.nanmean(nulo >= wr)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--holdout-a", required=True, dest="ha")
    ap.add_argument("--holdout-b", required=True, dest="hb")
    ap.add_argument("--plazo", default="diario", choices=["diario", "m5"],
                    help="con que datos y horizonte medir (diario=10, m5=288)")
    ap.add_argument("--reglas", default="auto", choices=["auto", "diario", "m5"],
                    help="que juego de reglas medir. 'auto' usa el del plazo. "
                         "Con --plazo m5 --reglas diario se mide la regla "
                         "diaria sobre datos de 5 minutos.")
    ap.add_argument("--costo", type=float, default=0.0)
    ap.add_argument("--horizonte", type=int, default=None,
                    help="velas para resolver. Si se omite: 10 en diario, 288 en m5")
    ap.add_argument("--k-tp", type=float, default=2.0, dest="k_tp")
    ap.add_argument("--k-sl", type=float, default=1.0, dest="k_sl")
    args = ap.parse_args()

    es_m5 = args.plazo == "m5"
    cual = args.reglas if args.reglas != "auto" else ("m5" if es_m5 else "diario")
    reglas = REGLAS_M5 if cual == "m5" else REGLAS_DIARIO
    if args.horizonte is None:
        args.horizonte = 288 if es_m5 else 10
    # en diario la hora no significa nada: todas las velas son la misma
    variables = FEATURE_LIST if es_m5 else [v for v in FEATURE_LIST
                                            if not v.startswith("hora_")]
    f_tr, f_a, f_b = (preparar(r, variables) for r in (args.train, args.ha, args.hb))
    cortes = {v: np.percentile(f_tr[v].values, [25, 50, 75]) for v in variables}
    rng = np.random.default_rng(0)

    print(f"### Validacion de reglas — NAS100, datos de "
          f"{'5 MINUTOS' if es_m5 else 'velas DIARIAS'} ###")
    print(f"reglas medidas: las de {'5 minutos' if cual == 'm5' else 'velas diarias'}")
    if es_m5 and cual == "diario":
        print()
        print("  OJO: la regla se encontro y se validó en velas DIARIAS. Aca se")
        print("  la mide sobre velas de 5 minutos, o sea que los tramos 'alto' se")
        print("  recalculan con los percentiles de M5 y significan otra cosa. Es")
        print("  una regla distinta que se llama igual.")
        print("  Dato previo: al buscar combinaciones en M5 esta no aparecio entre")
        print("  las 6 que superaban el umbral, ni siquiera en el entrenamiento.")
    print(f"objetivo {args.k_tp} ATR, stop {args.k_sl} ATR, "
          f"horizonte {args.horizonte} dias, costo {args.costo}")
    print(f"minimo aceptable: {MIN_OPS} operaciones por periodo\n")

    for lado, regla in reglas:
        nombre = " Y ".join(f"{v} {t}" for v, t in regla)
        print("=" * 78)
        print(f"{'COMPRA' if lado == 'BUY' else 'VENTA'}:  {nombre}")
        print("=" * 78)
        print(f"  {'periodo':<16}{'n':>5}{'acierto':>9}{'rango del acierto':>20}"
              f"{'promedio':>10}{'azar':>8}{'PF':>8}")
        veredictos = []
        for nom, f in (("entrenamiento", f_tr), ("HOLDOUT_A", f_a), ("HOLDOUT_B", f_b)):
            y = etiquetar(f, args.k_tp, args.k_sl, args.horizonte, lado)
            d = medir(f, mascara(f, regla, cortes), y, args.k_tp, args.k_sl,
                      args.costo, rng)
            if d is None or d["n"] == 0:
                print(f"  {nom:<16}{0:>5}   sin operaciones")
                veredictos.append(False)
                continue
            rango = f"{d['lo']:.0%} a {d['hi']:.0%}"
            print(f"  {nom:<16}{d['n']:>5}{d['wr']:>9.0%}{rango:>20}"
                  f"{d['base']:>10.0%}{d['p95']:>8.0%}{d['pf']:>8.2f}")
            if nom != "entrenamiento":
                veredictos.append(d["n"] >= MIN_OPS and d["wr"] > d["p95"]
                                  and d["pf"] > 1.0)
        print()
        print(f"  {'':<4}n: operaciones | rango: donde puede estar el acierto real")
        print(f"  {'':<4}promedio: acierto de TODAS las operaciones de ese periodo")
        print(f"  {'':<4}azar: acierto que alcanza el 5% de las selecciones al azar")
        print(f"  {'':<4}del mismo tamaño. La regla tiene que superarlo.")
        if all(veredictos):
            print("\n  -> PASA: en los dos periodos nuevos tiene suficientes")
            print("     operaciones, supera al azar y gana dinero.")
        else:
            print("\n  -> NO PASA. Motivos por periodo:")
            for nom, f in (("HOLDOUT_A", f_a), ("HOLDOUT_B", f_b)):
                y = etiquetar(f, args.k_tp, args.k_sl, args.horizonte, lado)
                d = medir(f, mascara(f, regla, cortes), y, args.k_tp, args.k_sl,
                          args.costo, rng)
                if d is None or d["n"] == 0:
                    print(f"     {nom}: sin operaciones")
                    continue
                fallas = []
                if d["n"] < MIN_OPS:
                    fallas.append(f"solo {d['n']} operaciones")
                if d["wr"] <= d["p95"]:
                    fallas.append(f"acierto {d['wr']:.0%} no supera al azar "
                                  f"({d['p95']:.0%})")
                if d["pf"] <= 1.0:
                    fallas.append(f"pierde dinero (PF {d['pf']:.2f})")
                print(f"     {nom}: {', '.join(fallas) if fallas else 'ok'}")
        print()

    if es_m5:
        print("=" * 78)
        print("OJO con el solapamiento: con horizonte de 288 velas cada operacion")
        print(f"dura un dia entero. Las 'n' de arriba se dividen por ~{args.horizonte}")
        print("para saber cuantos casos INDEPENDIENTES hay de verdad. 200")
        print("operaciones de 5 minutos son unos 30-40 dias distintos, no 200.")
    print("=" * 78)
    print("Para poner una regla a operar tienen que darse las tres cosas en los")
    print("DOS periodos nuevos: al menos 25 operaciones, acierto por encima del")
    print("azar, y rentabilidad mayor a 1. Con menos de eso no se puede")
    print("distinguir de las reglas que salen del ruido: en la busqueda anterior")
    print("aparecian 114 reglas 'buenas' con datos sin ninguna relacion.")


if __name__ == "__main__":
    main()
