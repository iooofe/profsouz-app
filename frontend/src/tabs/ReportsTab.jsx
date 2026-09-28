import React, { useEffect, useMemo, useState } from 'react';
import { Ban, Check, Download, Ellipsis, Eye, FileSearch, FileStack, Pencil, Search, SlidersHorizontal, Trash2, X } from 'lucide-react';
import { apiFetch } from '../lib/api';
import {
  ACCOUNT_TYPE_OPTIONS,
  ASSISTANCE_TYPE_OPTIONS,
  RESORT_OPTIONS,
  cn,
  formatCount,
  formatMoney,
  getErrorText,
  isPensionerStatus,
  normalizeKzAccountInput,
  pluralRu,
  requestStatusTone,
  useIsMobile,
  workerStatusTone,
} from '../lib/utils';
import { REQUEST_TYPE_META } from '../lib/requestTypes';
import {
  Alert,
  Badge,
  Card,
  EmptyState,
  Field,
  IconButton,
  LoadingBlock,
  Modal,
  Pagination,
  Segmented,
  SkeletonRows,
  Spinner,
  Toggle,
  useFeedback,
} from '../components/ui';

function TypeTag({ type }) {
  const meta = REQUEST_TYPE_META[type];
  if (!meta) return <span>{type}</span>;
  const Icon = meta.icon;
  return (
    <span className="type-tag">
      <span className={`type-tag-icon tone-${meta.tone}`}>
        <Icon size={15} />
      </span>
      {meta.label}
    </span>
  );
}

