# Pathfinder_ES

Pipeline para montar una copia interna bilingüe (EN/ES) de contenido de Pathfinder 2e desde `2e.aonprd.com`, con:

- Scraper responsable
- Base de datos SQLite
- Traducción EN→ES
- Backend FastAPI (búsqueda + filtros)
- Frontend dinámico (Vue) con menú de categorías/subcategorías
- Capa opcional de búsqueda semántica (embeddings hash + cache)

> ⚠️ Úsalo solo con consentimiento explícito del propietario del contenido y respetando ToS/robots/copyright.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Flujo completo

### 1) Scrapear

```bash
pathfinder-es scrape --db data/pathfinder.db --max-pages 200 --delay 1.2
```

### 2) Traducir

```bash
pathfinder-es translate --db data/pathfinder.db --lang es
```

### 3) (Opcional) Generar embeddings para búsqueda semántica

```bash
pathfinder-es embed --db data/pathfinder.db --dims 128
```

### 4) Levantar backend API

```bash
pathfinder-es serve --host 0.0.0.0 --port 8000
```

Docs API: `http://localhost:8000/docs`

### 5) Frontend moderno y dinámico

```bash
python -m http.server 4173 -d frontend
```

Abre `http://localhost:4173`.

## Endpoints principales

- `GET /taxonomy` (categorías + subcategorías)
- `GET /rules?q=&category=&subcategory=&lang=&limit=&offset=`
- `GET /rules/{id}`
- `GET /rules/{id}/related?limit=&lang=`
- `GET /categories`

## Notas

- El frontend refresca resultados en tiempo real al escribir (debounce).
- `pages.subcategory` se rellena desde la URL durante el scraping.
- Si falta traducción para `lang`, el backend usa fallback EN.


## Diagnóstico rápido si no ves contenido

1. Comprueba que la API tenga datos:

```bash
curl http://127.0.0.1:8000/stats
```

Si `pages` es `0`, aún no hay contenido cargado en esa DB.

2. Asegúrate de usar la misma DB en scrape y serve:

```bash
pathfinder-es scrape --db data/pathfinder.db --max-pages 300
pathfinder-es translate --db data/pathfinder.db --lang es
pathfinder-es serve --host 0.0.0.0 --port 8000
```

3. Si abres el frontend desde otra máquina, revisa la URL API en la propia UI (campo `URL API`).



## Menú jerárquico (nuevo)

El frontend ya no muestra categorías técnicas tipo `*.aspx`.
Ahora presenta un menú legible y desplegable por dominios:

- Character Creation
  - Ancestries
  - Archetypes
  - Backgrounds
  - Classes
- Equipment
  - All Equipment
  - Adventuring Gear
  - Alchemical Items
  - Armor
  - Held Items
  - Runes
  - Shields
  - Weapons
  - Worn Items
- Feats
  - All Feats
  - General
  - General (NoSkill)
  - Skill

La asignación a ese menú se hace por coincidencias de texto (`title`, `url`, etc.) para que sea navegable incluso con datos scrapeados heterogéneos.


## Cambios en el scraping (HTML completo)

Ahora el scraper guarda **dos representaciones** por página:

- `content_text_en`: texto para búsqueda/traducción/embeddings.
- `content_html_en`: HTML del contenido principal con estructura (títulos, tablas, enlaces, etc.).

Además, los enlaces internos de AON se conservan como referencias navegables dentro de tu app (`data-internal-url`) para saltar entre reglas relacionadas.

### ¿Tengo que volver a ejecutar todo?

**Sí, debes volver a ejecutar al menos el scraping** para llenar `content_html_en` y mejorar el formato:

```bash
pathfinder-es scrape --db data/pathfinder.db --max-pages 300
```

Opcionalmente, para coherencia total de búsqueda semántica/traducciones después del re-scrape:

```bash
pathfinder-es translate --db data/pathfinder.db --lang es
pathfinder-es embed --db data/pathfinder.db --dims 128
```


## Frontend Reader v2

Se ha rediseñado el frontend en 3 paneles para que sea manejable:

- **Panel izquierdo:** árbol desplegable de categorías/subcategorías con filtro rápido.
- **Panel central:** listado de resultados filtrados por categoría/subcategoría + búsqueda textual.
- **Panel derecho (reader):**
  - `Texto formateado` (lectura limpia),
  - `HTML original (EN)` para preservar tablas, enlaces y estructura de AON.

Los enlaces internos dentro del HTML (`data-internal-url`) son navegables desde el propio reader.
