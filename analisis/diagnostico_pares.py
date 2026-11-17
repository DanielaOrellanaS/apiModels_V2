"""
diagnostico_pares.py -- por que un par no esta abriendo operaciones.

Lee lo que el SERVIDOR ya guarda, sin tocar MT4:
  predicciones.jsonl        cada consulta que un EA le hizo a /predict (tambien las NADA).
                            Los pares que van por /prueba/ (NAS100, BTCUSD) quedan aca tambien.
  selectivo_cierres.jsonl   cada cierre que NEO_SELECTIVO v2.2 reporto (lo que alimenta la pestana).

COMO LEERLO. El EA (NEO_SELECTIVO v2.2, OnTick) hace los chequeos en este orden:
  1. hay una orden abierta de este EA en este simbolo  -> NO consulta la API
  2. hora muerta (solo 4-7 horas sueltas por dia)      -> NO consulta la API
  3. AutoTrading apagado                               -> NO consulta la API
  4. consulta la API                                   -> queda un registro en predicciones.jsonl
  5. tabla de lados -> OrderSend (SL y TP van dentro del OrderSend; no hay OrderModify)
Entonces:
  "DEJO DE CONSULTAR"  = pasa algo ANTES de la API (orden abierta, EA descargado, AutoTrading,
                         MT4 apagado, o el servidor no tiene modelo activo para ese par).
  "consulta y no opera" = el problema esta DESPUES de la API (tabla de lados, OrderSend, reporte).

LIMITE: el archivo no dice QUE EA consulto. Si otro EA (NEO_MINIMAL, prueba, otra cuenta) consulta
el mismo par al mismo servidor, sus consultas cuentan como si fueran del selectivo.

Uso (desde la carpeta del proyecto):
    py analisis\\diagnostico_pares.py --pred datos\\operaciones\\predicciones.jsonl ^
        --cierres datos\\operaciones\\selectivo_cierres.jsonl --desde 2026-10-28
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Tabla de lados de NEO_SELECTIVO v2.2. Si la cambias en el EA, cambiala aca tambien.
HABILITADOS = {
    "NAS100": {"SELL"},
    "GER40": {"BUY", "SELL"},
    "US30": {"BUY", "SELL"},
    "GBPUSD": {"SELL"},
    "BTCUSD": set(),
}
BOGOTA = timezone(timedelta(hours=-5))      # Colombia no tiene horario de verano
TOL_APERTURA_S = 900                        # una senal abre dentro de los 15 min de su vela
ES_24_7 = {"BTCUSD"}                        # opera fines de semana: no sirve de referencia


def leer_pred(ruta, desde):
    por = defaultdict(list)                 # simbolo -> [(t_utc, resultado, fecha_vela_servidor)]
    total = 0
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            if not linea.strip():
                continue
            try:
                r = json.loads(linea)
                t = datetime.fromisoformat(r["registrado_en"])
                fv = datetime.fromisoformat(r["fecha_vela"])
                sim = r["symbol"].upper()
                res = r["resultado"]
            except (ValueError, KeyError):
                continue
            total += 1
            if fv.date() >= desde:
                por[sim].append((t, res, fv))
    for v in por.values():
        v.sort()
    return por, total


def leer_cierres(ruta):
    por = defaultdict(list)                 # simbolo -> [(apertura_servidor, tipo, ticket)]
    for linea in open(ruta, encoding="utf-8"):
        if not linea.strip():
            continue
        try:
            r = json.loads(linea)
            por[r["symbol"].upper()].append(
                (datetime.fromisoformat(r["fecha_apertura"]), r["tipo"], r["ticket"]))
        except (ValueError, KeyError):
            continue
    return por


def tiene_operacion(senal, cierres_sim):
    _, res, fv = senal
    return any(tipo == res and 0 <= (ap - fv).total_seconds() <= TOL_APERTURA_S
               for ap, tipo, _ in cierres_sim)


def bogota(t):
    return t.astimezone(BOGOTA).strftime("%d-%b %H:%M")


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True, help="predicciones.jsonl (o prueba_predicciones.jsonl)")
    ap.add_argument("--cierres", help="selectivo_cierres.jsonl (opcional pero recomendado)")
    ap.add_argument("--desde", help="YYYY-MM-DD (dia del servidor). Por defecto, los ultimos 7 dias")
    ap.add_argument("--gap-horas", type=float, default=12.0, dest="gap",
                    help="horas sin consultar (respecto al resto de los pares) para decir que dejo de consultar")
    a = ap.parse_args()

    if not Path(a.pred).exists():
        raise SystemExit(f"No existe {a.pred}.")
    if a.desde:
        desde = date.fromisoformat(a.desde)
    else:
        desde = (datetime.now(timezone.utc) - timedelta(days=7)).date()

    pred, total = leer_pred(a.pred, desde)
    cierres = None
    if a.cierres:
        if Path(a.cierres).exists():
            cierres = leer_cierres(a.cierres)
        else:
            print(f"AVISO: no existe {a.cierres}; se sigue sin cruzar con operaciones.\n")
    if not pred:
        raise SystemExit(f"{total} registros en el archivo, ninguno con vela desde {desde}.")

    ultimos = {s: v[-1][0] for s, v in pred.items()}
    base = [t for s, t in ultimos.items() if s not in ES_24_7] or list(ultimos.values())
    ref = max(base)
    print(f"{a.pred}: {total} registros; desde {desde} (dia del servidor).")
    print(f"Referencia = ultima consulta de los pares que no son 24/7: {bogota(ref)} (hora Bogota)\n")

    simbolos = sorted(set(pred) | set(HABILITADOS))
    for s in simbolos:
        hab = HABILITADOS.get(s)
        hab_txt = ",".join(sorted(hab)) if hab else "NINGUNO (apagado en la tabla)"
        print("=" * 78)
        print(f"{s}   lados habilitados en el EA: {hab_txt}")
        filas = pred.get(s, [])
        if not filas:
            print("  SIN CONSULTAS en la ventana. Para el servidor este par no existe: el EA no esta")
            print("  cargado en ese grafico, o el servidor no tiene modelo activo para ese par (mira")
            print("  /estado: si el par falta ahi, /predict contesta NADA sin dejar registro).")
            continue

        ult = filas[-1]
        gap_h = (ref - ult[0]).total_seconds() / 3600
        senales = [f for f in filas if f[1] in (hab or ())]
        cs = cierres.get(s, []) if cierres is not None else None

        # ---- por dia (dia del servidor) ----
        dias = defaultdict(Counter)
        for _, res, fv in filas:
            dias[fv.date()]["consultas"] += 1
            dias[fv.date()][res] += 1
        if cs is not None:
            for apert, _, _ in cs:
                if apert.date() >= desde:
                    dias[apert.date()]["trades"] += 1
        print(f"  {'dia':<12}{'consultas':>10}{'BUY':>6}{'SELL':>6}{'NADA':>7}"
              + (f"{'trades':>8}" if cs is not None else ""))
        for d in sorted(dias):
            c = dias[d]
            print(f"  {d.isoformat():<12}{c['consultas']:>10}{c['BUY']:>6}{c['SELL']:>6}{c['NADA']:>7}"
                  + (f"{c['trades']:>8}" if cs is not None else ""))
        print(f"  ultima consulta: {bogota(ult[0])} Bogota (vela {ult[2]:%d-%b %H:%M} servidor) "
              f"respuesta {ult[1]}")

        # ---- diagnostico ----
        if gap_h > a.gap:
            print(f"\n  >>> DEJO DE CONSULTAR: {gap_h:.0f} h antes que el resto de los pares.")
            if ult[1] in (hab or ()):
                if cs is None:
                    print("      Su ultima consulta fue una SENAL habilitada. Pasa --cierres para saber si esa")
                    print("      orden se cerro.")
                elif tiene_operacion(ult, cs):
                    print("      La ultima senal abrio una orden y esa orden YA CERRO y fue reportada: no hay una")
                    print("      orden abierta bloqueando. Entonces el EA se detuvo por otra cosa: EA descargado")
                    print("      de ese grafico, AutoTrading apagado, MT4 reiniciado o sin conexion, o el")
                    print("      servidor perdio el modelo de este par (/estado).")
                else:
                    print("      Su ultima consulta fue una SENAL habilitada y NO hay operacion reportada para ella.")
                    print("      Lo mas probable: esa orden sigue ABIERTA y bloquea el par (el EA no consulta mientras")
                    print(f"      tenga una orden suya abierta). Busca en MT4 > Operaciones una orden NEO_SEL de {s}.")
                    print("      (Tambien pasa si el cierre se cerro pero no se reporto: mira el Historial de MT4.)")
            else:
                print("      Su ultima consulta NO fue una senal que abriera orden, asi que este EA no dejo una")
                print("      orden bloqueando (salvo otro EA con el mismo MagicNumber en ese par). Causas posibles:")
                print("      EA descargado de ese grafico, AutoTrading")
                print("      apagado, MT4 reiniciado o sin conexion, o el servidor perdio el modelo (/estado).")
        else:
            print("\n  El EA sigue consultando.")
            if not hab:
                print("  Lados todos apagados en la tabla: no abre nada, es lo esperado.")
            elif not senales:
                print("  El modelo no emitio ninguna senal habilitada en la ventana (todo NADA o lados apagados).")
            elif cs is None:
                print(f"  {len(senales)} senales habilitadas en la ventana. Pasa --cierres para ver si abrieron.")
            else:
                sin = [x for x in senales if not tiene_operacion(x, cs)]
                if not sin:
                    print(f"  Las {len(senales)} senales habilitadas tienen operacion reportada: todo normal.")
                else:
                    print(f"  >>> {len(sin)} de {len(senales)} senales habilitadas NO tienen operacion reportada.")
                    print("      O el EA recibio la senal y no abrio (busca en Experts: 'FAIL OrderSend', 'FAIL margen',")
                    print("      'tp/sl invalidos'), o abrio y no se reporto el cierre (grafico con una version vieja del")
                    print("      EA, que reporta a otro archivo), o la ultima sigue abierta. Las mas recientes (vela del servidor):")
                    for _, res, fv in sin[-5:]:
                        print(f"        {fv:%d-%b %H:%M}  {res}")
        print()


if __name__ == "__main__":
    main()
