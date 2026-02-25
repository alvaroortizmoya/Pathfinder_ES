# Pathfinder_ES

Pipeline para montar una copia interna bilingüe (EN/ES) de contenido de Pathfinder 2e desde `2e.aonprd.com`, con:

- Scraper responsable
- Base de datos SQLite
- Traducción EN→ES
- Backend FastAPI (búsqueda + filtros)
- Frontend Vue con toggle de idioma
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

Documentación interactiva: `http://localhost:8000/docs`

### 5) Frontend interno

Sirve `frontend/index.html` con cualquier servidor estático:

```bash
python -m http.server 4173 -d frontend
```

Abre `http://localhost:4173`.

## Endpoints principales

- `GET /rules?q=&category=&lang=&limit=&offset=`
- `GET /rules/{id}`
- `GET /rules/{id}/related?limit=&lang=`
- `GET /categories`

## Notas de arquitectura

- `pages.category` se infiere de la URL (primer segmento de path) y permite filtros.
- `page_vectors` guarda embeddings hash (sin dependencias pesadas).
- `semantic_cache` cachea resultados de relacionados para consultas repetidas.
- Si falta traducción en `lang`, el backend hace fallback a contenido EN.
