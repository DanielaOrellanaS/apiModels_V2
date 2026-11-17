r"""
filtro_volatilidad.py -- ¿los datos sirven para ALGO?

Contexto: predecir DIRECCION con estas variables fallo en los 5 simbolos.
Cuatro versiones del modelo, AUC entre 0.49 y 0.55 (0.50 = moneda al aire).

Este script cambia la pregunta. En vez de "¿hacia donde va el precio?",
pregunta "¿cuanto se va a mover?". La volatilidad se agrupa (los ratos
movidos vienen seguidos de ratos movidos), asi que es mucho mas predecible
que la direccion. El volumen y la hora del dia, que no explicaron nada de la
direccion, son justamente variables de actividad.

Dos partes:

  [A] ¿Se puede predecir la volatilidad?
      Etiqueta: en las proximas H velas, ¿el precio recorrio mas de k veces
      el ATR actual? Se entrena sobre TRAIN y se mide el AUC en HOLDOUT.

      Este es el resultado clave del script. Si da 0.65 o mas, las variables
      SI tienen informacion -- solo que no sobre la direccion. Si da 0.52,
      las variables no tienen informacion de ningun tipo, y ahi se termina
      el camino de verdad.

  [B] ¿Sirve como filtro?
      Se toma el modelo direccional que ya existe y se mira su winrate SOLO
      en las velas donde este modelo predice movimiento alto, contra su
      winrate en todas. Si sube, el filtro aporta.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\filtro_volatilidad.py --symbol NAS100 --version v6_20260914 ^
        --train datos\crudos\NAS100_TRAIN_2025-10-09_al_2026-06-03_M5.csv ^
        --holdout datos\crudos\NAS100_HOLDOUT_B_CONFIRM_2026-07-24_al_2026-09-13_M5.csv
"""
import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import (cargar_csv_exportado, construir_features, etiquetar_tp_sl,
                  FEATURE_LIST)
from registry import Registry


