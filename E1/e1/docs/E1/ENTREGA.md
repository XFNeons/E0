# Ficha técnica de entrega — E1 (Capa Plata, Limpieza y Puerta de Calidad)

**Equipo:**  **Observatorio:** precios de abasto (SNIIM / central de abastos) 
 **Tag:** `e1`  **Fecha:** [13/11/2026]

## 1. Cómo reproducir
```bash
pip install -r requirements.txt
python -m pytest -q          # pruebas
python -m src.pipeline       # Bronce -> Plata -> Oro (+ cuarentena y reporte)
```
Automatización: `.github/workflows/pipeline-e1.yml` (manual, en cada push a `src/` y semanal).

## 2. Mapa de entregables
| Requisito de la rúbrica | Dónde está |
|---|---|
| Atípicos y ruido (IQR, Z robusto, Isolation Forest) | `src/limpieza.py::detectar_atipicos`, `tratar_atipicos` · notebook §5 |
| Normalización Min-Max y Z-Score | `src/limpieza.py::normalizar` · notebook §6 |
| Discretización y jerarquías conceptuales | `src/limpieza.py::discretizar` · notebook §6 |
| Reducción (agregación, selección, muestreo) | `src/limpieza.py::agregar_periodo`, `seleccionar_variables`, `muestra_estratificada` · notebook §7 |
| Integración y conflictos de esquema/tipos | `src/integracion.py` · notebook §1–2 |
| Puerta de Calidad (Pandera) + cuarentena con motivo | `src/calidad.py` · `data/cuarentena/cuarentena.csv` |
| Relatoría | `docs/relatoria-E1.md` |

## 3. Resultados (copiar de `data/reportes/reporte_calidad.json`)
| Métrica | Valor |
|---|---|
| Filas en Bronce (por fuente) |  |
| Series de precios (producto·calidad·presentación·origen) | [Producto] |
| Registros válidos → Plata | [Calidad] |
| Registros en cuarentena | [Presentacion] |
| Motivos principales de cuarentena | [Origen] |
| Periodos distintos en Plata (≥ 36) | [PrecioMin] |
| % faltante por variable y mecanismo | [PrecioMax] |
| Atípicos tratados por consenso | [PrecioFrec] |

## 4. Decisiones y supuestos
- Unidad de análisis: *serie* = producto + calidad + presentación + origen. Todo (imputación, atípicos, normalización) se calcula dentro de cada serie; los precios de productos distintos no son comparables.
- `N/D` se trata como faltante legítimo, no como error.
- Imputación: interpolación lineal por serie (máx. 3 observaciones) → mediana de la serie. Sin mediana global; lo no imputable va a cuarentena.
- Regla de coherencia en la Puerta de Calidad: `precio_min ≤ precio_frec ≤ precio_max`.
- Atípicos: winsorización a límites IQR solo si ≥2 de 3 detectores coinciden; se conserva `<var>_original`. Series con < 8 observaciones no se evalúan.
- Registros inválidos nunca se borran: van a cuarentena con `_motivo_cuarentena`.
- Normalización (Min-Max/Z-Score) por serie sobre todo el histórico; en E2 deberá ajustarse solo con entrenamiento (evitar fuga).
- [COMPLETAR supuestos propios del sector]

## 5. Calidad (PSP)
- Registros de tiempo y defectos de E1 actualizados en `calidad/tiempo-<nombre>.csv` y `calidad/defectos-tiempo-MisaelReyes.csv`.
- Avance de los 3 objetivos de calidad definidos en E0: 
| Objetivo de calidad | Meta | Resultado en E1 | Evidencia | Estado |
|---|---|---|---|---|
| 1. Completitud de la serie histórica: cubrir al menos 36 periodos mensuales en la capa Plata | ≥ 36 periodos | [ ] periodos | data/reportes/reporte_calidad.json (periodos_distintos) | [Cumplido / Parcial] |

| 2. Validez de los datos: ningún registro fuera de rango, incoherente o duplicado en Plata; todo registro rechazado queda en cuarentena con motivo | 0 inválidos en Plata; 100% de rechazados con motivo | [ ] inválidos en Plata; [ ] registros en cuarentena, todos con motivo | tests/test_pipeline.py y data/cuarentena/cuarentena.csv | [Cumplido / Parcial] |

| 3. Calidad del proceso (PSP): corregir el 100% de los defectos detectados y mantener la densidad de defectos en 1 o menos por hora trabajada | 100% corregidos; ≤ 1 defecto/hora | [ ] defectos / [ ] horas = [ ] por hora; [ ]% corregidos | calidad/tiempo-MisaelReyes.csv y calidad/defectos-MisaelReyes.csv | [Cumplido / Parcial] |