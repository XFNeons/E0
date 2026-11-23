# Ficha de entrega técnica — E1

| Campo | Valor |
|---|---|
| Proyecto | Observatorio del Comercio al por Menor en Colima (OCMC) |
| Repositorio | https://github.com/XFNeons/E0 (carpeta `E1/e1/`) |
| Tag | `e1` |
| Fecha de entrega | `[AAAA-MM-DD]` |
| Integrantes | Andrik H. García Morales `[agregar resto del equipo]` |
| Corrida de Actions que generó Plata/Oro | `[URL de la corrida en verde]` |

## 1. Arquitectura

```
E0/data/bronze/  (JSON crudo, lo escribe el extractor de E0)
      │
      ▼  src/integracion.py   lectores por fuente, tipado, revisiones, diario→mensual
tabla larga unificada
      │
      ▼  src/calidad.py       Puerta de Calidad (Pandera, lazy=True)
      ├──► data/cuarentena/cuarentena.csv   (rechazados + motivo, append-only)
      ▼
data/plata/plata_largo.csv
      │
      ▼  src/limpieza.py      faltantes, atípicos, escalamiento, discretización, reducción
data/plata/plata_ancho_limpio.csv
      │
      ▼
data/oro/panel_colima_mensual.csv   (E1 y E2)
data/oro/panel_entidades.csv        (E3)
data/oro/parametros_escalado.json
data/reportes/reporte_calidad.json  (+ diagnóstico de faltantes, atípicos, conflictos)
```

Todo corre en automático en GitHub Actions (`.github/workflows/captura-bronce.yml`) después de la captura semanal de Bronce.

## 2. Checklist de entregables

| Requisito | Dónde | Estado |
|---|---|---|
| Faltantes: diagnóstico MCAR/MAR/MNAR e imputación justificada | `limpieza.diagnosticar_faltantes`, `limpieza.imputar`, notebook §3 | ☑ |
| Atípicos y ruido (Z robusto, IQR, Isolation Forest) | `limpieza.detectar_atipicos`, `tratar_atipicos`, `isolation_forest`, notebook §4 | ☑ |
| Normalización Min-Max y Z-score | `limpieza.ajustar_escaladores` / `aplicar_escaladores`, notebook §5 | ☑ |
| Discretización y jerarquías conceptuales | `limpieza.discretizar`, `jerarquia_tiempo`, notebook §6 | ☑ |
| Reducción (agregación, ventana, selección de variables) | `integracion.a_mensual`, `limpieza.seleccionar_variables`, notebook §7 | ☑ |
| Integración y resolución de conflictos de esquema y tipos | `src/integracion.py`, notebook §1 | ☑ |
| Puerta de Calidad con Pandera y cuarentena con motivo | `src/calidad.py`, notebook §2 | ☑ |
| Pruebas automáticas | `tests/test_pipeline.py` (13 pruebas) | ☑ |
| Notebook ejecutado con salidas y datos reales | `docs/E1/limpieza.ipynb` | ☐ |
| Relatoría de etapa | `docs/relatoria-E1.md` | ☐ completar |

## 3. Cómo ejecutar

```bash
cd E1/e1
pip install -r requirements.txt
python -m unittest discover -s tests -v   # pruebas con Bronce sintética
python -m src.pipeline --demo             # demo -> data_demo/ (no se sube)
python -m src.pipeline                    # datos reales de E0/data/bronze -> data/
jupyter notebook docs/E1/limpieza.ipynb   # Kernel -> Restart & Run All, y guardar
```

Códigos de salida del pipeline: `0` correcto, `2` Puerta cerrada por falla de esquema, `3` Bronce vacía.

## 4. Reglas de la Puerta de Calidad

| Regla | Columna | Si falla |
|---|---|---|
| Esquema estricto (columnas y tipos exactos) | todas | Puerta cerrada, no se escribe Plata |
| Serie, fuente, entidad y variable en catálogo | `serie`, `fuente`, `entidad`, `variable` | cuarentena |
| Campos obligatorios no vacíos | `serie` … `fecha`, `origen` | cuarentena |
| Fecha entre 2005-01-01 y hoy | `fecha` | cuarentena |
| Valor original numérico o faltante declarado (`N/E`) | `valor_crudo`, `valor` | cuarentena |
| Valor dentro del rango plausible de su variable | `valor` | cuarentena |
| Unidad igual a la del catálogo | `unidad` | cuarentena |
| Un registro por serie y mes | `serie` + `fecha` | cuarentena |

## 5. Resultados (copiar de `data/reportes/reporte_calidad.json`)

| Métrica | Valor |
|---|---|
| Registros evaluados | `[ ]` |
| Registros válidos → Plata | `[ ]` |
| Registros en cuarentena | `[ ]` |
| Tasa de aprobación | `[ ]` |
| Conflictos de revisión resueltos | `[ ]` |
| Celdas imputadas (lineal / estacional) | `[ ]` |
| Atípicos reemplazados / conservados | `[ ]` |
| Variables seleccionadas para Oro | `[ ]` |

## 6. Pendientes conocidos

1. Sustituir los IDs `PENDIENTE` de la EMEC en `E0/config/fuentes.json`. Sin ellos, Oro solo tiene INPC, TIIE y tipo de cambio.
2. Ejecutar el notebook con los datos reales y guardarlo con salidas.
