import React, { useEffect, useState } from 'react';
import { BedDouble, CalendarRange, FileSpreadsheet, Ticket, Wallet } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { WORKER_CATEGORY_OPTIONS, cn, formatMoney, getErrorText, pluralRu, useIsMobile } from '../lib/utils';
import { Alert, Badge, Card, EmptyState, Field, Segmented, SkeletonRows } from '../components/ui';

export default function StatementsTab() {
  const isMobile = useIsMobile();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState(null);
  const [periodStart, setPeriodStart] = useState('');
  const [rangeMode, setRangeMode] = useState('period');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [appliedRange, setAppliedRange] = useState(null);
  const [workerCategory, setWorkerCategory] = useState('all');

  // Ведомость за месяц (period_start) или за свои даты (start_date/end_date), с фильтром по категории.
  const load = async ({ period = periodStart, range = appliedRange, category = workerCategory } = {}) => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      if (range) {
        params.set('start_date', range.from);
        params.set('end_date', range.to);
      } else if (period) {
        params.set('period_start', period);
      }
      if (category !== 'all') params.set('worker_category', category);
      const query = params.toString() ? `?${params.toString()}` : '';
      const response = await apiFetch(`/api/v2/statements/${query}`);
      setData(response);
      if (!range && !period && response.all_periods?.length > 0) {
        setPeriodStart(response.all_periods[0].period_start);
      }
    } catch (e) {
      setError(getErrorText(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load({ period: '' });
  }, []);

  const choosePeriod = (value) => {
    setPeriodStart(value);
    setAppliedRange(null);
    load({ period: value, range: null });
  };

  const switchRangeMode = (mode) => {
    setRangeMode(mode);
    if (mode === 'period' && appliedRange) {
      setAppliedRange(null);
      load({ range: null });
    }
  };

  const applyDates = () => {
    if (!dateFrom || !dateTo) {
      setError('Для своего периода укажите обе даты');
      return;
    }
    const range = dateFrom <= dateTo ? { from: dateFrom, to: dateTo } : { from: dateTo, to: dateFrom };
    setAppliedRange(range);
    load({ range });
  };

  const chooseCategory = (value) => {
    setWorkerCategory(value);
    load({ category: value });
  };

  const renderSection = (title, section) => {
    const rows = section?.rows || [];
    const showOwner = rows.some((row) => row.user_account);
    const vouchers = rows.reduce((sum, row) => sum + (Number(row.vouchers_count) || 0), 0);
    const bedDays = rows.reduce((sum, row) => sum + (Number(row.bed_days) || 0), 0);

    return (
      <Card
        key={title}
        flush
        title={title}
        subtitle={
          <Badge tone={section?.status?.code === 'active' ? 'green' : 'gray'} dot>
            {section?.status?.label || '—'}
          </Badge>
        }
        actions={
          <a className="btn btn-secondary" href={section?.excel_url} target="_blank" rel="noreferrer">
            <FileSpreadsheet size={16} /> Скачать Excel
          </a>
        }
      >
        <div className="summary-strip">
          <div>
            <Ticket size={16} />
            <span>Путевок</span>
            <strong>{vouchers}</strong>
          </div>
          <div>
            <BedDouble size={16} />
            <span>Койко-дней</span>
            <strong>{bedDays}</strong>
          </div>
          <div>
            <Wallet size={16} />
            <span>Итого</span>
            <strong>{formatMoney(section?.total_sum)} ₸</strong>
          </div>
        </div>
        {rows.length === 0 ? (
          <EmptyState compact title="За период записей нет" text="Путевки с датой начала в этом периоде появятся здесь." />
        ) : isMobile ? (
          <ul className="statement-list">
            {rows.map((row) => (
              <li key={`${title}-${row.number}-${row.vacation_id}`}>
                <span className="statement-num">{row.number}</span>
                <div className="statement-main">
                  <strong>{row.full_name}</strong>
                  <span>
                    Таб. № {row.personnel_number || '—'}, ИИН {row.inn || '—'}
                    {row.user_account ? `, ${row.user_account}` : ''}
                  </span>
                  <span>
                    {row.vouchers_count} {pluralRu(Number(row.vouchers_count) || 0, 'путевка', 'путевки', 'путевок')} ,{' '}
                    {row.bed_days} койко-дн.
                  </span>
                </div>
                <strong className="statement-sum">{formatMoney(row.price)}</strong>
              </li>
            ))}
          </ul>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="col-num">№</th>
                  <th>ФИО</th>
                  {showOwner && <th>Предприятие</th>}
                  <th>Таб. №</th>
                  <th>ИИН</th>
                  <th className="num">Путевок</th>
                  <th className="num">Койко-дни</th>
                  <th className="num">Сумма, ₸</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={`${title}-${row.number}-${row.vacation_id}`}>
                    <td className="col-num muted">{row.number}</td>
                    <td>
                      <strong className="cell-strong">{row.full_name}</strong>
                    </td>
                    {showOwner && <td>{row.user_account || '—'}</td>}
                    <td className="tnum">{row.personnel_number || '—'}</td>
                    <td className="tnum">{row.inn || '—'}</td>
                    <td className="num">{row.vouchers_count}</td>
                    <td className="num">{row.bed_days}</td>
                    <td className="num">{formatMoney(row.price)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={showOwner ? 5 : 4}>Итого</td>
                  <td className="num">{vouchers}</td>
                  <td className="num">{bedDays}</td>
                  <td className="num">{formatMoney(section?.total_sum)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </Card>
    );
  };

  return (
    <div className="stack">
      {error && <Alert tone="error">{error}</Alert>}

      <Card className="filter-card">
        {data?.custom_range && (
          <div className="filter-row">
            <div className="period-display">
              <div>
                <span>Свой период</span>
                <strong>{`${data.period_start_human} — ${data.period_end_human}`}</strong>
              </div>
            </div>
          </div>
        )}
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
                <select value={periodStart} onChange={(e) => choosePeriod(e.target.value)} aria-label="Период">
                  {(data?.all_periods || []).map((p) => (
                    <option key={p.period_start} value={p.period_start}>
                      {p.label}
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
          <Field label="Категория" hint="Ведомость и Excel будут только с выбранными">
            <select value={workerCategory} onChange={(e) => chooseCategory(e.target.value)}>
              {WORKER_CATEGORY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>
        </div>
      </Card>

      {loading && !data ? (
        <Card flush>
          <SkeletonRows rows={5} cols={5} />
        </Card>
      ) : (
        data && (
          <div className={cn('stack', loading && 'is-loading')}>
            {renderSection('Санаторий «Жартас»', data.zhartas)}
            {renderSection('Дом отдыха «Шахтер»', data.shakhter)}
          </div>
        )
      )}
    </div>
  );
}
