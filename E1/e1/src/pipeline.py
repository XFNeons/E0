"""Orquestador Bronce -> Puerta de Calidad -> Plata -> Oro.

Uso (desde E1/e1/):
    python -m src.pipeline            # usa la Bronce real de E0/data/bronze
    python -m src.pipeline --demo     # genera Bronce sintética y escribe en data_demo/
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, limpieza, linaje
from .calidad import PuertaCerrada, aplicar_puerta
from .integracion import integrar

log = logging.getLogger("pipeline")

NOMBRE_COLUMNA = {
    "emec_menor_ingresos_colima": "ingresos_colima",
    "emec_menor_personal_colima": "personal_colima",
    "emec_menor_remuneraciones_colima": "remuneraciones_colima",
    "emec_menor_ingresos_jalisco": "ingresos_jalisco",
    "emec_menor_ingresos_michoacan": "ingresos_michoacan",
    "emec_menor_ingresos_nayarit": "ingresos_nayarit",
    "inpc_general_nacional": "inpc",
    "tiie_28d": "tiie",
    "tipo_cambio_fix": "tipo_cambio",
}
OBJETIVO = "ingresos_colima"


def a_ancho(plata: pd.DataFrame) -> pd.DataFrame:
    ancho = (plata.assign(col=plata["serie"].map(NOMBRE_COLUMNA))
             .pivot(index="fecha", columns="col", values="valor").sort_index())
    ancho = ancho.reindex(pd.date_range(ancho.index.min(), ancho.index.max(), freq="MS"))
    ancho.columns.name = None
    ancho.index.name = "fecha"
    return ancho


def limpiar(ancho: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Atípicos (sobre lo observado) -> imputación de faltantes interiores."""
    limpio, metodos, diags = pd.DataFrame(index=ancho.index), {}, []
    for col in ancho.columns:
        observada = ancho[col]
        primero, ultimo = observada.first_valid_index(), observada.last_valid_index()
        tramo = observada.loc[primero:ultimo]
        tratada, diag = limpieza.tratar_atipicos(tramo)
        # Lo que tratar_atipicos interpoló fueron picos; los faltantes originales se imputan aparte.
        tratada[tramo.isna()] = np.nan
        imputada, metodo = limpieza.imputar(tratada)
        metodo[diag["tratamiento"].eq("reemplazado_por_interpolacion")] = "atipico_reemplazado"
        limpio[col] = imputada.reindex(ancho.index)
        metodos[col] = metodo.reindex(ancho.index).fillna("fuera_de_rango_de_la_serie")
        diags.append(diag.assign(serie=col).reset_index(names="fecha"))
    atipicos = pd.concat(diags, ignore_index=True)
    atipicos = atipicos[atipicos["atipico_z"] | atipicos["atipico_iqr"]]
    return limpio, {"metodos": pd.DataFrame(metodos), "atipicos": atipicos}


def construir_oro(limpio: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], dict]:
    # Reducción 1: ventana temporal común para el análisis
    df = limpio.loc[config.FECHA_INICIO_ORO:].copy()

    # Variables derivadas
    for col in [c for c in df.columns if c.startswith(("ingresos", "personal", "remuneraciones"))]:
        df[f"{col}_crec_anual"] = df[col].pct_change(12, fill_method=None) * 100
    if "inpc" in df:
        df["inflacion_anual"] = df["inpc"].pct_change(12, fill_method=None) * 100
    if f"{OBJETIVO}_crec_anual" in df:
        df["ingresos_crec_anual"] = df[f"{OBJETIVO}_crec_anual"]

    # Fin del periodo de entrenamiento: 12 meses antes del último dato observado de la objetivo
    ref = OBJETIVO if OBJETIVO in df else df.columns[0]
    fin_entrenamiento = df[ref].last_valid_index() - pd.DateOffset(months=config.MESES_PRUEBA)

    # Atípicos multivariados (Isolation Forest) sobre el crecimiento anual de Colima
    vect = [c for c in ["ingresos_colima_crec_anual", "personal_colima_crec_anual",
                        "remuneraciones_colima_crec_anual"] if c in df]
    df["atipico_multivariado"] = limpieza.isolation_forest(df[vect]) if len(vect) >= 2 else False

    # Reducción 2: selección de variables continuas para el panel de E1/E2
    candidatas = [c for c in ["ingresos_colima", "personal_colima", "remuneraciones_colima",
                              "inpc", "tiie", "tipo_cambio"] if c in df]
    seleccion, descartes = limpieza.seleccionar_variables(df[candidatas].dropna(), [OBJETIVO])

    # Escalamiento ajustado solo con entrenamiento
    parametros = limpieza.ajustar_escaladores(df, seleccion, fin_entrenamiento)
    escaladas = limpieza.aplicar_escaladores(df, parametros)

    # Discretización y jerarquía de tiempo
    discretas = limpieza.discretizar(df, fin_entrenamiento)
    tiempo = limpieza.jerarquia_tiempo(df.index)

    columnas_panel = (seleccion + [c for c in ["ingresos_crec_anual", "inflacion_anual"] if c in df]
                      + ["atipico_multivariado"])
    panel = pd.concat([tiempo, df[columnas_panel], escaladas, discretas], axis=1)
    panel.insert(0, "conjunto", np.where(panel.index <= fin_entrenamiento, "entrenamiento", "prueba"))
    panel.insert(1, "entidad", "Colima")
    panel.insert(2, "region", config.REGION["Colima"])
    panel.insert(3, "sector", config.SECTOR["ingresos"])

    # Panel por entidad (E3): formato largo con jerarquía geográfica
    estados = [c for c in df.columns if c.startswith("ingresos_") and not c.endswith("crec_anual")]
    entidades = []
    for col in estados:
        nombre = {"colima": "Colima", "jalisco": "Jalisco", "michoacan": "Michoacán",
                  "nayarit": "Nayarit"}.get(col.split("_", 1)[1], col)
        entidades.append(pd.DataFrame({
            "entidad": nombre, "region": config.REGION.get(nombre, ""), "pais": "México",
            "ingresos": df[col], "ingresos_crec_anual": df.get(f"{col}_crec_anual"),
            "personal": df.get(f"personal_{col.split('_', 1)[1]}"),
            "remuneraciones": df.get(f"remuneraciones_{col.split('_', 1)[1]}"),
        }, index=df.index).join(tiempo[["trimestre", "anio"]]))
    panel_entidades = (pd.concat(entidades).reset_index(names="fecha").dropna(subset=["ingresos"])
                       .reset_index(drop=True) if entidades else pd.DataFrame())

    info = {"fin_entrenamiento": str(fin_entrenamiento.date()),
            "variables_seleccionadas": seleccion,
            "variables_descartadas": descartes.to_dict("records"),
            "parametros_escalado": parametros,
            "meses_atipico_multivariado": [str(d.date()) for d in df.index[df["atipico_multivariado"]]],
            "filas_panel": int(len(panel)), "filas_panel_entidades": int(len(panel_entidades))}
    return {"panel_colima_mensual": panel.reset_index(names="fecha"),
            "panel_entidades": panel_entidades}, info


