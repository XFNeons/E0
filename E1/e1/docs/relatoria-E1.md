# Relatoría de etapa — E1: capas Plata y Oro

**Proyecto:** Observatorio del Comercio al por Menor en Colima
**Periodo de la etapa:** `[fecha inicio]` – `[fecha fin]`
**Integrantes:** Andrik H. García Morales `[agregar]`

## 1. Qué nos propusimos

Llevar los datos crudos capturados en E0 (INEGI EMEC e INPC, Banxico TIIE y tipo de cambio) a tablas confiables y listas para responder las tres preguntas analíticas:
- **E1**: pronosticar el índice de ingresos del comercio al por menor de Colima.
- **E2**: experimentar con los factores temporada × tasa de interés (× inflación).
- **E3**: comparar Colima con Jalisco, Michoacán y Nayarit.

Todo debía quedar automatizado y ningún dato inválido podía perderse sin dejar rastro.

## 2. Qué hicimos

1. **Integración.**
   - Escribimos un lector para cada formato JSON y unificamos todo a un esquema largo: serie, entidad, variable, unidad, fecha y valor.
   - Las fechas venían en dos formatos y los valores como texto, con comas de miles y `N/E`.
   - Agregamos a mensual los datos diarios de Banxico.
   - Resolvimos las revisiones de INEGI quedándonos con la captura más reciente y registrando cada conflicto.
2. **Puerta de Calidad con Pandera.**
   - Esquema estricto, catálogos, rangos por variable, unicidad por serie y mes, y distinción entre un faltante declarado y un texto no numérico.
   - Los rechazados van a cuarentena con su motivo y la hora de la corrida.
3. **Faltantes.** Clasificamos cada hueco según su posición (inicio, interior o final) y probamos si es MCAR o MAR. Imputamos solo los interiores: interpolación lineal en huecos cortos y estacional escalada en huecos largos.
4. **Atípicos.**
   - Usamos Z-score robusto e IQR sobre la variación mensual sin estacionalidad, e Isolation Forest para los atípicos multivariados.
   - Los picos aislados se reemplazan; los choques de 2020 se conservan.
5. **Escalamiento, discretización y jerarquías.**
   - Min-Max y Z-score ajustados solo con el periodo de entrenamiento.
   - Discretizamos los factores de E2 y armamos las jerarquías de tiempo, geografía y sector.
6. **Reducción.** Agregación de diario a mensual, ventana común desde 2015 y selección de variables por correlación.
7. **Automatización.**
   - El mismo workflow de GitHub Actions que captura Bronce corre las 13 pruebas y el pipeline, y guarda Plata, Oro, cuarentena y reportes.

## 3. Decisiones y por qué

| Decisión | Alternativa descartada | Razón |
|---|---|---|
| Detectar atípicos sobre la variación mensual desestacionalizada | Z-score sobre el nivel | El nivel tiene tendencia y estacionalidad: todos los eneros salían como atípicos |
| Conservar los atípicos de 2020 | Eliminarlos o recortarlos | El cierre por COVID-19 fue real; borrarlo sesga el pronóstico y el experimento |
| No imputar los meses finales sin publicar | Rellenarlos | Son justamente lo que E1 debe pronosticar; imputarlos sería inventar la respuesta |
| Ajustar escaladores solo con entrenamiento | Ajustar con toda la serie | Evita fuga de información hacia los 12 meses de prueba |
| Cuarentena append-only | Sobrescribir en cada corrida | Trazabilidad: se puede auditar qué se rechazó en cada corrida |

## 4. Resultados

`[COMPLETAR con data/reportes/reporte_calidad.json de la corrida real: tasa de aprobación, motivos más frecuentes de cuarentena, mecanismo de faltantes por serie, atípicos tratados y conservados, variables finales en Oro.]`

## 5. Problemas que encontramos y cómo los resolvimos

| Problema | Solución |
|---|---|
| `[ej. Banxico manda días con 'N/E']` | `[se excluyen del promedio mensual y no van a cuarentena porque la fuente los declara]` |
| `[ ]` | `[ ]` |

## 6. Aprendizajes del equipo

1. `[ ]`
2. `[ ]`
3. `[ ]`

## 7. Seguimiento de objetivos de calidad (PSP)

| Objetivo (definido en E0) | Meta | Resultado en E1 |
|---|---|---|
| Ejecuciones de Actions en verde | ≥ 95 % | `[ ]` |
| Series con ≥ 36 periodos y sin error | 100 % | `[ ]` |
| Defectos encontrados antes del push | ≥ 70 % | `[ ]` |

Horas totales de la etapa: `[sumar calidad/tiempo-*.csv]` · Defectos registrados: `[ ]`

## 8. Siguiente etapa (E2)

Usar `oro/panel_colima_mensual.csv` (columnas `temporada`, `tiie_nivel`, `inflacion_nivel` e `ingresos_crec_anual`) para el ANOVA factorial, y `oro/panel_entidades.csv` para preparar la MANOVA de E3.
