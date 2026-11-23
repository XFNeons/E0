"""Fuente especializada geoespacial: DENUE (INEGI) con GeoPandas.

Flujo:  Bronce DENUE -> tipado -> Puerta de Calidad (Pandera) -> Plata (puntos válidos)
        -> GeoPandas (EPSG:6372) -> Oro:
             * oro/comercio_municipios.csv     indicadores por municipio (+ capa .geojson si hay límites)
             * oro/comercio_hexagonos.geojson  densidad en hexágonos de 1 km (celdas < 3 suprimidas)
             * oro/comparativo_estados.csv     estructura por estrato y subsector (Colima vs vecinos)
             * oro/linaje_geo.csv              cada fila de Oro -> establecimientos (CLEE) -> archivo Bronce
        -> mapas en docs/E2/img/ y mapa interactivo (si folium está instalado).

Uso (desde E2/e2):
    python -m src.geo            # Bronce real en E0/data/bronze/denue
    python -m src.geo --demo     # Bronce sintética -> data_demo/
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import math
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

try:                                   # pandera >= 0.24
    import pandera.pandas as pa
except ImportError:
    import pandera as pa
from pandera.errors import SchemaErrors

from . import config

log = logging.getLogger("geo")
CODIGO_ESTRATO = {v: k for k, v in config.ESTRATOS.items()}


def id_estable(*partes) -> str:
    return hashlib.sha1("|".join(map(str, partes)).encode()).hexdigest()[:16]


def _captura(archivo: Path) -> pd.Timestamp:
    return pd.to_datetime(archivo.stem, format="%Y-%m-%d_%H%M%S", errors="coerce")


# ====================================================================== lectura de Bronce
def _ultimas(dir_denue: Path, prefijo: str) -> list[Path]:
    """El DENUE es una foto del directorio: se usa la captura más reciente de cada carpeta."""
    return [sorted(d.glob("*.json"))[-1] for d in sorted(dir_denue.glob(f"{prefijo}*"))
            if d.is_dir() and any(d.glob("*.json"))]


def leer_establecimientos(dir_bronce: Path) -> pd.DataFrame:
    filas = []
    for archivo in _ultimas(dir_bronce / "denue", "establecimientos_"):
        crudo = archivo.read_bytes()
        payload = json.loads(crudo)
        ruta = archivo.relative_to(dir_bronce).as_posix()
        huella = hashlib.sha256(crudo).hexdigest()
        mun = payload.get("_captura", {}).get("municipio") or archivo.parent.name[-3:]
        for r in payload.get("respuesta", []):
            filas.append({**{k: r.get(k) for k in config.CAMPOS_CONSERVADOS},
                          "municipio_solicitado": str(mun).zfill(3), "ruta_bronce": ruta,
                          "sha256_bronce": huella, "id_bronce": f"{ruta}#{r.get('CLEE')}",
                          "captura": _captura(archivo)})
    return pd.DataFrame(filas)


def leer_cuantificar(dir_bronce: Path) -> pd.DataFrame:
    filas = []
    for archivo in _ultimas(dir_bronce / "denue", "cuantificar_estrato"):
        payload = json.loads(archivo.read_bytes())
        estrato = int(payload.get("_captura", {}).get("estrato", archivo.parent.name[-1]))
        for r in payload.get("respuesta", []):
            filas.append({"subsector": str(r.get("AE")), "area": str(r.get("AG")), "estrato": estrato,
                          "total": pd.to_numeric(r.get("Total"), errors="coerce"),
                          "ruta_bronce": archivo.relative_to(dir_bronce).as_posix(),
                          "captura": _captura(archivo)})
    return pd.DataFrame(filas)


# ====================================================================== tipado e integración
def tipar(df: pd.DataFrame) -> pd.DataFrame:
    """Une el esquema de la API (todo texto, nombres heterogéneos) a tipos y nombres del proyecto."""
    out = pd.DataFrame({
        "clee": df["CLEE"].astype("string"),
        "cve_mun": df["AreaGeo"].astype("string").str[2:5],
        "municipio_solicitado": df["municipio_solicitado"].astype("string"),
        "subsector": df["SUBSECTOR_ACTIVIDAD_ID"].astype("string"),
        "clase": df["CLASE_ACTIVIDAD_ID"].astype("string"),
        "estrato_texto": df["Estrato"].astype("string"),
        "estrato": df["Estrato"].map(CODIGO_ESTRATO).astype("float64"),
        "lat": pd.to_numeric(df["Latitud"], errors="coerce"),
        "lon": pd.to_numeric(df["Longitud"], errors="coerce"),
        "fecha_alta": pd.to_datetime(df["Fecha_Alta"], format="%Y-%m", errors="coerce"),
        "tipo": df["Tipo"].astype("string"),
        "ageb": df["AGEB"].astype("string"),
    })
    for c in ["ruta_bronce", "sha256_bronce", "id_bronce", "captura"]:
        out[c] = df[c]
    out["municipio"] = out["municipio_solicitado"].map(config.MUNICIPIOS)
    return out


# ====================================================================== Puerta de Calidad
MOTIVOS = {
    "in_range": "Coordenada fuera de la parte continental de Colima, o estrato fuera de 1-7",
    "not_nullable": "Campo obligatorio vacío o no interpretable (coordenada, estrato, clave)",
    "field_uniqueness": "CLEE duplicado (el mismo establecimiento aparece dos veces)",
    "sector_46": "El establecimiento no pertenece al comercio al por menor (sector 46)",
    "municipio_consistente": "La clave geográfica del establecimiento no coincide con el municipio consultado",
    "isin": "Valor fuera del catálogo",
}


def esquema() -> pa.DataFrameSchema:
    return pa.DataFrameSchema(
        columns={
            "clee": pa.Column(str, nullable=False, unique=True),
            "cve_mun": pa.Column(str, pa.Check.isin(list(config.MUNICIPIOS)), nullable=False),
            "municipio_solicitado": pa.Column(str, pa.Check.isin(list(config.MUNICIPIOS)), nullable=False),
            "subsector": pa.Column(str, nullable=False),
            "clase": pa.Column(str, nullable=True),
            "estrato_texto": pa.Column(str, nullable=True),
            "estrato": pa.Column(float, pa.Check.in_range(1, 7), nullable=False),
            "lat": pa.Column(float, pa.Check.in_range(config.LAT_MIN, config.LAT_MAX), nullable=False),
            "lon": pa.Column(float, pa.Check.in_range(config.LON_MIN, config.LON_MAX), nullable=False),
            "fecha_alta": pa.Column("datetime64[ns]", nullable=True),
            "tipo": pa.Column(str, nullable=True),
            "ageb": pa.Column(str, nullable=True),
            "ruta_bronce": pa.Column(str, nullable=False),
            "sha256_bronce": pa.Column(str, nullable=False),
            "id_bronce": pa.Column(str, nullable=False),
            "captura": pa.Column("datetime64[ns]", nullable=False),
            "municipio": pa.Column(str, nullable=False),
        },
        checks=[
            pa.Check(lambda d: d["subsector"].astype(str).str.startswith(config.SECTOR), name="sector_46"),
            pa.Check(lambda d: d["cve_mun"].astype(str) == d["municipio_solicitado"].astype(str),
                     name="municipio_consistente"),
        ],
        strict=True, coerce=True, name="puerta_denue",
    )


def aplicar_puerta(df: pd.DataFrame, dir_cuarentena: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    df = df.reset_index(drop=True)
    corrida = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    sch = esquema()
    try:
        validos = sch.validate(df, lazy=True)
        fallas = pd.DataFrame(columns=["index", "column", "check", "failure_case"])
    except SchemaErrors as err:
        fallas = err.failure_cases.copy()
        if fallas["index"].isna().any():
            raise RuntimeError(f"Puerta DENUE cerrada por falla de esquema: "
                               f"{fallas[fallas['index'].isna()][['column', 'check']].to_dict('records')}") from err
        fallas["index"] = fallas["index"].astype(int)
        validos = sch.validate(df.drop(index=fallas["index"].unique()), lazy=False)

    if fallas.empty:
        cuarentena = df.iloc[0:0].assign(motivo="", regla="")
    else:
        txt = lambda s: s.map(lambda v: "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v))
        f = fallas.assign(check=txt(fallas["check"]), column=txt(fallas["column"]))
        f["motivo"] = f["check"].map(lambda c: MOTIVOS.get(c.split("(")[0], c))
        por_fila = f.groupby("index").agg(
            motivo=("motivo", lambda s: " | ".join(dict.fromkeys(s))),
            regla=("check", lambda s: " | ".join(dict.fromkeys(c.split("(")[0] for c in s))),
            columna=("column", lambda s: " | ".join(dict.fromkeys(x or "(fila)" for x in s))))
        cuarentena = df.loc[por_fila.index].join(por_fila)
    cuarentena = cuarentena.assign(corrida_utc=corrida)
    if dir_cuarentena is not None and len(cuarentena):
        destino = dir_cuarentena / "cuarentena_denue.csv"
        cuarentena.to_csv(destino, mode="a", header=not destino.exists(), index=False)
    resumen = {"evaluados": int(len(df)), "validos": int(len(validos)), "cuarentena": int(len(cuarentena)),
               "por_regla": cuarentena["regla"].str.split(r" \| ").explode().value_counts().to_dict()
               if len(cuarentena) else {}}
    return validos.reset_index(drop=True), cuarentena, resumen


# ====================================================================== indicadores (sin GeoPandas)
def distancia_competidor(df: pd.DataFrame) -> pd.Series:
    """Distancia (m) al establecimiento más cercano del MISMO subsector: medida de competencia.
    Haversine con BallTree; no requiere proyección."""
    from sklearn.neighbors import BallTree
    salida = pd.Series(np.nan, index=df.index)
    for _, g in df.groupby("subsector"):
        if len(g) < 2:
            continue
        coords = np.radians(g[["lat", "lon"]].to_numpy())
        dist, _ = BallTree(coords, metric="haversine").query(coords, k=2)
        salida.loc[g.index] = dist[:, 1] * 6_371_000
    return salida


def indicadores_municipio(df: pd.DataFrame, hoy: pd.Timestamp | None = None) -> pd.DataFrame:
    hoy = hoy or pd.Timestamp.today()
    corte = hoy - pd.DateOffset(months=config.MESES_ALTA_RECIENTE)
    d = df.assign(micro=df["estrato"].eq(1), alta_reciente=df["fecha_alta"] >= corte)
    base = d.groupby(["cve_mun", "municipio"]).agg(
        establecimientos=("clee", "size"),
        pct_micro=("micro", lambda s: round(100 * s.mean(), 2)),
        pct_altas_recientes=("alta_reciente", lambda s: round(100 * s.mean(), 2)),
        dist_mediana_competidor_m=("dist_competidor_m", lambda s: round(float(s.median()), 1)),
    ).reset_index()
    sub = (d.pivot_table(index="cve_mun", columns="subsector", values="clee", aggfunc="size", fill_value=0)
           .add_prefix("sub_").reset_index())
    out = base.merge(sub, on="cve_mun", how="left")
    out["pct_del_estado"] = (100 * out["establecimientos"] / out["establecimientos"].sum()).round(2)
    return out


def comparativo_estados(cuant: pd.DataFrame) -> pd.DataFrame:
    """Estructura del comercio por estrato en Colima y estados vecinos (conteos agregados de Cuantificar)."""
    est = cuant[cuant["area"].isin(config.ESTADOS_COMPARACION)].copy()
    if est.empty:
        return pd.DataFrame()
    est["entidad"] = est["area"].map(config.ESTADOS_COMPARACION)
    tot = est[est["estrato"].eq(0)].groupby("entidad")["total"].sum().rename("establecimientos")
    por_estrato = (est[est["estrato"].gt(0)].pivot_table(index="entidad", columns="estrato", values="total",
                                                         aggfunc="sum", fill_value=0))
    por_estrato.columns = [f"pct_estrato_{c}" for c in por_estrato.columns]
    por_estrato = (100 * por_estrato.div(por_estrato.sum(axis=1), axis=0)).round(2)
    sub = est[est["estrato"].eq(0)].pivot_table(index="entidad", columns="subsector", values="total",
                                                aggfunc="sum", fill_value=0)
    sub = (100 * sub.div(sub.sum(axis=1), axis=0)).round(2).add_prefix("pct_sub_")
    out = pd.concat([tot, por_estrato, sub], axis=1).reset_index()
    out["region"] = "Occidente"
    out["fecha_ingesta"] = est["captura"].max()
    out["archivos_bronce"] = ";".join(sorted(est["ruta_bronce"].unique()))
    return out


def consistencia_con_cuantificar(ind: pd.DataFrame, cuant: pd.DataFrame) -> pd.DataFrame:
    """Contraste entre fuentes: puntos descargados vs. conteo oficial por municipio (estrato 0)."""
    c = cuant[cuant["estrato"].eq(0) & cuant["area"].str.len().eq(5)]
    tot = c.groupby(c["area"].str[2:])["total"].sum().rename("total_cuantificar")
    out = ind[["cve_mun", "municipio", "establecimientos"]].merge(tot, left_on="cve_mun", right_index=True, how="left")
    out["diferencia_pct"] = (100 * (out["establecimientos"] - out["total_cuantificar"]) / out["total_cuantificar"]).round(2)
    return out


# ====================================================================== GeoPandas
def _gpd():
    import geopandas as gpd  # import diferido: el resto del módulo funciona sin GeoPandas
    return gpd


def a_geodataframe(df: pd.DataFrame):
    gpd = _gpd()
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["lon"], df["lat"]),
                            crs=config.CRS_GEO).to_crs(config.CRS_METRICO)


def cargar_municipios(dir_ref: Path = config.REFERENCIA):
    """Capa opcional de límites municipales del Marco Geoestadístico de INEGI (06mun.shp o .gpkg/.geojson)."""
    gpd = _gpd()
    for patron in ("*mun*.gpkg", "*mun*.geojson", "*mun*.shp"):
        archivos = sorted(dir_ref.glob(patron))
        if archivos:
            capa = gpd.read_file(archivos[0]).to_crs(config.CRS_METRICO)
            col = next((c for c in ["CVE_MUN", "cve_mun", "CVEGEO"] if c in capa.columns), None)
            if col is None:
                return None
            capa["cve_mun"] = capa[col].astype(str).str[-3:].str.zfill(3)
            capa["area_km2"] = (capa.geometry.area / 1e6).round(2)
            return capa[["cve_mun", "area_km2", "geometry"]]
    return None


def malla_hexagonal(bounds, lado: float):
    """Hexágonos de cara plana que cubren la caja (minx, miny, maxx, maxy) en metros."""
    from shapely.geometry import Polygon
    gpd = _gpd()
    minx, miny, maxx, maxy = bounds
    ancho, alto = 2 * lado, math.sqrt(3) * lado
    dx, dy = 1.5 * lado, alto
    vertices = [(lado * math.cos(math.radians(a)), lado * math.sin(math.radians(a))) for a in range(0, 360, 60)]
    poligonos, ids = [], []
    col = 0
    x = minx
    while x <= maxx + ancho:
        y = miny - (alto / 2 if col % 2 else 0)
        fila = 0
        while y <= maxy + alto:
            poligonos.append(Polygon([(x + vx, y + vy) for vx, vy in vertices]))
            ids.append(f"H{col:03d}_{fila:03d}")
            y += dy
            fila += 1
        x += dx
        col += 1
    return gpd.GeoDataFrame({"hex_id": ids}, geometry=poligonos, crs=config.CRS_METRICO)


def contar_en_hexagonos(puntos, lado: float = config.LADO_HEX_M):
    gpd = _gpd()
    malla = malla_hexagonal(puntos.total_bounds, lado)
    unidos = gpd.sjoin(puntos[["clee", "id_bronce", "captura", "ruta_bronce", "geometry"]], malla,
                       how="inner", predicate="within")
    conteo = unidos.groupby("hex_id").agg(establecimientos=("clee", "size"),
                                          fecha_ingesta=("captura", "max"),
                                          archivos_bronce=("ruta_bronce", lambda s: ";".join(sorted(set(s)))))
    hexes = malla.merge(conteo, on="hex_id", how="inner")
    hexes["suprimido"] = hexes["establecimientos"] < config.UMBRAL_SUPRESION
    hexes.loc[hexes["suprimido"], "establecimientos"] = np.nan     # privacidad: no se publica el conteo
    area_km2 = 1.5 * math.sqrt(3) * (lado / 1000) ** 2
    hexes["por_km2"] = (hexes["establecimientos"] / area_km2).round(2)
    hexes["id_fila_oro"] = hexes["hex_id"].map(lambda h: id_estable("comercio_hexagonos", h))
    return hexes, unidos[["hex_id", "clee", "id_bronce"]]


def mapas(hexes, municipios_ind: pd.DataFrame, capa_mun, destino: Path) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    destino.mkdir(parents=True, exist_ok=True)
    salidas = []

    fig, ax = plt.subplots(figsize=(9, 8))
    visibles = hexes[~hexes["suprimido"]]
    visibles.plot(ax=ax, column="por_km2", cmap="viridis", legend=True, linewidth=0,
                  legend_kwds={"label": "Establecimientos por km² (hexágonos de 1 km de lado)", "shrink": .6})
    hexes[hexes["suprimido"]].plot(ax=ax, color="lightgrey", linewidth=0)
    if capa_mun is not None:
        capa_mun.boundary.plot(ax=ax, color="black", linewidth=.6)
    ax.set_title("Comercio al por menor en Colima — densidad de establecimientos (DENUE)")
    ax.set_axis_off()
    ax.annotate("Gris: celdas con menos de 3 establecimientos (suprimidas por privacidad).\n"
                "Fuente: INEGI, DENUE. Proyección EPSG:6372.", (0, -0.02), xycoords="axes fraction",
                fontsize=8, va="top")
    p = destino / "mapa_densidad_hexagonos.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    salidas.append(p)

    fig, ax = plt.subplots(figsize=(9, 6))
    if capa_mun is not None:
        m = capa_mun.merge(municipios_ind, on="cve_mun", how="left")
        m["densidad"] = m["establecimientos"] / m["area_km2"]
        m.plot(ax=ax, column="densidad", cmap="YlOrRd", legend=True, edgecolor="black", linewidth=.5,
               legend_kwds={"label": "Establecimientos por km²", "shrink": .6})
        for _, r in m.iterrows():
            ax.annotate(r["municipio"], r.geometry.representative_point().coords[0], ha="center", fontsize=7)
        ax.set_axis_off()
        ax.set_title("Densidad de comercio al por menor por municipio")
    else:
        s = municipios_ind.sort_values("establecimientos")
        ax.barh(s["municipio"], s["establecimientos"], color="#3b6ea5")
        ax.set_xlabel("Establecimientos (sector 46)")
        ax.set_title("Establecimientos de comercio al por menor por municipio\n"
                     "(agrega los límites del Marco Geoestadístico para verlo como mapa)")
    p = destino / "mapa_municipios.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    salidas.append(p)

    try:
        html = destino / "mapa_interactivo.html"
        visibles.to_crs(config.CRS_GEO).explore(column="por_km2", cmap="viridis",
                                                tooltip=["hex_id", "establecimientos", "por_km2"]).save(html)
        salidas.append(html)
    except Exception as e:  # noqa: BLE001 - folium es opcional
        log.info("Mapa interactivo omitido (%s)", e)
    return salidas


# ====================================================================== orquestador
def correr(bronce: Path = config.BRONCE, salida: Path = config.DATOS, img: Path = config.IMG) -> dict:
    for c in ("plata", "oro", "cuarentena", "reportes"):
        (salida / c).mkdir(parents=True, exist_ok=True)
    crudo = leer_establecimientos(bronce)
    if crudo.empty:
        raise FileNotFoundError(f"No hay capturas del DENUE en {bronce / 'denue'}")
    crudo["ruta_bronce"] = _prefijo(bronce) + crudo["ruta_bronce"]   # ruta relativa a la raíz del repo
    tipado = tipar(crudo)
    # Duplicados EXACTOS (misma fila repetida por la paginación): se conserva la primera aparición y
    # la copia va a cuarentena con su motivo; nada se elimina en silencio.
    dup = tipado.duplicated(keep="first")
    if dup.any():
        copias = tipado[dup].assign(motivo="Duplicado exacto de otra fila; se conserva la primera aparición",
                                    regla="duplicado_exacto", columna="(fila)",
                                    corrida_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
        destino = salida / "cuarentena" / "cuarentena_denue.csv"
        copias.to_csv(destino, mode="a", header=not destino.exists(), index=False)
    validos, cuarentena, puerta = aplicar_puerta(tipado[~dup], salida / "cuarentena")
    puerta["duplicados_exactos"] = int(dup.sum())
    log.info("Puerta DENUE: %d válidos, %d a cuarentena", puerta["validos"], puerta["cuarentena"])

    validos["dist_competidor_m"] = distancia_competidor(validos).round(1)
    validos.insert(0, "id_registro", validos["id_bronce"].map(lambda x: id_estable("denue", x)))
    validos.to_csv(salida / "plata" / "denue_establecimientos.csv", index=False)

    cuant = leer_cuantificar(bronce)
    ind = indicadores_municipio(validos)
    consist = consistencia_con_cuantificar(ind, cuant) if len(cuant) else pd.DataFrame()
    if len(consist):
        ind = ind.merge(consist[["cve_mun", "total_cuantificar", "diferencia_pct"]], on="cve_mun", how="left")

    # Linaje por fila de municipio
    lin_mun = validos[["cve_mun", "clee", "id_bronce", "ruta_bronce", "sha256_bronce", "captura"]].copy()
    lin_mun["id_fila_oro"] = lin_mun["cve_mun"].map(lambda m: id_estable("comercio_municipios", m))
    lin_mun["tabla"] = "comercio_municipios"
    resumen_mun = lin_mun.groupby("cve_mun").agg(
        id_fila_oro=("id_fila_oro", "first"), fecha_ingesta=("captura", "max"),
        archivos_bronce=("ruta_bronce", lambda s: ";".join(sorted(set(s)))))
    ind = resumen_mun.reset_index().merge(ind, on="cve_mun")

    comp = comparativo_estados(cuant) if len(cuant) else pd.DataFrame()
    if len(comp):
        comp.insert(0, "id_fila_oro", comp["entidad"].map(lambda e: id_estable("comparativo_estados", e)))

    reporte = {"puerta": puerta, "municipios": int(len(ind)), "consistencia_cuantificar": consist.to_dict("records")}
    lineas_linaje = [lin_mun]

    try:
        gpd = _gpd()
        puntos = a_geodataframe(validos)
        capa_mun = cargar_municipios()
        if capa_mun is not None:
            cruce = gpd.sjoin(puntos[["clee", "cve_mun", "geometry"]], capa_mun[["cve_mun", "geometry"]],
                              how="left", predicate="within", lsuffix="denue", rsuffix="marco")
            reporte["municipio_espacial_coincide_pct"] = round(
                100 * float((cruce["cve_mun_denue"] == cruce["cve_mun_marco"]).mean()), 2)
            ind = ind.merge(capa_mun[["cve_mun", "area_km2"]], on="cve_mun", how="left")
            ind["establecimientos_por_km2"] = (ind["establecimientos"] / ind["area_km2"]).round(3)
            gpd.GeoDataFrame(capa_mun.merge(ind, on="cve_mun")).to_crs(config.CRS_GEO).to_file(
                salida / "oro" / "comercio_municipios.geojson", driver="GeoJSON")
        hexes, hex_puntos = contar_en_hexagonos(puntos)
        hexes.to_crs(config.CRS_GEO).to_file(salida / "oro" / "comercio_hexagonos.geojson", driver="GeoJSON")
        lin_hex = hex_puntos.merge(validos[["clee", "ruta_bronce", "sha256_bronce", "captura"]], on="clee")
        lin_hex["id_fila_oro"] = lin_hex["hex_id"].map(lambda h: id_estable("comercio_hexagonos", h))
        lin_hex["tabla"] = "comercio_hexagonos"
        lineas_linaje.append(lin_hex.drop(columns="hex_id"))
        reporte["hexagonos"] = {"total": int(len(hexes)), "suprimidos": int(hexes["suprimido"].sum())}
        reporte["mapas"] = [p.name for p in mapas(hexes, ind, capa_mun, img)]
        reporte["geopandas"] = True
    except ImportError:
        log.warning("GeoPandas no está instalado: se omiten hexágonos y mapas")
        reporte["geopandas"] = False

    ind.to_csv(salida / "oro" / "comercio_municipios.csv", index=False)
    if len(comp):
        comp.to_csv(salida / "oro" / "comparativo_estados.csv", index=False)
    linaje = pd.concat(lineas_linaje, ignore_index=True).rename(columns={"captura": "fecha_ingesta"})
    linaje[["tabla", "id_fila_oro", "clee", "id_bronce", "ruta_bronce", "sha256_bronce", "fecha_ingesta"]].to_csv(
        salida / "oro" / "linaje_geo.csv", index=False)
    reporte["linaje"] = {"filas": int(len(linaje)), "filas_oro_rastreadas": int(linaje["id_fila_oro"].nunique())}
    (salida / "reportes" / "reporte_geo.json").write_text(
        json.dumps(reporte, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return reporte


def _prefijo(bronce: Path) -> str:
    try:
        return Path(bronce).resolve().relative_to(config.REPO).as_posix() + "/"
    except ValueError:
        return Path(bronce).resolve().as_posix() + "/"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", action="store_true", help="Bronce sintética (no son datos reales)")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        if a.demo:
            from .demo_denue import generar
            with tempfile.TemporaryDirectory() as tmp:
                destino = config.PAQUETE / "data_demo"
                print(json.dumps(correr(generar(Path(tmp)), destino, destino / "img"), indent=1,
                                 ensure_ascii=False, default=str))
        else:
            correr()
    except FileNotFoundError as e:
        log.warning("%s", e)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
