r"""
analizar_horario.py — ¿las pérdidas de un símbolo/lado se concentran en
algún horario en particular? Lee datos/operaciones/cierres.jsonl directo
(la fuente en tiempo real, no hace falta exportar nada de MT4).

    py analizar_horario.py --symbol NAS100 --tipo SELL
    py analizar_horario.py --symbol US30 --tipo SELL
"""
import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

CIERRES_PATH = Path("datos/operaciones/cierres.jsonl")


def parsear_fecha(s):
    try:
        return datetime.strptime(s.split("+")[0], "%Y-%m-%dT%H:%M:%S")
    except (ValueError, AttributeError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--tipo", required=True, choices=["BUY", "SELL"])
    args = ap.parse_args()

    if not CIERRES_PATH.exists():
        raise SystemExit(f"No existe {CIERRES_PATH}")

    filas = []
    with open(CIERRES_PATH, encoding="utf-8") as f:
        for linea in f:
            try:
                r = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if r["symbol"].upper() == args.symbol.upper() and r["tipo"].upper() == args.tipo.upper():
                filas.append(r)

    print(f"=== {args.symbol} {args.tipo} — {len(filas)} operaciones totales en cierres.jsonl ===\n")
    if not filas:
        print("Sin datos para este símbolo/lado.")
        return

    # por hora del dia (UTC, la misma que manda MT4 en fecha_apertura)
    por_hora = defaultdict(lambda: [0, 0])  # hora -> [ganadas, perdidas]
    por_dia_semana = defaultdict(lambda: [0, 0])  # 0=lunes .. 6=domingo
    dias_semana_nombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    for r in filas:
        fecha = parsear_fecha(r.get("fecha_apertura"))
        if fecha is None:
            continue
        gano = r["puntos"] > 0
        por_hora[fecha.hour][0 if gano else 1] += 1
        por_dia_semana[fecha.weekday()][0 if gano else 1] += 1

    print(f"{'Hora (UTC)':<12}{'Ganadas':<10}{'Perdidas':<10}{'Winrate':<10}{'Total'}")
    print("-" * 52)
    for h in range(24):
        g, p = por_hora[h]
        total = g + p
        if total == 0:
            continue
        wr = g / total * 100
        marca = "  <-- revisar" if wr < 25 and total >= 5 else ""
        print(f"{h:02d}:00-{h:02d}:59  {g:<10}{p:<10}{wr:<9.1f}%{total}{marca}")

    print(f"\n{'Día':<12}{'Ganadas':<10}{'Perdidas':<10}{'Winrate':<10}{'Total'}")
    print("-" * 52)
    for d in range(7):
        g, p = por_dia_semana[d]
        total = g + p
        if total == 0:
            continue
        wr = g / total * 100
        marca = "  <-- revisar" if wr < 25 and total >= 5 else ""
        print(f"{dias_semana_nombre[d]:<12}{g:<10}{p:<10}{wr:<9.1f}%{total}{marca}")

    print("\nSi alguna franja horaria concentra la mayoría de las pérdidas (marcada con "
          "'<-- revisar'), es una pista real -- puede ser spread ancho en horario de baja "
          "liquidez, igual que ya encontramos antes con NAS100 compra.")

    # tendencia en el tiempo: primera mitad vs segunda mitad del periodo, por fecha real
    con_fecha = [(parsear_fecha(r.get("fecha_apertura")), r["puntos"] > 0) for r in filas]
    con_fecha = [(f, g) for f, g in con_fecha if f is not None]
    con_fecha.sort(key=lambda x: x[0])
    if len(con_fecha) >= 20:
        mitad = len(con_fecha) // 2
        primera, segunda = con_fecha[:mitad], con_fecha[mitad:]
        wr1 = sum(g for _, g in primera) / len(primera) * 100
        wr2 = sum(g for _, g in segunda) / len(segunda) * 100
        print(f"\n=== TENDENCIA EN EL TIEMPO ===")
        print(f"Primera mitad  ({primera[0][0].date()} a {primera[-1][0].date()}): "
              f"winrate {wr1:.1f}%  (n={len(primera)})")
        print(f"Segunda mitad  ({segunda[0][0].date()} a {segunda[-1][0].date()}): "
              f"winrate {wr2:.1f}%  (n={len(segunda)})")
        if wr2 < wr1 - 10:
            print("-> Empeorando con el tiempo: más compatible con que el mercado reciente "
                  "se comporta distinto al período validado, que con un bug de siempre.")
        elif wr1 < wr2 - 10:
            print("-> Mejorando con el tiempo: podría estar normalizándose solo.")
        else:
            print("-> Estable en las dos mitades: no es que haya empeorado recién -- viene "
                  "mal desde el principio, más compatible con algo estructural que con un "
                  "cambio reciente del mercado.")


if __name__ == "__main__":
    main()
