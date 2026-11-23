"""Genera una capa Bronce SINTÉTICA con el mismo formato JSON que las APIs reales de INEGI y
Banxico, con defectos sembrados a propósito para probar el pipeline y la Puerta de Calidad.

¡No son datos reales! Solo sirven para pruebas y para el modo --demo.

Defectos sembrados (y qué debe pasar con cada uno):
  * personal_colima: 3 meses 'N/E' en 2019            -> faltante interior, interpolación lineal
  * remuneraciones_colima: 6 meses 'N/E' en 2016      -> hueco largo, imputación estacional
  * ingresos_colima: pico x1.6 en 2017-05            -> atípico (ruido), reemplazado
  * ingresos_colima: caída por COVID en 2020          -> atípico conservado (evento conocido)
  * ingresos_colima: segunda captura revisa el último mes -> conflicto de revisión, gana la última
  * ingresos_jalisco: valor '1O4.2' (letra O)         -> cuarentena: no numérico
  * ingresos_nayarit: valor '-5'                      -> cuarentena: fuera de rango
  * tiie_28d: un día con 'abc'                        -> cuarentena: no numérico
  * tiie_28d / tipo_cambio_fix: días 'N/E'            -> faltante declarado, se excluye del promedio
  * serie_desconocida (INEGI)                         -> cuarentena: fuera del catálogo
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

INICIO_EMEC, FIN_EMEC = "2008-01-01", "2026-08-01"
INICIO_BMX, FIN_BMX = "2015-01-01", "2026-11-20"


def _serie_emec(rng, nivel, tendencia, amplitud, ruido) -> pd.Series:
    fechas = pd.date_range(INICIO_EMEC, FIN_EMEC, freq="MS")
    t = np.arange(len(fechas))
    estacional = amplitud * np.select([fechas.month == 12, fechas.month.isin([7, 8, 11]),
                                       fechas.month.isin([1, 2])], [1.0, 0.4, -0.5], 0.0)
    s = nivel + tendencia * t + estacional + rng.normal(0, ruido, len(t))
    covid = (fechas >= "2020-04-01") & (fechas <= "2020-06-01")
    s[covid] *= np.array([0.62, 0.70, 0.82])
    return pd.Series(s.round(4), index=fechas)


def _inegi(serie: pd.Series, sustituciones: dict | None = None) -> dict:
    sustituciones = sustituciones or {}
    obs = []
    for f, v in serie.items():
        clave = f.strftime("%Y/%m")
        obs.append({"TIME_PERIOD": clave, "OBS_VALUE": sustituciones.get(clave, f"{v:.4f}"),
                    "OBS_EXCEPTION": None, "OBS_STATUS": None, "OBS_SOURCE": "", "OBS_NOTE": ""})
    return {"Header": {"Name": "Sintético", "Email": ""},
            "Series": [{"INDICADOR": "DEMO", "FREQ": "8", "OBSERVATIONS": obs}]}


def _banxico(serie_id: str, serie: pd.Series, sustituciones: dict | None = None) -> dict:
    sustituciones = sustituciones or {}
    datos = [{"fecha": f.strftime("%d/%m/%Y"),
              "dato": sustituciones.get(f.strftime("%d/%m/%Y"), f"{v:,.4f}")} for f, v in serie.items()]
    return {"bmx": {"series": [{"idSerie": serie_id, "titulo": "Sintético", "datos": datos}]}}


def _guardar(base: Path, fuente: str, clave: str, payload: dict, marca: str) -> None:
    destino = base / fuente / clave / f"{marca}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def generar(base: Path, semilla: int = 7) -> Path:
    rng = np.random.default_rng(semilla)
    m1, m2 = "2026-11-02_131700", "2026-11-16_131700"

    ingresos = _serie_emec(rng, 88, 0.12, 9, 1.2)
    ingresos.loc["2017-05-01"] *= 1.6
    _guardar(base, "inegi", "emec_menor_ingresos_colima", _inegi(ingresos), m1)
    revisada = ingresos.copy()
    revisada.iloc[-1] += 1.7
    _guardar(base, "inegi", "emec_menor_ingresos_colima", _inegi(revisada), m2)

    personal = _serie_emec(rng, 92, 0.05, 2, 0.6)
    _guardar(base, "inegi", "emec_menor_personal_colima",
             _inegi(personal, {k: "N/E" for k in ["2019/03", "2019/04", "2019/05"]}), m1)
    remun = _serie_emec(rng, 95, 0.03, 3, 0.9)
    _guardar(base, "inegi", "emec_menor_remuneraciones_colima",
             _inegi(remun, {f"2016/{m:02d}": "N/E" for m in range(4, 10)}), m1)

    _guardar(base, "inegi", "emec_menor_ingresos_jalisco",
             _inegi(_serie_emec(rng, 90, 0.15, 10, 1.0), {"2018/07": "1O4.2"}), m1)
    _guardar(base, "inegi", "emec_menor_ingresos_michoacan",
             _inegi(_serie_emec(rng, 85, 0.10, 8, 1.4)), m1)
    _guardar(base, "inegi", "emec_menor_ingresos_nayarit",
             _inegi(_serie_emec(rng, 80, 0.14, 12, 1.6), {"2021/02": "-5"}), m1)

    meses = pd.date_range(INICIO_EMEC, FIN_EMEC, freq="MS")
    inpc = pd.Series(70 * 1.0035 ** np.arange(len(meses)), index=meses)
    _guardar(base, "inegi", "inpc_general_nacional", _inegi(inpc), m1)
    _guardar(base, "inegi", "serie_desconocida", _inegi(inpc.head(5)), m1)

    dias = pd.bdate_range(INICIO_BMX, FIN_BMX)
    tiie = pd.Series(np.clip(3.3 + 8 * np.sin(np.linspace(0, 3.2, len(dias))) ** 2
                             + rng.normal(0, 0.02, len(dias)), 3, 12), index=dias)
    malos = {dias[30].strftime("%d/%m/%Y"): "abc", dias[400].strftime("%d/%m/%Y"): "N/E"}
    _guardar(base, "banxico", "tiie_28d", _banxico("SF43783", tiie, malos), m2)
    tc = pd.Series(14.7 + np.cumsum(rng.normal(0, 0.06, len(dias))).clip(-2, 7), index=dias)
    _guardar(base, "banxico", "tipo_cambio_fix",
             _banxico("SF43718", tc, {dias[1000].strftime("%d/%m/%Y"): "N/E"}), m2)
    return base


if __name__ == "__main__":
    import sys
    print(generar(Path(sys.argv[1] if len(sys.argv) > 1 else "bronce_demo")))
