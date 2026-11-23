"""Bronce SINTÉTICA del DENUE (mismo formato que la API, ya minimizado) para pruebas y --demo.
¡No son datos reales!

Defectos sembrados:
  * un establecimiento con coordenadas (0, 0)                 -> cuarentena: fuera de Colima
  * un CLEE repetido                                          -> cuarentena: duplicado
  * un establecimiento de manufactura (subsector 311)         -> cuarentena: fuera del sector 46
  * un establecimiento cuyo AreaGeo dice otro municipio       -> cuarentena: municipio inconsistente
  * un estrato con texto no reconocido                         -> cuarentena: estrato inválido
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import config

CENTROS = {  # (lat, lon, tamaño relativo)
    "001": (18.937, -103.962, 0.04), "002": (19.243, -103.728, 0.25), "003": (19.321, -103.758, 0.03),
    "004": (19.205, -103.808, 0.03), "005": (19.329, -103.603, 0.03), "006": (18.999, -103.736, 0.01),
    "007": (19.052, -104.316, 0.22), "008": (19.386, -104.058, 0.01), "009": (18.909, -103.874, 0.15),
    "010": (19.267, -103.737, 0.23),
}
PESO_SUBSECTOR = {"461": .45, "462": .05, "463": .12, "464": .08, "465": .09, "466": .07,
                  "467": .07, "468": .06, "469": .01}


def _establecimiento(rng, i, mun, lat, lon, sub) -> dict:
    estrato = int(rng.choice([1, 2, 3, 4, 5, 6, 7], p=[.86, .07, .04, .015, .01, .004, .001]))
    clase = sub + f"{rng.integers(110, 199)}"
    return {"CLEE": f"06{mun}{sub}{i:011d}", "Id": str(9_000_000 + i), "Clase_actividad": f"Clase sintética {clase}",
            "Estrato": config.ESTRATOS[estrato], "Tipo": "Fijo", "CP": "28000",
            "Ubicacion": f"LOCALIDAD, {config.MUNICIPIOS[mun].upper()}, Colima",
            "Longitud": f"{lon:.6f}", "Latitud": f"{lat:.6f}", "AGEB": "0001", "Manzana": "001",
            "CLASE_ACTIVIDAD_ID": clase, "SECTOR_ACTIVIDAD_ID": sub[:2], "SUBSECTOR_ACTIVIDAD_ID": sub,
            "RAMA_ACTIVIDAD_ID": clase[:4], "SUBRAMA_ACTIVIDAD_ID": clase[:5], "Tipo_Asentamiento": "COLONIA",
            "Fecha_Alta": f"{rng.integers(2010, 2026)}-{rng.integers(1, 13):02d}", "AreaGeo": f"06{mun}0001"}


def generar(base: Path, total: int = 3000, semilla: int = 11) -> Path:
    rng = np.random.default_rng(semilla)
    marca = "2026-11-16_131700"
    i = 0
    for mun, (lat0, lon0, peso) in CENTROS.items():
        n = max(5, int(total * peso))
        regs = []
        for _ in range(n):
            i += 1
            sub = rng.choice(list(PESO_SUBSECTOR), p=list(PESO_SUBSECTOR.values()))
            lat, lon = rng.normal(lat0, 0.018), rng.normal(lon0, 0.018)
            regs.append(_establecimiento(rng, i, mun, lat, lon, str(sub)))
        if mun == "002":
            regs[0]["Latitud"], regs[0]["Longitud"] = "0", "0"
            regs.append(dict(regs[5]))                                  # CLEE duplicado
            regs[10]["SUBSECTOR_ACTIVIDAD_ID"], regs[10]["SECTOR_ACTIVIDAD_ID"] = "311", "31"
            regs[11]["AreaGeo"] = "060070001"                           # dice Manzanillo
            regs[12]["Estrato"] = "sin dato"
        payload = {"_captura": {"metodo": "BuscarAreaActEstr", "entidad": "06", "municipio": mun,
                                "nota": "DATOS SINTÉTICOS"}, "respuesta": regs}
        destino = base / "denue" / f"establecimientos_06{mun}" / f"{marca}.json"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    pob = {"06": 1.0, "14": 12.0, "16": 6.5, "18": 1.9}
    for estrato in range(8):
        resp = []
        for area in list(config.ESTADOS_COMPARACION) + ["06" + m for m in config.MUNICIPIOS]:
            # el conteo oficial difiere un poco de lo descargado (altas y bajas entre fechas de corte)
            escala = pob.get(area, CENTROS.get(area[2:], (0, 0, .1))[2]) * total * 1.03
            for sub, p in PESO_SUBSECTOR.items():
                frac = 1.0 if estrato == 0 else [.86, .07, .04, .015, .01, .004, .001][estrato - 1]
                resp.append({"AE": sub, "AG": area, "Total": str(int(escala * p * frac))})
        payload = {"_captura": {"metodo": "Cuantificar", "estrato": estrato, "nota": "DATOS SINTÉTICOS"},
                   "respuesta": resp}
        destino = base / "denue" / f"cuantificar_estrato{estrato}" / f"{marca}.json"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return base
