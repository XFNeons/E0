# Entrega E0 — Trusted Data Lab

## Integrantes

## Enlaces
- Propuesta: [docs/E0/propuesta.md](propuesta.md)
- Datos crudos (Bronce): [datos/bronce/](../../datos/bronce/)
- Registros de calidad: [calidad/](../../calidad/)

## Máquina de Captura
- **Extractor:** `scripts/extractor.py` — descarga la serie histórica del aguacate Hass desde el conjunto de datos de figshare (fuente SNIIM) y guarda el CSV crudo en `datos/bronce/`.
- **Automatización:** `.github/workflows/captura.yml`, programado para ejecutarse todos los días a las 08:00 UTC.
- **Periodos descargados:** [36 semanas / 36 meses] 

## Sistema de Calidad (PSP)
- Archivos por integrante en `calidad/`.
- Objetivos de calidad definidos en la propuesta (sección 5).

## Notas técnicas
- Los datos de la fuente 1 son de carácter público (SNIIM) y se redistribuyen con atribución. Los datos de la fuente 2 (INEGI) se usan bajo los Términos de Libre Uso del INEGI.
- El script de extracción está diseñado para ser idempotente: si el archivo ya existe, lo sobrescribe con la versión más reciente.