"""
entrenar.py — un solo comando por símbolo.

    py entrenar.py --symbol NAS100 ^
        --train datos/crudos/NAS100_TRAIN_....csv ^
        --holdout-a datos/crudos/NAS100_HOLDOUT_A_TPSL_....csv

Qué hace, en este orden:
  1. Carga TRAIN, construye features (core.py) UNA vez (no dependen de TP/SL).
  2. Barre TP = k_tp*ATR, SL = k_sl*ATR (grilla configurable) — no puntos
     fijos, para que el TP/SL no quede pegado a un nivel de precio que hoy
     es razonable y en 6 meses no.
  3. Para cada combinación y cada lado (BUY/SELL): descarta de entrada las
     que ni el baseline de dirección fija (comprar/vender siempre) puede
     ganar con el costo real — no tiene sentido entrenar un modelo para un
     TP/SL que ni la apuesta ciega más favorable gana.
  4. De las que sobreviven, entrena LogisticRegression (le ganó a
     GradientBoosting en la prueba de señal — ver conversación) y evalúa en
     HOLDOUT_A (nunca en TRAIN — fuga de información; nunca en HOLDOUT_B —
     ese es el que confirma una sola vez en validar.py).
  5. Se queda con la combinación que MEJOR PF da en HOLDOUT_A contra su
     propio baseline, con un mínimo de operaciones — no la que da el PF más
     alto a secas (eso sobreajusta al holdout de selección).
  6. Guarda el modelo (BUY y SELL, un solo archivo .pkl) y registra la
     versión en registry.json como "candidato" — NO la activa. Activarla es
     una decisión manual después de correr validar.py.

No re-normaliza nada con percentiles de train (ahí estaba el bug de
saturación del proyecto anterior) — las features de core.py ya son
dimensionless por diseño, así que un StandardScaler común (media/desvío,
sin clip) alcanza y no se rompe si el precio sale del rango histórico.
"""
import argparse
import warnings
from pathlib import Path

import joblib
import math
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

from core import cargar_csv_exportado, construir_features, etiquetar_tp_sl, FEATURE_LIST
from registry import Registry

warnings.filterwarnings("ignore")

COSTO_PUNTOS = 3          # spread + slippage asumido, en puntos. Ajustar si hace falta.
HORIZONTE_VELAS = 288      # 1 dia en M5. Si no toca TP ni SL en este plazo, se descarta.
MIN_OPERACIONES_HOLDOUT_A = 300  # antes 80. Con 80 operaciones el PF se dispara
                                 # por azar y el barrido de 288 combinaciones termina
                                 # eligiendo el que tuvo mas suerte, no el mas robusto.
                                 # Ademas las operaciones se solapan (horizonte de 288
                                 # velas sobre ~48 dias), asi que 80 operaciones son
                                 # ~30 casos realmente distintos.
# Grilla ampliada hacia abajo: sin class_weight='balanced' las probabilidades
# ya no estan infladas, asi que con tasas base de 25-33% casi ninguna fila
# superaria 0.60 y el modelo no operaria nunca.
UMBRALES_A_PROBAR = [0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]

# Piso minimo de SL, en multiplos de ATR. Un SL menor a esto puede dar el
# PF mas alto EN EL BACKTEST, pero en ejecucion real es mas sensible al
# spread del momento de lo que el backtest puede ver -- ya lo confirmamos
# en vivo con NAS100 compra (k_sl=0.5, winrate 8.4%, SL de apenas 8 puntos
# saltando por spread en horario de baja liquidez). No se prohibe evaluarlo
# (queda en la grilla, se ve en el log), pero no puede ganar como candidato
# final. Se puede relajar por linea de comando con --sl-minimo si hace
# falta, pero el default es a proposito conservador.
MIN_K_SL = 1.0

