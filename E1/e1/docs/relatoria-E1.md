# Relatoría de etapa — E1

**Periodo:** [13/11/2026]

## 1. ¿Qué nos propusimos?
Pasar de datos crudos (Bronce) a datos confiables (Plata/Oro) con una Puerta de Calidad automática. [COMPLETAR en 2–3 líneas]

## 2. ¿Qué hicimos?
- Integramos [ ] fuentes de precios de abasto (SNIIM [y figshare]) en un esquema común. Resolvimos encabezados con acentos y puntos ("Precio Mín", "Obs."), formatos de fecha, valores con `$` y comas, "N/D" como dato faltante legítimo y registros duplicados. Cada serie de precios se define por producto, calidad, presentación y origen.
- Puerta de Calidad (Pandera): [ ] registros fueron a cuarentena por [motivos principales: fuera de rango / incoherencia entre precio mínimo, frecuente y máximo / duplicados / valores no numéricos / fechas inválidas]. Cada registro rechazado conserva su motivo en `data/cuarentena/cuarentena.csv`; ninguno se borra en silencio.
- Faltantes: [ ]% en `precio_frec` y [ ]% en `precio_min`. Probamos el mecanismo contra las demás variables con Mann-Whitney y chi-cuadrada (corrección de Bonferroni) y resultó [MCAR no rechazado / MAR probable, asociado a ___]. MNAR no puede probarse con los datos observados; lo discutimos con conocimiento del sector: [justificar si "N/D" aparece cuando hay escasez o el precio se dispara]. Imputamos por interpolación lineal dentro de cada serie (máximo 3 observaciones consecutivas), luego mediana de la serie. No usamos mediana global porque mezclaría precios de productos distintos. Lo no imputable fue a cuarentena.
- Atípicos: aplicamos tres detectores (IQR por serie, Z-score robusto con MAD sobre mediana móvil e Isolation Forest sobre precio relativo a la mediana de su serie). Se detectaron [ ] por IQR, [ ] por Z robusto y [ ] por Isolation Forest, y [ ] coincidieron en al menos 2 de 3. Decisión: winsorizar solo esos casos a los límites IQR y conservar el valor original en `<variable>_original`, porque [razón de dominio: p. ej. un salto de precio por escasez real no debe eliminarse].
- Oro: Min-Max y Z-Score por serie, discretización del precio relativo (terciles y 4 rangos), jerarquías (fecha < mes < trimestre < semestre < año; estado de origen < macro-región) y reducción por agregación mensual, selección de variables y muestreo estratificado.

## 3. Problemas encontrados y cómo se resolvieron
| Problema | Causa | Solución | Tiempo (min) |
|---|---|---|---|
| Los archivos `.csv` de registro de tiempo, defectos y datos no se podían leer como CSV | Eran libros de Excel (.xlsx) renombrados | Se reconvirtieron a CSV UTF-8 real y se adoptó "Guardar como → CSV UTF-8" | [ ] |


## 4. Aprendizajes
- Técnicos: los precios de productos distintos no son comparables, así que la limpieza, la normalización y los atípicos deben hacerse dentro de cada serie. "N/D" es un faltante legítimo y no un error de captura. Un registro inválido debe ir a cuarentena con su motivo y no desaparecer. Reglas de coherencia entre columnas (mínimo ≤ frecuente ≤ máximo) detectan errores que el rango por sí solo no ve.
