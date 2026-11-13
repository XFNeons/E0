import pandas as pd
from src import config as C
from src import limpieza as L
from src.demo_datos import generar
from src.pipeline import ejecutar


def test_a_numero_formatos():
    r = L.a_numero(pd.Series(["1,234.50", "1234,5", "$99", "abc", None]))
    assert r.iloc[0] == 1234.5 and r.iloc[1] == 1234.5 and r.iloc[2] == 99
    assert pd.isna(r.iloc[3]) and pd.isna(r.iloc[4])


def test_normalizar_texto():
    assert L.normalizar_texto(pd.Series(["  MICHOACÁN "])).iloc[0] == "michoacan"


def test_pipeline_no_pierde_registros_en_silencio(tmp_path):
    generar(tmp_path / "bronce")
    rep = ejecutar(tmp_path)
    cuar = pd.read_csv(tmp_path / "cuarentena" / "cuarentena.csv")
    assert len(cuar) == rep["puerta_calidad"]["cuarentena"] > 0
    assert (cuar["_motivo_cuarentena"].fillna("") != "").all()
    # conservacion: bronce = plata + cuarentena
    assert rep["filas_bronce"]["A"] == rep["puerta_calidad"]["validos"] + len(cuar)
    assert rep["cumple_min_periodos"]


def test_plata_coherente(tmp_path):
    generar(tmp_path / "bronce")
    ejecutar(tmp_path)
    plata = pd.read_csv(tmp_path / "plata" / "plata.csv")
    for col, (lo, hi) in C.RANGOS.items():
        assert plata[col].notna().all() and plata[col].between(lo, hi).all()
    assert not plata.duplicated(C.LLAVES).any()
    assert (plata["precio_min"] <= plata["precio_max"]).all()


def test_n_d_es_faltante_no_error(tmp_path):
    generar(tmp_path / "bronce")
    cuar_txt = ejecutar(tmp_path)["puerta_calidad"]["motivos"]
    assert not any("precio_min no numerico" in m for m in cuar_txt)   # N/D se imputa, no se rechaza
