import React, { useEffect, useState } from 'react';
import { BedDouble, CalendarRange, FileSpreadsheet, Ticket, Wallet } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { cn, formatMoney, getErrorText, pluralRu, useIsMobile } from '../lib/utils';
import { Alert, Badge, Card, EmptyState, SkeletonRows } from '../components/ui';

export default function StatementsTab() {
  const isMobile = useIsMobile();
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
                    Таб. № {row.personnel_number || '—'}
                    {row.user_account ? ` · ${row.user_account}` : ''}
                  </span>
                  <span>
                    {row.vouchers_count} {pluralRu(Number(row.vouchers_count) || 0, 'путевка', 'путевки', 'путевок')} ·{' '}
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
                    <td className="num">{row.vouchers_count}</td>
                    <td className="num">{row.bed_days}</td>
                    <td className="num">{formatMoney(row.price)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={showOwner ? 4 : 3}>Итого</td>
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
        <div className="filter-row">
          <div className="period-display">
            <span className="period-icon">
              <CalendarRange size={20} />
            </span>
            <div>
              <span>Период ведомостей</span>
              <strong>{data ? `${data.period_start_human} — ${data.period_end_human}` : '—'}</strong>
            </div>
          </div>
          <label className="field field-inline">
            <span className="field-label">Выбрать период</span>
            <select value={periodStart} onChange={(e) => setPeriodStart(e.target.value)}>
              {(data?.all_periods || []).map((p) => (
                <option key={p.period_start} value={p.period_start}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
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
