# Propuesta del Observatorio — Entrega E0

**Observatorio del Comercio al por Menor en Colima (OCMC)**
Proyecto integrador · Instituto Tecnológico de Colima · Noviembre de 2026
Repositorio: `XFNeons/E0` (carpeta `E0/`) · Integrantes: Andrik Huemanc García Morales *(agregar al resto del equipo)*

---

## 1. Ficha del observatorio

| Campo | Definición |
|---|---|
| **Sector económico** | Comercio al por menor (sector 46 del SCIAN): abarrotes, ropa, calzado, ferreterías, farmacias, autoservicio y departamentales. |
| **Región** | Estado de Colima (10 municipios), con Jalisco, Michoacán y Nayarit como estados de comparación. |
| **Unidad de análisis** | Mes (serie mensual de la Encuesta Mensual sobre Empresas Comerciales, EMEC, de INEGI, índice 2018=100). |
| **Pregunta detonadora** | *¿Cómo se comportarán los ingresos del comercio al por menor en Colima en los próximos seis meses, qué factores (temporada, tasas de interés, inflación, tipo de cambio) explican sus variaciones y en qué se diferencia Colima de sus estados vecinos?* |
| **Cliente potencial** | Comerciantes minoristas locales y su cámara empresarial (CANACO SERVYTUR Colima), así como la Secretaría de Desarrollo Económico del Estado, que necesitan anticipar ventas para planear inventario, contratación de temporada y crédito. |
| **Valor para el cliente** | Un tablero mensual con pronóstico a 6 meses, alertas de cambio de tendencia y comparativo regional, construido solo con datos públicos oficiales. |

### Justificación

El comercio al por menor es uno de los principales empleadores de Colima y es muy sensible a la temporada (regreso a clases, El Buen Fin, diciembre) y a la actividad turística de Manzanillo. Los comercios pequeños suelen decidir compras e inventario por intuición, sin un referente estadístico local. INEGI publica cada mes la EMEC con desagregación por entidad federativa, lo que permite construir una serie histórica larga (2008 a la fecha) y actualizarla automáticamente.

---

## 2. Entrevista de campo

> **Estado: pendiente de realizar.** Esta sección contiene el guion y la plantilla de registro. Debe completarse con una entrevista real de al menos 15 minutos a alguien del sector (dueño o encargado de una tienda de abarrotes, ferretería, tienda de ropa o farmacia en Colima / Villa de Álvarez, o personal de CANACO).

**Datos de la entrevista**

| Campo | Valor |
|---|---|
| Persona entrevistada (nombre o iniciales, con su consentimiento) | `[pendiente]` |
| Puesto / tipo de negocio | `[pendiente]` |
| Municipio | `[pendiente]` |
| Fecha, hora y duración | `[pendiente]` (mínimo 15 min) |
| Medio (presencial / llamada) | `[pendiente]` |
| Evidencia | `[pendiente]` foto del lugar, audio con permiso o notas firmadas |

**Aviso de consentimiento leído al inicio:** "Somos estudiantes del Tecnológico de Colima. La información se usará solo con fines académicos; no publicaremos datos de ventas de su negocio ni su nombre sin su permiso."

### Guion y registro

| # | Pregunta | Respuesta resumida | Aprendizaje para el observatorio |
|---|---|---|---|
| 1 | ¿En qué meses del año vende más y en cuáles menos? ¿Cuánto cambia, aproximadamente, entre un mes bueno y uno malo? | `[pendiente]` | Confirma o corrige la estacionalidad que modelaremos en E1 y los niveles del factor "temporada" en E2. |
| 2 | ¿Qué hace cuando sube el precio de lo que compra a sus proveedores? ¿Lo pasa al cliente de inmediato? | `[pendiente]` | Valida si la inflación (INPC) es un factor relevante de ingresos reales. |
| 3 | ¿Usa crédito (bancario, de proveedores, tarjetas) para surtir? ¿Notó cambios cuando subieron o bajaron las tasas? | `[pendiente]` | Valida la inclusión de la TIIE como factor en E2. |
| 4 | ¿Cuánto influye el turismo o la llegada de visitantes (Manzanillo, vacaciones) en sus ventas? ¿Siente competencia de Guadalajara o de compras en línea? | `[pendiente]` | Orienta la comparación regional de E3 y posibles variables adicionales. |
| 5 | Si cada mes recibiera un pronóstico de cómo van a estar las ventas del comercio en Colima, ¿qué decisión tomaría con él? ¿Con cuánta anticipación lo necesitaría? | `[pendiente]` | Define el horizonte del pronóstico (propuesto: 6 meses) y el formato del entregable para el cliente. |

