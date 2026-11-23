"""Extractor ético del DENUE (INEGI) hacia la capa Bronce.

Dos métodos de la API oficial del DENUE:
  * Cuantificar         conteos agregados de establecimientos (sin datos de ningún negocio):
                        municipios de Colima y estados de comparación, por subsector y estrato.
  * BuscarAreaActEstr   establecimientos del sector 46 en cada municipio de Colima, con coordenadas.
                        Se aplica MINIMIZACIÓN: antes de escribir en Bronce se eliminan nombre,
                        razón social, teléfono, correo, sitio web y domicilio (ver config.CAMPOS_CONSERVADOS).

Reutiliza las utilidades del extractor de E0 (robots.txt, reintentos, manifiesto, hash) para
que todas las fuentes compartan el mismo manifiesto y las mismas reglas éticas.

Uso (desde la raíz del repo):
    python E2/e2/src/extractor_denue.py            # requiere la variable DENUE_TOKEN
    python E2/e2/src/extractor_denue.py --dry-run
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

sys.path.insert(0, str(config.REPO / "E0" / "src"))
import extractor_bronce as e0  # noqa: E402

log = logging.getLogger("denue")


def _url(metodo: str, *partes: str, token: str) -> str:
    return "/".join([config.API_DENUE, metodo, *map(str, partes), token])


def _guardar(clave: str, payload: dict, url: str, token: str, n: int) -> dict:
    """Escribe en Bronce (idempotente por hash) y registra en el manifiesto compartido de E0."""
    ahora = dt.datetime.now(dt.timezone.utc)
    crudo = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    fila = {"timestamp_utc": ahora.isoformat(timespec="seconds"), "fuente": "denue", "clave": clave,
            "id_serie": payload["_captura"]["metodo"], "url_sin_token": e0.ocultar_token(url, token),
            "http_status": 200, "sha256": e0.sha256(json.dumps(payload["respuesta"], sort_keys=True).encode()),
            "n_observaciones": n}
    if fila["sha256"] == e0.ultimo_hash("denue", clave):
        fila["resultado"] = "sin_cambios"
    else:
        destino = config.BRONCE_DENUE / clave / f"{ahora:%Y-%m-%d_%H%M%S}.json"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(crudo)
        fila.update(archivo=str(destino.relative_to(config.REPO / "E0")), resultado="nuevo")
    e0.registrar(fila)
    log.info("[denue/%s] %s (%d registros)", clave, fila["resultado"], n)
    return fila


def _get_json(url: str, headers: dict):
    r = e0.get_con_reintentos(url, headers)
    r.raise_for_status()
    datos = r.json()
    if not isinstance(datos, list):          # la API devuelve texto o dict cuando no hay resultados
        return []
    return datos


def minimizar(registros: list[dict]) -> list[dict]:
    return [{k: r.get(k) for k in config.CAMPOS_CONSERVADOS} for r in registros]


def capturar_cuantificar(token: str, headers: dict) -> list[dict]:
    actividades = ",".join(config.SUBSECTORES)
    areas = ",".join(list(config.ESTADOS_COMPARACION) +
                     [config.ENTIDAD + m for m in config.MUNICIPIOS])
    filas = []
    for estrato in range(0, 8):
        url = _url("Cuantificar", actividades, areas, estrato, token=token)
        datos = _get_json(url, headers)
        payload = {"_captura": {"metodo": "Cuantificar", "actividad": actividades, "areas": areas,
                                "estrato": estrato}, "respuesta": datos}
        filas.append(_guardar(f"cuantificar_estrato{estrato}", payload, url, token, len(datos)))
        time.sleep(config.PAUSA_SEG)
    return filas


def capturar_establecimientos(token: str, headers: dict) -> list[dict]:
    filas = []
    for mun in config.MUNICIPIOS:
        registros, inicio = [], 1
        while True:
            fin = inicio + config.TAM_PAGINA - 1
            url = _url("BuscarAreaActEstr", config.ENTIDAD, mun, 0, 0, 0, config.SECTOR, 0, 0, 0, 0,
                       inicio, fin, 0, 0, token=token)
            pagina = _get_json(url, headers)
            registros += pagina
            time.sleep(config.PAUSA_SEG)
            if len(pagina) < config.TAM_PAGINA:
                break
            inicio = fin + 1
        conservados = minimizar(registros)
        payload = {"_captura": {"metodo": "BuscarAreaActEstr", "entidad": config.ENTIDAD, "municipio": mun,
                                "sector": config.SECTOR, "campos_conservados": config.CAMPOS_CONSERVADOS,
                                "nota_privacidad": "nombre, razón social, contacto y domicilio eliminados en la captura"},
                   "respuesta": conservados}
        filas.append(_guardar(f"establecimientos_{config.ENTIDAD}{mun}", payload,
                              url, token, len(conservados)))
    return filas


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--solo", choices=["cuantificar", "establecimientos"])
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg_e0 = e0.cargar_config()
    headers = {"User-Agent": cfg_e0["user_agent"], "Accept": "application/json"}
    token = os.getenv(config.TOKEN_ENV)

    if args.dry_run:
        log.info("[dry-run] Cuantificar: %s", _url("Cuantificar", ",".join(config.SUBSECTORES), "06,...", 0, token="***"))
        log.info("[dry-run] Establecimientos: %d municipios, páginas de %d", len(config.MUNICIPIOS), config.TAM_PAGINA)
        return 0
    if not token:
        log.warning("Falta %s: se omite la captura del DENUE", config.TOKEN_ENV)
        return 0
    if not e0.robots_permite(config.ROBOTS_INEGI, config.API_DENUE, cfg_e0["user_agent"]):
        log.error("robots.txt prohíbe %s", config.API_DENUE)
        return 1
    try:
        if args.solo in (None, "cuantificar"):
            capturar_cuantificar(token, headers)
        if args.solo in (None, "establecimientos"):
            capturar_establecimientos(token, headers)
    except Exception as e:  # noqa: BLE001
        log.error("Falla en la captura del DENUE: %s", e0.ocultar_token(str(e), token))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
