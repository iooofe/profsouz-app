import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import calendar

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils import timezone

from .forms import FamilyMemberForm, WorkerForm
from .models import (
    CoalRequest,
    FamilyMember,
    FuneralRequest,
    MaterialAssistanceRequest,
    Statement,
    VacationLimit,
    VacationRequest,
    Worker,
)


def is_admin(user):
    return user.username == 'АДМИН' or user.is_staff or user.is_superuser


def api_login_required(view_func):
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Требуется авторизация'}, status=401)
        return view_func(request, *args, **kwargs)

    _wrapped.__name__ = getattr(view_func, '__name__', 'wrapped')
    _wrapped.__doc__ = getattr(view_func, '__doc__')
    _wrapped.__module__ = getattr(view_func, '__module__')
    return _wrapped


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ('1', 'true', 'yes', 'да', 'y', 'on')


def _json_payload(request):
    if request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            return {}
    return {}


def _api_error(message, status=400, extra=None):
    payload = {'success': False, 'error': message}
    if extra:
        payload.update(extra)
    return JsonResponse(payload, status=status)


def _date_iso(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


def _date_human(value):
    if not value:
        return None
    return value.strftime('%d.%m.%Y')


def _datetime_human(value):
    if not value:
        return None
    return value.strftime('%d.%m.%Y %H:%M')


def _period_end_from_start(period_start):
    last_day = calendar.monthrange(period_start.year, period_start.month)[1]
    return date(period_start.year, period_start.month, min(30, last_day))


def _get_statement_period():
    today = timezone.now().date()
    period_start = date(today.year, today.month, 1)
    period_end = _period_end_from_start(period_start)
    return period_start, period_end


def _workers_qs(user):
    if is_admin(user):
        return Worker.objects.all().select_related('user').order_by('full_name')
    return Worker.objects.filter(user=user).select_related('user').order_by('full_name')


def _serialize_family_member(member):
    return {
        'id': member.id,
        'full_name': member.full_name,
        'relationship': member.relationship,
        'relationship_display': member.get_relationship_display(),
        'id_number': member.id_number or '',
        'id_issue_date': _date_iso(member.id_issue_date),
        'id_issued_by': member.id_issued_by or '',
        'birth_date': _date_iso(member.birth_date),
        'age': member.get_age() if member.birth_date else None,
    }


def _serialize_worker(worker, include_family=False):
    data = {
        'id': worker.id,
        'full_name': worker.full_name,
        'personnel_number': worker.personnel_number or '',
        'inn': worker.inn or '',
        'status': worker.status,
        'status_display': worker.get_status_display(),
        'is_union_member': bool(worker.is_union_member),
        'department': worker.department or '',
        'position': worker.position or '',
        'is_contract_member': bool(worker.is_contract_member),
        'phone': worker.phone or '',
        'address': worker.address or '',
        'id_number': worker.id_number or '',
        'id_issue_date': _date_iso(worker.id_issue_date),
        'id_issued_by': worker.id_issued_by or '',
        'has_benefits': bool(worker.has_benefits),
        'benefits_name': worker.benefits_name or '',
        'has_miner_glory': bool(worker.has_miner_glory),
        'account_20_digit': worker.account_20_digit or '',
        'current_account': worker.current_account or '',
        'is_dead': bool(worker.is_dead),
        'death_date': _date_iso(worker.death_date),
        'death_date_display': _date_human(worker.death_date),
        'created_at': _datetime_human(worker.created_at),
        'updated_at': _datetime_human(worker.updated_at),
        'user_id': worker.user.id if worker.user else None,
        'user_account': worker.user.username if worker.user else None,
        'files': {
            'benefits_file_url': worker.benefits_file.url if worker.benefits_file else None,
            'benefits_file_name': worker.benefits_file.name.split('/')[-1] if worker.benefits_file else None,
            'miner_glory_file_url': worker.miner_glory_file.url if worker.miner_glory_file else None,
            'miner_glory_file_name': worker.miner_glory_file.name.split('/')[-1] if worker.miner_glory_file else None,
            'house_passport_file_url': worker.house_passport_file.url if worker.house_passport_file else None,
            'house_passport_file_name': worker.house_passport_file.name.split('/')[-1] if worker.house_passport_file else None,
            'pensioner_id_file_url': worker.pensioner_id_file.url if worker.pensioner_id_file else None,
            'pensioner_id_file_name': worker.pensioner_id_file.name.split('/')[-1] if worker.pensioner_id_file else None,
            'death_certificate_file_url': worker.death_certificate_file.url if worker.death_certificate_file else None,
            'death_certificate_file_name': worker.death_certificate_file.name.split('/')[-1] if worker.death_certificate_file else None,
        },
        'family_members_count': worker.family_members.count(),
    }
    if include_family:
        data['family_members'] = [_serialize_family_member(m) for m in worker.family_members.all().order_by('id')]
    return data


def _parse_family_members_payload(source):
    raw = source.get('family_members')
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _parse_ids(value):
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                items = parsed
            else:
                items = value.split(',')
        except Exception:
            items = value.split(',')
    else:
        return []
    result = []
    for item in items:
        s = str(item).strip()
        if s.isdigit():
            result.append(int(s))
    return result


def _parse_seasons(payload, request):
    if payload and isinstance(payload, dict):
        seasons = payload.get('seasons')
    else:
        seasons = None
    if seasons is None:
        seasons = request.POST.getlist('seasons')
    if seasons is None:
        return []
    if isinstance(seasons, str):
        try:
            parsed = json.loads(seasons)
            seasons = parsed if isinstance(parsed, list) else [seasons]
        except Exception:
            seasons = [s for s in seasons.split(',') if s.strip()]
    if not isinstance(seasons, list):
        return []
    output = []
    for season in seasons:
        s = str(season).strip()
        if s.isdigit():
            output.append(int(s))
    return output


def _worker_scope_for_user(user, worker_id):
    if is_admin(user):
        return get_object_or_404(Worker, id=worker_id)
    return get_object_or_404(Worker, id=worker_id, user=user)


def _request_scope_for_user(user, model, request_id):
    if is_admin(user):
        return get_object_or_404(model, id=request_id)
    return get_object_or_404(model, id=request_id, worker__user=user)


def _vacation_effective_price(item):
    """Возвращает итоговую стоимость путевки: сохраненную (если валидна) или расчетную."""
    calculated_price = item.calculate_price()
    try:
        stored_price = item.price
    except Exception:
        stored_price = None

    if stored_price is None:
        return calculated_price

    try:
        return stored_price if stored_price > 0 else calculated_price
    except Exception:
        return calculated_price


def _parse_optional_custom_price(raw, resort):
    value = (raw or '').strip()
    if not value:
        return None
    if resort not in ('zhartas', 'shakhter'):
        raise ValueError('Ручная цена доступна только для курортов Жартас и Шахтер')
    try:
        parsed = Decimal(value.replace(',', '.'))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError('Некорректная цена путевки')
    if parsed <= 0:
        raise ValueError('Цена путевки должна быть больше 0')
    return parsed


def _serialize_vacation_request(item):
    effective_price = _vacation_effective_price(item)
    calculated_price = item.calculate_price()
    try:
        stored_price = item.price
    except Exception:
        stored_price = None
    is_custom_price = (
        item.resort in ('zhartas', 'shakhter')
        and stored_price is not None
        and calculated_price is not None
        and stored_price != calculated_price
    )
    return {
        'id': item.id,
        'type': 'vacation',
        'worker_id': item.worker_id,
        'worker_name': item.worker.full_name,
        'resort': item.resort,
        'resort_display': item.get_resort_display(),
        'start_date': _date_iso(item.start_date),
        'end_date': _date_iso(item.end_date),
        'status': item.get_status(),
        'status_text': item.get_status_display_text(),
        'is_rejected': bool(item.is_rejected),
        'request_status': item.request_status,
        'created_at': _datetime_human(item.created_at),
        'created_at_iso': item.created_at.isoformat(),
        'price': float(effective_price) if effective_price is not None else None,
        'price_is_custom': bool(is_custom_price),
        'places_count': item.get_places_count(),
        'worker_goes': bool(getattr(item, 'worker_goes', True)),
        'family_members_count': item.family_members.count(),
        'download_url': reverse('main:download_vacation_request', args=[item.id]),
        'detail_url': reverse('main:vacation_request_detail', args=[item.id]),
        'owner': item.user.username,
    }


def _serialize_material_request(item):
    if item.account_type == '20_digit':
        account_number = item.account_number or item.worker.account_20_digit or ''
    else:
        account_number = item.account_number or item.worker.current_account or ''

    return {
        'id': item.id,
        'type': 'material',
        'worker_id': item.worker_id,
        'worker_name': item.worker.full_name,
        'assistance_type': item.assistance_type,
        'assistance_type_display': item.get_assistance_type_display(),
        'amount': float(item.amount) if item.amount is not None else None,
        'account_type': item.account_type,
        'account_type_display': item.get_account_type_display(),
        'account_number': account_number,
        'status': item.get_status(),
        'status_text': item.get_status_display_text(),
        'request_status': item.request_status,
        'created_at': _datetime_human(item.created_at),
        'created_at_iso': item.created_at.isoformat(),
        'download_url': reverse('main:download_material_assistance', args=[item.id]),
        'detail_url': reverse('main:material_assistance_detail', args=[item.id]),
        'owner': item.user.username,
    }


def _serialize_coal_request(item):
    if item.account_type == '20_digit':
        account_number = item.account_number or item.worker.account_20_digit or ''
    else:
        account_number = item.account_number or item.worker.current_account or ''

    return {
        'id': item.id,
        'type': 'coal',
        'worker_id': item.worker_id,
        'worker_name': item.worker.full_name,
        'account_type': item.account_type,
        'account_type_display': item.get_account_type_display(),
        'account_number': account_number,
        'status': item.get_status(),
        'status_text': item.get_status_display_text(),
        'request_status': item.request_status,
        'created_at': _datetime_human(item.created_at),
        'created_at_iso': item.created_at.isoformat(),
        'download_url': reverse('main:download_coal_request', args=[item.id]),
        'detail_url': reverse('main:coal_request_detail', args=[item.id]),
        'owner': item.user.username,
    }


def _serialize_funeral_request(item):
    if item.account_type == '20_digit':
        account_number = item.account_number or ''
    else:
        account_number = item.account_number or item.worker.current_account or ''

    return {
        'id': item.id,
        'type': 'funeral',
        'worker_id': item.worker_id,
        'worker_name': item.worker.full_name,
        'applicant_full_name': item.applicant_full_name,
        'applicant_inn': item.applicant_inn,
        'account_type': item.account_type,
        'account_type_display': item.get_account_type_display(),
        'account_number': account_number,
        'status': item.get_status(),
        'status_text': item.get_status_display_text(),
        'request_status': item.request_status,
        'created_at': _datetime_human(item.created_at),
        'created_at_iso': item.created_at.isoformat(),
        'download_url': reverse('main:download_funeral_request', args=[item.id]),
        'detail_url': reverse('main:funeral_request_detail', args=[item.id]),
        'owner': item.user.username,
    }


@ensure_csrf_cookie
def spa_entry(request, path=''):
    return render(request, 'spa/index.html')


@ensure_csrf_cookie
@require_http_methods(['GET'])
def api_auth_bootstrap(request):
    usernames = list(User.objects.order_by('username').values_list('username', flat=True))
    user_payload = None
    if request.user.is_authenticated:
        user_payload = {
            'id': request.user.id,
            'username': request.user.username,
            'is_admin': is_admin(request.user),
        }
    return JsonResponse({
        'success': True,
        'csrf_token': get_token(request),
        'authenticated': bool(request.user.is_authenticated),
        'user': user_payload,
        'accounts': usernames,
    })


@require_http_methods(['POST'])
def api_auth_login(request):
    payload = _json_payload(request)
    username = (payload.get('username') or request.POST.get('username') or '').strip()
    password = payload.get('password') or request.POST.get('password') or ''

    if not username or not password:
        return _api_error('Укажите логин и пароль')

    user = authenticate(request, username=username, password=password)
    if user is None:
        return _api_error('Неверный логин или пароль', status=401)
    if not user.is_active:
        return _api_error('Аккаунт неактивен', status=403)

    login(request, user)
    return JsonResponse({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'is_admin': is_admin(user),
        }
    })


