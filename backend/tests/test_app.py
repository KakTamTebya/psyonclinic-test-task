import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app
from sources import Doctor, SourceError


class RefreshTests(unittest.TestCase):
    def test_error_preserves_previous_complete_snapshot(self):
        doc = Doctor("abc", "Орлов Иван Петрович", "Невролог", 10)
        with patch.object(app, "snapshot", None), patch.object(app, "load_sources") as load:
            load.side_effect = [(([doc], 1), ([], 1)), SourceError("Источник недоступен")]
            client = TestClient(app.app)
            before = client.get("/api/comparison").json()
            failed = client.post("/api/refresh")
            self.assertEqual(failed.status_code, 503)
            self.assertEqual(failed.json()["previous"], before)
            self.assertEqual(client.get("/api/comparison").json(), before)
