from __future__ import annotations

import argparse
import json
from pathlib import Path

from .scraper import AONScraper, utc_now_iso
from .semantic import build_hash_embedding, to_json, utc_now_iso as semantic_now
from .storage import connect
from .server import run_api


def cmd_scrape(args: argparse.Namespace) -> None:
    db_path = Path(args.db)
    scraper = AONScraper(start_url=args.start_url, delay_s=args.delay, timeout_s=args.timeout)

    with connect(db_path) as conn:
        for page in scraper.crawl(max_pages=args.max_pages):
            conn.execute(
                """
                INSERT INTO pages (url, title, category, subcategory, content_en, content_text_en, content_html_en, crawled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                  title=excluded.title,
                  category=excluded.category,
                  subcategory=excluded.subcategory,
                  content_en=excluded.content_en,
                  content_text_en=excluded.content_text_en,
                  content_html_en=excluded.content_html_en,
                  crawled_at=excluded.crawled_at
                """,
                (page.url, page.title, page.category, page.subcategory, page.content_text_en, page.content_text_en, page.content_html_en, utc_now_iso()),
            )
        conn.commit()

    print(f"Scraping completado. DB: {db_path}")


def cmd_translate(args: argparse.Namespace) -> None:
    db_path = Path(args.db)
    from .translator import Translator

    translator = Translator(source="en", target=args.lang)

    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, COALESCE(content_text_en, content_en) AS content_source
            FROM pages
            ORDER BY id
            LIMIT ?
            """,
            (args.limit,),
        ).fetchall()

        for page_id, content_source in rows:
            translated = translator.translate(content_source)
            conn.execute(
                """
                INSERT INTO translations (page_id, lang, content, translated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(page_id, lang) DO UPDATE SET
                  content=excluded.content,
                  translated_at=excluded.translated_at
                """,
                (page_id, args.lang, translated, utc_now_iso()),
            )
        conn.commit()

    print(f"Traducción completada ({args.lang}).")


def cmd_export(args: argparse.Namespace) -> None:
    db_path = Path(args.db)
    output = Path(args.output)

    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT p.url, p.title, p.category, p.subcategory, COALESCE(p.content_text_en, p.content_en), p.content_html_en, t.content AS content_es
            FROM pages p
            LEFT JOIN translations t ON t.page_id = p.id AND t.lang = 'es'
            ORDER BY p.id
            """
        ).fetchall()

    payload = [
        {
            "url": row[0],
            "title": row[1],
            "category": row[2],
            "subcategory": row[3],
            "content": {"en": row[4], "es": row[6]},
            "content_html_en": row[5],
        }
        for row in rows
    ]

    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exportado: {output}")


def cmd_embed(args: argparse.Namespace) -> None:
    db_path = Path(args.db)
    with connect(db_path) as conn:
        rows = conn.execute("SELECT id, COALESCE(content_text_en, content_en) AS content_source FROM pages ORDER BY id LIMIT ?", (args.limit,)).fetchall()
        for row in rows:
            vec = build_hash_embedding(row["content_source"], dims=args.dims)
            conn.execute(
                """
                INSERT INTO page_vectors (page_id, model, vector_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(page_id) DO UPDATE SET
                  model=excluded.model,
                  vector_json=excluded.vector_json,
                  updated_at=excluded.updated_at
                """,
                (row["id"], f"hash-{args.dims}", to_json(vec), semantic_now()),
            )
        conn.commit()
    print(f"Embeddings generados para {len(rows)} páginas")


def cmd_serve(args: argparse.Namespace) -> None:
    run_api(host=args.host, port=args.port, reload=args.reload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pipeline scraper + traductor para AON Pathfinder 2e")
    sub = parser.add_subparsers(dest="command", required=True)

    scrape = sub.add_parser("scrape", help="Rastrear páginas y guardar contenido en inglés")
    scrape.add_argument("--db", default="data/pathfinder.db")
    scrape.add_argument("--start-url", default="https://2e.aonprd.com")
    scrape.add_argument("--max-pages", type=int, default=100)
    scrape.add_argument("--delay", type=float, default=1.0)
    scrape.add_argument("--timeout", type=int, default=30)
    scrape.set_defaults(func=cmd_scrape)

    translate = sub.add_parser("translate", help="Traducir páginas al idioma objetivo")
    translate.add_argument("--db", default="data/pathfinder.db")
    translate.add_argument("--lang", default="es")
    translate.add_argument("--limit", type=int, default=1000)
    translate.set_defaults(func=cmd_translate)

    export = sub.add_parser("export", help="Exportar JSON bilingüe (en/es)")
    export.add_argument("--db", default="data/pathfinder.db")
    export.add_argument("--output", default="data/pathfinder_bilingual.json")
    export.set_defaults(func=cmd_export)

    embed = sub.add_parser("embed", help="Generar embeddings hash para búsqueda semántica")
    embed.add_argument("--db", default="data/pathfinder.db")
    embed.add_argument("--limit", type=int, default=100000)
    embed.add_argument("--dims", type=int, default=128)
    embed.set_defaults(func=cmd_embed)

    serve = sub.add_parser("serve", help="Arrancar API FastAPI")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    serve.set_defaults(func=cmd_serve)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "db", None):
        Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    if getattr(args, "output", None):
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    args.func(args)


if __name__ == "__main__":
    main()
