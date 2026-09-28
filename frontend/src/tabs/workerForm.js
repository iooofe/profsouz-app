export function buildWorkerFormData(formState) {
  const fd = new FormData();
  fd.append('full_name', formState.full_name || '');
  fd.append('personnel_number', formState.personnel_number || '');
  fd.append('inn', formState.inn || '');
  fd.append('status', formState.status || 'worker');
  fd.append('is_union_member', formState.is_union_member === 'true' ? 'True' : 'False');
  fd.append('department', formState.department || '');
  fd.append('position', formState.position || '');
  fd.append('is_contract_member', formState.is_contract_member === 'true' ? 'True' : 'False');
  fd.append('phone', formState.phone || '');
  fd.append('address', formState.address || '');
  fd.append('id_number', formState.id_number || '');
  fd.append('id_issue_date', formState.id_issue_date || '');
  fd.append('id_issued_by', formState.id_issued_by || '');
  fd.append('has_benefits', formState.has_benefits === 'true' ? 'True' : 'False');
  fd.append('benefits_name', formState.benefits_name || '');
  fd.append('has_miner_glory', formState.has_miner_glory === 'true' ? 'True' : 'False');
  fd.append('account_20_digit', formState.account_20_digit || '');
  fd.append('current_account', formState.current_account || '');
  fd.append('enterprise_subdivision', formState.enterprise_subdivision || '');
  fd.append('regress_100_active', formState.regress_100_active === 'true' ? 'True' : 'False');
  fd.append('regress_29_active', formState.regress_29_active === 'true' ? 'True' : 'False');
  fd.append('regress_15_active', formState.regress_15_active === 'true' ? 'True' : 'False');
  fd.append('is_dead', formState.is_dead === 'true' ? 'True' : 'False');
  fd.append('death_date', formState.death_date || '');

  if (formState.user_id) {
    fd.append('user_id', formState.user_id);
  }

  const family = (formState.family_members || []).map((item) => ({
    id: item.id || null,
    full_name: item.full_name || '',
    relationship: item.relationship || 'other',
    id_number: item.id_number || '',
    id_issue_date: item.id_issue_date || '',
    id_issued_by: item.id_issued_by || '',
    birth_date: item.birth_date || '',
  }));
  fd.append('family_members', JSON.stringify(family));

  const fileKeys = [
    'benefits_file',
    'miner_glory_file',
    'house_passport_file',
    'pensioner_id_file',
    'death_certificate_file',
  ];
  for (const key of fileKeys) {
    if (formState.files[key] instanceof File) {
      fd.append(key, formState.files[key]);
    }
  }

  return fd;
}
