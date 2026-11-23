"""Configuración de la fuente geoespacial (DENUE) — Entrega E2."""
from __future__ import annotations

from pathlib import Path

PAQUETE = Path(__file__).resolve().parents[1]        # E2/e2
REPO = PAQUETE.parents[1]
BRONCE = REPO / "E0" / "data" / "bronze"              # misma capa Bronce del observatorio
BRONCE_DENUE = BRONCE / "denue"
DATOS = PAQUETE / "data"
REFERENCIA = DATOS / "referencia"                     # capa opcional de límites municipales
IMG = PAQUETE / "docs" / "E2" / "img"

API_DENUE = "https://www.inegi.org.mx/app/api/denue/v1/consulta"
ROBOTS_INEGI = "https://www.inegi.org.mx/robots.txt"
TOKEN_ENV = "DENUE_TOKEN"
TAM_PAGINA = 1000
PAUSA_SEG = 2

ENTIDAD = "06"
MUNICIPIOS = {   # Catálogo Único de Claves Geoestadísticas de INEGI
    "001": "Armería", "002": "Colima", "003": "Comala", "004": "Coquimatlán",
    "005": "Cuauhtémoc", "006": "Ixtlahuacán", "007": "Manzanillo", "008": "Minatitlán",
    "009": "Tecomán", "010": "Villa de Álvarez",
}
ESTADOS_COMPARACION = {"06": "Colima", "14": "Jalisco", "16": "Michoacán", "18": "Nayarit"}
SECTOR = "46"
SUBSECTORES = {
    "461": "Abarrotes, alimentos, bebidas, hielo y tabaco",
    "462": "Tiendas de autoservicio y departamentales",
    "463": "Productos textiles, bisutería, accesorios de vestir y calzado",
    "464": "Artículos para el cuidado de la salud",
    "465": "Artículos de papelería, esparcimiento y uso personal",
    "466": "Enseres domésticos, computadoras y decoración",
    "467": "Ferretería, tlapalería y vidrios",
    "468": "Vehículos de motor, refacciones y combustibles",
    "469": "Intermediación y comercio al por menor por internet",
}
ESTRATOS = {1: "0 a 5 personas", 2: "6 a 10 personas", 3: "11 a 30 personas", 4: "31 a 50 personas",
            5: "51 a 100 personas", 6: "101 a 250 personas", 7: "251 y más personas"}

# Minimización de datos (privacidad): SOLO estos campos de la API se guardan en Bronce.
# Se descartan en la captura: Nombre, Razon_social, Telefono, Correo_e, Sitio_internet, Calle,
# Num_Exterior, Num_Interior, numero_local, EDIFICIO_PISO, Colonia y nombres de corredor.
CAMPOS_CONSERVADOS = [
    "CLEE", "Id", "Clase_actividad", "Estrato", "Tipo", "CP", "Ubicacion", "Longitud", "Latitud",
    "AGEB", "Manzana", "CLASE_ACTIVIDAD_ID", "SECTOR_ACTIVIDAD_ID", "SUBSECTOR_ACTIVIDAD_ID",
    "RAMA_ACTIVIDAD_ID", "SUBRAMA_ACTIVIDAD_ID", "Tipo_Asentamiento", "Fecha_Alta", "AreaGeo",
]

# Caja envolvente de la parte continental de Colima (las islas Revillagigedo quedan fuera a propósito)
LAT_MIN, LAT_MAX = 18.60, 19.60
LON_MIN, LON_MAX = -104.75, -103.45

CRS_GEO = "EPSG:4326"
CRS_METRICO = "EPSG:6372"         # México ITRF2008 / LCC: distancias y áreas en metros
LADO_HEX_M = 1000                 # hexágonos de 1 km de lado
UMBRAL_SUPRESION = 3              # celdas con menos de 3 establecimientos no se publican
MESES_ALTA_RECIENTE = 24
