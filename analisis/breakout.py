r"""
breakout.py -- ruptura del rango de apertura en NAS100, con controles.

La idea: no predecir la direccion. Se marca el rango (maximo y minimo) de los
primeros minutos despues de la apertura y se opera hacia donde el precio rompa
ese rango. La direccion la confirma el propio precio.

Lo que YA sabemos y por eso este script trae controles:
  - Operar el movimiento sin apostar a la direccion se probo el 22-sep con 7
    configuraciones y 3 filtros: en NAS100 el mejor caso necesitaba que el
    precio se moviera 67.7% de las veces y se movio 69.8%. Al filo, y era el
    unico positivo entre 21 combinaciones.
  - El filtro de volatilidad, probado de tres formas distintas, mejoro en unos
    simbolos y empeoro en otros. En NAS100 compra EMPEORO 2.9 puntos.
Asi que aca no se da nada por sentado: todo se compara contra controles.

REGLA, fijada de antemano (3 variantes, ninguna mas):
    rango de los primeros 15, 30 o 60 minutos desde la apertura.
    Entrada: al romper el rango, en el precio del borde.
    Stop: el borde opuesto del rango.
    Objetivo: 2 veces la distancia al stop.
    Una sola operacion por dia. Si no se resuelve, se cierra al final del dia.

CONTROLES (esto es lo que decide si la regla sirve):
    direccion al azar : misma hora de entrada, mismo stop y objetivo, pero el
                        lado se sortea. Si el breakout no le gana a esto, la
                        ruptura no aporta nada.
    filtro al azar    : descarta la misma cantidad de dias que el filtro de
                        volatilidad, pero al azar. Si el filtro no le gana a
                        esto, el filtro no aporta nada.

El modelo de volatilidad se entrena SOLO con el primer 70% del historial.
Los resultados se informan por separado para todo el periodo y para el ultimo
30%, que el modelo no vio.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\breakout.py --csv datos\crudos\indicadores_NAS100_2026-09-23.CSV --costo 0.85
"""
import argparse

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

VENTANAS = [15, 30, 60]          # minutos de rango, fijadas de antemano
RR = 2.0                          # objetivo = 2 veces la distancia al stop
VARS_VOL = ["rsi5", "adx5", "atr_rel", "vol_rel", "hora_sin", "hora_cos",
            "rango_rel", "bb_ancho5"]


def cargar(ruta):
    df = pd.read_csv(ruta, sep=";")
    df.columns = [c.strip() for c in df.columns]
    df["fecha"] = pd.to_datetime(df["fecha"].astype(str).str.strip(),
                                 format="%Y.%m.%d %H:%M")
    df = df.sort_values("fecha").reset_index(drop=True)
    c = df["precioclose5"]
    df["atr_rel"] = df["atr5"] / c
    df["vol_rel"] = df["volume5"] / df["volume5"].rolling(20).mean()
    df["rango_rel"] = (df["preciohigh5"] - df["preciolow5"]) / df["atr5"]
    ancho = df["iBBs5"] - df["iBBi5"]
    df["bb_ancho5"] = ancho / c
    minutos = df["fecha"].dt.hour * 60 + df["fecha"].dt.minute
    df["hora_sin"] = np.sin(2 * np.pi * minutos / 1440)
    df["hora_cos"] = np.cos(2 * np.pi * minutos / 1440)
    df["dia"] = df["fecha"].dt.date
    return df


def detectar_apertura(df):
    """La apertura es la hora en que el ATR pega el salto mas grande."""
    med = df.groupby(df["fecha"].dt.hour)["atr5"].median()
    salto = med.diff()
    return int(salto.idxmax())


def modelo_volatilidad(df, corte):
    """Entrena con el primer 70% y devuelve la probabilidad para todas las filas."""
    s_hi, s_lo = df["preciohigh5"], df["preciolow5"]
    fut_max = s_hi.iloc[::-1].rolling(24).max().iloc[::-1].shift(-1)
    fut_min = s_lo.iloc[::-1].rolling(24).min().iloc[::-1].shift(-1)
    rec = (fut_max - fut_min).values
    y = np.where(~np.isnan(rec) & (df["atr5"].values > 0),
                 (rec >= 6 * df["atr5"].values).astype(float), np.nan)
    X = df[VARS_VOL].replace([np.inf, -np.inf], np.nan)
    ok_tr = (~np.isnan(y)) & (~X.isna().any(axis=1)).values & (df.index < corte)
    sc = StandardScaler().fit(X[ok_tr])
    mod = LogisticRegression(max_iter=2000).fit(sc.transform(X[ok_tr]), y[ok_tr])
    Xf = X.fillna(X.median())
    return mod.predict_proba(sc.transform(Xf))[:, 1]


