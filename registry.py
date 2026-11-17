"""
registry.py — única fuente de verdad de qué modelo/API está corriendo.

Resuelve directamente el riesgo del resumen §8: "resolver_modelo() filtra por
symbol pero no por version, y con --candidato auto elige por fecha de archivo".
Acá NUNCA se elige por mtime ni por nombre de archivo. Se elige por lo que diga
registry.json, y punto.

Uso típico:
    from registry import Registry
    reg = Registry()

    # al terminar de entrenar un modelo nuevo:
    reg.registrar_version(
        symbol="NAS100",
        version_id="v1_20260805",
        archivo_modelo="modelos/NAS100/v1_20260805.pt",
        archivo_scaler="modelos/NAS100/v1_20260805_scaler.pkl",
        features=FEATURE_LIST,
        tp=200, sl=30, costo=3, horizonte=288,
        entrenado_con={"desde": "2025-09-22", "hasta": "2026-04-09", "n_filas": 38736},
        estado="candidato",   # candidato -> demo -> produccion -> retirado
        notas="primer modelo con features relativas y target TP/SL",
    )

    # solo cuando ya se validó con validar.py y se decide activar:
    reg.activar(symbol="NAS100", version_id="v1_20260805")

    # para que la API sepa qué cargar:
    activo = reg.activo("NAS100")   # -> dict con toda la info de la version activa, o None
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

RUTA_DEFAULT = Path(__file__).parent / "registry.json"


class Registry:
    def __init__(self, ruta=RUTA_DEFAULT):
        self.ruta = Path(ruta)
        if not self.ruta.exists():
            raise FileNotFoundError(f"No existe {self.ruta}. Copiá el registry.json base primero.")
        self._cargar()

    def _cargar(self):
        with open(self.ruta, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def _guardar(self):
        # escritura atomica: escribe a un temporal y renombra, para no dejar
        # el json corrupto si algo falla a mitad de escritura.
        tmp = self.ruta.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.ruta)

    @staticmethod
    def _ahora():
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    # -----------------------------------------------------------------
    def registrar_version(self, symbol, version_id, archivo_modelo, archivo_scaler,
                           features, tp, sl, costo, horizonte, entrenado_con,
                           estado="candidato", notas=""):
        symbol = symbol.upper()
        existe = [v for v in self.data["versiones"]
                  if v["symbol"] == symbol and v["version_id"] == version_id]
        if existe:
            raise ValueError(f"{symbol}/{version_id} ya existe en el registry. "
                              f"Usá otro version_id (sugerido: incluir fecha).")

        entrada = {
            "symbol": symbol,
            "version_id": version_id,
            "archivo_modelo": archivo_modelo,
            "archivo_scaler": archivo_scaler,
            "features": features,
            "tp": tp, "sl": sl, "costo": costo, "horizonte": horizonte,
            "entrenado_con": entrenado_con,
            "estado": estado,
            "creado_en": self._ahora(),
            "activado_en": None,
            "desactivado_en": None,
            "notas": notas,
            "lados_aprobados": [],   # se llena SOLO cuando validar.py corre y aprueba
            "validado_en": None,
        }
        self.data["versiones"].append(entrada)
        self._guardar()
        return entrada

    def marcar_lados_aprobados(self, symbol, version_id, lados):
        """Llamado por validar.py al terminar -- es la UNICA forma en que un
        lado (BUY/SELL) queda habilitado para servir señales. Si un lado no
        esta en esta lista, api.py no lo va a ofrecer, sin importar que el
        .pkl lo tenga adentro."""
        symbol = symbol.upper()
        entrada = self._buscar(symbol, version_id)
        if entrada is None:
            raise ValueError(f"No existe {symbol}/{version_id}.")
        entrada["lados_aprobados"] = list(lados)
        entrada["validado_en"] = self._ahora()
        self._guardar()
        return entrada

    def activar(self, symbol, version_id):
        """Marca version_id como la version activa de symbol. Desactiva la
        anterior. Se NIEGA a activar si validar.py todavia no aprobo ningun
        lado -- asi no puede pasar de nuevo que algo sin validar quede
        sirviendo señales solo porque alguien llamo a activar() de mas."""
        symbol = symbol.upper()
        objetivo = self._buscar(symbol, version_id)
        if objetivo is None:
            raise ValueError(f"No existe {symbol}/{version_id}. Registrala primero con registrar_version().")
        if not objetivo.get("lados_aprobados"):
            raise ValueError(
                f"{symbol}/{version_id} todavía no tiene ningún lado aprobado por validar.py "
                f"(lados_aprobados está vacío). Corré validar.py primero -- no se puede activar "
                f"a ciegas."
            )

        anterior_id = self.data["activos"].get(symbol)
        if anterior_id:
            anterior = self._buscar(symbol, anterior_id)
            if anterior:
                anterior["estado"] = "retirado"
                anterior["desactivado_en"] = self._ahora()

        objetivo["estado"] = "produccion"
        objetivo["activado_en"] = self._ahora()
        objetivo["desactivado_en"] = None
        self.data["activos"][symbol] = version_id
        self._guardar()
        return objetivo

    def activo(self, symbol):
        """Devuelve el dict completo de la version activa de symbol, o None."""
        symbol = symbol.upper()
        version_id = self.data["activos"].get(symbol)
        if not version_id:
            return None
        return self._buscar(symbol, version_id)

    def _buscar(self, symbol, version_id):
        for v in self.data["versiones"]:
            if v["symbol"] == symbol and v["version_id"] == version_id:
                return v
        return None

    # -----------------------------------------------------------------
    def registrar_cambio_api(self, version_api, descripcion):
        """Loguea un cambio de contrato/version de api.py. Llamar SIEMPRE que
        cambie un endpoint, un campo de respuesta, o el formato de la URL."""
        entrada = {
            "version_api": version_api,
            "descripcion": descripcion,
            "fecha": self._ahora(),
        }
        self.data["api"]["historial"].append(entrada)
        self.data["api"]["version_actual"] = version_api
        self._guardar()
        return entrada

    def estado(self):
        """Resumen legible para consola."""
        lineas = ["=== Registry ==="]
        for symbol, vid in self.data["activos"].items():
            if vid:
                v = self._buscar(symbol, vid)
                lineas.append(f"{symbol}: {vid}  (activo desde {v['activado_en']})")
            else:
                lineas.append(f"{symbol}: sin version activa")
        lineas.append(f"API version actual: {self.data['api']['version_actual']}")
        return "\n".join(lineas)


if __name__ == "__main__":
    reg = Registry()
    print(reg.estado())
