import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  FileText,
  Info,
  Loader2,
  Paperclip,
  X,
  XCircle,
} from 'lucide-react';
import { cn } from '../lib/utils';

export function Spinner({ size = 18, className }) {
  return <Loader2 className={cn('spin', className)} size={size} aria-hidden="true" />;
}

export function LoadingBlock({ label = 'Загрузка...' }) {
  return (
    <div className="loading-block" role="status">
      <Spinner size={22} />
      <span>{label}</span>
    </div>
  );
}

export function SkeletonRows({ rows = 6, cols = 6 }) {
  return (
    <div className="skeleton-table" aria-hidden="true">
      {Array.from({ length: rows }).map((_, r) => (
        <div className="skeleton-row" key={r}>
          {Array.from({ length: cols }).map((__, c) => (
            <span className="skeleton" key={c} style={{ width: `${55 + ((r * 7 + c * 13) % 40)}%` }} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function Badge({ tone = 'gray', dot = false, children, className }) {
  return (
    <span className={cn('badge', `badge-${tone}`, className)}>
      {dot && <span className="badge-dot" />}
      {children}
    </span>
  );
}

export function IconButton({ icon: Icon, label, tone, onClick, href, disabled, size = 16, className, ...rest }) {
  const classes = cn('icon-btn', tone && `icon-btn-${tone}`, className);
  if (href && !disabled) {
    return (
      <a className={classes} href={href} target="_blank" rel="noreferrer" aria-label={label} data-tip={label} {...rest}>
        <Icon size={size} />
      </a>
    );
  }
  return (
    <button
      type="button"
      className={classes}
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      data-tip={label}
      {...rest}
    >
      <Icon size={size} />
    </button>
  );
}

export function Card({ title, subtitle, icon: Icon, actions, children, className, bodyClassName, flush = false }) {
  return (
    <section className={cn('card', className)}>
      {(title || actions) && (
        <header className="card-head">
          <div className="card-head-main">
            {Icon && (
              <span className="card-icon">
                <Icon size={18} />
              </span>
            )}
            <div>
              {title && <h3 className="card-title">{title}</h3>}
              {subtitle && <div className="card-subtitle">{subtitle}</div>}
            </div>
          </div>
          {actions && <div className="card-actions">{actions}</div>}
        </header>
      )}
      <div className={cn(flush ? 'card-body-flush' : 'card-body', bodyClassName)}>{children}</div>
    </section>
  );
}

export function Field({ label, hint, required, children, className, span, as = 'label' }) {
  const Tag = as;
  return (
    <Tag className={cn('field', span === 'full' && 'field-full', span === 2 && 'field-span-2', className)}>
      {label && (
        <span className="field-label">
          {label}
          {required && <span className="field-required">*</span>}
        </span>
      )}
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </Tag>
  );
}

export function Toggle({ checked, onChange, label, description, disabled }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={!!checked}
      className={cn('toggle', checked && 'is-on')}
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
    >
      <span className="toggle-track">
        <span className="toggle-thumb" />
      </span>
      {(label || description) && (
        <span className="toggle-text">
          {label && <span className="toggle-label">{label}</span>}
          {description && <span className="toggle-desc">{description}</span>}
        </span>
      )}
    </button>
  );
}

/** Toggle bound to the string flags ('true' / 'false') used by the worker form. */
export function FlagToggle({ value, onChange, label, description }) {
  return (
    <Toggle
      checked={value === 'true'}
      onChange={(next) => onChange(next ? 'true' : 'false')}
      label={label}
      description={description}
    />
  );
}

export function FileInput({ label, file, onChange, current, hint, required }) {
  const inputRef = useRef(null);
  const hasNew = file instanceof File;

  return (
    <div className="field">
      {label && (
        <span className="field-label">
          {label}
          {required && <span className="field-required">*</span>}
        </span>
      )}
      <div className={cn('file-input', hasNew && 'has-file')}>
        <span className="file-icon">{hasNew ? <FileText size={16} /> : <Paperclip size={16} />}</span>
        <div className="file-meta">
          {hasNew ? (
            <span className="file-name" title={file.name}>
              {file.name}
            </span>
          ) : current?.name ? (
            <span className="file-name">
              <a href={current.url} target="_blank" rel="noreferrer" title={current.name}>
                {current.name}
              </a>
            </span>
          ) : (
            <span className="file-empty">Файл не выбран</span>
          )}
          {hasNew && current?.name && <span className="file-sub">Заменит: {current.name}</span>}
        </div>
        {hasNew ? (
          <button
            type="button"
            className="file-clear"
            onClick={() => {
              if (inputRef.current) inputRef.current.value = '';
              onChange(null);
            }}
            aria-label="Убрать файл"
          >
            <X size={14} />
          </button>
        ) : null}
        <label className="btn btn-ghost btn-sm file-pick">
          {hasNew || current?.name ? 'Заменить' : 'Выбрать'}
          <input
            ref={inputRef}
            type="file"
            className="visually-hidden"
            onChange={(e) => onChange(e.target.files?.[0] || null)}
          />
        </label>
      </div>
      {hint && <span className="field-hint">{hint}</span>}
    </div>
  );
}

// Открытые модальные окна по порядку открытия: Esc закрывает только верхнее.
const openModalStack = [];

export function Modal({ open, onClose, title, subtitle, icon: Icon, size = 'md', children, footer, bodyClassName }) {
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return undefined;
    const token = {};
    openModalStack.push(token);
    const onKey = (event) => {
      if (event.key === 'Escape' && openModalStack[openModalStack.length - 1] === token) {
        onCloseRef.current?.();
      }
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      openModalStack.splice(openModalStack.indexOf(token), 1);
      if (!openModalStack.length) document.body.style.overflow = '';
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="modal-overlay" onMouseDown={onClose}>
      <div
        className={cn('modal', `modal-${size}`)}
        role="dialog"
        aria-modal="true"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <header className="modal-head">
          <div className="modal-head-main">
            {Icon && (
              <span className="modal-icon">
                <Icon size={18} />
              </span>
            )}
            <div>
              <h3>{title}</h3>
              {subtitle && <p>{subtitle}</p>}
            </div>
          </div>
          <IconButton icon={X} label="Закрыть" onClick={onClose} />
        </header>
        <div className={cn('modal-body', bodyClassName)}>{children}</div>
        {footer && <footer className="modal-foot">{footer}</footer>}
      </div>
    </div>
  );
}

export function EmptyState({ icon: Icon = Info, title, text, action, compact = false }) {
  return (
    <div className={cn('empty-state', compact && 'is-compact')}>
      <span className="empty-icon">
        <Icon size={compact ? 18 : 22} />
      </span>
      {title && <strong>{title}</strong>}
      {text && <p>{text}</p>}
      {action}
    </div>
  );
}

export function Segmented({ options, value, onChange, size, className }) {
  return (
    <div className={cn('segmented', size === 'sm' && 'segmented-sm', className)} role="tablist">
      {options.map((option) => {
        const Icon = option.icon;
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={value === option.value}
            className={cn('segmented-item', value === option.value && 'is-active')}
            onClick={() => onChange(option.value)}
          >
            {Icon && <Icon size={15} />}
            <span>{option.label}</span>
            {option.count !== undefined && <span className="segmented-count">{option.count}</span>}
          </button>
        );
      })}
    </div>
  );
}

export function Pagination({ page, pages, onChange, summary, children }) {
  return (
    <div className="pager">
      <div className="pager-summary">{summary}</div>
      <div className="pager-controls">
        {children}
        {pages > 1 && (
          <>
            <IconButton icon={ChevronsLeft} label="Первая страница" disabled={page <= 1} onClick={() => onChange(1)} />
            <IconButton icon={ChevronLeft} label="Назад" disabled={page <= 1} onClick={() => onChange(page - 1)} />
            <span className="pager-page">
              {page} <span className="muted">из</span> {pages}
            </span>
            <IconButton icon={ChevronRight} label="Вперед" disabled={page >= pages} onClick={() => onChange(page + 1)} />
            <IconButton
              icon={ChevronsRight}
              label="Последняя страница"
              disabled={page >= pages}
              onClick={() => onChange(pages)}
            />
          </>
        )}
      </div>
    </div>
  );
}

export function Alert({ tone = 'error', children, onClose }) {
  const Icon = tone === 'error' ? XCircle : tone === 'success' ? CheckCircle2 : tone === 'warn' ? AlertTriangle : Info;
  return (
    <div className={cn('alert', `alert-${tone}`)} role={tone === 'error' ? 'alert' : 'status'}>
      <Icon size={18} />
      <div className="alert-text">{children}</div>
      {onClose && <IconButton icon={X} label="Скрыть" onClick={onClose} size={14} />}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Toasts and confirmation dialogs                                     */
/* ------------------------------------------------------------------ */

const FeedbackContext = createContext(null);

export function FeedbackProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const [confirmState, setConfirmState] = useState(null);
  const idRef = useRef(0);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (input) => {
      const item = typeof input === 'string' ? { title: input } : input;
      idRef.current += 1;
      const id = idRef.current;
      setToasts((prev) => [...prev.slice(-3), { tone: 'success', ...item, id }]);
      window.setTimeout(() => dismiss(id), item.tone === 'error' ? 7000 : 4500);
    },
    [dismiss]
  );

  const confirm = useCallback(
    (options) =>
      new Promise((resolve) => {
        setConfirmState({ ...options, resolve });
      }),
    []
  );

  const closeConfirm = (result) => {
    confirmState?.resolve(result);
    setConfirmState(null);
  };

  return (
    <FeedbackContext.Provider value={{ toast, confirm }}>
      {children}
      <div className="toast-stack" aria-live="polite">
        {toasts.map((t) => {
          const Icon = t.tone === 'error' ? XCircle : t.tone === 'warn' ? AlertTriangle : CheckCircle2;
          return (
            <div key={t.id} className={cn('toast', `toast-${t.tone}`)}>
              <Icon size={18} />
              <div className="toast-text">
                <strong>{t.title}</strong>
                {t.text && <span>{t.text}</span>}
              </div>
              <button type="button" className="toast-close" onClick={() => dismiss(t.id)} aria-label="Закрыть">
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
      <Modal
        open={!!confirmState}
        onClose={() => closeConfirm(false)}
        title={confirmState?.title || 'Подтвердите действие'}
        icon={confirmState?.tone === 'danger' ? AlertTriangle : Info}
        size="sm"
        footer={
          <>
            <button type="button" className="btn btn-secondary" onClick={() => closeConfirm(false)}>
              Отмена
            </button>
            <button
              type="button"
              className={cn('btn', confirmState?.tone === 'danger' ? 'btn-danger-solid' : 'btn-primary')}
              onClick={() => closeConfirm(true)}
              autoFocus
            >
              {confirmState?.confirmText || 'Подтвердить'}
            </button>
          </>
        }
      >
        <p className="confirm-text">{confirmState?.text}</p>
      </Modal>
    </FeedbackContext.Provider>
  );
}

export function useFeedback() {
  return useContext(FeedbackContext);
}
