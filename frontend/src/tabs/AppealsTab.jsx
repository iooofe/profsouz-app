import React, { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Download, MessageSquare, Search, UserRound, X } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { getErrorText, initials, pluralRu, requestStatusTone, useDebounce, workerStatusTone } from '../lib/utils';
import { REQUEST_TYPE_META } from '../lib/requestTypes';
import { Alert, Badge, Card, EmptyState, IconButton, LoadingBlock } from '../components/ui';

export default function AppealsTab() {
  const [search, setSearch] = useState('');
  const [year, setYear] = useState(String(new Date().getFullYear()));
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const debouncedSearch = useDebounce(search, 250);

  useEffect(() => {
    // Ответ на устаревший запрос (пользователь уже ввел другой текст/год) игнорируем.
    let active = true;
    const run = async () => {
      if (debouncedSearch.trim().length < 2) {
        setRows([]);
        setLoading(false);
        return;
      }
      setLoading(true);
      setError('');
      try {
        const response = await apiFetch(
          `/api/v2/appeals/?search=${encodeURIComponent(debouncedSearch.trim())}&year=${encodeURIComponent(year)}`
        );
        if (active) setRows(response.results || []);
      } catch (e) {
        if (active) setError(getErrorText(e));
      } finally {
        if (active) setLoading(false);
      }
    };
    run();
    return () => {
      active = false;
    };
  }, [debouncedSearch, year]);

  const shiftYear = (delta) => setYear((prev) => String((Number(prev) || new Date().getFullYear()) + delta));
  const tooShort = debouncedSearch.trim().length < 2;

  return (
    <div className="stack">
      <Card className="filter-card">
        <div className="filter-row">
          <div className="search-field search-lg">
            <Search size={17} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="ФИО, табельный номер или ИИН работника"
              autoFocus
            />
            {search && (
              <button type="button" className="search-clear" onClick={() => setSearch('')} aria-label="Очистить поиск">
                <X size={15} />
              </button>
            )}
          </div>
          <div className="year-picker" aria-label="Год">
            <IconButton icon={ChevronLeft} label="Предыдущий год" onClick={() => shiftYear(-1)} />
            <input
              type="number"
              min="2000"
              max="2100"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              aria-label="Год"
            />
            <IconButton icon={ChevronRight} label="Следующий год" onClick={() => shiftYear(1)} />
          </div>
        </div>
      </Card>

      {error && <Alert tone="error">{error}</Alert>}

      {loading ? (
        <Card>
          <LoadingBlock label="Ищем обращения..." />
        </Card>
      ) : tooShort ? (
        <Card>
          <EmptyState
            icon={MessageSquare}
            title="Найдите работника"
            text="Введите минимум 2 символа — покажем все его обращения за выбранный год."
          />
        </Card>
      ) : rows.length === 0 ? (
        <Card>
          <EmptyState icon={UserRound} title="Никого не нашли" text="Проверьте написание ФИО или табельный номер." />
        </Card>
      ) : (
        <div className="appeal-list">
          {rows.map((item) => (
            <Card key={item.worker.id} flush>
              <div className="appeal-head">
                <span className="avatar avatar-md">{initials(item.worker.full_name)}</span>
                <div className="appeal-head-text">
                  <strong>{item.worker.full_name}</strong>
                  <span>
                    Таб. № {item.worker.personnel_number || '—'}
                    {item.worker.department ? ` · ${item.worker.department}` : ''}
                    {item.worker.user_account ? ` · ${item.worker.user_account}` : ''}
                  </span>
                </div>
                {item.worker.status_display && (
                  <Badge tone={workerStatusTone(item.worker.status)}>{item.worker.status_display}</Badge>
                )}
                <div className="appeal-count">
                  <strong>{item.appeals_count}</strong>
                  <span>
                    {pluralRu(item.appeals_count, 'обращение', 'обращения', 'обращений')} за {year}
                  </span>
                </div>
              </div>
              {item.appeals_count ? (
                <ul className="appeal-items">
                  {(item.appeals || []).map((appeal) => {
                    const meta = REQUEST_TYPE_META[appeal.type];
                    const Icon = meta?.icon;
                    return (
                      <li key={`${item.worker.id}-${appeal.type}-${appeal.id}`}>
                        {Icon && (
                          <span className={`type-tag-icon tone-${meta.tone}`}>
                            <Icon size={15} />
                          </span>
                        )}
                        <span className="appeal-type">{meta?.label || appeal.type}</span>
                        <span className="appeal-date num">{appeal.created_at || '—'}</span>
                        <Badge tone={requestStatusTone(appeal.status)} dot>
                          {appeal.status_text || '—'}
                        </Badge>
                        {appeal.download_url ? (
                          <IconButton icon={Download} label="Скачать документ" href={appeal.download_url} />
                        ) : (
                          <span className="icon-btn-placeholder" />
                        )}
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <div className="appeal-empty">За {year} год обращений нет</div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
