import React, { useEffect, useMemo, useState } from 'react';
import {
  BarChart3,
  Briefcase,
  Check,
  ClipboardList,
  Download,
  Eye,
  EyeOff,
  FileStack,
  Loader2,
  LogOut,
  Plus,
  Search,
  TableProperties,
  UserPlus,
  Users,
  X,
} from 'lucide-react';
import { apiFetch } from './lib/api';

const TABS = [
  { id: 'workers', label: 'Работники', icon: Users },
  { id: 'applications', label: 'Заявления', icon: UserPlus },
  { id: 'reports', label: 'Отчеты', icon: FileStack },
  { id: 'statements', label: 'Ведомости', icon: TableProperties },
  { id: 'lists', label: 'Списки', icon: ClipboardList },
  { id: 'dashboard', label: 'Сводка', icon: BarChart3 },
];

const EMPTY_WORKER_FORM = {
  full_name: '',
  personnel_number: '',
  inn: '',
  status: 'worker',
  is_union_member: 'false',
  department: '',
  position: '',
  is_contract_member: 'false',
  phone: '',
  address: '',
  id_number: '',
  id_issue_date: '',
  id_issued_by: '',
  has_benefits: 'false',
  benefits_name: '',
  has_miner_glory: 'false',
  account_20_digit: '',
  current_account: '',
  is_dead: 'false',
  death_date: '',
  user_id: '',
  family_members: [],
  files: {
    benefits_file: null,
    miner_glory_file: null,
    house_passport_file: null,
    pensioner_id_file: null,
    death_certificate_file: null,
  },
};

const RESORT_OPTIONS = [
  { value: 'orlenok', label: 'ДОЦ "Орленок"' },
  { value: 'zhartas', label: 'Санаторий "Жартас"' },
  { value: 'balkhash', label: 'Санаторий "Балхаш"' },
  { value: 'discovery', label: '"Дискавери"' },
  { value: 'shakhter', label: 'Дом отдыха "Шахтер"' },
];

const ACCOUNT_TYPE_OPTIONS = [
  { value: '20_digit', label: 'Карточный счет' },
  { value: 'current', label: 'Текущий счет' },
];

const ASSISTANCE_TYPE_OPTIONS = [
  { value: 'sick_leave', label: 'Больничный лист' },
  { value: 'childbirth', label: 'Рождение ребенка' },
  { value: 'funeral', label: 'Погребение близких родственников' },
  { value: 'treatment', label: 'На лечение' },
];

const PENSIONER_STATUSES = new Set(['pensioner', 'regressnik_pensioner']);

function cn(...parts) {
  return parts.filter(Boolean).join(' ');
}

function getErrorText(error) {
  if (!error) return '';
  if (typeof error === 'string') return error;
  if (error.message) return error.message;
  return 'Ошибка запроса';
}

function formatMoney(value) {
  if (value === null || value === undefined || value === '') return '—';
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function triggerDownload(url) {
  if (!url) return;
  const iframe = document.createElement('iframe');
  iframe.style.display = 'none';
  iframe.src = url;
  document.body.appendChild(iframe);
  window.setTimeout(() => {
    iframe.remove();
  }, 60_000);
}

function toBooleanString(value) {
  return value ? 'true' : 'false';
}

function isPensionerStatus(status) {
  return PENSIONER_STATUSES.has(status);
}

function normalizeKzAccountInput(value, allowEmpty = false) {
  const raw = String(value ?? '').toUpperCase().replace(/\s+/g, '');
  if (allowEmpty && raw === '') return '';
  const body = raw.startsWith('KZ') ? raw.slice(2) : raw.replace(/^K?Z?/, '');
  const digits = body.replace(/\D/g, '');
  return `KZ${digits}`.slice(0, 20);
}

function useDebounce(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}

async function getReferences() {
  return apiFetch('/api/v2/reference/');
}

function buildWorkerFormData(formState) {
  const fd = new FormData();
  fd.append('full_name', formState.full_name || '');
  fd.append('personnel_number', formState.personnel_number || '');
  fd.append('inn', formState.inn || '');
  fd.append('status', formState.status || 'worker');
  fd.append('is_union_member', formState.is_union_member === 'true' ? 'True' : 'False');
  fd.append('department', formState.department || '');
  fd.append('position', formState.position || '');
  fd.append('is_contract_member', formState.is_contract_member === 'true' ? 'True' : 'False');
  fd.append('phone', formState.phone || '');
  fd.append('address', formState.address || '');
  fd.append('id_number', formState.id_number || '');
  fd.append('id_issue_date', formState.id_issue_date || '');
  fd.append('id_issued_by', formState.id_issued_by || '');
  fd.append('has_benefits', formState.has_benefits === 'true' ? 'True' : 'False');
  fd.append('benefits_name', formState.benefits_name || '');
  fd.append('has_miner_glory', formState.has_miner_glory === 'true' ? 'True' : 'False');
  fd.append('account_20_digit', formState.account_20_digit || '');
  fd.append('current_account', formState.current_account || '');
  fd.append('is_dead', formState.is_dead === 'true' ? 'True' : 'False');
  fd.append('death_date', formState.death_date || '');

  if (formState.user_id) {
    fd.append('user_id', formState.user_id);
  }

  const family = (formState.family_members || []).map((item) => ({
    full_name: item.full_name || '',
    relationship: item.relationship || 'other',
    id_number: item.id_number || '',
    id_issue_date: item.id_issue_date || '',
    id_issued_by: item.id_issued_by || '',
    birth_date: item.birth_date || '',
  }));
  fd.append('family_members', JSON.stringify(family));

  const fileKeys = [
    'benefits_file',
    'miner_glory_file',
    'house_passport_file',
    'pensioner_id_file',
    'death_certificate_file',
  ];
  for (const key of fileKeys) {
    if (formState.files[key] instanceof File) {
      fd.append(key, formState.files[key]);
    }
  }

  return fd;
}

function App() {
  const [bootLoading, setBootLoading] = useState(true);
  const [authData, setAuthData] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [authError, setAuthError] = useState('');
  const [references, setReferences] = useState(null);

  const loadAuth = async () => {
    setBootLoading(true);
    setAuthError('');
    try {
      const bootstrap = await apiFetch('/api/v2/auth/bootstrap/');
      setAccounts(bootstrap.accounts || []);

      if (bootstrap.authenticated && bootstrap.user) {
        setAuthData(bootstrap.user);
        const ref = await getReferences();
        setReferences(ref);
      } else {
        setAuthData(null);
      }
    } catch (error) {
      setAuthError(getErrorText(error));
    } finally {
      setBootLoading(false);
    }
  };

  useEffect(() => {
    loadAuth();
  }, []);

  const handleLogin = async ({ username, password }) => {
    setAuthError('');
    const response = await apiFetch('/api/v2/auth/login/', {
      method: 'POST',
      body: { username, password },
    });
    setAuthData(response.user);
    const ref = await getReferences();
    setReferences(ref);
  };

  const handleLogout = async () => {
    try {
      await apiFetch('/api/v2/auth/logout/', { method: 'POST' });
    } catch {
      // ignore
    }
    setAuthData(null);
    setReferences(null);
    window.history.replaceState({}, '', '/login/');
  };

  if (bootLoading) {
    return (
      <div className="screen-center">
        <Loader2 className="spin" size={30} />
        <span>Загрузка...</span>
      </div>
    );
  }

  if (!authData) {
    return <LoginScreen accounts={accounts} onLogin={handleLogin} authError={authError} />;
  }

  return (
    <Shell
      user={authData}
      references={references}
      onLogout={handleLogout}
      onRefreshReference={async () => {
        const ref = await getReferences();
        setReferences(ref);
      }}
    />
  );
}

function LoginScreen({ accounts, onLogin, authError }) {
  const [username, setUsername] = useState(accounts[0] || '');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState('');

  useEffect(() => {
    if (!username && accounts.length > 0) {
      setUsername(accounts[0]);
    }
  }, [accounts, username]);

  const submit = async (event) => {
    event.preventDefault();
    setLocalError('');
    if (!username || !password) {
      setLocalError('Укажите аккаунт и пароль');
      return;
    }
    setLoading(true);
    try {
      await onLogin({ username, password });
      window.history.replaceState({}, '', '/');
    } catch (error) {
      setLocalError(getErrorText(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={submit}>
        <h1>Профсоюз</h1>
        <p>Вход в систему</p>

        <label>
          Аккаунт
          <select value={username} onChange={(e) => setUsername(e.target.value)}>
            {accounts.map((acc) => (
              <option key={acc} value={acc}>
                {acc}
              </option>
            ))}
          </select>
        </label>

        <label>
          Пароль
          <div className="password-field">
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Введите пароль"
              autoComplete="current-password"
            />
            <button
              type="button"
              className="password-toggle-btn"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </label>

        {(localError || authError) && <div className="error-banner">{localError || authError}</div>}

        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? (
            <>
              <Loader2 className="spin" size={16} /> Вход...
            </>
          ) : (
            'Войти'
          )}
        </button>
      </form>
    </div>
  );
}

function Shell({ user, references, onLogout, onRefreshReference }) {
  const [activeTab, setActiveTab] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('tab') || 'workers';
  });

  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set('tab', activeTab);
    window.history.replaceState({}, '', url);
  }, [activeTab]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Briefcase size={18} />
          <span>Профсоюз</span>
        </div>
        <nav>
          {TABS.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                className={cn('nav-btn', activeTab === tab.id && 'active')}
                onClick={() => setActiveTab(tab.id)}
              >
                <Icon size={16} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div>
            <h2>{TABS.find((t) => t.id === activeTab)?.label}</h2>
          </div>
          <div className="topbar-right">
            <div className="user-pill">{user.username}</div>
            <button className="btn btn-secondary" onClick={onLogout}>
              <LogOut size={14} />
              Выход
            </button>
          </div>
        </header>

        <section className="content">
          {activeTab === 'dashboard' && <DashboardTab />}
          {activeTab === 'workers' && (
            <WorkersTab user={user} references={references} onRefreshReference={onRefreshReference} />
          )}
          {activeTab === 'applications' && <ApplicationsTab user={user} />}
          {activeTab === 'reports' && <ReportsTab user={user} references={references} />}
          {activeTab === 'statements' && <StatementsTab />}
          {activeTab === 'lists' && <ListsTab user={user} references={references} />}
        </section>
      </main>
    </div>
  );
}

function DashboardTab() {
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

  if (loading) {
    return (
      <div className="card center">
        <Loader2 className="spin" size={20} />
      </div>
    );
  }

  if (error) {
    return <div className="error-banner">{error}</div>;
  }

  if (!data) return null;

  const stats = [
    ['Работники', data.counts?.workers],
    ['Заявления на путевку', data.counts?.vacation_requests],
    ['Матпомощь', data.counts?.material_requests],
    ['Уголь', data.counts?.coal_requests],
    ['Погребение', data.counts?.funeral_requests],
  ];

  return (
    <div className="dashboard-grid">
      {stats.map(([label, value]) => (
        <div className="stat-card" key={label}>
          <span>{label}</span>
          <strong>{value ?? 0}</strong>
        </div>
      ))}

      <div className="card card-wide">
        <h3>Текущий период ведомостей</h3>
        <p>
          {data.current_statement_period?.period_start_human} - {data.current_statement_period?.period_end_human}
        </p>
      </div>
    </div>
  );
}

