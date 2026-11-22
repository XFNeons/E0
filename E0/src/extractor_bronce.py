"""
Extractor ético de la capa Bronce - Observatorio del Comercio al por Menor en Colima.

Principios:
  * Solo usa APIs oficiales y documentadas (INEGI BIE y Banxico SIE); no hace scraping de HTML.
  * Revisa robots.txt antes de cada fuente y se detiene si la ruta está prohibida.
  * Se identifica con un User-Agent con contacto y espera entre peticiones.
  * Los tokens se leen de variables de entorno (GitHub Secrets); nunca se guardan en disco ni en logs.
  * Guarda la respuesta CRUDA tal como llega (Bronce = sin transformar) y registra un manifiesto
    con fecha, URL sin token, código HTTP, hash SHA-256 y número de periodos.
  * Es idempotente: si el contenido no cambió desde la última captura, no duplica el archivo.

Uso:
    python src/extractor_bronce.py                 # todas las fuentes
    python src/extractor_bronce.py --fuente inegi  # solo una
    python src/extractor_bronce.py --dry-run       # valida configuración sin descargar
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from urllib import robotparser
from urllib.parse import urlparse

import requests

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = RAIZ / "config" / "fuentes.json"
BRONCE = RAIZ / "data" / "bronze"
MANIFIESTO = BRONCE / "_manifiesto.csv"
CAMPOS_MANIFIESTO = [
    "timestamp_utc", "fuente", "clave", "id_serie", "url_sin_token", "http_status",
    "sha256", "n_observaciones", "n_periodos_mensuales", "primer_periodo", "ultimo_periodo",
    "archivo", "resultado",
]

log = logging.getLogger("bronce")


# ----------------------------------------------------------------------------- utilidades
def cargar_config(ruta: Path = CONFIG) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ocultar_token(url: str, token: str | None) -> str:
    return url.replace(token, "***TOKEN***") if token else url


def robots_permite(robots_url: str, url: str, user_agent: str, timeout: int = 15) -> bool:
    """Devuelve True si robots.txt permite la URL. Si robots.txt no existe (404) se permite;
    si no se puede consultar por error de red, se registra y se permite solo para APIs
    oficiales documentadas (criterio documentado en docs/E0/propuesta.md)."""
    rp = robotparser.RobotFileParser()
    try:
        r = requests.get(robots_url, headers={"User-Agent": user_agent}, timeout=timeout)
        if r.status_code == 404:
            log.info("robots.txt no existe en %s: sin restricciones declaradas", robots_url)
            return True
        r.raise_for_status()
        rp.parse(r.text.splitlines())
    except requests.RequestException as e:
        log.warning("No se pudo leer %s (%s); se continúa por ser API oficial documentada", robots_url, e)
        return True
    ruta = urlparse(url).path
    permitido = rp.can_fetch(user_agent, ruta)
    log.info("robots.txt %s -> %s: %s", robots_url, ruta.split("/")[1:6], "PERMITIDO" if permitido else "PROHIBIDO")
    return permitido


def get_con_reintentos(url: str, headers: dict, intentos: int = 4, timeout: int = 60) -> requests.Response:
    espera = 5
    for i in range(1, intentos + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            return r
        except requests.RequestException as e:
            if i == intentos:
                raise
            log.warning("Intento %d/%d falló (%s). Reintentando en %ds", i, intentos, e, espera)
            time.sleep(espera)
            espera *= 2
    raise RuntimeError("inalcanzable")


# ----------------------------------------------------------------------------- parsers (solo para validar, no transforman lo guardado)
def periodos_inegi(payload: dict) -> list[str]:
    obs = payload.get("Series", [{}])[0].get("OBSERVATIONS", []) or []
    return [o["TIME_PERIOD"] for o in obs if o.get("OBS_VALUE") not in (None, "")]


def periodos_banxico(payload: dict) -> list[str]:
    datos = payload.get("bmx", {}).get("series", [{}])[0].get("datos", []) or []
    return [d["fecha"] for d in datos if d.get("dato") not in (None, "", "N/E")]


def a_mes(periodo: str) -> str:
    """Normaliza '2024/03', '2024/03/15' o '15/03/2024' a 'AAAA-MM'."""
    p = periodo.replace("-", "/")
    partes = p.split("/")
    if len(partes[0]) == 4:            # AAAA/MM[/DD]
        return f"{partes[0]}-{partes[1].zfill(2)}" if len(partes) > 1 else partes[0]
    if len(partes) == 3:               # DD/MM/AAAA (Banxico)
        return f"{partes[2]}-{partes[1].zfill(2)}"
    return p


# ----------------------------------------------------------------------------- manifiesto
def ultimo_hash(fuente: str, clave: str) -> str | None:
    if not MANIFIESTO.exists():
        return None
    ultimo = None
    with open(MANIFIESTO, encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if fila["fuente"] == fuente and fila["clave"] == clave and fila["resultado"] in ("nuevo", "sin_cambios"):
                ultimo = fila["sha256"]
    return ultimo


def registrar(fila: dict) -> None:
    MANIFIESTO.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not MANIFIESTO.exists()
    with open(MANIFIESTO, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_MANIFIESTO)
        if nuevo:
            w.writeheader()
        w.writerow({k: fila.get(k, "") for k in CAMPOS_MANIFIESTO})


# ----------------------------------------------------------------------------- captura
def capturar_serie(fuente: str, serie: dict, url: str, token: str | None, headers: dict,
                   parser, min_periodos: int) -> dict:
    ahora = dt.datetime.now(dt.timezone.utc)
    fila = {"timestamp_utc": ahora.isoformat(timespec="seconds"), "fuente": fuente,
            "clave": serie["clave"], "id_serie": serie["id"], "url_sin_token": ocultar_token(url, token)}
    try:
        r = get_con_reintentos(url, headers)
        fila["http_status"] = r.status_code
        r.raise_for_status()
        crudo = r.content
        payload = json.loads(crudo)
    except Exception as e:  # noqa: BLE001 - se registra cualquier fallo en el manifiesto
        fila["resultado"] = f"error: {type(e).__name__}: {ocultar_token(str(e), token)}"[:300]
        log.error("[%s/%s] %s", fuente, serie["clave"], fila["resultado"])
        registrar(fila)
        return fila

    periodos = parser(payload)
    meses = sorted({a_mes(p) for p in periodos})
    fila.update({
        "sha256": sha256(crudo), "n_observaciones": len(periodos), "n_periodos_mensuales": len(meses),
        "primer_periodo": meses[0] if meses else "", "ultimo_periodo": meses[-1] if meses else "",
    })

    if fila["sha256"] == ultimo_hash(fuente, serie["clave"]):
        fila["resultado"] = "sin_cambios"
        log.info("[%s/%s] sin cambios desde la última captura", fuente, serie["clave"])
    else:
        destino = BRONCE / fuente / serie["clave"] / f"{ahora:%Y-%m-%d_%H%M%S}.json"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(crudo)  # se guarda el cuerpo exacto recibido
        fila["archivo"] = str(destino.relative_to(RAIZ))
        fila["resultado"] = "nuevo"
        log.info("[%s/%s] guardado %s (%d periodos mensuales: %s a %s)", fuente, serie["clave"],
                 fila["archivo"], len(meses), fila["primer_periodo"], fila["ultimo_periodo"])

    if len(meses) < min_periodos:
        log.warning("[%s/%s] solo %d periodos (< %d requeridos)", fuente, serie["clave"], len(meses), min_periodos)
    registrar(fila)
    return fila


def correr_inegi(cfg: dict, comun: dict, dry: bool) -> list[dict]:
    token = os.getenv(cfg["token_env"])
    resultados = []
    for s in cfg["series"]:
        if "PENDIENTE" in s["id"]:
            log.warning("[inegi/%s] ID pendiente: se omite (ver README, sección 'IDs de INEGI')", s["clave"])
            continue
        url = cfg["base_url"].format(id=s["id"], area=s["area"], banco=s["banco"], token=token or "SIN_TOKEN")
        if dry:
            log.info("[dry-run] inegi %s -> %s", s["clave"], ocultar_token(url, token))
            continue
        if not token:
            log.error("Falta la variable de entorno %s", cfg["token_env"])
            break
        resultados.append(capturar_serie("inegi", s, url, token, comun["headers"], periodos_inegi, comun["min"]))
        time.sleep(comun["pausa"])
    return resultados


def correr_banxico(cfg: dict, comun: dict, dry: bool) -> list[dict]:
    token = os.getenv(cfg["token_env"])
    fin = dt.date.today().isoformat()
    resultados = []
    for s in cfg["series"]:
        url = cfg["base_url"].format(id=s["id"], inicio=cfg["fecha_inicio"], fin=fin)
        if dry:
            log.info("[dry-run] banxico %s -> %s", s["clave"], url)
            continue
        if not token:
            log.error("Falta la variable de entorno %s", cfg["token_env"])
            break
        headers = {**comun["headers"], "Bmx-Token": token}  # token en header, no en la URL
        resultados.append(capturar_serie("banxico", s, url, token, headers, periodos_banxico, comun["min"]))
        time.sleep(comun["pausa"])
    return resultados


EJECUTORES = {"inegi": correr_inegi, "banxico": correr_banxico}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fuente", choices=list(EJECUTORES), help="Ejecutar solo una fuente")
    ap.add_argument("--dry-run", action="store_true", help="Validar configuración sin descargar")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    config = cargar_config()
    comun = {"headers": {"User-Agent": config["user_agent"], "Accept": "application/json"},
             "pausa": config["pausa_entre_peticiones_seg"], "min": config["min_periodos"]}

    todos = []
    for nombre, cfg in config["fuentes"].items():
        if args.fuente and nombre != args.fuente:
            continue
        muestra = cfg["base_url"].split("{")[0]
        if not args.dry_run and not robots_permite(cfg["robots_url"], muestra, config["user_agent"]):
            log.error("robots.txt prohíbe %s: fuente omitida", muestra)
            continue
        todos += EJECUTORES[nombre](cfg, comun, args.dry_run)

    errores = [r for r in todos if str(r.get("resultado", "")).startswith("error")]
    log.info("Resumen: %d series procesadas, %d errores", len(todos), len(errores))
    # Falla el job solo si TODO falló, para que una serie caída no detenga la captura del resto.
    return 1 if todos and len(errores) == len(todos) else 0


if __name__ == "__main__":
    sys.exit(main())
