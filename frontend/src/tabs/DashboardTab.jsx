import React, { useEffect, useState } from 'react';
import {
  ArrowRight,
  CalendarRange,
  ClipboardList,
  Flame,
  Flower2,
  HandCoins,
  Palmtree,
  TableProperties,
  Users,
} from 'lucide-react';
import { apiFetch } from '../lib/api';
import { formatCount, getErrorText } from '../lib/utils';
import { Alert, Card, Spinner } from '../components/ui';

const QUICK_ACTIONS = [
  { type: 'vacation', title: 'Путевка', text: 'Санатории, дом отдыха, детский лагерь', icon: Palmtree, tone: 'teal' },
  { type: 'material', title: 'Материальная помощь', text: 'Больничный, рождение ребенка, лечение', icon: HandCoins, tone: 'blue' },
  { type: 'coal', title: 'Уголь', text: 'Компенсация за уголь пенсионерам', icon: Flame, tone: 'amber' },
  { type: 'funeral', title: 'Погребение', text: 'Выплата на погребение пенсионера', icon: Flower2, tone: 'violet' },
];

function greeting() {
  const hour = new Date().getHours();
  if (hour < 5) return 'Доброй ночи';
  if (hour < 12) return 'Доброе утро';
  if (hour < 18) return 'Добрый день';
  return 'Добрый вечер';
}

export default function DashboardTab({ user, onNavigate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await apiFetch('/api/v2/dashboard/');
      setData(response);
    } catch (e) {
      setError(getErrorText(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const stats = [
    { label: 'Работники', value: data?.counts?.workers, icon: Users, tone: 'blue', tab: 'workers' },
    { label: 'Путевки', value: data?.counts?.vacation_requests, icon: Palmtree, tone: 'teal', tab: 'reports' },
    { label: 'Матпомощь', value: data?.counts?.material_requests, icon: HandCoins, tone: 'indigo', tab: 'reports' },
    { label: 'Уголь', value: data?.counts?.coal_requests, icon: Flame, tone: 'amber', tab: 'reports' },
    { label: 'Погребение', value: data?.counts?.funeral_requests, icon: Flower2, tone: 'violet', tab: 'reports' },
  ];

  return (
    <div className="stack stack-lg">
      <div className="hero">
        <div>
          <h2>
            {greeting()}, {user.username}
          </h2>
          <p>
            {new Date().toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
          </p>
        </div>
        {data?.current_statement_period && (
          <div className="hero-period">
            <CalendarRange size={18} />
            <div>
              <span>Текущий период ведомостей</span>
              <strong>
                {data.current_statement_period.period_start_human} — {data.current_statement_period.period_end_human}
              </strong>
            </div>
          </div>
        )}
      </div>

      {error && <Alert tone="error">{error}</Alert>}

      <div className="stat-grid">
        {stats.map(({ label, value, icon: Icon, tone, tab }) => (
          <button type="button" className="stat-card" key={label} onClick={() => onNavigate(tab)}>
            <span className={`stat-icon tone-${tone}`}>
              <Icon size={20} />
            </span>
            <span className="stat-label">{label}</span>
            <strong className="stat-value">{loading ? <Spinner size={18} /> : formatCount(value)}</strong>
          </button>
        ))}
      </div>

      <Card title="Создать заявление" subtitle="Выберите вид — откроется форма с подсказками">
        <div className="quick-grid">
          {QUICK_ACTIONS.map(({ type, title, text, icon: Icon, tone }) => (
            <button
              type="button"
              key={type}
              className="quick-card"
              onClick={() => onNavigate('applications', { applicationType: type })}
            >
              <span className={`quick-icon tone-${tone}`}>
                <Icon size={22} />
              </span>
              <span className="quick-text">
                <strong>{title}</strong>
                <span>{text}</span>
              </span>
              <ArrowRight size={18} className="quick-arrow" />
            </button>
          ))}
        </div>
      </Card>

      <div className="link-grid">
        <button type="button" className="link-card" onClick={() => onNavigate('statements')}>
          <TableProperties size={20} />
          <div>
            <strong>Ведомости путевок</strong>
            <span>Жартас и Шахтер за текущий период</span>
          </div>
          <ArrowRight size={18} />
        </button>
        <button type="button" className="link-card" onClick={() => onNavigate('lists')}>
          <ClipboardList size={20} />
          <div>
            <strong>Списки выплат</strong>
            <span>Уголь, доплаты, ритуальные услуги, реестры</span>
          </div>
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
}
