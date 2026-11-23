# Declaración de Ética y Legalidad de los Datos

**Observatorio del Comercio al por Menor en Colima (OCMC)** · Proyecto integrador, Ingeniería de Datos, Instituto Tecnológico de Colima
**Versión:** E2 · `[AAAA-MM-DD]` · **Responsables:** Andrik H. García Morales `[agregar equipo]`

Este documento declara qué datos usa el observatorio, con qué permiso, cómo se protegen las personas y los negocios, qué sesgos tienen las fuentes y qué hacemos para mitigarlos. Aplica a todo el repositorio (`E0/`, `E1/`, `E2/`).

---

## 1. Principios

1. **Solo fuentes oficiales y canales autorizados.** Usamos APIs públicas documentadas con token personal; no hacemos scraping de páginas HTML.
2. **Minimización.** Capturamos solo los campos que necesitamos para responder las preguntas del observatorio. Lo demás se descarta antes de guardar.
3. **Agregación antes de publicar.** Ningún producto de la capa Oro identifica a una persona. Los mapas se publican en hexágonos y por municipio, y se suprimen las celdas con pocos establecimientos.
4. **Trazabilidad.** Cada cifra publicada se puede rastrear hasta el archivo crudo y la fecha en que se descargó (ver §6).
5. **Nada se borra en silencio.** Los registros inválidos van a cuarentena con su motivo.
6. **Atribución y no suplantación.** Citamos la fuente en cada producto y no presentamos nuestros resultados como cifras oficiales.

---

## 2. Inventario de fuentes, términos de uso y licencias

| Fuente | Producto | Acceso | Licencia y términos | Datos personales |
|---|---|---|---|---|
| INEGI · Banco de Información Económica (BIE) | EMEC (ingresos, personal y remuneraciones del comercio al por menor, por estado) e INPC | API de Indicadores v2.0 + token (`INEGI_TOKEN`) | Términos de Libre Uso de la Información del INEGI | No: agregados estadísticos |
| Banco de México · SIE | TIIE a 28 días y tipo de cambio FIX | API SIE REST + token en encabezado `Bmx-Token` (`BANXICO_TOKEN`) | Términos del SIE y su "Salvedad de uso"; límites de consultas por token | No |
| INEGI · DENUE | Establecimientos del sector 46 en Colima (ubicación, actividad, estrato) y conteos agregados (`Cuantificar`) | API del DENUE + token (`DENUE_TOKEN`) | Términos de Libre Uso de la Información del INEGI | Posibles: nombre, razón social y contacto de negocios de personas físicas. **Se eliminan en la captura** (§4) |
| INEGI · Marco Geoestadístico (opcional) | Límites municipales de Colima | Descarga manual, una vez | Términos de Libre Uso de la Información del INEGI | No |
| Entrevista de campo (E0) | Opiniones de un comerciante | Entrevista presencial | Consentimiento informado verbal | Sí: se anonimiza (§4.4) |

### 2.1 Condiciones de los Términos de Libre Uso del INEGI que cumplimos

| Condición | Cómo la cumplimos |
|---|---|
| Se puede copiar, distribuir y transformar la información sin alterar ni suprimir sus metadatos | Bronce guarda la respuesta original (salvo los campos eliminados por privacidad en el DENUE, lo que se declara en el propio archivo, en `_captura.nota_privacidad`) |
| Dar crédito: "Fuente: INEGI, *nombre del producto*" | Cada mapa, tabla del notebook y documento lleva la leyenda de la fuente |
| No aparentar que el uso representa una postura oficial del INEGI | Leyenda en README, propuesta y mapas: "Este trabajo no representa una postura oficial del INEGI ni de Banco de México" |

### 2.2 Banco de México

La API SIE exige un token personal y tiene límites de consultas por token. El extractor hace **2 peticiones por ejecución**, con pausa de 2 s, y corre una vez por semana. El token viaja en el encabezado HTTP, nunca en la URL ni en los logs. Citamos "Fuente: Banco de México, SIE".

---

## 3. Análisis de robots.txt

Todas nuestras capturas usan **APIs oficiales para desarrolladores**, que son el canal que las instituciones dispusieron para el acceso automatizado. Aun así, el extractor revisa `robots.txt` en **cada ejecución**:

```python
# E0/src/extractor_bronce.py  -> robots_permite()
rp = urllib.robotparser.RobotFileParser(); rp.parse(texto_robots)
rp.can_fetch(USER_AGENT, "/app/api/...")   # si devuelve False, la fuente se omite
```

| Sitio | Ruta consultada | Resultado (log de GitHub Actions del `[fecha]`) |
|---|---|---|
| `www.inegi.org.mx/robots.txt` | `/app/api/indicadores/...` | `[PERMITIDO / PROHIBIDO]` |
| `www.inegi.org.mx/robots.txt` | `/app/api/denue/...` | `[PERMITIDO / PROHIBIDO]` |
| `www.banxico.org.mx/robots.txt` | `/SieAPIRest/...` | `[PERMITIDO / PROHIBIDO]` |

> **[Pegar aquí las capturas del log de Actions con las líneas `robots.txt ... PERMITIDO`, o el texto de cada robots.txt revisado ese día.]**

Otras prácticas de buen ciudadano de la red:
- `User-Agent` que identifica al proyecto con correo de contacto.
- Pausa de 2 s entre peticiones y reintentos con espera exponencial ante errores 429 y 5xx.
- Captura idempotente: si los datos no cambiaron (mismo SHA-256), no se vuelven a guardar.
- El DENUE, que se actualiza pocas veces al año, se consulta **solo una vez al mes**.

---

## 4. Privacidad y protección de datos

