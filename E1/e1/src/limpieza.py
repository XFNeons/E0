"""Limpieza estadistica: faltantes, atipicos, normalizacion, discretizacion, reduccion.
Todo se calcula DENTRO de cada serie (producto/calidad/presentacion/origen): los precios de
productos distintos no son comparables entre si."""
import unicodedata

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.feature_selection import VarianceThreshold

from . import config as C


# ------------------------------------------------------------- utilidades de tipos
def normalizar_texto(s: pd.Series) -> pd.Series:
    def _n(x):
        if pd.isna(x):
            return x
        x = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode()
        return " ".join(x.lower().strip().split())
    return s.map(_n)


def a_numero(s: pd.Series) -> pd.Series:
    """Convierte '$1,234.50' o '1234,5' a float. Lo no convertible queda NaN."""
    if pd.api.types.is_numeric_dtype(s):
        return s.astype(float)
    t = s.astype("string").str.replace(r"[\$\s%]", "", regex=True)
    ambos = t.str.contains(",", na=False) & t.str.contains(r"\.", na=False)
    t = t.where(~ambos, t.str.replace(",", "", regex=False))
    t = t.str.replace(",", ".", regex=False)
    return pd.to_numeric(t, errors="coerce")


# ------------------------------------------------------------- faltantes
def diagnosticar_faltantes(df: pd.DataFrame, cols=None) -> dict:
    """
    Mecanismo de faltantes por columna: se contrasta el indicador de faltante contra las demas
    variables observadas (Mann-Whitney en numericas, chi2 en categoricas) con Bonferroni.
    Asociacion significativa -> MAR probable; sin asociacion -> MCAR no rechazado.
    MNAR no es verificable con datos observados: requiere justificacion de dominio.
    """
    cols = cols or C.NUMERICAS
    aux = df.copy()
    aux["anio"] = aux["periodo"].dt.year
    out = {}
    for col in cols:
        miss = aux[col].isna()
        if miss.sum() == 0:
            out[col] = {"pct_faltante": 0.0, "mecanismo": "sin faltantes", "pruebas": []}
            continue
        pruebas = []
        for otra in [c for c in C.NUMERICAS if c != col]:
            a, b = aux.loc[miss, otra].dropna(), aux.loc[~miss, otra].dropna()
            if len(a) > 2 and len(b) > 2:
                try:
                    pruebas.append({"contra": otra, "prueba": "Mann-Whitney",
                                    "p": float(stats.mannwhitneyu(a, b).pvalue)})
                except ValueError:
                    pass
        for cat in [c for c in C.CATEGORICAS_MAR if c in aux.columns]:
            tabla = pd.crosstab(aux[cat], miss)
            if tabla.shape[1] == 2 and tabla.shape[0] > 1:
                pruebas.append({"contra": cat, "prueba": "chi2",
                                "p": float(stats.chi2_contingency(tabla)[1])})
        pruebas = [t for t in pruebas if t["p"] == t["p"]]
        alpha_b = C.ALPHA_MAR / max(len(pruebas), 1)
        sig = [t["contra"] for t in pruebas if t["p"] < alpha_b]
        out[col] = {
            "pct_faltante": round(float(miss.mean() * 100), 2),
            "mecanismo": f"MAR probable (asociado a: {', '.join(sig)})" if sig else "MCAR no rechazado",
            "alpha_bonferroni": alpha_b,
            "pruebas": pruebas,
            "advertencia_MNAR": "No verificable con datos observados; justificar con conocimiento del sector.",
        }
    return out