### Aprendizajes clave (completar después de la entrevista)

1. `[pendiente]`
2. `[pendiente]`
3. `[pendiente]`

**¿La entrevista confirma el problema?** `[pendiente: sí / parcialmente / no, y qué ajustamos en la pregunta detonadora]`

---

## 3. Las tres preguntas analíticas

### E1 — Variable a pronosticar

**Pregunta:** ¿Cuál será el índice de ingresos reales por suministro de bienes y servicios del comercio al por menor en Colima (EMEC, 2018=100) en cada uno de los próximos 6 meses?

- **Variable objetivo (y):** índice mensual de ingresos reales, comercio al por menor, Colima.
- **Horizonte:** 6 meses; validación con los últimos 12 meses como conjunto de prueba.
- **Métrica de éxito:** MAPE menor a 5 % frente a un modelo ingenuo estacional (valor del mismo mes del año anterior).
- **Modelos candidatos:** ingenuo estacional (línea base), suavizamiento exponencial Holt-Winters y SARIMA(X) con TIIE e INPC como regresores.

### E2 — Factores a experimentar

**Pregunta:** ¿Cambia el crecimiento anual de los ingresos minoristas de Colima según la temporada del año y el nivel de tasas de interés, y existe interacción entre ambos?

| Factor | Niveles | Fuente |
|---|---|---|
| A. Temporada | Alta (julio–agosto, noviembre–diciembre) / Baja (resto) | Calendario |
| B. Nivel de tasa TIIE 28 días | Alta (≥ mediana del periodo) / Baja (< mediana) | Banxico SIE |
| C. *(opcional)* Inflación | Alta / Baja respecto a la mediana | INEGI INPC |

- **Respuesta:** variación porcentual anual del índice de ingresos.
- **Diseño:** factorial 2×2 (o 2³ con el factor C) sobre los meses observados, analizado con ANOVA de dos vías e interacción; se verificarán supuestos de normalidad y homocedasticidad de residuos.

### E3 — Grupos multivariados a comparar

**Pregunta:** ¿El perfil del comercio al por menor de Colima —ingresos, personal ocupado y remuneraciones medias— es estadísticamente distinto al de Jalisco, Michoacán y Nayarit?

- **Grupos:** 4 entidades federativas (Colima, Jalisco, Michoacán, Nayarit).
- **Vector de respuesta:** (ingresos reales, personal ocupado total, remuneraciones medias reales), variación anual mensual.
- **Técnicas:** MANOVA de una vía (prueba de Pillai), seguido de análisis discriminante o de componentes principales para interpretar en qué variables se separan los grupos.

---

## 4. Plan de recopilación de datos

### 4.1 Fuentes

| # | Fuente | Qué aportamos | Acceso | Frecuencia | Periodos disponibles |
|---|---|---|---|---|---|
| 1 | **INEGI — Banco de Información Económica (BIE)**, Encuesta Mensual sobre Empresas Comerciales (EMEC) e INPC | Variable objetivo (E1), grupos de E3, factor inflación (E2) | API de Indicadores v2.0 (JSON), con token gratuito | Mensual | EMEC por entidad: desde 2008 (más de 200 meses) |
| 2 | **Banco de México — Sistema de Información Económica (SIE)** | Factores de E2: TIIE a 28 días y tipo de cambio FIX | API REST SIE (JSON), con token gratuito enviado en el encabezado `Bmx-Token` | Diaria / mensual | Desde 2015 en la configuración (más de 130 meses) |

