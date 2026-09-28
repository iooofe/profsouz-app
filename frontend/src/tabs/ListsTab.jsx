import React, { useEffect, useMemo, useState } from 'react';
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Award,
  CalendarRange,
  ClipboardList,
  FileSpreadsheet,
  Flame,
  Flower2,
  HandCoins,
  Check,
  Search,
  SlidersHorizontal,
  X,
} from 'lucide-react';
import { apiFetch } from '../lib/api';
import { cn, formatCount, getErrorText, pluralRu, useIsMobile } from '../lib/utils';
import { Alert, Badge, Card, EmptyState, Field, Segmented, SkeletonRows, Spinner } from '../components/ui';

const LIST_CONFIGS = {
  coal: {
    label: 'Компенсация за уголь',
    short: 'Уголь',
    icon: Flame,
    endpoint: '/coal-compensation/list/',
    rowsKey: 'compensation_data',
    excel: '/coal-compensation/excel/',
  },
  bonus: {
    label: 'Доплата за 3 степени',
    short: 'Доплата 3 ст.',
    icon: Award,
    endpoint: '/bonus-payment/list/',
    rowsKey: 'bonus_data',
    excel: '/bonus-payment/excel/',
  },
  funeral: {
    label: 'Ритуальные услуги',
    short: 'Ритуальные',
    icon: Flower2,
    endpoint: '/funeral-services/list/',
    rowsKey: 'funeral_data',
    excel: '/funeral-services/excel/',
  },
  pensioner: {
    label: 'Матпомощь пенсионерам',
    short: 'Пенсионерам',
    icon: HandCoins,
    endpoint: '/pensioner-material-assistance/list/',
    rowsKey: 'assistance_data',
    excel: '/pensioner-material-assistance/excel/',
  },
  registry: {
    label: 'Реестр матпомощи',
    short: 'Реестр',
    icon: ClipboardList,
    endpoint: '/material-assistance/registry/list/',
    rowsKey: 'registry_data',
    excel: '/material-assistance/registry/excel/',
  },
};

const MONEY_FIELDS = new Set(['accrued', 'ipn', 'to_pay', 'amount']);

function formatPeriodLabel(value) {
  const match = /^(\d{4})-(\d{2})-\d{2}$/.exec(String(value || ''));
  if (!match) return value;
  const label = new Date(Number(match[1]), Number(match[2]) - 1, 1).toLocaleDateString('ru-RU', {
    month: 'long',
    year: 'numeric',
  });
  return (label.charAt(0).toUpperCase() + label.slice(1)).replace(/\s*г\.?$/, '');
}

