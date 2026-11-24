from collections import Counter, defaultdict
from dataclasses import asdict
import re
import unicodedata

from rapidfuzz.distance import OSA


SPECIALTIES = {"невропатолог": "невролог", "окулист": "офтальмолог"}
ORDER = {"possible": 0, "exact": 1, "api": 2, "catalog": 2}


def tokens(value):
    text = unicodedata.normalize("NFKC", value).casefold().replace("ё", "е")
    return tuple(re.findall(r"[^\W\d_]+", text))


def index(doctors):
    records, groups = {}, defaultdict(list)
    for doctor in doctors:
        parts = tokens(doctor.name)
        full = tuple(sorted(parts)) if len(parts) >= 3 and all(len(word) > 1 for word in parts) else ()
        label = " ".join(word for word in tokens(doctor.specialty) if word != "врач")
        specialty = SPECIALTIES.get(label, label)
        records[doctor.id] = (doctor, parts, full, specialty)
        if full and specialty:
            groups[full, specialty].append(doctor.id)
    return records, {key: ids[0] for key, ids in groups.items() if len(ids) == 1}


def name_reason(a, b):
    if min(len(a), len(b)) < 2:
        return None
    # Some catalog cards put initials before the surname.
    if len(b[-1]) > 1 and len(b[0]) == 1:
        b = (b[-1], *b[:-1])
    if a[0] == b[0] and a[1] == b[1] and len(a[1]) > 1:
        if min(len(a), len(b)) == 2:
            return "Совпадают фамилия, имя и специальность. Для проверки не хватает отчества."
        if len(a) == len(b) == 3 and a[2] != b[2]:
            return "Совпадают фамилия, имя и специальность. Отчество указано по-разному."
    if a[0] == b[0] and any(len(x) == 1 for x in (*a[1:], *b[1:])):
        if all(x == y or (min(len(x), len(y)) == 1 and x[0] == y[0]) for x, y in zip(a[1:], b[1:])):
            return "Совпадают фамилия, инициалы и специальность. Имя или отчество сокращено."
    if len(a) == len(b) and len(a) >= 3:
        differences = [(x, y) for x, y in zip(a, b) if x != y]
        if len(differences) == 1:
            x, y = differences[0]
            if min(len(x), len(y)) >= 4 and OSA.distance(x, y, score_cutoff=1) == 1:
                return "Специальности совпадают. В одной части ФИО различается написание на одну букву или переставлены соседние буквы."
    return None


def row(status, api=None, catalog=None, reason=""):
    return {"status": status, "api": asdict(api) if api else None,
            "catalog": asdict(catalog) if catalog else None, "reason": reason}


def reconcile(api, catalog):
    (left, unique_api), (right, unique_catalog) = map(index, (api, catalog))
    rows = []
    for key in unique_api.keys() & unique_catalog.keys():
        a = left.pop(unique_api[key])[0]
        b = right.pop(unique_catalog[key])[0]
        rows.append(row("exact", a, b))

    candidates = []
    for a, a_name, a_full, a_spec in left.values():
        for b, b_name, b_full, b_spec in right.values():
            if a_full and a_full == b_full:
                reason = ("Полное ФИО и специальность повторяются в выборке."
                          if a_spec == b_spec else "Полное ФИО совпадает. Источники указывают разные специальности.")
            else:
                reason = name_reason(a_name, b_name) if a_spec and a_spec == b_spec else None
            if reason:
                candidates.append((a, b, reason))
    left_counts = Counter(a.id for a, _, _ in candidates)
    right_counts = Counter(b.id for _, b, _ in candidates)
    for a, b, reason in candidates:
        if left_counts[a.id] > 1 or right_counts[b.id] > 1:
            reason += " Подходят несколько записей."
        rows.append(row("possible", a, b, reason))
    rows.extend(row("api", api=d) for d, *_ in left.values() if not left_counts[d.id])
    rows.extend(row("catalog", catalog=d) for d, *_ in right.values() if not right_counts[d.id])
    return sorted(rows, key=lambda r: (ORDER[r["status"]], tokens((r["api"] or r["catalog"])["name"])))
