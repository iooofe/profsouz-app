import React, { useEffect, useState } from 'react';
import { ClipboardList, Flame, Flower2, HandCoins, Palmtree, TableProperties } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { formatCount, getErrorText } from '../lib/utils';
import { Alert, Spinner } from '../components/ui';

const ACTIONS = [
  { type: 'vacation', title: 'Путевка', text: 'Санаторий, дом отдыха, детский лагерь', icon: Palmtree },
  { type: 'material', title: 'Материальная помощь', text: 'Больничный, рождение ребенка, лечение', icon: HandCoins },
  { type: 'coal', title: 'Уголь', text: 'Компенсация за уголь пенсионерам', icon: Flame },
  { type: 'funeral', title: 'Погребение', text: 'Выплата на погребение пенсионера', icon: Flower2 },
];

export default function DashboardTab({ onNavigate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        setData(await apiFetch('/api/v2/dashboard/'));
      } catch (e) {
        setError(getErrorText(e));
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const counts = [
    { label: 'работников', value: data?.counts?.workers, tab: 'workers' },
    { label: 'путевок', value: data?.counts?.vacation_requests, tab: 'reports' },
    { label: 'матпомощь', value: data?.counts?.material_requests, tab: 'reports' },
    { label: 'уголь', value: data?.counts?.coal_requests, tab: 'reports' },
    { label: 'погребение', value: data?.counts?.funeral_requests, tab: 'reports' },
  ];
  const period = data?.current_statement_period;

  return (
    <div className="home">
      {error && <Alert tone="error">{error}</Alert>}

      <section className="home-start" aria-labelledby="home-start-title">
        <h2 id="home-start-title">Оформить заявление</h2>
        <p>Выберите вид. Документ Word скачается сразу после создания.</p>
        <div className="home-actions">
          {ACTIONS.map(({ type, title, text, icon: Icon }) => (
            <button
              type="button"
              key={type}
              className="home-action"
              onClick={() => onNavigate('applications', { applicationType: type })}
            >
              <Icon size={22} strokeWidth={1.75} />
              <strong>{title}</strong>
              <span>{text}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="home-counts" aria-label="Сейчас в системе">
        {counts.map(({ label, value, tab }) => (
          <button type="button" key={label} className="home-count" onClick={() => onNavigate(tab)}>
            <strong>{loading ? <Spinner size={16} /> : formatCount(value)}</strong>
            <span>{label}</span>
          </button>
        ))}
      </section>

      <section className="home-docs">
        <button type="button" className="home-doc" onClick={() => onNavigate('statements')}>
          <TableProperties size={20} strokeWidth={1.75} />
          <span>
            <strong>Ведомости путевок</strong>
            <span>
              {period ? `Текущий период: ${period.period_start_human}–${period.period_end_human}` : 'Жартас и Шахтер'}
            </span>
          </span>
        </button>
        <button type="button" className="home-doc" onClick={() => onNavigate('lists')}>
          <ClipboardList size={20} strokeWidth={1.75} />
          <span>
            <strong>Списки выплат</strong>
            <span>Уголь, доплаты, ритуальные услуги, реестры</span>
          </span>
        </button>
      </section>
    </div>
  );
}