export default function ListsTab({ user, references }) {
  const listConfigs = LIST_CONFIGS;
  const isMobile = useIsMobile();
  const [filtersOpen, setFiltersOpen] = useState(false);

  const [active, setActive] = useState('coal');
  const [period, setPeriod] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [rangeMode, setRangeMode] = useState('period');
  const [enterpriseFilter, setEnterpriseFilter] = useState('all');
  const [workerCategory, setWorkerCategory] = useState('all');
  const [accountTypeFilter, setAccountTypeFilter] = useState('all');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [listSearch, setListSearch] = useState('');
  const [sortField, setSortField] = useState('number');
  const [sortDirection, setSortDirection] = useState('asc');

  const load = async ({
    targetList = active,
    targetPeriod = period,
    targetDateFrom = dateFrom,
    targetDateTo = dateTo,
  } = {}) => {
    setLoading(true);
    setError('');

    try {
      const conf = listConfigs[targetList];
      const params = new URLSearchParams();
      if (targetDateFrom && targetDateTo) {
        params.set('start_date', targetDateFrom);
        params.set('end_date', targetDateTo);
      } else if (targetPeriod) {
        params.set('period_start', targetPeriod);
      }
      if (user.is_admin && enterpriseFilter !== 'all') {
        params.set('user_id', enterpriseFilter);
      }
      if (workerCategory !== 'all') {
        params.set('worker_category', workerCategory);
      }
      if (accountTypeFilter !== 'all') {
        params.set('account_type_filter', accountTypeFilter);
      }
      const query = params.toString() ? `?${params.toString()}` : '';
      const response = await apiFetch(`${conf.endpoint}${query}`);
      setData(response);
      if (!targetPeriod && !targetDateFrom && !targetDateTo && response.all_periods?.length > 0) {
        setPeriod(response.all_periods[0]);
      }
    } catch (e) {
      setError(getErrorText(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load({ targetList: active });
  }, [active, enterpriseFilter, workerCategory, accountTypeFilter]);

  useEffect(() => {
    if (period && !dateFrom && !dateTo) {
      load({ targetList: active, targetPeriod: period });
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
        fd.append('period_start', dateFrom || period);
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

      await load();
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
      await load();
    } catch (e) {
      setError(getErrorText(e));
    }
  };

  const renderValue = (row, field) => {
    const value = row[field];
    if (typeof value === 'boolean') {
      return (
        <Badge tone={value ? 'green' : 'gray'} dot>
          {value ? 'Да' : 'Нет'}
        </Badge>
      );
    }
    if (field === 'status_text' && value) {
      return <Badge tone="gray">{value}</Badge>;
    }
    return value || <span className="muted">—</span>;
  };

  const renderCell = (row, field) => {
    if (!user.is_admin) return renderValue(row, field);

    const editableFields = {
      coal: ['accrued', 'ipn', 'to_pay'],
      bonus: ['accrued', 'ipn', 'to_pay'],
      funeral: ['to_pay'],
      pensioner: ['accrued', 'ipn', 'to_pay'],
    };

    if (!editableFields[active] || !editableFields[active].includes(field)) {
      return renderValue(row, field);
    }

    return (
      <input
        className="table-input"
        defaultValue={row[field] || ''}
        onBlur={(e) => {
          if (e.target.value !== String(row[field] || '')) savePaymentField(row, field, e.target.value);
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') e.currentTarget.blur();
        }}
        inputMode="decimal"
        placeholder="0"
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
    if (dateFrom && dateTo) {
      params.set('start_date', dateFrom);
      params.set('end_date', dateTo);
    } else if (period) {
      params.set('period_start', period);
    }
    if (user.is_admin && enterpriseFilter !== 'all') {
      params.set('user_id', enterpriseFilter);
    }
    if (workerCategory !== 'all') {
      params.set('worker_category', workerCategory);
    }
    if (accountTypeFilter !== 'all') {
      params.set('account_type_filter', accountTypeFilter);
    }
    if (!params.toString()) return baseUrl;
    const separator = baseUrl.includes('?') ? '&' : '?';
    return `${baseUrl}${separator}${params.toString()}`;
  };

  const switchList = (key) => {
    setActive(key);
    setPeriod('');
    setDateFrom('');
    setDateTo('');
    setRangeMode('period');
    setListSearch('');
    setSortField('number');
    setSortDirection('asc');
  };

  const switchRangeMode = (mode) => {
    setRangeMode(mode);
    if (mode === 'period' && (dateFrom || dateTo)) {
      setDateFrom('');
      setDateTo('');
      load({ targetList: active, targetPeriod: period, targetDateFrom: '', targetDateTo: '' });
    }
  };

  const applyDates = () => {
    if (!dateFrom || !dateTo) {
      setError('Для произвольного периода укажите обе даты');
      return;
    }
    setPeriod('');
    load({ targetList: active, targetPeriod: '', targetDateFrom: dateFrom, targetDateTo: dateTo });
  };

  const conf = listConfigs[active];
  const extraFilterCount =
    (workerCategory !== 'all' ? 1 : 0) +
    (accountTypeFilter !== 'all' ? 1 : 0) +
    (user.is_admin && enterpriseFilter !== 'all' ? 1 : 0);
  const titleField = columns.some(([, field]) => field === 'full_name') ? 'full_name' : 'applicant_full_name';
  const moneyColumns = columns.filter(([, field]) => MONEY_FIELDS.has(field));
  const metaColumns = columns.filter(
    ([, field]) => !MONEY_FIELDS.has(field) && !['number', titleField, 'is_issued', 'status_text'].includes(field)
  );
  const colCount = columns.length + (hasIssuedColumn ? 1 : 0) + (showEnterpriseColumn ? 1 : 0);

  return (
    <div className="stack">
      <Segmented
        className="segmented-scroll segmented-tabs"
        options={Object.entries(listConfigs).map(([key, item]) => ({ value: key, label: item.label, icon: item.icon }))}
        value={active}
        onChange={switchList}
      />

      <Card className="filter-card">
        <div className="filter-grid">
          <div className="field">
            <span className="field-label">Период</span>
            <div className="period-control">
              <Segmented
                size="sm"
                options={[
                  { value: 'period', label: 'Месяц' },
                  { value: 'range', label: 'Свои даты' },
                ]}
                value={rangeMode}
                onChange={switchRangeMode}
              />
              {rangeMode === 'period' ? (
                <select
                  value={period}
                  onChange={(e) => {
                    setDateFrom('');
                    setDateTo('');
                    setPeriod(e.target.value);
                  }}
                  aria-label="Период"
                >
                  {(data?.all_periods || []).map((p) => (
                    <option key={p} value={p}>
                      {formatPeriodLabel(p)}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="date-range">
                  <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} aria-label="Дата начала" />
                  <span>—</span>
                  <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} aria-label="Дата окончания" />
                  <button className="btn btn-secondary" type="button" onClick={applyDates}>
                    Применить
                  </button>
                </div>
              )}
            </div>
          </div>

          {isMobile && (
            <button
              type="button"
              className={cn('btn btn-secondary btn-block filter-more', filtersOpen && 'is-open')}
              onClick={() => setFiltersOpen((v) => !v)}
              aria-expanded={filtersOpen}
            >
              <SlidersHorizontal size={17} /> {filtersOpen ? 'Скрыть фильтры' : 'Категория, счет, предприятие'}
              {extraFilterCount > 0 && <span className="filter-count">{extraFilterCount}</span>}
            </button>
          )}

          <Field label="Категория" className={cn(isMobile && !filtersOpen && 'is-hidden')}>
            <select value={workerCategory} onChange={(e) => setWorkerCategory(e.target.value)}>
              <option value="all">Все</option>
              <option value="workers">Работники</option>
              <option value="pensioners">Пенсионеры</option>
              <option value="regress">Регресс</option>
            </select>
          </Field>

          <Field label="Тип счета" className={cn(isMobile && !filtersOpen && 'is-hidden')}>
            <select value={accountTypeFilter} onChange={(e) => setAccountTypeFilter(e.target.value)}>
              <option value="all">Все</option>
              <option value="20_digit">Карточный</option>
              <option value="current">Текущий</option>
            </select>
          </Field>

          {user.is_admin && (
            <Field label="Предприятие" className={cn(isMobile && !filtersOpen && 'is-hidden')}>
              <select value={enterpriseFilter} onChange={(e) => setEnterpriseFilter(e.target.value)}>
                <option value="all">Все предприятия (общий)</option>
                {(references?.users || []).map((item) => (
                  <option key={item.id} value={String(item.id)}>
                    {item.username}
                  </option>
                ))}
              </select>
            </Field>
          )}
        </div>
      </Card>

      {error && (
        <Alert tone="error" onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      <Card flush>
        <div className="list-head">
          <div className="list-head-main">
            <h3>{conf.label}</h3>
            <div className="list-meta">
              <span>
                <CalendarRange size={14} /> {data?.period_start || '—'} — {data?.period_end || '—'}
              </span>
              {data?.status_display && (
                <Badge tone={/вед/i.test(data.status_display) ? 'green' : 'gray'} dot>
                  {data.status_display}
                </Badge>
              )}
              {typeof data?.unissued_count === 'number' && typeof data?.total_count === 'number' && (
                <Badge tone={data.unissued_count ? 'amber' : 'green'}>
                  Не выдано: {data.unissued_count} из {data.total_count}
                </Badge>
              )}
              <span className="muted">
                {loading ? (
                  <Spinner size={14} />
                ) : (
                  `${formatCount(visibleRows.length)} ${pluralRu(visibleRows.length, 'запись', 'записи', 'записей')}`
                )}
              </span>
            </div>
          </div>
          <div className="list-head-actions">
            <div className="search-field">
              <Search size={16} />
              <input value={listSearch} onChange={(e) => setListSearch(e.target.value)} placeholder="Поиск в списке" />
              {listSearch && (
                <button type="button" className="search-clear" onClick={() => setListSearch('')} aria-label="Очистить поиск">
                  <X size={15} />
                </button>
              )}
            </div>
            <a className="btn btn-primary" href={buildExcelUrl(conf.excel)} target="_blank" rel="noreferrer">
              <FileSpreadsheet size={16} /> Excel
            </a>
          </div>
        </div>

        {user.is_admin && active !== 'registry' && (
          <div className="list-hint">Суммы можно править прямо в таблице — изменения сохраняются при выходе из ячейки.</div>
        )}

        {loading && !data ? (
          <SkeletonRows rows={6} cols={7} />
        ) : isMobile ? (
          <div className={cn('m-cards', loading && 'is-loading')}>
            {visibleRows.map((row, index) => (
              <section
                key={`${active}-${index}-${row.number || row.id || index}`}
                className={cn('pay-card', hasIssuedColumn && row.is_issued && 'is-done')}
              >
                <div className="pay-card-head">
                  <span className="pay-card-num">{row.number}</span>
                  <strong className="pay-card-title">{row[titleField] || '—'}</strong>
                  {hasIssuedColumn && (
                    <button
                      type="button"
                      className={cn('issued-btn', row.is_issued && 'is-on')}
                      aria-pressed={!!row.is_issued}
                      onClick={() => toggleIssued(row, !row.is_issued)}
                    >
                      {row.is_issued && <Check size={15} />}
                      {row.is_issued ? 'Выдано' : 'Выдать'}
                    </button>
                  )}
                </div>
                <dl className="pay-card-meta">
                  {metaColumns.map(([title, field]) => (
                    <div key={field}>
                      <dt>{title}</dt>
                      <dd className={cn(field === 'account_number' && 'mono')}>{renderValue(row, field)}</dd>
                    </div>
                  ))}
                  {columns.some(([, field]) => field === 'status_text') && (
                    <div>
                      <dt>Статус</dt>
                      <dd>{renderValue(row, 'status_text')}</dd>
                    </div>
                  )}
                  {columns.some(([, field]) => field === 'is_issued') && !hasIssuedColumn && (
                    <div>
                      <dt>Выдано</dt>
                      <dd>{renderValue(row, 'is_issued')}</dd>
                    </div>
                  )}
                  {showEnterpriseColumn && (
                    <div>
                      <dt>Предприятие</dt>
                      <dd>{row.user_account || '—'}</dd>
                    </div>
                  )}
                </dl>
                {moneyColumns.length > 0 && (
                  <div className="pay-card-money" style={{ gridTemplateColumns: `repeat(${moneyColumns.length}, minmax(0, 1fr))` }}>
                    {moneyColumns.map(([title, field]) => (
                      <label key={field} className="pay-money">
                        <span>{title}</span>
                        <span className="pay-money-value">{renderCell(row, field)}</span>
                      </label>
                    ))}
                  </div>
                )}
              </section>
            ))}
            {visibleRows.length === 0 && (
              <EmptyState
                compact
                icon={listSearch.trim() ? Search : conf.icon}
                title={listSearch.trim() ? 'По запросу ничего не найдено' : 'За период записей нет'}
                text={listSearch.trim() ? undefined : 'Попробуйте выбрать другой период или фильтры.'}
              />
            )}
          </div>
        ) : (
          <div className={cn('table-wrap', loading && 'is-loading')}>
            <table className="data-table table-compact">
              <thead>
                <tr>
                  {columns.map(([title, field]) => {
                    const activeSort = sortField === field;
                    const SortIcon = activeSort ? (sortDirection === 'asc' ? ArrowUp : ArrowDown) : ArrowUpDown;
                    return (
                      <th
                        key={field}
                        className={cn('sortable-th', activeSort && 'is-sorted', MONEY_FIELDS.has(field) && 'num')}
                        onClick={() => onSortClick(field)}
                        aria-sort={activeSort ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
                      >
                        <span className="th-inner">
                          {title}
                          <SortIcon size={13} className="th-sort" />
                        </span>
                      </th>
                    );
                  })}
                  {hasIssuedColumn && <th className="col-center">Выдано</th>}
                  {showEnterpriseColumn && <th>Предприятие</th>}
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row, index) => (
                  <tr key={`${active}-${index}-${row.number || row.id || index}`} className={cn(row.is_issued && hasIssuedColumn && 'row-done')}>
                    {columns.map(([, field]) => (
                      <td
                        key={field}
                        className={cn(
                          MONEY_FIELDS.has(field) && 'num',
                          field === 'account_number' && 'mono',
                          field === 'number' && 'col-num muted',
                          (field === 'full_name' || field === 'applicant_full_name') && 'cell-strong'
                        )}
                      >
                        {renderCell(row, field)}
                      </td>
                    ))}
                    {hasIssuedColumn && (
                      <td className="col-center">
                        <label className="issued-check" title={row.is_issued ? 'Выдано' : 'Не выдано'}>
                          <input
                            type="checkbox"
                            checked={!!row.is_issued}
                            onChange={(e) => toggleIssued(row, e.target.checked)}
                          />
                          <span />
                        </label>
                      </td>
                    )}
                    {showEnterpriseColumn && <td>{row.user_account || <span className="muted">—</span>}</td>}
                  </tr>
                ))}
                {visibleRows.length === 0 && (
                  <tr>
                    <td colSpan={colCount} className="empty-cell">
                      <EmptyState
                        compact
                        icon={listSearch.trim() ? Search : conf.icon}
                        title={listSearch.trim() ? 'По запросу ничего не найдено' : 'За период записей нет'}
                        text={listSearch.trim() ? undefined : 'Попробуйте выбрать другой период или фильтры.'}
                      />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
