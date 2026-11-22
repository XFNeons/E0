"""Pruebas sin red del extractor de la capa Bronce."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import extractor_bronce as ex  # noqa: E402


def respuesta_falsa(payload: dict, status: int = 200):
    r = mock.Mock()
    r.status_code = status
    r.content = json.dumps(payload).encode()
    r.raise_for_status = mock.Mock()
    return r


INEGI = {"Series": [{"OBSERVATIONS": [
    {"TIME_PERIOD": f"{2020 + i // 12}/{i % 12 + 1:02d}", "OBS_VALUE": str(100 + i)} for i in range(40)]}]}
BANXICO = {"bmx": {"series": [{"datos": [
    {"fecha": f"{d:02d}/{m:02d}/2023", "dato": "11.5"} for m in range(1, 13) for d in (1, 15)]}]}}


class TestParsers(unittest.TestCase):
    def test_periodos_inegi(self):
        self.assertEqual(len(ex.periodos_inegi(INEGI)), 40)

    def test_banxico_cuenta_meses_no_dias(self):
        meses = {ex.a_mes(p) for p in ex.periodos_banxico(BANXICO)}
        self.assertEqual(len(meses), 12)

    def test_a_mes(self):
        self.assertEqual(ex.a_mes("2024/03"), "2024-03")
        self.assertEqual(ex.a_mes("15/03/2024"), "2024-03")

    def test_token_oculto(self):
        self.assertNotIn("abc123", ex.ocultar_token("https://x/abc123?type=json", "abc123"))

    def test_config_valida(self):
        cfg = ex.cargar_config()
        self.assertGreaterEqual(cfg["min_periodos"], 36)
        self.assertGreaterEqual(len(cfg["fuentes"]), 2)


class TestCaptura(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.p = [mock.patch.object(ex, "RAIZ", self.tmp),
                  mock.patch.object(ex, "BRONCE", self.tmp / "data/bronze"),
                  mock.patch.object(ex, "MANIFIESTO", self.tmp / "data/bronze/_manifiesto.csv")]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()

    def test_guarda_crudo_e_idempotente(self):
        serie = {"clave": "prueba", "id": "1"}
        with mock.patch.object(ex.requests, "get", return_value=respuesta_falsa(INEGI)):
            f1 = ex.capturar_serie("inegi", serie, "https://x/TOKEN", "TOKEN", {}, ex.periodos_inegi, 36)
            f2 = ex.capturar_serie("inegi", serie, "https://x/TOKEN", "TOKEN", {}, ex.periodos_inegi, 36)
        self.assertEqual(f1["resultado"], "nuevo")
        self.assertEqual(f2["resultado"], "sin_cambios")
        self.assertEqual(f1["n_periodos_mensuales"], 40)
        guardado = json.loads((self.tmp / f1["archivo"]).read_text())
        self.assertEqual(guardado, INEGI)  # se guarda sin transformar
        manifiesto = (self.tmp / "data/bronze/_manifiesto.csv").read_text()
        self.assertNotIn("TOKEN/", manifiesto.replace("***TOKEN***", ""))


if __name__ == "__main__":
    unittest.main()