def operaciones(df, apertura, minutos_rango):
    """Una fila por dia con los datos de la ruptura, si la hubo."""
    ops = []
    for dia, g in df.groupby("dia", sort=True):
        g = g.reset_index(drop=True)
        ini = g["fecha"].dt.hour * 60 + g["fecha"].dt.minute
        desde = apertura * 60
        vent = g[(ini >= desde) & (ini < desde + minutos_rango)]
        if len(vent) < max(2, minutos_rango // 10):
            continue
        alto, bajo = vent["preciohigh5"].max(), vent["preciolow5"].min()
        if not (alto > bajo):
            continue
        resto = g[ini >= desde + minutos_rango]
        if len(resto) < 6:
            continue
        # primera vela que rompe
        rompe = None
        for _, r in resto.iterrows():
            arriba = r["preciohigh5"] > alto
            abajo = r["preciolow5"] < bajo
            if arriba and abajo:
                break          # rompe los dos lados en la misma vela: ambiguo
            if arriba or abajo:
                rompe = (r, "BUY" if arriba else "SELL")
                break
        if rompe is None:
            continue
        fila, lado = rompe
        idx = resto.index[resto["fecha"] == fila["fecha"]][0]
        camino = resto.loc[idx + 1:]
        if len(camino) < 2:
            continue
        ops.append(dict(dia=dia, fecha=fila["fecha"], lado=lado,
                        entrada=alto if lado == "BUY" else bajo,
                        alto=alto, bajo=bajo,
                        p_vol=fila["p_vol"],
                        hi=camino["preciohigh5"].values,
                        lo=camino["preciolow5"].values,
                        cierre=camino["precioclose5"].values[-1]))
    return ops


def resolver(op, lado, costo):
    """Resultado en puntos. El stop es el borde opuesto; el objetivo, RR veces
    esa distancia. Si en la misma vela se tocan los dos, gana el stop."""
    e = op["entrada"]
    d = op["alto"] - op["bajo"]
    if lado == "BUY":
        sl, tp = e - d, e + RR * d
        for k in range(len(op["hi"])):
            if op["lo"][k] <= sl:
                return sl - e - costo
            if op["hi"][k] >= tp:
                return tp - e - costo
        return op["cierre"] - e - costo
    sl, tp = e + d, e - RR * d
    for k in range(len(op["hi"])):
        if op["hi"][k] >= sl:
            return e - sl - costo
        if op["lo"][k] <= tp:
            return e - tp - costo
    return e - op["cierre"] - costo


def resumen(res):
    r = np.array(res, dtype=float)
    if len(r) == 0:
        return None
    gan, per = r[r > 0].sum(), -r[r < 0].sum()
    return dict(n=len(r), wr=float((r > 0).mean()),
                pf=gan / per if per > 0 else float("inf"),
                total=float(r.sum()))


def linea(nombre, d):
    if d is None:
        return f"    {nombre:<34}{'sin operaciones':>34}"
    return (f"    {nombre:<34}{d['n']:>6}{d['wr']:>9.1%}{d['pf']:>9.3f}"
            f"{d['total']:>12,.0f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--costo", type=float, default=0.0)
    ap.add_argument("--apertura", type=int, default=None,
                    help="hora de apertura (servidor). Si se omite, se detecta")
    args = ap.parse_args()

    df = cargar(args.csv)
    corte = int(len(df) * 0.70)
    fecha_corte = df["fecha"].iloc[corte]
    df["p_vol"] = modelo_volatilidad(df, corte)
    apertura = args.apertura if args.apertura is not None else detectar_apertura(df)

    print(f"### Ruptura del rango de apertura — {args.csv.split(chr(92))[-1]} ###")
    print(f"{len(df)} velas  {df['fecha'].iloc[0]} -> {df['fecha'].iloc[-1]}")
    print(f"hora de apertura detectada: {apertura}h (servidor)")
    print(f"modelo de volatilidad entrenado hasta {fecha_corte}")
    print(f"objetivo = {RR} x la distancia al stop | costo {args.costo}\n")

    rng = np.random.default_rng(0)
    for mins in VENTANAS:
        ops = operaciones(df, apertura, mins)
        if len(ops) < 40:
            print(f"rango de {mins} min: solo {len(ops)} dias con ruptura, se omite\n")
            continue
        corte_vol = np.median([o["p_vol"] for o in ops])

        print("=" * 76)
        print(f"RANGO DE LOS PRIMEROS {mins} MINUTOS   ({len(ops)} dias con ruptura)")
        print("=" * 76)
        for etiqueta, sub in (("TODO EL PERIODO", ops),
                              ("SOLO EL ULTIMO 30% (no visto)",
                               [o for o in ops if o["fecha"] > fecha_corte])):
            if len(sub) < 20:
                continue
            print(f"\n  {etiqueta}")
            print(f"    {'':<34}{'n':>6}{'acierto':>9}{'PF':>9}{'total':>12}")
            base = [resolver(o, o["lado"], args.costo) for o in sub]
            print(linea("ruptura, sin filtro", resumen(base)))
            azar_dir = [resolver(o, rng.choice(["BUY", "SELL"]), args.costo)
                        for o in sub]
            print(linea("CONTROL: direccion al azar", resumen(azar_dir)))
            alto = [o for o in sub if o["p_vol"] >= corte_vol]
            print(linea("ruptura + filtro volatilidad",
                        resumen([resolver(o, o["lado"], args.costo) for o in alto])))
            idx = rng.choice(len(sub), len(alto), replace=False)
            print(linea("CONTROL: filtro al azar",
                        resumen([resolver(sub[i], sub[i]["lado"], args.costo)
                                 for i in idx])))
        print()

    print("Como leerlo:")
    print("  La ruptura sirve solo si le gana claramente al CONTROL de direccion")
    print("  al azar. Si empatan, el precio rompe para cualquier lado y la")
    print("  ruptura no informa nada.")
    print("  El filtro sirve solo si le gana al CONTROL de filtro al azar.")
    print("  Y el PF tiene que superar 1 en el ULTIMO 30%, no solo en todo el")
    print("  periodo: ese tramo es el unico que el modelo no vio.")


if __name__ == "__main__":
    main()
