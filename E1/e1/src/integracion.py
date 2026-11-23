"""Lectura de Bronce e integración de fuentes heterogéneas (INEGI BIE y Banxico SIE).

Discrepancias que se resuelven aquí:
  * Esquema: INEGI entrega Series[0].OBSERVATIONS[{TIME_PERIOD, OBS_VALUE}];
             Banxico entrega bmx.series[0].datos[{fecha, dato}].
  * Formato de fecha: '2024/03' (INEGI, mensual) vs '15/03/2024' (Banxico, día/mes/año).
  * Tipo del valor: ambos llegan como texto; Banxico usa coma de miles ('1,234.56') y 'N/E'.
  * Frecuencia: Banxico es diaria y se agrega a mensual (promedio) -> reducción por agregación.
  * Revisiones: si la misma serie y periodo aparece en varias capturas con valores distintos
    (INEGI revisa cifras preliminares), gana la captura más reciente y el conflicto se registra.
  * Nombres: cada serie se mapea a (entidad, variable, unidad, fuente) con config.SERIES.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

COLUMNAS_LARGO = ["serie", "fuente", "entidad", "variable", "unidad", "fecha",
                  "valor_crudo", "valor", "captura", "archivo"]


# ------------------------------------------------------------------ lectura de Bronce
def _fecha_captura(archivo: Path) -> pd.Timestamp:
    """El extractor nombra los archivos AAAA-MM-DD_hhmmss.json."""
    return pd.to_datetime(archivo.stem, format="%Y-%m-%d_%H%M%S", errors="coerce")


def _filas_inegi(payload: dict) -> list[tuple[str, object]]:
    obs = (payload.get("Series") or [{}])[0].get("OBSERVATIONS") or []
    return [(o.get("TIME_PERIOD"), o.get("OBS_VALUE")) for o in obs]


def _filas_banxico(payload: dict) -> list[tuple[str, object]]:
    datos = ((payload.get("bmx") or {}).get("series") or [{}])[0].get("datos") or []
    return [(d.get("fecha"), d.get("dato")) for d in datos]


LECTORES = {"inegi": _filas_inegi, "banxico": _filas_banxico}


def leer_bronce(dir_bronce: Path) -> pd.DataFrame:
    """Lee TODAS las capturas crudas de Bronce a un formato largo, todavía como texto."""
    registros = []
    for fuente, lector in LECTORES.items():
        for archivo in sorted((dir_bronce / fuente).glob("*/*.json")):
            serie = archivo.parent.name
            payload = json.loads(archivo.read_text(encoding="utf-8"))
            for periodo, valor in lector(payload):
                registros.append({"serie": serie, "fuente": fuente, "periodo_crudo": periodo,
                                  "valor_crudo": None if valor is None else str(valor),
                                  "captura": _fecha_captura(archivo), "archivo": archivo.name})
    return pd.DataFrame(registros, columns=["serie", "fuente", "periodo_crudo", "valor_crudo",
                                            "captura", "archivo"])


# ------------------------------------------------------------------ tipado
def es_faltante_declarado(valor_crudo: pd.Series) -> pd.Series:
    """True si la fuente declaró el dato como no disponible (None, '', 'N/E', ...)."""
    texto = valor_crudo.astype("string").str.strip()
    return (texto.isna() | texto.isin(config.FALTANTES_DECLARADOS)).fillna(True).astype(bool)


def parsear_fecha(periodo: pd.Series, fuente: pd.Series) -> pd.Series:
    """Convierte '2024/03' (INEGI) y '15/03/2024' (Banxico) a Timestamp; inválidas -> NaT."""
    texto = periodo.astype("string").str.strip()
    inegi = pd.to_datetime(texto.where(fuente == "inegi"), format="%Y/%m", errors="coerce")
    banxico = pd.to_datetime(texto.where(fuente == "banxico"), format="%d/%m/%Y", errors="coerce")
    return inegi.fillna(banxico)


def parsear_valor(valor_crudo: pd.Series) -> pd.Series:
    """Texto -> float. Quita comas de miles. Los faltantes declarados y el texto no numérico
    quedan como NaN; la Puerta de Calidad distingue ambos casos usando valor_crudo."""
    texto = valor_crudo.astype("string").str.strip().str.replace(",", "", regex=False)
    return pd.to_numeric(texto, errors="coerce").astype("float64")


def tipar(crudo: pd.DataFrame) -> pd.DataFrame:
    df = crudo.copy()
    df["fecha"] = parsear_fecha(df["periodo_crudo"], df["fuente"])
    df["valor"] = parsear_valor(df["valor_crudo"])
    meta = pd.DataFrame.from_dict(config.SERIES, orient="index")
    df = df.join(meta, on="serie")
    # Series en Bronce que no están en el catálogo conservan nulos y la Puerta las rechaza.
    return df


# ------------------------------------------------------------------ resolución de conflictos
def resolver_revisiones(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Para cada (serie, fecha) conserva la captura más reciente. Devuelve también la tabla
    de conflictos (mismo periodo con valores distintos entre capturas) para documentarlos."""
    df = df.sort_values(["serie", "periodo_crudo", "captura"])
    llave = ["serie", "periodo_crudo"]
    distintos = df.groupby(llave)["valor_crudo"].transform("nunique") > 1
    conflictos = (df[distintos]
                  .groupby(llave)
                  .agg(valores=("valor_crudo", lambda s: " -> ".join(map(str, s))),
                       capturas=("captura", "count"))
                  .reset_index())
    ultimo = df.drop_duplicates(subset=llave, keep="last")
    return ultimo, conflictos