### 4.1 Marco legal

- **Ley del Sistema Nacional de Información Estadística y Geográfica (LSNIEG).** Los datos que los informantes entregan al INEGI son confidenciales y solo se usan con fines estadísticos. Solo usamos lo que el INEGI ya publicó.
- **Ley Federal de Protección de Datos Personales en Posesión de los Particulares.** Un negocio de una persona física puede aparecer en el DENUE con su nombre o su teléfono, y esos son datos personales. Aunque el DENUE es público, **no los necesitamos**, así que no los tratamos.

### 4.2 Minimización en la captura del DENUE

`E2/e2/src/extractor_denue.py` aplica `minimizar()` **antes de escribir en Bronce**:

| Se conserva | Se elimina |
|---|---|
| CLEE (clave estadística pública, necesaria para el linaje), clase y subsector SCIAN, estrato de personal, tipo, código postal, AGEB, manzana, latitud y longitud, fecha de alta, clave geográfica | Nombre del establecimiento, razón social, teléfono, correo electrónico, sitio web, calle, número exterior e interior, número de local, piso, colonia y nombre del corredor |

Esto es una excepción **deliberada y documentada** a la regla de que Bronce sea una copia exacta de la fuente: preferimos perder fidelidad antes que guardar datos personales que no usamos.

### 4.3 Publicación agregada (control de divulgación)

Las coordenadas de un micronegocio pueden coincidir con un domicilio particular. Por eso:
- La capa Oro **no publica puntos**. Publica indicadores por municipio y conteos en **hexágonos de 1 km de lado**.
- Las celdas con **menos de 3 establecimientos se suprimen**: no se publica su conteo y aparecen en gris en el mapa (`config.UMBRAL_SUPRESION`).
- Los mapas no rotulan negocios individuales.

### 4.4 Entrevista de campo

Hubo consentimiento verbal informado y se explicó el uso académico. Se publica solo el tipo de negocio y el municipio, sin nombre ni cifras de ventas del negocio. Las notas originales no se suben al repositorio.

### 4.5 Credenciales

`INEGI_TOKEN`, `BANXICO_TOKEN` y `DENUE_TOKEN` se guardan como *secrets* de GitHub. El extractor los enmascara (`***TOKEN***`) en el manifiesto y en los logs, y ninguno está en el código.

---

## 5. Sesgos conocidos y mitigación

| Sesgo | Dónde | Efecto | Mitigación |
|---|---|---|---|
| **Cobertura de la informalidad** | DENUE y EMEC | Ambulantes, tianguis y venta por redes sociales casi no aparecen, así que se subestima el comercio en zonas populares | Se declara en cada producto: "comercio establecido". No se interpreta una celda vacía como ausencia de comercio |
| **Desfase temporal del directorio** | DENUE | Un negocio que ya cerró puede seguir registrado y uno nuevo puede no aparecer todavía | Se compara con `Cuantificar` (columna `diferencia_pct`). Se reporta la fecha de corte y la de ingesta |
| **Fecha de alta ≠ fecha de apertura** | DENUE `Fecha_Alta` | "Altas recientes" mide actualización del registro, no nacimiento de negocios | Se nombra "altas recientes en el directorio", no "aperturas" |
| **Muestra de la EMEC** | EMEC | La encuesta mensual sigue una muestra de empresas formales medianas y grandes; Colima tiene pocas unidades en muestra, lo que da más volatilidad | Se usa el Z-score robusto y no se interpretan movimientos de un solo mes |
| **Choque COVID-19** | Todas las series 2020 | Valores extremos reales | Se conservan y se marcan; no se eliminan (E1) |
| **Unidad de área modificable (MAUP)** | Mapas | El patrón cambia según el tamaño del hexágono o de la división municipal | Se publican dos escalas (municipio y hexágono de 1 km) y se documenta el tamaño |
| **Sesgo urbano** | Mapas de densidad | Colima, Villa de Álvarez y Manzanillo dominan visualmente | Se reportan también porcentajes por municipio y la distancia al competidor, no solo conteos |
| **Comparación entre estados** | `comparativo_estados` | Jalisco es mucho más grande que Colima | Se compara la estructura (porcentajes por estrato y subsector), no los totales |

---

## 6. Linaje y rendición de cuentas

- Cada registro de Plata tiene `id_registro`, `id_bronce` (archivo y periodo), `ruta_bronce`, `sha256_bronce` y `captura` (fecha de ingesta).
- Cada fila de Oro tiene `id_fila_oro`, `fecha_ingesta` y `archivos_bronce`. El detalle celda por celda está en:
  - `E1/e1/data/oro/linaje_oro.csv` (series de tiempo)
  - `E2/e2/data/oro/linaje_geo.csv` (DENUE)
- `python -m src.linaje --verificar` (en `E1/e1`) comprueba que cada archivo citado existe y que su SHA-256 no cambió. Corre en cada ejecución de Actions.

---

## 7. Usos no permitidos de los productos del observatorio

- Reidentificar o contactar establecimientos a partir de los mapas o de la capa Bronce.
- Usar los conteos para fiscalización, cobranza o prospección comercial individual.
- Presentar los pronósticos como cifras oficiales.

## 8. Revisión

Este documento se revisa en cada entrega. Cambios:

| Versión | Fecha | Cambio |
|---|---|---|
| E2 | `[ ]` | Primera versión: fuentes INEGI BIE, Banxico SIE y DENUE |

*Fuente de datos: INEGI (EMEC, INPC, DENUE, Marco Geoestadístico); Banco de México (SIE). Este trabajo no representa una postura oficial del INEGI ni de Banco de México.*