def correr(bronce: Path | None = None, salida: Path | None = None) -> dict:
    r = config.rutas(bronce, salida).crear()
    log.info("Bronce: %s", r.bronce)

    largo, integ = integrar(r.bronce)
    integ["conflictos"].to_csv(r.reportes / "conflictos_revision.csv", index=False)

    validos, cuarentena, puerta = aplicar_puerta(largo, r)
    log.info("Puerta de Calidad: %d válidos, %d a cuarentena", puerta["registros_validos"],
             puerta["registros_en_cuarentena"])
    validos = linaje.asignar_id_registro(validos)
    validos.to_csv(r.plata / "plata_largo.csv", index=False)

    ancho = a_ancho(validos)
    faltantes = limpieza.diagnosticar_faltantes(ancho)
    faltantes.to_csv(r.reportes / "diagnostico_faltantes.csv", index=False)

    limpio, detalle = limpiar(ancho)
    detalle["atipicos"].to_csv(r.reportes / "atipicos.csv", index=False)
    (detalle["metodos"].reset_index(names="fecha")
     .to_csv(r.reportes / "metodo_por_celda.csv", index=False))
    limpio.reset_index(names="fecha").to_csv(r.plata / "plata_ancho_limpio.csv", index=False)

    tablas, oro = construir_oro(limpio)
    tablas, linaje_oro = linaje.construir_linaje(tablas, validos, detalle["metodos"], NOMBRE_COLUMNA,
                                                 linaje.prefijo_bronce(r.bronce))
    linaje_oro.to_csv(r.oro / "linaje_oro.csv", index=False)
    problemas = linaje.verificar(linaje_oro) if len(linaje_oro) else pd.DataFrame()
    for nombre, tabla in tablas.items():
        tabla.to_csv(r.oro / f"{nombre}.csv", index=False)
    (r.oro / "parametros_escalado.json").write_text(
        json.dumps(oro["parametros_escalado"], indent=2, ensure_ascii=False), encoding="utf-8")

    metodos = detalle["metodos"].stack().value_counts().to_dict()
    reporte = {
        "integracion": integ["resumen"],
        "puerta_de_calidad": puerta,
        "faltantes": faltantes.to_dict("records"),
        "celdas_por_metodo": {k: int(v) for k, v in metodos.items()},
        "atipicos": {
            "detectados": int(len(detalle["atipicos"])),
            "por_tratamiento": detalle["atipicos"]["tratamiento"].value_counts().to_dict(),
        },
        "oro": {k: v for k, v in oro.items() if k != "parametros_escalado"},
        "linaje": {
            "celdas_rastreadas": int(len(linaje_oro)),
            "filas_oro_sin_linaje": int(sum(t["archivos_bronce"].fillna("").eq("").sum()
                                            for t in tablas.values() if "archivos_bronce" in t)),
            "archivos_bronce_citados": int(linaje_oro["ruta_bronce"].replace("", np.nan).nunique())
            if len(linaje_oro) else 0,
            "archivos_con_problema": int(len(problemas)),
        },
    }
    (r.reportes / "reporte_calidad.json").write_text(
        json.dumps(reporte, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    log.info("Oro: %s", ", ".join(f"{k} ({len(v)} filas)" for k, v in tablas.items()))
    return reporte


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", action="store_true", help="Usar Bronce sintética (no son datos reales)")
    ap.add_argument("--bronce", type=Path, help="Carpeta Bronce alternativa")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        if args.demo:
            from .demo_datos import generar
            with tempfile.TemporaryDirectory() as tmp:
                correr(generar(Path(tmp)), config.PAQUETE / "data_demo")
        else:
            correr(args.bronce)
    except PuertaCerrada as e:
        log.error("%s", e)
        return 2
    except FileNotFoundError as e:
        log.error("%s", e)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