def etiqueta_volatilidad(high, low, atr, horizonte, k):
    """1 si en las proximas `horizonte` velas el recorrido (maximo menos
    minimo) supera k veces el ATR actual. Las ultimas filas quedan en -1
    porque no tienen futuro completo."""
    s_hi = pd.Series(high)
    s_lo = pd.Series(low)
    # maximo y minimo del tramo [t+1, t+horizonte]
    fut_max = s_hi.iloc[::-1].rolling(horizonte).max().iloc[::-1].shift(-1)
    fut_min = s_lo.iloc[::-1].rolling(horizonte).min().iloc[::-1].shift(-1)
    recorrido = (fut_max - fut_min).values
    y = np.full(len(high), -1, dtype=np.int8)
    ok = ~np.isnan(recorrido) & (atr > 0)
    y[ok] = (recorrido[ok] >= k * atr[ok]).astype(np.int8)
    return y, recorrido


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--version", required=True,
                    help="modelo direccional ya entrenado, para la parte [B]")
    ap.add_argument("--train", required=True)
    ap.add_argument("--holdout", required=True)
    ap.add_argument("--horizonte-vol", type=int, default=24, dest="hvol",
                    help="velas hacia adelante para medir el recorrido (24 = 2 horas)")
    ap.add_argument("--k", type=float, default=2.0,
                    help="cuantos ATR tiene que recorrer para contar como 'movido'")
    ap.add_argument("--horizonte", type=int, default=288,
                    help="horizonte del modelo direccional, para la parte [B]")
    args = ap.parse_args()

    symbol = args.symbol.upper()
    print(f"### {symbol} — ¿los datos predicen volatilidad? ###\n")

    feat_tr = construir_features(cargar_csv_exportado(args.train))
    feat_ho = construir_features(cargar_csv_exportado(args.holdout))
    print(f"TRAIN   {len(feat_tr)} barras  {feat_tr['fecha'].min()} -> {feat_tr['fecha'].max()}")
    print(f"HOLDOUT {len(feat_ho)} barras  {feat_ho['fecha'].min()} -> {feat_ho['fecha'].max()}")

    # ================= [A] =================
    print("\n" + "=" * 70)
    print(f"[A] Predecir volatilidad: ¿recorre mas de {args.k} ATR en las "
          f"proximas {args.hvol} velas?")
    print("=" * 70)

    y_tr, _ = etiqueta_volatilidad(feat_tr['high'].values, feat_tr['low'].values,
                                   feat_tr['atr5'].values, args.hvol, args.k)
    y_ho, _ = etiqueta_volatilidad(feat_ho['high'].values, feat_ho['low'].values,
                                   feat_ho['atr5'].values, args.hvol, args.k)
    m_tr, m_ho = y_tr != -1, y_ho != -1

    X_tr = feat_tr[FEATURE_LIST].values[m_tr]
    X_ho = feat_ho[FEATURE_LIST].values[m_ho]
    yt, yh = y_tr[m_tr], y_ho[m_ho]

    print(f"  velas movidas en TRAIN:   {yt.mean():.1%}")
    print(f"  velas movidas en HOLDOUT: {yh.mean():.1%}")
    if yt.mean() < 0.05 or yt.mean() > 0.95:
        print("\n  El umbral k deja casi todo de un lado. Probar otro --k.")
        return

    scaler = StandardScaler().fit(X_tr)
    modelo = LogisticRegression(max_iter=1000).fit(scaler.transform(X_tr), yt)
    p_ho = modelo.predict_proba(scaler.transform(X_ho))[:, 1]
    auc = roc_auc_score(yh, p_ho)

    print(f"\n  AUC en HOLDOUT: {auc:.3f}")
    print(f"  (referencia: 0.50 = moneda al aire | la DIRECCION dio 0.49-0.55)")
    if auc >= 0.65:
        print("  -> LAS VARIABLES SI TIENEN INFORMACION. No sobre la direccion,")
        print("     pero si sobre cuanto se va a mover. Vale seguir por aca.")
    elif auc >= 0.58:
        print("  -> Hay algo, pero moderado. Mirar la parte [B] antes de decidir.")
    else:
        print("  -> Las variables NO tienen informacion util de ningun tipo.")
        print("     Ni direccion ni volatilidad. Ahi se termina este camino.")

    # peso de cada variable, para ver cuales mandan
    pesos = sorted(zip(FEATURE_LIST, modelo.coef_[0]),
                   key=lambda x: -abs(x[1]))[:6]
    print("\n  Variables que mas pesan:")
    for n, c in pesos:
        print(f"    {n:<16}{c:>+8.3f}")

    # ================= [B] =================
    print("\n" + "=" * 70)
    print("[B] ¿Sirve como filtro para el modelo direccional?")
    print("=" * 70)

    reg = Registry()
    entrada = reg._buscar(symbol, args.version)
    if entrada is None:
        print(f"  No existe {symbol}/{args.version} en registry.json. Se omite.")
        return
    paquete = joblib.load(entrada["archivo_modelo"])

    high, low = feat_ho['high'].values, feat_ho['low'].values
    close, atr = feat_ho['close'].values, feat_ho['atr5'].values
    idx_ho = np.where(m_ho)[0]

    for lado_key, m in paquete.items():
        lado = "BUY" if lado_key == "buy" else "SELL"
        k_tp, k_sl, umbral = m["k_tp"], m["k_sl"], m["umbral"]
        tp_arr, sl_arr = k_tp * atr, k_sl * atr
        labels, _ = etiquetar_tp_sl(high, low, close, tp_arr, sl_arr,
                                    args.horizonte, lado)
        probs_dir = m["modelo"].predict_proba(
            m["scaler"].transform(feat_ho[FEATURE_LIST].values))[:, 1]
        opera = (labels != -1) & (probs_dir >= umbral)

        # probabilidad de volatilidad alineada con todas las filas
        p_vol = np.full(len(feat_ho), np.nan)
        p_vol[idx_ho] = p_ho

        print(f"\n  --- {lado} (k_tp={k_tp} k_sl={k_sl} umbral={umbral}) ---")
        if opera.sum() < 50:
            print(f"      solo {int(opera.sum())} operaciones, muestra insuficiente")
            continue
        base_wr = labels[opera].mean()
        print(f"      {'filtro':<28}{'n':>7}{'winrate':>10}{'cambio':>10}")
        print(f"      {'sin filtro':<28}{int(opera.sum()):>7}{base_wr:>10.1%}"
              f"{'—':>10}")
        for pct in (50, 70, 90):
            corte = np.nanpercentile(p_vol[opera], pct)
            sel = opera & (p_vol >= corte)
            if sel.sum() < 30:
                continue
            wr = labels[sel].mean()
            print(f"      {f'solo el {100-pct}% mas movido':<28}{int(sel.sum()):>7}"
                  f"{wr:>10.1%}{wr - base_wr:>+10.1%}")

    print("\n" + "=" * 70)
    print("Como leerlo:")
    print("  [A] es lo que decide. Si el AUC de volatilidad es tan bajo como el")
    print("      de direccion, las variables no sirven para nada y no hay mas")
    print("      que probar con estos datos.")
    print("  [B] solo tiene sentido si [A] dio bien. Un filtro que mejora el")
    print("      winrate 5 puntos puede dar vuelta la rentabilidad.")


if __name__ == "__main__":
    main()
