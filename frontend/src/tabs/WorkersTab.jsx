import React, { useEffect, useRef, useState } from 'react';
import { ChevronRight, Download, FileStack, Pencil, Plus, Search, Trash2, UserPlus, UserRound, Users, X } from 'lucide-react';
import { apiFetch } from '../lib/api';
import {
  EMPTY_WORKER_FORM,
  REPORT_TYPE_LABEL,
  WORKER_FILE_FIELDS,
  cn,
  formatCount,
  getErrorText,
  hasAccount,
  initials,
  normalizeKzAccountInput,
  requestStatusTone,
  toBooleanString,
  useDebounce,
  useIsMobile,
  workerStatusTone,
} from '../lib/utils';
import {
  Alert,
  Badge,
  Card,
  EmptyState,
  Field,
  FileInput,
  FlagToggle,
  IconButton,
  Modal,
  Pagination,
  SkeletonRows,
  Spinner,
  useFeedback,
} from '../components/ui';
import { buildWorkerFormData } from './workerForm';

function FormSection({ id, title, description, children }) {
  return (
    <section className="form-section" id={id}>
      <div className="form-section-head">
        <h4>{title}</h4>
        {description && <p>{description}</p>}
      </div>
      {children}
    </section>
  );
}

export default function WorkersTab({ user, references, onRefreshReference }) {
  const { toast, confirm } = useFeedback();
  const isMobile = useIsMobile();
  const [workers, setWorkers] = useState([]);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [openingId, setOpeningId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [formState, setFormState] = useState(EMPTY_WORKER_FORM);
  const [workerReports, setWorkerReports] = useState([]);

  const debouncedSearch = useDebounce(search, 250);
  const requestSeq = useRef(0);

  // На телефоне следующие страницы дописываются в конец списка («Показать ещё»).
  const loadWorkers = async (targetPage = page, append = false) => {
    // Учитываем только ответ на последний запрос: поиск медленный, старые ответы могут прийти позже новых.
    requestSeq.current += 1;
    const seq = requestSeq.current;
    setLoading(true);
    setError('');
    try {
      const response = await apiFetch(
        `/api/v2/workers/?page=${targetPage}&page_size=50&search=${encodeURIComponent(debouncedSearch)}`
      );
      if (seq !== requestSeq.current) return;
      const results = response.results || [];
      setWorkers((prev) => (append ? [...prev, ...results] : results));
      setPagination(response.pagination || null);
    } catch (e) {
      if (seq === requestSeq.current) setError(getErrorText(e));
    } finally {
      if (seq === requestSeq.current) setLoading(false);
    }
  };

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

  useEffect(() => {
    loadWorkers(page, isMobile && page > 1);
  }, [debouncedSearch, page]);

  const reloadWorkers = async () => {
    if (isMobile && page !== 1) {
      setPage(1);
      return;
    }
    await loadWorkers(page);
  };

  const setField = (key, value) => setFormState((prev) => ({ ...prev, [key]: value }));

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
    setOpeningId(id);
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
        phone: worker.phone || '+7',
        address: worker.address || '',
        id_number: worker.id_number || '',
        id_issue_date: worker.id_issue_date || '',
        id_issued_by: worker.id_issued_by || '',
        has_benefits: toBooleanString(worker.has_benefits),
        benefits_name: worker.benefits_name || '',
        has_miner_glory: toBooleanString(worker.has_miner_glory),
        account_20_digit: worker.account_20_digit || 'KZ',
        current_account: worker.current_account || 'KZ',
        enterprise_subdivision: worker.enterprise_subdivision || '',
        regress_100_active: toBooleanString(worker.regress_100_active),
        regress_29_active: toBooleanString(worker.regress_29_active),
        regress_15_active: toBooleanString(worker.regress_15_active),
        is_dead: toBooleanString(worker.is_dead),
        death_date: worker.death_date || '',
        user_id: worker.user_id ? String(worker.user_id) : '',
        family_members: worker.family_members || [],
        existing_files: worker.files || {},
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
      toast({ tone: 'error', title: 'Не удалось открыть карточку', text: getErrorText(e) });
    } finally {
      setOpeningId(null);
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
      const wasEditing = !!editingId;
      closeForm();
      toast({ title: wasEditing ? 'Изменения сохранены' : 'Работник добавлен', text: formState.full_name });
      await reloadWorkers();
      if (user.is_admin) {
        await onRefreshReference();
      }
    } catch (e) {
      setFormError(getErrorText(e));
    } finally {
      setSaving(false);
    }
  };

  const deleteWorker = async (worker, { fromForm = false } = {}) => {
    const ok = await confirm({
      title: 'Удалить работника?',
      text: `${worker.full_name} будет удален вместе с данными карточки. Это действие нельзя отменить.`,
      confirmText: 'Удалить',
      tone: 'danger',
    });
    if (!ok) return;
    try {
      await apiFetch(`/api/v2/workers/${worker.id}/`, { method: 'DELETE' });
      toast({ title: 'Работник удален', text: worker.full_name });
      if (fromForm) closeForm();
      await reloadWorkers();
    } catch (e) {
      toast({ tone: 'error', title: 'Не удалось удалить', text: getErrorText(e) });
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

  const sectionNav = [
    ['ws-main', 'Основное'],
    ['ws-work', 'Работа'],
    ['ws-contacts', 'Контакты'],
    ['ws-accounts', 'Счета'],
    ['ws-benefits', 'Льготы'],
    ['ws-docs', 'Документы'],
    ['ws-family', 'Семья'],
    ['ws-marks', 'Отметки'],
    ...(editingId ? [['ws-reports', 'Заявления']] : []),
  ];
  // Прокручиваем только тело карточки: scrollIntoView сдвигал бы и само окно вместе с шапкой.
  const scrollToSection = (id) => {
    const section = document.getElementById(id);
    const body = section?.closest('.modal-body');
    if (!section || !body) return;
    const navHeight = body.querySelector('.section-nav')?.offsetHeight || 0;
    const top = section.getBoundingClientRect().top - body.getBoundingClientRect().top + body.scrollTop - navHeight - 4;
    body.scrollTo({ top, behavior: 'smooth' });
  };

  const total = pagination?.count ?? workers.length;
  const pageSize = pagination?.page_size || 50;
  const currentPage = pagination?.page || page;
  const rangeStart = total ? (currentPage - 1) * pageSize + 1 : 0;
  const rangeEnd = Math.min(currentPage * pageSize, total);

  const showBenefitsName = formState.has_benefits === 'true' || !!formState.benefits_name;
  const showDeathDate = formState.is_dead === 'true' || !!formState.death_date;

  return (
    <div className="stack workers-stack">
      <div className="toolbar">
        <div className="search-field search-lg">
          <Search size={17} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={isMobile ? 'ФИО, таб. номер, ИИН' : 'Поиск по ФИО, табельному номеру, ИИН, участку...'}
          />
          {search && (
            <button type="button" className="search-clear" onClick={() => setSearch('')} aria-label="Очистить поиск">
              <X size={15} />
            </button>
          )}
        </div>
        <button className="btn btn-primary toolbar-add" onClick={openCreate}>
          <UserPlus size={17} /> Добавить работника
        </button>
      </div>

      {error && <Alert tone="error">{error}</Alert>}

      <Card flush>
        {loading && !workers.length ? (
          <SkeletonRows rows={8} cols={6} />
        ) : workers.length === 0 ? (
          <EmptyState
            icon={debouncedSearch ? Search : Users}
            title={debouncedSearch ? 'Никого не нашли' : 'Работников пока нет'}
            text={
              debouncedSearch
                ? 'Проверьте написание или поищите по табельному номеру.'
                : 'Добавьте первого работника, чтобы оформлять заявления.'
            }
            action={
              !debouncedSearch && (
                <button className="btn btn-primary" onClick={openCreate}>
                  <Plus size={16} /> Добавить работника
                </button>
              )
            }
          />
        ) : isMobile ? (
          <div className="m-list">
            {workers.map((worker) => (
              <button type="button" key={worker.id} className="m-item" onClick={() => openEdit(worker.id)}>
                <span className="avatar avatar-md">{initials(worker.full_name)}</span>
                <span className="m-item-main">
                  <strong>{worker.full_name}</strong>
                  <span className="m-item-sub">
                    {worker.position || 'Должность не указана'}
                    {worker.personnel_number ? `, Таб. № ${worker.personnel_number}` : ''}
                  </span>
                  <span className="m-item-badges">
                    <Badge tone={workerStatusTone(worker.status)}>{worker.status_display}</Badge>
                  </span>
                </span>
                {openingId === worker.id ? <Spinner size={18} /> : <ChevronRight size={20} className="m-item-arrow" />}
              </button>
            ))}
          </div>
        ) : (
          <div className={cn('table-wrap', loading && 'is-loading')}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Работник</th>
                  <th>Таб. №</th>
                  <th>ИИН</th>
                  <th>Статус</th>
                  <th>Участок</th>
                  <th>Счет</th>
                  <th className="col-actions" aria-label="Действия" />
                </tr>
              </thead>
              <tbody>
                {workers.map((worker) => {
                  const account = hasAccount(worker.account_20_digit)
                    ? worker.account_20_digit
                    : hasAccount(worker.current_account)
                      ? worker.current_account
                      : '';
                  return (
                    <tr key={worker.id} className="row-clickable" onClick={() => openEdit(worker.id)}>
                      <td>
                        <div className="person-cell">
                          <span className="avatar avatar-sm">{initials(worker.full_name)}</span>
                          <div>
                            <strong>{worker.full_name}</strong>
                            <span>{worker.position || 'Должность не указана'}</span>
                          </div>
                        </div>
                      </td>
                      <td className="tnum">{worker.personnel_number || <span className="muted">—</span>}</td>
                      <td className="tnum">{worker.inn || <span className="muted">—</span>}</td>
                      <td>
                        <Badge tone={workerStatusTone(worker.status)}>{worker.status_display}</Badge>
                      </td>
                      <td>{worker.department || <span className="muted">—</span>}</td>
                      <td className="mono">{account || <span className="muted">—</span>}</td>
                      <td className="col-actions" onClick={(e) => e.stopPropagation()}>
                        <div className="row-actions">
                          {openingId === worker.id ? (
                            <span className="icon-btn">
                              <Spinner size={16} />
                            </span>
                          ) : (
                            <IconButton icon={Pencil} label="Открыть карточку" onClick={() => openEdit(worker.id)} />
                          )}
                          <IconButton icon={Trash2} label="Удалить" tone="danger" onClick={() => deleteWorker(worker)} />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {total > 0 && isMobile && (
          <div className="load-more">
            <span>
              Показано {formatCount(workers.length)} из {formatCount(total)}
            </span>
            {pagination?.has_next && (
              <button type="button" className="btn btn-secondary btn-block" onClick={() => setPage((p) => p + 1)} disabled={loading}>
                {loading ? <Spinner size={16} /> : null} Показать ещё
              </button>
            )}
          </div>
        )}

        {total > 0 && !isMobile && (
          <Pagination
            page={currentPage}
            pages={pagination?.pages || 1}
            onChange={setPage}
            summary={
              <>
                Показано {formatCount(rangeStart)}–{formatCount(rangeEnd)} из {formatCount(total)}
              </>
            }
          />
        )}
      </Card>

      <button type="button" className="fab" onClick={openCreate} aria-label="Добавить работника">
        <Plus size={22} /> Добавить
      </button>

      <Modal
        open={formOpen}
        onClose={closeForm}
        size="xl"
        icon={editingId ? UserRound : UserPlus}
        title={editingId ? formState.full_name || 'Карточка работника' : 'Новый работник'}
        subtitle={editingId ? 'Редактирование карточки работника' : 'Заполните карточку. Поля со звездочкой обязательны'}
        footer={
          <>
            {formError && <div className="form-error foot-error">{formError}</div>}
            {editingId && (
              <button
                type="button"
                className="btn btn-ghost btn-danger-text foot-delete"
                onClick={() => deleteWorker({ id: editingId, full_name: formState.full_name }, { fromForm: true })}
              >
                <Trash2 size={16} /> Удалить
              </button>
            )}
            <span className="foot-spacer" />
            <button type="button" className="btn btn-secondary" onClick={closeForm}>
              Отмена
            </button>
            <button className="btn btn-primary" type="submit" form="worker-form" disabled={saving}>
              {saving ? (
                <>
                  <Spinner size={16} /> Сохранение...
                </>
              ) : (
                'Сохранить'
              )}
            </button>
          </>
        }
      >
        <form id="worker-form" className="form-sections" onSubmit={saveWorker}>
          <nav className="section-nav" aria-label="Разделы карточки">
            {sectionNav.map(([id, label]) => (
              <button type="button" key={id} className="section-nav-item" onClick={() => scrollToSection(id)}>
                {label}
              </button>
            ))}
          </nav>
          <FormSection id="ws-main" title="Основные данные">
            <div className="form-grid">
              <Field label="ФИО" required span={2}>
                <input value={formState.full_name} onChange={(e) => setField('full_name', e.target.value)} required />
              </Field>
              <Field label="Статус">
                <select value={formState.status} onChange={(e) => setField('status', e.target.value)}>
                  {(references?.worker_status_choices || [
                    { value: 'worker', label: 'Работник' },
                    { value: 'pensioner', label: 'Пенсионер' },
                  ]).map((statusItem) => (
                    <option key={statusItem.value} value={statusItem.value}>
                      {statusItem.label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Табельный номер">
                <input
                  value={formState.personnel_number}
                  onChange={(e) => setField('personnel_number', e.target.value)}
                  inputMode="numeric"
                />
              </Field>
              <Field label="ИИН">
                <input value={formState.inn} onChange={(e) => setField('inn', e.target.value)} inputMode="numeric" />
              </Field>
              {user.is_admin && (
                <Field label="Аккаунт предприятия">
                  <select value={formState.user_id} onChange={(e) => setField('user_id', e.target.value)}>
                    <option value="">Выберите аккаунт</option>
                    {(references?.users || []).map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.username}
                      </option>
                    ))}
                  </select>
                </Field>
              )}
            </div>
          </FormSection>

          <FormSection id="ws-work" title="Место работы">
            <div className="form-grid">
              <Field label="Участок" required>
                <input value={formState.department} onChange={(e) => setField('department', e.target.value)} required />
              </Field>
              <Field label="Должность" required>
                <input value={formState.position} onChange={(e) => setField('position', e.target.value)} required />
              </Field>
              <Field label="Подразделение (Энергоуголь)">
                <select
                  value={formState.enterprise_subdivision}
                  onChange={(e) => setField('enterprise_subdivision', e.target.value)}
                >
                  <option value="">Не выбрано</option>
                  {(references?.enterprise_subdivision_choices || []).map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
            <div className="toggle-grid">
              <FlagToggle
                label="Член профсоюза"
                value={formState.is_union_member}
                onChange={(v) => setField('is_union_member', v)}
              />
              <FlagToggle
                label="Присоединен к коллективному договору"
                value={formState.is_contract_member}
                onChange={(v) => setField('is_contract_member', v)}
              />
            </div>
          </FormSection>

          <FormSection id="ws-contacts" title="Контакты и удостоверение личности">
            <div className="form-grid">
              <Field label="Телефон">
                <input
                  value={formState.phone}
                  onChange={(e) => setField('phone', e.target.value)}
                  onBlur={() =>
                    setFormState((prev) => ({
                      ...prev,
                      phone: (prev.phone || '').trim() || '+7',
                    }))
                  }
                  inputMode="tel"
                />
              </Field>
              <Field label="Адрес" span={2}>
                <input value={formState.address} onChange={(e) => setField('address', e.target.value)} />
              </Field>
              <Field label="Номер удостоверения" required>
                <input value={formState.id_number} onChange={(e) => setField('id_number', e.target.value)} required />
              </Field>
              <Field label="Дата выдачи">
                <input type="date" value={formState.id_issue_date} onChange={(e) => setField('id_issue_date', e.target.value)} />
              </Field>
              <Field label="Кем выдано">
                <input value={formState.id_issued_by} onChange={(e) => setField('id_issued_by', e.target.value)} />
              </Field>
            </div>
          </FormSection>

          <FormSection id="ws-accounts" title="Банковские счета" description="Номер счета начинается с KZ, до 20 символов">
            <div className="form-grid form-grid-2">
              <Field label="Карточный счет">
                <input
                  className="mono"
                  value={formState.account_20_digit}
                  onChange={(e) => setField('account_20_digit', normalizeKzAccountInput(e.target.value, true))}
                />
              </Field>
              <Field label="Текущий счет">
                <input
                  className="mono"
                  value={formState.current_account}
                  onChange={(e) => setField('current_account', normalizeKzAccountInput(e.target.value, true))}
                />
              </Field>
            </div>
          </FormSection>

          <FormSection id="ws-benefits" title="Льготы и регресс">
            <div className="toggle-grid">
              <FlagToggle label="Есть льготы" value={formState.has_benefits} onChange={(v) => setField('has_benefits', v)} />
              <FlagToggle
                label="Шахтерская / трудовая слава"
                value={formState.has_miner_glory}
                onChange={(v) => setField('has_miner_glory', v)}
              />
            </div>
            {showBenefitsName && (
              <div className="form-grid">
                <Field label="Название льготы" span={2}>
                  <input value={formState.benefits_name} onChange={(e) => setField('benefits_name', e.target.value)} />
                </Field>
              </div>
            )}
            <div className="toggle-grid toggle-grid-3">
              <FlagToggle
                label="Регресс 100%"
                description="Пункт 13.1"
                value={formState.regress_100_active}
                onChange={(v) => setField('regress_100_active', v)}
              />
              <FlagToggle
                label="Регресс 29%"
                description="Пункт 13.2"
                value={formState.regress_29_active}
                onChange={(v) => setField('regress_29_active', v)}
              />
              <FlagToggle
                label="Регресс 15%"
                description="Пункт 13.3"
                value={formState.regress_15_active}
                onChange={(v) => setField('regress_15_active', v)}
              />
            </div>
          </FormSection>

          <FormSection id="ws-docs" title="Документы" description="Сканы и фото документов работника">
            <div className="form-grid form-grid-2">
              {WORKER_FILE_FIELDS.map(([fileKey, label]) => {
                const existing = formState.existing_files?.[fileKey];
                return (
                  <FileInput
                    key={fileKey}
                    label={label}
                    file={formState.files?.[fileKey]}
                    current={existing?.name && existing?.download_url ? { name: existing.name, url: existing.download_url } : null}
                    onChange={(file) =>
                      setFormState((prev) => ({
                        ...prev,
                        files: { ...prev.files, [fileKey]: file },
                      }))
                    }
                  />
                );
              })}
            </div>
          </FormSection>

          <FormSection id="ws-family" title="Члены семьи" description="Используются при оформлении путевок">
            {(formState.family_members || []).length === 0 ? (
              <EmptyState compact icon={Users} text="Члены семьи не добавлены" />
            ) : (
              <div className="family-list">
                {(formState.family_members || []).map((member, index) => (
                  <div className="family-card" key={`family-${index}`}>
                    <div className="family-card-head">
                      <span className="family-index">{index + 1}</span>
                      <strong>{member.full_name || 'Новый член семьи'}</strong>
                      <IconButton icon={Trash2} label="Убрать" tone="danger" onClick={() => removeFamilyMember(index)} />
                    </div>
                    <div className="form-grid">
                      <Field label="ФИО" span={2}>
                        <input
                          value={member.full_name || ''}
                          onChange={(e) => updateFamilyMember(index, 'full_name', e.target.value)}
                        />
                      </Field>
                      <Field label="Родство">
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
                      </Field>
                      <Field label="Дата рождения">
                        <input
                          type="date"
                          value={member.birth_date || ''}
                          onChange={(e) => updateFamilyMember(index, 'birth_date', e.target.value)}
                        />
                      </Field>
                      <Field label="Удостоверение / свидетельство">
                        <input
                          value={member.id_number || ''}
                          onChange={(e) => updateFamilyMember(index, 'id_number', e.target.value)}
                        />
                      </Field>
                      <Field label="Дата выдачи">
                        <input
                          type="date"
                          value={member.id_issue_date || ''}
                          onChange={(e) => updateFamilyMember(index, 'id_issue_date', e.target.value)}
                        />
                      </Field>
                      <Field label="Кем выдано" span="full">
                        <input
                          value={member.id_issued_by || ''}
                          onChange={(e) => updateFamilyMember(index, 'id_issued_by', e.target.value)}
                        />
                      </Field>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <button type="button" className="btn btn-secondary btn-dashed" onClick={addFamilyMember}>
              <Plus size={16} /> Добавить члена семьи
            </button>
          </FormSection>

          <FormSection id="ws-marks" title="Особые отметки">
            <div className="toggle-grid">
              <FlagToggle label="Помечен как умерший" value={formState.is_dead} onChange={(v) => setField('is_dead', v)} />
            </div>
            {showDeathDate && (
              <div className="form-grid">
                <Field label="Дата смерти">
                  <input type="date" value={formState.death_date} onChange={(e) => setField('death_date', e.target.value)} />
                </Field>
              </div>
            )}
          </FormSection>

          {editingId && (
            <FormSection id="ws-reports" title="Заявления работника" description={`Всего: ${workerReports.length}`}>
              {workerReports.length ? (
                <div className="table-wrap table-inset">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Вид</th>
                        <th>Дата</th>
                        <th>Статус</th>
                        <th className="col-actions" aria-label="Действия" />
                      </tr>
                    </thead>
                    <tbody>
                      {workerReports.map((row) => (
                        <tr key={`${row.type}-${row.id}`}>
                          <td>{REPORT_TYPE_LABEL[row.type] || row.type}</td>
                          <td>{row.created_at || '—'}</td>
                          <td>
                            <Badge tone={requestStatusTone(row.status)} dot>
                              {row.status_text || '—'}
                            </Badge>
                          </td>
                          <td className="col-actions">
                            {row.download_url ? (
                              <IconButton icon={Download} label="Скачать документ" href={row.download_url} />
                            ) : (
                              <span className="muted">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState compact icon={FileStack} text="По этому работнику заявлений еще не было" />
              )}
            </FormSection>
          )}
        </form>
      </Modal>
    </div>
  );
}
