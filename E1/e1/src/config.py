"""
CONFIGURACION DEL PIPELINE E1 -- Observatorio de precios de abasto (SNIIM / central de abastos)

*** Este es el unico archivo que deben ajustar. ***
Datos esperados en Bronce (una fila = un producto/calidad/presentacion/origen en una fecha):
  Producto | Calidad | Presentacion | Origen | Precio Min | Precio Max | Precio Frec | Obs. (+ fecha)
Los encabezados se comparan SIN acentos, mayusculas ni puntos, asi que "Precio Mín" == "precio min".
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def rutas(base=None):
    """Carpetas de las capas. base=None -> data/ del repositorio."""
    base = Path(base) if base else RAIZ / "data"
    return {
        "bronce": base / "bronce",
        "plata": base / "plata",
        "oro": base / "oro",
        "cuarentena": base / "cuarentena",
        "reportes": base / "reportes",
    }



FUENTES = {
    "A": {
        "patron": "*.csv",
        "col_fecha": "fecha",
        "fecha_en_archivo": r"(\d{4}-\d{2}-\d{2})",
        "dayfirst": True,
        "renombrar": {
            "producto": "producto", "calidad": "calidad", "presentacion": "presentacion",
            "origen": "origen", "precio min": "precio_min", "precio max": "precio_max",
            "precio frec": "precio_frec", "obs": "obs",
        },
    },
   
}

# ---------------------------------------------------------------- VARIABLES
CLAVES_SERIE = ["producto", "calidad", "presentacion", "origen"]   # definen UNA serie de precios
GRUPO = "serie"                                  # columna compuesta (se crea sola)
LLAVES = ["periodo"] + CLAVES_SERIE              # llave unica de un registro
VARIABLE_OBJETIVO = "precio_frec"                # lo que se pronosticara (E1 de la propuesta)
COVARIABLES = ["precio_min", "precio_max"]
NUMERICAS = [VARIABLE_OBJETIVO] + COVARIABLES

NULOS = ["n/d", "nd", "s/d", "na", "n/a", "-", "--", "", "null", "none"]   # = dato faltante (NO error)

# Rangos validos (min, max) -> fuera de rango = cuarentena. AJUSTEN a sus productos/presentaciones.
RANGOS = {"precio_frec": (0.01, 50_000.0), "precio_min": (0.01, 50_000.0), "precio_max": (0.01, 50_000.0)}
# Reglas de coherencia entre columnas: (a, b) significa  a <= b
COHERENCIA = [("precio_min", "precio_frec"), ("precio_frec", "precio_max")]
PERIODO_MIN = "2000-01-01"

# Valores permitidos por columna clave (None/ausente = no se restringe). Usen texto NORMALIZADO
# (minusculas, sin acentos). Ej.: {"calidad": ["primera", "extra", "segunda"]}
VALIDOS = {}
ALIAS = {}   # {"origen": {"mich": "michoacan"}}

# Jerarquia conceptual geografica: origen -> macro-region (texto normalizado)
MACRO_ORIGEN = {
    "michoacan": "occidente", "jalisco": "occidente", "colima": "occidente", "nayarit": "occidente",
    "sinaloa": "norte", "sonora": "norte", "baja california": "norte", "chihuahua": "norte",
    "tamaulipas": "norte", "nuevo leon": "norte", "coahuila": "norte", "durango": "norte",
    "guanajuato": "bajio-centro", "queretaro": "bajio-centro", "mexico": "bajio-centro",
    "puebla": "bajio-centro", "morelos": "bajio-centro", "hidalgo": "bajio-centro",
    "oaxaca": "sur-sureste", "chiapas": "sur-sureste", "veracruz": "sur-sureste",
    "guerrero": "sur-sureste", "yucatan": "sur-sureste", "tabasco": "sur-sureste",
}
CATEGORICAS_MAR = ["producto", "origen", "calidad", "anio"]   # contra que se prueba el faltante

# ---------------------------------------------------------------- PARAMETROS
FRECUENCIA_OBJETIVO = "M"       # frecuencia del Oro agregado y del conteo de periodos ("W" semanal)
ALPHA_MAR = 0.05
LIMITE_INTERPOLACION = 3        # max. observaciones consecutivas a interpolar
MIN_OBS_SERIE = 8               # series con menos observaciones no se evaluan por atipicos
Z_ROBUSTO_UMBRAL = 3.5
IQR_K = 1.5
IF_CONTAMINACION = 0.02
CORR_MAX = 0.90
SEMILLA = 42
MIN_PERIODOS = 36               # requisito de la rubrica (E0)