def imputar(df: pd.DataFrame, cols=None):
    """
    Imputacion por serie: 1) interpolacion lineal dentro de la serie (max. LIMITE_INTERPOLACION
    observaciones consecutivas), 2) mediana de la serie. NO se usa mediana global: mezclaria
    precios de productos distintos. Lo que siga faltando (serie sin datos) lo manda el pipeline
    a cuarentena. Cada imputacion deja la bandera <col>_imputado.
    """
    cols = cols or C.NUMERICAS
    df = df.sort_values(C.LLAVES).reset_index(drop=True).copy()
    resumen = {}
    for col in cols:
        falt = df[col].isna()
        if falt.any():
            df[col] = df.groupby(C.GRUPO)[col].transform(
                lambda s: s.interpolate(method="linear", limit=C.LIMITE_INTERPOLACION,
                                        limit_direction="both"))
            df[col] = df[col].fillna(df.groupby(C.GRUPO)[col].transform("median"))
        df[f"{col}_imputado"] = falt & df[col].notna()
        resumen[col] = int(df[f"{col}_imputado"].sum())
    return df, resumen


# ------------------------------------------------------------- atipicos
def detectar_atipicos(df: pd.DataFrame, cols=None) -> pd.DataFrame:
    """
    - IQR por serie                                  -> atipico_iqr
    - Z-score robusto (MAD) sobre la desviacion respecto a la mediana movil (5 obs.) de la
      serie, para no marcar la tendencia/estacionalidad     -> atipico_zrob
    - Isolation Forest sobre precios RELATIVOS a la mediana de su serie -> atipico_if
    Series con < MIN_OBS_SERIE observaciones no se evaluan (IQR/MAD poco confiables).
    Consenso: atipico_final = al menos 2 de 3.
    """
    cols = cols or C.NUMERICAS
    df = df.copy()
    n = df.groupby(C.GRUPO)[cols[0]].transform("size")
    evaluable = n >= C.MIN_OBS_SERIE
    for col in cols:
        g = df.groupby(C.GRUPO)[col]
        q1, q3 = g.transform(lambda s: s.quantile(.25)), g.transform(lambda s: s.quantile(.75))
        iqr = q3 - q1
        df[f"{col}_lim_inf"] = q1 - C.IQR_K * iqr
        df[f"{col}_lim_sup"] = q3 + C.IQR_K * iqr
        iqr_flag = ((df[col] < df[f"{col}_lim_inf"]) | (df[col] > df[f"{col}_lim_sup"])) & evaluable

        med_mov = g.transform(lambda s: s.rolling(5, center=True, min_periods=1).median())
        dev = df[col] - med_mov
        mad = dev.groupby(df[C.GRUPO]).transform(lambda s: np.median(np.abs(s - np.median(s))))
        zrob = 0.6745 * dev / mad.replace(0, np.nan)
        df[f"{col}_atipico_iqr"] = iqr_flag.fillna(False)
        df[f"{col}_atipico_zrob"] = ((zrob.abs() > C.Z_ROBUSTO_UMBRAL) & evaluable).fillna(False)

    med = df.groupby(C.GRUPO)[cols].transform("median")
    X = (df[cols] / med - 1).replace([np.inf, -np.inf], np.nan).fillna(0)
    iso = IsolationForest(contamination=C.IF_CONTAMINACION, random_state=C.SEMILLA)
    if_flag = pd.Series(iso.fit_predict(X) == -1, index=df.index) & evaluable
    for col in cols:
        df[f"{col}_atipico_if"] = if_flag
        votos = (df[f"{col}_atipico_iqr"].astype(int) + df[f"{col}_atipico_zrob"].astype(int)
                 + df[f"{col}_atipico_if"].astype(int))
        df[f"{col}_atipico_final"] = votos >= 2
    return df


def tratar_atipicos(df: pd.DataFrame, cols=None):
    """Winsorizacion a los limites IQR solo en atipicos de consenso (se conserva el original)."""
    cols = cols or C.NUMERICAS
    df = df.copy()
    resumen = {}
    for col in cols:
        m = df[f"{col}_atipico_final"]
        df[f"{col}_original"] = df[col]
        df.loc[m, col] = df.loc[m, col].clip(df.loc[m, f"{col}_lim_inf"], df.loc[m, f"{col}_lim_sup"])
        resumen[col] = {"iqr": int(df[f"{col}_atipico_iqr"].sum()),
                        "z_robusto": int(df[f"{col}_atipico_zrob"].sum()),
                        "isolation_forest": int(df[f"{col}_atipico_if"].sum()),
                        "consenso_tratados": int(m.sum())}
    return df, resumen


