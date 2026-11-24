# Сверка врачей

Локальная сверка специалистов из Medical API и Doctor Catalog. FastAPI отдаёт JSON, React запускается отдельно.

## Запуск

Нужны Python 3.11+ и Node.js 18+. Установите зависимости из корня проекта.

```sh
python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
```

Скопируйте `.env.example` в `.env` и укажите `MEDICAL_API_KEY`. Можно также задать ключ в переменных окружения сервера.

Запустите сервер API в первом терминале.

```sh
python backend/app.py
```

Запустите интерфейс во втором терминале.

```sh
npm --prefix frontend run dev
```

Откройте [127.0.0.1:5173](http://127.0.0.1:5173). API доступен на [127.0.0.1:8000/api/comparison](http://127.0.0.1:8000/api/comparison).

Команда `npm --prefix frontend run build` создаёт `frontend/bundle.js` для отдельной статической раздачи.

## Тесты

```sh
cd backend
python -m unittest discover -s tests
```