# Grilla de multiplicadores de ATR. k_tp/k_sl > 1 casi siempre (TP mas lejos
# que SL) porque es la logica de "ganancias grandes, perdidas controladas"
# que se pidio -- pero se deja probar parejo tambien por si el mercado no
# se comporta como se espera.
GRID_K_TP = [2, 3, 4, 6, 8, 10]
GRID_K_SL = [0.5, 0.75, 1, 1.5, 2, 3]


def pf_baseline_direccion_fija(high, low, close, tp, sl, horizonte, lado, costo):
    """PF de 'siempre {lado} en cada vela' — el piso que cualquier modelo
    tiene que superar. Si ni esto gana, ese TP/SL no sirve para nada."""
    labels, _ = etiquetar_tp_sl(high, low, close, tp, sl, horizonte, lado)
    mask = labels != -1
    resueltas = labels[mask]
    if len(resueltas) == 0:
        return 0.0, 0
    tp_res = tp[mask] if not np.isscalar(tp) else np.full(mask.sum(), tp)
    sl_res = sl[mask] if not np.isscalar(sl) else np.full(mask.sum(), sl)
    ganancias = tp_res[resueltas == 1].sum()
    perdidas = sl_res[resueltas == 0].sum() + len(resueltas) * costo
    pf = ganancias / perdidas if perdidas > 0 else (float("inf") if ganancias > 0 else 0.0)
    return pf, len(resueltas)


def redondear_precio(x):
    """Redondea a ~6 cifras significativas en vez de a 2 decimales fijos, para
    que sirva igual en indices (75.08) que en forex (0.00076214)."""
    if x is None or x <= 0:
        return 0.0
    return round(float(x), max(2, 5 - int(math.floor(math.log10(abs(x))))))


def pf_modelo(y_true, probs, umbral, tp, sl, costo):
    opera = probs >= umbral
    n = int(opera.sum())
    if n == 0:
        return 0.0, 0, 0.0
    aciertos = (y_true[opera] == 1).sum()
    fallos = (y_true[opera] == 0).sum()
    # TP/SL elemento por elemento de las filas OPERADAS. Antes se usaba el
    # promedio de TODAS las filas, lo que inflaba o desinflaba el PF segun si
    # el modelo prefiere momentos de ATR alto o bajo. Ahora coincide con el
    # criterio de validar.py.
    tp_arr = np.full(len(y_true), tp, dtype=float) if np.isscalar(tp) else np.asarray(tp, dtype=float)
    sl_arr = np.full(len(y_true), sl, dtype=float) if np.isscalar(sl) else np.asarray(sl, dtype=float)
    y_op = y_true[opera]
    ganancias = tp_arr[opera][y_op == 1].sum()
    perdidas = sl_arr[opera][y_op == 0].sum() + n * costo
    pf = ganancias / perdidas if perdidas > 0 else (float("inf") if ganancias > 0 else 0.0)
    wr = aciertos / n
    return pf, n, wr


