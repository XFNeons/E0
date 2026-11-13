"""Integracion de fuentes heterogeneas: esquema comun, tipos y fusion."""
import re

import pandas as pd

from . import config as C
from .limpieza import a_numero, normalizar_texto


def _clave(c: str) -> str:
    """Encabezado comparable: sin acentos, mayusculas ni puntos."""
    return normalizar_texto(pd.Series([c])).iloc[0].replace(".", "").strip()


def cargar_fuente(nombre: str, carpeta_bronce) -> pd.DataFrame:
    """Lee todos los archivos de la fuente (detecta separador y codificacion)."""
    cfg = C.FUENTES[nombre]
    archivos = sorted(carpeta_bronce.glob(cfg["patron"]))
    if not archivos:
        raise FileNotFoundError(f"Sin archivos para la fuente {nombre}: {carpeta_bronce}/{cfg['patron']}")
    partes = []
    for a in archivos:
        for enc in ("utf-8-sig", "cp1252"):
            try:
                d = pd.read_csv(a, dtype=str, encoding=enc, sep=None, engine="python")
                break
            except UnicodeDecodeError:
                continue
        d["_archivo"] = a.name
        partes.append(d)
    return pd.concat(partes, ignore_index=True)


def estandarizar_esquema(df: pd.DataFrame, nombre: str) -> pd.DataFrame:
    """
    Esquema comun y tipos:
      - encabezados normalizados y renombrados,
      - fecha -> datetime (columna, o tomada del nombre del archivo),
      - claves de serie -> texto normalizado (sin acentos/mayusculas) + alias,
      - precios con '$', comas o 'N/D' -> float ('N/D' = faltante legitimo, NO error).
    Lo no convertible NO se borra: queda en `_motivo_previo` y la Puerta de Calidad lo
    manda a cuarentena.
    """
    cfg = C.FUENTES[nombre]
    df = df.rename(columns={c: _clave(c) for c in df.columns}).copy()
    ren = {_clave(k): v for k, v in cfg["renombrar"].items()}
    faltan = [k for k in ren if k not in df.columns]
    if faltan:
        raise KeyError(f"Fuente {nombre}: columnas {faltan} no existen en Bronce "
                       f"(hay: {list(df.columns)}). Ajusten config.FUENTES.")
    df = df.rename(columns=ren)
    df["_fuente"] = nombre
    df["_motivo_previo"] = ""

    col_f = _clave(cfg.get("col_fecha", "fecha"))
    if col_f in df.columns:
        crudo = df[col_f]
    elif cfg.get("fecha_en_archivo"):
        crudo = df["_archivo"].str.extract(cfg["fecha_en_archivo"])[0]
    else:
        raise KeyError(f"Fuente {nombre}: no hay columna de fecha '{col_f}' ni regla fecha_en_archivo.")
    f = pd.to_datetime(crudo, errors="coerce", format="mixed", dayfirst=cfg.get("dayfirst", False))
    df.loc[f.isna(), "_motivo_previo"] += "fecha no interpretable; "
    df["periodo"] = f.dt.normalize()

    for col in C.CLAVES_SERIE:
        df[col] = normalizar_texto(df[col])
        if col in C.ALIAS:
            df[col] = df[col].replace(C.ALIAS[col])
    df[C.GRUPO] = df[C.CLAVES_SERIE].fillna("?").agg(" | ".join, axis=1)

    for col in C.NUMERICAS:
        if col in df.columns:
            t = df[col].astype("string").str.strip()
            t = t.where(~t.str.lower().isin(C.NULOS), pd.NA)       # N/D -> faltante legitimo
            num = a_numero(t)
            malo = num.isna() & t.notna()
            df.loc[malo, "_motivo_previo"] += f"{col} no numerico; "
            df[col] = num
    return df


def integrar(fuentes: dict):
    """
    Left-join de las fuentes secundarias (si hay) sobre C.LLAVES, con la primera como base.
    Duplicados de llave en fuentes secundarias NO se borran en silencio: se conserva la mas
    reciente y las demas se devuelven como cuarentena con motivo.
    """
    nombres = list(fuentes)
    base = fuentes[nombres[0]].copy()
    cuarentena = []
    for n in nombres[1:]:
        d = fuentes[n].copy()
        dup = d.duplicated(C.LLAVES, keep="last")
        if dup.any():
            q = d[dup].copy()
            q["_motivo_cuarentena"] = f"duplicado de llave en fuente {n} (se conserva la ultima captura)"
            cuarentena.append(q)
        d = d[~dup]
        nuevas = [c for c in d.columns if c in C.NUMERICAS and c not in base.columns]
        d = d[C.LLAVES + nuevas + ["_motivo_previo"]].rename(columns={"_motivo_previo": f"_mp_{n}"})
        base = base.merge(d, on=C.LLAVES, how="left")
        base[f"_en_fuente_{n}"] = base[nuevas].notna().any(axis=1) if nuevas else False
        base["_motivo_previo"] = base["_motivo_previo"] + base.pop(f"_mp_{n}").fillna("")
    cuar = pd.concat(cuarentena, ignore_index=True) if cuarentena else pd.DataFrame()
    return base.reset_index(drop=True), cuar
