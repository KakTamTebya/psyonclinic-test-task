from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
import requests


ORIGIN = "https://interview.psyonclinic.ru"
API_LIMIT = 200
CATALOG_PAGES = 30


class SourceError(Exception):
    pass


@dataclass(frozen=True)
class Doctor:
    id: str
    name: str
    specialty: str
    experience: int | None
    clinic: str | None = None
    price: str | None = None


def get_page(session, path, source, **params):
    try:
        response = session.get(ORIGIN + path, params=params, timeout=(5, 15), allow_redirects=False)
    except requests.RequestException as exc:
        raise SourceError(f"{source} не отвечает. Проверьте соединение и повторите обновление.") from exc
    if response.status_code in (401, 403):
        raise SourceError(f"{source} отклонил доступ. Проверьте MEDICAL_API_KEY на сервере." if source == "Medical API" else f"{source} отклонил доступ.")
    if response.status_code == 429:
        raise SourceError(f"{source} ограничил частоту запросов. Попробуйте обновить данные позже.")
    if response.status_code != 200:
        raise SourceError(f"{source} вернул HTTP {response.status_code}. Повторите обновление позже.")
    return response


def load_api(key):
    if not key:
        raise SourceError("Укажите MEDICAL_API_KEY в серверном окружении или файле .env и перезапустите приложение.")
    records = {}
    with requests.Session() as session:
        session.headers.update({"Authorization": f"Bearer {key}", "Accept": "application/json"})
        page = 0
        received = 0
        while received < API_LIMIT:
            page += 1
            response = get_page(session, "/api/v1/specialists", "Medical API", page=page, per_page=100)
            try:
                body = response.json()
                if int(body["current_page"]) != page or not isinstance(body["data"], list):
                    raise ValueError("Unexpected page")
                batch = body["data"][:API_LIMIT - received]
                received += len(batch)
                for item in batch:
                    name = " ".join(str(item[k]).strip() for k in ("last_name", "first_name", "middle_name") if item.get(k))
                    specialty = item["specialty"]
                    if not name or not isinstance(specialty, str) or not specialty.strip():
                        raise ValueError("Missing name or specialty")
                    years = item.get("experience_years")
                    doc = Doctor(str(item["id"]), name, specialty, int(years) if years is not None else None)
                    records[doc.id] = doc
                if not batch or page >= int(body["last_page"]):
                    break
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                raise SourceError("Не удалось прочитать список специалистов Medical API. Проверьте формат ответа.") from exc
    return list(records.values()), page


def parse_catalog(html):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("article.doctor-card")
    if not cards and not re.search(r"Найдено:\s*0\b", soup.get_text(" ", strip=True)):
        raise SourceError("В HTML каталога не найдены карточки врачей. Возможно, изменилась разметка.")
    records = []
    for card in cards:
        link = card.select_one("h3 a[href]")
        specialty = card.select_one("h3 + p")
        if not link or not specialty or not link.get_text(strip=True) or not specialty.get_text(strip=True):
            raise SourceError("В карточке Doctor Catalog отсутствует ФИО или специальность.")
        years = re.search(r"Стаж\s*[:·]?\s*(\d+)", card.get_text(" ", strip=True), re.I)
        clinic = card.select_one("p.truncate")
        price = next((s.get_text(" ", strip=True) for s in card.select("strong") if "₽" in s.get_text()), None)
        records.append(Doctor(urlsplit(link["href"]).path, link.get_text(" ", strip=True),
                              specialty.get_text(" ", strip=True), int(years[1]) if years else None,
                              clinic.get_text(" ", strip=True) if clinic else None, price))
    return records, soup.select_one('a[rel~="next"]') is not None


def load_catalog():
    records = {}
    with requests.Session() as session:
        for page in range(1, CATALOG_PAGES + 1):
            response = get_page(session, "/doctors", "Doctor Catalog", page=page, sort="experience")
            doctors, more = parse_catalog(response.content.decode("utf-8", errors="replace"))
            records.update((doctor.id, doctor) for doctor in doctors)
            if not more:
                break
    return list(records.values()), page


def load_sources(key):
    with ThreadPoolExecutor(max_workers=2) as pool:
        api = pool.submit(load_api, key)
        catalog = pool.submit(load_catalog)
        return api.result(), catalog.result()
