"""Datos sinteticos con la estructura SNIIM y problemas INYECTADOS (para probar sin Bronce real)."""
import numpy as np
import pandas as pd


def generar(carpeta_bronce, seed=7):
    rng = np.random.default_rng(seed)
    carpeta_bronce.mkdir(parents=True, exist_ok=True)
    fechas = pd.date_range("2022-01-03", periods=208, freq="W-MON")        # ~48 meses
    series = [("Aguacate Hass", "Primera", "Caja de 20 kg", "Michoacán", 600),
              ("Aguacate Hass", "Extra", "Caja de 20 kg", "Michoacán", 700),
              ("Limón persa", "Primera", "Kilogramo", "Colima", 25),
              ("Limón persa", "Primera", "Kilogramo", "Veracruz", 22),
              ("Jitomate saladette", "Primera", "Caja de 20 kg", "Sinaloa", 250),
              ("Jitomate saladette", "Extra", "Caja de 20 kg", "Sinaloa", 300)]
    filas = []
    for prod, cal, pres, ori, base in series:
        t = np.arange(len(fechas))
        frec = base * (1 + 0.0015 * t + 0.15 * np.sin(2 * np.pi * t / 52)) * (1 + rng.normal(0, .02, len(t)))
        for j, f in enumerate(fechas):
            filas.append({"Fecha": f.strftime("%d/%m/%Y"), "Producto": prod, "Calidad": cal,
                          "Presentación": pres, "Origen": ori,
                          "Precio Mín": frec[j] * .9, "Precio Max": frec[j] * 1.12, "Precio Frec": frec[j],
                          "Obs.": "" if rng.random() > .05 else "Mercado con poca oferta"})
    d = pd.DataFrame(filas)
    for c in ["Precio Mín", "Precio Max", "Precio Frec"]:
        d[c] = d[c].round(2).astype(object)
    jit = d.index[d["Producto"] == "Jitomate saladette"]
    d.loc[rng.choice(jit, 25, replace=False), "Precio Frec"] = "N/D"          # MAR: por producto
    d.loc[rng.choice(d.index, 10, replace=False), "Precio Mín"] = "N/D"
    for i in rng.choice(d.index, 4, replace=False):                            # atipicos coherentes
        for c in ["Precio Mín", "Precio Max", "Precio Frec"]:
            if isinstance(d.loc[i, c], float):
                d.loc[i, c] = round(d.loc[i, c] * 7, 2)
    d.loc[5, "Precio Frec"] = -50                                              # fuera de rango
    d.loc[8, "Precio Max"] = d.loc[8, "Precio Mín"] if isinstance(d.loc[8, "Precio Mín"], float) else 1  # frec>max
    d.loc[10, "Precio Frec"] = "abc"                                           # no numerico
    d.loc[12, "Fecha"] = "fecha-mala"                                          # fecha invalida
    d.loc[15, "Precio Mín"], d.loc[15, "Precio Max"] = 900.0, 100.0            # min > max
    d["Precio Frec"] = d["Precio Frec"].map(lambda v: f"${v:,.2f}" if isinstance(v, float) else v)  # "$1,234.50"
    d.loc[20, "Origen"] = " MICHOACAN "                                        # variante de texto (se normaliza)
    d = pd.concat([d, d.iloc[[30, 31, 32]]], ignore_index=True)                # duplicados exactos
    d.to_csv(carpeta_bronce / "sniim_demo.csv", index=False, encoding="utf-8-sig")
