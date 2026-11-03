import React, { useEffect, useState } from 'react';
import {
  BarChart3,
  ChevronRight,
  ClipboardList,
  Ellipsis,
  Eye,
  EyeOff,
  FilePlus2,
  FileStack,
  FileText,
  Handshake,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  Plus,
  ShieldCheck,
  TableProperties,
  Users,
  X,
} from 'lucide-react';
import { apiFetch } from './lib/api';
import { cn, getErrorText, getReferences, initials } from './lib/utils';
import { FeedbackProvider, Spinner } from './components/ui';
import DashboardTab from './tabs/DashboardTab';
import WorkersTab from './tabs/WorkersTab';
import ApplicationsTab from './tabs/ApplicationsTab';
import ReportsTab from './tabs/ReportsTab';
import AppealsTab from './tabs/AppealsTab';
import StatementsTab from './tabs/StatementsTab';
import ListsTab from './tabs/ListsTab';

const NAV_GROUPS = [
  {
    title: 'Обзор',
    items: [{ id: 'dashboard', label: 'Главная', icon: LayoutDashboard }],
  },
  {
    title: 'Работа',
    items: [
      { id: 'workers', label: 'Работники', icon: Users },
      { id: 'applications', label: 'Новое заявление', icon: FilePlus2 },
      { id: 'reports', label: 'Отчеты', icon: FileStack },
      { id: 'appeals', label: 'Обращения', icon: MessageSquare },
    ],
  },
  {
    title: 'Документы',
    items: [
      { id: 'statements', label: 'Ведомости', icon: TableProperties },
      { id: 'lists', label: 'Списки выплат', icon: ClipboardList },
    ],
  },
];

const TAB_META = {
  dashboard: { title: 'Главная', description: '' },
  workers: { title: 'Работники', description: 'Работники и пенсионеры, их документы и члены семьи' },
  applications: {
    title: 'Новое заявление',
    description: 'Выберите вид заявления и заполните форму — документ скачается автоматически',
  },
  reports: { title: 'Отчеты', description: 'Все созданные заявления: просмотр, скачивание и исправление' },
  appeals: { title: 'Обращения', description: 'История обращений работника за выбранный год' },
  statements: { title: 'Ведомости', description: 'Ведомости путевок в «Жартас» и «Шахтер» по периодам' },
  lists: { title: 'Списки выплат', description: 'Списки выплат и реестры с выгрузкой в Excel' },
  more: { title: 'Ещё', description: 'Другие разделы и аккаунт' },
};

const KNOWN_TABS = new Set(Object.keys(TAB_META));

// Нижняя панель на телефоне: основные разделы + «Ещё» для остальных.
const BOTTOM_NAV = [
  { id: 'dashboard', label: 'Главная', icon: LayoutDashboard },
  { id: 'workers', label: 'Работники', icon: Users },
  { id: 'applications', label: 'Заявление', icon: Plus, primary: true },
  { id: 'reports', label: 'Отчеты', icon: FileStack },
  { id: 'more', label: 'Ещё', icon: Ellipsis, also: ['appeals', 'statements', 'lists'] },
];