# ------------------------------------------------------------- normalizacion
def normalizar(df: pd.DataFrame, cols=None) -> pd.DataFrame:
    """Min-Max (<col>_mm) y Z-Score (<col>_z) DENTRO de cada serie.
    En E2 los parametros deben ajustarse solo con entrenamiento (evitar fuga)."""
    cols = cols or C.NUMERICAS
    df = df.copy()
    for col in cols:
        g = df.groupby(C.GRUPO)[col]
        rango = (g.transform("max") - g.transform("min")).replace(0, np.nan)
        df[f"{col}_mm"] = ((df[col] - g.transform("min")) / rango).fillna(0.0)
        sd = g.transform(lambda s: s.std(ddof=0)).replace(0, np.nan)
        df[f"{col}_z"] = ((df[col] - g.transform("mean")) / sd).fillna(0.0)
    return df


# ------------------------------------------------------------- discretizacion
def discretizar(df: pd.DataFrame) -> pd.DataFrame:
    """Discretizacion del precio RELATIVO a la mediana de su serie (terciles y 4 rangos) +
    jerarquias: dia < mes < trimestre < semestre < anio  y  origen < macro-region."""
    df = df.copy()
    y = C.VARIABLE_OBJETIVO
    df[f"{y}_rel"] = df[y] / df.groupby(C.GRUPO)[y].transform("median")
    df[f"{y}_nivel"] = pd.qcut(df[f"{y}_rel"].rank(method="first"), 3, labels=["bajo", "medio", "alto"])
    df[f"{y}_rango"] = pd.cut(df[f"{y}_rel"], 4, labels=["R1", "R2", "R3", "R4"])
    df["mes"] = df["periodo"].dt.month
    df["trimestre"] = df["periodo"].dt.quarter
    df["semestre"] = np.where(df["mes"] <= 6, 1, 2)
    df["anio"] = df["periodo"].dt.year
    df["macro_region"] = df["origen"].map(C.MACRO_ORIGEN).fillna("otro")
    return df


# ------------------------------------------------------------- reduccion
def agregar_periodo(df: pd.DataFrame) -> pd.DataFrame:
    """Reduccion por agregacion: observaciones -> promedio por FRECUENCIA_OBJETIVO y serie."""
    d = df.copy()
    d["periodo_agg"] = d["periodo"].dt.to_period(C.FRECUENCIA_OBJETIVO).dt.to_timestamp()
    keys = C.CLAVES_SERIE + [C.GRUPO, "macro_region", "periodo_agg"]
    g = d.groupby(keys, observed=True, dropna=False)
    out = g[C.NUMERICAS].mean().reset_index()
    out["n_obs"] = g.size().values
    return out


def seleccionar_variables(df: pd.DataFrame):
    """Reduccion por seleccion: quita varianza ~0 y variables con |r| > CORR_MAX
    (precio_min/max suelen ser casi redundantes con precio_frec)."""
    z = [f"{c}_z" for c in C.NUMERICAS]
    info = {"varianza_cero": [], "correlacion_alta": []}
    vt = VarianceThreshold(1e-8).fit(df[z])
    info["varianza_cero"] = [c for c, ok in zip(z, vt.get_support()) if not ok]
    keep = [c for c in z if c not in info["varianza_cero"]]
    corr = df[keep].corr().abs()
    objetivo = C.VARIABLE_OBJETIVO + "_z"
    for i, a in enumerate(keep):
        for b in keep[i + 1:]:
            if a in info["correlacion_alta"] or b in info["correlacion_alta"]:
                continue
            if corr.loc[a, b] > C.CORR_MAX:
                info["correlacion_alta"].append(b if b != objetivo else a)
    keep = [c for c in keep if c not in info["correlacion_alta"]]
    return keep, info


def muestra_estratificada(df: pd.DataFrame, frac=0.3, por="producto") -> pd.DataFrame:
    """Reduccion por muestreo estratificado (util para EDA rapido)."""
    return df.groupby(por, group_keys=False).sample(frac=frac, random_state=C.SEMILLA)
