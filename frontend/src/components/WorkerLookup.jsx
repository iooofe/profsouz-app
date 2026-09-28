import React, { useEffect, useRef, useState } from 'react';
import { Search, UserRound, X } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { initials, isPensionerStatus, useDebounce, workerStatusTone } from '../lib/utils';
import { Badge, Spinner } from './ui';

export default function WorkerLookup({ label, pensionerOnly = false, onSelect, selectedWorker, hint }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const debounced = useDebounce(query, 250);
  const wrapRef = useRef(null);

  useEffect(() => {
    if (debounced.trim().length < 2) {
      setResults([]);
      setSearched(false);
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
          setSearched(true);
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

  useEffect(() => {
    const onDocClick = (event) => {
      if (wrapRef.current && !wrapRef.current.contains(event.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  return (
    <div className="field lookup" ref={wrapRef}>
      {label && <span className="field-label">{label}</span>}
      {selectedWorker ? (
        <div className="selected-worker">
          <span className="avatar avatar-md">{initials(selectedWorker.full_name)}</span>
          <div className="selected-worker-text">
            <strong>{selectedWorker.full_name}</strong>
            <span>
              Таб. № {selectedWorker.personnel_number || '—'}
              {selectedWorker.department ? ` · ${selectedWorker.department}` : ''}
            </span>
          </div>
          {selectedWorker.status_display && (
            <Badge tone={workerStatusTone(selectedWorker.status)}>{selectedWorker.status_display}</Badge>
          )}
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => onSelect(null)}>
            <X size={14} /> Изменить
          </button>
        </div>
      ) : (
        <>
          <div className="search-field">
            <Search size={16} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => results.length && setOpen(true)}
              placeholder={pensionerOnly ? 'ФИО или табельный номер пенсионера' : 'ФИО или табельный номер'}
            />
            {loading && <Spinner size={15} />}
          </div>
          {hint && <span className="field-hint">{hint}</span>}
          {open && searched && (
            <div className="lookup-list">
              {results.length === 0 ? (
                <div className="lookup-empty">
                  <UserRound size={16} /> Никого не нашли по запросу «{debounced}»
                </div>
              ) : (
                results.map((worker) => (
                  <button
                    type="button"
                    key={worker.id}
                    className="lookup-item"
                    onClick={() => {
                      onSelect(worker);
                      setOpen(false);
                      setQuery('');
                    }}
                  >
                    <span className="avatar avatar-sm">{initials(worker.full_name)}</span>
                    <span className="lookup-item-text">
                      <strong>{worker.full_name}</strong>
                      <span>
                        Таб. № {worker.personnel_number || '—'}
                        {worker.department ? ` · ${worker.department}` : ''}
                      </span>
                    </span>
                    {worker.status_display && (
                      <Badge tone={workerStatusTone(worker.status)}>{worker.status_display}</Badge>
                    )}
                  </button>
                ))
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