def evaluar_combo(feat_train, feat_a, k_tp, k_sl, lado, costo, horizonte):
    tp_train = k_tp * feat_train['atr5'].values
    sl_train = k_sl * feat_train['atr5'].values
    tp_a = k_tp * feat_a['atr5'].values
    sl_a = k_sl * feat_a['atr5'].values

    lab_tr, _ = etiquetar_tp_sl(feat_train['high'].values, feat_train['low'].values,
                                 feat_train['close'].values, tp_train, sl_train, horizonte, lado)
    lab_a, _ = etiquetar_tp_sl(feat_a['high'].values, feat_a['low'].values,
                                feat_a['close'].values, tp_a, sl_a, horizonte, lado)

    mask_tr = lab_tr != -1
    mask_a = lab_a != -1
    if mask_tr.sum() < 500 or mask_a.sum() < MIN_OPERACIONES_HOLDOUT_A:
        return None

    # Filtro rapido: si ni el baseline de direccion fija gana en holdout A
    # con este TP/SL, no vale la pena entrenar nada.
    pf_base_a, n_base_a = pf_baseline_direccion_fija(
        feat_a['high'].values, feat_a['low'].values, feat_a['close'].values,
        tp_a, sl_a, horizonte, lado, costo)
    if pf_base_a < 0.85:   # un poco de margen, no exactamente 1.0
        return None

    X_tr = feat_train.loc[mask_tr, FEATURE_LIST].values
    y_tr = lab_tr[mask_tr]
    X_a = feat_a.loc[mask_a, FEATURE_LIST].values
    y_a = lab_a[mask_a]

    if len(np.unique(y_tr)) < 2:
        return None

    scaler = StandardScaler().fit(X_tr)
    # SIN class_weight='balanced'. Con reponderacion, predict_proba estima la
    # probabilidad bajo un prior artificial 50/50, no la real: declaraba ~18
    # puntos de mas cuando la tasa base estaba por debajo del 50%, y de menos
    # cuando estaba por encima (confirmado en los 5 simbolos, con el signo
    # cambiando justo donde corresponde). Ahora la probabilidad significa algo.
    modelo = LogisticRegression(max_iter=1000)
    modelo.fit(scaler.transform(X_tr), y_tr)

    probs_a = modelo.predict_proba(scaler.transform(X_a))[:, 1]
    try:
        auc = roc_auc_score(y_a, probs_a)
    except ValueError:
        auc = float('nan')

    mejor = None
    for umbral in UMBRALES_A_PROBAR:
        pf, n, wr = pf_modelo(y_a, probs_a, umbral, tp_a[mask_a], sl_a[mask_a], costo)
        if n < MIN_OPERACIONES_HOLDOUT_A:
            continue
        if pf <= pf_base_a:   # tiene que ganarle a la apuesta ciega, si no no aporta
            continue
        if mejor is None or pf > mejor['pf']:
            mejor = dict(umbral=umbral, pf=pf, n=n, wr=wr)

    if mejor is None:
        return None

    return dict(
        k_tp=k_tp, k_sl=k_sl, lado=lado, auc_holdoutA=auc,
        pf_baseline_a=pf_base_a, n_baseline_a=n_base_a,
        umbral=mejor['umbral'], pf_holdoutA=mejor['pf'],
        n_holdoutA=mejor['n'], wr_holdoutA=mejor['wr'],
        scaler=scaler, modelo=modelo,
    )


