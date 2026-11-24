import {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';

const apiUrl = 'http://127.0.0.1:8000';
const catalogOrigin = 'https://interview.psyonclinic.ru';
const labels = {
  exact: 'Совпало', possible: 'Возможно совпадение',
  api: 'Только в Medical API', catalog: 'Только в Doctor Catalog',
};
const fields = {
  name: 'ФИО', specialty: 'Специальность', experience: 'Стаж, лет', clinic: 'Клиника', price: 'Публичная цена',
};
const normalize = text => text.normalize('NFKC').toLowerCase().replaceAll('ё', 'е')
  .replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
const rowKey = ({api, catalog}) => JSON.stringify([api?.id, catalog?.id]);

function DoctorDetail({row}) {
  const {api, catalog, status, reason} = row;
  const url = catalog?.id.startsWith('/doctors/') && new URL(catalogOrigin + catalog.id);
  return <section aria-label="Карточка сверки">
    <h2>{(api ?? catalog).name}</h2>
    <p className={status}>{labels[status]}</p>
    {reason && <p>{reason}</p>}
    {(!api || !catalog) &&
      <p>В загруженной выборке {api ? 'Doctor Catalog' : 'Medical API'} подходящая запись не найдена.</p>}
    <table aria-label="Сравнение полей по источникам">
      <thead><tr><th scope="col">Поле</th><th scope="col">Medical API</th><th scope="col">Doctor Catalog</th></tr></thead>
      <tbody>{Object.entries(fields).map(([key, title]) => {
        const different = api && catalog && ['name', 'specialty', 'experience'].includes(key)
          && api[key] !== catalog[key];
        return <tr key={key} className={different ? 'different' : undefined}>
          <th scope="row">{title}{different && <small>Различие</small>}</th>
          <td>{api?.[key] ?? '—'}</td><td>{catalog?.[key] ?? '—'}</td>
        </tr>;
      })}</tbody>
    </table>
    {url && url.pathname.startsWith('/doctors/') &&
      <p><a href={url.href} target="_blank" rel="noreferrer">Карточка в Doctor Catalog ↗</a></p>}
  </section>;
}

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('');
  const [selection, setSelection] = useState(null);

  async function load(refresh = false) {
    setLoading(true);
    setError('');
    try {
      const path = refresh ? '/api/refresh' : '/api/comparison';
      const response = await fetch(apiUrl + path, {method: refresh ? 'POST' : 'GET', cache: 'no-store'});
      const body = await response.json();
      if (response.ok) setData(body);
      else {
        if (body.previous) setData(body.previous);
        setError(body.error || 'Сервер не смог обновить данные.');
      }
    } catch {
      setError('Не удалось получить данные от сервера.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const terms = normalize(search).split(' ').filter(Boolean);
  const rows = data?.rows.filter(row => {
    if (filter && row.status !== filter && !(filter === 'only' && (!row.api || !row.catalog))) return false;
    return !terms.length || [row.api, row.catalog].some(doctor => {
      if (!doctor) return false;
      const text = normalize(`${doctor.name} ${doctor.specialty}`);
      return terms.every(term => text.includes(term));
    });
  }) ?? [];
  const selected = rows.find(row => rowKey(row) === selection) ?? rows[0];

  return <main>
    <header>
      <h1>Сверка врачей</h1>
      <button disabled={loading} onClick={() => load(true)}>{loading ? 'Загрузка…' : 'Обновить данные'}</button>
    </header>
    {data && <p>Medical API — {data.apiCount} · Doctor Catalog — {data.catalogCount}
      {' · Обновлено '}{new Date(data.updatedAt).toLocaleString('ru-RU')}</p>}
    <p role="status">{loading ? 'Загружаем данные…' : error && error +
      (data ? ' Показана последняя успешная сверка.' : '')}</p>
    <div className="filters">
      <label>Поиск <input type="search" placeholder="ФИО или специальность" value={search}
        onChange={event => setSearch(event.target.value)} /></label>
      <label>Статус <select value={filter} onChange={event => setFilter(event.target.value)}>
        <option value="">Все статусы</option>
        <option value="only">Только в одном источнике</option>
        {Object.entries(labels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
      </select></label>
    </div>
    {data && <p aria-live="polite">Найдено {rows.length} из {data.rows.length}</p>}
    <div className="results">
      <ul aria-label="Найденные записи">{rows.map(row => {
        const doctor = row.api ?? row.catalog;
        return <li key={rowKey(row)}><button aria-pressed={row === selected} onClick={() => setSelection(rowKey(row))}>
          <strong>{doctor.name}</strong>
          <small>{doctor.specialty} · {labels[row.status]}</small>
        </button></li>;
      })}</ul>
      {selected && <DoctorDetail row={selected} />}
    </div>
  </main>;
}

createRoot(document.getElementById('root')).render(<App />);
