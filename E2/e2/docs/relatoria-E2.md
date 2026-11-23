# Relatoría de etapa — E2: fuente geoespacial, linaje y ética

**Proyecto:** Observatorio del Comercio al por Menor en Colima
**Periodo:** `[fecha inicio]` – `[fecha fin]`
**Integrantes:** Andrik H. García Morales `[agregar]`

## 1. Qué nos propusimos

- Sumar una fuente que agregara una dimensión que las series de tiempo no tienen: **dónde** está el comercio y **cómo** se reparte por tamaño y giro.
- Poder responder, para cualquier cifra publicada, de qué archivo crudo salió y cuándo se descargó.
- Dejar por escrito las reglas éticas y legales del observatorio.

## 2. Qué hicimos

1. **Extractor del DENUE.**
   - Usa dos métodos de la API oficial: `Cuantificar`, que da conteos agregados, y `BuscarAreaActEstr`, que da los establecimientos del sector 46 por municipio, paginando de 1,000 en 1,000.
   - Antes de guardar en Bronce elimina nombre, razón social, contacto y domicilio.
   - Reutiliza el manifiesto, la revisión de robots.txt y los reintentos del extractor de E0.
2. **Puerta de Calidad del DENUE con Pandera.**
   - Reglas: CLEE único, coordenadas dentro de la parte continental de Colima, sector 46, estrato válido y clave municipal consistente con el municipio consultado.
   - Los duplicados exactos se separan y van a cuarentena con su motivo.
3. **GeoPandas.**
   - Proyección a EPSG:6372 para medir en metros.
   - Malla hexagonal de 1 km con supresión de celdas con menos de 3 establecimientos.
   - Unión espacial con el Marco Geoestadístico (opcional).
   - Distancia al competidor más cercano del mismo subsector, calculada con BallTree y haversine.
4. **Contraste entre fuentes.** Comparamos los puntos descargados contra el conteo oficial de `Cuantificar` en cada municipio.
5. **Linaje de punta a punta.** Plata y Oro llevan ahora el archivo Bronce, su SHA-256 y la fecha de ingesta, y hay un rastreador por línea de comandos.
6. **`docs/etica-datos.md`.** Términos de uso, robots.txt, licencias, privacidad, sesgos y usos no permitidos.

## 3. Decisiones y por qué

| Decisión | Alternativa | Razón |
|---|---|---|
| DENUE como fuente especializada | Redes sociales (YouTube, Reddit) | Se relaciona directamente con el sector y la región; las métricas de redes sobre comercio en Colima serían escasas y ruidosas |
| Eliminar campos personales en la captura | Guardarlos en Bronce y filtrarlos en Oro | El repositorio es público: lo que entra a Bronce se publica |
| Hexágonos de 1 km con supresión de celdas con menos de 3 establecimientos | Mapa de puntos | Un punto puede ser un domicilio particular; los hexágonos tienen área uniforme y vecindad simétrica |
| EPSG:6372 para cálculos | Grados (EPSG:4326) | Las áreas y distancias en grados no son comparables |
| Usar la captura más reciente del DENUE | Acumular todas | El DENUE es una foto del directorio, no una serie |
| Linaje por celda en un archivo aparte, más un resumen en cada fila | Solo una columna por fila | Una fila de Oro mezcla varias fuentes y rezagos (por ejemplo, el crecimiento anual usa t y t−12) |

## 4. Resultados

`[COMPLETAR con reporte_geo.json y los mapas: establecimientos por municipio, municipio con más competencia (menor distancia mediana), % de micronegocios, diferencia contra Cuantificar, celdas suprimidas.]`

![Densidad de comercio](E2/img/mapa_densidad_hexagonos.png)

## 5. Problemas y soluciones

| Problema | Solución |
|---|---|
| La API del DENUE devuelve texto en lugar de una lista cuando no hay resultados | `_get_json` trata cualquier respuesta que no sea lista como página vacía |
| El mismo establecimiento aparecía dos veces | Duplicado exacto: se conserva el primero y la copia va a cuarentena |
| `[ ]` | `[ ]` |

## 6. Aprendizajes

1. `[ ]`
2. `[ ]`
3. `[ ]`

## 7. Objetivos de calidad (PSP)

| Objetivo | Meta | Resultado E2 |
|---|---|---|
| Ejecuciones de Actions en verde | ≥ 95 % | `[ ]` |
| Filas de Oro con linaje completo | 100 % | `[ ]` |
| Defectos encontrados antes del push | ≥ 70 % | `[ ]` |

## 8. Siguiente etapa

Usar `comparativo_estados.csv` y los indicadores municipales como variables adicionales para la comparación multivariada de E3.
