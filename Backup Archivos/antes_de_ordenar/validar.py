"""
validar.py — LA comprobación única. Un comando, un reporte.

    py validar.py --symbol NAS100 --version v1_20260805 ^
        --holdout-b datos/crudos/NAS100_HOLDOUT_B_CONFIRM_....csv ^
        [--log datos/logs/log_NAS100_2026_08_04.csv]

HOLDOUT_B es el único holdout que esto toca — nunca se usó para elegir
TP/SL ni umbral (eso pasó en HOLDOUT_A, dentro de entrenar.py). Corrida
única: no se re-corre ajustando nada según el resultado. Si da mal, la
respuesta es cambiar el enfoque, no repetir con otro parámetro hasta que
pase (eso invalidaría la prueba).

Qué hace, en este orden (reglas del resumen del proyecto anterior, §11):
  1. PF del modelo en HOLDOUT_B vs baseline de dirección fija (mismo TP/SL,
     mismo costo, mismo período). Ningún PF vale sin esta comparación.
  2. Null por permutación circular: agarra el patrón exacto de cuándo
     opera el modelo (respeta el agrupamiento en rachas) y lo desplaza a
     posiciones aleatorias del mismo holdout, muchas veces. Si el PF real
     no se distingue de esos PF sintéticos, no hay señal — es azar con
     suerte.
  3. Chequeo de saturación: cuántas filas de HOLDOUT_B caen fuera del
     rango que vio el modelo en TRAIN, feature por feature.
  4. Reconciliación contra log real (si se pasa --log y hay precio que lo
     cubra): cuánto hubiese ganado/perdido el modelo actual sobre las
     señales que ya se mandaron en producción.

Un solo reporte en reportes/<symbol>_<version>_<fecha>.md — nunca un
archivo nuevo por corrida ni por chequeo.
"""
import argparse
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from core import cargar_csv_exportado, construir_features, etiquetar_tp_sl, FEATURE_LIST
from registry import Registry

warnings.filterwarnings("ignore")

N_PERMUTACIONES_NULL = 2000


# =======================================================================
# 1. PF del modelo vs baseline
# =======================================================================
def calcular_pf(labels, opera_mask, tp_arr, sl_arr, costo):
    n = int(opera_mask.sum())
    if n == 0:
        return 0.0, 0, 0.0
    sub = labels[opera_mask]
    tp_sub = tp_arr[opera_mask]
    sl_sub = sl_arr[opera_mask]
    ganancias = tp_sub[sub == 1].sum()
    perdidas = sl_sub[sub == 0].sum() + n * costo
    pf = ganancias / perdidas if perdidas > 0 else (float("inf") if ganancias > 0 else 0.0)
    wr = (sub == 1).sum() / n
    return pf, n, wr


# =======================================================================
# 2. Null por permutación circular (conserva el agrupamiento de señales)
# =======================================================================
def null_permutacion_circular(labels, opera_mask, tp_arr, sl_arr, costo, n_iter):
    # La rotacion se hace SOLO dentro de las filas resueltas. Antes se rotaba
    # sobre el vector completo, asi que la mascara caia sobre filas con
    # label == -1: esas sumaban al costo pero nunca podian ganar, lo que hundia
    # la distribucion nula y hacia que el p-valor saliera mas chico de lo real.
    # Al rotar dentro de las resueltas, el null tiene exactamente el mismo n y
    # las mismas reglas que el caso real.
    resuelto = labels != -1
    idx_res = np.where(resuelto)[0]
    mask_res = opera_mask[idx_res]
    pf_reales, _, _ = calcular_pf(labels, opera_mask, tp_arr, sl_arr, costo)
    pf_nulls = []
    rng = np.random.RandomState(42)
    for _ in range(n_iter):
        k = rng.randint(1, len(idx_res))
        mask_shift = np.zeros(len(labels), dtype=bool)
        mask_shift[idx_res[np.roll(mask_res, k)]] = True
        pf_n, n_n, _ = calcular_pf(labels, mask_shift, tp_arr, sl_arr, costo)
        if n_n > 0:
            pf_nulls.append(pf_n)
    pf_nulls = np.array(pf_nulls)
    p_valor = float((pf_nulls >= pf_reales).mean()) if len(pf_nulls) else float("nan")
    return dict(pf_real=pf_reales, p_valor=p_valor,
                null_p50=float(np.median(pf_nulls)) if len(pf_nulls) else float("nan"),
                null_p95=float(np.percentile(pf_nulls, 95)) if len(pf_nulls) else float("nan"))