@api_login_required
@require_http_methods(['POST'])
def api_auth_logout(request):
    logout(request)
    return JsonResponse({'success': True})


@require_http_methods(['GET'])
def api_auth_me(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': True, 'authenticated': False, 'user': None})
    return JsonResponse({
        'success': True,
        'authenticated': True,
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'is_admin': is_admin(request.user),
        }
    })


@api_login_required
@require_http_methods(['GET'])
def api_reference_data(request):
    users = []
    if is_admin(request.user):
        users = list(User.objects.order_by('username').values('id', 'username'))

    return JsonResponse({
        'success': True,
        'users': users,
        'worker_status_choices': [{'value': v, 'label': l} for v, l in Worker.STATUS_CHOICES],
        'relationship_choices': [{'value': v, 'label': l} for v, l in FamilyMember.RELATIONSHIP_CHOICES],
        'resort_choices': [{'value': v, 'label': l} for v, l in VacationRequest.RESORT_CHOICES],
        'assistance_type_choices': [{'value': v, 'label': l} for v, l in MaterialAssistanceRequest.ASSISTANCE_TYPE_CHOICES],
        'account_type_choices': [{'value': v, 'label': l} for v, l in CoalRequest.ACCOUNT_TYPE_CHOICES],
    })


@api_login_required
@require_http_methods(['GET'])
def api_dashboard(request):
    user_is_admin = is_admin(request.user)

    workers_qs = _workers_qs(request.user)

    if user_is_admin:
        vacation_qs = VacationRequest.objects.all()
        material_qs = MaterialAssistanceRequest.objects.all()
        coal_qs = CoalRequest.objects.all()
        funeral_qs = FuneralRequest.objects.all()
    else:
        vacation_qs = VacationRequest.objects.filter(worker__user=request.user)
        material_qs = MaterialAssistanceRequest.objects.filter(worker__user=request.user)
        coal_qs = CoalRequest.objects.filter(worker__user=request.user)
        funeral_qs = FuneralRequest.objects.filter(worker__user=request.user)

    period_start, period_end = _get_statement_period()

    return JsonResponse({
        'success': True,
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'is_admin': user_is_admin,
        },
        'counts': {
            'workers': workers_qs.count(),
            'vacation_requests': vacation_qs.count(),
            'material_requests': material_qs.count(),
            'coal_requests': coal_qs.count(),
            'funeral_requests': funeral_qs.count(),
        },
        'current_statement_period': {
            'period_start': _date_iso(period_start),
            'period_end': _date_iso(period_end),
            'period_start_human': _date_human(period_start),
            'period_end_human': _date_human(period_end),
        }
    })


