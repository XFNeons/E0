# Ficha de entrega técnica — E0

| Campo | Valor |
|---|---|
| Proyecto | Observatorio del Comercio al por Menor en Colima (OCMC) |
| Repositorio | https://github.com/XFNeons/E0 (carpeta `E0/`) |
| Tag | `e0` |
| Fecha de entrega | `[AAAA-MM-DD]` |
| Integrantes | Andrik Huemanc García Morales `[agregar resto del equipo]` |
| Colaboradores agregados | `[usuarios GitHub de los 3 profesores]` |

## 1. Checklist de entregables

| Entregable | Ubicación | Estado |
|---|---|---|
| Propuesta del observatorio (3–5 págs.) | `docs/E0/propuesta.md` | ☐ |
| — Ficha del observatorio | `propuesta.md` §1 | ☑ |
| — Entrevista de campo (≥ 15 min, 5 preguntas) | `propuesta.md` §2 | ☐ pendiente de realizar |
| — Preguntas analíticas E1, E2, E3 | `propuesta.md` §3 | ☑ |
| — Plan de datos con ≥ 2 fuentes y análisis ético/legal | `propuesta.md` §4 | ☑ (falta pegar captura de robots.txt) |
| Extractor ético automático | `src/extractor_bronce.py` | ☑ |
| Workflow de GitHub Actions | `.github/workflows/captura-bronce.yml` (raíz del repo) | ☑ |
| Serie histórica cruda ≥ 36 periodos | `data/bronze/` + `_manifiesto.csv` | ☐ tras la primera corrida |
| Registros PSP por integrante | `calidad/tiempo-<nombre>.csv`, `calidad/defectos-<nombre>.csv` | ☑ (Andrik) |
| 3 objetivos de calidad medibles | `calidad/README.md` | ☑ |

## 2. Cómo ejecutar

```bash
pip install -r requirements.txt
export INEGI_TOKEN=...      # registro en https://www.inegi.org.mx/servicios/api_indicadores.html
export BANXICO_TOKEN=...   # https://www.banxico.org.mx/SieAPIRest/service/v1/token
python -m unittest discover -s tests -v
python src/extractor_bronce.py --dry-run   # valida configuración
python src/extractor_bronce.py             # captura real
```

En GitHub: *Settings → Secrets and variables → Actions* → crear `INEGI_TOKEN` y `BANXICO_TOKEN`. Después, *Actions → Captura capa Bronce → Run workflow*.

## 3. Evidencia de la captura

| Serie | Fuente | Periodos mensuales | Primer periodo | Último periodo | Resultado |
|---|---|---|---|---|---|
| `[copiar de data/bronze/_manifiesto.csv]` | | | | | |

Enlace a la corrida exitosa de Actions: `[URL]`

## 4. Decisiones técnicas

- **Solo APIs oficiales**: menor carga al servidor y cumplimiento de términos de uso; no se usa scraping de HTML.
- **Bronce inmutable**: se guarda el JSON exacto recibido, con marca de tiempo; nunca se sobrescribe.
- **Idempotencia** por hash SHA-256: si INEGI o Banxico no publicaron nada nuevo, no se crea archivo.
- **Configuración separada del código** (`config/fuentes.json`) para agregar series sin tocar Python.
- **Tokens como GitHub Secrets**, enmascarados en el manifiesto.

## 5. Pendientes conocidos

1. Sustituir los IDs `PENDIENTE` de la EMEC en `config/fuentes.json` por las claves reales del BIE.
2. Realizar y documentar la entrevista de campo.
3. Pegar la evidencia de robots.txt y de la primera corrida de Actions.
