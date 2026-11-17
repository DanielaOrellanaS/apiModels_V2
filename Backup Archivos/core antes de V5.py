"""
core.py — única fuente de verdad de features y etiquetas.

entrenar.py, validar.py y api.py importan de acá.

DECISIÓN CLAVE (corregida el 05-ago-2026, ver README): cada feature se
calcula a partir de UNA sola foto de indicadores — los mismos campos que el
EA ya manda por URL en cada request. Nada de ventanas móviles calculadas
sobre historial completo del lado del servidor, porque la API en producción
no recibe una serie, recibe un request a la vez. Esto es lo que garantiza
que entrenar.py y api.py calculen la feature EXACTAMENTE igual — no hay
segunda implementación que se pueda desincronizar.

Campos que llegan por request (confirmados correctos, 0% en cero, indexados
bien): c5, ema550, ema5200, macdLine5, signalLine5, adx5, diPlus5, diMinus5,
r5, r15, m5, s5, m15, s15, atr5 (atr5 es NUEVO, ver abajo).

Se descartaron (ver README para el detalle de cada bug):
  - ema50_prev / ema5200_prev (M5): duplicados de ema550/ema5200, r~0.99999.
  - todo el bloque M15 de EMA/MACD/ADX (ema5015...diMinus15): usa el índice
    de vela M5 para pedir una vela M15 -> ~0 en el historico. No se usa.
  - ret1 (retorno de 1 vela): el campo 'c5d' que debía traer el cierre
    anterior en realidad manda el mismo valor que 'c5' (bug de copy-paste
    en el armado de URL). Sin cierre anterior real, no se puede calcular
    sin tocar el EA para un campo de bajo valor (1 vela de retorno es casi
    puro ruido). Se descarta en vez de agregar más campos al request.
  - percentil_inf / percentil_sup: siempre null en la respuesta real.

atr5 es un campo NUEVO que hay que agregar al EA (una línea: iATR). Se pide
igual porque el TP/SL van a ser múltiplos de ATR (ver plan de entrenar.py),
así que el EA lo va a necesitar de todas formas para abrir la orden.

Para el HISTÓRICO (los CSV ya exportados no traen atr5, porque el EA viejo
no lo mandaba), se aproxima con ATR14 calculado en pandas sobre el
histórico. Es una aproximación — puede haber una pequeña diferencia de
escala contra el iATR real de MT4 (distinta convención de suavizado).
validar.py tiene que chequear que la distribución de atr5 en producción no
se dispare respecto a la del entrenamiento antes de confiar en el modelo.
"""
import re
import numpy as np
import pandas as pd

URL_FIELDS_CONFIABLES = [
    'r5', 'r15', 'm5', 's5', 'm15', 's15',
    'adx5', 'diPlus5', 'diMinus5', 'macdLine5', 'signalLine5',
    'ema550', 'ema5200',
    # V5: campos que ya venian en la URL pero no se usaban, mas dos nuevos.
    'h5', 'l5', 'v5', 'v5ma20', 'c5d',
]

# 09-sep-2026: las 3 variables de M15 (rsi15, stoch_m15, stoch_s15) VUELVEN,
# pero SOLO sirven si el CSV se exporto con EXPORTAR_DATASETS_3PERIODOS_V4.mq4
# o posterior.
#
# Historia: hasta V3, el exportador las leia con
#     barra15 = iBarShift(simbolo, PERIOD_M15, hora_de_la_vela_M5)
# o sea la vela M15 que CONTIENE a la de 5 minutos. Sobre historico esa vela ya
# esta cerrada, asi que la fila de las 10:05 guardaba el indicador de la M15 de
# 10:00-10:15: diez minutos de futuro. El EA en vivo no puede tener eso, y por
# eso el modelo mostraba +30% a +45% de ventaja en los 12 meses del CSV y caia
# a 25-33% operando.
#
# Cuanto valian esas 3 variables: entrenando sin ellas (v4, 08-sep) la ventaja
# se desplomo de +39% a +3% y el AUC de 0.67 a 0.51 (0.50 = moneda al aire).
# Es decir, TODO el poder predictivo venia de la fuga.
#
# V4 del exportador usa la ultima M15 ya cerrada al momento de la consulta,
# que es lo mismo que lee el EA. Si se entrena con CSVs viejos (V3 o
# anteriores) la fuga vuelve: hay que reexportar.
# --- V5 (09-sep-2026): 6 variables nuevas -------------------------------
# Las 15 anteriores son todas indicadores derivados del precio, y sin la fuga
# de futuro dieron AUC 0.47-0.57 en los 8 simbolo/lado probados: la zona del
# azar. La hipotesis de V5 es que faltaba informacion de OTRO tipo, no mas
# indicadores del mismo precio.
#
#   vol_rel     actividad de esta vela contra su promedio de 20. El volumen
#               crudo no sirve (cambia de escala entre simbolos y epocas);
#               el cociente si es comparable.
#   rango_rel   que tan grande fue la vela contra el ATR. Distingue una vela
#               ancha de una angosta dentro del mismo nivel de volatilidad.
#   cierre_pos  donde cerro dentro de su propio rango. Cerca de 1 = cerro en
#               el maximo (presion compradora); cerca de 0 = en el minimo.
#   ret1        retorno de una vela. Antes no se podia: el campo c5d mandaba
#               el mismo valor que c5 (bug de copy-paste, arreglado en V5).
#   hora_sin/cos  hora del dia en forma ciclica, para que las 23:55 y las
#               00:05 queden cerca en vez de en extremos opuestos. Hasta
#               ahora el modelo trataba igual las 3 AM que la apertura de
#               Nueva York.
#
# REQUIERE CSV exportado con EXPORTAR_DATASETS_3PERIODOS_V5.mq4 o posterior.
FEATURE_LIST = [
    'rel_ema50', 'rel_ema200', 'rel_ema50_200',
    'atr_rel',
    'rsi5', 'rsi15',
    'stoch_m5', 'stoch_s5', 'stoch_m15', 'stoch_s15',
    'adx5', 'di_diff5',
    'macd_rel', 'macdsig_rel', 'macd_hist_rel',
    'vol_rel', 'rango_rel', 'cierre_pos', 'ret1', 'hora_sin', 'hora_cos',
]