Ambas fuentes superan holgadamente el mínimo de 36 periodos requeridos.

### 4.2 Análisis ético y legal

| Criterio | INEGI | Banxico |
|---|---|---|
| **Tipo de acceso** | API oficial documentada para desarrolladores; no se hace scraping de páginas HTML. | API oficial documentada; no se hace scraping. |
| **robots.txt** | El extractor descarga y evalúa `https://www.inegi.org.mx/robots.txt` con `urllib.robotparser` en cada ejecución y se detiene si la ruta `/app/api/` está prohibida. El resultado queda en el log de GitHub Actions. `[Pegar aquí captura o texto del robots.txt revisado el día de la entrega]` | Mismo procedimiento con `https://www.banxico.org.mx/robots.txt` para la ruta `/SieAPIRest/`. `[Pegar captura]` |
| **Términos de uso** | Los Términos de Libre Uso de la Información del INEGI permiten copiar, distribuir y usar la información, siempre que no se alteren los metadatos, se cite la fuente ("Fuente: INEGI, EMEC") y no se presente el trabajo como postura oficial del INEGI. | El uso del API requiere un token personal de consulta y está sujeto a límites de número de consultas y a la "Salvedad de uso" publicada por Banxico; se citará "Fuente: Banco de México, SIE". |
| **Datos personales** | No hay: son agregados estadísticos por entidad. La EMEC protege la confidencialidad de los informantes por ley. | No hay: indicadores financieros agregados. |
| **Carga al servidor** | Una petición por serie, pausa de 2 s entre peticiones, reintentos con espera exponencial y ejecución semanal. Si el contenido no cambió, no se guarda de nuevo. | Igual; dos peticiones por ejecución. |
| **Identificación** | User-Agent con nombre del proyecto y correo de contacto del equipo. | Igual. |
| **Credenciales** | Token guardado como *secret* de GitHub (`INEGI_TOKEN`); nunca se escribe en el repositorio ni en los logs (se enmascara en el manifiesto). | Token como *secret* `BANXICO_TOKEN`, enviado por encabezado HTTP. |
| **Entrevista** | Consentimiento verbal informado; anonimización del negocio; no se publican cifras de ventas individuales. | — |

### 4.3 Arquitectura de captura (capa Bronce)

```
GitHub Actions (cron semanal + manual)
  └─ src/extractor_bronce.py
       ├─ revisa robots.txt de cada fuente
       ├─ consulta API INEGI (BIE) y API Banxico (SIE)
       ├─ guarda la respuesta JSON cruda, sin transformar:
       │     data/bronze/<fuente>/<serie>/<AAAA-MM-DD_hhmmss>.json
       └─ agrega una fila al manifiesto data/bronze/_manifiesto.csv
            (fecha, URL sin token, HTTP, SHA-256, n.º de periodos, resultado)
```

Las capas Plata (limpieza y tipado) y Oro (series mensuales integradas para E1–E3) se construirán en las siguientes entregas.

---

## 5. Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| INEGI cambia la clave de un indicador o rebasa la serie (cambio de año base). | Configuración externa en `config/fuentes.json`; el manifiesto detecta cambios de hash y de número de periodos. |
| Caída temporal de una API. | Reintentos con espera exponencial; el job no falla si al menos una serie se capturó. |
| La entrevista no confirma la relevancia de un factor. | Se reemplaza el factor en E2 (por ejemplo, por llegada de turistas) antes de E2. |
| Revisiones de cifras preliminares de la EMEC. | Bronce guarda cada versión; la capa Plata usará siempre la última captura. |

---

*Fuente de datos: INEGI, Encuesta Mensual sobre Empresas Comerciales (EMEC) e Índice Nacional de Precios al Consumidor; Banco de México, Sistema de Información Económica. Este trabajo no representa una postura oficial del INEGI ni de Banco de México.*