def entrenar_lado(feat_train, feat_a, lado, costo, horizonte, sl_minimo):
    print(f"\n--- {lado}: barriendo {len(GRID_K_TP)*len(GRID_K_SL)} combinaciones TP/SL (multiplos de ATR) ---")
    resultados = []
    for k_tp in GRID_K_TP:
        for k_sl in GRID_K_SL:
            r = evaluar_combo(feat_train, feat_a, k_tp, k_sl, lado, costo, horizonte)
            if r is not None:
                resultados.append(r)
                bajo_piso = " (< piso, no puede ganar)" if k_sl < sl_minimo else ""
                print(f"  k_tp={k_tp:>4} k_sl={k_sl:>4}  PF_holdoutA={r['pf_holdoutA']:.3f} "
                      f"(baseline={r['pf_baseline_a']:.3f})  n={r['n_holdoutA']:<4}  "
                      f"umbral={r['umbral']}  AUC={r['auc_holdoutA']:.3f}{bajo_piso}")

    if not resultados:
        print(f"  Ningun combo de TP/SL para {lado} le gana a su baseline en HOLDOUT_A. "
              f"No hay candidato para este lado.")
        return None

    candidatos_validos = [r for r in resultados if r['k_sl'] >= sl_minimo]
    if not candidatos_validos:
        mejor_descartado = max(resultados, key=lambda r: r['pf_holdoutA'])
        print(f"  Todos los combos que superaron el baseline tienen k_sl < {sl_minimo} "
              f"(el mejor descartado: k_sl={mejor_descartado['k_sl']}, "
              f"PF={mejor_descartado['pf_holdoutA']:.3f}) -- no hay candidato con SL "
              f"suficientemente ancho para {lado}.")
        return None

    ganador = max(candidatos_validos, key=lambda r: r['pf_holdoutA'])
    print(f"  -> Ganador {lado}: k_tp={ganador['k_tp']} k_sl={ganador['k_sl']} "
          f"umbral={ganador['umbral']}  PF_holdoutA={ganador['pf_holdoutA']:.3f}")
    return ganador


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--train", required=True)
    ap.add_argument("--holdout-a", required=True, dest="holdout_a")
    ap.add_argument("--costo", type=float, default=COSTO_PUNTOS)
    ap.add_argument("--horizonte", type=int, default=HORIZONTE_VELAS)
    ap.add_argument("--sl-minimo", type=float, default=MIN_K_SL, dest="sl_minimo",
                     help=f"piso minimo de k_sl (multiplo de ATR), default {MIN_K_SL}")
    ap.add_argument("--version", default=None)
    args = ap.parse_args()

    symbol = args.symbol.upper()
    print(f"=== entrenar.py — {symbol} ===")

    print(f"Cargando TRAIN: {args.train}")
    df_train = cargar_csv_exportado(args.train)
    feat_train = construir_features(df_train)
    print(f"  {len(feat_train)} filas, {feat_train['fecha'].min()} -> {feat_train['fecha'].max()}")
    if df_train['atr5_aproximado'].iloc[0]:
        print("  AVISO: atr5 en TRAIN es una aproximacion (EWM sobre historico), no viene "
              "de iATR real -- este CSV no trae atr5 en la url (exportado con una version "
              "vieja del script). validar.py debe chequear que no haya drift grande contra "
              "el atr5 real que reporte el EA en vivo.")
    else:
        print("  OK: atr5 en TRAIN es el REAL (iATR de MT4, viene en la url) -- no es aproximado.")

    # Chequeo de escala: costo fijo vs. ATR del simbolo. Un costo pensado para
    # indices (precio en miles) puede ser miles de veces mas grande que el TP
    # tipico de un forex (precio ~1.0-2.0) -- si eso pasa, NINGUNA combinacion
    # le va a ganar nunca al baseline, no por falta de señal real, sino porque
    # el costo se come todo antes de empezar. Confirmado con EURUSD: ATR
    # mediana 0.00032, costo fijo 3 -- 4700x mas grande que el TP tipico.
    atr_mediana = feat_train['atr5'].median()
    tp_tipico_min = GRID_K_TP[0] * atr_mediana
    if args.costo > tp_tipico_min * 0.5:
        print(f"\n  ⚠️  ALARMA DE ESCALA: costo={args.costo} vs. ATR mediana={atr_mediana:.6f} "
              f"(TP mas chico posible en la grilla ≈ {tp_tipico_min:.6f}).")
        print(f"      El costo fijo es mas grande que la mitad del TP mas chico que se va a probar.")
        print(f"      Con esto, es matematicamente imposible que algun combo le gane al baseline --")
        print(f"      no es una conclusion real sobre si hay señal, es un problema de unidades.")
        print(f"      Pasa costo real de este simbolo con --costo (revisar el spread real en MT4,")
        print(f"      en las mismas unidades que el precio -- para forex, algo como 0.00003-0.0002).")
        raise SystemExit(1)

    print(f"Cargando HOLDOUT_A: {args.holdout_a}")
    df_a = cargar_csv_exportado(args.holdout_a)
    feat_a = construir_features(df_a)
    print(f"  {len(feat_a)} filas, {feat_a['fecha'].min()} -> {feat_a['fecha'].max()}")

    ganador_buy = entrenar_lado(feat_train, feat_a, 'BUY', args.costo, args.horizonte, args.sl_minimo)
    ganador_sell = entrenar_lado(feat_train, feat_a, 'SELL', args.costo, args.horizonte, args.sl_minimo)

    if ganador_buy is None and ganador_sell is None:
        print(f"\n[{symbol}] No se encontro ninguna combinacion TP/SL que le gane a su "
              f"baseline en HOLDOUT_A, ni en BUY ni en SELL. No se guarda nada. "
              f"Esto es una respuesta valida: puede ser que no haya señal explotable "
              f"para este símbolo con estas features.")
        return

    version = args.version or f"v1_{pd.Timestamp.now().strftime('%Y%m%d')}"
    carpeta_modelo = Path("modelos") / symbol
    carpeta_modelo.mkdir(parents=True, exist_ok=True)
    archivo_modelo = carpeta_modelo / f"{version}.pkl"

    # k_tp/k_sl van ADENTRO del paquete (no solo en registry.json) porque
    # api.py y validar.py necesitan recalcular tp/sl real por vela usando el
    # atr5 de cada momento -- un tp/sl fijo se volvería a saturar con el
    # tiempo, exactamente el problema que ya arreglamos en las features.
    paquete = {}
    if ganador_buy:
        paquete['buy'] = {'scaler': ganador_buy['scaler'], 'modelo': ganador_buy['modelo'],
                           'umbral': ganador_buy['umbral'],
                           'k_tp': ganador_buy['k_tp'], 'k_sl': ganador_buy['k_sl']}
    if ganador_sell:
        paquete['sell'] = {'scaler': ganador_sell['scaler'], 'modelo': ganador_sell['modelo'],
                            'umbral': ganador_sell['umbral'],
                            'k_tp': ganador_sell['k_tp'], 'k_sl': ganador_sell['k_sl']}
    joblib.dump(paquete, archivo_modelo)

    # tp/sl que se registran: los del lado ganador con mejor PF_holdoutA
    # (si BUY y SELL usan multiplicadores distintos, se documenta la
    # diferencia en notas -- la API por ahora manda un solo tp/sl por
    # símbolo, ver limitacion en el reporte)
    candidatos_tpsl = [g for g in (ganador_buy, ganador_sell) if g is not None]
    mejor_general = max(candidatos_tpsl, key=lambda g: g['pf_holdoutA'])
    atr_mediana_train = float(feat_train['atr5'].median())
    # round(x, 2) dejaba tp=0.0 y sl=0.0 en forex (2 * 0.0005 -> 0.0), y el EA
    # descarta la orden si tp o sl son 0. Se redondea por cifras significativas.
    tp_final = redondear_precio(mejor_general['k_tp'] * atr_mediana_train)
    sl_final = redondear_precio(mejor_general['k_sl'] * atr_mediana_train)

    notas = (f"BUY: {'k_tp='+str(ganador_buy['k_tp'])+' k_sl='+str(ganador_buy['k_sl']) if ganador_buy else 'sin candidato'}. "
             f"SELL: {'k_tp='+str(ganador_sell['k_tp'])+' k_sl='+str(ganador_sell['k_sl']) if ganador_sell else 'sin candidato'}. "
             f"tp/sl registrados en puntos = multiplicador x mediana(ATR14) de TRAIN "
             f"({atr_mediana_train:.2f}). En producción el TP/SL real varía con el ATR "
             f"del momento -- esto es solo el valor de referencia para registry.json.")

    reg = Registry()
    reg.registrar_version(
        symbol=symbol, version_id=version,
        archivo_modelo=str(archivo_modelo), archivo_scaler=str(archivo_modelo),
        features=FEATURE_LIST,
        tp=tp_final, sl=sl_final, costo=args.costo, horizonte=args.horizonte,
        entrenado_con={"desde": str(feat_train['fecha'].min().date()),
                       "hasta": str(feat_train['fecha'].max().date()),
                       "n_filas": len(feat_train)},
        estado="candidato",
        notas=notas,
    )

    print(f"\n[{symbol}] Candidato guardado: {archivo_modelo}")
    print(f"[{symbol}] Registrado en registry.json como '{version}' (estado=candidato, NO activo)")
    print(f"[{symbol}] Siguiente paso: py validar.py --symbol {symbol} --version {version}")


if __name__ == "__main__":
    main()
