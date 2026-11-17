r"""
generar_regla.py -- calcula los cortes de la regla y los guarda para la API.

La regla que sobrevivio a toda la validacion:

    COMPRA NAS100 en velas DIARIAS cuando
        rel_ema50_200 esta en el tramo "alto"   (entre el 50% y el 75%)
        Y adx5 esta en el tramo "alto"          (entre el 50% y el 75%)

    con objetivo 2 ATR y stop 1 ATR, resuelto en 10 dias.

Resultados que tuvo (ver validar_reglas.py):
    entrenamiento  74 ops  acierto 54%  (promedio 36%)  PF 2.30
    HOLDOUT_A      34 ops  acierto 68%  (promedio 32%)  PF 3.95
    HOLDOUT_B      34 ops  acierto 47%  (promedio 31%)  PF 1.50

Los tramos "alto" son percentiles calculados sobre el TRAIN. Este script los
calcula y los escribe en regla_diaria.json, que es lo que lee la API. De esa
forma los numeros no quedan escritos a mano en el codigo y se puede ver de
donde salieron.

IMPORTANTE: los cortes se calculan SOLO con el archivo de entrenamiento. Si se
recalculan con datos nuevos, la regla deja de ser la que se valido.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\generar_regla.py --train datos\crudos\NAS100_TRAIN_2017-10-16_al_2024-01-21_D1.csv
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import cargar_csv_exportado, construir_features

SALIDA = Path("regla_diaria.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--symbol", default="NAS100")
    args = ap.parse_args()

    f = construir_features(cargar_csv_exportado(args.train))
    f = f.replace([np.inf, -np.inf], np.nan)

    cortes = {}
    for v in ("rel_ema50_200", "adx5"):
        s = f[v].dropna().values
        p25, p50, p75 = np.percentile(s, [25, 50, 75])
        cortes[v] = dict(p25=float(p25), p50=float(p50), p75=float(p75))

    datos = dict(
        symbol=args.symbol.upper(),
        timeframe="D1",
        lado="BUY",
        k_tp=2.0,
        k_sl=1.0,
        horizonte_dias=10,
        # "alto" = entre el percentil 50 y el 75 del entrenamiento
        condiciones=[
            dict(variable="rel_ema50_200", tramo="alto",
                 desde=cortes["rel_ema50_200"]["p50"],
                 hasta=cortes["rel_ema50_200"]["p75"]),
            dict(variable="adx5", tramo="alto",
                 desde=cortes["adx5"]["p50"],
                 hasta=cortes["adx5"]["p75"]),
        ],
        cortes_completos=cortes,
        entrenado_con=Path(args.train).name,
        velas_entrenamiento=int(len(f)),
        desde=str(f["fecha"].iloc[0].date()),
        hasta=str(f["fecha"].iloc[-1].date()),
        generado_en=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        resultados_validacion=dict(
            entrenamiento=dict(n=74, acierto=0.54, promedio=0.36, pf=2.30),
            holdout_a=dict(n=34, acierto=0.68, promedio=0.32, pf=3.95),
            holdout_b=dict(n=34, acierto=0.47, promedio=0.31, pf=1.50),
        ),
        aviso=("Regla en PRUEBA. Salio de una busqueda de 340 combinaciones, y "
               "el control mostro que del ruido salen unas 114 que parecen "
               "buenas. Sobrevivio a dos periodos nuevos, pero con 34 "
               "operaciones cada uno y un acierto que va de 68% a 47%. Ademas "
               "los dos periodos fueron alcistas. Operar con lote minimo."),
    )

    SALIDA.write_text(json.dumps(datos, indent=2, ensure_ascii=False),
                      encoding="utf-8")

    print(f"### Regla generada — {args.symbol.upper()} diario ###")
    print(f"entrenada con {Path(args.train).name}")
    print(f"{len(f)} velas, {datos['desde']} -> {datos['hasta']}\n")
    print("La regla se activa cuando SE CUMPLEN LAS DOS condiciones:")
    for c in datos["condiciones"]:
        print(f"  {c['variable']:<16} entre {c['desde']:>10.5f} y {c['hasta']:>10.5f}")
    print()
    print("  rel_ema50_200 = ema50 / ema200 - 1   (las dos del grafico DIARIO)")
    print("  adx5          = ADX(14) del grafico DIARIO")
    print()
    print(f"objetivo {datos['k_tp']} ATR, stop {datos['k_sl']} ATR, "
          f"{datos['horizonte_dias']} dias")
    print(f"\nGuardado en {SALIDA.resolve()}")
    print("La API lo lee de ahi. Si se borra, el endpoint devuelve NADA.")


if __name__ == "__main__":
    main()