@api_login_required
@require_http_methods(['GET', 'POST'])
def api_workers(request):
    user_is_admin = is_admin(request.user)

    if request.method == 'GET':
        search = request.GET.get('search', '').strip()
        page = max(int(request.GET.get('page', '1') or 1), 1)
        page_size = min(max(int(request.GET.get('page_size', '50') or 50), 1), 200)

        workers = _workers_qs(request.user)
        if search:
            search_lower = search.lower()
            worker_ids = []
            for worker in workers:
                if (
                    search_lower in (worker.full_name or '').lower()
                    or search_lower in (worker.personnel_number or '').lower()
                    or search_lower in (worker.inn or '').lower()
                    or search_lower in (worker.department or '').lower()
                    or search_lower in (worker.position or '').lower()
                    or search_lower in (worker.phone or '').lower()
                ):
                    worker_ids.append(worker.id)
            workers = _workers_qs(request.user).filter(id__in=worker_ids)

        paginator = Paginator(workers, page_size)
        page_obj = paginator.get_page(page)
        results = [_serialize_worker(w) for w in page_obj.object_list]

        return JsonResponse({
            'success': True,
            'results': results,
            'pagination': {
                'page': page_obj.number,
                'page_size': page_size,
                'pages': paginator.num_pages,
                'count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            },
        })

    payload = _json_payload(request)
    data = request.POST if request.POST else payload
    files = request.FILES

    worker_form = WorkerForm(data, files)
    if not worker_form.is_valid():
        return _api_error('Ошибка в данных работника', extra={'fields': worker_form.errors})

    family_payload = _parse_family_members_payload(data)

    valid_family_forms = []
    for idx, member_data in enumerate(family_payload, 1):
        if not (member_data.get('full_name') or '').strip():
            continue
        fm_form = FamilyMemberForm(member_data)
        if fm_form.is_valid():
            valid_family_forms.append(fm_form)
        else:
            return _api_error(
                f'Ошибка в данных члена семьи #{idx}',
                extra={'fields': fm_form.errors, 'member_index': idx},
            )

    with transaction.atomic():
        worker = worker_form.save(commit=False)
        if user_is_admin:
            user_id = data.get('user_id')
            if user_id:
                try:
                    worker.user = User.objects.get(id=int(user_id))
                except (ValueError, User.DoesNotExist):
                    return _api_error('Пользователь для работника не найден')
            elif not worker.user_id:
                worker.user = request.user
        else:
            worker.user = request.user
        worker.save()

        for fm_form in valid_family_forms:
            fm = fm_form.save(commit=False)
            fm.worker = worker
            fm.save()

    return JsonResponse({'success': True, 'worker': _serialize_worker(worker, include_family=True)})


@api_login_required
@require_http_methods(['GET', 'PUT', 'PATCH', 'DELETE', 'POST'])
def api_worker_detail(request, worker_id):
    user_is_admin = is_admin(request.user)
    worker = _worker_scope_for_user(request.user, worker_id)

    if request.method == 'GET':
        return JsonResponse({'success': True, 'worker': _serialize_worker(worker, include_family=True)})

    if request.method in ('DELETE',):
        worker_name = worker.full_name
        worker.delete()
        return JsonResponse({'success': True, 'message': f'Работник {worker_name} удален'})

    if request.method == 'POST' and request.POST.get('_method', '').upper() == 'DELETE':
        worker_name = worker.full_name
        worker.delete()
        return JsonResponse({'success': True, 'message': f'Работник {worker_name} удален'})

    payload = _json_payload(request)
    data = request.POST if request.POST else payload
    files = request.FILES

    worker_form = WorkerForm(data, files, instance=worker)
    if not worker_form.is_valid():
        return _api_error('Ошибка в данных работника', extra={'fields': worker_form.errors})

    family_payload = _parse_family_members_payload(data)
    valid_family_forms = []
    for idx, member_data in enumerate(family_payload, 1):
        if not (member_data.get('full_name') or '').strip():
            continue
        fm_form = FamilyMemberForm(member_data)
        if fm_form.is_valid():
            valid_family_forms.append(fm_form)
        else:
            return _api_error(
                f'Ошибка в данных члена семьи #{idx}',
                extra={'fields': fm_form.errors, 'member_index': idx},
            )

    with transaction.atomic():
        worker = worker_form.save(commit=False)
        if user_is_admin and data.get('user_id'):
            try:
                worker.user = User.objects.get(id=int(data.get('user_id')))
            except (ValueError, User.DoesNotExist):
                return _api_error('Пользователь для работника не найден')
        worker.save()

        worker.family_members.all().delete()
        for fm_form in valid_family_forms:
            fm = fm_form.save(commit=False)
            fm.worker = worker
            fm.save()

    return JsonResponse({'success': True, 'worker': _serialize_worker(worker, include_family=True)})


@api_login_required
@require_http_methods(['GET'])
def api_vacation_requests(request):
    search = request.GET.get('search', '').strip().lower()
    if is_admin(request.user):
        qs = VacationRequest.objects.all().select_related('worker', 'user').prefetch_related('family_members').defer('price').order_by('-created_at')
    else:
        qs = VacationRequest.objects.filter(worker__user=request.user).select_related('worker', 'user').prefetch_related('family_members').defer('price').order_by('-created_at')

    if search:
        ids = []
        for item in qs:
            if (
                search in (item.worker.full_name or '').lower()
                or search in (item.worker.personnel_number or '').lower()
                or search in (item.worker.department or '').lower()
                or search in (item.get_resort_display() or '').lower()
            ):
                ids.append(item.id)
        qs = qs.filter(id__in=ids)

    return JsonResponse({'success': True, 'results': [_serialize_vacation_request(i) for i in qs]})


@api_login_required
@require_http_methods(['POST'])
def api_create_vacation_request(request):
    payload = _json_payload(request)
    source = request.POST if request.POST else payload

    worker_id = source.get('worker_id')
    if not worker_id:
        return _api_error('Не выбран работник')

    worker = _worker_scope_for_user(request.user, worker_id)

    resort = (source.get('resort') or '').strip()
    start_date_str = source.get('start_date')
    end_date_str = source.get('end_date')
    custom_price_raw = source.get('custom_price')

    if not resort:
        return _api_error('Не выбран курорт')

    if worker.status == 'pensioner' and resort in ['balkhash', 'discovery']:
        resort_name = dict(VacationRequest.RESORT_CHOICES).get(resort, resort)
        return _api_error(f'Пенсионеры не могут выбирать курорт "{resort_name}"')

    if not start_date_str or not end_date_str:
        return _api_error('Не указаны даты поездки')

    seasons = _parse_seasons(payload, request)
    if resort == 'orlenok':
        if not seasons:
            return _api_error('Для ДОЦ "Орленок" необходимо выбрать хотя бы один сезон')
        if not all(1 <= s <= 4 for s in seasons):
            return _api_error('Сезоны должны быть числами от 1 до 4')
    else:
        seasons = []

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except Exception:
        return _api_error('Неверный формат даты')

    if end_date < start_date:
        return _api_error('Дата окончания не может быть раньше даты начала')

    if start_date.year < 2000 or end_date.year < 2000:
        return _api_error('Год в дате поездки должен быть не ранее 2000')

    trip_days = (end_date - start_date).days + 1
    if trip_days > 31:
        return _api_error('Длительность путевки не может превышать 31 день')

    try:
        custom_price = _parse_optional_custom_price(custom_price_raw, resort)
    except ValueError as exc:
        return _api_error(str(exc))

    family_member_ids = _parse_ids(source.get('family_members'))
    worker_goes = _parse_bool(source.get('worker_goes', True))

    if not worker_goes and len(family_member_ids) == 0:
        return _api_error('Нужно выбрать хотя бы одного отдыхающего: работник или член семьи')

    family_members = FamilyMember.objects.filter(id__in=family_member_ids, worker=worker)

    for fm in family_members:
        if fm.is_child_or_grandchild():
            if not fm.birth_date:
                return _api_error(f'Для {fm.get_relationship_display().lower()} {fm.full_name} нужно указать дату рождения')
            age = fm.get_age()
            if age is None:
                continue
            if resort == 'orlenok' and age >= 14:
                return _api_error(
                    f'{fm.get_relationship_display()} {fm.full_name} не проходит по возрасту для ДОЦ "Орленок" (возраст {age} лет)'
                )
            if resort == 'discovery' and age >= 18:
                if not request.FILES.get('study_certificate_file'):
                    return _api_error(
                        f'Для {fm.get_relationship_display().lower()} {fm.full_name} старше 18 лет для курорта "Дискавери" нужна справка об очном обучении'
                    )

    if not is_admin(request.user) and resort in ['zhartas', 'shakhter']:
        limit, _ = VacationLimit.get_or_create_limit(request.user, resort)
        new_places = (1 if worker_goes else 0) + len(family_member_ids)
        if new_places > limit.get_remaining_places():
            return _api_error(
                f'Превышен лимит путевок: доступно {limit.get_remaining_places()}, требуется {new_places}'
            )

    vacation = VacationRequest.objects.create(
        user=request.user,
        worker=worker,
        resort=resort,
        start_date=start_date,
        end_date=end_date,
        worker_goes=worker_goes,
        study_certificate_file=request.FILES.get('study_certificate_file'),
        seasons=seasons,
    )
    if family_member_ids:
        vacation.family_members.set(family_members)

    calculated = vacation.calculate_price()
    final_price = custom_price if custom_price is not None else calculated
    if final_price is not None:
        vacation.price = final_price
        vacation.save(update_fields=['price', 'updated_at'])

    return JsonResponse({
        'success': True,
        'request': _serialize_vacation_request(vacation),
        'download_url': reverse('main:download_vacation_request', args=[vacation.id]),
    })


@api_login_required
@require_http_methods(['GET'])
def api_material_requests(request):
    search = request.GET.get('search', '').strip().lower()
    if is_admin(request.user):
        qs = MaterialAssistanceRequest.objects.all().select_related('worker', 'user').order_by('-created_at')
    else:
        qs = MaterialAssistanceRequest.objects.filter(worker__user=request.user).select_related('worker', 'user').order_by('-created_at')

    if search:
        ids = []
        for item in qs:
            if (
                search in (item.worker.full_name or '').lower()
                or search in (item.worker.personnel_number or '').lower()
                or search in (item.get_assistance_type_display() or '').lower()
            ):
                ids.append(item.id)
        qs = qs.filter(id__in=ids)

    return JsonResponse({'success': True, 'results': [_serialize_material_request(i) for i in qs]})


@api_login_required
@require_http_methods(['POST'])
def api_create_material_request(request):
    payload = _json_payload(request)
    source = request.POST if request.POST else payload

    worker_id = source.get('worker_id')
    if not worker_id:
        return _api_error('Не выбран работник')

    worker = _worker_scope_for_user(request.user, worker_id)

    assistance_type = (source.get('assistance_type') or '').strip()
    amount_raw = source.get('amount') or '0'
    account_type = source.get('account_type')
    account_number = (source.get('account_number') or '').strip()

    if not assistance_type:
        return _api_error('Не выбран вид помощи')
    if account_type not in dict(MaterialAssistanceRequest.ACCOUNT_TYPE_CHOICES):
        return _api_error('Некорректный тип счета')
    if not account_number:
        return _api_error('Не указан номер счета')
    if not account_number.startswith('KZ'):
        return _api_error('Номер счета должен начинаться с KZ')
    if len(account_number) != 20:
        return _api_error('Номер счета должен содержать KZ и 18 цифр')
    if not account_number[2:].isdigit():
        return _api_error('После KZ должны быть только цифры')

    if worker.status == 'pensioner':
        if MaterialAssistanceRequest.objects.filter(worker=worker, assistance_type=assistance_type).exists():
            return _api_error('Повторное оформление запрещено: заявление на этот вид помощи уже существует')
        if assistance_type == 'treatment' and CoalRequest.objects.filter(worker=worker).exists():
            return _api_error('Нельзя оформить помощь на лечение: для пенсионера уже есть заявление на уголь')
        amount_decimal = Decimal('0')
    else:
        try:
            amount_decimal = Decimal(str(amount_raw))
        except (InvalidOperation, TypeError, ValueError):
            return _api_error('Некорректная сумма')
        if amount_decimal <= 0:
            return _api_error('Сумма должна быть больше 0')

    with transaction.atomic():
        if account_type == '20_digit':
            worker.account_20_digit = account_number
        else:
            worker.current_account = account_number
        worker.save()

        item = MaterialAssistanceRequest.objects.create(
            user=request.user,
            worker=worker,
            assistance_type=assistance_type,
            amount=amount_decimal,
            account_type=account_type,
            account_number=account_number,
        )

    return JsonResponse({
        'success': True,
        'request': _serialize_material_request(item),
        'download_url': reverse('main:download_material_assistance', args=[item.id]),
    })


@api_login_required
@require_http_methods(['GET'])
def api_coal_requests(request):
    search = request.GET.get('search', '').strip().lower()
    if is_admin(request.user):
        qs = CoalRequest.objects.all().select_related('worker', 'user').order_by('-created_at')
    else:
        qs = CoalRequest.objects.filter(worker__user=request.user).select_related('worker', 'user').order_by('-created_at')

    if search:
        ids = []
        for item in qs:
            if (
                search in (item.worker.full_name or '').lower()
                or search in (item.worker.personnel_number or '').lower()
                or search in (item.worker.department or '').lower()
            ):
                ids.append(item.id)
        qs = qs.filter(id__in=ids)

    return JsonResponse({'success': True, 'results': [_serialize_coal_request(i) for i in qs]})


@api_login_required
@require_http_methods(['POST'])
def api_create_coal_request(request):
    payload = _json_payload(request)
    source = request.POST if request.POST else payload

    worker_id = source.get('worker_id')
    if not worker_id:
        return _api_error('Не выбран пенсионер')

    worker = _worker_scope_for_user(request.user, worker_id)
    if worker.status != 'pensioner':
        return _api_error('Заявление на уголь доступно только для пенсионеров')

    if CoalRequest.objects.filter(worker=worker).exists():
        return _api_error('Повторное оформление запрещено: для пенсионера уже есть заявление на уголь')

    if MaterialAssistanceRequest.objects.filter(worker=worker, worker__status='pensioner', assistance_type='treatment').exists():
        return _api_error('Нельзя оформить уголь: для пенсионера уже есть заявление на материальную помощь (лекарства)')

    account_type = source.get('account_type')
    account_number = (source.get('account_number') or '').strip()

    if account_type not in dict(CoalRequest.ACCOUNT_TYPE_CHOICES):
        return _api_error('Некорректный тип счета')

    if not account_number:
        return _api_error('Не указан номер счета')
    if not account_number.startswith('KZ'):
        return _api_error('Номер счета должен начинаться с KZ')
    if len(account_number) != 20:
        return _api_error('Номер счета должен содержать KZ и 18 цифр')
    if not account_number[2:].isdigit():
        return _api_error('После KZ должны быть только цифры')

    with transaction.atomic():
        if request.FILES.get('passport_file'):
            worker.house_passport_file = request.FILES['passport_file']
        if request.FILES.get('pensioner_id_file'):
            worker.pensioner_id_file = request.FILES['pensioner_id_file']

        if account_type == '20_digit':
            worker.account_20_digit = account_number
        else:
            worker.current_account = account_number
        worker.save()

        item = CoalRequest.objects.create(
            user=request.user,
            worker=worker,
            account_type=account_type,
            account_number=account_number,
        )

    return JsonResponse({
        'success': True,
        'request': _serialize_coal_request(item),
        'download_url': reverse('main:download_coal_request', args=[item.id]),
    })


@api_login_required
@require_http_methods(['GET'])
def api_funeral_requests(request):
    search = request.GET.get('search', '').strip().lower()
    if is_admin(request.user):
        qs = FuneralRequest.objects.all().select_related('worker', 'user').order_by('-created_at')
    else:
        qs = FuneralRequest.objects.filter(worker__user=request.user).select_related('worker', 'user').order_by('-created_at')

    if search:
        ids = []
        for item in qs:
            if (
                search in (item.worker.full_name or '').lower()
                or search in (item.applicant_full_name or '').lower()
                or search in (item.worker.personnel_number or '').lower()
            ):
                ids.append(item.id)
        qs = qs.filter(id__in=ids)

    return JsonResponse({'success': True, 'results': [_serialize_funeral_request(i) for i in qs]})


@api_login_required
@require_http_methods(['POST'])
def api_create_funeral_request(request):
    payload = _json_payload(request)
    source = request.POST if request.POST else payload

    worker_id = source.get('worker_id')
    if not worker_id:
        return _api_error('Не выбран пенсионер')

    worker = _worker_scope_for_user(request.user, worker_id)
    if worker.status != 'pensioner':
        return _api_error('Заявление на погребение доступно только для пенсионеров')

    applicant_full_name = (source.get('applicant_full_name') or '').strip()
    applicant_inn = ''.join(c for c in (source.get('applicant_inn') or '') if c.isdigit())
    account_type = source.get('account_type')
    account_number = (source.get('account_number') or '').strip()
    death_date_raw = (source.get('death_date') or '').strip()

    if not applicant_full_name:
        return _api_error('Не указано ФИО заявителя')
    if len(applicant_inn) != 12:
        return _api_error('ИИН должен содержать 12 цифр')
    if account_type not in dict(FuneralRequest.ACCOUNT_TYPE_CHOICES):
        return _api_error('Некорректный тип счета')
    if not account_number:
        return _api_error('Не указан номер счета')
    if not account_number.startswith('KZ'):
        return _api_error('Номер счета должен начинаться с KZ')
    if len(account_number) != 20:
        return _api_error('Номер счета должен содержать KZ и 18 цифр')
    if not account_number[2:].isdigit():
        return _api_error('После KZ должны быть только цифры')

    death_date = None
    if death_date_raw:
        try:
            death_date = datetime.strptime(death_date_raw, '%Y-%m-%d').date()
        except ValueError:
            return _api_error('Некорректная дата смерти пенсионера')
        if death_date > date.today():
            return _api_error('Дата смерти не может быть в будущем')

    with transaction.atomic():
        should_update_worker = False
        if request.FILES.get('death_certificate_file'):
            worker.death_certificate_file = request.FILES['death_certificate_file']
            should_update_worker = True
        if death_date:
            worker.death_date = death_date
            should_update_worker = True
        if should_update_worker:
            worker.is_dead = True
            worker.save()

        item = FuneralRequest.objects.create(
            user=request.user,
            worker=worker,
            applicant_full_name=applicant_full_name,
            applicant_inn=applicant_inn,
            account_type=account_type,
            account_number=account_number,
        )

        if request.FILES.get('applicant_id_file'):
            item.applicant_id_file = request.FILES['applicant_id_file']
            item.save(update_fields=['applicant_id_file', 'updated_at'])

    return JsonResponse({
        'success': True,
        'request': _serialize_funeral_request(item),
        'download_url': reverse('main:download_funeral_request', args=[item.id]),
        'worker_marked_dead': bool(worker.is_dead),
    })


@api_login_required
@require_http_methods(['GET', 'POST'])
def api_vacation_limits(request):
    if request.method == 'GET':
        if is_admin(request.user):
            return JsonResponse({'success': True, 'limits': []})

        result = []
        for resort in ('zhartas', 'shakhter'):
            limit, _ = VacationLimit.get_or_create_limit(request.user, resort)
            result.append({
                'resort': resort,
                'resort_display': dict(VacationLimit.RESORT_CHOICES).get(resort, resort),
                'limit': limit.limit,
                'used': limit.get_used_places(),
                'remaining': limit.get_remaining_places(),
                'period_start': _date_iso(limit.period_start),
                'period_start_human': _date_human(limit.period_start),
            })
        return JsonResponse({'success': True, 'limits': result})

    if is_admin(request.user):
        return _api_error('Для администратора лимиты не используются', status=403)

    payload = _json_payload(request)
    source = request.POST if request.POST else payload

    resort = (source.get('resort') or 'zhartas').strip()
    if resort not in ('zhartas', 'shakhter'):
        return _api_error('Некорректный курорт')

    try:
        new_limit = int(source.get('limit'))
    except (TypeError, ValueError):
        return _api_error('Некорректное значение лимита')

    if new_limit < 0:
        return _api_error('Лимит не может быть отрицательным')

    limit, created = VacationLimit.get_or_create_limit(request.user, resort)
    old_limit = limit.limit
    if not created and old_limit > 0 and new_limit < old_limit:
        return _api_error(f'Можно только увеличить лимит. Текущий: {limit.limit}')

    limit.limit = new_limit
    if created or old_limit == 0:
        limit.is_initial = True
    else:
        limit.is_initial = False
    limit.save()

    return JsonResponse({
        'success': True,
        'limit': {
            'resort': resort,
            'resort_display': dict(VacationLimit.RESORT_CHOICES).get(resort, resort),
            'limit': limit.limit,
            'used': limit.get_used_places(),
            'remaining': limit.get_remaining_places(),
            'period_start': _date_iso(limit.period_start),
            'period_start_human': _date_human(limit.period_start),
        },
    })


@api_login_required
@require_http_methods(['GET'])
def api_reports(request):
    user_is_admin = is_admin(request.user)
    selected_user_id = request.GET.get('user_id')
    selected_user_id_int = None
    if user_is_admin and selected_user_id:
        try:
            selected_user_id_int = int(selected_user_id)
        except (TypeError, ValueError):
            selected_user_id_int = None

    if user_is_admin:
        vacation = VacationRequest.objects.all().select_related('worker', 'user').prefetch_related('family_members').defer('price')
        material = MaterialAssistanceRequest.objects.all().select_related('worker', 'user')
        coal = CoalRequest.objects.all().select_related('worker', 'user')
        funeral = FuneralRequest.objects.all().select_related('worker', 'user')
        if selected_user_id_int:
            vacation = vacation.filter(user_id=selected_user_id_int)
            material = material.filter(user_id=selected_user_id_int)
            coal = coal.filter(user_id=selected_user_id_int)
            funeral = funeral.filter(user_id=selected_user_id_int)
    else:
        vacation = VacationRequest.objects.filter(worker__user=request.user).select_related('worker', 'user').prefetch_related('family_members').defer('price')
        material = MaterialAssistanceRequest.objects.filter(worker__user=request.user).select_related('worker', 'user')
        coal = CoalRequest.objects.filter(worker__user=request.user).select_related('worker', 'user')
        funeral = FuneralRequest.objects.filter(worker__user=request.user).select_related('worker', 'user')

    items = []
    items.extend(_serialize_vacation_request(v) for v in vacation)
    items.extend(_serialize_material_request(v) for v in material)
    items.extend(_serialize_coal_request(v) for v in coal)
    items.extend(_serialize_funeral_request(v) for v in funeral)

    items.sort(key=lambda x: x.get('created_at_iso') or '', reverse=True)

    return JsonResponse({'success': True, 'results': items})


@api_login_required
@require_http_methods(['GET'])
def api_statements(request):
    selected_period_start = request.GET.get('period_start')
    if selected_period_start:
        try:
            period_start = date.fromisoformat(selected_period_start)
            period_end = _period_end_from_start(period_start)
        except Exception:
            period_start, period_end = _get_statement_period()
    else:
        period_start, period_end = _get_statement_period()

    user_is_admin = is_admin(request.user)

    if user_is_admin:
        zhartas_qs = VacationRequest.objects.filter(
            resort='zhartas',
            start_date__gte=period_start,
            start_date__lte=period_end,
            is_rejected=False,
        ).select_related('worker', 'user').prefetch_related('family_members').defer('price').order_by('worker__full_name')

        shakhter_qs = VacationRequest.objects.filter(
            resort='shakhter',
            start_date__gte=period_start,
            start_date__lte=period_end,
            is_rejected=False,
        ).select_related('worker', 'user').prefetch_related('family_members').defer('price').order_by('worker__full_name')
    else:
        zhartas_qs = VacationRequest.objects.filter(
            user=request.user,
            resort='zhartas',
            start_date__gte=period_start,
            start_date__lte=period_end,
            is_rejected=False,
        ).select_related('worker').prefetch_related('family_members').defer('price').order_by('worker__full_name')

        shakhter_qs = VacationRequest.objects.filter(
            user=request.user,
            resort='shakhter',
            start_date__gte=period_start,
            start_date__lte=period_end,
            is_rejected=False,
        ).select_related('worker').prefetch_related('family_members').defer('price').order_by('worker__full_name')

    zhartas_rows = []
    zhartas_total = 0.0
    for idx, vacation in enumerate(zhartas_qs, 1):
        vouchers = vacation.get_places_count()
        bed_days = vouchers * vacation.get_duration_days()
        effective_price = _vacation_effective_price(vacation)
        try:
            price = float(effective_price) if effective_price is not None else 0.0
        except (TypeError, ValueError, InvalidOperation):
            price = 0.0
        zhartas_total += price
        zhartas_rows.append({
            'number': idx,
            'full_name': vacation.worker.full_name,
            'personnel_number': vacation.worker.personnel_number,
            'vouchers_count': vouchers,
            'bed_days': bed_days,
            'price': price,
            'vacation_id': vacation.id,
            'worker_id': vacation.worker.id,
            'user_account': vacation.user.username if user_is_admin else None,
        })

    shakhter_rows = []
    shakhter_total = 0.0
    for idx, vacation in enumerate(shakhter_qs, 1):
        vouchers = vacation.get_places_count()
        bed_days = vouchers * vacation.get_duration_days()
        effective_price = _vacation_effective_price(vacation)
        try:
            price = float(effective_price) if effective_price is not None else 0.0
        except (TypeError, ValueError, InvalidOperation):
            price = 0.0
        shakhter_total += price
        shakhter_rows.append({
            'number': idx,
            'full_name': vacation.worker.full_name,
            'personnel_number': vacation.worker.personnel_number,
            'vouchers_count': vouchers,
            'bed_days': bed_days,
            'price': price,
            'vacation_id': vacation.id,
            'worker_id': vacation.worker.id,
            'user_account': vacation.user.username if user_is_admin else None,
        })

    if user_is_admin:
        today = timezone.now().date()
        is_current_period = period_start <= today <= period_end
        status_code = 'active' if is_current_period else 'closed'
        status_display = 'Ведется' if is_current_period else 'Закрыт'
        zhartas_status = {'code': status_code, 'label': status_display}
        shakhter_status = {'code': status_code, 'label': status_display}
    else:
        zhartas_statement, _ = Statement.get_or_create_statement(request.user, period_start, period_end, 'zhartas')
        shakhter_statement, _ = Statement.get_or_create_statement(request.user, period_start, period_end, 'shakhter')
        zhartas_status = {'code': zhartas_statement.status, 'label': zhartas_statement.get_status_display()}
        shakhter_status = {'code': shakhter_statement.status, 'label': shakhter_statement.get_status_display()}

    period_candidates = set()
    if user_is_admin:
        statement_qs = Statement.objects.all().order_by('-period_start')
        period_candidates.update(statement_qs.values_list('period_start', flat=True))
        period_candidates.update(VacationRequest.objects.values_list('start_date', flat=True))
    else:
        statement_qs = Statement.objects.filter(user=request.user).order_by('-period_start')
        period_candidates.update(statement_qs.values_list('period_start', flat=True))
        period_candidates.update(VacationRequest.objects.filter(user=request.user).values_list('start_date', flat=True))

    normalized_periods = set()
    for d in period_candidates:
        if not d:
            continue
        normalized_periods.add(date(d.year, d.month, 1))

    normalized_periods.add(period_start)
    all_periods = sorted(list(normalized_periods), reverse=True)

    return JsonResponse({
        'success': True,
        'period_start': _date_iso(period_start),
        'period_end': _date_iso(period_end),
        'period_start_human': _date_human(period_start),
        'period_end_human': _date_human(period_end),
        'all_periods': [
            {
                'period_start': _date_iso(p),
                'label': f"{_date_human(p)} - {_date_human(_period_end_from_start(p))}",
            }
            for p in all_periods
        ],
        'zhartas': {
            'status': zhartas_status,
            'rows': zhartas_rows,
            'total_sum': zhartas_total,
            'excel_url': f"{reverse('main:generate_zhartas_statement_excel')}?period_start={_date_iso(period_start)}",
        },
        'shakhter': {
            'status': shakhter_status,
            'rows': shakhter_rows,
            'total_sum': shakhter_total,
            'excel_url': f"{reverse('main:generate_shakhter_statement_excel')}?period_start={_date_iso(period_start)}",
        },
    })