# ------------------------------------------------------------------ reducción por agregación
def a_mensual(df: pd.DataFrame) -> pd.DataFrame:
    """Series diarias (Banxico) -> promedio mensual. Series mensuales se normalizan al día 1.
    Solo agrega registros con fecha y valor válidos; los inválidos pasan intactos para que
    la Puerta de Calidad los envíe a cuarentena con su motivo."""
    df = df.copy()
    df["mes"] = df["fecha"].dt.to_period("M").dt.to_timestamp()
    es_diaria = df["fuente"].eq("banxico")
    valido = df["fecha"].notna() & df["valor"].notna()

    diarias_ok = df[es_diaria & valido]
    agregadas = (diarias_ok.groupby(["serie", "fuente", "entidad", "variable", "unidad", "mes"],
                                    dropna=False)
                 .agg(valor=("valor", "mean"), n_dias=("valor", "size"),
                      captura=("captura", "max"), archivo=("archivo", "last"))
                 .reset_index())
    agregadas["valor_crudo"] = agregadas["valor"].round(6).astype(str)
    agregadas["origen"] = "promedio_mensual_de_" + agregadas["n_dias"].astype(str) + "_dias"

    # Un día no numérico de Banxico no se promedia: se manda a la Puerta para quedar registrado.
    # Los días con faltante declarado ('N/E') simplemente no entran al promedio.
    diarias_malas = df[es_diaria & ~valido & ~es_faltante_declarado(df["valor_crudo"])].copy()
    diarias_malas["origen"] = "dato_diario_invalido"
    diarias_malas["mes"] = diarias_malas["fecha"]   # conserva el día exacto para rastrearlo

    mensuales = df[~es_diaria].copy()
    mensuales["origen"] = "dato_mensual"
    mensuales["mes"] = mensuales["mes"].where(mensuales["fecha"].notna())

    salida = pd.concat([mensuales, diarias_malas, agregadas], ignore_index=True)
    salida["fecha"] = salida["mes"]
    return salida.drop(columns=["mes", "n_dias", "periodo_crudo"], errors="ignore")


def completar_calendario(df: pd.DataFrame) -> pd.DataFrame:
    """Hace explícitos los meses ausentes dentro del rango de cada serie (faltantes implícitos),
    para que el diagnóstico de faltantes los vea."""
    piezas = []
    for serie, g in df[df["fecha"].notna()].groupby("serie"):
        meses = pd.date_range(g["fecha"].min(), g["fecha"].max(), freq="MS")
        faltan = meses.difference(pd.DatetimeIndex(g["fecha"]))
        if len(faltan):
            base = g.iloc[0]
            piezas.append(pd.DataFrame({
                "serie": serie, "fuente": base["fuente"], "entidad": base["entidad"],
                "variable": base["variable"], "unidad": base["unidad"], "fecha": faltan,
                "valor_crudo": None, "valor": np.nan, "captura": pd.NaT,
                "archivo": "", "origen": "mes_ausente_en_fuente"}))
    return pd.concat([df, *piezas], ignore_index=True) if piezas else df


def integrar(dir_bronce: Path) -> tuple[pd.DataFrame, dict]:
    """Bronce -> tabla larga unificada, lista para la Puerta de Calidad."""
    crudo = leer_bronce(dir_bronce)
    if crudo.empty:
        raise FileNotFoundError(f"No hay capturas en {dir_bronce}. Corre primero el extractor de E0 "
                                "o usa --demo.")
    tipado = tipar(crudo)
    unico, conflictos = resolver_revisiones(tipado)
    mensual = completar_calendario(a_mensual(unico))
    mensual = mensual.sort_values(["serie", "fecha"]).reset_index(drop=True)
    resumen = {
        "registros_bronce": int(len(crudo)),
        "capturas_leidas": int(crudo[["serie", "archivo"]].drop_duplicates().shape[0]),
        "series": sorted(crudo["serie"].unique().tolist()),
        "conflictos_de_revision": int(len(conflictos)),
        "registros_integrados": int(len(mensual)),
    }
    return mensual, {"resumen": resumen, "conflictos": conflictos}
