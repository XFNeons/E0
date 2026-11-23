# E1 — Capas Plata y Oro · Observatorio del Comercio al por Menor en Colima

Pipeline **Bronce → Puerta de Calidad (Pandera) → Plata → Oro** con cuarentena de registros inválidos.

```
src/
  config.py       rutas, catálogo de series, rangos, umbrales
  integracion.py  lectura de Bronce (INEGI + Banxico), tipado, revisiones, diario→mensual
  calidad.py      Puerta de Calidad con Pandera + cuarentena con motivo
  limpieza.py     faltantes, atípicos, escalamiento, discretización, reducción
  pipeline.py     orquestador (python -m src.pipeline [--demo])
  demo_datos.py   Bronce SINTÉTICA con defectos sembrados (solo pruebas)
tests/            13 pruebas sin red
docs/E1/          limpieza.ipynb y ENTREGA.md
docs/             relatoria-E1.md
data/             plata/, oro/, cuarentena/, reportes/ (los escribe el pipeline)
calidad/          registros PSP
```

## Uso rápido

```bash
cd E1/e1
pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m src.pipeline            # datos reales de ../../E0/data/bronze
```

En GitHub Actions corre solo, después de cada captura de Bronce.
