# Observatorio del Comercio al por Menor en Colima

Proyecto integrador — Instituto Tecnológico de Colima.

**Pregunta detonadora:** ¿Cómo se comportarán los ingresos del comercio al por menor en Colima en los próximos seis meses, qué factores los explican y en qué se diferencia Colima de sus estados vecinos?

## Estructura

```
../.github/workflows/captura-bronce.yml  # captura automática semanal (raíz del repo)
config/fuentes.json                    # catálogo de series (INEGI y Banxico)
src/extractor_bronce.py                # extractor ético
data/bronze/                           # datos crudos + _manifiesto.csv
docs/E0/propuesta.md                   # propuesta (E0)
docs/E0/ENTREGA.md                     # ficha de entrega técnica
calidad/                               # PSP: registros de tiempo y defectos, objetivos
tests/                                 # pruebas sin red
```

## Puesta en marcha

1. Obtener tokens gratuitos de [INEGI](https://www.inegi.org.mx/servicios/api_indicadores.html) y [Banxico SIE](https://www.banxico.org.mx/SieAPIRest/service/v1/token).
2. En GitHub: *Settings → Secrets and variables → Actions* → `INEGI_TOKEN` y `BANXICO_TOKEN`.
3. *Actions → Captura capa Bronce → Run workflow*.

## IDs de INEGI (EMEC por entidad)

Las series de la EMEC estatal se identifican con una clave numérica del BIE. Para obtenerlas:

1. Abrir el **Constructor de consultas** de la API de Indicadores de INEGI (desde la página de la API), banco **BIE**.
2. Navegar: *Indicadores económicos de coyuntura → Encuesta Mensual sobre Empresas Comerciales (EMEC) → Serie 2018 → por entidad federativa → Colima → 46 Comercio al por menor* → Ingresos / Personal ocupado / Remuneraciones.
3. Copiar el número de indicador y pegarlo en el campo `id` correspondiente de `config/fuentes.json` (reemplazando `PENDIENTE`). Repetir para Jalisco, Michoacán y Nayarit.
4. Probar localmente con `python src/extractor_bronce.py --fuente inegi`.

*Fuente: INEGI, EMEC e INPC; Banco de México, SIE. Este proyecto no representa una postura oficial de esas instituciones.*
