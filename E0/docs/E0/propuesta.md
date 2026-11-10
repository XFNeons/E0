# Propuesta del Observatorio E0
## Observatorio de Precios de Frutas y Hortalizas en México

### 1. Ficha del Observatorio

- **Sector:** Comercio agroalimentario / Abasto mayorista.
- **Región:** Villa De Alvarez(El Tringulito Villa De Alvarez)
- **Pregunta detonadora:** ¿Cómo están evolucionando los precios al mayoreo del aguacate Hass en las verdulerias de Villa de Alvarez y qué factores explican sus variaciones semanales?
- **Cliente potencial:** Asociaciones de comerciantes de centrales de abasto, pequeñas cadenas de restaurantes y consumidores informados que buscan anticipar el costo de la canasta básica.

### 2. Entrevista de Campo

- **Persona entrevistada:** ["Comerciante de frutas y verduras en comericio "El triangulito", 15 años de experiencia"]
- **Fecha y duración:** [2026-09-NOV, 20 minutos]
- **Modalidad:** [Presencial]

**Preguntas realizadas:**

1. ¿Cómo decide el precio de venta del aguacate cada semana?
El precio lo saco más que nada por lo que me cobra el proveedor esa semana. Si el proveedor me sube, yo tengo que subirle también, porque si no, pierdo. A veces también le pregunto a otros compañeros del pasillo cuánto están vendiendo ellos, para no quedarme muy caro ni muy barato. Pero no hay una fórmula; es más bien lo que se va viendo cada día. Si veo que llega mucho aguacate, bajo un poco el precio para que se venda rápido y no se me eche a perder.

2. ¿Qué tan fácil o difícil es anticipar si el precio del aguacate va a subir o bajar?
Está difícil. A veces uno cree que va a subir porque hay poca mercancía, pero de repente llega un camión con bastante y el precio se cae. O al revés, uno piensa que va a estar barato y resulta que sube porque hubo helada en Michoacán o porque se complicó el transporte. La verdad es que es pura experiencia y hasta suerte. No hay algo que te diga 'esta semana va a subir' con seguridad. Uno se guía por lo que oye, por lo que ve en las noticias, pero casi siempre se equivoca uno.

3. ¿Qué fuentes de información consulta para saber cómo se comportarán los precios?
Casi no consulto nada formal. A veces veo las noticias en la tele o en el celular, si dicen algo del aguacate o de Michoacán, pero no entro a páginas de precios ni nada de eso. Lo que más hago es preguntar a otros comerciantes, a los cargadores, a los que traen la mercancía. Ellos te dicen 'viene poca', 'viene mucha', y con eso uno se hace una idea. También a veces el proveedor me avisa 'la próxima semana va a subir' y pues uno se prepara. Pero datos, datos, no. No tengo una página ni una app que me diga cómo va a estar.

4. ¿Ha notado cambios en la demanda o en el precio en las últimas semanas?
Sí, sí he notado. Estas últimas semanas el precio ha estado moviéndose bastante. Hubo una semana que subió como 10 pesos el kilo de un día para otro, y la gente se espantó y dejó de comprar. Se llevaban menos, o se iban a la fruta más barata. Y luego a la semana siguiente bajó un poco y la gente volvió. La demanda también cambia mucho con la temporada: en diciembre y enero se vende más porque la gente hace guacamole para las posadas y la Navidad. En cambio en febrero o marzo baja mucho. Pero de un mes a otro, el precio sí ha estado más loco que otros años.

5. Si tuviera acceso a un pronóstico semanal del precio del aguacate, ¿lo usaría para tomar decisiones de compra o venta?
¡Claro que sí! Si yo supiera que la próxima semana va a subir, compro más ahora y lo guardo, o le apuesto a comprar más barato antes de que suba. Y si sé que va a bajar, pues vendo rápido lo que tengo y no compro tanto. Eso me ayudaría un montón a no perder. A veces uno compra y al día siguiente el precio se cae y uno se queda con la mercancía cara y ya no la puede vender al mismo precio. Con un pronóstico, aunque sea aproximado, uno se arriesga menos. Sí lo usaría, siempre y cuando sea fácil de ver, en el celular, y no me cueste nada o muy poquito.

