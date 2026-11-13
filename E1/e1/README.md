# Paquete E1 — Trusted Data Lab (observatorio de precios de abasto)

Pipeline Bronce → Plata → Oro con Puerta de Calidad (Pandera) y cuarentena.
Esquema esperado en Bronce: `Producto | Calidad | Presentación | Origen | Precio Mín | Precio Max | Precio Frec | Obs.` + **fecha**.

## Antes de correrlo (3 cosas que dependen de SU captura)
1. **Fecha:** si su CSV no trae columna de fecha, el pipeline la toma del *nombre del archivo* (por defecto `aaaa-mm-dd`). Ajusten `col_fecha`, `fecha_en_archivo` y `dayfirst` en `src/config.py`.
2. **Archivos:** `patron` en `config.FUENTES` es `*.csv`; restrínjanlo (p. ej. `sniim*.csv`) si en `data/bronce/` hay otras fuentes. Si su Bronce está en otra carpeta, cambien `rutas()`.
3. **Segunda fuente (figshare):** descomenten y ajusten la fuente `"B"` en `config.FUENTES`. Ajusten también `RANGOS` a sus presentaciones (precio por caja vs. por kg).

## Pasos
1. Copien el contenido de este zip en la **raíz** de su repositorio (fusionen carpetas; no sobrescriban su captura de E0).
2. Prueben: `python -m src.pipeline --demo` y luego con sus datos: `python -m src.pipeline`.
3. Ejecuten `docs/E1/limpieza.ipynb` completo y guárdenlo **con salidas**.
4. Completen los `[COMPLETAR]` de `docs/E1/ENTREGA.md` y `docs/relatoria-E1.md` con `data/reportes/reporte_calidad.json`.
5. Agreguen a `calidad/tiempo-*.csv` y `calidad/defectos-*.csv` sus tiempos y defectos REALES de E1 (guarden como **CSV UTF-8**, no como Excel).
6. Publiquen:
```bash
git add . && git commit -m "E1: capa Plata, limpieza y puerta de calidad"
git push origin main
git tag e1 && git push origin e1
```
7. Registren el enlace en el formulario oficial.