LABEL_PARAMS_DEFAULT = dict(horizonte=288)  # velas M5 (288 = 1 dia). tp/sl se buscan, no son fijos.


# =======================================================================
# Carga de CSV historico exportado por EXPORTAR_DATASETS_3PERIODOS.mq4
# =======================================================================
def cargar_csv_exportado(path):
    df = pd.read_csv(path, sep=';', encoding='utf-8')
    df['fecha'] = pd.to_datetime(df['fecha'], format='%Y.%m.%d %H:%M')
    for c in ['open', 'high', 'low', 'close', 'volumen']:
        df[c] = df[c].astype(float)
    for f in URL_FIELDS_CONFIABLES:
        patron = re.compile(r'[&?]' + f + r'=([\-0-9.]+)')
        df[f] = df['url'].str.extract(patron).astype(float)
    df = df.sort_values('fecha').reset_index(drop=True)

    # atr5 REAL: desde el 18-ago-2026, EXPORTAR_DATASETS_3PERIODOS_V3.mq4 lo
    # manda en la URL (mismo iATR(simbolo, PERIOD_M5, 14, barra) que usa el
    # EA en vivo). Los CSV viejos (V2 y anteriores) no lo tienen -- para esos
    # se sigue aproximando, pero SOLO como respaldo, nunca si el real esta
    # disponible. Confirmado con datos reales: la aproximacion desviaba
    # hasta 33% del ATR real segun el simbolo (chequear_drift_atr.py).
    patron_atr = re.compile(r'[&?]atr5=([\-0-9.]+)')
    atr5_real = df['url'].str.extract(patron_atr).astype(float).iloc[:, 0]
    tiene_atr_real = atr5_real.notna().mean() > 0.95  # casi todas las filas lo traen

    if tiene_atr_real:
        df['atr5'] = atr5_real
        df['atr5_aproximado'] = False
    else:
        prev_close = df['close'].shift(1)
        tr = pd.concat([
            (df['high'] - df['low']),
            (df['high'] - prev_close).abs(),
            (df['low'] - prev_close).abs(),
        ], axis=1).max(axis=1)
        df['atr5'] = tr.ewm(span=14, adjust=False).mean()
        df['atr5_aproximado'] = True  # marca para que validar.py lo tenga en cuenta
    return df


