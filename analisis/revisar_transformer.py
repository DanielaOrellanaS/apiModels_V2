r"""
revisar_transformer.py -- revisar el CSV del sistema anterior ANTES de usarlo.

Motivo: el archivo transformer trae 46 columnas y un año entero de historial,
bastante mas que las 21 variables y los 8 meses que usamos hoy. Puede aportar.
Pero ya nos paso dos veces que un dato traia informacion del futuro sin que se
notara, asi que no se entrena con el hasta revisarlo.

Que revisa:

  [A] Coherencia del OHLC. El maximo tiene que ser >= al minimo, y ambos
      tienen que contener al abierto y al cierre. Nuestro propio exportador
      tenia un error de copiado aca (guardaba el abierto en el maximo y el
      cierre en el minimo), asi que hay que confirmarlo.

  [B] Fuga de futuro en las columnas de 15 minutos. Se reconstruyen las velas
      de 15 minutos a partir de los cierres de 5 minutos del mismo archivo, se
      calcula el indicador dos veces (con la vela de 15 en curso y con la
      anterior ya cerrada) y se ve a cual se parece el valor guardado.
      Si se parece al de la vela en curso, tiene futuro adentro.

  [C] Detector general de fuga. Para cada columna numerica mide la correlacion
      con el movimiento FUTURO del precio. Ninguna variable honesta deberia
      correlacionar fuerte con algo que todavia no paso. Es la prueba que
      habria detectado el problema de las tres variables de 15 minutos, y la
      que detecta de una el archivo TX.

  [D] Cobertura: cuanto historial hay y si faltan velas.

Uso:
    py analisis\revisar_transformer.py --csv transformer_GER40_2026-09-23.CSV
    py analisis\revisar_transformer.py --csv TX_GER40_2026-09-23.CSV
"""
import argparse

import numpy as np
import pandas as pd


def cargar(ruta):
    df = pd.read_csv(ruta, sep=";")
    df.columns = [c.strip() for c in df.columns]
    df["fecha"] = pd.to_datetime(df["fecha"].astype(str).str.strip(),
                                 format="%Y.%m.%d %H:%M")
    return df.sort_values("fecha").reset_index(drop=True)


