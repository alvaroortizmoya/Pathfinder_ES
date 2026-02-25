from __future__ import annotations

import argparse
from pathlib import Path


from .scraper import AONScraper, utc_now_iso
from .storage import connect


def cmd_scrape(args: argparse.Namespace) -> None:
    db_path = Path(args.db)
    scraper = AONScraper(start_url=args.start_url, delay_s=args.delay, timeout_s=args.timeout)

    with connect(db_path) as conn:
        for page in scraper.crawl(max_pages=args.max_pages):
            conn.execute(
                """
                INSERT INTO pages (url, title, content_en, crawled_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                  title=excluded.title,
                  content_en=excluded.content_en,
                  crawled_at=excluded.crawled_at
                """,
                (page.url, page.title, page.content_en, utc_now_iso()),
            )
        conn.commit()

    print(f"[green]Scraping completado. DB:[/green] {db_path}")


def cmd_translate(args: argparse.Namespace) -> None:
    db_path = Path(args.db)
    from .translator import Translator

    translator = Translator(source="en", target=args.lang)

    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, content_en
            FROM pages
            ORDER BY id
            LIMIT ?
            """,
            (args.limit,),
        ).fetchall()

        for page_id, content_en in rows:
            translated = translator.translate(content_en)
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

    print(f"[green]Traducción completada[/green] ({args.lang}).")


def cmd_export(args: argparse.Namespace) -> None:
    db_path = Path(args.db)
    output = Path(args.output)

    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT p.url, p.title, p.content_en, t.content AS content_es
            FROM pages p
            LEFT JOIN translations t ON t.page_id = p.id AND t.lang = 'es'
            ORDER BY p.id
            """
        ).fetchall()

    import json

    payload = [
        {
            "url": row[0],
            "title": row[1],
            "content": {"en": row[2], "es": row[3]},
        }
        for row in rows
    ]

    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[green]Exportado:[/green] {output}")


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

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    if getattr(args, "output", None):
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    args.func(args)


if __name__ == "__main__":
    main()