function WorkersTab({ user, references, onRefreshReference }) {
  const [workers, setWorkers] = useState([]);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [formState, setFormState] = useState(EMPTY_WORKER_FORM);
  const [workerReports, setWorkerReports] = useState([]);

  const debouncedSearch = useDebounce(search, 250);

  const loadWorkers = async (targetPage = page) => {
    setLoading(true);
    setError('');
    try {
      const response = await apiFetch(
        `/api/v2/workers/?page=${targetPage}&page_size=50&search=${encodeURIComponent(debouncedSearch)}`
      );
      setWorkers(response.results || []);
      setPagination(response.pagination || null);
    } catch (e) {
      setError(getErrorText(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

  useEffect(() => {
    loadWorkers(page);
  }, [debouncedSearch, page]);

  const openCreate = () => {
    setEditingId(null);
    setFormError('');
    setWorkerReports([]);
    setFormState({ ...EMPTY_WORKER_FORM, user_id: user.is_admin ? '' : user.id });
    setFormOpen(true);
  };

  const openEdit = async (id) => {
    setFormError('');
    setEditingId(id);
    setWorkerReports([]);
    setSaving(false);
    try {
      const response = await apiFetch(`/api/v2/workers/${id}/`);
      const worker = response.worker;
      setWorkerReports(response.reports || []);
      setFormState({
        ...EMPTY_WORKER_FORM,
        full_name: worker.full_name || '',
        personnel_number: worker.personnel_number || '',
        inn: worker.inn || '',
        status: worker.status || 'worker',
        is_union_member: toBooleanString(worker.is_union_member),
        department: worker.department || '',
        position: worker.position || '',
        is_contract_member: toBooleanString(worker.is_contract_member),
        phone: worker.phone || '',
        address: worker.address || '',
        id_number: worker.id_number || '',
        id_issue_date: worker.id_issue_date || '',
        id_issued_by: worker.id_issued_by || '',
        has_benefits: toBooleanString(worker.has_benefits),
        benefits_name: worker.benefits_name || '',
        has_miner_glory: toBooleanString(worker.has_miner_glory),
        account_20_digit: worker.account_20_digit || '',
        current_account: worker.current_account || '',
        is_dead: toBooleanString(worker.is_dead),
        death_date: worker.death_date || '',
        user_id: worker.user_id ? String(worker.user_id) : '',
        family_members: worker.family_members || [],
        files: {
          benefits_file: null,
          miner_glory_file: null,
          house_passport_file: null,
          pensioner_id_file: null,
          death_certificate_file: null,
        },
      });
      setFormOpen(true);
    } catch (e) {
      setError(getErrorText(e));
    }
  };

  const closeForm = () => {
    setFormOpen(false);
    setEditingId(null);
    setFormError('');
    setWorkerReports([]);
  };

  const saveWorker = async (event) => {
    event.preventDefault();
    setSaving(true);
    setFormError('');
    try {
      const body = buildWorkerFormData(formState);
      if (editingId) {
        await apiFetch(`/api/v2/workers/${editingId}/`, { method: 'POST', body });
      } else {
        await apiFetch('/api/v2/workers/', { method: 'POST', body });
      }
      closeForm();
      await loadWorkers(page);
      if (user.is_admin) {
        await onRefreshReference();
      }
    } catch (e) {
      setFormError(getErrorText(e));
    } finally {
      setSaving(false);
    }
  };

  const deleteWorker = async (id) => {
    if (!window.confirm('Удалить работника?')) return;
    try {
      await apiFetch(`/api/v2/workers/${id}/`, { method: 'DELETE' });
      await loadWorkers(page);
    } catch (e) {
      setError(getErrorText(e));
    }
  };

  const updateFamilyMember = (index, key, value) => {
    setFormState((prev) => {
      const nextFamily = [...(prev.family_members || [])];
      nextFamily[index] = { ...nextFamily[index], [key]: value };
      return { ...prev, family_members: nextFamily };
    });
  };

  const addFamilyMember = () => {
    setFormState((prev) => ({
      ...prev,
      family_members: [
        ...(prev.family_members || []),
        {
          full_name: '',
          relationship: 'other',
          id_number: '',
          id_issue_date: '',
          id_issued_by: '',
          birth_date: '',
        },
      ],
    }));
  };

  const removeFamilyMember = (index) => {
    setFormState((prev) => ({
      ...prev,
      family_members: (prev.family_members || []).filter((_, idx) => idx !== index),
    }));
  };

  const workerReportTypeLabel = {
    vacation: 'Путевка',
    material: 'Матпомощь',
    coal: 'Уголь',
    funeral: 'Погребение',
  };

  return (
    <div className="stack">
      <div className="toolbar">
        <div className="search-field">
          <Search size={14} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Поиск по ФИО, табельному, ИИН, участку..."
          />
        </div>
        <button className="btn btn-primary" onClick={openCreate}>
          <Plus size={14} /> Добавить
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        {loading ? (
          <div className="center">
            <Loader2 className="spin" size={20} />
          </div>
        ) : (
          <>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ФИО</th>
                    <th>Таб. номер</th>
                    <th>ИИН</th>
                    <th>Статус</th>
                    <th>Участок</th>
                    <th>Должность</th>
                    <th>Счета</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {workers.map((worker) => (
                    <tr key={worker.id}>
                      <td>{worker.full_name}</td>
                      <td>{worker.personnel_number || '—'}</td>
                      <td>{worker.inn || '—'}</td>
                      <td>
                        <span className={cn('badge', isPensionerStatus(worker.status) ? 'warn' : 'ok')}>
                          {worker.status_display}
                        </span>
                      </td>
                      <td>{worker.department || '—'}</td>
                      <td>{worker.position || '—'}</td>
                      <td>{worker.account_20_digit || worker.current_account || '—'}</td>
                      <td className="actions-cell">
                        <button className="btn btn-secondary" onClick={() => openEdit(worker.id)}>
                          Изм.
                        </button>
                        <button className="btn btn-danger" onClick={() => deleteWorker(worker.id)}>
                          Удалить
                        </button>
                      </td>
                    </tr>
                  ))}
                  {workers.length === 0 && (
                    <tr>
                      <td colSpan={8} className="empty-row">
                        Нет данных
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {pagination && pagination.pages > 1 && (
              <div className="pager">
                <button className="btn btn-secondary" disabled={!pagination.has_previous} onClick={() => setPage(1)}>
                  Первая
                </button>
                <button
                  className="btn btn-secondary"
                  disabled={!pagination.has_previous}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Назад
                </button>
                <span>
                  {pagination.page} / {pagination.pages}
                </span>
                <button
                  className="btn btn-secondary"
                  disabled={!pagination.has_next}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Вперед
                </button>
                <button
                  className="btn btn-secondary"
                  disabled={!pagination.has_next}
                  onClick={() => setPage(pagination.pages)}
                >
                  Последняя
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {formOpen && (
        <div className="modal-overlay" onClick={closeForm}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3>{editingId ? 'Редактирование работника' : 'Новый работник'}</h3>
              <button className="icon-btn" onClick={closeForm}>
                <X size={16} />
              </button>
            </div>

            <form className="form-grid" onSubmit={saveWorker}>
              <label>
                ФИО
                <input
                  value={formState.full_name}
                  onChange={(e) => setFormState((prev) => ({ ...prev, full_name: e.target.value }))}
                  required
                />
              </label>
              <label>
                Табельный номер
                <input
                  value={formState.personnel_number}
                  onChange={(e) => setFormState((prev) => ({ ...prev, personnel_number: e.target.value }))}
                />
              </label>
              <label>
                ИИН
                <input
                  value={formState.inn}
                  onChange={(e) => setFormState((prev) => ({ ...prev, inn: e.target.value }))}
                />
              </label>
              <label>
                Статус
                <select
                  value={formState.status}
                  onChange={(e) => setFormState((prev) => ({ ...prev, status: e.target.value }))}
                >
                  {(references?.worker_status_choices || [
                    { value: 'worker', label: 'Работник' },
                    { value: 'pensioner', label: 'Пенсионер' },
                  ]).map((statusItem) => (
                    <option key={statusItem.value} value={statusItem.value}>
                      {statusItem.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Член профсоюза
                <select
                  value={formState.is_union_member}
                  onChange={(e) => setFormState((prev) => ({ ...prev, is_union_member: e.target.value }))}
                >
                  <option value="true">Да</option>
                  <option value="false">Нет</option>
                </select>
              </label>
              <label>
                Присоединен к кол. договору
                <select
                  value={formState.is_contract_member}
                  onChange={(e) => setFormState((prev) => ({ ...prev, is_contract_member: e.target.value }))}
                >
                  <option value="true">Да</option>
                  <option value="false">Нет</option>
                </select>
              </label>
              <label>
                Участок
                <input
                  value={formState.department}
                  onChange={(e) => setFormState((prev) => ({ ...prev, department: e.target.value }))}
                  required
                />
              </label>
              <label>
                Должность
                <input
                  value={formState.position}
                  onChange={(e) => setFormState((prev) => ({ ...prev, position: e.target.value }))}
                  required
                />
              </label>
              <label>
                Телефон
                <input
                  value={formState.phone}
                  onChange={(e) => setFormState((prev) => ({ ...prev, phone: e.target.value }))}
                />
              </label>
              <label>
                Адрес
                <input
                  value={formState.address}
                  onChange={(e) => setFormState((prev) => ({ ...prev, address: e.target.value }))}
                />
              </label>
              <label>
                Удостоверение
                <input
                  value={formState.id_number}
                  onChange={(e) => setFormState((prev) => ({ ...prev, id_number: e.target.value }))}
                  required
                />
              </label>
              <label>
                Дата выдачи
                <input
                  type="date"
                  value={formState.id_issue_date}
                  onChange={(e) => setFormState((prev) => ({ ...prev, id_issue_date: e.target.value }))}
                />
              </label>
              <label>
                Кем выдано
                <input
                  value={formState.id_issued_by}
                  onChange={(e) => setFormState((prev) => ({ ...prev, id_issued_by: e.target.value }))}
                />
              </label>
              <label>
                Льготы
                <select
                  value={formState.has_benefits}
                  onChange={(e) => setFormState((prev) => ({ ...prev, has_benefits: e.target.value }))}
                >
                  <option value="true">Да</option>
                  <option value="false">Нет</option>
                </select>
              </label>
              <label>
                Название льготы
                <input
                  value={formState.benefits_name}
                  onChange={(e) => setFormState((prev) => ({ ...prev, benefits_name: e.target.value }))}
                />
              </label>
              <label>
                Шахтерская/трудовая слава
                <select
                  value={formState.has_miner_glory}
                  onChange={(e) => setFormState((prev) => ({ ...prev, has_miner_glory: e.target.value }))}
                >
                  <option value="true">Да</option>
                  <option value="false">Нет</option>
                </select>
              </label>
              <label>
                Карточный счет
                <input
                  value={formState.account_20_digit}
                  onChange={(e) =>
                    setFormState((prev) => ({
                      ...prev,
                      account_20_digit: normalizeKzAccountInput(e.target.value, true),
                    }))
                  }
                />
              </label>
              <label>
                Текущий счет
                <input
                  value={formState.current_account}
                  onChange={(e) =>
                    setFormState((prev) => ({
                      ...prev,
                      current_account: normalizeKzAccountInput(e.target.value, true),
                    }))
                  }
                />
              </label>
              <label>
                Помечен как умерший
                <select
                  value={formState.is_dead}
                  onChange={(e) => setFormState((prev) => ({ ...prev, is_dead: e.target.value }))}
                >
                  <option value="false">Нет</option>
                  <option value="true">Да</option>
                </select>
              </label>
              <label>
                Дата смерти
                <input
                  type="date"
                  value={formState.death_date}
                  onChange={(e) => setFormState((prev) => ({ ...prev, death_date: e.target.value }))}
                />
              </label>

              {user.is_admin && (
                <label>
                  Аккаунт владельца
                  <select
                    value={formState.user_id}
                    onChange={(e) => setFormState((prev) => ({ ...prev, user_id: e.target.value }))}
                  >
                    <option value="">Выберите аккаунт</option>
                    {(references?.users || []).map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.username}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              <label>
                Файл льгот
                <input
                  type="file"
                  onChange={(e) =>
                    setFormState((prev) => ({
                      ...prev,
                      files: { ...prev.files, benefits_file: e.target.files?.[0] || null },
                    }))
                  }
                />
              </label>
              <label>
                Файл славы
                <input
                  type="file"
                  onChange={(e) =>
                    setFormState((prev) => ({
                      ...prev,
                      files: { ...prev.files, miner_glory_file: e.target.files?.[0] || null },
                    }))
                  }
                />
              </label>
              <label>
                Паспорт дома
                <input
                  type="file"
                  onChange={(e) =>
                    setFormState((prev) => ({
                      ...prev,
                      files: { ...prev.files, house_passport_file: e.target.files?.[0] || null },
                    }))
                  }
                />
              </label>
              <label>
                Удостоверение пенсионера
                <input
                  type="file"
                  onChange={(e) =>
                    setFormState((prev) => ({
                      ...prev,
                      files: { ...prev.files, pensioner_id_file: e.target.files?.[0] || null },
                    }))
                  }
                />
              </label>
              <label>
                Справка о смерти
                <input
                  type="file"
                  onChange={(e) =>
                    setFormState((prev) => ({
                      ...prev,
                      files: { ...prev.files, death_certificate_file: e.target.files?.[0] || null },
                    }))
                  }
                />
              </label>

              <div className="family-block">
                <div className="family-head">
                  <h4>Члены семьи</h4>
                  <button type="button" className="btn btn-secondary" onClick={addFamilyMember}>
                    <Plus size={12} /> Добавить
                  </button>
                </div>
                {(formState.family_members || []).map((member, index) => (
                  <div className="family-row" key={`family-${index}`}>
                    <input
                      placeholder="ФИО"
                      value={member.full_name || ''}
                      onChange={(e) => updateFamilyMember(index, 'full_name', e.target.value)}
                    />
                    <select
                      value={member.relationship || 'other'}
                      onChange={(e) => updateFamilyMember(index, 'relationship', e.target.value)}
                    >
                      {(references?.relationship_choices || []).map((rel) => (
                        <option key={rel.value} value={rel.value}>
                          {rel.label}
                        </option>
                      ))}
                    </select>
                    <input
                      placeholder="Удостоверение"
                      value={member.id_number || ''}
                      onChange={(e) => updateFamilyMember(index, 'id_number', e.target.value)}
                    />
                    <input
                      type="date"
                      value={member.id_issue_date || ''}
                      onChange={(e) => updateFamilyMember(index, 'id_issue_date', e.target.value)}
                    />
                    <input
                      placeholder="Кем выдано"
                      value={member.id_issued_by || ''}
                      onChange={(e) => updateFamilyMember(index, 'id_issued_by', e.target.value)}
                    />
                    <input
                      type="date"
                      value={member.birth_date || ''}
                      onChange={(e) => updateFamilyMember(index, 'birth_date', e.target.value)}
                    />
                    <button type="button" className="btn btn-danger" onClick={() => removeFamilyMember(index)}>
                      <X size={12} />
                    </button>
                  </div>
                ))}
              </div>

              {editingId && (
                <section className="report-detail-section">
                  <div className="family-head">
                    <h4>Связанные отчеты</h4>
                    <span className="muted">Всего: {workerReports.length}</span>
                  </div>
                  {workerReports.length ? (
                    <div className="table-wrap">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Тип</th>
                            <th>Дата</th>
                            <th>Статус</th>
                            <th />
                          </tr>
                        </thead>
                        <tbody>
                          {workerReports.map((row) => (
                            <tr key={`${row.type}-${row.id}`}>
                              <td>{workerReportTypeLabel[row.type] || row.type}</td>
                              <td>{row.created_at || '—'}</td>
                              <td>
                                <span className={cn('badge', row.status === 'active' ? 'ok' : 'warn')}>
                                  {row.status_text || '—'}
                                </span>
                              </td>
                              <td className="actions-cell">
                                {row.download_url ? (
                                  <a className="btn btn-secondary" href={row.download_url} target="_blank" rel="noreferrer">
                                    <Download size={13} /> Скачать
                                  </a>
                                ) : (
                                  '—'
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="muted">По этому работнику отчеты пока не создавались.</p>
                  )}
                </section>
              )}

              {formError && <div className="error-banner">{formError}</div>}

              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={closeForm}>
                  Отмена
                </button>
                <button className="btn btn-primary" type="submit" disabled={saving}>
                  {saving ? (
                    <>
                      <Loader2 className="spin" size={14} /> Сохранение...
                    </>
                  ) : (
                    'Сохранить'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function WorkerLookup({ label, pensionerOnly = false, onSelect, selectedWorker }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debounced = useDebounce(query, 250);

  useEffect(() => {
    if (debounced.trim().length < 2) {
      setResults([]);
      return;
    }

    let mounted = true;
    const run = async () => {
      setLoading(true);
      try {
        const resp = await apiFetch(`/api/search-workers/?q=${encodeURIComponent(debounced)}`);
        let rows = resp.results || [];
        if (pensionerOnly) {
          rows = rows.filter((w) => isPensionerStatus(w.status));
        }
        if (mounted) {
          setResults(rows);
          setOpen(true);
        }
      } catch {
        if (mounted) {
          setResults([]);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    run();
    return () => {
      mounted = false;
    };
  }, [debounced, pensionerOnly]);

  return (
    <div className="lookup">
      <label>{label}</label>
      {selectedWorker ? (
        <div className="selected-worker">
          <div>
            <strong>{selectedWorker.full_name}</strong>
            <p>
              {selectedWorker.personnel_number || '—'} · {selectedWorker.department || '—'}
            </p>
          </div>
          <button className="btn btn-secondary" onClick={() => onSelect(null)}>
            Сброс
          </button>
        </div>
      ) : (
        <>
          <div className="search-field">
            <Search size={14} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Введите минимум 2 символа"
            />
            {loading && <Loader2 className="spin" size={14} />}
          </div>
          {open && results.length > 0 && (
            <div className="lookup-list">
              {results.map((worker) => (
                <button
                  key={worker.id}
                  className="lookup-item"
                  onClick={() => {
                    onSelect(worker);
                    setOpen(false);
                    setQuery('');
                  }}
                >
                  <strong>{worker.full_name}</strong>
                  <span>
                    {worker.personnel_number || '—'} · {worker.department || '—'}
                  </span>
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ApplicationsTab({ user }) {
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [limits, setLimits] = useState([]);
  const [limitForm, setLimitForm] = useState({ resort: 'zhartas', limit: '' });

  const [vacationWorker, setVacationWorker] = useState(null);
  const [vacationWorkerData, setVacationWorkerData] = useState(null);
  const [vacationData, setVacationData] = useState({
    resort: 'zhartas',
    start_date: '',
    end_date: '',
    worker_goes: true,
    family_members: [],
    seasons: [],
    custom_price: '',
    study_certificate_file: null,
  });

  const [materialWorker, setMaterialWorker] = useState(null);
  const [materialData, setMaterialData] = useState({
    assistance_type: 'sick_leave',
    amount: '',
    account_type: '20_digit',
    account_number: 'KZ',
    account_file: null,
  });

  const [coalWorker, setCoalWorker] = useState(null);
  const [coalData, setCoalData] = useState({
    account_type: '20_digit',
    account_number: 'KZ',
    account_file: null,
    passport_file: null,
    pensioner_id_file: null,
  });

  const [funeralWorker, setFuneralWorker] = useState(null);
  const [funeralData, setFuneralData] = useState({
    applicant_full_name: '',
    applicant_inn: '',
    account_type: '20_digit',
    account_number: 'KZ',
    account_file: null,
    death_date: '',
    applicant_id_file: null,
    death_certificate_file: null,
  });

  useEffect(() => {
    const loadFamily = async () => {
      if (!vacationWorker) {
        setVacationWorkerData(null);
        setVacationData((prev) => ({ ...prev, family_members: [] }));
        return;
      }
      try {
        const response = await apiFetch(`/api/worker/${vacationWorker.id}/family/`);
        setVacationWorkerData(response);
      } catch {
        setVacationWorkerData(null);
      }
    };
    loadFamily();
  }, [vacationWorker]);

  const loadLimits = async () => {
    if (user.is_admin) return;
    try {
      const response = await apiFetch('/api/v2/vacation-limits/');
      setLimits(response.limits || []);
    } catch (e) {
      showResult(getErrorText(e), true);
    }
  };

  useEffect(() => {
    loadLimits();
  }, [user.is_admin]);

  const showResult = (message, isError = false) => {
    if (isError) {
      setError(message);
      setSuccess('');
    } else {
      setSuccess(message);
      setError('');
    }
  };

  const submitVacation = async (event) => {
    event.preventDefault();
    if (!vacationWorker) {
      showResult('Выберите работника для заявления на путевку', true);
      return;
    }

    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('worker_id', vacationWorker.id);
      fd.append('resort', vacationData.resort);
      fd.append('start_date', vacationData.start_date);
      fd.append('end_date', vacationData.end_date);
      fd.append('worker_goes', vacationData.worker_goes ? 'true' : 'false');
      fd.append('family_members', JSON.stringify(vacationData.family_members));
      fd.append('seasons', JSON.stringify(vacationData.seasons));
      if (['zhartas', 'shakhter'].includes(vacationData.resort) && String(vacationData.custom_price || '').trim()) {
        fd.append('custom_price', String(vacationData.custom_price || '').trim());
      }
      if (vacationData.study_certificate_file) {
        fd.append('study_certificate_file', vacationData.study_certificate_file);
      }

      const response = await apiFetch('/api/v2/applications/vacation/create/', {
        method: 'POST',
        body: fd,
      });

      showResult('Заявление на путевку создано');
      triggerDownload(response.download_url);
    } catch (e) {
      showResult(getErrorText(e), true);
    } finally {
      setLoading(false);
    }
  };

  const submitMaterial = async (event) => {
    event.preventDefault();
    if (!materialWorker) {
      showResult('Выберите работника для материальной помощи', true);
      return;
    }

    setLoading(true);
    try {
      const accountNumber = normalizeKzAccountInput(materialData.account_number);
      const fd = new FormData();
      fd.append('worker_id', materialWorker.id);
      fd.append('assistance_type', materialData.assistance_type);
      fd.append('amount', materialData.amount);
      fd.append('account_type', materialData.account_type);
      fd.append('account_number', accountNumber);
      if (materialData.account_file) {
        fd.append('account_file', materialData.account_file);
      }

      const response = await apiFetch('/api/v2/applications/material/create/', {
        method: 'POST',
        body: fd,
      });

      showResult('Заявление на материальную помощь создано');
      triggerDownload(response.download_url);
    } catch (e) {
      showResult(getErrorText(e), true);
    } finally {
      setLoading(false);
    }
  };

  const submitCoal = async (event) => {
    event.preventDefault();
    if (!coalWorker) {
      showResult('Выберите пенсионера для заявления на уголь', true);
      return;
    }

    setLoading(true);
    try {
      const accountNumber = normalizeKzAccountInput(coalData.account_number);
      const fd = new FormData();
      fd.append('worker_id', coalWorker.id);
      fd.append('account_type', coalData.account_type);
      fd.append('account_number', accountNumber);
      if (coalData.account_file) {
        fd.append('account_file', coalData.account_file);
      }
      if (coalData.passport_file) {
        fd.append('passport_file', coalData.passport_file);
      }
      if (coalData.pensioner_id_file) {
        fd.append('pensioner_id_file', coalData.pensioner_id_file);
      }

      const response = await apiFetch('/api/v2/applications/coal/create/', {
        method: 'POST',
        body: fd,
      });
      showResult('Заявление на уголь создано');
      triggerDownload(response.download_url);
    } catch (e) {
      showResult(getErrorText(e), true);
    } finally {
      setLoading(false);
    }
  };

  const submitFuneral = async (event) => {
    event.preventDefault();
    if (!funeralWorker) {
      showResult('Выберите пенсионера для заявления на погребение', true);
      return;
    }

    setLoading(true);
    try {
      const accountNumber = normalizeKzAccountInput(funeralData.account_number);
      const fd = new FormData();
      fd.append('worker_id', funeralWorker.id);
      fd.append('applicant_full_name', funeralData.applicant_full_name);
      fd.append('applicant_inn', funeralData.applicant_inn);
      fd.append('account_type', funeralData.account_type);
      fd.append('account_number', accountNumber);
      fd.append('death_date', funeralData.death_date);
      if (funeralData.account_file) {
        fd.append('account_file', funeralData.account_file);
      }
      if (funeralData.applicant_id_file) {
        fd.append('applicant_id_file', funeralData.applicant_id_file);
      }
      if (funeralData.death_certificate_file) {
        fd.append('death_certificate_file', funeralData.death_certificate_file);
      }

      const response = await apiFetch('/api/v2/applications/funeral/create/', {
        method: 'POST',
        body: fd,
      });
      showResult('Заявление на погребение создано');
      triggerDownload(response.download_url);
    } catch (e) {
      showResult(getErrorText(e), true);
    } finally {
      setLoading(false);
    }
  };

  const submitLimit = async (event) => {
    event.preventDefault();
    if (user.is_admin) return;
    setLoading(true);
    try {
      await apiFetch('/api/v2/vacation-limits/', {
        method: 'POST',
        body: {
          resort: limitForm.resort,
          limit: limitForm.limit,
        },
      });
      showResult('Лимит сохранен');
      await loadLimits();
    } catch (e) {
      showResult(getErrorText(e), true);
    } finally {
      setLoading(false);
    }
  };

  const toggleFamily = (id) => {
    setVacationData((prev) => {
      const current = prev.family_members || [];
      return {
        ...prev,
        family_members: current.includes(id)
          ? current.filter((item) => item !== id)
          : [...current, id],
      };
    });
  };

  const toggleSeason = (season) => {
    setVacationData((prev) => {
      const current = prev.seasons || [];
      return {
        ...prev,
        seasons: current.includes(season) ? current.filter((s) => s !== season) : [...current, season],
      };
    });
  };

  return (
    <div className="stack">
      {(error || success) && (
        <div className={cn('notice', error ? 'notice-error' : 'notice-ok')}>
          {error || success}
        </div>
      )}

      {!user.is_admin && (
        <div className="card form-card">
          <h3>Лимиты на путевки</h3>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Курорт</th>
                  <th>Лимит</th>
                  <th>Использовано</th>
                  <th>Осталось</th>
                  <th>Период</th>
                </tr>
              </thead>
              <tbody>
                {limits.map((item) => (
                  <tr key={item.resort}>
                    <td>{item.resort_display}</td>
                    <td>{item.limit}</td>
                    <td>{item.used}</td>
                    <td>{item.remaining}</td>
                    <td>{item.period_start_human}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <form className="cols-2" onSubmit={submitLimit}>
            <label>
              Курорт
              <select
                value={limitForm.resort}
                onChange={(e) => setLimitForm((prev) => ({ ...prev, resort: e.target.value }))}
              >
                <option value="zhartas">Жартас</option>
                <option value="shakhter">Шахтер</option>
              </select>
            </label>
            <label>
              Новый лимит
              <input
                type="number"
                min="0"
                value={limitForm.limit}
                onChange={(e) => setLimitForm((prev) => ({ ...prev, limit: e.target.value }))}
                required
              />
            </label>
            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading ? <Loader2 className="spin" size={14} /> : <Check size={14} />} Обновить лимит
            </button>
          </form>
        </div>
      )}

      <div className="app-grid">
        <form className="card form-card" onSubmit={submitVacation}>
          <h3>Заявление на путевку</h3>
          <WorkerLookup label="Работник" onSelect={setVacationWorker} selectedWorker={vacationWorker} />

          <label>
            Курорт
            <select
              value={vacationData.resort}
              onChange={(e) => {
                const nextResort = e.target.value;
                setVacationData((prev) => ({
                  ...prev,
                  resort: nextResort,
                  seasons: nextResort === 'orlenok' ? prev.seasons : [],
                  custom_price: ['zhartas', 'shakhter'].includes(nextResort) ? prev.custom_price : '',
                  study_certificate_file: nextResort === 'discovery' ? prev.study_certificate_file : null,
                }));
              }}
            >
              {RESORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          {['zhartas', 'shakhter'].includes(vacationData.resort) && (
            <label>
              Ручная цена (опционально)
              <input
                type="number"
                step="0.01"
                min="0"
                value={vacationData.custom_price}
                onChange={(e) => setVacationData((prev) => ({ ...prev, custom_price: e.target.value }))}
                placeholder="Пусто = стандартный расчет"
              />
              <span className="field-hint">Если поле пустое, система посчитает стоимость автоматически.</span>
            </label>
          )}

          <div className="cols-2">
            <label>
              Дата начала
              <input
                type="date"
                value={vacationData.start_date}
                onChange={(e) => setVacationData((prev) => ({ ...prev, start_date: e.target.value }))}
                required
              />
            </label>
            <label>
              Дата окончания
              <input
                type="date"
                value={vacationData.end_date}
                onChange={(e) => setVacationData((prev) => ({ ...prev, end_date: e.target.value }))}
                required
              />
            </label>
          </div>

          <label className="checkbox-line">
            <input
              type="checkbox"
              checked={vacationData.worker_goes}
              onChange={(e) => setVacationData((prev) => ({ ...prev, worker_goes: e.target.checked }))}
            />
            <span>Работник едет</span>
          </label>

          {vacationData.resort === 'orlenok' && (
            <div className="chips-block">
              <span>Сезоны:</span>
              {[1, 2, 3, 4].map((season) => (
                <button
                  type="button"
                  key={season}
                  className={cn('chip', vacationData.seasons.includes(season) && 'chip-active')}
                  onClick={() => toggleSeason(season)}
                >
                  {season}
                </button>
              ))}
            </div>
          )}

          {vacationWorkerData?.family_members?.length > 0 && (
            <div className="family-select">
              <span>Члены семьи:</span>
              {vacationWorkerData.family_members.map((member) => (
                <label key={member.id} className="checkbox-line">
                  <input
                    type="checkbox"
                    checked={vacationData.family_members.includes(member.id)}
                    onChange={() => toggleFamily(member.id)}
                  />
                  <span>
                    {member.full_name} ({member.relationship})
                  </span>
                </label>
              ))}
            </div>
          )}

          {vacationData.resort === 'discovery' && (
            <label>
              Справка об очном обучении
              <input
                type="file"
                onChange={(e) =>
                  setVacationData((prev) => ({ ...prev, study_certificate_file: e.target.files?.[0] || null }))
                }
              />
            </label>
          )}

          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? <Loader2 className="spin" size={14} /> : <Check size={14} />} Создать
          </button>
        </form>

        <form className="card form-card" onSubmit={submitMaterial}>
          <h3>Материальная помощь</h3>
          <WorkerLookup label="Работник" onSelect={setMaterialWorker} selectedWorker={materialWorker} />

          <label>
            Вид помощи
            <select
              value={materialData.assistance_type}
              onChange={(e) => setMaterialData((prev) => ({ ...prev, assistance_type: e.target.value }))}
            >
              {ASSISTANCE_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Тип счета
            <select
              value={materialData.account_type}
              onChange={(e) => setMaterialData((prev) => ({ ...prev, account_type: e.target.value }))}
            >
              {ACCOUNT_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Номер счета
            <input
              value={materialData.account_number}
              onChange={(e) =>
                setMaterialData((prev) => ({ ...prev, account_number: normalizeKzAccountInput(e.target.value) }))
              }
              placeholder="KZ..."
              maxLength={20}
              required
            />
          </label>

          <label>
            Прикрепить счет
            <input
              type="file"
              onChange={(e) => setMaterialData((prev) => ({ ...prev, account_file: e.target.files?.[0] || null }))}
            />
          </label>

          <label>
            Сумма
            <input
              type="number"
              step="0.01"
              value={materialData.amount}
              onChange={(e) => setMaterialData((prev) => ({ ...prev, amount: e.target.value }))}
            />
          </label>

          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? <Loader2 className="spin" size={14} /> : <Check size={14} />} Создать
          </button>
        </form>

        <form className="card form-card" onSubmit={submitCoal}>
          <h3>Заявление на уголь</h3>
          <WorkerLookup
            label="Пенсионер"
            pensionerOnly
            onSelect={setCoalWorker}
            selectedWorker={coalWorker}
          />

          <label>
            Тип счета
            <select
              value={coalData.account_type}
              onChange={(e) => setCoalData((prev) => ({ ...prev, account_type: e.target.value }))}
            >
              {ACCOUNT_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Номер счета
            <input
              value={coalData.account_number}
              onChange={(e) =>
                setCoalData((prev) => ({ ...prev, account_number: normalizeKzAccountInput(e.target.value) }))
              }
              placeholder="KZ..."
              maxLength={20}
              required
            />
          </label>

          <label>
            Прикрепить счет
            <input
              type="file"
              onChange={(e) => setCoalData((prev) => ({ ...prev, account_file: e.target.files?.[0] || null }))}
            />
          </label>

          <label>
            Техпаспорт дома
            <input
              type="file"
              onChange={(e) => setCoalData((prev) => ({ ...prev, passport_file: e.target.files?.[0] || null }))}
            />
          </label>

          <label>
            Удостоверение пенсионера
            <input
              type="file"
              onChange={(e) =>
                setCoalData((prev) => ({ ...prev, pensioner_id_file: e.target.files?.[0] || null }))
              }
            />
          </label>

          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? <Loader2 className="spin" size={14} /> : <Check size={14} />} Создать
          </button>
        </form>

        <form className="card form-card" onSubmit={submitFuneral}>
          <h3>Заявление на погребение</h3>
          <WorkerLookup
            label="Пенсионер"
            pensionerOnly
            onSelect={setFuneralWorker}
            selectedWorker={funeralWorker}
          />

          <label>
            ФИО заявителя
            <input
              value={funeralData.applicant_full_name}
              onChange={(e) => setFuneralData((prev) => ({ ...prev, applicant_full_name: e.target.value }))}
              required
            />
          </label>

          <label>
            ИИН заявителя
            <input
              value={funeralData.applicant_inn}
              onChange={(e) => setFuneralData((prev) => ({ ...prev, applicant_inn: e.target.value }))}
              required
            />
          </label>

          <label>
            Тип счета
            <select
              value={funeralData.account_type}
              onChange={(e) => setFuneralData((prev) => ({ ...prev, account_type: e.target.value }))}
            >
              {ACCOUNT_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Номер счета
            <input
              value={funeralData.account_number}
              onChange={(e) =>
                setFuneralData((prev) => ({ ...prev, account_number: normalizeKzAccountInput(e.target.value) }))
              }
              placeholder="KZ..."
              maxLength={20}
              required
            />
          </label>

          <label>
            Прикрепить счет
            <input
              type="file"
              onChange={(e) => setFuneralData((prev) => ({ ...prev, account_file: e.target.files?.[0] || null }))}
            />
          </label>

          <label>
            Дата смерти пенсионера
            <input
              type="date"
              value={funeralData.death_date}
              onChange={(e) => setFuneralData((prev) => ({ ...prev, death_date: e.target.value }))}
            />
          </label>

          <label>
            Удостоверение заявителя
            <input
              type="file"
              onChange={(e) =>
                setFuneralData((prev) => ({ ...prev, applicant_id_file: e.target.files?.[0] || null }))
              }
            />
          </label>

          <label>
            Справка о смерти
            <input
              type="file"
              onChange={(e) =>
                setFuneralData((prev) => ({ ...prev, death_certificate_file: e.target.files?.[0] || null }))
              }
            />
          </label>

          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? <Loader2 className="spin" size={14} /> : <Check size={14} />} Создать
          </button>
        </form>
      </div>
    </div>
  );
}

function ReportsTab({ user, references }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [enterpriseFilter, setEnterpriseFilter] = useState('all');
  const [enterpriseSort, setEnterpriseSort] = useState('default');
  const [workerStatusSort, setWorkerStatusSort] = useState('default');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [detailData, setDetailData] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editLoading, setEditLoading] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState('');
  const [editData, setEditData] = useState(null);
  const [workerFamilyOptions, setWorkerFamilyOptions] = useState([]);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      if (user.is_admin && enterpriseFilter !== 'all') {
        params.set('user_id', enterpriseFilter);
      }
      const query = params.toString() ? `?${params.toString()}` : '';
      const response = await apiFetch(`/api/v2/reports/${query}`);
      setRows(response.results || []);
    } catch (e) {
      setError(getErrorText(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [enterpriseFilter]);

  const workerStatusOrder = useMemo(() => {
    const map = {};
    (references?.worker_status_choices || []).forEach((item, index) => {
      map[item.value] = index;
    });
    return map;
  }, [references]);

  const filteredRows = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = rows.filter((row) => {
      const typeOk = typeFilter === 'all' || row.type === typeFilter;
      const searchOk =
        !q ||
        (row.worker_name || '').toLowerCase().includes(q) ||
        (row.worker_status_display || '').toLowerCase().includes(q) ||
        (row.owner || '').toLowerCase().includes(q) ||
        (row.status_text || '').toLowerCase().includes(q);
      return typeOk && searchOk;
    });

    if (workerStatusSort !== 'default' || (user.is_admin && enterpriseSort !== 'default')) {
      filtered.sort((a, b) => {
        if (workerStatusSort !== 'default') {
          const direction = workerStatusSort === 'desc' ? -1 : 1;
          const orderA = workerStatusOrder[a.worker_status] ?? Number.MAX_SAFE_INTEGER;
          const orderB = workerStatusOrder[b.worker_status] ?? Number.MAX_SAFE_INTEGER;
          const orderCompare = orderA - orderB;
          if (orderCompare !== 0) {
            return orderCompare * direction;
          }
          const statusA = String(a.worker_status_display || '').toLowerCase();
          const statusB = String(b.worker_status_display || '').toLowerCase();
          const statusCompare = statusA.localeCompare(statusB, 'ru');
          if (statusCompare !== 0) {
            return statusCompare * direction;
          }
        }

        if (user.is_admin && enterpriseSort !== 'default') {
          const enterpriseDirection = enterpriseSort === 'owner_desc' ? -1 : 1;
          const ownerA = String(a.owner || '').toLowerCase();
          const ownerB = String(b.owner || '').toLowerCase();
          const ownerCompare = ownerA.localeCompare(ownerB, 'ru');
          if (ownerCompare !== 0) {
            return ownerCompare * enterpriseDirection;
          }
        }
        return String(b.created_at_iso || '').localeCompare(String(a.created_at_iso || ''));
      });
    }

    return filtered;
  }, [rows, search, typeFilter, workerStatusSort, enterpriseSort, workerStatusOrder, user.is_admin]);

  useEffect(() => {
    setPage(1);
  }, [search, typeFilter, workerStatusSort, enterpriseSort, pageSize, rows.length]);

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const pagedRows = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return filteredRows.slice(startIndex, startIndex + pageSize);
  }, [filteredRows, currentPage, pageSize]);

  const loadDetail = async (row) => {
    setDetailModalOpen(true);
    setDetailData(null);
    setDetailLoading(true);
    try {
      const data = await apiFetch(row.detail_url);
      setDetailData({ ...data, _type: row.type, _id: row.id, _source: row });
    } catch (e) {
      setError(getErrorText(e));
    } finally {
      setDetailLoading(false);
    }
  };

  const rejectReport = async (row) => {
    if (!user.is_admin) return;
    if (!window.confirm('Перевести заявление в статус "Неактивно/Отклонено"?')) return;

    const map = {
      vacation: `/api/vacation-request/${row.id}/reject/`,
      material: `/api/material-assistance/${row.id}/reject/`,
      coal: `/api/coal-request/${row.id}/reject/`,
      funeral: `/api/funeral-request/${row.id}/reject/`,
    };

    const endpoint = map[row.type];
    if (!endpoint) return;

    try {
      await apiFetch(endpoint, { method: 'POST' });
      await load();
      if (detailData && detailData._id === row.id && detailData._type === row.type) {
        setDetailData(null);
        setDetailModalOpen(false);
      }
    } catch (e) {
      setError(getErrorText(e));
    }
  };

  const deleteReport = async (row) => {
    const endpointMap = {
      vacation: `/api/vacation-request/${row.id}/delete/`,
      material: `/api/material-assistance/${row.id}/delete/`,
      coal: `/api/coal-request/${row.id}/delete/`,
      funeral: `/api/funeral-request/${row.id}/delete/`,
    };

    const endpoint = endpointMap[row.type];
    if (!endpoint) return;

    if (!window.confirm('Удалить заявление?')) return;

    try {
      await apiFetch(endpoint, { method: 'POST' });
      await load();
      if (detailData && detailData._id === row.id && detailData._type === row.type) {
        setDetailData(null);
        setDetailModalOpen(false);
      }
    } catch (e) {
      setError(getErrorText(e));
    }
  };

  const closeEditModal = () => {
    setEditModalOpen(false);
    setEditLoading(false);
    setEditSaving(false);
    setEditData(null);
    setEditError('');
    setWorkerFamilyOptions([]);
  };

  const openEdit = async (row) => {
    setDetailModalOpen(false);
    setEditModalOpen(true);
    setEditLoading(true);
    setEditSaving(false);
    setEditError('');
    setEditData(null);
    setWorkerFamilyOptions([]);

    try {
      const detail = await apiFetch(row.detail_url);
      const prepared = {
        type: row.type,
        id: row.id,
        row,
        workerName: detail.worker?.full_name || row.worker_name || '',
        workerId: detail.worker?.id || null,
        form: {},
      };

      if (row.type === 'vacation') {
        prepared.form = {
          resort: detail.vacation_details?.resort_code || 'zhartas',
          start_date: detail.vacation_details?.start_date_iso || '',
          end_date: detail.vacation_details?.end_date_iso || '',
          worker_goes: detail.vacation_details?.worker_goes !== false,
          family_members: Array.isArray(detail.selected_family_ids) ? detail.selected_family_ids : [],
          seasons: Array.isArray(detail.vacation_details?.seasons) ? detail.vacation_details.seasons : [],
          custom_price: detail.vacation_details?.price_is_custom ? String(detail.vacation_details?.price || '') : '',
        };

        if (prepared.workerId) {
          try {
            const familyResp = await apiFetch(`/api/worker/${prepared.workerId}/family/`);
            setWorkerFamilyOptions(familyResp.family_members || []);
          } catch {
            setWorkerFamilyOptions([]);
          }
        }
      }

      if (row.type === 'material') {
        prepared.form = {
          assistance_type: detail.assistance_details?.assistance_type_code || 'sick_leave',
          amount: detail.assistance_details?.amount !== undefined ? String(detail.assistance_details.amount ?? '') : '',
          account_type: detail.assistance_details?.account_type_code || '20_digit',
          account_number: normalizeKzAccountInput(detail.assistance_details?.account_number || ''),
        };
      }

      if (row.type === 'coal') {
        prepared.form = {
          account_type: detail.coal_details?.account_type_code || '20_digit',
          account_number: normalizeKzAccountInput(detail.coal_details?.account_number || ''),
        };
      }

      if (row.type === 'funeral') {
        prepared.form = {
          applicant_full_name: detail.funeral_details?.applicant_full_name || '',
          applicant_inn: detail.funeral_details?.applicant_inn || '',
          account_type: detail.funeral_details?.account_type_code || '20_digit',
          account_number: normalizeKzAccountInput(detail.funeral_details?.account_number || ''),
          death_date: detail.funeral_details?.death_date_iso || '',
        };
      }

      setEditData(prepared);
    } catch (e) {
      setEditError(getErrorText(e));
    } finally {
      setEditLoading(false);
    }
  };

  const updateEditField = (field, value) => {
    setEditData((prev) => {
      if (!prev) return prev;
      return { ...prev, form: { ...prev.form, [field]: value } };
    });
  };

  const toggleEditFamily = (id) => {
    setEditData((prev) => {
      if (!prev) return prev;
      const current = prev.form.family_members || [];
      const next = current.includes(id) ? current.filter((item) => item !== id) : [...current, id];
      return { ...prev, form: { ...prev.form, family_members: next } };
    });
  };

  const toggleEditSeason = (season) => {
    setEditData((prev) => {
      if (!prev) return prev;
      const current = prev.form.seasons || [];
      const next = current.includes(season) ? current.filter((item) => item !== season) : [...current, season];
      return { ...prev, form: { ...prev.form, seasons: next } };
    });
  };

  const submitEdit = async (event) => {
    event.preventDefault();
    if (!editData) return;

    const endpointMap = {
      vacation: `/api/vacation-request/${editData.id}/edit/`,
      material: `/api/material-assistance/${editData.id}/edit/`,
      coal: `/api/coal-request/${editData.id}/edit/`,
      funeral: `/api/funeral-request/${editData.id}/edit/`,
    };
    const endpoint = endpointMap[editData.type];
    if (!endpoint) return;

    let payload = {};
    if (editData.type === 'vacation') {
      payload = {
        resort: editData.form.resort,
        start_date: editData.form.start_date,
        end_date: editData.form.end_date,
        worker_goes: !!editData.form.worker_goes,
        family_members: editData.form.family_members || [],
        seasons: editData.form.resort === 'orlenok' ? editData.form.seasons || [] : [],
      };
      if (['zhartas', 'shakhter'].includes(editData.form.resort) && String(editData.form.custom_price || '').trim()) {
        payload.custom_price = String(editData.form.custom_price).trim();
      }
    }
    if (editData.type === 'material') {
      payload = {
        assistance_type: editData.form.assistance_type,
        amount: editData.form.amount,
        account_type: editData.form.account_type,
        account_number: normalizeKzAccountInput(editData.form.account_number),
      };
    }
    if (editData.type === 'coal') {
      payload = {
        account_type: editData.form.account_type,
        account_number: normalizeKzAccountInput(editData.form.account_number),
      };
    }
    if (editData.type === 'funeral') {
      payload = {
        applicant_full_name: editData.form.applicant_full_name,
        applicant_inn: editData.form.applicant_inn,
        account_type: editData.form.account_type,
        account_number: normalizeKzAccountInput(editData.form.account_number),
        death_date: editData.form.death_date,
      };
    }

    setEditSaving(true);
    setEditError('');
    try {
      await apiFetch(endpoint, { method: 'POST', body: payload });
      closeEditModal();
      await load();
      if (detailData && detailData._id === editData.id && detailData._type === editData.type) {
        setDetailData(null);
        setDetailModalOpen(false);
      }
    } catch (e) {
      setEditError(getErrorText(e));
    } finally {
      setEditSaving(false);
    }
  };

  const typeLabel = {
    vacation: 'Путевка',
    material: 'Матпомощь',
    coal: 'Уголь',
    funeral: 'Погребение',
  };

  const asText = (value) => {
    if (value === null || value === undefined || value === '') return '—';
    if (Array.isArray(value)) return value.length ? value.join(', ') : '—';
    if (typeof value === 'boolean') return value ? 'Да' : 'Нет';
    return String(value);
  };

  const canEditRow = (row) => row.status !== 'inactive';

  const renderDetailGrid = (items) => (
    <div className="report-detail-grid">
      {items.map((item) => (
        <div className="report-detail-item" key={item.label}>
          <span className="report-detail-label">{item.label}</span>
          {item.href ? (
            <a className="report-detail-link" href={item.href} target="_blank" rel="noreferrer">
              {asText(item.value)}
            </a>
          ) : (
            <span className="report-detail-value">{item.money ? formatMoney(item.value) : asText(item.value)}</span>
          )}
        </div>
      ))}
    </div>
  );

  return (
    <div className="stack">
      <div className="card">
        <div className="toolbar">
          <div className="search-field">
            <Search size={14} />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Поиск..." />
          </div>
          <div className="right-actions">
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
              <option value="all">Все типы</option>
              <option value="vacation">Путевка</option>
              <option value="material">Матпомощь</option>
              <option value="coal">Уголь</option>
              <option value="funeral">Погребение</option>
            </select>
            {user.is_admin && (
              <select value={enterpriseFilter} onChange={(e) => setEnterpriseFilter(e.target.value)}>
                <option value="all">Все предприятия</option>
                {(references?.users || []).map((item) => (
                  <option key={item.id} value={String(item.id)}>
                    {item.username}
                  </option>
                ))}
              </select>
            )}
            {user.is_admin && (
              <select value={enterpriseSort} onChange={(e) => setEnterpriseSort(e.target.value)}>
                <option value="default">Сортировка: по дате</option>
                <option value="owner_asc">Предприятие: А-Я</option>
                <option value="owner_desc">Предприятие: Я-А</option>
              </select>
            )}
            <select value={workerStatusSort} onChange={(e) => setWorkerStatusSort(e.target.value)}>
              <option value="default">Статус работника: по умолчанию</option>
              <option value="asc">Статус работника: по возрастанию</option>
              <option value="desc">Статус работника: по убыванию</option>
            </select>
            <select value={String(pageSize)} onChange={(e) => setPageSize(Number(e.target.value))}>
              <option value="10">10 на странице</option>
              <option value="20">20 на странице</option>
              <option value="50">50 на странице</option>
            </select>
          </div>
        </div>

        {error && <div className="error-banner">{error}</div>}

        {loading ? (
          <div className="center">
            <Loader2 className="spin" size={20} />
          </div>
        ) : (
          <>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Тип</th>
                    {user.is_admin && <th>Предприятие</th>}
                    <th>Работник</th>
                    <th>Статус работника</th>
                    <th>Статус</th>
                    <th>Дата</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {pagedRows.map((row) => (
                    <tr key={`${row.type}-${row.id}`}>
                      <td>{typeLabel[row.type] || row.type}</td>
                      {user.is_admin && <td>{row.owner || '—'}</td>}
                      <td>{row.worker_name}</td>
                      <td>
                        <span className={cn('badge', isPensionerStatus(row.worker_status) ? 'warn' : 'ok')}>
                          {row.worker_status_display || '—'}
                        </span>
                      </td>
                      <td>
                        <span className={cn('badge', row.status === 'active' ? 'ok' : row.status === 'pending' ? 'warn' : '')}>
                          {row.status_text}
                        </span>
                      </td>
                      <td>{row.created_at}</td>
                      <td className="actions-cell">
                        <button className="btn btn-secondary" onClick={() => loadDetail(row)} title="Детали">
                          <Eye size={13} />
                        </button>
                        <a className="btn btn-secondary" href={row.download_url} target="_blank" rel="noreferrer" title="Скачать">
                          <Download size={13} />
                        </a>
                        <button
                          className="btn btn-secondary"
                          onClick={() => openEdit(row)}
                          disabled={!canEditRow(row)}
                          title={canEditRow(row) ? 'Редактировать' : 'Редактирование недоступно'}
                        >
                          Изм.
                        </button>
                        {user.is_admin && (
                          <button className="btn btn-danger" onClick={() => rejectReport(row)}>
                            Отказать
                          </button>
                        )}
                        <button className="btn btn-danger" onClick={() => deleteReport(row)}>
                          Удалить
                        </button>
                      </td>
                    </tr>
                  ))}
                  {filteredRows.length === 0 && (
                    <tr>
                      <td colSpan={user.is_admin ? 7 : 6} className="empty-row">
                        Нет данных
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {filteredRows.length > 0 && (
              <div className="pager">
                <button className="btn btn-secondary" disabled={currentPage <= 1} onClick={() => setPage(currentPage - 1)}>
                  Назад
                </button>
                <span>
                  Страница {currentPage} из {totalPages}
                </span>
                <button
                  className="btn btn-secondary"
                  disabled={currentPage >= totalPages}
                  onClick={() => setPage(currentPage + 1)}
                >
                  Вперед
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {detailModalOpen && (
        <div className="modal-overlay" onClick={() => setDetailModalOpen(false)}>
          <div className="modal modal-detail" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3>Детали заявления</h3>
              <button className="icon-btn" onClick={() => setDetailModalOpen(false)}>
                <X size={16} />
              </button>
            </div>

            {detailLoading ? (
              <div className="center">
                <Loader2 className="spin" size={20} />
              </div>
            ) : detailData ? (
              <>
                <div className="detail-meta">
                  <span>Тип: {asText(typeLabel[detailData._type] || detailData.type)}</span>
                  <span>ID: {detailData.id}</span>
                  <span>Создано: {detailData.created_at}</span>
                  <span>
                    Статус:{' '}
                    {asText(
                      detailData.vacation_details?.status_text ||
                        detailData.assistance_details?.status_text ||
                        detailData.coal_details?.status_text ||
                        detailData.funeral_details?.status_text ||
                        detailData._source?.status_text
                    )}
                  </span>
                  <span>Аккаунт: {asText(detailData._source?.owner)}</span>
                </div>
                <div className="report-detail-stack">
                  <section className="report-detail-section">
                    <h4>Работник</h4>
                    {renderDetailGrid([
                      { label: 'ФИО', value: detailData.worker?.full_name },
                      { label: 'Табельный номер', value: detailData.worker?.personnel_number },
                      { label: 'ИИН', value: detailData.worker?.inn },
                      { label: 'Статус', value: detailData.worker?.status },
                      { label: 'Подразделение', value: detailData.worker?.department },
                      { label: 'Должность', value: detailData.worker?.position },
                      { label: 'Телефон', value: detailData.worker?.phone },
                      { label: 'Адрес', value: detailData.worker?.address },
                      { label: 'Умерший', value: detailData.worker?.is_dead },
                      { label: 'Дата смерти', value: detailData.worker?.death_date },
                    ])}
                  </section>

                  {detailData.vacation_details && (
                    <section className="report-detail-section">
                      <h4>Данные путевки</h4>
                      {renderDetailGrid([
                        { label: 'Курорт', value: detailData.vacation_details.resort },
                        { label: 'Дата начала', value: detailData.vacation_details.start_date },
                        { label: 'Дата окончания', value: detailData.vacation_details.end_date },
                        { label: 'Длительность (дней)', value: detailData.vacation_details.duration_days },
                        { label: 'Количество человек', value: detailData.vacation_details.people_count },
                        { label: 'Работник едет', value: detailData.vacation_details.worker_goes },
                        { label: 'Сезоны Орленок', value: detailData.vacation_details.seasons },
                        { label: 'Цена за день', value: detailData.vacation_details.price_per_day, money: true },
                        { label: 'Ручная цена', value: detailData.vacation_details.price_is_custom ? 'Да' : 'Нет' },
                        { label: 'Итоговая сумма', value: detailData.vacation_details.price, money: true },
                        {
                          label: 'Справка об очном обучении',
                          value: detailData.study_certificate_file_name || 'Файл отсутствует',
                          href: detailData.study_certificate_file || undefined,
                        },
                      ])}
                    </section>
                  )}

                  {detailData.assistance_details && (
                    <section className="report-detail-section">
                      <h4>Данные материальной помощи</h4>
                      {renderDetailGrid([
                        { label: 'Вид помощи', value: detailData.assistance_details.assistance_type },
                        { label: 'Сумма', value: detailData.assistance_details.amount, money: true },
                        { label: 'Тип счета', value: detailData.assistance_details.account_type },
                        { label: 'Номер счета', value: detailData.assistance_details.account_number },
                        {
                          label: 'Прикрепленный счет',
                          value: detailData.assistance_details.account_file_name || 'Файл отсутствует',
                          href: detailData.assistance_details.account_file_url || undefined,
                        },
                        { label: 'Статус', value: detailData.assistance_details.status_text },
                      ])}
                    </section>
                  )}

                  {detailData.coal_details && (
                    <section className="report-detail-section">
                      <h4>Данные заявления на уголь</h4>
                      {renderDetailGrid([
                        { label: 'Тип счета', value: detailData.coal_details.account_type },
                        { label: 'Счет', value: detailData.coal_details.account_number },
                        {
                          label: 'Прикрепленный счет',
                          value: detailData.coal_details.account_file_name || 'Файл отсутствует',
                          href: detailData.coal_details.account_file_url || undefined,
                        },
                        { label: 'Статус', value: detailData.coal_details.status_text },
                        {
                          label: 'Техпаспорт дома',
                          value: detailData.coal_details.passport_file_name || 'Файл отсутствует',
                          href: detailData.coal_details.passport_file_url || undefined,
                        },
                        {
                          label: 'Удостоверение пенсионера',
                          value: detailData.coal_details.pensioner_id_file_name || 'Файл отсутствует',
                          href: detailData.coal_details.pensioner_id_file_url || undefined,
                        },
                      ])}
                    </section>
                  )}

                  {detailData.funeral_details && (
                    <section className="report-detail-section">
                      <h4>Данные заявления на погребение</h4>
                      {renderDetailGrid([
                        { label: 'ФИО заявителя', value: detailData.funeral_details.applicant_full_name },
                        { label: 'ИИН заявителя', value: detailData.funeral_details.applicant_inn },
                        { label: 'Тип счета', value: detailData.funeral_details.account_type },
                        { label: 'Счет', value: detailData.funeral_details.account_number },
                        {
                          label: 'Прикрепленный счет',
                          value: detailData.funeral_details.account_file_name || 'Файл отсутствует',
                          href: detailData.funeral_details.account_file_url || undefined,
                        },
                        { label: 'Дата смерти пенсионера', value: detailData.funeral_details.death_date },
                        { label: 'Статус', value: detailData.funeral_details.status_text },
                        {
                          label: 'Удостоверение личности заявителя',
                          value: detailData.funeral_details.applicant_id_file_name || 'Файл отсутствует',
                          href: detailData.funeral_details.applicant_id_file_url || undefined,
                        },
                        {
                          label: 'Справка о смерти',
                          value: detailData.funeral_details.death_certificate_file_name || 'Файл отсутствует',
                          href: detailData.funeral_details.death_certificate_file_url || undefined,
                        },
                      ])}
                    </section>
                  )}

                  {detailData.family_members && (
                    <section className="report-detail-section">
                      <h4>Члены семьи</h4>
                      {detailData.family_members.length ? (
                        <div className="table-wrap">
                          <table className="data-table report-family-table">
                            <thead>
                              <tr>
                                <th>ФИО</th>
                                <th>Родство</th>
                                <th>Номер документа</th>
                                <th>Дата выдачи</th>
                                <th>Кем выдан</th>
                              </tr>
                            </thead>
                            <tbody>
                              {detailData.family_members.map((member) => (
                                <tr key={member.id}>
                                  <td>{asText(member.full_name)}</td>
                                  <td>{asText(member.relationship)}</td>
                                  <td>{asText(member.id_number)}</td>
                                  <td>{asText(member.id_issue_date)}</td>
                                  <td>{asText(member.id_issued_by)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <p className="muted">Члены семьи не указаны</p>
                      )}
                    </section>
                  )}
                </div>
                <div className="modal-actions">
                  {detailData?._source?.download_url && (
                    <a className="btn btn-secondary" href={detailData._source.download_url} target="_blank" rel="noreferrer">
                      <Download size={14} /> Скачать
                    </a>
                  )}
                  <button
                    className="btn btn-secondary"
                    onClick={() => openEdit(detailData._source)}
                    disabled={!canEditRow(detailData._source)}
                  >
                    Редактировать
                  </button>
                  {user.is_admin && (
                    <button className="btn btn-danger" onClick={() => rejectReport(detailData._source)}>
                      Отказать
                    </button>
                  )}
                  <button className="btn btn-danger" onClick={() => deleteReport(detailData._source)}>
                    Удалить
                  </button>
                </div>
              </>
            ) : (
              <p className="muted">Нет данных</p>
            )}
          </div>
        </div>
      )}

      {editModalOpen && (
        <div className="modal-overlay" onClick={closeEditModal}>
          <div className="modal modal-detail" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3>Редактирование заявления</h3>
              <button className="icon-btn" onClick={closeEditModal}>
                <X size={16} />
              </button>
            </div>

            {editLoading ? (
              <div className="center">
                <Loader2 className="spin" size={20} />
              </div>
            ) : editData ? (
              <form className="form-grid report-edit-form" onSubmit={submitEdit}>
                <div className="detail-meta">
                  <span>Тип: {typeLabel[editData.type] || editData.type}</span>
                  <span>ID: {editData.id}</span>
                  <span>Работник: {editData.workerName || '—'}</span>
                </div>

                {editData.type === 'vacation' && (
                  <>
                    <label>
                      Курорт
                      <select
                        value={editData.form.resort}
                        onChange={(e) => {
                          const nextResort = e.target.value;
                          setEditData((prev) => {
                            if (!prev) return prev;
                            return {
                              ...prev,
                              form: {
                                ...prev.form,
                                resort: nextResort,
                                seasons: nextResort === 'orlenok' ? prev.form.seasons : [],
                                custom_price: ['zhartas', 'shakhter'].includes(nextResort) ? prev.form.custom_price : '',
                              },
                            };
                          });
                        }}
                      >
                        {RESORT_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <div className="cols-2">
                      <label>
                        Дата начала
                        <input
                          type="date"
                          value={editData.form.start_date}
                          onChange={(e) => updateEditField('start_date', e.target.value)}
                          required
                        />
                      </label>
                      <label>
                        Дата окончания
                        <input
                          type="date"
                          value={editData.form.end_date}
                          onChange={(e) => updateEditField('end_date', e.target.value)}
                          required
                        />
                      </label>
                    </div>

                    <label className="checkbox-line">
                      <input
                        type="checkbox"
                        checked={!!editData.form.worker_goes}
                        onChange={(e) => updateEditField('worker_goes', e.target.checked)}
                      />
                      <span>Работник едет</span>
                    </label>

                    {editData.form.resort === 'orlenok' && (
                      <div className="chips-block">
                        <span>Сезоны:</span>
                        {[1, 2, 3, 4].map((season) => (
                          <button
                            type="button"
                            key={season}
                            className={cn('chip', (editData.form.seasons || []).includes(season) && 'chip-active')}
                            onClick={() => toggleEditSeason(season)}
                          >
                            {season}
                          </button>
                        ))}
                      </div>
                    )}

                    {['zhartas', 'shakhter'].includes(editData.form.resort) && (
                      <label>
                        Ручная цена (опционально)
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={editData.form.custom_price || ''}
                          onChange={(e) => updateEditField('custom_price', e.target.value)}
                          placeholder="Пусто = стандартный расчет"
                        />
                        <span className="field-hint">Если поле пустое, система посчитает стоимость автоматически.</span>
                      </label>
                    )}

                    <div className="family-select">
                      <span>Члены семьи:</span>
                      {workerFamilyOptions.length > 0 ? (
                        workerFamilyOptions.map((member) => (
                          <label key={member.id} className="checkbox-line">
                            <input
                              type="checkbox"
                              checked={(editData.form.family_members || []).includes(member.id)}
                              onChange={() => toggleEditFamily(member.id)}
                            />
                            <span>
                              {member.full_name} ({member.relationship})
                            </span>
                          </label>
                        ))
                      ) : (
                        <p className="muted">Нет доступных членов семьи</p>
                      )}
                    </div>
                  </>
                )}

                {editData.type === 'material' && (
                  <>
                    <label>
                      Вид помощи
                      <select
                        value={editData.form.assistance_type}
                        onChange={(e) => updateEditField('assistance_type', e.target.value)}
                      >
                        {ASSISTANCE_TYPE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Сумма
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={editData.form.amount}
                        onChange={(e) => updateEditField('amount', e.target.value)}
                      />
                    </label>
                    <label>
                      Тип счета
                      <select
                        value={editData.form.account_type}
                        onChange={(e) => updateEditField('account_type', e.target.value)}
                      >
                        {ACCOUNT_TYPE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Номер счета
                      <input
                        value={editData.form.account_number}
                        onChange={(e) => updateEditField('account_number', normalizeKzAccountInput(e.target.value))}
                        maxLength={20}
                        required
                      />
                    </label>
                  </>
                )}

                {editData.type === 'coal' && (
                  <>
                    <label>
                      Тип счета
                      <select
                        value={editData.form.account_type}
                        onChange={(e) => updateEditField('account_type', e.target.value)}
                      >
                        {ACCOUNT_TYPE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Номер счета
                      <input
                        value={editData.form.account_number}
                        onChange={(e) => updateEditField('account_number', normalizeKzAccountInput(e.target.value))}
                        maxLength={20}
                        required
                      />
                    </label>
                  </>
                )}

                {editData.type === 'funeral' && (
                  <>
                    <label>
                      ФИО заявителя
                      <input
                        value={editData.form.applicant_full_name}
                        onChange={(e) => updateEditField('applicant_full_name', e.target.value)}
                        required
                      />
                    </label>
                    <label>
                      ИИН заявителя
                      <input
                        value={editData.form.applicant_inn}
                        onChange={(e) => updateEditField('applicant_inn', e.target.value)}
                        required
                      />
                    </label>
                    <label>
                      Тип счета
                      <select
                        value={editData.form.account_type}
                        onChange={(e) => updateEditField('account_type', e.target.value)}
                      >
                        {ACCOUNT_TYPE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Номер счета
                      <input
                        value={editData.form.account_number}
                        onChange={(e) => updateEditField('account_number', normalizeKzAccountInput(e.target.value))}
                        maxLength={20}
                        required
                      />
                    </label>
                    <label>
                      Дата смерти пенсионера
                      <input
                        type="date"
                        value={editData.form.death_date || ''}
                        onChange={(e) => updateEditField('death_date', e.target.value)}
                      />
                    </label>
                  </>
                )}

                {editError && <div className="error-banner">{editError}</div>}

                <div className="modal-actions">
                  <button type="button" className="btn btn-secondary" onClick={closeEditModal}>
                    Отмена
                  </button>
                  <button className="btn btn-primary" type="submit" disabled={editSaving}>
                    {editSaving ? (
                      <>
                        <Loader2 className="spin" size={14} /> Сохранение...
                      </>
                    ) : (
                      'Сохранить'
                    )}
                  </button>
                </div>
              </form>
            ) : (
              <p className="muted">Нет данных</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function StatementsTab() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState(null);
  const [periodStart, setPeriodStart] = useState('');

  const load = async (period = periodStart) => {
    setLoading(true);
    setError('');
    try {
      const query = period ? `?period_start=${encodeURIComponent(period)}` : '';
      const response = await apiFetch(`/api/v2/statements/${query}`);
      setData(response);
      if (!period && response.all_periods?.length > 0) {
        setPeriodStart(response.all_periods[0].period_start);
      }
    } catch (e) {
      setError(getErrorText(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load('');
  }, []);

  useEffect(() => {
    if (periodStart) {
      load(periodStart);
    }
  }, [periodStart]);

  const renderTable = (title, section) => (
    <div className="card" key={title}>
      <div className="section-head">
        <div>
          <h3>{title}</h3>
          <p>
            Статус: <span className={cn('badge', section.status?.code === 'active' ? 'ok' : '')}>{section.status?.label}</span>
          </p>
        </div>
        <a className="btn btn-primary" href={section.excel_url} target="_blank" rel="noreferrer">
          <Download size={14} /> Excel
        </a>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>№</th>
              <th>ФИО</th>
              <th>Табельный</th>
              <th>Кол-во</th>
              <th>Койко-дни</th>
              <th>Сумма</th>
            </tr>
          </thead>
          <tbody>
            {(section.rows || []).map((row) => (
              <tr key={`${title}-${row.number}-${row.vacation_id}`}>
                <td>{row.number}</td>
                <td>{row.full_name}</td>
                <td>{row.personnel_number || '—'}</td>
                <td>{row.vouchers_count}</td>
                <td>{row.bed_days}</td>
                <td>{formatMoney(row.price)}</td>
              </tr>
            ))}
            {(section.rows || []).length === 0 && (
              <tr>
                <td colSpan={6} className="empty-row">
                  Нет данных за период
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="table-total">Итого: {formatMoney(section.total_sum)}</div>
    </div>
  );

  return (
    <div className="stack">
      {error && <div className="error-banner">{error}</div>}

      <div className="card section-head">
        <div>
          <h3>Период ведомостей</h3>
          {data && (
            <p>
              {data.period_start_human} - {data.period_end_human}
            </p>
          )}
        </div>
        <select value={periodStart} onChange={(e) => setPeriodStart(e.target.value)}>
          {(data?.all_periods || []).map((p) => (
            <option key={p.period_start} value={p.period_start}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="card center">
          <Loader2 className="spin" size={20} />
        </div>
      ) : (
        data && (
          <>
            {renderTable('Ведомость путевок за Жартас', data.zhartas)}
            {renderTable('Ведомость путевок за Шахтер', data.shakhter)}
          </>
        )
      )}
    </div>
  );
}

function ListsTab({ user, references }) {
  const listConfigs = {
    coal: {
      label: 'Компенсация за уголь',
      endpoint: '/coal-compensation/list/',
      rowsKey: 'compensation_data',
      excel: '/coal-compensation/excel/',
    },
    bonus: {
      label: 'Доплата за 3 степени',
      endpoint: '/bonus-payment/list/',
      rowsKey: 'bonus_data',
      excel: '/bonus-payment/excel/',
    },
    funeral: {
      label: 'Ритуальные услуги',
      endpoint: '/funeral-services/list/',
      rowsKey: 'funeral_data',
      excel: '/funeral-services/excel/',
    },
    pensioner: {
      label: 'Матпомощь пенсионерам',
      endpoint: '/pensioner-material-assistance/list/',
      rowsKey: 'assistance_data',
      excel: '/pensioner-material-assistance/excel/',
    },
    registry: {
      label: 'Реестр матпомощи',
      endpoint: '/material-assistance/registry/list/',
      rowsKey: 'registry_data',
      excel: '/material-assistance/registry/excel/',
    },
  };

  const [active, setActive] = useState('coal');
  const [period, setPeriod] = useState('');
  const [enterpriseFilter, setEnterpriseFilter] = useState('all');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [listSearch, setListSearch] = useState('');
  const [sortField, setSortField] = useState('number');
  const [sortDirection, setSortDirection] = useState('asc');

  const load = async (targetList = active, targetPeriod = period) => {
    setLoading(true);
    setError('');

    try {
      const conf = listConfigs[targetList];
      const params = new URLSearchParams();
      if (targetPeriod) {
        params.set('period_start', targetPeriod);
      }
      if (user.is_admin && enterpriseFilter !== 'all') {
        params.set('user_id', enterpriseFilter);
      }
      const query = params.toString() ? `?${params.toString()}` : '';
      const response = await apiFetch(`${conf.endpoint}${query}`);
      setData(response);
      if (!targetPeriod && response.all_periods?.length > 0) {
        setPeriod(response.all_periods[0]);
      }
    } catch (e) {
      setError(getErrorText(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(active, '');
  }, [active, enterpriseFilter]);

  useEffect(() => {
    if (period) {
      load(active, period);
    }
  }, [period]);

  const rows = data ? data[listConfigs[active].rowsKey] || [] : [];
  const hasIssuedColumn = user.is_admin && (active === 'coal' || active === 'pensioner');
  const showEnterpriseColumn = user.is_admin && enterpriseFilter === 'all';

  const savePaymentField = async (row, field, value) => {
    if (!user.is_admin) return;

    try {
      if (active === 'coal') {
        const fd = new FormData();
        fd.append(field, value);
        await apiFetch(`/api/coal-compensation/${row.coal_request_id}/update-payment/`, {
          method: 'POST',
          body: fd,
        });
      }

      if (active === 'bonus') {
        const fd = new FormData();
        fd.append('period_start', period);
        fd.append(field, value);
        await apiFetch(`/api/bonus-payment/${row.worker_id}/update-payment/`, {
          method: 'POST',
          body: fd,
        });
      }

      if (active === 'funeral') {
        const fd = new FormData();
        fd.append(field, value);
        await apiFetch(`/api/funeral-services/${row.funeral_request_id}/update-payment/`, {
          method: 'POST',
          body: fd,
        });
      }

      if (active === 'pensioner') {
        const fd = new FormData();
        fd.append(field, value);
        await apiFetch(`/api/pensioner-material-assistance/${row.material_request_id}/update-payment/`, {
          method: 'POST',
          body: fd,
        });
      }

      await load(active, period);
    } catch (e) {
      setError(getErrorText(e));
    }
  };

  const toggleIssued = async (row, nextValue) => {
    try {
      if (active === 'coal') {
        await apiFetch(`/api/coal-compensation/${row.coal_request_id}/toggle-issued/`, {
          method: 'POST',
          body: { is_issued: !!nextValue },
        });
      }
      if (active === 'pensioner') {
        await apiFetch(`/api/pensioner-material-assistance/${row.material_request_id}/toggle-issued/`, {
          method: 'POST',
          body: { is_issued: !!nextValue },
        });
      }
      await load(active, period);
    } catch (e) {
      setError(getErrorText(e));
    }
  };

  const renderCell = (row, field) => {
    if (!user.is_admin) return row[field] || '—';

    const editableFields = {
      coal: ['accrued', 'ipn', 'to_pay'],
      bonus: ['accrued', 'ipn', 'to_pay'],
      funeral: ['to_pay'],
      pensioner: ['accrued', 'ipn', 'to_pay'],
    };

    if (!editableFields[active] || !editableFields[active].includes(field)) {
      return row[field] || '—';
    }

    return (
      <input
        className="table-input"
        defaultValue={row[field] || ''}
        onBlur={(e) => savePaymentField(row, field, e.target.value)}
      />
    );
  };

  const columns = useMemo(() => {
    if (active === 'coal') {
      return [
        ['№', 'number'],
        ['ФИО', 'full_name'],
        ['Статус работника', 'worker_status_display'],
        ['ИИН', 'inn'],
        ['Счет', 'account_number'],
        ['Банк', 'bank'],
        ['Льготы', 'benefits'],
        ['Начислено', 'accrued'],
        ['ИПН', 'ipn'],
        ['К выплате', 'to_pay'],
      ];
    }
    if (active === 'bonus') {
      return [
        ['№', 'number'],
        ['ФИО', 'full_name'],
        ['Статус работника', 'worker_status_display'],
        ['ИИН', 'inn'],
        ['Счет', 'account_number'],
        ['Банк', 'bank'],
        ['Льготы', 'benefits'],
        ['Начислено', 'accrued'],
        ['ИПН', 'ipn'],
        ['К выплате', 'to_pay'],
      ];
    }
    if (active === 'funeral') {
      return [
        ['№', 'number'],
        ['ФИО заявителя', 'applicant_full_name'],
        ['ИИН заявителя', 'applicant_inn'],
        ['Счет', 'account_number'],
        ['Пенсионер', 'pensioner_full_name'],
        ['Статус работника', 'worker_status_display'],
        ['Банк', 'bank'],
        ['К выплате', 'to_pay'],
      ];
    }
    if (active === 'pensioner') {
      return [
        ['№', 'number'],
        ['ФИО', 'full_name'],
        ['Статус работника', 'worker_status_display'],
        ['ИИН', 'inn'],
        ['Счет', 'account_number'],
        ['Банк', 'bank'],
        ['Льготы', 'benefits'],
        ['Начислено', 'accrued'],
        ['ИПН', 'ipn'],
        ['К выплате', 'to_pay'],
      ];
    }
    if (active === 'registry') {
      return [
        ['№', 'number'],
        ['ФИО', 'full_name'],
        ['Статус работника', 'worker_status_display'],
        ['ИИН', 'inn'],
        ['Счет', 'account_number'],
        ['Вид помощи', 'assistance_type'],
        ['Сумма', 'amount'],
        ['Статус', 'status_text'],
        ['Дата', 'created_at'],
        ['Выдано', 'is_issued'],
      ];
    }
    return [
      ['№', 'number'],
      ['ФИО', 'full_name'],
      ['Статус работника', 'worker_status_display'],
      ['ИИН', 'inn'],
      ['Вид помощи', 'assistance_type'],
      ['Сумма', 'amount'],
      ['Статус', 'status_text'],
      ['Дата', 'created_at'],
      ['Выдано', 'is_issued'],
    ];
  }, [active]);

  const sortRows = (leftValue, rightValue) => {
    const normalize = (value) => {
      if (value === null || value === undefined || value === '') return null;
      if (typeof value === 'number') return value;
      if (typeof value === 'boolean') return value ? 1 : 0;

      const text = String(value).trim();
      const dateMatch = text.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
      if (dateMatch) {
        return new Date(Number(dateMatch[3]), Number(dateMatch[2]) - 1, Number(dateMatch[1])).getTime();
      }

      const compact = text.replace(/\s+/g, '').replace(',', '.');
      if (/^-?\d+(\.\d+)?$/.test(compact)) {
        return Number(compact);
      }

      return text.toLowerCase();
    };

    const left = normalize(leftValue);
    const right = normalize(rightValue);

    if (left === null && right === null) return 0;
    if (left === null) return 1;
    if (right === null) return -1;

    let result = 0;
    if (typeof left === 'number' && typeof right === 'number') {
      result = left - right;
    } else {
      result = String(left).localeCompare(String(right), 'ru');
    }

    return sortDirection === 'asc' ? result : -result;
  };

  const visibleRows = useMemo(() => {
    let filtered = [...rows];
    const query = listSearch.trim().toLowerCase();

    if (query) {
      const searchableFields = columns.map(([, field]) => field);
      if (showEnterpriseColumn) {
        searchableFields.push('user_account');
      }
      filtered = filtered.filter((row) =>
        searchableFields.some((field) => {
          const value = row[field];
          if (value === null || value === undefined) return false;
          if (typeof value === 'boolean') {
            const boolText = value ? 'да true' : 'нет false';
            return boolText.includes(query);
          }
          return String(value).toLowerCase().includes(query);
        })
      );
    }

    if (sortField) {
      filtered.sort((a, b) => sortRows(a[sortField], b[sortField]));
    }
    return filtered;
  }, [rows, listSearch, columns, sortField, sortDirection, showEnterpriseColumn]);

  const onSortClick = (field) => {
    if (sortField !== field) {
      setSortField(field);
      setSortDirection('asc');
      return;
    }
    setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
  };

  const buildExcelUrl = (baseUrl) => {
    const params = new URLSearchParams();
    if (period) {
      params.set('period_start', period);
    }
    if (user.is_admin && enterpriseFilter !== 'all') {
      params.set('user_id', enterpriseFilter);
    }
    if (!params.toString()) return baseUrl;
    const separator = baseUrl.includes('?') ? '&' : '?';
    return `${baseUrl}${separator}${params.toString()}`;
  };

  return (
    <div className="stack">
      <div className="toolbar list-toolbar">
        <div className="tab-inline">
          {Object.entries(listConfigs).map(([key, conf]) => (
            <button
              key={key}
              className={cn('btn btn-secondary', active === key && 'tab-active')}
              onClick={() => {
                setActive(key);
                setPeriod('');
                setListSearch('');
                setSortField('number');
                setSortDirection('asc');
              }}
            >
              {conf.label}
            </button>
          ))}
        </div>

        <div className="right-actions">
          {user.is_admin && (
            <select value={enterpriseFilter} onChange={(e) => setEnterpriseFilter(e.target.value)}>
              <option value="all">Все предприятия (общий)</option>
              {(references?.users || []).map((item) => (
                <option key={item.id} value={String(item.id)}>
                  {item.username}
                </option>
              ))}
            </select>
          )}
          <label className="search-field list-search">
            <Search size={14} />
            <input
              value={listSearch}
              onChange={(e) => setListSearch(e.target.value)}
              placeholder="Поиск по текущему списку"
            />
          </label>
          <select value={period} onChange={(e) => setPeriod(e.target.value)}>
            {(data?.all_periods || []).map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <a className="btn btn-primary" href={buildExcelUrl(listConfigs[active].excel)} target="_blank" rel="noreferrer">
            <Download size={14} /> Excel
          </a>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div className="section-head">
          <div>
            <h3>{listConfigs[active].label}</h3>
            <p>
              Период: {data?.period_start || '—'} - {data?.period_end || '—'} | Статус: {data?.status_display || '—'}
            </p>
            {typeof data?.unissued_count === 'number' && typeof data?.total_count === 'number' && (
              <p>
                Невыдано: {data.unissued_count} из {data.total_count}
              </p>
            )}
          </div>
        </div>

        {loading ? (
          <div className="center">
            <Loader2 className="spin" size={20} />
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  {columns.map((column) => (
                    <th
                      key={column[1]}
                      className={cn('sortable-th', sortField === column[1] && 'sortable-th-active')}
                      onClick={() => onSortClick(column[1])}
                    >
                      {column[0]}
                      <span className="th-sort">
                        {sortField === column[1] ? (sortDirection === 'asc' ? '▲' : '▼') : '↕'}
                      </span>
                    </th>
                  ))}
                  {hasIssuedColumn && <th>Выдано</th>}
                  {showEnterpriseColumn && <th>Предприятие</th>}
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row, index) => (
                  <tr key={`${active}-${index}-${row.number || row.id || index}`}>
                    {columns.map((column) => (
                      <td key={column[1]}>{renderCell(row, column[1])}</td>
                    ))}
                    {hasIssuedColumn && (
                      <td>
                        <input
                          type="checkbox"
                          checked={!!row.is_issued}
                          onChange={(e) => toggleIssued(row, e.target.checked)}
                        />
                      </td>
                    )}
                    {showEnterpriseColumn && <td>{row.user_account || '—'}</td>}
                  </tr>
                ))}
                {visibleRows.length === 0 && (
                  <tr>
                    <td
                      colSpan={columns.length + (hasIssuedColumn ? 1 : 0) + (showEnterpriseColumn ? 1 : 0)}
                      className="empty-row"
                    >
                      {listSearch.trim() ? 'По вашему запросу ничего не найдено' : 'Нет данных за период'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