# =======================================================================
# 3. Saturación: filas de HOLDOUT_B fuera del rango visto en TRAIN
# =======================================================================
def chequear_saturacion(feat_train, feat_holdout):
    filas = []
    for f in FEATURE_LIST:
        lo, hi = feat_train[f].min(), feat_train[f].max()
        fuera = ((feat_holdout[f] < lo) | (feat_holdout[f] > hi)).mean()
        filas.append((f, lo, hi, fuera))
    return pd.DataFrame(filas, columns=["feature", "min_train", "max_train", "pct_fuera_holdout"])


# =======================================================================
# 4. Reconciliación contra log real
# =======================================================================
def reconciliar_log(path_log, feat_precio, paquete, costo, horizonte):
    """path_log: CSV real de MetaTrader (formato log_<SYM>_<fecha>.csv).
    feat_precio: DataFrame con fecha/high/low/close/atr5 que DEBE cubrir las
    fechas del log -- si no las cubre, se avisa y se salta, no se inventa.
    paquete: el dict cargado del .pkl (con k_tp/k_sl por lado), para usar el
    TP/SL correcto segun el lado de cada señal, con el ATR real de ese
    momento -- no un TP/SL fijo igual para BUY y SELL."""
    log = pd.read_csv(path_log, sep=';')
    log['date'] = pd.to_datetime(log['date'], format='%Y.%m.%d %H:%M')

    cubre = (log['date'].min() >= feat_precio['fecha'].min()) and \
            (log['date'].max() <= feat_precio['fecha'].max())
    if not cubre:
        return None, (f"El log va de {log['date'].min()} a {log['date'].max()}, pero los "
                       f"datos de precio disponibles van de {feat_precio['fecha'].min()} a "
                       f"{feat_precio['fecha'].max()}. Faltan datos de precio para reconciliar "
                       f"-- re-exportar con EXPORTAR_DATASETS_3PERIODOS.mq4 cubriendo esas fechas.")

    precio = feat_precio.set_index('fecha')
    resultados = []  # (lado, resultado, tp_usado, sl_usado)
    for _, fila in log.iterrows():
        lado = fila.get('score_modelo')
        if lado not in ('BUY', 'SELL'):
            continue
        clave = 'buy' if lado == 'BUY' else 'sell'
        if clave not in paquete:
            continue  # el modelo nuevo no tiene candidato para ese lado
        k_tp, k_sl = paquete[clave]['k_tp'], paquete[clave]['k_sl']

        idx = precio.index.searchsorted(fila['date'])
        if idx >= len(precio) or idx == 0:
            continue
        atr_momento = precio['atr5'].values[idx - 1]
        tp_dist = k_tp * atr_momento
        sl_dist = k_sl * atr_momento

        high = precio['high'].values[idx:idx + horizonte]
        low = precio['low'].values[idx:idx + horizonte]
        close_entrada = precio['close'].values[idx - 1]
        tp_level = close_entrada + tp_dist if lado == 'BUY' else close_entrada - tp_dist
        sl_level = close_entrada - sl_dist if lado == 'BUY' else close_entrada + sl_dist
        resultado = None
        for h, l in zip(high, low):
            toco_tp = h >= tp_level if lado == 'BUY' else l <= tp_level
            toco_sl = l <= sl_level if lado == 'BUY' else h >= sl_level
            if toco_sl:
                resultado = 0
                break
            if toco_tp:
                resultado = 1
                break
        if resultado is not None:
            resultados.append((lado, resultado, tp_dist, sl_dist))

    if not resultados:
        return None, "El log no tiene señales BUY/SELL resueltas dentro del rango de precio disponible."

    ganancias = sum(tp for _, r, tp, _ in resultados if r == 1)
    perdidas = sum(sl for _, r, _, sl in resultados if r == 0) + len(resultados) * costo
    pf = ganancias / perdidas if perdidas > 0 else float("inf")
    n = len(resultados)
    wins = sum(1 for _, r, _, _ in resultados if r == 1)
    por_lado = {}
    for lado_r in ('BUY', 'SELL'):
        sub = [r for l, r, _, _ in resultados if l == lado_r]
        if sub:
            por_lado[lado_r] = dict(n=len(sub), wins=sum(sub), pct=sum(sub) / len(sub))
    return dict(n=n, wins=wins, losses=n - wins, pf=pf,
                pct_ganadas=wins / n, por_lado=por_lado), None


