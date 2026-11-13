"""
Pipeline E1:  Bronce -> integracion -> Puerta de Calidad -> Plata -> limpieza -> Oro
Uso:
    python -m src.pipeline            # usa data/bronce del repositorio
    python -m src.pipeline --demo     # genera datos sinteticos en data_demo/ y los procesa
"""
import argparse
import json
import sys

import pandas as pd

from . import config as C
from . import integracion as I
from . import limpieza as L
from .calidad import puerta_de_calidad


def ejecutar(base=None) -> dict:
    R = C.rutas(base)
    for p in R.values():
        p.mkdir(parents=True, exist_ok=True)
    rep = {}

    # 1) carga + esquema comun
    crudas = {n: I.cargar_fuente(n, R["bronce"]) for n in C.FUENTES}
    rep["filas_bronce"] = {n: len(d) for n, d in crudas.items()}
    est = {n: I.estandarizar_esquema(d, n) for n, d in crudas.items()}

    # 2) integracion
    integrado, cuar_integ = I.integrar(est)
    rep["filas_integradas"] = len(integrado)

    # 3) Puerta de calidad
    validos, cuar, motivos = puerta_de_calidad(integrado)
    if len(cuar_integ):
        cuar = pd.concat([cuar, cuar_integ], ignore_index=True)
        motivos["duplicado de llave en fuente secundaria"] = len(cuar_integ)

    # 4) faltantes (diagnostico sobre datos validos, antes de imputar)
    rep["faltantes_diagnostico"] = L.diagnosticar_faltantes(validos)
    imputado, rep["imputados"] = L.imputar(validos)

    # series sin datos suficientes: tampoco se borran, van a cuarentena
    sin_dato = imputado[C.NUMERICAS].isna().any(axis=1)
    if sin_dato.any():
        q = imputado[sin_dato].copy()
        q["_motivo_cuarentena"] = "faltante no imputable (serie sin datos suficientes)"
        cuar = pd.concat([cuar, q], ignore_index=True)
        motivos["faltante no imputable (serie sin datos suficientes)"] = int(sin_dato.sum())
        imputado = imputado[~sin_dato].reset_index(drop=True)
    rep["puerta_calidad"] = {"validos": len(imputado), "cuarentena": len(cuar), "motivos": motivos}
    cuar.to_csv(R["cuarentena"] / "cuarentena.csv", index=False, encoding="utf-8")

    # 5) atipicos
    flag = L.detectar_atipicos(imputado)
    limpio, rep["atipicos"] = L.tratar_atipicos(flag)
    plata_cols = [c for c in limpio.columns
                  if not any(s in c for s in ["_lim_inf", "_lim_sup", "_atipico_iqr",
                                              "_atipico_zrob", "_atipico_if"])]
    plata = limpio[plata_cols]
    plata.to_csv(R["plata"] / "plata.csv", index=False)

    # 6) Oro: normalizacion, discretizacion, reduccion
    oro = L.discretizar(L.normalizar(plata))
    keep, info_sel = L.seleccionar_variables(oro)
    rep["seleccion_variables"] = {"conservadas": keep, **info_sel}
    oro.to_csv(R["oro"] / "oro_observaciones.csv", index=False)
    agg = L.agregar_periodo(oro)
    agg.to_csv(R["oro"] / "oro_agregado.csv", index=False)

    # 7) cobertura historica (requisito de la rubrica: >= 36 periodos)
    per = plata["periodo"].dt.to_period(C.FRECUENCIA_OBJETIVO)
    rep["series"] = int(plata[C.GRUPO].nunique())
    rep["periodos_distintos"] = int(per.nunique())
    por_serie = plata.assign(_p=per).groupby(C.GRUPO)["_p"].nunique()
    rep["series_con_min_periodos"] = int((por_serie >= C.MIN_PERIODOS).sum())
    rep["cumple_min_periodos"] = rep["periodos_distintos"] >= C.MIN_PERIODOS
    with open(R["reportes"] / "reporte_calidad.json", "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False, default=str)
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="usar datos sinteticos en data_demo/")
    a = ap.parse_args()
    base = None
    if a.demo:
        from .demo_datos import generar
        base = C.RAIZ / "data_demo"
        generar(base / "bronce")
    rep = ejecutar(base)
    pc = rep["puerta_calidad"]
    print(f"Bronce: {rep['filas_bronce']} | validos -> Plata: {pc['validos']} | cuarentena: {pc['cuarentena']}")
    for m, n in pc["motivos"].items():
        print(f"   - {m}: {n}")
    print(f"Series: {rep['series']} | periodos ({C.FRECUENCIA_OBJETIVO}): {rep['periodos_distintos']} "
          f"(>= {C.MIN_PERIODOS}: {rep['cumple_min_periodos']}) | series con >= {C.MIN_PERIODOS} periodos: "
          f"{rep['series_con_min_periodos']}")
    sys.exit(0 if rep["cumple_min_periodos"] else 1)


if __name__ == "__main__":
    main()
