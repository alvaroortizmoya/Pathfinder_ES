# Pathfinder_ES

Base inicial para crear un **repositorio interno bilingüe (EN/ES)** del contenido de Pathfinder 2e desde [2e.aonprd.com](https://2e.aonprd.com), con scraping responsable y traducción automática.

> ⚠️ Úsalo solo con consentimiento explícito del propietario del contenido, respetando términos de uso, `robots.txt`, límites de tráfico y copyright.

## Qué incluye este MVP

- **Scraper** de páginas internas de AON2e.
- **Almacenamiento SQLite** con contenido en inglés.
- **Pipeline de traducción** (por defecto EN→ES) manteniendo ambos idiomas.
- **Export JSON bilingüe** para alimentar una web interna.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Flujo recomendado

1. **Scrapear** contenido en inglés:

```bash
pathfinder-es scrape --db data/pathfinder.db --max-pages 200 --delay 1.2
```

2. **Traducir** al castellano:

```bash
pathfinder-es translate --db data/pathfinder.db --lang es
```

3. **Exportar JSON bilingüe**:

```bash
pathfinder-es export --db data/pathfinder.db --output data/pathfinder_bilingual.json
```

## Estructura de datos

- `pages`: URL, título y `content_en`.
- `translations`: traducciones por idioma (`lang`), vinculadas por `page_id`.

Esto te permite montar una UI interna con selector de idioma y fallback al inglés cuando falte traducción.

## Siguiente paso sugerido (web interna)

Con `data/pathfinder_bilingual.json`, puedes crear:

- Backend FastAPI (búsqueda + filtros por categoría).
- Frontend (Next.js, Vue o Svelte) con toggle EN/ES.
- Cache semántica y vector DB opcional para búsquedas tipo “reglas relacionadas”.

## Nota de calidad de traducción

La traducción automática te da velocidad, pero para términos reglísticos conviene:

- Glosario propio (traits, condiciones, acciones, etc.).
- Post-edición humana para reglas clave.
- QA de consistencia terminológica.
