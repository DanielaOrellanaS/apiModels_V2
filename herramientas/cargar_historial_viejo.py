r"""
cargar_historial_viejo.py — junta el historial viejo (CSV exportado a mano
desde EXPORTAR_HISTORIAL_NEO_MINIMAL.mq4) con el archivo que alimenta el
reporte en vivo (datos/operaciones/cierres.jsonl).

Se corre UNA sola vez, para no perder las operaciones que se cerraron antes
de que NEO_MINIMAL_V1 empezara a avisar solo. Es seguro correrlo más de una
vez -- si un ticket ya está cargado (viejo o nuevo, vía webhook), no se
duplica.

    py cargar_historial_viejo.py --csv datos\logs\historial_NEO_MINIMAL_2026-08-14.csv
"""
import argparse
import json
from pathlib import Path

import pandas as pd

CIERRES_PATH = Path("datos/operaciones/cierres.jsonl")


def tickets_existentes():
    if not CIERRES_PATH.exists():
        return set()
    vistos = set()
    with open(CIERRES_PATH, encoding="utf-8") as f:
        for linea in f:
            try:
                vistos.add(json.loads(linea)["ticket"])
            except (json.JSONDecodeError, KeyError):
                continue
    return vistos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="el historial_NEO_MINIMAL_*.csv exportado de MT4")
    args = ap.parse_args()

    df = pd.read_csv(args.csv, sep=';')
    ya_estan = tickets_existentes()
    print(f"Ya había {len(ya_estan)} operaciones en {CIERRES_PATH}")

    CIERRES_PATH.parent.mkdir(parents=True, exist_ok=True)
    agregadas = 0
    with open(CIERRES_PATH, "a", encoding="utf-8") as f:
        for _, fila in df.iterrows():
            ticket = int(fila["ticket"])
            if ticket in ya_estan:
                continue

            signo = 1 if str(fila["tipo"]).upper() == "BUY" else -1
            puntos = signo * (float(fila["precio_cierre"]) - float(fila["precio_apertura"]))

            registro = dict(
                ticket=ticket,
                symbol=str(fila["simbolo"]).upper(),
                tipo=str(fila["tipo"]).upper(),
                fecha_apertura=str(fila["fecha_apertura"]),
                precio_apertura=float(fila["precio_apertura"]),
                fecha_cierre=str(fila["fecha_cierre"]),
                precio_cierre=float(fila["precio_cierre"]),
                sl=float(fila["sl"]),
                tp=float(fila["tp"]),
                profit=float(fila["profit"]),
                puntos=puntos,
                registrado_en="migrado_del_historial_csv",
            )
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
            agregadas += 1
            ya_estan.add(ticket)

    print(f"Agregadas {agregadas} operaciones nuevas (las que ya estaban se saltaron, sin duplicar).")
    print(f"Total ahora en {CIERRES_PATH}: {len(ya_estan)}")
    print("\nAbrí http://127.0.0.1/reporte_winrate.html para ver todo junto.")


if __name__ == "__main__":
    main()