# =======================================================================
# Features — UNA foto de indicadores adentro, FEATURE_LIST afuera.
# Esta es la función que también va a llamar api.py con los campos del
# request en vivo. No debe usar nada que no venga en `fila`.
# =======================================================================
def construir_features_fila(fila):
    """fila: dict o Series con al menos los campos de URL_FIELDS_CONFIABLES
    + 'close' + 'atr5'. Devuelve un dict con FEATURE_LIST."""
    c5 = fila['close']
    out = {}
    out['rel_ema50']     = fila['ema550']  / c5 - 1
    out['rel_ema200']    = fila['ema5200'] / c5 - 1
    out['rel_ema50_200'] = fila['ema550']  / fila['ema5200'] - 1
    out['atr_rel']       = fila['atr5'] / c5

    out['rsi5']  = fila['r5']
    out['rsi15'] = fila['r15']
    out['stoch_m5']  = fila['m5']
    out['stoch_s5']  = fila['s5']
    out['stoch_m15'] = fila['m15']
    out['stoch_s15'] = fila['s15']
    out['adx5']     = fila['adx5']
    out['di_diff5'] = fila['diPlus5'] - fila['diMinus5']

    out['macd_rel']      = fila['macdLine5'] / c5
    out['macdsig_rel']   = fila['signalLine5'] / c5
    out['macd_hist_rel'] = (fila['macdLine5'] - fila['signalLine5']) / c5

    # ---- V5 ----
    v5, v5ma20 = fila.get('v5'), fila.get('v5ma20')
    out['vol_rel'] = (v5 / v5ma20) if (v5ma20 and v5ma20 > 0) else 1.0

    h5, l5 = fila.get('h5'), fila.get('l5')
    atr = fila['atr5']
    rango = (h5 - l5) if (h5 is not None and l5 is not None) else 0.0
    out['rango_rel'] = (rango / atr) if atr > 0 else 0.0
    # 0.5 = neutro, para velas sin rango (mercado parado)
    out['cierre_pos'] = ((c5 - l5) / rango) if rango > 0 else 0.5

    c5d = fila.get('c5d')
    out['ret1'] = (c5 / c5d - 1) if (c5d and c5d > 0) else 0.0

    # Hora del dia en forma ciclica. minutos desde medianoche -> angulo.
    f = fila.get('fecha')
    if f is not None and not (isinstance(f, float) and np.isnan(f)):
        minutos = f.hour * 60 + f.minute
    else:
        minutos = 0
    ang = 2 * np.pi * minutos / 1440.0
    out['hora_sin'] = float(np.sin(ang))
    out['hora_cos'] = float(np.cos(ang))
    return out


def construir_features(df):
    """Aplica construir_features_fila() a todo un DataFrame historico.
    Devuelve DataFrame con FEATURE_LIST + fecha/high/low/close (estas
    últimas para el etiquetado, no son features del modelo)."""
    # 'fecha' se necesita adentro para hora_sin/hora_cos
    filas = df.apply(construir_features_fila, axis=1, result_type='expand')
    filas['fecha'] = df['fecha'].values
    filas['high'] = df['high'].values
    filas['low'] = df['low'].values
    filas['close'] = df['close'].values
    filas['atr5'] = df['atr5'].values
    return filas


# =======================================================================
# Etiquetado: primer toque de TP o SL
# =======================================================================
def etiquetar_tp_sl(high, low, close, tp, sl, horizonte, lado):
    """
    lado: 'BUY' o 'SELL'. tp/sl: escalar (mismo valor para todas las filas)
    O array del mismo largo que close (TP/SL propio por fila — así se usa
    para TP/SL como múltiplo de ATR, que varía vela a vela). Unidades de
    precio absolutas en ambos casos.
    Entrada asumida = close[t]; se evalúa desde la vela t+1.
      1  -> TP tocado antes que SL dentro del horizonte
      0  -> SL tocado antes que TP (empate misma vela: gana SL, conservador)
      -1 -> no se resolvió dentro del horizonte (excluir del entrenamiento)
    """
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    n = len(close)
    tp_arr = np.full(n, tp, dtype=float) if np.isscalar(tp) else np.asarray(tp, dtype=float)
    sl_arr = np.full(n, sl, dtype=float) if np.isscalar(sl) else np.asarray(sl, dtype=float)
    labels = np.full(n, -1, dtype=np.int8)
    velas = np.full(n, -1, dtype=np.int32)

    for t in range(n - 1):
        entry = close[t]
        if lado == 'BUY':
            tp_level = entry + tp_arr[t]
            sl_level = entry - sl_arr[t]
        else:
            tp_level = entry - tp_arr[t]
            sl_level = entry + sl_arr[t]

        fin = min(t + 1 + horizonte, n)
        for k in range(t + 1, fin):
            toco_tp = (high[k] >= tp_level) if lado == 'BUY' else (low[k] <= tp_level)
            toco_sl = (low[k] <= sl_level) if lado == 'BUY' else (high[k] >= sl_level)
            if toco_sl:
                labels[t] = 0
                velas[t] = k - t
                break
            if toco_tp:
                labels[t] = 1
                velas[t] = k - t
                break
    return labels, velas


def preparar_dataset(path_csv, lado, tp, sl, horizonte=None):
    """Pipeline completo: CSV exportado -> features + etiqueta para un TP/SL
    dado (en unidades de precio, ya resuelto desde ATR). Filas no resueltas
    se descartan."""
    horizonte = horizonte or LABEL_PARAMS_DEFAULT['horizonte']
    df = cargar_csv_exportado(path_csv)
    feat = construir_features(df)
    labels, velas = etiquetar_tp_sl(
        feat['high'].values, feat['low'].values, feat['close'].values,
        tp=tp, sl=sl, horizonte=horizonte, lado=lado,
    )
    feat['label'] = labels
    feat['velas_hasta_resolver'] = velas
    resueltas = feat[feat['label'] != -1].reset_index(drop=True)
    return resueltas
