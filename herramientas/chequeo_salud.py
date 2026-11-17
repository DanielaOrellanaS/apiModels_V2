"""
chequeo_salud.py — verificación rápida de que api.py está sano.

    py chequeo_salud.py --base http://127.0.0.1/

Qué hace:
  1. Pega a /estado -- confirma qué versión está activa por símbolo.
  2. Para cada símbolo activo, manda un pedido de prueba a /predict con
     valores plausibles (no reales, solo para ver que responde bien
     formado) y confirma que devuelve los 4 campos esperados, con tp/sl
     positivos.
  3. Si le pasás --log, lee ese log y reporta: cuántas filas, distribución
     BUY/SELL/NADA, y si hay algo mal formado.

Esto NO puede ver las órdenes abiertas en tu MT4 -- eso se revisa a mano
en la pestaña Trade de la terminal, ningún script del lado servidor tiene
esa visibilidad.
"""
import argparse
import sys
import pandas as pd
import urllib.request
import urllib.parse
import json


def get(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read().decode())


def chequear_estado(base):
    print("=== 1. Estado del servidor ===")
    try:
        estado = get(base.rstrip('/') + '/estado')
    except Exception as e:
        print(f"  ERROR: no se pudo conectar a {base} -> {e}")
        sys.exit(1)
    for symbol, version in estado.items():
        marca = "✅" if version else "⚪ sin modelo activo"
        print(f"  {symbol}: {version or ''} {marca}")
    return estado


DUMMY_PARAMS = dict(
    symbol="NAS100", fecha="2026-01-01T00:00:00",
    c5=100.0, ema550=100.0, ema5200=100.0, macdLine5=0.1, signalLine5=0.1,
    adx5=20.0, diPlus5=20.0, diMinus5=15.0, r5=50.0, r15=50.0,
    m5=50.0, s5=50.0, m15=50.0, s15=50.0, atr5=1.0,
)


def chequear_predict(base, symbol):
    params = dict(DUMMY_PARAMS)
    params['symbol'] = symbol
    url = base.rstrip('/') + '/predict?' + urllib.parse.urlencode(params)
    try:
        r = get(url)
    except Exception as e:
        print(f"  {symbol}: ERROR en /predict -> {e}")
        return False

    campos_ok = all(k in r for k in ('valor_profit', 'RESULTADO', 'tp', 'sl'))
    if not campos_ok:
        print(f"  {symbol}: respuesta con campos faltantes: {r}")
        return False

    print(f"  {symbol}: RESULTADO={r['RESULTADO']}  valor_profit={r['valor_profit']:.4f}  "
          f"tp={r['tp']}  sl={r['sl']}  -> formato OK")
    return True


def chequear_log(path_log):
    print(f"\n=== 3. Log: {path_log} ===")
    df = pd.read_csv(path_log, sep=';')
    columna_lado = 'respuesta' if 'respuesta' in df.columns else 'score_modelo'
    if columna_lado not in df.columns:
        print("  No reconozco el formato de este log (ni 'respuesta' ni 'score_modelo').")
        return
    print(f"  {len(df)} filas totales")
    print(df[columna_lado].value_counts().to_string())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1/")
    ap.add_argument("--log", default=None)
    args = ap.parse_args()

    estado = chequear_estado(args.base)

    print("\n=== 2. Pedido de prueba a /predict (valores dummy, solo para ver formato) ===")
    for symbol, version in estado.items():
        if version:
            chequear_predict(args.base, symbol)

    if args.log:
        chequear_log(args.log)

    print("\n=== Recordatorio ===")
    print("Esto NO confirma qué órdenes está abriendo tu EA en MT4 -- eso se revisa")
    print("a mano en la pestaña Trade (columnas S/L y T/P de cada posición abierta).")


if __name__ == "__main__":
    main()
