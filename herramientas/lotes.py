r"""
lotes.py -- calcula el lote por simbolo, simple y sin sorpresas.

El "valor del punto" NO se recalcula: esta fijo abajo, con los valores que se
dedujeron de mas de 1000 operaciones cerradas (agrupando profit/puntos, que da
exactamente lote x valor_del_punto). Son constantes exactas del contrato, no
promedios, asi que no hace falta re-estimarlas y re-estimarlas con pocas
operaciones solo mete ruido (con 7 operaciones GER40 dio 192.99 en vez de 1.16,
porque una operacion con `puntos` cerca de cero rompe la division).

Lo unico que se estima aca es la distancia media del SL, usando TODO el
historial disponible de cada simbolo.

Uso:
    py lotes.py --balance 22067 --riesgo-pct 0.25
    py lotes.py --balance 22067 --riesgo-pct 0.1     (mas conservador)
"""
import argparse
import json
from pathlib import Path
from statistics import median

CIERRES = Path("datos/operaciones/cierres.jsonl")

# valor de 1 punto de precio, por lote completo, en USD.
# NAS100/US30/BTCUSD cotizan en USD -> 1.00
# GER40 cotiza en EUR -> 1.16 (el cambio EURUSD)
VALOR_PUNTO = {
    "NAS100": 1.00,
    "US30":   1.00,
    "GER40":  1.16,
    "BTCUSD": 1.00,
    "GBPUSD": 100000.0,   # 1 lote estandar = 100.000 unidades
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--balance", type=float, required=True)
    ap.add_argument("--riesgo-pct", type=float, default=0.25, dest="riesgo_pct")
    ap.add_argument("--ultimas", type=int, default=30,
                    help="usar solo las N operaciones mas recientes de cada simbolo. "
                         "El SL depende del k_sl del modelo activo, asi que el "
                         "historial viejo (modelos v1, con otros k_sl) da un SL que "
                         "ya no corresponde: en BTCUSD, todo el historial daba 59 "
                         "puntos cuando el SL real de hoy es ~240.")
    args = ap.parse_args()

    if not CIERRES.exists():
        raise SystemExit(f"No existe {CIERRES}")

    cierres = []
    for linea in open(CIERRES, encoding="utf-8"):
        try:
            cierres.append(json.loads(linea))
        except json.JSONDecodeError:
            continue

    riesgo = args.balance * args.riesgo_pct / 100.0
    print(f"Balance de referencia: {args.balance:,.2f} USD")
    print(f"Riesgo por operacion:  {args.riesgo_pct}%  =  {riesgo:,.2f} USD")
    print(f"SL estimado con las ultimas {args.ultimas} operaciones de cada simbolo\n")
    print(f"{'Simbolo':<10}{'n ops':>7}{'SL medio':>13}{'valor/punto':>13}"
          f"{'perdida x lote':>16}{'LOTE':>9}")
    print("-" * 68)

    tabla = {}
    for sym, vp in VALOR_PUNTO.items():
        sub = [c for c in cierres
               if c["symbol"].upper() == sym and c.get("sl", 0) > 0]
        sub.sort(key=lambda c: c.get("fecha_cierre", ""))
        sub = sub[-args.ultimas:]          # solo las mas recientes
        dists = [abs(c["precio_apertura"] - c["sl"]) for c in sub]
        if len(dists) < 10:
            print(f"{sym:<10}{len(dists):>7}   historial insuficiente (hacen falta 10)")
            continue

        sl = median(dists)
        perdida_lote = sl * vp
        lote = riesgo / perdida_lote
        lote = max(0.01, round(lote // 0.01 * 0.01, 2))
        tabla[sym] = lote

        print(f"{sym:<10}{len(dists):>7}{sl:>13.5f}{vp:>13.2f}"
              f"{perdida_lote:>16.2f}{lote:>9.2f}")

    if tabla:
        print("\n--- Para pegar en LoteDeEsteSimbolo() del EA ---")
        for sym, lote in tabla.items():
            esp = " " * max(1, 8 - len(sym))
            print(f'   if(StringFind(s, "{sym}"){esp}>= 0) return {lote:.2f};')

    print("\nEl SL medio es una MEDIANA: la mitad de las operaciones va a tener un SL")
    print("mas ancho que ese, y va a arriesgar mas que el objetivo. Es un riesgo")
    print("promedio, no un tope. Para poner un techo duro, usar el input LoteMaximo.")


if __name__ == "__main__":
    main()
