# E2 — Fuente geoespacial (DENUE), linaje y ética

```
src/config.py           municipios, subsectores, campos conservados, CRS, umbrales
src/extractor_denue.py  captura ética DENUE -> E0/data/bronze/denue/ (minimización de datos)
src/geo.py              Puerta de Calidad, GeoPandas, hexágonos, indicadores, mapas, linaje
src/demo_denue.py       Bronce DENUE sintética (solo pruebas)
tests/                  10 pruebas
docs/etica-datos.md     Declaración de Ética y Legalidad
docs/E2/ENTREGA.md      ficha técnica · docs/relatoria-E2.md relatoría
data/                   plata/, oro/, cuarentena/, reportes/, referencia/ (límites municipales opcionales)
```

El linaje Oro -> Bronce de las series de tiempo vive en `E1/e1/src/linaje.py`.

*Fuente: INEGI, DENUE. Este trabajo no representa una postura oficial del INEGI.*