def rsi(serie, periodo=5):
    d = serie.diff()
    sube = d.clip(lower=0).ewm(alpha=1 / periodo, adjust=False).mean()
    baja = (-d.clip(upper=0)).ewm(alpha=1 / periodo, adjust=False).mean()
    return 100 - 100 / (1 + sube / baja.replace(0, np.nan))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--velas-futuro", type=int, default=12, dest="fut",
                    help="cuantas velas hacia adelante mira el detector [C]")
    args = ap.parse_args()

    df = cargar(args.csv)
    print(f"### {args.csv} ###")
    print(f"{len(df)} filas, {len(df.columns)} columnas")
    print(f"desde {df['fecha'].min()}  hasta {df['fecha'].max()}\n")

    # ---------------- [A] ----------------
    print("=" * 74)
    print("[A] Coherencia del OHLC")
    print("=" * 74)
    grupos = [("5 minutos", "precioopen5", "precioclose5", "preciohigh5", "preciolow5"),
              ("15 minutos", "precioopen15", "precioclose15", "preciohigh15", "preciolow15")]
    hay_ohlc = False
    for nombre, o, c, h, l in grupos:
        if not all(col in df.columns for col in (o, c, h, l)):
            continue
        hay_ohlc = True
        mal_hl = (df[h] < df[l]).mean()
        contiene = ((df[h] >= df[[o, c]].max(axis=1) - 1e-9) &
                    (df[l] <= df[[o, c]].min(axis=1) + 1e-9)).mean()
        igual_oc = ((df[h] == df[o]) & (df[l] == df[c])).mean()
        print(f"  {nombre}:")
        print(f"    maximo menor que el minimo : {mal_hl:.1%} de las filas")
        print(f"    max/min contienen a open/close: {contiene:.1%}")
        print(f"    max==open Y min==close       : {igual_oc:.1%}")
        if igual_oc > 0.5:
            print("    -> ERROR: el maximo guarda el ABIERTO y el minimo el CIERRE.")
            print("       Es el mismo error de copiado que tenia nuestro exportador.")
            print("       Estas cuatro columnas no sirven como estan.")
        elif contiene > 0.99:
            print("    -> OK")
    if not hay_ohlc:
        print("  (el archivo no trae columnas de OHLC)")

    # ---------------- [B] ----------------
    print("\n" + "=" * 74)
    print("[B] ¿Las columnas de 15 minutos traen futuro?")
    print("=" * 74)
    if "precioclose5" not in df.columns or "rsi15" not in df.columns:
        print("  (faltan columnas para hacer esta prueba)")
    else:
        d = df.set_index("fecha")
        ventana = d.index.floor("15min")
        # cierre de cada vela de 15 = cierre del ultimo M5 de esa ventana
        cierre15 = d["precioclose5"].groupby(ventana).last()
        r_cerrada = rsi(cierre15, 5)             # valor al cerrar esa ventana
        en_curso = r_cerrada.reindex(ventana).values      # la ventana actual
        anterior = r_cerrada.shift(1).reindex(ventana).values  # la ya cerrada
        guardado = d["rsi15"].values
        ok = ~np.isnan(en_curso) & ~np.isnan(anterior) & ~np.isnan(guardado)
        e1 = np.abs(guardado[ok] - en_curso[ok]).mean()
        e2 = np.abs(guardado[ok] - anterior[ok]).mean()
        print(f"  diferencia media contra la vela de 15 EN CURSO : {e1:.3f}")
        print(f"  diferencia media contra la vela ANTERIOR cerrada: {e2:.3f}")
        if e1 < e2:
            print("  -> Se parece a la vela EN CURSO: TRAE FUTURO.")
            print("     Es el mismo problema que ya encontramos en nuestros datos.")
            print("     Estas columnas no se pueden usar tal cual.")
        else:
            print("  -> Se parece a la vela ya cerrada: sin futuro aparente.")

    # ---------------- [C] ----------------
    print("\n" + "=" * 74)
    print(f"[C] Detector general: correlacion con el movimiento de las proximas "
          f"{args.fut} velas")
    print("=" * 74)
    base = "precioclose5" if "precioclose5" in df.columns else (
        "pr1" if "pr1" in df.columns else None)
    if base is None:
        print("  (no hay columna de precio para calcular el movimiento futuro)")
    else:
        fut = df[base].shift(-args.fut) - df[base]
        filas = []
        for col in df.columns:
            if col in ("fecha", "simbolo", "timeframe"):
                continue
            s = pd.to_numeric(df[col], errors="coerce")
            if s.isna().all():
                continue
            if s.nunique(dropna=True) < 3:
                continue
            c = s.corr(fut)
            if not np.isnan(c):
                filas.append((col, c))
        filas.sort(key=lambda x: -abs(x[1]))
        print(f"  {'columna':<22}{'correlacion':>13}")
        for col, c in filas[:12]:
            aviso = ""
            if abs(c) > 0.30:
                aviso = "   <-- FUGA CLARA"
            elif abs(c) > 0.15:
                aviso = "   <-- sospechosa"
            print(f"  {col:<22}{c:>13.3f}{aviso}")
        peor = abs(filas[0][1]) if filas else 0
        print()
        if peor > 0.30:
            print("  -> Hay al menos una columna que sabe lo que va a pasar. No se")
            print("     puede entrenar con este archivo sin sacarlas.")
        elif peor > 0.15:
            print("  -> Hay columnas sospechosas. Revisar una por una antes de usar.")
        else:
            print("  -> Ninguna columna correlaciona fuerte con el futuro.")
            print("     (no garantiza que no haya fuga, pero descarta la mas evidente)")

    # ---------------- [D] ----------------
    print("\n" + "=" * 74)
    print("[D] Cobertura del historial")
    print("=" * 74)
    dias = df["fecha"].dt.date.nunique()
    print(f"  {len(df)} filas en {dias} dias distintos")
    print(f"  fechas repetidas: {len(df) - df['fecha'].nunique()}")
    if len(df) > 1:
        huecos = df["fecha"].diff().dt.total_seconds().div(60)
        print(f"  separacion mas comun entre filas: "
              f"{huecos.mode().iloc[0]:.0f} minutos")
        print(f"  huecos de mas de 1 dia: {(huecos > 1440).sum()}")


if __name__ == "__main__":
    main()
