"""Puerta de Calidad automática (Pandera) con cuarentena.

Regla del proyecto: ningún registro se borra en silencio. Cada fila que falla una regla se
escribe en data/cuarentena/ con el motivo, la regla (check), el valor que falló y la hora de
la corrida. Solo las filas que pasan TODAS las reglas llegan a la capa Plata.

Si la falla es de esquema (falta una columna, columna inesperada), no se puede saber qué filas
son válidas: la Puerta se cierra, no se escribe Plata y la corrida falla.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

try:                                   # pandera >= 0.24
    import pandera.pandas as pa
except ImportError:                    # pandera < 0.24
    import pandera as pa
from pandera.errors import SchemaErrors

from . import config
from .integracion import es_faltante_declarado


class PuertaCerrada(RuntimeError):
    """Falla de esquema: el lote completo no puede pasar a Plata."""


# ------------------------------------------------------------------ reglas de fila
def _valor_numerico_o_faltante(df: pd.DataFrame) -> pd.Series:
    """El texto original debe ser un número o un faltante declarado por la fuente ('N/E')."""
    return df["valor"].notna() | es_faltante_declarado(df["valor_crudo"])


def _valor_en_rango_de_su_variable(df: pd.DataFrame) -> pd.Series:
    lim = df["variable"].map(config.RANGOS)
    bajo = lim.map(lambda t: t[0] if isinstance(t, tuple) else float("nan"))
    alto = lim.map(lambda t: t[1] if isinstance(t, tuple) else float("nan"))
    return df["valor"].isna() | df["valor"].between(bajo, alto)


def _unidad_consistente(df: pd.DataFrame) -> pd.Series:
    esperada = df["serie"].map({k: v["unidad"] for k, v in config.SERIES.items()})
    return df["unidad"].eq(esperada)


def _linaje_completo(df: pd.DataFrame) -> pd.Series:
    """Todo valor observado debe apuntar a su archivo Bronce y a su fecha de ingesta.
    Solo los meses que la fuente no publicó (origen = mes_ausente_en_fuente) no tienen origen."""
    tiene = (df["id_bronce"].fillna("").astype(str).str.len() > 0) & df["captura"].notna()
    return tiene | df["origen"].eq("mes_ausente_en_fuente")


MOTIVOS = {
    "linaje_completo": "El registro no tiene archivo Bronce de origen o fecha de ingesta",
    "valor_numerico_o_faltante": "El valor original no es numérico ni un faltante declarado por la fuente",
    "valor_en_rango_de_su_variable": "Valor fuera del rango plausible definido para su variable",
    "unidad_consistente": "La unidad no coincide con la del catálogo de la serie",
    "multiple_fields_uniqueness": "Registro duplicado para la misma serie y mes",
    "not_nullable": "Campo obligatorio vacío",
    "isin": "Valor fuera del catálogo permitido",
    "in_range": "Fecha fuera del rango permitido",
    "greater_than_or_equal_to": "Valor por debajo del mínimo",
    "less_than_or_equal_to": "Valor por encima del máximo",
}


def construir_esquema(hoy: pd.Timestamp | None = None) -> pa.DataFrameSchema:
    hoy = hoy or pd.Timestamp.today().normalize()
    return pa.DataFrameSchema(
        columns={
            "serie": pa.Column(str, pa.Check.isin(list(config.SERIES)), nullable=False),
            "fuente": pa.Column(str, pa.Check.isin(["inegi", "banxico"]), nullable=False),
            "entidad": pa.Column(str, pa.Check.isin(list(config.REGION)), nullable=False),
            "variable": pa.Column(str, pa.Check.isin(list(config.RANGOS)), nullable=False),
            "unidad": pa.Column(str, nullable=False),
            "fecha": pa.Column("datetime64[ns]",
                               pa.Check.in_range(pd.Timestamp(config.FECHA_MIN), hoy),
                               nullable=False),
            "valor_crudo": pa.Column(nullable=True),          # texto tal como llegó, sin coerción
            "valor": pa.Column(float, nullable=True),          # los faltantes se imputan después
            "captura": pa.Column("datetime64[ns]", nullable=True),
            "archivo": pa.Column(str, nullable=True),
            "ruta_bronce": pa.Column(str, nullable=True),     # linaje: archivo crudo de origen
            "sha256_bronce": pa.Column(str, nullable=True),   # linaje: huella del archivo
            "id_bronce": pa.Column(str, nullable=True),       # linaje: archivo + periodo
            "origen": pa.Column(str, nullable=False),
        },
        checks=[
            pa.Check(_valor_numerico_o_faltante, name="valor_numerico_o_faltante"),
            pa.Check(_valor_en_rango_de_su_variable, name="valor_en_rango_de_su_variable"),
            pa.Check(_unidad_consistente, name="unidad_consistente"),
            pa.Check(_linaje_completo, name="linaje_completo"),
        ],
        unique=["serie", "fecha"],
        strict=True,
        coerce=True,
        name="puerta_plata",
    )


def _motivo(check: str) -> str:
    base = str(check).split("(")[0]
    return MOTIVOS.get(base, MOTIVOS.get(str(check), str(check)))


def aplicar_puerta(df: pd.DataFrame, rutas: config.Rutas | None = None,
                   hoy: pd.Timestamp | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Valida el lote completo (lazy=True: junta todas las fallas, no solo la primera).
    Devuelve (validos, cuarentena, resumen) y, si se dan rutas, escribe la cuarentena."""
    esquema = construir_esquema(hoy)
    corrida = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    df = df.reset_index(drop=True)

    try:
        validos = esquema.validate(df, lazy=True)
        fallas = pd.DataFrame(columns=["index", "column", "check", "failure_case"])
    except SchemaErrors as err:
        fallas = err.failure_cases.copy()
        de_esquema = fallas[fallas["index"].isna()]
        if not de_esquema.empty:
            detalle = de_esquema[["column", "check", "failure_case"]].to_dict("records")
            raise PuertaCerrada(f"Falla de esquema, no se escribe Plata: {detalle}") from err
        fallas["index"] = fallas["index"].astype(int)
        malos = sorted(fallas["index"].unique())
        validos = esquema.validate(df.drop(index=malos), lazy=False)

    if fallas.empty:
        cuarentena = df.iloc[0:0].assign(motivo=pd.Series(dtype=str), regla=pd.Series(dtype=str),
                                         columna=pd.Series(dtype=str), valor_que_fallo=pd.Series(dtype=str))
    else:
        fallas["motivo"] = fallas["check"].map(_motivo)
        texto = lambda col: col.map(lambda v: "" if v is None or (isinstance(v, float) and pd.isna(v))
                                    else str(v))
        por_fila = (fallas.assign(columna=texto(fallas["column"]).replace("", "(fila)"),
                                  check=texto(fallas["check"]),
                                  failure_case=texto(fallas["failure_case"]))
                    .groupby("index")
                    .agg(motivo=("motivo", lambda s: " | ".join(dict.fromkeys(s))),
                         regla=("check", lambda s: " | ".join(dict.fromkeys(s))),
                         columna=("columna", lambda s: " | ".join(dict.fromkeys(s))),
                         valor_que_fallo=("failure_case", lambda s: " | ".join(dict.fromkeys(s)))))
        cuarentena = df.loc[por_fila.index].join(por_fila)
    cuarentena = cuarentena.assign(corrida_utc=corrida)

    resumen = {
        "corrida_utc": corrida,
        "registros_evaluados": int(len(df)),
        "registros_validos": int(len(validos)),
        "registros_en_cuarentena": int(len(cuarentena)),
        "tasa_aprobacion": round(len(validos) / len(df), 4) if len(df) else None,
        "cuarentena_por_regla": (fallas["check"].astype(str).map(lambda c: c.split("(")[0])
                                 .value_counts().to_dict() if not fallas.empty else {}),
    }

    if rutas is not None and len(cuarentena):
        destino = rutas.cuarentena / "cuarentena.csv"
        # append-only: la cuarentena acumula todas las corridas; nunca se sobrescribe
        cuarentena.to_csv(destino, mode="a", header=not destino.exists(), index=False)
        resumen["archivo_cuarentena"] = str(Path(destino).name)
    return validos.reset_index(drop=True), cuarentena, resumen