const MORE_ITEMS = [
  { id: 'appeals', label: 'Обращения', text: 'История обращений работника за год', icon: MessageSquare, tone: 'blue' },
  { id: 'statements', label: 'Ведомости', text: 'Путевки в «Жартас» и «Шахтер»', icon: TableProperties, tone: 'teal' },
  { id: 'lists', label: 'Списки выплат', text: 'Уголь, доплаты, ритуальные, реестры', icon: ClipboardList, tone: 'amber' },
];

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
        <span className="brand-mark brand-mark-lg">
          <Handshake size={26} />
        </span>
        <Spinner size={20} />
      </div>
    );
  }

  return (
    <FeedbackProvider>
      {authData ? (
        <Shell
          user={authData}
          references={references}
          onLogout={handleLogout}
          onRefreshReference={async () => {
            const ref = await getReferences();
            setReferences(ref);
          }}
        />
      ) : (
        <LoginScreen accounts={accounts} onLogin={handleLogin} authError={authError} />
      )}
    </FeedbackProvider>
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

  const features = [
    { icon: Users, text: 'Работники, пенсионеры и члены их семей' },
    { icon: FileText, text: 'Заявления с готовым документом для печати' },
    { icon: BarChart3, text: 'Ведомости и списки выплат в Excel' },
  ];

  return (
    <div className="auth-page">
      <aside className="auth-aside">
        <div className="auth-aside-inner">
          <div className="auth-brand">
            <span className="brand-mark brand-mark-light">
              <Handshake size={22} />
            </span>
            <span>Профсоюз</span>
          </div>
          <div className="auth-hero">
            <h1>Учет и заявления профсоюзной организации</h1>
            <p>Все заявления, выплаты и ведомости предприятий — в одном месте.</p>
          </div>
          <ul className="auth-features">
            {features.map(({ icon: Icon, text }) => (
              <li key={text}>
                <span>
                  <Icon size={16} />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>
      </aside>

      <main className="auth-main">
        <form className="auth-card" onSubmit={submit}>
          <div className="auth-card-brand">
            <span className="brand-mark">
              <Handshake size={20} />
            </span>
            <span>Профсоюз</span>
          </div>
          <div className="auth-card-head">
            <h2>Вход в систему</h2>
            <p>Выберите аккаунт предприятия и введите пароль</p>
          </div>

          <label className="field">
            <span className="field-label">Аккаунт</span>
            <select value={username} onChange={(e) => setUsername(e.target.value)}>
              {accounts.map((acc) => (
                <option key={acc} value={acc}>
                  {acc}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span className="field-label">Пароль</span>
            <div className="input-affix">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Введите пароль"
                autoComplete="current-password"
                autoFocus
              />
              <button
                type="button"
                className="input-affix-btn"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
              >
                {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </div>
          </label>

          {(localError || authError) && <div className="form-error">{localError || authError}</div>}

          <button className="btn btn-primary btn-lg btn-block" type="submit" disabled={loading}>
            {loading ? (
              <>
                <Spinner size={16} /> Входим...
              </>
            ) : (
              'Войти'
            )}
          </button>

          <p className="auth-note">
            <ShieldCheck size={14} /> Забыли пароль? Обратитесь к администратору.
          </p>
        </form>
      </main>
    </div>
  );
}

function Shell({ user, references, onLogout, onRefreshReference }) {
  const [activeTab, setActiveTab] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    const tab = params.get('tab');
    return KNOWN_TABS.has(tab) ? tab : 'dashboard';
  });
  const [applicationType, setApplicationType] = useState('vacation');
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set('tab', activeTab);
    window.history.replaceState({}, '', url);
    window.scrollTo({ top: 0 });
  }, [activeTab]);

  const navigate = (tab, options = {}) => {
    if (options.applicationType) setApplicationType(options.applicationType);
    setActiveTab(tab);
    setNavOpen(false);
  };

  const meta = TAB_META[activeTab];

  return (
    <div className={cn('app-shell', navOpen && 'nav-open')}>
      <aside className="sidebar">
        <div className="sidebar-head">
          <div className="brand">
            <span className="brand-mark">
              <Handshake size={20} />
            </span>
            <div className="brand-text">
              <strong>Профсоюз</strong>
              <span>Учет и заявления</span>
            </div>
          </div>
          <button type="button" className="icon-btn sidebar-close" onClick={() => setNavOpen(false)} aria-label="Закрыть меню">
            <X size={18} />
          </button>
        </div>

        <nav className="sidebar-nav">
          {NAV_GROUPS.map((group) => (
            <div className="nav-group" key={group.title}>
              <div className="nav-group-title">{group.title}</div>
              {group.items.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    className={cn('nav-btn', activeTab === tab.id && 'active')}
                    onClick={() => navigate(tab.id)}
                    aria-current={activeTab === tab.id ? 'page' : undefined}
                  >
                    <Icon size={18} />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-user">
          <span className="avatar">{initials(user.username)}</span>
          <div className="sidebar-user-text">
            <strong title={user.username}>{user.username}</strong>
            <span>{user.is_admin ? 'Администратор' : 'Предприятие'}</span>
          </div>
          <button type="button" className="icon-btn" onClick={onLogout} aria-label="Выйти" data-tip="Выйти">
            <LogOut size={17} />
          </button>
        </div>
      </aside>
      <div className="sidebar-backdrop" onClick={() => setNavOpen(false)} />

      <main className="main-area">
        <header className="topbar">
          <button type="button" className="icon-btn menu-btn" onClick={() => setNavOpen(true)} aria-label="Открыть меню">
            <Menu size={20} />
          </button>
          <div className="topbar-title">
            <h1>{meta.title}</h1>
            {meta.description && <p>{meta.description}</p>}
          </div>
          {activeTab !== 'more' && (
            <button type="button" className="topbar-avatar" onClick={() => navigate('more')} aria-label="Аккаунт и другие разделы">
              <span className="avatar avatar-sm">{initials(user.username)}</span>
            </button>
          )}
        </header>

        <section className="content" key={activeTab}>
          {activeTab === 'dashboard' && <DashboardTab user={user} onNavigate={navigate} />}
          {activeTab === 'workers' && (
            <WorkersTab user={user} references={references} onRefreshReference={onRefreshReference} />
          )}
          {activeTab === 'applications' && (
            <ApplicationsTab user={user} activeType={applicationType} onTypeChange={setApplicationType} />
          )}
          {activeTab === 'reports' && <ReportsTab user={user} references={references} />}
          {activeTab === 'appeals' && <AppealsTab />}
          {activeTab === 'statements' && <StatementsTab />}
          {activeTab === 'lists' && <ListsTab user={user} references={references} />}
          {activeTab === 'more' && <MoreTab user={user} onNavigate={navigate} onLogout={onLogout} />}
        </section>
      </main>

      <nav className="bottom-nav" aria-label="Основное меню">
        {BOTTOM_NAV.map((item) => {
          const Icon = item.icon;
          const active = activeTab === item.id || (item.also || []).includes(activeTab);
          return (
            <button
              key={item.id}
              type="button"
              className={cn('bottom-nav-item', item.primary && 'is-primary', active && 'is-active')}
              onClick={() => navigate(item.id)}
              aria-current={active ? 'page' : undefined}
            >
              <span className="bottom-nav-icon">
                <Icon size={item.primary ? 26 : 22} strokeWidth={item.primary ? 2.4 : 2} />
              </span>
              <span className="bottom-nav-label">{item.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}

function MoreTab({ user, onNavigate, onLogout }) {
  return (
    <div className="stack">
      <section className="card more-user">
        <span className="avatar avatar-lg">{initials(user.username)}</span>
        <div>
          <strong>{user.username}</strong>
          <span>{user.is_admin ? 'Администратор' : 'Предприятие'}</span>
        </div>
      </section>

      <section className="card more-list">
        {MORE_ITEMS.map(({ id, label, text, icon: Icon, tone }) => (
          <button type="button" key={id} className="more-row" onClick={() => onNavigate(id)}>
            <span className={`more-row-icon tone-${tone}`}>
              <Icon size={20} />
            </span>
            <span className="more-row-text">
              <strong>{label}</strong>
              <span>{text}</span>
            </span>
            <ChevronRight size={20} className="more-row-arrow" />
          </button>
        ))}
      </section>

      <button type="button" className="btn btn-secondary btn-lg btn-block more-logout" onClick={onLogout}>
        <LogOut size={18} /> Выйти
      </button>
    </div>
  );
}

export default App;
