# Ficha de entrega técnica — E2

| Campo | Valor |
|---|---|
| Proyecto | Observatorio del Comercio al por Menor en Colima (OCMC) |
| Repositorio | https://github.com/XFNeons/E0 (carpeta `E2/e2/`) |
| Tag | `e2` |
| Fecha de entrega | `[AAAA-MM-DD]` |
| Integrantes | Andrik H. García Morales `[agregar resto del equipo]` |
| Corrida de Actions | `[URL de la corrida en verde]` |

## 1. Fuente especializada elegida: geoespacial (DENUE + GeoPandas)

**Por qué el DENUE:** la EMEC (E0/E1) dice *cuánto* vende el comercio de Colima, pero no *dónde* está. El DENUE ubica cada establecimiento del sector 46 y permite medir concentración, competencia y estructura por tamaño a nivel municipal y por zonas.

| Componente | Archivo |
|---|---|
| Extractor ético (Cuantificar + BuscarAreaActEstr, minimización, robots.txt, manifiesto compartido) | `src/extractor_denue.py` |
| Tipado, Puerta de Calidad (Pandera) y cuarentena | `src/geo.py` → `tipar`, `esquema`, `aplicar_puerta` |
| GeoPandas: EPSG:4326 → EPSG:6372, unión espacial con el Marco Geoestadístico, malla hexagonal de 1 km | `src/geo.py` → `a_geodataframe`, `cargar_municipios`, `malla_hexagonal`, `contar_en_hexagonos` |
| Indicadores por municipio: establecimientos, % micro, % altas recientes, distancia mediana al competidor del mismo subsector, densidad por km² | `src/geo.py` → `indicadores_municipio`, `distancia_competidor` |
| Comparativo de estructura Colima vs. Jalisco, Michoacán y Nayarit (insumo para E3) | `src/geo.py` → `comparativo_estados` |
| Contraste entre fuentes (puntos descargados vs. conteo oficial) | `src/geo.py` → `consistencia_con_cuantificar` |
| Visualización cartográfica | `docs/E2/img/mapa_densidad_hexagonos.png`, `mapa_municipios.png`, `mapa_interactivo.html` |

### Salidas en Oro (`data/oro/`)

| Archivo | Contenido |
|---|---|
| `comercio_municipios.csv` / `.geojson` | 10 municipios con indicadores, densidad y linaje |
| `comercio_hexagonos.geojson` | Conteo y densidad por hexágono; celdas con menos de 3 establecimientos suprimidas |
| `comparativo_estados.csv` | % por estrato y subsector en 4 estados |
| `linaje_geo.csv` | Fila de Oro → CLEE → archivo Bronce, con SHA-256 y fecha de ingesta |

## 2. Declaración de Ética y Legalidad

`docs/etica-datos.md`: términos de uso de INEGI y Banxico, análisis de robots.txt, licencias, privacidad (minimización y supresión), sesgos con su mitigación, y usos no permitidos.

## 3. Linaje y trazabilidad

| Capa | Campos de linaje |
|---|---|
| Bronce | Nombre del archivo = fecha y hora UTC de ingesta; `_manifiesto.csv` con URL sin token, SHA-256 y resultado |
| Plata (E1) | `id_registro`, `id_bronce` (archivo + periodo, o rango de días si es promedio), `ruta_bronce`, `sha256_bronce`, `captura` |
| Plata (E2) | `id_registro`, `id_bronce` (archivo + CLEE), `ruta_bronce`, `sha256_bronce`, `captura` |
| Oro (todas las tablas) | `id_fila_oro`, `fecha_ingesta`, `archivos_bronce` en cada fila; detalle en `linaje_oro.csv` y `linaje_geo.csv` |

Valores imputados en E1: `linaje_oro.csv` incluye `vecino_anterior` y `vecino_posterior`, los registros Bronce de los que se interpoló. Si el original está en cuarentena, la columna `origen` lo indica.

Comandos para rastrear un registro (desde `E1/e1`):

```bash
python -m src.linaje panel_colima_mensual 2024-03-01   # de dónde sale cada columna de esa fila
python -m src.linaje panel_entidades 2024-03-01 --entidad Jalisco
python -m src.linaje --verificar                       # archivos Bronce existen y no cambiaron
```

La Puerta de Calidad de E1 tiene una regla nueva, `linaje_completo`: un registro sin archivo de origen o sin fecha de ingesta va a cuarentena.

## 4. Checklist

| Requisito | Estado |
|---|---|
| Fuente especializada integrada (geoespacial con GeoPandas y mapas) | ☑ código · ☐ datos reales |
| `docs/etica-datos.md` | ☑ · ☐ pegar evidencia de robots.txt |
| Linaje Oro → Bronce con fecha de ingesta | ☑ |
| Pruebas automáticas (E1: 17, E2: 10) | ☑ |
| `docs/E2/ENTREGA.md` y `docs/relatoria-E2.md` | ☑ · ☐ completar resultados |

## 5. Cómo ejecutar

```bash
# Captura (requiere DENUE_TOKEN; también corre en Actions)
python E2/e2/src/extractor_denue.py

cd E2/e2
pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m src.geo --demo     # con datos sintéticos -> data_demo/
python -m src.geo            # con la Bronce real
```

Capa opcional de límites municipales: descarga el **Marco Geoestadístico** de Colima desde el sitio de INEGI y copia los archivos `06mun.*` (`.shp`, `.shx`, `.dbf`, `.prj`) a `E2/e2/data/referencia/`. Con ella se calculan la densidad por km² y el mapa coroplético, y se verifica que el municipio de cada punto coincida con el polígono.

## 6. Resultados (copiar de `data/reportes/reporte_geo.json`)

| Métrica | Valor |
|---|---|
| Establecimientos descargados / válidos / en cuarentena | `[ ]` |
| Diferencia contra Cuantificar (mediana por municipio) | `[ ]` |
| Hexágonos publicados / suprimidos | `[ ]` |
| % de puntos cuyo municipio coincide con el polígono del Marco | `[ ]` |

## 7. Pendientes

1. Crear el secret `DENUE_TOKEN` y correr el workflow (botón *Run workflow*).
2. (Opcional) Subir los límites municipales a `data/referencia/`.
3. Pegar la evidencia de robots.txt en `docs/etica-datos.md`.
