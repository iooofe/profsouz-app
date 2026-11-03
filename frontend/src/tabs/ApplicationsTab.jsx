import React, { useEffect, useState } from 'react';
import { Check, Download, FileStack, Flame, Flower2, HandCoins, Info, Palmtree } from 'lucide-react';
import { apiFetch } from '../lib/api';
import {
  ACCOUNT_TYPE_OPTIONS,
  ASSISTANCE_TYPE_OPTIONS,
  RESORT_OPTIONS,
  cn,
  getErrorText,
  isEnergougol,
  isPensionerStatus,
  normalizeKzAccountInput,
  resolveWorkerAccount,
  triggerDownload,
} from '../lib/utils';
import { Alert, Card, Field, FileInput, Segmented, Spinner, Toggle, useFeedback } from '../components/ui';
import WorkerLookup from '../components/WorkerLookup';

const APPLICATION_TYPES = [
  { value: 'vacation', label: 'Путевка', text: 'Санаторий, дом отдыха, лагерь', icon: Palmtree, tone: 'teal' },
  { value: 'material', label: 'Материальная помощь', short: 'Матпомощь', text: 'Больничный, рождение, лечение', icon: HandCoins, tone: 'blue' },
  { value: 'coal', label: 'Уголь', text: 'Компенсация за уголь', icon: Flame, tone: 'amber' },
  { value: 'funeral', label: 'Погребение', text: 'Выплата на погребение', icon: Flower2, tone: 'violet' },
];

const SUBDIVISION_FALLBACK = [
  { value: 'energo_ugol', label: 'Энергоуголь' },
  { value: 'pu', label: 'ПУ' },
  { value: 'svyaz', label: 'Связь' },
];

function Step({ number, title, children }) {
  return (
    <section className="step">
      <div className="step-head">
        <span className="step-number">{number}</span>
        <h4>{title}</h4>
      </div>
      <div className="step-body">{children}</div>
    </section>
  );
}

function AccountFields({ accountType, accountNumber, onTypeChange, onNumberChange }) {
  return (
    <div className="form-grid form-grid-2">
      <Field label="Тип счета" as="div">
        <Segmented
          options={ACCOUNT_TYPE_OPTIONS}
          value={accountType}
          onChange={onTypeChange}
          className="segmented-block"
        />
      </Field>
      <Field label="Номер счета" required hint="Подставляется из карточки работника, можно исправить">
        <input
          className="mono"
          value={accountNumber}
          onChange={(e) => onNumberChange(normalizeKzAccountInput(e.target.value))}
          placeholder="KZ..."
          maxLength={20}
          required
        />
      </Field>
    </div>
  );
}

function SubmitBar({ loading, label = 'Создать заявление' }) {
  return (
    <div className="submit-bar">
      <p>
        <Download size={15} /> После создания документ Word скачается автоматически
      </p>
      <button className="btn btn-primary btn-lg" type="submit" disabled={loading}>
        {loading ? <Spinner size={16} /> : <Check size={17} />} {label}
      </button>
    </div>
  );
}

