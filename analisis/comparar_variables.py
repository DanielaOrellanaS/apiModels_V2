r"""
comparar_variables.py -- ¿las columnas nuevas aportan algo?

El archivo indicadores_*.CSV (corregido) trae columnas que hoy no usamos:
Bollinger de 5 y 15 minutos, las medias, MACD y ADX de 15 minutos, el ATR de
15, el volumen de 15 y el valor previo de varios indicadores. Ademas trae un
año completo en vez de 8 meses.

Antes de modificar el EA para que mande todo eso en vivo, hay que saber si
sirve. Este script entrena dos modelos sobre EXACTAMENTE los mismos datos y
la misma etiqueta, cambiando solo las variables:

    BASE      las 21 que usamos hoy
    AMPLIADO  las 21 mas las nuevas

y compara el AUC sobre un tramo final que ningun modelo vio.

El AUC es lo que decide. Hoy la direccion da entre 0.49 y 0.55, que es la zona
del azar. Si el ampliado no llega a 0.58, las columnas nuevas no aportan y no
tiene sentido tocar el EA.

Se reparte 70% entrenamiento / 15% ajuste / 15% prueba final, en orden
cronologico. Objetivo 2 ATR y stop 1 ATR, fijos, sin barrido de combinaciones.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\comparar_variables.py --csv datos\crudos\indicadores_NAS100_2026-09-23.CSV
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import etiquetar_tp_sl

K_TP, K_SL = 2.0, 1.0

BASE = ['rel_ema50', 'rel_ema200', 'rel_ema50_200', 'atr_rel',
        'rsi5', 'rsi15', 'stoch_m5', 'stoch_s5', 'stoch_m15', 'stoch_s15',
        'adx5', 'di_diff5', 'macd_rel', 'macdsig_rel', 'macd_hist_rel',
        'vol_rel', 'rango_rel', 'cierre_pos', 'ret1', 'hora_sin', 'hora_cos']

NUEVAS = ['bb_pos5', 'bb_ancho5', 'bb_pos15', 'bb_ancho15',
          'rel_ema50_15', 'rel_ema200_15', 'rel_ema50_200_15',
          'macd_rel15', 'macd_hist_rel15', 'adx15', 'di_diff15',
          'atr_rel15', 'vol_rel15', 'rango_rel15', 'cierre_pos15',
          'pend_ema50', 'pend_macd_hist']


def cargar(ruta):
    df = pd.read_csv(ruta, sep=";")
    df.columns = [c.strip() for c in df.columns]
    df["fecha"] = pd.to_datetime(df["fecha"].astype(str).str.strip(),
                                 format="%Y.%m.%d %H:%M")
    return df.sort_values("fecha").reset_index(drop=True)


def construir(df):
    c = df["precioclose5"]
    f = pd.DataFrame(index=df.index)
    f["fecha"] = df["fecha"]
    f["high"] = df["preciohigh5"]
    f["low"] = df["preciolow5"]
    f["close"] = c
    f["atr5"] = df["atr5"]

    # ---- las 21 de hoy ----
    f["rel_ema50"] = df["ema550"] / c - 1
    f["rel_ema200"] = df["ema5200"] / c - 1
    f["rel_ema50_200"] = df["ema550"] / df["ema5200"] - 1
    f["atr_rel"] = df["atr5"] / c
    f["rsi5"] = df["rsi5"]
    f["rsi15"] = df["rsi15"]
    f["stoch_m5"] = df["iStochaMain5"]
    f["stoch_s5"] = df["iStochaSign5"]
    f["stoch_m15"] = df["iStochaMain15"]
    f["stoch_s15"] = df["iStochaSign15"]
    f["adx5"] = df["adx5"]
    f["di_diff5"] = df["diPlus5"] - df["diMinus5"]
    f["macd_rel"] = df["macdLine5"] / c
    f["macdsig_rel"] = df["signalLine5"] / c
    f["macd_hist_rel"] = (df["macdLine5"] - df["signalLine5"]) / c
    # el volumen crudo no es comparable entre epocas: se usa contra su promedio
    f["vol_rel"] = df["volume5"] / df["volume5"].rolling(20).mean()
    rango = df["preciohigh5"] - df["preciolow5"]
    f["rango_rel"] = rango / df["atr5"]
    f["cierre_pos"] = np.where(rango > 0, (c - df["preciolow5"]) / rango, 0.5)
    f["ret1"] = c / c.shift(1) - 1
    minutos = df["fecha"].dt.hour * 60 + df["fecha"].dt.minute
    f["hora_sin"] = np.sin(2 * np.pi * minutos / 1440)
    f["hora_cos"] = np.cos(2 * np.pi * minutos / 1440)

    # ---- las nuevas ----
    anchoB5 = df["iBBs5"] - df["iBBi5"]
    f["bb_pos5"] = np.where(anchoB5 > 0, (c - df["iBBi5"]) / anchoB5, 0.5)
    f["bb_ancho5"] = anchoB5 / c
    anchoB15 = df["iBBs15"] - df["iBBi15"]
    f["bb_pos15"] = np.where(anchoB15 > 0, (c - df["iBBi15"]) / anchoB15, 0.5)
    f["bb_ancho15"] = anchoB15 / c
    f["rel_ema50_15"] = df["ema5015"] / c - 1
    f["rel_ema200_15"] = df["ema20015"] / c - 1
    f["rel_ema50_200_15"] = df["ema5015"] / df["ema20015"] - 1
    f["macd_rel15"] = df["macdLine15"] / c
    f["macd_hist_rel15"] = (df["macdLine15"] - df["signalLine15"]) / c
    f["adx15"] = df["adx15"]
    f["di_diff15"] = df["diPlus15"] - df["diMinus15"]
    f["atr_rel15"] = df["atr15"] / c
    f["vol_rel15"] = df["volume15"] / df["volume15"].rolling(20).mean()
    rango15 = df["preciohigh15"] - df["preciolow15"]
    f["rango_rel15"] = np.where(df["atr15"] > 0, rango15 / df["atr15"], 0)
    f["cierre_pos15"] = np.where(rango15 > 0,
                                 (df["precioclose15"] - df["preciolow15"]) / rango15, 0.5)
    # pendiente: cuanto se movio el indicador respecto de la vela anterior
    f["pend_ema50"] = df["ema550"] / df["ema50_prev"] - 1
    hist = df["macdLine5"] - df["signalLine5"]
    hist_prev = df["macdLine_prev5"] - df["signalLine_prev5"]
    f["pend_macd_hist"] = (hist - hist_prev) / c
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--horizonte", type=int, default=288)
    args = ap.parse_args()

    df = cargar(args.csv)
    f = construir(df)
    f = f.replace([np.inf, -np.inf], np.nan)
    todas = BASE + NUEVAS
    f = f.dropna(subset=todas).reset_index(drop=True)

    n = len(f)
    i1, i2 = int(n * 0.70), int(n * 0.85)
    print(f"### {Path(args.csv).name} ###")
    print(f"{n} velas utiles   {f['fecha'].iloc[0]} -> {f['fecha'].iloc[-1]}")
    print(f"  entrenamiento : {i1} velas, hasta {f['fecha'].iloc[i1-1]}")
    print(f"  ajuste        : {i2-i1} velas, hasta {f['fecha'].iloc[i2-1]}")
    print(f"  prueba final  : {n-i2} velas (nunca vistas)")
    print(f"objetivo {K_TP} ATR, stop {K_SL} ATR\n")

    high, low = f["high"].values, f["low"].values
    close, atr = f["close"].values, f["atr5"].values

    for lado in ("BUY", "SELL"):
        labels, _ = etiquetar_tp_sl(high, low, close, K_TP * atr, K_SL * atr,
                                    args.horizonte, lado)
        print("=" * 66)
        print(f"{'COMPRA' if lado == 'BUY' else 'VENTA'}")
        print("=" * 66)
        res = {}
        for nombre, cols in (("BASE (21 de hoy)", BASE),
                             ("AMPLIADO (21 + 17)", BASE + NUEVAS)):
            tr = slice(0, i1)
            ho = slice(i2, n)
            ytr, yho = labels[tr], labels[ho]
            mtr, mho = ytr != -1, yho != -1
            if mtr.sum() < 500 or mho.sum() < 200:
                print("  datos insuficientes")
                break
            Xtr = f[cols].values[tr][mtr]
            Xho = f[cols].values[ho][mho]
            sc = StandardScaler().fit(Xtr)
            mod = LogisticRegression(max_iter=2000).fit(sc.transform(Xtr), ytr[mtr])
            p = mod.predict_proba(sc.transform(Xho))[:, 1]
            auc = roc_auc_score(yho[mho], p)
            res[nombre] = auc
            print(f"  {nombre:<22} AUC = {auc:.3f}   "
                  f"({len(cols)} variables, {int(mtr.sum())} velas de entrenamiento)")
        if len(res) == 2:
            a, b = res["BASE (21 de hoy)"], res["AMPLIADO (21 + 17)"]
            print(f"\n  diferencia: {b - a:+.3f}")
            if b >= 0.58:
                print("  -> El ampliado llega a 0.58. Vale modificar el EA para que")
                print("     mande las columnas nuevas.")
            elif b - a > 0.02:
                print("  -> Mejora algo, pero sigue lejos de 0.58. No alcanza para")
                print("     justificar el cambio en el EA.")
            else:
                print("  -> Las columnas nuevas NO aportan. Mismo resultado que hoy.")
        print()

    print("Recordatorio: 0.50 es tirar una moneda. Con el año entero y las")
    print("columnas limpias, este es el mejor dato que se puede obtener con")
    print("indicadores tecnicos sobre velas de 5 minutos.")


if __name__ == "__main__":
    main()