**Aprendizajes clave:**

- El entrevistado mencionó que el precio del aguacate cambia cada semana y que no existe una herramienta sencilla y gratuita que le ayude a anticiparlo.  
- Actualmente se guía por la experiencia y por lo que escucha de otros comerciantes, no por datos formales.  
- Confirmó que un pronóstico semanal le ayudaría a decidir cuánto comprar y a qué precio ofrecer, reduciendo el riesgo de pérdidas.  
- El problema planteado en la pregunta detonadora es real y relevante para su actividad diaria.

### 3. Las 3 Preguntas Analíticas

- **Variable a pronosticar (E1):** Precio promedio samanal al mayoreo del aguacate Hass (calidad Extra) en Comercio el triangulito en V de Alv, expresado en pesos por kilogramo.
- **Factores a experimentar (E2):** Semana del año (estacionalidad), precio del diésel, tipo de cambio USD/MXN, volumen de importación reportado y precio del aguacate en la semana anterior.
- **Grupos multivariados a comparar (E3):** Precio del aguacate Hass frente al precio de otras frutas de la canasta básica (jitomate, cebolla, papa) y comparación entre distintas calidades (Extra vs. Primera).

### 4. Plan de Recopilación de Datos

**Fuente 1: SNIIM — Precios de frutas y hortalizas (datos históricos en CSV)**

- **URL:** `https://figshare.com/articles/dataset/productos_sniim_a-c/20085977` (conjunto de datos que recopila archivos CSV del SNIIM, incluyendo `sniim_producto_aguacate_hass_calidad_extra.csv`)[reference:0].
- **Datos a extraer:** Serie histórica de precios del aguacate Hass calidad Extra (precio mínimo, máximo y frecuente por kilogramo).
- **Análisis ético y legal:**
  - `robots.txt`: El sitio de origen (SNIIM, `www.economia-sniim.gob.mx`) publica información estadística de carácter público. No se encontró una restricción explícita en el `robots.txt` para el acceso a los datos de precios.
  - Términos de uso: La información del SNIIM es de carácter público y su uso es responsabilidad de los usuarios. Se debe citar la fuente (SNIIM-SE).
  - **Decisión:** Se descargarán los archivos CSV estáticos desde el repositorio de figshare, que a su vez redistribuye datos públicos del SNIIM. Se citará la fuente original en todos los productos del observatorio.

**Fuente 2: INEGI — Índice Nacional de Precios al Consumidor (INPC)**

- **URL:** Serie histórica del INPC, descargable en CSV desde el sitio del INEGI o desde portales que redistribuyen la serie con licencia abierta.
- **Datos a extraer:** Serie mensual del INPC general (base 2ª quincena de julio de 2018 = 100) para calcular la inflación y comparar con la evolución del precio del aguacate.
- **Análisis ético y legal:**
  - `robots.txt`: El INEGI permite el acceso a su información y cuenta con una sección de “Términos de Libre Uso”.
  - Términos de uso: “Puede utilizar la información del INEGI con apego a lo dispuesto en los ‘Términos de Libre Uso de la Información del INEGI’”.
  - **Decisión:** Se descargará la serie en CSV desde el portal del INEGI o desde un espejo que mantenga la licencia de datos abiertos, y se citará la fuente (INEGI).

### 5. Objetivos de Calidad (PSP)

1. **Objetivo 1:** Ejecutar el extractor automático sin errores durante 7 días consecutivos (verificable en el historial de GitHub Actions).
2. **Objetivo 2:** Registrar el 100% del tiempo de trabajo de cada integrante en los archivos `calidad/tiempo-<nombre>.csv`.
3. **Objetivo 3:** Reducir en un 20% el número de defectos registrados en `calidad/defectos-<nombre>.csv` entre la entrega E0 y la entrega E1.