import unittest
from unittest.mock import Mock, patch

from sources import SourceError, load_api, parse_catalog


class SourceTests(unittest.TestCase):
    def test_html_card_uses_price_instead_of_rating(self):
        html = """<article class="doctor-card"><h3><a href="/doctors/ivanova">Иванова О. А.</a></h3>
                  <p>Терапевт</p><p>Стаж 0 лет</p><strong>4,8</strong><p class="truncate">Клиника</p>
                  <strong>от 2 050 ₽</strong></article><a rel="next" href="?page=2">Далее</a>"""
        records, more = parse_catalog(html)
        self.assertTrue(more)
        self.assertEqual((records[0].experience, records[0].clinic, records[0].price), (0, "Клиника", "от 2 050 ₽"))

    def test_missing_optional_fields_and_empty_catalog(self):
        docs, _ = parse_catalog('<article class="doctor-card"><h3><a href="/doctors/demo">Имя</a></h3><p>Врач</p></article>')
        self.assertIsNone(docs[0].price)
        self.assertIsNone(docs[0].experience)
        self.assertIsNone(docs[0].clinic)
        self.assertEqual(parse_catalog("<p>Найдено: 0</p>"), ([], False))
        with self.assertRaises(SourceError):
            parse_catalog("<p>Недоступно</p>")

    @patch("sources.get_page")
    def test_pagination_stops_at_200(self, get_page):
        def response(session, path, source, page, per_page):
            self.assertEqual(per_page, 100)
            items = [{"id": str(i), "last_name": "Орлов", "first_name": "Иван", "specialty": "Невролог"}
                     for i in range(100 * (page - 1), 100 * page)]
            return Mock(json=lambda: {"data": items, "current_page": page, "last_page": 3})
        get_page.side_effect = response
        doctors, pages = load_api("test-only")
        self.assertEqual((len(doctors), pages, get_page.call_count), (200, 2, 2))
