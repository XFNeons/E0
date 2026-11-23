"""Linaje y trazabilidad: Oro -> Plata -> Bronce.

Cada fila de Oro recibe:
  * id_fila_oro      identificador estable de la fila (tabla + llaves)
  * fecha_ingesta    fecha UTC de la captura Bronce más reciente que alimenta la fila
  * archivos_bronce  archivos crudos de los que sale la fila (separados por ';')

Y data/oro/linaje_oro.csv guarda el detalle celda por celda:
  columna de Oro -> registro de Plata (id_registro) -> archivo y periodo en Bronce (id_bronce),
  huella SHA-256 del archivo, fecha de ingesta y método (observado, imputado, atípico reemplazado).

Uso del rastreador (desde E1/e1):
    python -m src.linaje panel_colima_mensual 2024-03-01
    python -m src.linaje panel_entidades 2024-03-01 --entidad Jalisco
    python -m src.linaje --verificar          # comprueba que cada archivo Bronce existe y no cambió
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd

from . import config

# columna de Oro -> [(columna del ancho de Plata, rezago en meses)], transformación aplicada
DICCIONARIO_COLIMA: dict[str, tuple[list[tuple[str, int]], str]] = {
    "ingresos_colima": ([("ingresos_colima", 0)], "limpieza (atípicos e imputación)"),
    "personal_colima": ([("personal_colima", 0)], "limpieza (atípicos e imputación)"),
    "remuneraciones_colima": ([("remuneraciones_colima", 0)], "limpieza (atípicos e imputación)"),
    "inpc": ([("inpc", 0)], "limpieza"),
    "tiie": ([("tiie", 0)], "promedio mensual de datos diarios + limpieza"),
    "tipo_cambio": ([("tipo_cambio", 0)], "promedio mensual de datos diarios + limpieza"),
    "ingresos_crec_anual": ([("ingresos_colima", 0), ("ingresos_colima", 12)],
                            "100 * (x_t / x_{t-12} - 1)"),
    "inflacion_anual": ([("inpc", 0), ("inpc", 12)], "100 * (inpc_t / inpc_{t-12} - 1)"),
}


def id_estable(*partes) -> str:
    return hashlib.sha1("|".join(map(str, partes)).encode()).hexdigest()[:16]


def asignar_id_registro(plata: pd.DataFrame) -> pd.DataFrame:
    plata = plata.copy()
    plata.insert(0, "id_registro", [id_estable(s, f, b) for s, f, b in
                                    zip(plata["serie"], plata["fecha"], plata["id_bronce"])])
    return plata


def _celdas_colima(panel: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for fecha in panel["fecha"]:
        for col_oro, (fuentes, transf) in DICCIONARIO_COLIMA.items():
            if col_oro not in panel.columns:
                continue
            for col_ancho, rezago in fuentes:
                filas.append({"tabla": "panel_colima_mensual", "fecha": fecha, "entidad": "Colima",
                              "columna_oro": col_oro, "col_ancho": col_ancho,
                              "fecha_fuente": fecha - pd.DateOffset(months=rezago),
                              "transformacion": transf})
    return pd.DataFrame(filas)


def _celdas_entidades(panel: pd.DataFrame) -> pd.DataFrame:
    sufijo = {"Colima": "colima", "Jalisco": "jalisco", "Michoacán": "michoacan", "Nayarit": "nayarit"}
    filas = []
    for _, r in panel.iterrows():
        suf = sufijo.get(r["entidad"], "")
        mapa = {"ingresos": [(f"ingresos_{suf}", 0)],
                "personal": [(f"personal_{suf}", 0)],
                "remuneraciones": [(f"remuneraciones_{suf}", 0)],
                "ingresos_crec_anual": [(f"ingresos_{suf}", 0), (f"ingresos_{suf}", 12)]}
        for col_oro, fuentes in mapa.items():
            if col_oro not in panel.columns or pd.isna(r.get(col_oro)):
                continue
            for col_ancho, rezago in fuentes:
                filas.append({"tabla": "panel_entidades", "fecha": r["fecha"], "entidad": r["entidad"],
                              "columna_oro": col_oro, "col_ancho": col_ancho,
                              "fecha_fuente": r["fecha"] - pd.DateOffset(months=rezago),
                              "transformacion": "limpieza" if rezago == 0 else "crecimiento anual"})
    return pd.DataFrame(filas)


def _vecinos_observados(plata: pd.DataFrame, llaves: pd.DataFrame) -> pd.DataFrame:
    """Para cada (serie, fecha_fuente) pedida: el registro observado anterior y posterior en Plata
    (de ellos sale un valor imputado, aunque el registro original esté en cuarentena)."""
    obs = plata[plata["id_bronce"].fillna("").ne("") & plata["valor"].notna()]
    salida = []
    for serie, g in llaves.drop_duplicates().dropna().sort_values("fecha_fuente").groupby("serie"):
        o = obs[obs["serie"].eq(serie)].sort_values("fecha")[["fecha", "id_bronce"]]
        o = o.rename(columns={"fecha": "fecha_fuente"})
        prev = pd.merge_asof(g, o.rename(columns={"id_bronce": "vecino_anterior"}), on="fecha_fuente",
                             direction="backward", allow_exact_matches=False)
        nxt = pd.merge_asof(g, o.rename(columns={"id_bronce": "vecino_posterior"}), on="fecha_fuente",
                            direction="forward", allow_exact_matches=False)
        salida.append(prev.assign(vecino_posterior=nxt["vecino_posterior"].to_numpy()))
    return pd.concat(salida, ignore_index=True) if salida else pd.DataFrame(
        columns=["serie", "fecha_fuente", "vecino_anterior", "vecino_posterior"])


def prefijo_bronce(dir_bronce: Path) -> str:
    """Ruta de la carpeta Bronce relativa a la raíz del repo (o absoluta si está fuera, p. ej. en --demo)."""
    try:
        return Path(dir_bronce).resolve().relative_to(config.REPO).as_posix() + "/"
    except ValueError:
        return Path(dir_bronce).resolve().as_posix() + "/"


def construir_linaje(tablas: dict[str, pd.DataFrame], plata: pd.DataFrame, metodos: pd.DataFrame,
                     nombre_columna: dict[str, str], prefijo: str = "E0/data/bronze/"
                     ) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Devuelve las tablas de Oro con columnas de linaje por fila y la tabla de linaje por celda."""
    serie_de = {v: k for k, v in nombre_columna.items()}
    celdas = []
    if "panel_colima_mensual" in tablas and len(tablas["panel_colima_mensual"]):
        celdas.append(_celdas_colima(tablas["panel_colima_mensual"]))
    if "panel_entidades" in tablas and len(tablas["panel_entidades"]):
        celdas.append(_celdas_entidades(tablas["panel_entidades"]))
    celdas = pd.concat(celdas, ignore_index=True) if celdas else pd.DataFrame()
    if celdas.empty:
        return tablas, celdas

    celdas["serie"] = celdas["col_ancho"].map(serie_de)
    met = (metodos.rename_axis("fecha").reset_index()
           .melt(id_vars="fecha", var_name="col_ancho", value_name="metodo"))
    celdas = celdas.merge(met.rename(columns={"fecha": "fecha_fuente"}), on=["col_ancho", "fecha_fuente"], how="left")
    cols_plata = ["id_registro", "serie", "fecha", "id_bronce", "ruta_bronce", "sha256_bronce", "captura", "origen"]
    celdas = celdas.merge(plata[cols_plata].rename(columns={"fecha": "fecha_fuente", "captura": "fecha_ingesta"}),
                          on=["serie", "fecha_fuente"], how="left")
    vecinos = _vecinos_observados(plata, celdas[["serie", "fecha_fuente"]])
    celdas = celdas.merge(vecinos, on=["serie", "fecha_fuente"], how="left")
    sin_plata = celdas["id_registro"].isna()
    celdas.loc[sin_plata, "origen"] = "sin_registro_valido_en_plata (revisar cuarentena)"
    imputada = ~celdas["metodo"].fillna("").isin(["observado", ""])
    celdas.loc[~imputada, ["vecino_anterior", "vecino_posterior"]] = None

    celdas["id_fila_oro"] = [id_estable(t, f.date(), e) for t, f, e in
                             zip(celdas["tabla"], celdas["fecha"], celdas["entidad"])]
    celdas["ruta_bronce"] = celdas["ruta_bronce"].where(celdas["ruta_bronce"].fillna("").eq(""),
                                                        prefijo + celdas["ruta_bronce"].fillna(""))
    columnas = ["tabla", "id_fila_oro", "fecha", "entidad", "columna_oro", "transformacion", "fecha_fuente",
                "serie", "metodo", "id_registro", "id_bronce", "ruta_bronce", "sha256_bronce", "fecha_ingesta",
                "origen", "vecino_anterior", "vecino_posterior"]
    celdas = celdas[columnas].sort_values(["tabla", "fecha", "entidad", "columna_oro"]).reset_index(drop=True)

    # Resumen por fila, que se pega a cada tabla de Oro
    resumen = (celdas.groupby(["tabla", "fecha", "entidad"])
               .agg(id_fila_oro=("id_fila_oro", "first"), fecha_ingesta=("fecha_ingesta", "max"),
                    archivos_bronce=("ruta_bronce", lambda s: ";".join(sorted({x for x in s if isinstance(x, str) and x}))))
               .reset_index())
    salida = {}
    for nombre, tabla in tablas.items():
        r = resumen[resumen["tabla"].eq(nombre)].drop(columns="tabla")
        if tabla.empty:
            salida[nombre] = tabla
            continue
        llaves = ["fecha", "entidad"]
        t = tabla.drop(columns=[c for c in ["id_fila_oro", "fecha_ingesta", "archivos_bronce"] if c in tabla])
        t = t.merge(r, on=llaves, how="left")
        t["id_fila_oro"] = t["id_fila_oro"].fillna(pd.Series(
            [id_estable(nombre, f.date(), e) for f, e in zip(t["fecha"], t["entidad"])], index=t.index))
        salida[nombre] = t[["id_fila_oro", "fecha_ingesta", "archivos_bronce"] +
                           [c for c in t.columns if c not in ("id_fila_oro", "fecha_ingesta", "archivos_bronce")]]
    return salida, celdas


