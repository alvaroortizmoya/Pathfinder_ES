import types
import unittest
from unittest.mock import patch

from pathfinder_es import server


class ServerTests(unittest.TestCase):
    def test_load_uvicorn_raises_clear_error_when_missing(self):
        with patch("pathfinder_es.server.importlib.import_module", side_effect=ModuleNotFoundError):
            with self.assertRaises(SystemExit) as ctx:
                server.load_uvicorn()

        self.assertIn("uvicorn", str(ctx.exception))
        self.assertIn("pip install", str(ctx.exception))

    def test_run_api_calls_uvicorn_run(self):
        calls = {}

        def fake_run(app, host, port, reload):
            calls["app"] = app
            calls["host"] = host
            calls["port"] = port
            calls["reload"] = reload

        fake_uvicorn = types.SimpleNamespace(run=fake_run)

        with patch("pathfinder_es.server.load_uvicorn", return_value=fake_uvicorn):
            server.run_api(host="127.0.0.1", port=8001, reload=True)

        self.assertEqual(calls["app"], "pathfinder_es.api:app")
        self.assertEqual(calls["host"], "127.0.0.1")
        self.assertEqual(calls["port"], 8001)
        self.assertTrue(calls["reload"])


if __name__ == "__main__":
    unittest.main()
