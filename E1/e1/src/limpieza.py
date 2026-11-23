"""Limpieza y preprocesamiento estadístico (Plata -> Oro).

1. Faltantes: diagnóstico del mecanismo (MCAR / MAR / MNAR) e imputación justificada.
2. Atípicos y ruido: Z-score robusto (MAD), IQR e Isolation Forest.
3. Normalización (Min-Max) y estandarización (Z-score), ajustadas solo con el periodo de entrenamiento.
4. Discretización y jerarquías conceptuales (tiempo, geografía, sector).
5. Reducción: agregación (diario->mensual, en integracion.py), ventana temporal y selección de variables.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest

from . import config

# Meses con choque real conocido (cierre de comercios no esenciales por COVID-19).
# Un atípico aquí se CONSERVA: es información, no ruido.
EVENTOS_CONOCIDOS = pd.date_range("2020-03-01", "2020-12-01", freq="MS")


# ============================================================== 1. FALTANTES
def _posicion_faltantes(s: pd.Series) -> tuple[int, int, int]:
    """(al inicio, interiores, al final) de una serie ordenada por fecha."""
    nulos = s.isna().to_numpy()
    if not nulos.any():
        return 0, 0, 0
    validos = np.flatnonzero(~nulos)
    if len(validos) == 0:
        return int(nulos.sum()), 0, 0
    inicio, fin = validos[0], validos[-1]
    return int(inicio), int(nulos[inicio:fin + 1].sum()), int(len(nulos) - fin - 1)


def diagnosticar_faltantes(ancho: pd.DataFrame, alfa: float = 0.05) -> pd.DataFrame:
    """Para cada serie con faltantes interiores prueba si la falta se asocia con:
      * el valor de otras series en el mismo mes (Mann-Whitney)  -> evidencia de MAR
      * el mes del año (chi-cuadrada)                            -> evidencia de MAR (calendario)
    Si ninguna prueba es significativa, el patrón es compatible con MCAR.
    Faltantes solo al final = rezago de publicación (estructural, no se imputa).
    MNAR no es verificable con los datos observados; se argumenta por el proceso de la fuente."""
    filas = []
    for col in ancho.columns:
        s = ancho[col]
        ini, interior, fin = _posicion_faltantes(s)
        total = int(s.isna().sum())
        pruebas, p_min = [], np.nan
        if interior > 0:
            ind = s.isna()
            for otra in ancho.columns.drop(col):
                a, b = ancho.loc[ind, otra].dropna(), ancho.loc[~ind, otra].dropna()
                if len(a) >= 2 and len(b) >= 2:
                    p = stats.mannwhitneyu(a, b).pvalue
                    pruebas.append((f"valor de {otra}", p))
            tabla = pd.crosstab(ind, ancho.index.month)
            if tabla.shape[0] == 2:
                pruebas.append(("mes del año", stats.chi2_contingency(tabla).pvalue))
            if pruebas:
                p_min = min(p for _, p in pruebas)
        significativas = [n for n, p in pruebas if p < alfa / max(len(pruebas), 1)]  # Bonferroni
        if total == 0:
            mecanismo, accion = "sin faltantes", "ninguna"
        elif interior == 0 and ini > 0 and fin == 0:
            mecanismo = "fuera de cobertura (la fuente inicia en " + str(s.first_valid_index().date()) + ")"
            accion = "no imputar; el análisis usa la ventana común desde " + config.FECHA_INICIO_ORO
        elif interior == 0 and fin > 0:
            mecanismo = "estructural (rezago de publicación)"
            accion = "no imputar; el modelo de E1 pronostica esos meses"
        elif significativas:
            mecanismo = "MAR (asociado a " + ", ".join(significativas) + ")"
            accion = "imputación condicionada: interpolación temporal (la serie depende del tiempo)"
        else:
            mecanismo = "compatible con MCAR"
            accion = "interpolación temporal (huecos <=3 meses) o estacional (huecos más largos)"
        filas.append({"serie": col, "faltantes": total, "pct": round(100 * total / len(s), 2),
                      "al_inicio": ini, "interiores": interior, "al_final": fin,
                      "p_valor_minimo": None if np.isnan(p_min) else round(float(p_min), 4),
                      "mecanismo": mecanismo, "accion": accion})
    return pd.DataFrame(filas)


def imputar(s: pd.Series, max_lineal: int = 3) -> tuple[pd.Series, pd.Series]:
    """Imputa solo huecos INTERIORES. Devuelve (serie, método por fila).
    * Huecos <= max_lineal meses: interpolación lineal en el tiempo (la serie es suave mes a mes).
    * Huecos más largos: mismo mes del año anterior escalado por el nivel reciente
      (conserva la estacionalidad, que una línea recta borraría)."""
    s = s.astype(float).copy()
    metodo = pd.Series(np.where(s.isna(), "", "observado"), index=s.index, dtype=object)
    validos = s.dropna()
    if validos.empty:
        return s, metodo
    interior = s.index[(s.index > validos.index[0]) & (s.index < validos.index[-1]) & s.isna()]
    if len(interior) == 0:
        metodo[s.isna()] = "no_imputado"
        return s, metodo

    grupos = (s.isna() != s.isna().shift()).cumsum()
    lineal = s.interpolate(method="time", limit_area="inside")
    for _, idx in s[s.isna()].groupby(grupos[s.isna()]).groups.items():
        idx = [i for i in idx if i in interior]
        if not idx:
            continue
        if len(idx) <= max_lineal:
            s[idx] = lineal[idx]
            metodo[idx] = "interpolacion_lineal"
        else:
            for i in idx:
                previo = i - pd.DateOffset(years=1)
                if previo in s.index and pd.notna(s[previo]):
                    antes = s[:i].dropna()
                    ratio = antes.iloc[-1] / s.get(antes.index[-1] - pd.DateOffset(years=1), np.nan)
                    s[i] = s[previo] * (ratio if pd.notna(ratio) else 1.0)
                    metodo[i] = "estacional_escalada"
                else:
                    s[i] = lineal[i]
                    metodo[i] = "interpolacion_lineal"
    metodo[s.isna()] = "no_imputado"
    return s, metodo


# ============================================================== 2. ATÍPICOS Y RUIDO
def z_robusto(x: pd.Series) -> pd.Series:
    """Z-score robusto (Iglewicz y Hoaglin): 0.6745 (x - mediana) / MAD."""
    med = x.median()
    mad = (x - med).abs().median()
    if not mad or np.isnan(mad):
        return pd.Series(0.0, index=x.index)
    return 0.6745 * (x - med) / mad


def fuera_iqr(x: pd.Series, k: float = config.FACTOR_IQR) -> pd.Series:
    q1, q3 = x.quantile([0.25, 0.75])
    iqr = q3 - q1
    return (x < q1 - k * iqr) | (x > q3 + k * iqr)


def detectar_atipicos(s: pd.Series) -> pd.DataFrame:
    """Se evalúa la variación mensual en logaritmos sin su patrón estacional (se resta la mediana
    de la variación de cada mes calendario). Así ni la tendencia ni la caída normal de enero se
    confunden con atípicos. Un 'pico' aislado (error de captura) produce un salto grande de ida y
    otro de vuelta en el mes siguiente."""
    dlog = np.log(s).diff()
    residuo = dlog - dlog.groupby(dlog.index.month).transform("median")
    z = z_robusto(residuo)
    df = pd.DataFrame({"valor": s, "dlog": dlog, "residuo": residuo, "z_robusto": z,
                       "atipico_z": z.abs() > config.UMBRAL_Z_ROBUSTO,
                       "atipico_iqr": fuera_iqr(residuo.dropna()).reindex(s.index, fill_value=False)})
    pico = df["atipico_z"] & df["atipico_z"].shift(-1, fill_value=False) & \
        (np.sign(residuo) != np.sign(residuo.shift(-1)))
    df["es_pico"] = pico
    df["es_rebote"] = pico.shift(1, fill_value=False)   # el regreso al nivel normal tras el pico
    df["evento_conocido"] = df.index.isin(EVENTOS_CONOCIDOS)
    return df


def tratar_atipicos(s: pd.Series) -> tuple[pd.Series, pd.DataFrame]:
    """Política: los picos aislados fuera de eventos conocidos se consideran ruido y se reemplazan
    por interpolación; los saltos en eventos conocidos (COVID-19) se conservan y solo se marcan.
    El valor original nunca se pierde: queda en la tabla de diagnóstico."""
    diag = detectar_atipicos(s)
    a_tratar = diag["es_pico"] & ~diag["evento_conocido"]
    tratada = s.copy()
    tratada[a_tratar] = np.nan
    tratada = tratada.interpolate(method="time", limit_area="inside")
    diag["tratamiento"] = np.select(
        [a_tratar, diag["es_rebote"] & ~diag["evento_conocido"],
         (diag["atipico_z"] | diag["atipico_iqr"]) & diag["evento_conocido"],
         diag["atipico_z"], diag["atipico_iqr"]],
        ["reemplazado_por_interpolacion", "rebote_del_pico_se_corrige_al_reemplazarlo",
         "conservado_evento_conocido", "conservado_marcado_revisar", "marcado_solo_iqr"],
        default="")
    return tratada, diag


def isolation_forest(df: pd.DataFrame) -> pd.Series:
    """Atípicos multivariados: meses cuyo VECTOR de crecimientos anuales es raro aunque cada
    variable por separado no lo sea."""
    datos = df.dropna()
    if len(datos) < 24:
        return pd.Series(False, index=df.index)
    modelo = IsolationForest(contamination=config.CONTAMINACION_IFOREST, random_state=config.SEMILLA)
    etiqueta = pd.Series(modelo.fit_predict(datos) == -1, index=datos.index)
    return etiqueta.reindex(df.index, fill_value=False)


# ============================================================== 3. ESCALAMIENTO
def ajustar_escaladores(df: pd.DataFrame, columnas: list[str], fin_entrenamiento: pd.Timestamp) -> dict:
    """Parámetros calculados SOLO con datos hasta fin_entrenamiento (evita fuga de información
    hacia los 12 meses de prueba del pronóstico de E1)."""
    entrenamiento = df.loc[df.index <= fin_entrenamiento, columnas]
    return {c: {"min": float(entrenamiento[c].min()), "max": float(entrenamiento[c].max()),
                "media": float(entrenamiento[c].mean()), "desv": float(entrenamiento[c].std(ddof=0))}
            for c in columnas}


def aplicar_escaladores(df: pd.DataFrame, parametros: dict) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    for c, p in parametros.items():
        rango = p["max"] - p["min"]
        out[f"{c}_minmax"] = (df[c] - p["min"]) / rango if rango else 0.0
        out[f"{c}_z"] = (df[c] - p["media"]) / p["desv"] if p["desv"] else 0.0
    return out


# ============================================================== 4. DISCRETIZACIÓN Y JERARQUÍAS
def jerarquia_tiempo(fechas: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame({
        "mes": fechas.month,
        "trimestre": fechas.year.astype(str) + "-T" + fechas.quarter.astype(str),
        "semestre": fechas.year.astype(str) + "-S" + ((fechas.month - 1) // 6 + 1).astype(str),
        "anio": fechas.year,
        "temporada": np.where(fechas.month.isin(list(config.MESES_TEMPORADA_ALTA)), "alta", "baja"),
    }, index=fechas)


def discretizar(df: pd.DataFrame, fin_entrenamiento: pd.Timestamp) -> pd.DataFrame:
    """* tiie_nivel: alta/baja respecto a la mediana de entrenamiento (factor B de E2).
       * inflacion_nivel: alta/baja respecto a la mediana de la inflación anual (factor C de E2).
       * crecimiento_ingresos: terciles (bajo / medio / alto) del crecimiento anual de ingresos."""
    out = pd.DataFrame(index=df.index)
    train = df.index <= fin_entrenamiento
    if "tiie" in df:
        med = df.loc[train, "tiie"].median()
        out["tiie_nivel"] = np.where(df["tiie"].isna(), None, np.where(df["tiie"] >= med, "alta", "baja"))
    if "inflacion_anual" in df:
        med = df.loc[train, "inflacion_anual"].median()
        out["inflacion_nivel"] = np.where(df["inflacion_anual"].isna(), None,
                                          np.where(df["inflacion_anual"] >= med, "alta", "baja"))
    if "ingresos_crec_anual" in df:
        x = df["ingresos_crec_anual"]
        cortes = x[train].quantile([1 / 3, 2 / 3]).to_numpy()
        out["crecimiento_ingresos"] = pd.cut(x, [-np.inf, cortes[0], cortes[1], np.inf],
                                             labels=["bajo", "medio", "alto"]).astype(object)
    return out


# ============================================================== 5. REDUCCIÓN: SELECCIÓN DE VARIABLES
def seleccionar_variables(df: pd.DataFrame, protegidas: list[str],
                          umbral: float = config.UMBRAL_CORRELACION) -> tuple[list[str], pd.DataFrame]:
    """Descarta una variable de cada par con |r| >= umbral (información redundante).
    Las variables protegidas (la objetivo de E1) nunca se descartan."""
    corr = df.corr().abs()
    descartar, registro = set(), []
    cols = list(corr.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            if a in descartar or b in descartar:
                continue
            r = corr.loc[a, b]
            if r >= umbral:
                quitar = b if b not in protegidas else (a if a not in protegidas else None)
                if quitar:
                    descartar.add(quitar)
                    registro.append({"par": f"{a} ~ {b}", "r": round(float(r), 3), "descartada": quitar})
    return [c for c in cols if c not in descartar], pd.DataFrame(registro)