# =======================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--train", required=True)
    ap.add_argument("--holdout-b", required=True, dest="holdout_b")
    ap.add_argument("--log", default=None)
    ap.add_argument("--costo", type=float, default=3.0)
    ap.add_argument("--horizonte", type=int, default=288)
    args = ap.parse_args()

    symbol = args.symbol.upper()
    reg = Registry()
    entrada = reg._buscar(symbol, args.version)
    if entrada is None:
        raise SystemExit(f"No existe {symbol}/{args.version} en registry.json. Corré entrenar.py primero.")

    paquete = joblib.load(entrada["archivo_modelo"])

    print(f"=== validar.py — {symbol} / {args.version} ===")
    print("Cargando TRAIN (para el chequeo de saturación)...")
    feat_train = construir_features(cargar_csv_exportado(args.train))

    print("Cargando HOLDOUT_B (nunca tocado hasta ahora)...")
    feat_b = construir_features(cargar_csv_exportado(args.holdout_b))
    print(f"  {len(feat_b)} filas, {feat_b['fecha'].min()} -> {feat_b['fecha'].max()}")

    reporte = [f"# Validación — {symbol} / {args.version}",
               f"\nCorrida: {datetime.now().isoformat(timespec='seconds')}",
               f"\nHOLDOUT_B: {feat_b['fecha'].min()} -> {feat_b['fecha'].max()} ({len(feat_b)} filas)",
               "\n## 1-2. PF vs baseline y null por permutación circular\n"]

    resultados_lado = {}
    for lado, modelo_lado in paquete.items():
        k_tp, k_sl = modelo_lado["k_tp"], modelo_lado["k_sl"]
        tp_arr = k_tp * feat_b['atr5'].values
        sl_arr = k_sl * feat_b['atr5'].values
        lado_mayus = "BUY" if lado == "buy" else "SELL"

        labels, _ = etiquetar_tp_sl(feat_b['high'].values, feat_b['low'].values,
                                     feat_b['close'].values, tp_arr, sl_arr,
                                     args.horizonte, lado_mayus)
        mask_resuelto = labels != -1

        X = feat_b.loc[mask_resuelto, FEATURE_LIST].values
        probs = modelo_lado["modelo"].predict_proba(modelo_lado["scaler"].transform(X))[:, 1]
        opera = np.zeros(len(feat_b), dtype=bool)
        opera[np.where(mask_resuelto)[0]] = probs >= modelo_lado["umbral"]

        pf_modelo, n_modelo, wr_modelo = calcular_pf(labels, opera, tp_arr, sl_arr, args.costo)

        baseline_mask = mask_resuelto.copy()
        pf_base, n_base, wr_base = calcular_pf(labels, baseline_mask, tp_arr, sl_arr, args.costo)

        null = null_permutacion_circular(labels, opera, tp_arr, sl_arr, args.costo, N_PERMUTACIONES_NULL)

        resultados_lado[lado_mayus] = dict(pf_modelo=pf_modelo, n_modelo=n_modelo, wr_modelo=wr_modelo,
                                            pf_base=pf_base, n_base=n_base, **null)

        linea = (f"- **{lado_mayus}** (k_tp={k_tp} k_sl={k_sl} umbral={modelo_lado['umbral']}): "
                 f"PF_modelo={pf_modelo:.3f} (n={n_modelo}, WR={wr_modelo:.1%}) vs "
                 f"PF_baseline_direccion_fija={pf_base:.3f} (n={n_base}) — "
                 f"null: mediana={null['null_p50']:.3f} p95={null['null_p95']:.3f} "
                 f"**p={null['p_valor']:.4f}**"
                 f"{'  ✅ significativo (p<0.05) y supera baseline' if null['p_valor'] < 0.05 and pf_modelo > pf_base else '  ⚠️ NO pasa'}")
        print(linea)
        reporte.append(linea)

    print("\n--- 3. Saturación (TRAIN vs HOLDOUT_B) ---")
    sat = chequear_saturacion(feat_train, feat_b)
    reporte.append("\n## 3. Saturación — filas de HOLDOUT_B fuera del rango de TRAIN\n")
    reporte.append(sat.to_string(index=False))
    peor = sat.sort_values("pct_fuera_holdout", ascending=False).iloc[0]
    print(sat.to_string(index=False))
    if peor["pct_fuera_holdout"] > 0.05:
        alerta = (f"\n⚠️ '{peor['feature']}' tiene {peor['pct_fuera_holdout']:.1%} de HOLDOUT_B "
                  f"fuera del rango visto en TRAIN. Evaluar con cautela.")
        print(alerta)
        reporte.append(alerta)
    else:
        reporte.append("\nSin señales de saturación relevante.")

    print("\n--- 4. Reconciliación contra log real ---")
    reporte.append("\n## 4. Reconciliación contra log real\n")
    if args.log:
        res, error = reconciliar_log(args.log, feat_b, paquete, args.costo, args.horizonte)
        if error:
            print(f"  Saltado: {error}")
            reporte.append(f"Saltado: {error}")
        else:
            linea = (f"MODELO VIEJO (lo que realmente se mandó ese día): "
                     f"n={res['n']}  ganadas={res['wins']} ({res['pct_ganadas']:.1%})  "
                     f"perdidas={res['losses']}  PF={res['pf']:.3f}")
            print(f"  {linea}")
            reporte.append(linea)
            for lado_r, d in res['por_lado'].items():
                sub_linea = f"    {lado_r}: n={d['n']} ganadas={d['wins']} ({d['pct']:.1%})"
                print(sub_linea)
                reporte.append(sub_linea)

            # Comparación directa: qué hubiera hecho el modelo NUEVO ese
            # mismo día, con los mismos datos de precio reales. No reemplaza
            # un log real del modelo nuevo (todavía no corrió en vivo), pero
            # da la comparación inmediata sin esperar a que se acumule log.
            log_raw = pd.read_csv(args.log, sep=';')
            log_raw['date'] = pd.to_datetime(log_raw['date'], format='%Y.%m.%d %H:%M')
            desde, hasta = log_raw['date'].min(), log_raw['date'].max()
            print(f"\n  MODELO NUEVO en ese mismo rango ({desde} -> {hasta}), usando HOLDOUT_B:")
            reporte.append(f"\nMODELO NUEVO en ese mismo rango ({desde} -> {hasta}), usando HOLDOUT_B:")
            for lado_r, modelo_lado in paquete.items():
                lado_mayus = "BUY" if lado_r == "buy" else "SELL"
                k_tp, k_sl = modelo_lado["k_tp"], modelo_lado["k_sl"]
                ventana = (feat_b['fecha'] >= desde) & (feat_b['fecha'] <= hasta)
                sub = feat_b[ventana]
                if len(sub) == 0:
                    continue
                tp_arr = k_tp * sub['atr5'].values
                sl_arr = k_sl * sub['atr5'].values
                labels, _ = etiquetar_tp_sl(sub['high'].values, sub['low'].values,
                                             sub['close'].values, tp_arr, sl_arr,
                                             args.horizonte, lado_mayus)
                mask_resuelto = labels != -1
                if mask_resuelto.sum() == 0:
                    continue
                X = sub.loc[mask_resuelto, FEATURE_LIST].values
                probs = modelo_lado["modelo"].predict_proba(modelo_lado["scaler"].transform(X))[:, 1]
                opera = np.zeros(len(sub), dtype=bool)
                opera[np.where(mask_resuelto)[0]] = probs >= modelo_lado["umbral"]
                pf_d, n_d, wr_d = calcular_pf(labels, opera, tp_arr, sl_arr, args.costo)
                linea2 = f"    {lado_mayus}: n={n_d}  WR={wr_d:.1%}  PF={pf_d:.3f}" if n_d else f"    {lado_mayus}: 0 señales en esa ventana"
                print(linea2)
                reporte.append(linea2)
    else:
        print("  No se pasó --log. Saltado.")
        reporte.append("No se pasó --log en esta corrida.")

    Path("reportes").mkdir(exist_ok=True)
    ruta_reporte = Path("reportes") / f"{symbol}_{args.version}_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    ruta_reporte.write_text("\n".join(reporte), encoding="utf-8")
    print(f"\nReporte guardado: {ruta_reporte}")

    aprobados = [l for l, r in resultados_lado.items() if r['p_valor'] < 0.05 and r['pf_modelo'] > r['pf_base']]

    # Esto es lo que faltaba conectar: guardar en registry.json exactamente
    # que lados aprobaron -- api.py va a leer esto y NO va a servir un lado
    # que no este en esta lista, sin importar que el .pkl lo tenga adentro.
    reg.marcar_lados_aprobados(symbol, args.version, aprobados)

    print(f"\n=== Resultado: {aprobados if aprobados else 'NINGÚN lado pasa la validación'} ===")
    print(f"registry.json actualizado: lados_aprobados={aprobados} para {symbol}/{args.version}")
    if aprobados:
        print(f"Para activar: python -c \"from registry import Registry; "
              f"Registry().activar('{symbol}', '{args.version}')\"")
    else:
        print("Ningún lado aprobado -- Registry().activar() va a rechazar esta version hasta que "
              "haya al menos un lado que pase.")


if __name__ == "__main__":
    main()
