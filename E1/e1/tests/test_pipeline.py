"""Pruebas del pipeline E1 con la Bronce sintética (sin red). Correr desde E1/e1:
    python -m unittest discover -s tests -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import calidad, integracion, limpieza, linaje, pipeline  # noqa: E402
from src.demo_datos import generar  # noqa: E402


class TestPipelineDemo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.bronce = generar(cls.tmp / "bronce")
        cls.salida = cls.tmp / "salida"
        cls.reporte = pipeline.correr(cls.bronce, cls.salida)
        cls.cuarentena = pd.read_csv(cls.salida / "cuarentena" / "cuarentena.csv")

    # ---------------- integración
    def test_revision_resuelta_con_la_ultima_captura(self):
        self.assertEqual(self.reporte["integracion"]["conflictos_de_revision"], 1)
        plata = pd.read_csv(self.salida / "plata" / "plata_largo.csv", parse_dates=["fecha"])
        ultimo = plata[plata.serie.eq("emec_menor_ingresos_colima")].sort_values("fecha").iloc[-1]
        self.assertEqual(ultimo["archivo"], "2026-11-16_131700.json")

    def test_banxico_diario_agregado_a_mensual(self):
        plata = pd.read_csv(self.salida / "plata" / "plata_largo.csv", parse_dates=["fecha"])
        tiie = plata[plata.serie.eq("tiie_28d")]
        self.assertTrue((tiie["fecha"].dt.day == 1).all())
        self.assertFalse(tiie.duplicated("fecha").any())

    def test_coma_de_miles(self):
        self.assertEqual(integracion.parsear_valor(pd.Series(["1,234.5"])).iloc[0], 1234.5)

    # ---------------- puerta de calidad / cuarentena
    def test_cuarentena_con_motivo(self):
        self.assertTrue(self.cuarentena["motivo"].notna().all())
        crudos = set(self.cuarentena["valor_crudo"].astype(str))
        for esperado in ["1O4.2", "-5", "abc"]:
            self.assertIn(esperado, crudos)
        self.assertTrue(self.cuarentena["serie"].eq("serie_desconocida").any())

    def test_nada_se_pierde_en_silencio(self):
        p = self.reporte["puerta_de_calidad"]
        self.assertEqual(p["registros_evaluados"], p["registros_validos"] + p["registros_en_cuarentena"])

    def test_faltante_declarado_no_va_a_cuarentena(self):
        self.assertFalse(self.cuarentena["valor_crudo"].astype(str).eq("N/E").any())

    def test_falla_de_esquema_cierra_la_puerta(self):
        df = pd.DataFrame({"serie": ["tiie_28d"]})
        with self.assertRaises(calidad.PuertaCerrada):
            calidad.aplicar_puerta(df)

    # ---------------- limpieza
    def test_imputacion(self):
        metodos = self.reporte["celdas_por_metodo"]
        self.assertEqual(metodos.get("interpolacion_lineal"), 5)
        self.assertEqual(metodos.get("estacional_escalada"), 6)

    def test_pico_reemplazado_y_covid_conservado(self):
        at = pd.read_csv(self.salida / "reportes" / "atipicos.csv", parse_dates=["fecha"])
        col = at[at.serie.eq("ingresos_colima")].set_index("fecha")["tratamiento"]
        self.assertEqual(col[pd.Timestamp("2017-05-01")], "reemplazado_por_interpolacion")
        self.assertEqual(col[pd.Timestamp("2020-04-01")], "conservado_evento_conocido")

    def test_z_robusto_ignora_un_valor_extremo(self):
        z = limpieza.z_robusto(pd.Series([1, 2, 3, 4, 100.0]))
        self.assertGreater(z.iloc[-1], 3.5)
        self.assertLess(abs(z.iloc[2]), 0.01)

    # ---------------- oro
    def test_escaladores_sin_fuga(self):
        panel = pd.read_csv(self.salida / "oro" / "panel_colima_mensual.csv")
        ent = panel[panel.conjunto.eq("entrenamiento")]
        self.assertAlmostEqual(ent["ingresos_colima_minmax"].min(), 0.0, places=6)
        self.assertAlmostEqual(ent["ingresos_colima_minmax"].max(), 1.0, places=6)
        self.assertAlmostEqual(ent["ingresos_colima_z"].mean(), 0.0, places=6)

    def test_discretizacion_y_jerarquias(self):
        panel = pd.read_csv(self.salida / "oro" / "panel_colima_mensual.csv")
        for col in ["temporada", "tiie_nivel", "crecimiento_ingresos", "trimestre", "semestre", "region"]:
            self.assertIn(col, panel.columns)
        self.assertEqual(set(panel["temporada"]), {"alta", "baja"})
        ent = pd.read_csv(self.salida / "oro" / "panel_entidades.csv")
        self.assertEqual(ent["entidad"].nunique(), 4)

    # ---------------- linaje (E2)
    def test_cada_fila_de_oro_tiene_linaje(self):
        for tabla in ["panel_colima_mensual", "panel_entidades"]:
            t = pd.read_csv(self.salida / "oro" / f"{tabla}.csv")
            self.assertTrue(t["archivos_bronce"].notna().all(), tabla)
            self.assertTrue(t["fecha_ingesta"].notna().all(), tabla)
            self.assertTrue(t["id_fila_oro"].is_unique, tabla)

    def test_linaje_llega_al_archivo_bronce_y_no_cambio(self):
        lin = pd.read_csv(self.salida / "oro" / "linaje_oro.csv")
        self.assertTrue(linaje.verificar(lin).empty)
        obs = lin[lin["metodo"].eq("observado")]
        self.assertTrue(obs["id_bronce"].str.contains("#").all())

    def test_imputado_apunta_a_sus_vecinos(self):
        lin = pd.read_csv(self.salida / "oro" / "linaje_oro.csv")
        imp = lin[lin["metodo"].eq("interpolacion_lineal")]
        self.assertGreater(len(imp), 0)
        self.assertTrue(imp["vecino_anterior"].notna().all() and imp["vecino_posterior"].notna().all())

    def test_promedio_banxico_cita_rango_de_dias(self):
        plata = pd.read_csv(self.salida / "plata" / "plata_largo.csv")
        tiie = plata[plata["serie"].eq("tiie_28d")]
        self.assertTrue(tiie["id_bronce"].str.contains(r"#\d{2}/\d{2}/\d{4}\.\.").all())
        self.assertTrue(plata["id_registro"].is_unique)

    def test_reporte_json(self):
        r = json.loads((self.salida / "reportes" / "reporte_calidad.json").read_text(encoding="utf-8"))
        self.assertIn("puerta_de_calidad", r)
        self.assertTrue(np.isfinite(r["puerta_de_calidad"]["tasa_aprobacion"]))


if __name__ == "__main__":
    unittest.main()
