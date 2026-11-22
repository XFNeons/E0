# Sistema de Calidad inicial (PSP)

Cada integrante mantiene dos registros abiertos en esta carpeta:

- `tiempo-<nombre>.csv` — registro de tiempo (PSP Time Recording Log). `delta_min = (fin - inicio) - interrupcion_min`.
- `defectos-<nombre>.csv` — registro de defectos (PSP Defect Recording Log).

Copiar `tiempo-andrik.csv` y `defectos-andrik.csv` para cada integrante (`tiempo-<nombre>.csv`, `defectos-<nombre>.csv`) y llenarlos el mismo día que se trabaja.

**Fases:** Planeacion, Diseno, Codificacion, Revision, Pruebas, Postmortem.

**Tipos de defecto (estándar PSP):** 10-Documentacion, 20-Sintaxis, 30-Construccion/paquetes, 40-Asignacion, 50-Interfaz, 60-Verificacion, 70-Datos, 80-Funcion, 90-Sistema, 100-Entorno.

## Objetivos de calidad medibles (E0 → E1)

| # | Objetivo | Métrica | Meta | Cómo se mide |
|---|---|---|---|---|
| 1 | **Confiabilidad de la captura** | % de ejecuciones programadas de GitHub Actions que terminan en verde | ≥ 95 % | Pestaña *Actions* del repositorio |
| 2 | **Completitud de la capa Bronce** | Series configuradas con ≥ 36 periodos mensuales y `resultado` sin error en `data/bronze/_manifiesto.csv` | 100 % de las series | Revisar el manifiesto después de cada corrida |
| 3 | **Calidad del proceso personal** | Defectos encontrados en revisión o pruebas antes de hacer *push* a `main`, respecto al total registrado | ≥ 70 %, y registro de tiempo de 100 % de las sesiones | `defectos-<nombre>.csv` y `tiempo-<nombre>.csv` |
