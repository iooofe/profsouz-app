import { useEffect, useState } from 'react';
import { apiFetch } from './api';

export const WORKER_FILE_FIELDS = [
  ['benefits_file', 'Файл льгот'],
  ['miner_glory_file', 'Файл славы'],
  ['house_passport_file', 'Паспорт дома'],
  ['pensioner_id_file', 'Удостоверение'],
  ['death_certificate_file', 'Справка о смерти'],
];

export const EMPTY_WORKER_FORM = {
  full_name: '',
  personnel_number: '',
  inn: '',
  status: 'worker',
  is_union_member: 'false',
  department: '',
  position: '',
  is_contract_member: 'false',
  phone: '+7',
  address: '',
  id_number: '',
  id_issue_date: '',
  id_issued_by: '',
  has_benefits: 'false',
  benefits_name: '',
  has_miner_glory: 'false',
  account_20_digit: 'KZ',
  current_account: 'KZ',
  enterprise_subdivision: '',
  regress_100_active: 'false',
  regress_29_active: 'false',
  regress_15_active: 'false',
  is_dead: 'false',
  death_date: '',
  user_id: '',
  family_members: [],
  existing_files: {},
  files: {
    benefits_file: null,
    miner_glory_file: null,
    house_passport_file: null,
    pensioner_id_file: null,
    death_certificate_file: null,
  },
};

export const RESORT_OPTIONS = [
  { value: 'orlenok', label: 'ДОЦ "Орленок"' },
  { value: 'zhartas', label: 'Санаторий "Жартас"' },
  { value: 'balkhash', label: 'Санаторий "Балхаш"' },
  { value: 'discovery', label: '"Дискавери"' },
  { value: 'shakhter', label: 'Дом отдыха "Шахтер"' },
];

export const ACCOUNT_TYPE_OPTIONS = [
  { value: '20_digit', label: 'Карточный счет' },
  { value: 'current', label: 'Текущий счет' },
];

export const ASSISTANCE_TYPE_OPTIONS = [
  { value: 'sick_leave', label: 'Больничный лист' },
  { value: 'childbirth', label: 'Рождение ребенка' },
  { value: 'funeral', label: 'Погребение близких родственников' },
  { value: 'treatment', label: 'На лечение' },
];

export const WORKER_CATEGORY_OPTIONS = [
  { value: 'all', label: 'Все' },
  { value: 'workers', label: 'Все работающие' },
  { value: 'pensioners', label: 'Все пенсионеры' },
  { value: 'regress', label: 'Все регрессники' },
  { value: 'worker', label: 'Только работники' },
  { value: 'pensioner', label: 'Только пенсионеры' },
  { value: 'regressnik', label: 'Только регрессники' },
  { value: 'regressnik_worker', label: 'Регрессники-работники' },
  { value: 'regressnik_pensioner', label: 'Регрессники-пенсионеры' },
];

export const REPORT_TYPE_LABEL = {
  vacation: 'Путевка',
  material: 'Матпомощь',
  coal: 'Уголь',
  funeral: 'Погребение',
};

const PENSIONER_STATUSES = new Set(['pensioner', 'regressnik_pensioner']);

export function cn(...parts) {
  return parts.filter(Boolean).join(' ');
}

export function getErrorText(error) {
  if (!error) return '';
  if (typeof error === 'string') return error;
  if (error.message) return error.message;
  return 'Ошибка запроса';
}

export function formatMoney(value) {
  if (value === null || value === undefined || value === '') return '—';
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatCount(value) {
  const n = Number(value || 0);
  return n.toLocaleString('ru-RU');
}

export function pluralRu(n, one, few, many) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

export function initials(name) {
  const parts = String(name || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (!parts.length) return '?';
  return (parts[0][0] + (parts[1]?.[0] || '')).toUpperCase();
}

export function triggerDownload(url) {
  if (!url) return;
  const iframe = document.createElement('iframe');
  iframe.style.display = 'none';
  iframe.src = url;
  document.body.appendChild(iframe);
  window.setTimeout(() => {
    iframe.remove();
  }, 60_000);
}

export function toBooleanString(value) {
  return value ? 'true' : 'false';
}

export function isPensionerStatus(status) {
  return PENSIONER_STATUSES.has(status);
}

export function workerStatusTone(status) {
  if (status === 'worker') return 'green';
  if (status === 'pensioner') return 'amber';
  if (String(status || '').startsWith('regressnik')) return 'violet';
  return 'gray';
}

export function requestStatusTone(status) {
  if (status === 'active') return 'green';
  if (status === 'pending') return 'amber';
  if (status === 'inactive') return 'red';
  return 'gray';
}

export function normalizeKzAccountInput(value, allowEmpty = false) {
  const raw = String(value ?? '').toUpperCase().replace(/\s+/g, '');
  if (allowEmpty && raw === '') return '';
  const body = raw.startsWith('KZ') ? raw.slice(2) : raw.replace(/^K?Z?/, '');
  const digits = body.replace(/\D/g, '');
  return `KZ${digits}`.slice(0, 20);
}

export function resolveWorkerAccount(worker, accountType = '20_digit') {
  const card = normalizeKzAccountInput(worker?.card_account || worker?.account_20_digit || '', true);
  const current = normalizeKzAccountInput(worker?.current_account || '', true);
  if (accountType === '20_digit') {
    return card || current || 'KZ';
  }
  return current || card || 'KZ';
}

export function hasAccount(value) {
  const v = String(value || '').trim();
  return v !== '' && v.toUpperCase() !== 'KZ';
}

export function useDebounce(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}

export const MOBILE_QUERY = '(max-width: 768px)';

export function useMediaQuery(query) {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);

  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);
    onChange();
    if (mql.addEventListener) {
      mql.addEventListener('change', onChange);
      return () => mql.removeEventListener('change', onChange);
    }
    mql.addListener(onChange);
    return () => mql.removeListener(onChange);
  }, [query]);

  return matches;
}

export function useIsMobile() {
  return useMediaQuery(MOBILE_QUERY);
}

export async function getReferences() {
  return apiFetch('/api/v2/reference/');
}

export function isEnergougol(user) {
  return (user?.username || '').toUpperCase() === 'ЭНЕРГОУГОЛЬ';
}