# ------------------------------------------------------------------ verificación y rastreador
def verificar(linaje: pd.DataFrame, raiz_repo: Path = config.REPO) -> pd.DataFrame:
    """Comprueba que cada archivo Bronce citado existe y que su SHA-256 no cambió."""
    problemas = []
    pares = linaje[linaje["ruta_bronce"].fillna("").ne("")][["ruta_bronce", "sha256_bronce"]].drop_duplicates()
    for ruta, huella in pares.itertuples(index=False):
        archivo = Path(ruta) if Path(ruta).is_absolute() else raiz_repo / ruta
        if not archivo.exists():
            problemas.append({"ruta_bronce": ruta, "problema": "no existe"})
        elif hashlib.sha256(archivo.read_bytes()).hexdigest() != huella:
            problemas.append({"ruta_bronce": ruta, "problema": "el contenido cambió (SHA-256 distinto)"})
    return pd.DataFrame(problemas, columns=["ruta_bronce", "problema"])


def rastrear(linaje: pd.DataFrame, tabla: str, fecha: str, entidad: str = "Colima") -> pd.DataFrame:
    sel = linaje[linaje["tabla"].eq(tabla) & (pd.to_datetime(linaje["fecha"]) == pd.Timestamp(fecha))
                 & linaje["entidad"].eq(entidad)]
    return sel[["columna_oro", "transformacion", "fecha_fuente", "metodo", "id_registro",
                "id_bronce", "fecha_ingesta", "vecino_anterior", "vecino_posterior"]]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tabla", nargs="?")
    ap.add_argument("fecha", nargs="?")
    ap.add_argument("--entidad", default="Colima")
    ap.add_argument("--verificar", action="store_true")
    ap.add_argument("--datos", type=Path, default=config.PAQUETE / "data")
    a = ap.parse_args(argv)
    linaje = pd.read_csv(a.datos / "oro" / "linaje_oro.csv", parse_dates=["fecha", "fecha_fuente"])
    if a.verificar:
        p = verificar(linaje)
        print("Linaje íntegro: todos los archivos Bronce existen y no cambiaron." if p.empty else p.to_string())
        return 0 if p.empty else 1
    if not (a.tabla and a.fecha):
        ap.error("indica tabla y fecha, o --verificar")
    with pd.option_context("display.max_colwidth", 70, "display.width", 200):
        print(rastrear(linaje, a.tabla, a.fecha, a.entidad).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
