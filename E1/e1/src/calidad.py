"""Puerta de Calidad (Pandera). Los registros invalidos van a cuarentena CON motivo."""
import pandas as pd

try:
    import pandera.pandas as pa
except ImportError:  # pandera < 0.24
    import pandera as pa

from . import config as C


def construir_esquema() -> "pa.DataFrameSchema":
    cols = {"periodo": pa.Column("datetime64[ns]", coerce=True, nullable=False,
                                 checks=pa.Check.ge(pd.Timestamp(C.PERIODO_MIN)))}
    for k in C.CLAVES_SERIE:
        permitidos = C.VALIDOS.get(k)
        cols[k] = pa.Column(str, nullable=False, checks=pa.Check.isin(permitidos) if permitidos else [])
    for col, (lo, hi) in C.RANGOS.items():
        cols[col] = pa.Column(float, coerce=True, nullable=True,
                              checks=pa.Check.in_range(lo, hi, include_min=True, include_max=True))
    return pa.DataFrameSchema(cols, strict=False, unique=C.LLAVES, report_duplicates="exclude_first")


def puerta_de_calidad(df: pd.DataFrame):
    """
    Devuelve (validos, cuarentena, resumen_motivos). Reglas, en orden:
      1) fallos de conversion previos (_motivo_previo)
      2) llaves duplicadas (se conserva la primera aparicion)
      3) coherencia entre columnas (C.COHERENCIA, p. ej. precio_min <= precio_frec <= precio_max)
      4) esquema y rangos de Pandera (validacion lazy: reporta TODOS los fallos)
    """
    df = df.reset_index(drop=True).copy()
    motivos = {i: [] for i in df.index}

    for i, m in df["_motivo_previo"].items():
        if m:
            motivos[i] += [x.strip() for x in m.split(";") if x.strip()]

    dup = df.duplicated(C.LLAVES, keep="first") & df["periodo"].notna() & df[C.CLAVES_SERIE].notna().all(axis=1)
    for i in df.index[dup]:
        motivos[i].append("duplicado de llave (fecha+serie) en fuente base")

    for a, b in C.COHERENCIA:
        mal = df[a].notna() & df[b].notna() & (df[a] > df[b])
        for i in df.index[mal]:
            motivos[i].append(f"incoherencia: {a} > {b}")

    candidatos = df[[not motivos[i] for i in df.index]]
    try:
        construir_esquema().validate(candidatos, lazy=True)
    except pa.errors.SchemaErrors as e:
        fc = e.failure_cases
        sin_indice = fc[fc["index"].isna()]
        if len(sin_indice):
            raise RuntimeError("Fallo estructural del esquema (columna faltante/tipo):\n"
                               + sin_indice[["column", "check", "failure_case"]].to_string())
        for _, r in fc.iterrows():
            motivos[int(r["index"])].append(f"{r['column']}: falla '{r['check']}' (valor={r['failure_case']})")

    invalido = pd.Series({i: bool(m) for i, m in motivos.items()})
    cuar = df[invalido.values].copy()
    cuar["_motivo_cuarentena"] = ["; ".join(motivos[i]) for i in cuar.index]
    validos = df[~invalido.values].drop(columns=["_motivo_previo"]).reset_index(drop=True)

    resumen = {}
    for i in cuar.index:
        for m in motivos[i]:
            clave = m.split(" (valor=")[0]
            resumen[clave] = resumen.get(clave, 0) + 1
    return validos, cuar, resumen
