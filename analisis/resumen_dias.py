r"""
resumen_dias.py -- desglose manual por par, dia por dia, desde cierres.jsonl.

Sirve para dos cosas:

  1) El detalle que se puede comparar a mano contra el historial de MT4:
     por simbolo, lado y dia -> cuantas operaciones, cuantas ganadas, winrate
     y resultado en dinero.

  2) Detectar si FALTAN operaciones. El total en dinero que imprime tiene que
     coincidir con el Profit/Loss que muestra MT4 para el mismo periodo,
     filtrando por el comentario NEO_MINIMAL. Si no coinciden, hay ordenes
     que el EA no llego a reportar al servidor.

Uso, desde F:\ApiModels\apiModels_V2:
    py analisis\resumen_dias.py --dias 2
    py analisis\resumen_dias.py --desde 2026-09-13
"""
import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CIERRES = Path("datos/operaciones/cierres.jsonl")
SIMBOLOS = ["NAS100", "US30", "GER40", "BTCUSD", "GBPUSD"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=2,
                    help="cuantos dias con datos mostrar, contando hacia atras")
    ap.add_argument("--desde", default=None, help="YYYY-MM-DD; pisa a --dias")
    args = ap.parse_args()

    if not CIERRES.exists():
        raise SystemExit(f"No existe {CIERRES}")

    todos = []
    for linea in open(CIERRES, encoding="utf-8"):
        try:
            todos.append(json.loads(linea))
        except json.JSONDecodeError:
            continue

    dias_disp = sorted({str(c.get("fecha_cierre", ""))[:10] for c in todos
                        if len(str(c.get("fecha_cierre", ""))[:10]) == 10})
    if args.desde:
        dias = [d for d in dias_disp if d >= args.desde]
    else:
        dias = dias_disp[-args.dias:]
    if not dias:
        raise SystemExit("No hay dias con datos en ese rango.")

    sub = [c for c in todos if str(c.get("fecha_cierre", ""))[:10] in dias]

    print("=" * 78)
    print(f"DESGLOSE POR PAR — dias: {', '.join(dias)}")
    print("=" * 78)

    # ---- detalle por simbolo / lado / dia ----
    celdas = defaultdict(list)
    for c in sub:
        lado = "Compra" if str(c.get("tipo", "")).lower().startswith("b") else "Venta"
        celdas[(c["symbol"].upper(), lado, str(c["fecha_cierre"])[:10])].append(c)

    total_general = 0.0
    total_ops = 0
    for sym in SIMBOLOS:
        filas = [(l, d) for (s, l, d) in celdas if s == sym]
        if not filas:
            print(f"\n{sym:<10} SIN OPERACIONES en este periodo")
            print(f"{'':<10} (revisar si PermitirBUY/PermitirSELL estan en false "
                  f"en el grafico)")
            continue

        print(f"\n{sym}")
        print(f"  {'lado':<8}{'dia':<12}{'ops':>5}{'gano':>6}{'perdio':>8}"
              f"{'winrate':>9}{'USD':>12}")
        sym_ops = sym_prof = 0
        sym_gan = 0
        for lado in ("Compra", "Venta"):
            lado_ops = lado_gan = 0
            lado_prof = 0.0
            for d in dias:
                ops = celdas.get((sym, lado, d), [])
                if not ops:
                    continue
                n = len(ops)
                g = sum(1 for o in ops if o.get("puntos", 0) > 0)
                p = sum(float(o.get("profit", 0) or 0) for o in ops)
                lado_ops += n; lado_gan += g; lado_prof += p
                print(f"  {lado:<8}{d:<12}{n:>5}{g:>6}{n-g:>8}"
                      f"{g/n:>8.0%}{p:>12,.2f}")
            if lado_ops:
                print(f"  {'':<8}{'SUBTOTAL':<12}{lado_ops:>5}{lado_gan:>6}"
                      f"{lado_ops-lado_gan:>8}{lado_gan/lado_ops:>8.0%}"
                      f"{lado_prof:>12,.2f}")
                sym_ops += lado_ops; sym_gan += lado_gan; sym_prof += lado_prof
        if sym_ops:
            print(f"  {'TOTAL ' + sym:<20}{sym_ops:>5}{sym_gan:>6}"
                  f"{sym_ops-sym_gan:>8}{sym_gan/sym_ops:>8.0%}{sym_prof:>12,.2f}")
            total_general += sym_prof
            total_ops += sym_ops

    # ---- control contra MT4 ----
    print("\n" + "=" * 78)
    print("CONTROL — comparar contra MT4")
    print("=" * 78)
    print(f"  Operaciones reportadas al servidor : {total_ops}")
    print(f"  Resultado total                    : {total_general:,.2f} USD")
    print()
    print("  En MT4: pestaña Account History, click derecho -> Custom Period,")
    print(f"  del {dias[0]} al {dias[-1]}. Sumar SOLO las lineas cuyo comentario")
    print("  empiece con NEO_MINIMAL (las demas son de la otra estrategia de la")
    print("  cuenta, con magic 22, 9696, 301 o 12345).")
    print()
    print("  Si el numero de MT4 NO coincide con el de arriba, hay ordenes que el")
    print("  EA cerro pero no llego a reportar. Eso hace que el reporte web")
    print("  muestre menos operaciones de las reales.")

    # ---- que simbolos no aparecen ----
    activos = {s for (s, _, _) in celdas}
    faltan = [s for s in SIMBOLOS if s not in activos]
    if faltan:
        print("\n" + "=" * 78)
        print("SIN DATOS EN ESTE PERIODO")
        print("=" * 78)
        for s in faltan:
            ult = [c for c in todos if c["symbol"].upper() == s]
            if ult:
                f = max(str(c.get("fecha_cierre", ""))[:10] for c in ult)
                print(f"  {s:<10} ultima operacion: {f}")
            else:
                print(f"  {s:<10} nunca opero")
        print()
        print("  Un simbolo sin datos NO es un error del reporte: puede estar")
        print("  pausado (PermitirBUY/PermitirSELL en false) o el EA no estar")
        print("  cargado en ese grafico. Verificar en MT4 antes de sacar")
        print("  conclusiones del reporte.")


if __name__ == "__main__":
    main()
