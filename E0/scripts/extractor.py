import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

# URL de descarga directa del archivo CSV de aguacate Hass calidad Extra
# (Verificar en figshare: el enlace puede variar; usar el botón "Download" del archivo)
URL = "https://figshare.com/ndownloader/files/36006173"  # Ejemplo; reemplazar por el enlace real del archivo CSV

def main():
    carpeta_bronce = Path("datos/bronce")
    carpeta_bronce.mkdir(parents=True, exist_ok=True)

    try:
        respuesta = requests.get(URL, timeout=60)
        respuesta.raise_for_status()

        # Guardar el archivo crudo con la fecha de ejecución
        nombre_archivo = f"aguacate_hass_extra_{datetime.now().strftime('%Y%m%d')}.csv"
        ruta_archivo = carpeta_bronce / nombre_archivo
        ruta_archivo.write_bytes(respuesta.content)

        # Validación rápida: leer las primeras filas
        df = pd.read_csv(ruta_archivo)
        print(f"Archivo guardado: {ruta_archivo}")
        print(f"Filas: {len(df)}, Columnas: {list(df.columns)}")

    except Exception as e:
        print(f"Error al descargar o guardar los datos: {e}")
        raise

if __name__ == "__main__":
    main()