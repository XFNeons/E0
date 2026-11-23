"""Configuración del pipeline E1 (Bronce -> Plata -> Oro).

Rutas relativas a la raíz del repositorio:
    E0/data/bronze/        capa Bronce (la escribe el extractor de E0, no se modifica aquí)
    E1/e1/data/plata/      registros que pasaron la Puerta de Calidad
    E1/e1/data/cuarentena/ registros rechazados, con motivo (append-only, nunca se borran)
    E1/e1/data/oro/        tablas analíticas listas para E1-E3
    E1/e1/data/reportes/   reporte de calidad y bitácora de decisiones
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PAQUETE = Path(__file__).resolve().parents[1]          # E1/e1
REPO = PAQUETE.parents[1]                               # raíz del repositorio


@dataclass(frozen=True)
class Rutas:
    bronce: Path
    plata: Path
    cuarentena: Path
    oro: Path
    reportes: Path

    def crear(self) -> "Rutas":
        for p in (self.plata, self.cuarentena, self.oro, self.reportes):
            p.mkdir(parents=True, exist_ok=True)
        return self


def rutas(bronce: Path | None = None, salida: Path | None = None) -> Rutas:
    salida = salida or PAQUETE / "data"
    return Rutas(
        bronce=bronce or REPO / "E0" / "data" / "bronze",
        plata=salida / "plata",
        cuarentena=salida / "cuarentena",
        oro=salida / "oro",
        reportes=salida / "reportes",
    )


# ---------------------------------------------------------------- catálogo de series
# clave (carpeta en Bronce) -> metadatos que unifican el esquema de las dos fuentes
SERIES: dict[str, dict] = {
    "emec_menor_ingresos_colima":       {"entidad": "Colima",    "variable": "ingresos",       "unidad": "indice_2018"},
    "emec_menor_personal_colima":       {"entidad": "Colima",    "variable": "personal",       "unidad": "indice_2018"},
    "emec_menor_remuneraciones_colima": {"entidad": "Colima",    "variable": "remuneraciones", "unidad": "indice_2018"},
    "emec_menor_ingresos_jalisco":      {"entidad": "Jalisco",   "variable": "ingresos",       "unidad": "indice_2018"},
    "emec_menor_ingresos_michoacan":    {"entidad": "Michoacán", "variable": "ingresos",       "unidad": "indice_2018"},
    "emec_menor_ingresos_nayarit":      {"entidad": "Nayarit",   "variable": "ingresos",       "unidad": "indice_2018"},
    "inpc_general_nacional":            {"entidad": "Nacional",  "variable": "inpc",           "unidad": "indice_2q_jul_2018"},
    "tiie_28d":                         {"entidad": "Nacional",  "variable": "tiie",           "unidad": "porcentaje"},
    "tipo_cambio_fix":                  {"entidad": "Nacional",  "variable": "tipo_cambio",    "unidad": "pesos_por_dolar"},
}

# Rangos plausibles por variable para la Puerta de Calidad (fuera de rango -> cuarentena).
# Los índices 2018=100 de la EMEC estatal han oscilado aprox. entre 40 y 200 (caída COVID incluida).
RANGOS: dict[str, tuple[float, float]] = {
    "ingresos": (20.0, 300.0),
    "personal": (20.0, 300.0),
    "remuneraciones": (20.0, 300.0),
    "inpc": (50.0, 250.0),
    "tiie": (0.0, 30.0),
    "tipo_cambio": (5.0, 40.0),
}

FECHA_MIN = "2005-01-01"
FALTANTES_DECLARADOS = {"", "N/E", "NE", "ND", "N/D", "NA", "-", "null", "None"}

# Jerarquías conceptuales
REGION = {"Colima": "Occidente", "Jalisco": "Occidente", "Michoacán": "Occidente",
          "Nayarit": "Occidente", "Nacional": "Nacional"}
SECTOR = {"ingresos": "46 Comercio al por menor", "personal": "46 Comercio al por menor",
          "remuneraciones": "46 Comercio al por menor", "inpc": "Precios", "tiie": "Financiero",
          "tipo_cambio": "Financiero"}
MESES_TEMPORADA_ALTA = {7, 8, 11, 12}   # vacaciones de verano, Buen Fin y diciembre

# Limpieza
UMBRAL_Z_ROBUSTO = 3.5     # Iglewicz y Hoaglin (1993)
FACTOR_IQR = 1.5
CONTAMINACION_IFOREST = 0.05
MESES_PRUEBA = 12          # los últimos 12 meses no se usan para ajustar escaladores (evita fuga de información)
FECHA_INICIO_ORO = "2015-01-01"
UMBRAL_CORRELACION = 0.95  # selección de variables: se descarta una de cada par más correlacionado
SEMILLA = 42
