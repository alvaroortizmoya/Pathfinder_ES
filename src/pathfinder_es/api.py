from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .semantic import build_hash_embedding, cosine, from_json
from .storage import connect

DEFAULT_DB = Path("data/pathfinder.db")


def _cache_key(prefix: str, payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _build_taxonomy(rows: list) -> list[dict]:
    tree: dict[str, set[str]] = {}
    for row in rows:
        cat = (row["category"] or "uncategorized").strip().lower()
        sub = (row["subcategory"] or "general").strip().lower()
        tree.setdefault(cat, set()).add(sub)

    return [{"category": cat, "subcategories": sorted(tree[cat])} for cat in sorted(tree)]


def create_app(db_path: Path = DEFAULT_DB) -> FastAPI:
    app = FastAPI(title="Pathfinder ES API", version="0.4.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/stats")
    def stats() -> dict:
        with connect(db_path) as conn:
            pages = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
            translated_es = conn.execute("SELECT COUNT(*) FROM translations WHERE lang = 'es'").fetchone()[0]
            html_pages = conn.execute("SELECT COUNT(*) FROM pages WHERE content_html_en IS NOT NULL AND content_html_en != ''").fetchone()[0]
        return {"pages": pages, "translations_es": translated_es, "pages_with_html": html_pages}

    @app.get("/taxonomy")
    def taxonomy() -> list[dict]:
        with connect(db_path) as conn:
            rows = conn.execute("SELECT DISTINCT category, subcategory FROM pages ORDER BY category, subcategory").fetchall()
        return _build_taxonomy(rows)

    @app.get("/categories")
    def categories() -> list[str]:
        with connect(db_path) as conn:
            rows = conn.execute("SELECT DISTINCT category FROM pages WHERE category IS NOT NULL ORDER BY category").fetchall()
        return [row[0] for row in rows]

    @app.get("/rules")
    def list_rules(
        q: str | None = None,
        category: str | None = None,
        subcategory: str | None = None,
        lang: str = Query("es", pattern="^[a-z]{2}$"),
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ) -> dict:
        with connect(db_path) as conn:
            params: list = [lang]
            where = []
            if category:
                where.append("p.category = ?")
                params.append(category.lower())
            if subcategory:
                where.append("p.subcategory = ?")
                params.append(subcategory.lower())
            if q:
                where.append("(LOWER(p.title) LIKE ? OR LOWER(COALESCE(p.content_text_en, p.content_en)) LIKE ? OR LOWER(COALESCE(t.content,'')) LIKE ?)")
                like = f"%{q.lower()}%"
                params.extend([like, like, like])

            where_sql = f"WHERE {' AND '.join(where)}" if where else ""
            rows = conn.execute(
                f"""
                SELECT p.id, p.url, p.title, p.category, p.subcategory,
                       COALESCE(p.content_text_en, p.content_en) AS content_text,
                       t.content AS content_lang
                FROM pages p
                LEFT JOIN translations t ON t.page_id = p.id AND t.lang = ?
                {where_sql}
                ORDER BY p.title COLLATE NOCASE, p.id
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()

        items = []
        for row in rows:
            content = row["content_lang"] if row["content_lang"] else row["content_text"]
            items.append(
                {
                    "id": row["id"],
                    "url": row["url"],
                    "title": row["title"],
                    "category": row["category"],
                    "subcategory": row["subcategory"],
                    "lang": lang if row["content_lang"] else "en",
                    "snippet": (content or "")[:600],
                }
            )

        return {"items": items, "count": len(items)}

    def _row_to_rule_detail(row, lang: str) -> dict:
        html_content = row["content_html_en"]
        text_content = row["content_lang"] if row["content_lang"] else row["content_text"]
        return {
            "id": row["id"],
            "url": row["url"],
            "title": row["title"],
            "category": row["category"],
            "subcategory": row["subcategory"],
            "lang_served": lang if row["content_lang"] else "en",
            "content": text_content,
            "content_html_en": html_content,
            "has_html": bool(html_content),
        }

    @app.get("/rules/{page_id}")
    def get_rule(page_id: int, lang: str = Query("es", pattern="^[a-z]{2}$")) -> dict:
        with connect(db_path) as conn:
            row = conn.execute(
                """
                SELECT p.id, p.url, p.title, p.category, p.subcategory,
                       COALESCE(p.content_text_en, p.content_en) AS content_text,
                       p.content_html_en,
                       t.content AS content_lang
                FROM pages p
                LEFT JOIN translations t ON t.page_id = p.id AND t.lang = ?
                WHERE p.id = ?
                """,
                (lang, page_id),
            ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Rule not found")
        return _row_to_rule_detail(row, lang=lang)

    @app.get("/rules/by-url")
    def get_rule_by_url(url: str, lang: str = Query("es", pattern="^[a-z]{2}$")) -> dict:
        decoded_url = unquote(url)
        with connect(db_path) as conn:
            row = conn.execute(
                """
                SELECT p.id, p.url, p.title, p.category, p.subcategory,
                       COALESCE(p.content_text_en, p.content_en) AS content_text,
                       p.content_html_en,
                       t.content AS content_lang
                FROM pages p
                LEFT JOIN translations t ON t.page_id = p.id AND t.lang = ?
                WHERE p.url = ?
                """,
                (lang, decoded_url),
            ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Rule not found for URL")
        return _row_to_rule_detail(row, lang=lang)

    @app.get("/rules/{page_id}/related")
    def related_rules(page_id: int, limit: int = Query(10, ge=1, le=50), lang: str = Query("es", pattern="^[a-z]{2}$")) -> dict:
        request_payload = {"page_id": page_id, "limit": limit, "lang": lang}
        key = _cache_key("related", request_payload)

        with connect(db_path) as conn:
            cached = conn.execute("SELECT payload_json FROM semantic_cache WHERE cache_key = ?", (key,)).fetchone()
            if cached:
                return json.loads(cached[0])

            current = conn.execute("SELECT id, COALESCE(content_text_en, content_en) AS content_source FROM pages WHERE id = ?", (page_id,)).fetchone()
            if not current:
                raise HTTPException(status_code=404, detail="Rule not found")

            source_vec_row = conn.execute("SELECT vector_json FROM page_vectors WHERE page_id = ?", (page_id,)).fetchone()
            source_vec = from_json(source_vec_row[0]) if source_vec_row else build_hash_embedding(current["content_source"])

            candidates = conn.execute(
                """
                SELECT p.id, p.title, p.category, p.subcategory, p.url,
                       COALESCE(p.content_text_en, p.content_en) AS content_source,
                       pv.vector_json
                FROM pages p
                LEFT JOIN page_vectors pv ON pv.page_id = p.id
                WHERE p.id != ?
                LIMIT 1000
                """,
                (page_id,),
            ).fetchall()

            scored = []
            for row in candidates:
                target_vec = from_json(row["vector_json"]) if row["vector_json"] else build_hash_embedding(row["content_source"])
                score = cosine(source_vec, target_vec)
                scored.append((score, row))

            scored.sort(key=lambda item: item[0], reverse=True)
            items = [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "category": row["category"],
                    "subcategory": row["subcategory"],
                    "url": row["url"],
                    "score": round(score, 4),
                }
                for score, row in scored[:limit]
            ]
            payload = {"items": items, "count": len(items)}

            conn.execute(
                "INSERT OR REPLACE INTO semantic_cache (cache_key, payload_json, created_at) VALUES (?, ?, datetime('now'))",
                (key, json.dumps(payload, ensure_ascii=False)),
            )
            conn.commit()

        return payload

    return app


app = create_app()
