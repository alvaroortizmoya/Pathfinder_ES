from __future__ import annotations

import importlib


def load_uvicorn():
    try:
        return importlib.import_module("uvicorn")
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Falta la dependencia 'uvicorn'. Instálala con: pip install uvicorn "
            "(o reinstala el proyecto con `pip install -e .`)."
        ) from exc


def run_api(host: str, port: int, reload: bool) -> None:
    uvicorn = load_uvicorn()
    uvicorn.run("pathfinder_es.api:app", host=host, port=port, reload=reload)