export default function ReportsTab({ user, references }) {
  const { toast, confirm } = useFeedback();
  const isMobile = useIsMobile();
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [actionRow, setActionRow] = useState(null);
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

  const typeCounts = useMemo(() => {
    const counts = { all: rows.length, vacation: 0, material: 0, coal: 0, funeral: 0 };
    rows.forEach((row) => {
      if (counts[row.type] !== undefined) counts[row.type] += 1;
    });
    return counts;
  }, [rows]);

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
      setDetailModalOpen(false);
      toast({ tone: 'error', title: 'Не удалось загрузить заявление', text: getErrorText(e) });
    } finally {
      setDetailLoading(false);
    }
  };

  const rejectReport = async (row) => {
    if (!user.is_admin) return;
    const ok = await confirm({
      title: 'Отказать по заявлению?',
      text: `Заявление «${REQUEST_TYPE_META[row.type]?.label || row.type}» (${row.worker_name}) получит статус «Неактивно/Отклонено».`,
      confirmText: 'Отказать',
      tone: 'danger',
    });
    if (!ok) return;

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
      toast({ title: 'Заявление отклонено', text: row.worker_name });
      await load();
      if (detailData && detailData._id === row.id && detailData._type === row.type) {
        setDetailData(null);
        setDetailModalOpen(false);
      }
    } catch (e) {
      toast({ tone: 'error', title: 'Не удалось отказать', text: getErrorText(e) });
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

    const ok = await confirm({
      title: 'Удалить заявление?',
      text: `Заявление «${REQUEST_TYPE_META[row.type]?.label || row.type}» (${row.worker_name}) будет удалено без возможности восстановления.`,
      confirmText: 'Удалить',
      tone: 'danger',
    });
    if (!ok) return;

    try {
      try {
        await apiFetch(endpoint, { method: 'DELETE' });
      } catch (deleteError) {
        if (deleteError?.status !== 405) throw deleteError;
        await apiFetch(endpoint, { method: 'POST' });
      }
      toast({ title: 'Заявление удалено', text: row.worker_name });
      await load();
      if (detailData && detailData._id === row.id && detailData._type === row.type) {
        setDetailData(null);
        setDetailModalOpen(false);
      }
    } catch (e) {
      toast({ tone: 'error', title: 'Не удалось удалить', text: getErrorText(e) });
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
      };
      const isMaterialPensioner = isPensionerStatus(editData?.row?.worker_status);
      if (isMaterialPensioner || String(editData.form.account_number || '').trim()) {
        payload.account_type = editData.form.account_type;
        payload.account_number = normalizeKzAccountInput(editData.form.account_number);
      }
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
      const savedName = editData.workerName;
      closeEditModal();
      toast({ title: 'Заявление обновлено', text: savedName });
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

  const asText = (value) => {
    if (value === null || value === undefined || value === '') return '—';
    if (Array.isArray(value)) return value.length ? value.join(', ') : '—';
    if (typeof value === 'boolean') return value ? 'Да' : 'Нет';
    return String(value);
  };

  const canEditRow = (row) => row.status !== 'inactive';
  const editMaterialIsPensioner = editData?.type === 'material' && isPensionerStatus(editData?.row?.worker_status);

  const renderDetailGrid = (items) => (
    <dl className="detail-grid">
      {items.map((item) => (
        <div className={cn('detail-item', item.wide && 'is-wide')} key={item.label}>
          <dt>{item.label}</dt>
          <dd>
            {item.href ? (
              <a className="detail-link" href={item.href} target="_blank" rel="noreferrer">
                <Download size={14} /> {asText(item.value)}
              </a>
            ) : item.file ? (
              <span className="muted">{asText(item.value)}</span>
            ) : item.money ? (
              <span className="num">{formatMoney(item.value)}</span>
            ) : (
              asText(item.value)
            )}
          </dd>
        </div>
      ))}
    </dl>
  );

  const fileItem = (label, name, url) => ({
    label,
    value: name || 'Файл отсутствует',
    href: url || undefined,
    file: true,
  });

  const detailStatusText =
    detailData?.vacation_details?.status_text ||
    detailData?.assistance_details?.status_text ||
    detailData?.coal_details?.status_text ||
    detailData?.funeral_details?.status_text ||
    detailData?._source?.status_text;

  const detailMeta = detailData ? REQUEST_TYPE_META[detailData._type] : null;
  const editMeta = editData ? REQUEST_TYPE_META[editData.type] : null;
  const hasFilters = search.trim() || typeFilter !== 'all';
  const extraFilterCount =
    (user.is_admin && enterpriseFilter !== 'all' ? 1 : 0) +
    (user.is_admin && enterpriseSort !== 'default' ? 1 : 0) +
    (workerStatusSort !== 'default' ? 1 : 0);

  const typeOptions = [
    { value: 'all', label: 'Все', count: typeCounts.all },
    ...Object.entries(REQUEST_TYPE_META).map(([value, meta]) => ({
      value,
      label: meta.label,
      icon: meta.icon,
      count: typeCounts[value],
    })),
  ];

  return (
    <div className="stack">
      <Card className="filter-card">
        <div className="filter-row">
          <div className="search-field search-lg">
            <Search size={17} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={isMobile ? 'Работник, статус' : 'Поиск по работнику, предприятию, статусу...'}
            />
            {search && (
              <button type="button" className="search-clear" onClick={() => setSearch('')} aria-label="Очистить поиск">
                <X size={15} />
              </button>
            )}
          </div>
          {isMobile && (
            <button
              type="button"
              className={cn('btn btn-secondary filter-toggle', filtersOpen && 'is-open')}
              onClick={() => setFiltersOpen((v) => !v)}
              aria-expanded={filtersOpen}
              aria-label="Фильтры и сортировка"
            >
              <SlidersHorizontal size={18} />
              {extraFilterCount > 0 && <span className="filter-count">{extraFilterCount}</span>}
            </button>
          )}
          <Segmented options={typeOptions} value={typeFilter} onChange={setTypeFilter} className="segmented-scroll" />
        </div>
        <div className={cn('filter-row filter-row-secondary', isMobile && !filtersOpen && 'is-collapsed')}>
          {user.is_admin && (
            <Field label="Предприятие" className="field-inline">
              <select value={enterpriseFilter} onChange={(e) => setEnterpriseFilter(e.target.value)}>
                <option value="all">Все предприятия</option>
                {(references?.users || []).map((item) => (
                  <option key={item.id} value={String(item.id)}>
                    {item.username}
                  </option>
                ))}
              </select>
            </Field>
          )}
          {user.is_admin && (
            <Field label="Порядок" className="field-inline">
              <select value={enterpriseSort} onChange={(e) => setEnterpriseSort(e.target.value)}>
                <option value="default">Сначала новые</option>
                <option value="owner_asc">Предприятие: А–Я</option>
                <option value="owner_desc">Предприятие: Я–А</option>
              </select>
            </Field>
          )}
          <Field label="Статус работника" className="field-inline">
            <select value={workerStatusSort} onChange={(e) => setWorkerStatusSort(e.target.value)}>
              <option value="default">Без сортировки</option>
              <option value="asc">По возрастанию</option>
              <option value="desc">По убыванию</option>
            </select>
          </Field>
          <div className="filter-summary">
            {loading ? (
              <Spinner size={16} />
            ) : (
              <>
                {formatCount(filteredRows.length)} {pluralRu(filteredRows.length, 'заявление', 'заявления', 'заявлений')}
              </>
            )}
          </div>
        </div>
      </Card>

      {error && <Alert tone="error">{error}</Alert>}

      <Card flush>
        {loading && !rows.length ? (
          <SkeletonRows rows={8} cols={6} />
        ) : filteredRows.length === 0 ? (
          <EmptyState
            icon={hasFilters ? FileSearch : FileStack}
            title={hasFilters ? 'Ничего не найдено' : 'Заявлений пока нет'}
            text={
              hasFilters
                ? 'Попробуйте изменить запрос или выбрать другой вид заявления.'
                : 'Созданные заявления будут появляться здесь.'
            }
          />
        ) : isMobile ? (
          <div className={cn('m-list', loading && 'is-loading')}>
            {pagedRows.map((row) => {
              const meta = REQUEST_TYPE_META[row.type];
              const Icon = meta?.icon || FileStack;
              return (
                <div className="m-item m-item-report" key={`${row.type}-${row.id}`}>
                  <button type="button" className="m-item-hit" onClick={() => loadDetail(row)}>
                    <span className={`type-tag-icon type-tag-icon-lg tone-${meta?.tone || 'blue'}`}>
                      <Icon size={19} />
                    </span>
                    <span className="m-item-main">
                      <span className="m-item-sub">
                        {meta?.label || row.type} · {row.created_at}
                      </span>
                      <strong>{row.worker_name}</strong>
                      <span className="m-item-badges">
                        <Badge tone={requestStatusTone(row.status)} dot>
                          {row.status_text}
                        </Badge>
                        {user.is_admin && row.owner && <Badge tone="gray">{row.owner}</Badge>}
                      </span>
                    </span>
                  </button>
                  <IconButton icon={Ellipsis} label="Действия" className="m-item-more" onClick={() => setActionRow(row)} />
                </div>
              );
            })}
          </div>
        ) : (
          <div className={cn('table-wrap', loading && 'is-loading')}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Вид</th>
                  {user.is_admin && <th>Предприятие</th>}
                  <th>Работник</th>
                  <th>Статус заявления</th>
                  <th>Дата</th>
                  <th className="col-actions" aria-label="Действия" />
                </tr>
              </thead>
              <tbody>
                {pagedRows.map((row) => (
                  <tr key={`${row.type}-${row.id}`} className="row-clickable" onClick={() => loadDetail(row)}>
                    <td>
                      <TypeTag type={row.type} />
                    </td>
                    {user.is_admin && <td>{row.owner || <span className="muted">—</span>}</td>}
                    <td>
                      <div className="stacked-cell">
                        <strong>{row.worker_name}</strong>
                        {row.worker_status_display && (
                          <Badge tone={workerStatusTone(row.worker_status)} className="badge-sm">
                            {row.worker_status_display}
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td>
                      <Badge tone={requestStatusTone(row.status)} dot>
                        {row.status_text}
                      </Badge>
                    </td>
                    <td className="tnum nowrap">{row.created_at}</td>
                    <td className="col-actions" onClick={(e) => e.stopPropagation()}>
                      <div className="row-actions">
                        <IconButton icon={Eye} label="Подробнее" onClick={() => loadDetail(row)} />
                        <IconButton icon={Download} label="Скачать документ" href={row.download_url} />
                        <IconButton
                          icon={Pencil}
                          label={canEditRow(row) ? 'Исправить' : 'Отклоненное заявление нельзя изменить'}
                          onClick={() => openEdit(row)}
                          disabled={!canEditRow(row)}
                        />
                        {user.is_admin && (
                          <IconButton
                            icon={Ban}
                            label="Отказать"
                            tone="warn"
                            onClick={() => rejectReport(row)}
                            disabled={row.status === 'inactive'}
                          />
                        )}
                        <IconButton icon={Trash2} label="Удалить" tone="danger" onClick={() => deleteReport(row)} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {filteredRows.length > 0 && (
          <Pagination
            page={currentPage}
            pages={totalPages}
            onChange={setPage}
            summary={
              <>
                {formatCount((currentPage - 1) * pageSize + 1)}–
                {formatCount(Math.min(currentPage * pageSize, filteredRows.length))} из {formatCount(filteredRows.length)}
              </>
            }
          >
            <select
              className="select-sm"
              value={String(pageSize)}
              onChange={(e) => setPageSize(Number(e.target.value))}
              aria-label="Строк на странице"
            >
              <option value="10">по 10</option>
              <option value="20">по 20</option>
              <option value="50">по 50</option>
            </select>
          </Pagination>
        )}
      </Card>

      <Modal
        open={!!actionRow}
        onClose={() => setActionRow(null)}
        size="sm"
        icon={REQUEST_TYPE_META[actionRow?.type]?.icon || FileStack}
        title={actionRow?.worker_name || 'Заявление'}
        subtitle={actionRow ? `${REQUEST_TYPE_META[actionRow.type]?.label || ''} · ${actionRow.created_at}` : undefined}
        bodyClassName="action-sheet"
      >
        {actionRow && (
          <div className="action-list">
            <a className="btn btn-primary btn-lg btn-block" href={actionRow.download_url} target="_blank" rel="noreferrer" onClick={() => setActionRow(null)}>
              <Download size={18} /> Скачать документ
            </a>
            <button
              type="button"
              className="action-item"
              onClick={() => {
                const row = actionRow;
                setActionRow(null);
                loadDetail(row);
              }}
            >
              <Eye size={20} /> Подробнее
            </button>
            <button
              type="button"
              className="action-item"
              disabled={!canEditRow(actionRow)}
              onClick={() => {
                const row = actionRow;
                setActionRow(null);
                openEdit(row);
              }}
            >
              <Pencil size={20} /> Исправить
            </button>
            {user.is_admin && (
              <button
                type="button"
                className="action-item is-warn"
                disabled={actionRow.status === 'inactive'}
                onClick={() => {
                  const row = actionRow;
                  setActionRow(null);
                  rejectReport(row);
                }}
              >
                <Ban size={20} /> Отказать
              </button>
            )}
            <button
              type="button"
              className="action-item is-danger"
              onClick={() => {
                const row = actionRow;
                setActionRow(null);
                deleteReport(row);
              }}
            >
              <Trash2 size={20} /> Удалить
            </button>
          </div>
        )}
      </Modal>

      <Modal
        open={detailModalOpen}
        onClose={() => setDetailModalOpen(false)}
        size="lg"
        icon={detailMeta?.icon || FileStack}
        title={detailData ? `${detailMeta?.label || 'Заявление'} · ${detailData.worker?.full_name || detailData._source?.worker_name || ''}` : 'Заявление'}
        subtitle={detailData ? `№ ${detailData.id} от ${detailData.created_at}` : undefined}
        footer={
          detailData && (
            <>
              <button className="btn btn-ghost btn-danger-text" onClick={() => deleteReport(detailData._source)}>
                <Trash2 size={16} /> Удалить
              </button>
              {user.is_admin && (
                <button
                  className="btn btn-ghost btn-warn-text"
                  onClick={() => rejectReport(detailData._source)}
                  disabled={detailData._source?.status === 'inactive'}
                >
                  <Ban size={16} /> Отказать
                </button>
              )}
              <span className="foot-spacer" />
              <button
                className="btn btn-secondary"
                onClick={() => openEdit(detailData._source)}
                disabled={!canEditRow(detailData._source)}
              >
                <Pencil size={16} /> Исправить
              </button>
              {detailData?._source?.download_url && (
                <a className="btn btn-primary" href={detailData._source.download_url} target="_blank" rel="noreferrer">
                  <Download size={16} /> Скачать документ
                </a>
              )}
            </>
          )
        }
      >
        {detailLoading ? (
          <LoadingBlock />
        ) : detailData ? (
          <div className="detail-stack">
            <div className="detail-chips">
              <Badge tone={requestStatusTone(detailData._source?.status)} dot>
                {asText(detailStatusText)}
              </Badge>
              {detailData._source?.owner && <Badge tone="gray">Аккаунт: {detailData._source.owner}</Badge>}
            </div>

            <section className="detail-section">
              <h4>Работник</h4>
              {renderDetailGrid([
                { label: 'ФИО', value: detailData.worker?.full_name, wide: true },
                { label: 'Табельный номер', value: detailData.worker?.personnel_number },
                { label: 'ИИН', value: detailData.worker?.inn },
                { label: 'Статус', value: detailData.worker?.status },
                { label: 'Подразделение', value: detailData.worker?.department },
                { label: 'Должность', value: detailData.worker?.position },
                { label: 'Телефон', value: detailData.worker?.phone },
                { label: 'Адрес', value: detailData.worker?.address, wide: true },
                ...(detailData.worker?.is_dead === true || detailData.worker?.is_dead === 'Да' || detailData.worker?.death_date
                  ? [
                      { label: 'Умерший', value: detailData.worker?.is_dead },
                      { label: 'Дата смерти', value: detailData.worker?.death_date },
                    ]
                  : []),
              ])}
            </section>

            {detailData.vacation_details && (
              <section className="detail-section">
                <h4>Путевка</h4>
                {renderDetailGrid([
                  { label: 'Курорт', value: detailData.vacation_details.resort, wide: true },
                  { label: 'Дата начала', value: detailData.vacation_details.start_date },
                  { label: 'Дата окончания', value: detailData.vacation_details.end_date },
                  { label: 'Длительность, дней', value: detailData.vacation_details.duration_days },
                  { label: 'Количество человек', value: detailData.vacation_details.people_count },
                  { label: 'Работник едет', value: detailData.vacation_details.worker_goes },
                  { label: 'Сезоны «Орленка»', value: detailData.vacation_details.seasons },
                  { label: 'Цена за день', value: detailData.vacation_details.price_per_day, money: true },
                  { label: 'Своя цена', value: detailData.vacation_details.price_is_custom ? 'Да' : 'Нет' },
                  { label: 'Итоговая сумма', value: detailData.vacation_details.price, money: true },
                  fileItem(
                    'Справка об очном обучении',
                    detailData.study_certificate_file_name,
                    detailData.study_certificate_file
                  ),
                ])}
              </section>
            )}

            {detailData.assistance_details && (
              <section className="detail-section">
                <h4>Материальная помощь</h4>
                {renderDetailGrid([
                  { label: 'Вид помощи', value: detailData.assistance_details.assistance_type, wide: true },
                  { label: 'Сумма', value: detailData.assistance_details.amount, money: true },
                  { label: 'Тип счета', value: detailData.assistance_details.account_type },
                  { label: 'Номер счета', value: detailData.assistance_details.account_number },
                  fileItem(
                    'Скан счета',
                    detailData.assistance_details.account_file_name,
                    detailData.assistance_details.account_file_url
                  ),
                ])}
              </section>
            )}

            {detailData.coal_details && (
              <section className="detail-section">
                <h4>Уголь</h4>
                {renderDetailGrid([
                  { label: 'Тип счета', value: detailData.coal_details.account_type },
                  { label: 'Счет', value: detailData.coal_details.account_number },
                  fileItem('Скан счета', detailData.coal_details.account_file_name, detailData.coal_details.account_file_url),
                  fileItem(
                    'Техпаспорт дома',
                    detailData.coal_details.passport_file_name,
                    detailData.coal_details.passport_file_url
                  ),
                  fileItem(
                    'Удостоверение',
                    detailData.coal_details.pensioner_id_file_name,
                    detailData.coal_details.pensioner_id_file_url
                  ),
                ])}
              </section>
            )}

            {detailData.funeral_details && (
              <section className="detail-section">
                <h4>Погребение</h4>
                {renderDetailGrid([
                  { label: 'ФИО заявителя', value: detailData.funeral_details.applicant_full_name, wide: true },
                  { label: 'ИИН заявителя', value: detailData.funeral_details.applicant_inn },
                  { label: 'Дата смерти пенсионера', value: detailData.funeral_details.death_date },
                  { label: 'Тип счета', value: detailData.funeral_details.account_type },
                  { label: 'Счет', value: detailData.funeral_details.account_number },
                  fileItem(
                    'Скан счета',
                    detailData.funeral_details.account_file_name,
                    detailData.funeral_details.account_file_url
                  ),
                  fileItem(
                    'Скан счета получателя',
                    detailData.funeral_details.recipient_account_file_name,
                    detailData.funeral_details.recipient_account_file_url
                  ),
                  fileItem(
                    'Удостоверение заявителя',
                    detailData.funeral_details.applicant_id_file_name,
                    detailData.funeral_details.applicant_id_file_url
                  ),
                  fileItem(
                    'Справка о смерти',
                    detailData.funeral_details.death_certificate_file_name,
                    detailData.funeral_details.death_certificate_file_url
                  ),
                ])}
              </section>
            )}

            {detailData.family_members && (
              <section className="detail-section">
                <h4>Члены семьи</h4>
                {detailData.family_members.length ? (
                  <div className="table-wrap table-inset">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>ФИО</th>
                          <th>Родство</th>
                          <th>Документ</th>
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
        ) : (
          <EmptyState compact text="Нет данных" />
        )}
      </Modal>

      <Modal
        open={editModalOpen}
        onClose={closeEditModal}
        size="md"
        icon={editMeta?.icon || Pencil}
        title="Исправить заявление"
        subtitle={editData ? `${editMeta?.label || ''} · ${editData.workerName || '—'} · № ${editData.id}` : undefined}
        footer={
          <>
            {editError && <div className="form-error foot-error">{editError}</div>}
            <button type="button" className="btn btn-secondary" onClick={closeEditModal}>
              Отмена
            </button>
            <button className="btn btn-primary" type="submit" form="report-edit-form" disabled={editSaving || !editData}>
              {editSaving ? (
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
        {editLoading ? (
          <LoadingBlock />
        ) : editData ? (
          <form id="report-edit-form" className="form-stack" onSubmit={submitEdit}>
            {editData.type === 'vacation' && (
              <>
                <Field label="Курорт">
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
                </Field>
                <div className="form-grid form-grid-2">
                  <Field label="Дата начала" required>
                    <input
                      type="date"
                      value={editData.form.start_date}
                      onChange={(e) => updateEditField('start_date', e.target.value)}
                      required
                    />
                  </Field>
                  <Field label="Дата окончания" required>
                    <input
                      type="date"
                      value={editData.form.end_date}
                      onChange={(e) => updateEditField('end_date', e.target.value)}
                      required
                    />
                  </Field>
                </div>

                <Toggle
                  checked={!!editData.form.worker_goes}
                  onChange={(checked) => updateEditField('worker_goes', checked)}
                  label="Работник едет сам"
                />

                {editData.form.resort === 'orlenok' && (
                  <div className="field">
                    <span className="field-label">Сезоны «Орленка»</span>
                    <div className="chips">
                      {[1, 2, 3, 4].map((season) => {
                        const active = (editData.form.seasons || []).includes(season);
                        return (
                          <button
                            type="button"
                            key={season}
                            className={cn('chip', active && 'is-active')}
                            onClick={() => toggleEditSeason(season)}
                          >
                            {active && <Check size={14} />}
                            {season} сезон
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {['zhartas', 'shakhter'].includes(editData.form.resort) && (
                  <Field label="Своя цена (необязательно)" hint="Оставьте пустым — стоимость рассчитается автоматически">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={editData.form.custom_price || ''}
                      onChange={(e) => updateEditField('custom_price', e.target.value)}
                      placeholder="Автоматический расчет"
                    />
                  </Field>
                )}

                <div className="field">
                  <span className="field-label">Члены семьи</span>
                  {workerFamilyOptions.length > 0 ? (
                    <div className="check-list">
                      {workerFamilyOptions.map((member) => {
                        const checked = (editData.form.family_members || []).includes(member.id);
                        return (
                          <label key={member.id} className={cn('check-item', checked && 'is-checked')}>
                            <input type="checkbox" checked={checked} onChange={() => toggleEditFamily(member.id)} />
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
                  ) : (
                    <p className="muted">Нет доступных членов семьи</p>
                  )}
                </div>
              </>
            )}

            {editData.type === 'material' && (
              <>
                <Field label="Вид помощи">
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
                </Field>
                <Field label="Сумма, ₸">
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={editData.form.amount}
                    onChange={(e) => updateEditField('amount', e.target.value)}
                    disabled={editMaterialIsPensioner}
                  />
                </Field>
                {editMaterialIsPensioner ? (
                  <div className="form-grid form-grid-2">
                    <Field label="Тип счета">
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
                    </Field>
                    <Field label="Номер счета" required>
                      <input
                        className="mono"
                        value={editData.form.account_number}
                        onChange={(e) => updateEditField('account_number', normalizeKzAccountInput(e.target.value))}
                        maxLength={20}
                        required
                      />
                    </Field>
                  </div>
                ) : (
                  <p className="muted-note">Счет для работников берется из карточки работника.</p>
                )}
              </>
            )}

            {editData.type === 'coal' && (
              <div className="form-grid form-grid-2">
                <Field label="Тип счета">
                  <select value={editData.form.account_type} onChange={(e) => updateEditField('account_type', e.target.value)}>
                    {ACCOUNT_TYPE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Номер счета" required>
                  <input
                    className="mono"
                    value={editData.form.account_number}
                    onChange={(e) => updateEditField('account_number', normalizeKzAccountInput(e.target.value))}
                    maxLength={20}
                    required
                  />
                </Field>
              </div>
            )}

            {editData.type === 'funeral' && (
              <>
                <div className="form-grid form-grid-2">
                  <Field label="ФИО заявителя" required>
                    <input
                      value={editData.form.applicant_full_name}
                      onChange={(e) => updateEditField('applicant_full_name', e.target.value)}
                      required
                    />
                  </Field>
                  <Field label="ИИН заявителя" required>
                    <input
                      value={editData.form.applicant_inn}
                      onChange={(e) => updateEditField('applicant_inn', e.target.value)}
                      required
                    />
                  </Field>
                  <Field label="Тип счета">
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
                  </Field>
                  <Field label="Номер счета" required>
                    <input
                      className="mono"
                      value={editData.form.account_number}
                      onChange={(e) => updateEditField('account_number', normalizeKzAccountInput(e.target.value))}
                      maxLength={20}
                      required
                    />
                  </Field>
                  <Field label="Дата смерти пенсионера">
                    <input
                      type="date"
                      value={editData.form.death_date || ''}
                      onChange={(e) => updateEditField('death_date', e.target.value)}
                    />
                  </Field>
                </div>
              </>
            )}
          </form>
        ) : (
          editError && <Alert tone="error">{editError}</Alert>
        )}
      </Modal>
    </div>
  );
}
