import unittest

from matching import reconcile
from sources import Doctor


def doctor(name, specialty="Невролог", id="1", years=10):
    return Doctor(id, name, specialty, years)


class MatchingTests(unittest.TestCase):
    def test_spelling_and_order_with_different_experience(self):
        api = doctor("Орёл Иван Петрович")
        catalog = doctor("Иван   Петрович ОРЕЛ", "врач-невропатолог", years=12)
        result, = reconcile([api], [catalog])
        self.assertEqual(result["status"], "exact")
        self.assertEqual(result["catalog"]["name"], catalog.name)
        self.assertEqual(result["api"]["experience"], 10)

    def test_initials_missing_patronymic_typo_and_specialty_conflict(self):
        api = doctor("Орлов Иван Петрович")
        for candidate in (doctor("Орлов И.П."), doctor("И. П. Орлов"), doctor("Орлов Иван"),
                          doctor("Орлов Иван Сергеевич"), doctor("Оролв Иван Петрович"),
                          doctor("Орлоф Иван Петрович"), doctor("Орлоов Иван Петрович"),
                          doctor("Орлв Иван Петрович"),
                          doctor(api.name, "Терапевт")):
            with self.subTest(candidate=candidate):
                result, = reconcile([api], [candidate])
                self.assertEqual(result["status"], "possible")
                self.assertTrue(result["reason"])

    def test_duplicate_full_names_require_review(self):
        same = "Орлов Иван Петрович"
        result = reconcile([doctor(same)], [doctor(same, id="a"), doctor(same, id="b")])
        self.assertEqual(len(result), 2)
        self.assertTrue(all(r["status"] == "possible" and "несколько" in r["reason"] for r in result))

    def test_same_last_name_and_specialty_are_insufficient(self):
        result = reconcile([doctor("Орлов Иван Петрович")], [doctor("Орлов Олег Николаевич")])
        self.assertEqual({r["status"] for r in result}, {"api", "catalog"})
