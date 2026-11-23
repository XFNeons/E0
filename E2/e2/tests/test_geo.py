"""Pruebas de la fuente geoespacial (DENUE) con Bronce sintética. Desde E2/e2:
    python -m unittest discover -s tests -v
"""
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config, geo  # noqa: E402
from src.demo_denue import generar  # noqa: E402

HAY_GEOPANDAS = importlib.util.find_spec("geopandas") is not None


class TestGeoDemo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.bronce = generar(cls.tmp / "bronce")
        cls.salida = cls.tmp / "salida"
        cls.reporte = geo.correr(cls.bronce, cls.salida, cls.tmp / "img")
        cls.cuarentena = pd.read_csv(cls.salida / "cuarentena" / "cuarentena_denue.csv", dtype=str)
        cls.mun = pd.read_csv(cls.salida / "oro" / "comercio_municipios.csv", dtype={"cve_mun": str})
        cls.linaje = pd.read_csv(cls.salida / "oro" / "linaje_geo.csv", dtype=str)

    def test_minimizacion_sin_datos_de_contacto(self):
        for archivo in (self.bronce / "denue").glob("establecimientos_*/*.json"):
            registro = json.loads(archivo.read_text(encoding="utf-8"))["respuesta"][0]
            for campo in ["Nombre", "Razon_social", "Telefono", "Correo_e", "Sitio_internet", "Calle"]:
                self.assertNotIn(campo, registro)

    def test_cuarentena_con_motivo(self):
        reglas = " ".join(self.cuarentena["regla"])
        for r in ["in_range", "sector_46", "municipio_consistente", "not_nullable", "duplicado_exacto"]:
            self.assertIn(r, reglas)
        self.assertTrue(self.cuarentena["motivo"].str.len().gt(0).all())

    def test_nada_se_pierde(self):
        p = self.reporte["puerta"]
        self.assertEqual(p["evaluados"], p["validos"] + p["cuarentena"])

    def test_indicadores_municipales(self):
        self.assertEqual(len(self.mun), 10)
        self.assertAlmostEqual(self.mun["pct_del_estado"].sum(), 100, delta=0.1)
        self.assertTrue(self.mun["dist_mediana_competidor_m"].gt(0).all())
        self.assertLess(self.mun["diferencia_pct"].abs().median(), 10)

    def test_cada_fila_de_oro_es_rastreable(self):
        self.assertTrue(self.mun["archivos_bronce"].notna().all())
        self.assertTrue(self.mun["fecha_ingesta"].notna().all())
        rastreadas = set(self.linaje.loc[self.linaje.tabla.eq("comercio_municipios"), "id_fila_oro"])
        self.assertEqual(rastreadas, set(self.mun["id_fila_oro"]))
        self.assertEqual(self.linaje["clee"].nunique(), self.reporte["puerta"]["validos"])

    def test_huella_bronce_coincide(self):
        for ruta, huella in self.linaje[["ruta_bronce", "sha256_bronce"]].drop_duplicates().itertuples(index=False):
            self.assertEqual(hashlib.sha256(Path(ruta).read_bytes()).hexdigest(), huella)

    def test_comparativo_estados(self):
        comp = pd.read_csv(self.salida / "oro" / "comparativo_estados.csv")
        self.assertEqual(set(comp["entidad"]), set(config.ESTADOS_COMPARACION.values()))
        cols = [c for c in comp if c.startswith("pct_estrato_")]
        self.assertTrue((comp[cols].sum(axis=1).sub(100).abs() < 0.1).all())

    @unittest.skipUnless(HAY_GEOPANDAS, "GeoPandas no instalado")
    def test_hexagonos_y_supresion(self):
        import geopandas as gpd
        hexes = gpd.read_file(self.salida / "oro" / "comercio_hexagonos.geojson")
        self.assertEqual(hexes.crs.to_epsg(), 4326)
        self.assertTrue(hexes.loc[hexes["suprimido"], "establecimientos"].isna().all())
        self.assertTrue(hexes.loc[~hexes["suprimido"], "establecimientos"].ge(config.UMBRAL_SUPRESION).all())
        self.assertTrue(self.linaje["tabla"].eq("comercio_hexagonos").any())

    @unittest.skipUnless(HAY_GEOPANDAS, "GeoPandas no instalado")
    def test_mapas_generados(self):
        for nombre in ["mapa_densidad_hexagonos.png", "mapa_municipios.png"]:
            self.assertTrue((self.tmp / "img" / nombre).stat().st_size > 10_000)

    @unittest.skipUnless(HAY_GEOPANDAS, "GeoPandas no instalado")
    def test_malla_hexagonal_cubre_sin_huecos(self):
        malla = geo.malla_hexagonal((0, 0, 10_000, 10_000), 1000)
        self.assertAlmostEqual(malla.geometry.area.iloc[0], 1.5 * 3 ** 0.5 * 1000 ** 2, delta=1)
        self.assertTrue(malla.geometry.is_valid.all())


if __name__ == "__main__":
    unittest.main()