export default function ApplicationsTab({ user, activeType, onTypeChange }) {
  const { toast } = useFeedback();
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [limits, setLimits] = useState([]);
  const [limitSubdivisionChoices, setLimitSubdivisionChoices] = useState([]);
  const [limitSubdivision, setLimitSubdivision] = useState('energo_ugol');
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
    recipient_account_file: null,
    death_date: '',
    applicant_id_file: null,
    death_certificate_file: null,
  });

  const energougol = isEnergougol(user);

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

  const showResult = (message, isError = false) => {
    if (isError) {
      setError(message);
      setSuccess('');
      toast({ tone: 'error', title: 'Заявление не создано', text: message });
    } else {
      setSuccess(message);
      setError('');
      toast({ title: message, text: 'Документ скачивается' });
    }
  };

  const loadLimits = async () => {
    if (user.is_admin) return;
    try {
      const params = new URLSearchParams();
      if (energougol) {
        params.set('enterprise_subdivision', limitSubdivision);
      }
      const query = params.toString() ? `?${params.toString()}` : '';
      const response = await apiFetch(`/api/v2/vacation-limits/${query}`);
      setLimits(response.limits || []);
      setLimitSubdivisionChoices(response.enterprise_subdivision_choices || []);
    } catch (e) {
      setError(getErrorText(e));
    }
  };

  useEffect(() => {
    loadLimits();
  }, [user.is_admin, limitSubdivision]);

  useEffect(() => {
    if (!materialWorker) return;
    setMaterialData((prev) => {
      const next = { ...prev };
      if (isPensionerStatus(materialWorker.status)) {
        next.assistance_type = 'treatment';
      }
      next.account_number = resolveWorkerAccount(materialWorker, prev.account_type);
      return next;
    });
  }, [materialWorker]);

  useEffect(() => {
    if (!materialWorker) return;
    setMaterialData((prev) => ({
      ...prev,
      account_number: resolveWorkerAccount(materialWorker, prev.account_type),
    }));
  }, [materialData.account_type]);

  useEffect(() => {
    if (!coalWorker) return;
    setCoalData((prev) => ({
      ...prev,
      account_number: resolveWorkerAccount(coalWorker, prev.account_type),
    }));
  }, [coalWorker, coalData.account_type]);

  useEffect(() => {
    if (!funeralWorker) return;
    setFuneralData((prev) => ({
      ...prev,
      account_number: resolveWorkerAccount(funeralWorker, prev.account_type),
    }));
  }, [funeralWorker, funeralData.account_type]);

  useEffect(() => {
    setError('');
    setSuccess('');
  }, [activeType]);

  const materialWorkerIsPensioner = !!materialWorker && isPensionerStatus(materialWorker.status);

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
      if (energougol) {
        fd.append('enterprise_subdivision', limitSubdivision);
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
      loadLimits();
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
      fd.append('assistance_type', materialWorkerIsPensioner ? 'treatment' : materialData.assistance_type);
      fd.append('amount', materialData.amount);
      if (materialWorkerIsPensioner || accountNumber !== 'KZ') {
        fd.append('account_type', materialData.account_type);
        fd.append('account_number', accountNumber);
      }
      if (materialWorkerIsPensioner && materialData.account_file) {
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
      showResult('Выберите работника для заявления на уголь', true);
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
      if (funeralData.recipient_account_file) {
        fd.append('recipient_account_file', funeralData.recipient_account_file);
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
          enterprise_subdivision: energougol ? limitSubdivision : '',
        },
      });
      setError('');
      toast({ title: 'Лимит сохранен' });
      setLimitForm((prev) => ({ ...prev, limit: '' }));
      await loadLimits();
    } catch (e) {
      toast({ tone: 'error', title: 'Лимит не сохранен', text: getErrorText(e) });
    } finally {
      setLoading(false);
    }
  };

  const toggleFamily = (id) => {
    setVacationData((prev) => {
      const current = prev.family_members || [];
      return {
        ...prev,
        family_members: current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
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

  const subdivisionOptions = limitSubdivisionChoices.length ? limitSubdivisionChoices : SUBDIVISION_FALLBACK;
  const typeMeta = APPLICATION_TYPES.find((t) => t.value === activeType) || APPLICATION_TYPES[0];

  return (
    <div className="stack stack-lg">
      <div className="type-picker" role="tablist" aria-label="Вид заявления">
        {APPLICATION_TYPES.map(({ value, label, short, text, icon: Icon, tone }) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={activeType === value}
            className={cn('type-card', activeType === value && 'is-active')}
            onClick={() => onTypeChange(value)}
          >
            <span className={`type-icon tone-${tone}`}>
              <Icon size={22} />
            </span>
            <span className="type-text">
              <strong>
                <span className="type-label-full">{label}</span>
                <span className="type-label-short">{short || label}</span>
              </strong>
              <span className="type-desc">{text}</span>
            </span>
            <span className="type-check">
              <Check size={14} />
            </span>
          </button>
        ))}
      </div>

      <div className="apply-layout">
        <div className="apply-main">
          {error && (
            <Alert tone="error" onClose={() => setError('')}>
              {error}
            </Alert>
          )}
          {success && (
            <Alert tone="success" onClose={() => setSuccess('')}>
              {success}. Документ скачивается, заявление появится в разделе «Отчеты».
            </Alert>
          )}

          {activeType === 'vacation' && (
            <Card title="Заявление на путевку" icon={typeMeta.icon}>
              <form className="steps" onSubmit={submitVacation}>
                <Step number={1} title="Работник">
                  <WorkerLookup onSelect={setVacationWorker} selectedWorker={vacationWorker} />
                </Step>

                <Step number={2} title="Место отдыха и даты">
                  {energougol && (
                    <Field label="Подразделение" hint="Влияет на лимит мест">
                      <select value={limitSubdivision} onChange={(e) => setLimitSubdivision(e.target.value)}>
                        {subdivisionOptions.map((item) => (
                          <option key={item.value} value={item.value}>
                            {item.label}
                          </option>
                        ))}
                      </select>
                    </Field>
                  )}
                  <div className="field">
                    <span className="field-label">Курорт</span>
                    <div className="choice-grid">
                      {RESORT_OPTIONS.map((option) => (
                        <button
                          type="button"
                          key={option.value}
                          className={cn('choice', vacationData.resort === option.value && 'is-active')}
                          onClick={() => {
                            const nextResort = option.value;
                            setVacationData((prev) => ({
                              ...prev,
                              resort: nextResort,
                              seasons: nextResort === 'orlenok' ? prev.seasons : [],
                              custom_price: ['zhartas', 'shakhter'].includes(nextResort) ? prev.custom_price : '',
                              study_certificate_file: nextResort === 'discovery' ? prev.study_certificate_file : null,
                            }));
                          }}
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="form-grid form-grid-2">
                    <Field label="Дата начала" required>
                      <input
                        type="date"
                        value={vacationData.start_date}
                        onChange={(e) => setVacationData((prev) => ({ ...prev, start_date: e.target.value }))}
                        required
                      />
                    </Field>
                    <Field label="Дата окончания" required>
                      <input
                        type="date"
                        value={vacationData.end_date}
                        onChange={(e) => setVacationData((prev) => ({ ...prev, end_date: e.target.value }))}
                        required
                      />
                    </Field>
                  </div>

                  {vacationData.resort === 'orlenok' && (
                    <div className="field">
                      <span className="field-label">Сезоны «Орленка»</span>
                      <div className="chips">
                        {[1, 2, 3, 4].map((season) => (
                          <button
                            type="button"
                            key={season}
                            className={cn('chip', vacationData.seasons.includes(season) && 'is-active')}
                            onClick={() => toggleSeason(season)}
                          >
                            {vacationData.seasons.includes(season) && <Check size={14} />}
                            {season} сезон
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {['zhartas', 'shakhter'].includes(vacationData.resort) && (
                    <Field label="Своя цена (необязательно)" hint="Оставьте пустым — стоимость рассчитается автоматически">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={vacationData.custom_price}
                        onChange={(e) => setVacationData((prev) => ({ ...prev, custom_price: e.target.value }))}
                        placeholder="Автоматический расчет"
                      />
                    </Field>
                  )}
                </Step>

                <Step number={3} title="Кто едет">
                  <Toggle
                    checked={vacationData.worker_goes}
                    onChange={(checked) => setVacationData((prev) => ({ ...prev, worker_goes: checked }))}
                    label="Работник едет сам"
                    description="Выключите, если путевка только для членов семьи"
                  />
                  {vacationWorker ? (
                    vacationWorkerData?.family_members?.length > 0 ? (
                      <div className="field">
                        <span className="field-label">Члены семьи</span>
                        <div className="check-list">
                          {vacationWorkerData.family_members.map((member) => {
                            const checked = vacationData.family_members.includes(member.id);
                            return (
                              <label key={member.id} className={cn('check-item', checked && 'is-checked')}>
                                <input type="checkbox" checked={checked} onChange={() => toggleFamily(member.id)} />
                                <span className="check-box">
                                  <Check size={13} />
                                </span>
                                <span className="check-text">
                                  <strong>{member.full_name}</strong>
                                  <span>{member.relationship}</span>
                                </span>
                              </label>
                            );
                          })}
                        </div>
                      </div>
                    ) : (
                      <p className="muted-note">
                        <Info size={15} /> У работника нет членов семьи в карточке
                      </p>
                    )
                  ) : (
                    <p className="muted-note">
                      <Info size={15} /> Выберите работника, чтобы добавить членов семьи
                    </p>
                  )}
                </Step>

                {vacationData.resort === 'discovery' && (
                  <Step number={4} title="Документы">
                    <FileInput
                      label="Справка об очном обучении"
                      file={vacationData.study_certificate_file}
                      onChange={(file) => setVacationData((prev) => ({ ...prev, study_certificate_file: file }))}
                    />
                  </Step>
                )}

                <SubmitBar loading={loading} />
              </form>
            </Card>
          )}

          {activeType === 'material' && (
            <Card title="Материальная помощь" icon={typeMeta.icon}>
              <form className="steps" onSubmit={submitMaterial}>
                <Step number={1} title="Работник">
                  <WorkerLookup onSelect={setMaterialWorker} selectedWorker={materialWorker} />
                </Step>

                <Step number={2} title="Вид помощи и сумма">
                  <div className="form-grid form-grid-2">
                    <Field
                      label="Вид помощи"
                      hint={materialWorkerIsPensioner ? 'Для пенсионеров — только «На лечение»' : undefined}
                    >
                      <select
                        value={materialWorkerIsPensioner ? 'treatment' : materialData.assistance_type}
                        onChange={(e) => setMaterialData((prev) => ({ ...prev, assistance_type: e.target.value }))}
                        disabled={materialWorkerIsPensioner}
                      >
                        {ASSISTANCE_TYPE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field
                      label="Сумма, ₸"
                      hint={materialWorkerIsPensioner ? 'Для пенсионеров сумма не указывается' : undefined}
                    >
                      <input
                        type="number"
                        step="0.01"
                        value={materialData.amount}
                        onChange={(e) => setMaterialData((prev) => ({ ...prev, amount: e.target.value }))}
                        disabled={materialWorkerIsPensioner}
                        placeholder="0,00"
                      />
                    </Field>
                  </div>
                </Step>

                <Step number={3} title="Счет для выплаты">
                  {materialWorkerIsPensioner ? (
                    <>
                      <AccountFields
                        accountType={materialData.account_type}
                        accountNumber={materialData.account_number}
                        onTypeChange={(v) => setMaterialData((prev) => ({ ...prev, account_type: v }))}
                        onNumberChange={(v) => setMaterialData((prev) => ({ ...prev, account_number: v }))}
                      />
                      <FileInput
                        label="Скан счета"
                        file={materialData.account_file}
                        onChange={(file) => setMaterialData((prev) => ({ ...prev, account_file: file }))}
                      />
                    </>
                  ) : (
                    <p className="muted-note">
                      <Info size={15} /> Для работников счет автоматически берется из карточки работника
                    </p>
                  )}
                </Step>

                <SubmitBar loading={loading} />
              </form>
            </Card>
          )}

          {activeType === 'coal' && (
            <Card title="Заявление на уголь" icon={typeMeta.icon}>
              <form className="steps" onSubmit={submitCoal}>
                <Step number={1} title="Работник">
                  <WorkerLookup onSelect={setCoalWorker} selectedWorker={coalWorker} />
                </Step>

                <Step number={2} title="Счет для выплаты">
                  <AccountFields
                    accountType={coalData.account_type}
                    accountNumber={coalData.account_number}
                    onTypeChange={(v) => setCoalData((prev) => ({ ...prev, account_type: v }))}
                    onNumberChange={(v) => setCoalData((prev) => ({ ...prev, account_number: v }))}
                  />
                </Step>

                <Step number={3} title="Документы">
                  <div className="form-grid form-grid-2">
                    <FileInput
                      label="Скан счета"
                      file={coalData.account_file}
                      onChange={(file) => setCoalData((prev) => ({ ...prev, account_file: file }))}
                    />
                    <FileInput
                      label="Техпаспорт дома"
                      file={coalData.passport_file}
                      onChange={(file) => setCoalData((prev) => ({ ...prev, passport_file: file }))}
                    />
                    <FileInput
                      label="Удостоверение"
                      file={coalData.pensioner_id_file}
                      onChange={(file) => setCoalData((prev) => ({ ...prev, pensioner_id_file: file }))}
                    />
                  </div>
                </Step>

                <SubmitBar loading={loading} />
              </form>
            </Card>
          )}

          {activeType === 'funeral' && (
            <Card title="Заявление на погребение" icon={typeMeta.icon}>
              <form className="steps" onSubmit={submitFuneral}>
                <Step number={1} title="Пенсионер">
                  <WorkerLookup
                    pensionerOnly
                    onSelect={setFuneralWorker}
                    selectedWorker={funeralWorker}
                    hint="Поиск только среди пенсионеров"
                  />
                  <div className="form-grid form-grid-2">
                    <Field label="Дата смерти пенсионера">
                      <input
                        type="date"
                        value={funeralData.death_date}
                        onChange={(e) => setFuneralData((prev) => ({ ...prev, death_date: e.target.value }))}
                      />
                    </Field>
                  </div>
                </Step>

                <Step number={2} title="Заявитель">
                  <div className="form-grid form-grid-2">
                    <Field label="ФИО заявителя" required>
                      <input
                        value={funeralData.applicant_full_name}
                        onChange={(e) => setFuneralData((prev) => ({ ...prev, applicant_full_name: e.target.value }))}
                        required
                      />
                    </Field>
                    <Field label="ИИН заявителя" required>
                      <input
                        value={funeralData.applicant_inn}
                        onChange={(e) => setFuneralData((prev) => ({ ...prev, applicant_inn: e.target.value }))}
                        inputMode="numeric"
                        required
                      />
                    </Field>
                  </div>
                  <AccountFields
                    accountType={funeralData.account_type}
                    accountNumber={funeralData.account_number}
                    onTypeChange={(v) => setFuneralData((prev) => ({ ...prev, account_type: v }))}
                    onNumberChange={(v) => setFuneralData((prev) => ({ ...prev, account_number: v }))}
                  />
                </Step>

                <Step number={3} title="Документы">
                  <div className="form-grid form-grid-2">
                    <FileInput
                      label="Скан счета"
                      file={funeralData.account_file}
                      onChange={(file) => setFuneralData((prev) => ({ ...prev, account_file: file }))}
                    />
                    <FileInput
                      label="Номер счета получателя (скан)"
                      file={funeralData.recipient_account_file}
                      onChange={(file) => setFuneralData((prev) => ({ ...prev, recipient_account_file: file }))}
                    />
                    <FileInput
                      label="Удостоверение заявителя"
                      file={funeralData.applicant_id_file}
                      onChange={(file) => setFuneralData((prev) => ({ ...prev, applicant_id_file: file }))}
                    />
                    <FileInput
                      label="Справка о смерти"
                      file={funeralData.death_certificate_file}
                      onChange={(file) => setFuneralData((prev) => ({ ...prev, death_certificate_file: file }))}
                    />
                  </div>
                </Step>

                <SubmitBar loading={loading} />
              </form>
            </Card>
          )}
        </div>

        <aside className="apply-side">
          {!user.is_admin && activeType === 'vacation' && (
            <Card
              title="Лимиты путевок"
              subtitle={
                limits[0]?.period_start_human
                  ? `Период с ${limits[0].period_start_human}${
                      energougol ? `, ${subdivisionOptions.find((s) => s.value === limitSubdivision)?.label || ''}` : ''
                    }`
                  : 'Жартас и Шахтер, в койко-днях'
              }
            >
              <p className="limit-note">Койко-день — 1 человек на 1 день. Путевка на 3 человек на 12 дней = 36.</p>
              <div className="limit-list">
                {limits.length === 0 && <p className="muted">Лимиты еще не заданы</p>}
                {limits.map((item) => {
                  const pct = item.limit ? Math.min(100, Math.round((item.used / item.limit) * 100)) : 0;
                  return (
                    <div className="limit-item" key={item.resort}>
                      <div className="limit-row">
                        <strong>{item.resort_display}</strong>
                        <span>
                          <b>{item.remaining}</b> из {item.limit} свободно
                        </span>
                      </div>
                      <div className="progress">
                        <span className={cn(pct >= 90 && 'is-danger', pct >= 70 && pct < 90 && 'is-warn')} style={{ width: `${pct}%` }} />
                      </div>
                      <div className="limit-foot">Использовано: {item.used} койко-дн.</div>
                    </div>
                  );
                })}
              </div>

              <details className="limit-details">
                <summary>Увеличить лимит</summary>
              <form className="limit-form" onSubmit={submitLimit}>
                <div className="limit-form-row">
                  <select
                    value={limitForm.resort}
                    onChange={(e) => setLimitForm((prev) => ({ ...prev, resort: e.target.value }))}
                    aria-label="Курорт"
                  >
                    <option value="zhartas">Жартас</option>
                    <option value="shakhter">Шахтер</option>
                  </select>
                  <input
                    type="number"
                    min="0"
                    value={limitForm.limit}
                    onChange={(e) => setLimitForm((prev) => ({ ...prev, limit: e.target.value }))}
                    placeholder="Новый лимит"
                    aria-label="Новый лимит"
                    required
                  />
                </div>
                <button className="btn btn-secondary btn-block" type="submit" disabled={loading}>
                  {loading ? <Spinner size={15} /> : <Check size={15} />} Сохранить лимит
                </button>
              </form>
              </details>
            </Card>
          )}

          <Card title="Как это работает" className="how-card">
            <ol className="how-list">
              <li>
                <span>1</span>Найдите работника по ФИО или табельному номеру
              </li>
              <li>
                <span>2</span>Заполните данные и прикрепите сканы документов
              </li>
              <li>
                <span>3</span>Нажмите «Создать» — документ Word скачается сам
              </li>
            </ol>
            <div className="how-foot">
              <FileStack size={15} /> Созданные заявления можно найти и исправить в разделе «Отчеты»
            </div>
          </Card>
        </aside>
      </div>
    </div>
  );
}
