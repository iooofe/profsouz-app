from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, FileResponse
import os
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, date
import calendar
from decimal import Decimal, InvalidOperation
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from io import BytesIO
from urllib.parse import quote
from .forms import LoginForm, WorkerForm, FamilyMemberForm, VacationRequestForm, MaterialAssistanceRequestForm, CoalRequestForm, FuneralRequestForm
from .models import Worker, FamilyMember, VacationRequest, VacationLimit, Statement, MaterialAssistanceRequest, CoalRequest, FuneralRequest

EXCEL_HEADER_COLOR = "1F4F8F"
EXCEL_STATUS_ACTIVE_COLOR = "2D7D4A"
EXCEL_STATUS_CLOSED_COLOR = "6E7888"
EXCEL_TOTAL_FILL_COLOR = "F0F4FA"
EXCEL_BORDER_COLOR = "D8DEE8"
EXCEL_CURRENCY_FORMAT = '#,##0.00'
WORKER_CATEGORY_ALL = 'all'
WORKER_CATEGORY_WORKERS = 'workers'
WORKER_CATEGORY_PENSIONERS = 'pensioners'
WORKER_CATEGORY_REGRESS = 'regress'


def is_admin(user):
    """Проверяет, является ли пользователь администратором"""
    return user.username == 'АДМИН' or user.is_staff or user.is_superuser


def transliterate_filename(filename):
    """Транслитерация кириллицы в латиницу для имени файла"""
    translit_map = {
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'E',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
        'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    }
    result = ''
    for char in filename:
        result += translit_map.get(char, char)
    return result


def safe_excel_sheet_title(title):
    """Безопасный заголовок листа Excel (ограничение 31 символ и запрещенные знаки)."""
    invalid_chars = {'\\', '/', '*', '?', ':', '[', ']'}
    clean_title = ''.join('_' if ch in invalid_chars else ch for ch in title)
    return clean_title[:31] or "Sheet1"


def login_view(request):
    if request.user.is_authenticated:
        return redirect('main:index')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username'].strip()
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    # Проверяем что пользователь действительно залогинен
                    if request.user.is_authenticated:
                        messages.success(request, f'Добро пожаловать, {user.username}!')
                        next_url = request.GET.get('next', None)
                        if next_url:
                            return redirect(next_url)
                        return redirect('main:index')
                    else:
                        messages.error(request, 'Ошибка входа. Сессия не создана.')
                else:
                    messages.error(request, 'Ваш аккаунт неактивен')
            else:
                messages.error(request, 'Неверный логин или пароль. Проверьте правильность ввода.')
        else:
            # Форма невалидна, показываем ошибки
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'Ошибка в поле {field}: {error}')
    else:
        form = LoginForm()
    
    return render(request, 'main/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы')
    return redirect('main:login')


def get_period_end_for_start(period_start):
    """Возвращает конец периода: 30 число текущего месяца (или последний день месяца)."""
    last_day = calendar.monthrange(period_start.year, period_start.month)[1]
    return date(period_start.year, period_start.month, min(30, last_day))


def normalize_period_start(value):
    """Нормализует дату к началу периода: 1 число месяца."""
    return date(value.year, value.month, 1)


def get_statement_period():
    """Получает текущий период ведомости: с 1 по 30 число текущего месяца."""
    today = timezone.now().date()
    period_start = normalize_period_start(today)
    return period_start, get_period_end_for_start(period_start)


def get_requested_period(request, default_period_resolver=None):
    """Возвращает период по query-параметрам.

    Поддерживает два режима:
    - `start_date` + `end_date` для произвольного диапазона
    - `period_start` для месячного периода с 1 по 30 число
    """
    default_period_resolver = default_period_resolver or get_statement_period

    start_date_raw = (request.GET.get('start_date') or '').strip()
    end_date_raw = (request.GET.get('end_date') or '').strip()
    if start_date_raw and end_date_raw:
        try:
            period_start = date.fromisoformat(start_date_raw)
            period_end = date.fromisoformat(end_date_raw)
            if period_end < period_start:
                period_start, period_end = period_end, period_start
            return period_start, period_end
        except (ValueError, TypeError):
            return default_period_resolver()

    selected_period_start = (request.GET.get('period_start') or '').strip()
    if selected_period_start:
        try:
            period_start = date.fromisoformat(selected_period_start)
            return period_start, get_period_end_for_start(period_start)
        except (ValueError, TypeError):
            return default_period_resolver()

    return default_period_resolver()


def get_worker_category_filter(request):
    return (request.GET.get('worker_category') or WORKER_CATEGORY_ALL).strip()


def get_account_type_filter(request):
    return (request.GET.get('account_type_filter') or 'all').strip()


def apply_worker_category_filter(queryset, category, status_field='worker__status'):
    if category == WORKER_CATEGORY_WORKERS:
        statuses = [Worker.STATUS_WORKER, Worker.STATUS_REGRESSNIK_WORKER]
    elif category == WORKER_CATEGORY_PENSIONERS:
        statuses = [Worker.STATUS_PENSIONER, Worker.STATUS_REGRESSNIK_PENSIONER]
    elif category == WORKER_CATEGORY_REGRESS:
        statuses = [
            Worker.STATUS_REGRESSNIK,
            Worker.STATUS_REGRESSNIK_WORKER,
            Worker.STATUS_REGRESSNIK_PENSIONER,
        ]
    else:
        return queryset
    return queryset.filter(**{f'{status_field}__in': statuses})


def apply_request_account_type_filter(queryset, account_type_filter):
    if account_type_filter in {'20_digit', 'current'}:
        return queryset.filter(account_type=account_type_filter)
    return queryset


def get_admin_selected_user_id(request):
    """Возвращает выбранный аккаунт для админских фильтров списков/отчетов."""
    if not is_admin(request.user):
        return None
    raw = (request.GET.get('user_id') or '').strip()
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def get_print_enterprise_name(request, selected_user_id=None):
    """Возвращает имя предприятия для шапки печатных списков."""
    if is_admin(request.user):
        if selected_user_id:
            username = User.objects.filter(id=selected_user_id).values_list('username', flat=True).first()
            return username or 'Неизвестное предприятие'
        return 'Общий список (все предприятия)'
    return request.user.username


def get_request_enterprise_name(request_obj):
    """Возвращает название предприятия/аккаунта для шапки заявлений."""
    worker_user = getattr(getattr(request_obj, 'worker', None), 'user', None)
    if worker_user and getattr(worker_user, 'username', None):
        return worker_user.username
    owner_user = getattr(request_obj, 'user', None)
    if owner_user and getattr(owner_user, 'username', None):
        return owner_user.username
    return '—'


def get_enterprise_company_name(enterprise_name):
    """Возвращает отображаемое наименование компании с учетом исключений."""
    normalized = (enterprise_name or '').strip().upper()
    if normalized in {'УТТ', 'КПТУ', 'АДМИН'}:
        return 'АО «QARMЕТ»'
    return 'ТОО Karaganda komir'


def get_vacation_header_lines(vacation):
    """Возвращает 2 строки шапки заявления на путевку."""
    enterprise_name = get_request_enterprise_name(vacation)
    company_name = get_enterprise_company_name(enterprise_name)
    return (
        'председателю проф союзного коммитета___________',
        f'{enterprise_name} ({company_name})',
    )


def parse_optional_custom_price(raw_value, resort):
    value = (raw_value or '').strip()
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


def get_vacation_effective_price(vacation):
    """Возвращает сохраненную цену путевки (если валидна), иначе расчетную."""
    calculated_price = vacation.calculate_price()
    try:
        stored_price = vacation.price
    except Exception:
        stored_price = None
    if stored_price is None:
        return calculated_price
    try:
        return stored_price if stored_price > 0 else calculated_price
    except Exception:
        return calculated_price


def get_vacation_price_float(vacation):
    effective_price = get_vacation_effective_price(vacation)
    try:
        return float(effective_price) if effective_price is not None else 0.0
    except (TypeError, ValueError, InvalidOperation):
        return 0.0


def get_or_create_statement_for_period(user, period_start, period_end, resort='zhartas'):
    """Получает или создает ведомость для периода, закрывает истекшие"""
    # Закрываем все истекшие ведомости
    Statement.close_expired_statements()
    
    # Получаем или создаем ведомость для текущего периода
    statement, created = Statement.get_or_create_statement(user, period_start, period_end, resort)
    
    # Если период истек, закрываем ведомость
    today = timezone.now().date()
    if period_end < today and statement.status == 'active':
        statement.status = 'closed'
        statement.save()
    
    return statement


@login_required
def index(request):
    user_is_admin = is_admin(request.user)
    
    # Фильтруем работников: для админа - всех, для обычного пользователя - только своих
    if user_is_admin:
        all_workers = Worker.objects.all().select_related('user')
    else:
        all_workers = Worker.objects.filter(user=request.user)
    
    workers = all_workers
    search_query = request.GET.get('search', '').strip()
    
    if search_query:
        # SQLite не поддерживает регистронезависимый поиск для кириллицы через __icontains
        # Поэтому получаем всех работников и фильтруем в Python
        search_lower = search_query.lower()
        workers_list = list(workers)
        workers_filtered = []
        for worker in workers_list:
            if (search_lower in (worker.full_name or '').lower() or
                search_lower in (worker.personnel_number or '').lower() or
                search_lower in (worker.inn or '').lower() or
                search_lower in (worker.department or '').lower() or
                search_lower in (worker.position or '').lower() or
                search_lower in (worker.phone or '').lower()):
                workers_filtered.append(worker.id)
        workers = workers.filter(id__in=workers_filtered)

    # Пагинация списка работников для ускорения рендера страницы
    workers_count = workers.count()
    workers_paginator = Paginator(workers, 100)
    workers_page = workers_paginator.get_page(request.GET.get('page', 1))
    workers = workers_page.object_list
    
    worker_form = WorkerForm()
    
    if request.method == 'POST' and 'create_worker' in request.POST:
        worker_form = WorkerForm(request.POST, request.FILES)
        if worker_form.is_valid():
            worker = worker_form.save(commit=False)
            # Для админа можно выбрать пользователя, для обычного - только свой
            if not user_is_admin:
                worker.user = request.user
            worker.save()
            
            # Обработка членов семьи
            family_count = int(request.POST.get('family_count', 0))
            for i in range(family_count):
                family_full_name = request.POST.get(f'family_{i}_full_name', '').strip()
                if family_full_name:  # Только если указано ФИО
                    family_form = FamilyMemberForm({
                        'full_name': family_full_name,
                        'relationship': request.POST.get(f'family_{i}_relationship', ''),
                        'id_number': request.POST.get(f'family_{i}_id_number', ''),
                        'id_issue_date': request.POST.get(f'family_{i}_id_issue_date', '') or None,
                        'id_issued_by': request.POST.get(f'family_{i}_id_issued_by', ''),
                        'birth_date': request.POST.get(f'family_{i}_birth_date', '') or None,
                    })
                    if family_form.is_valid():
                        family_member = family_form.save(commit=False)
                        family_member.worker = worker
                        family_member.save()
            
            messages.success(request, f'Работник {worker.full_name} успешно создан!')
            # Редирект с сохранением активной вкладки
            return redirect(f"{reverse('main:index')}?tab=workers")
    
    # Получаем заявления для вкладки отчетов
    if user_is_admin:
        vacation_requests = VacationRequest.objects.all().select_related('worker', 'user').prefetch_related('family_members').defer('price').order_by('-created_at')
        material_assistance_requests = MaterialAssistanceRequest.objects.all().select_related('worker', 'user').order_by('-created_at')
        coal_requests = CoalRequest.objects.all().select_related('worker', 'user').order_by('-created_at')
        funeral_requests = FuneralRequest.objects.all().select_related('worker', 'user').order_by('-created_at')
    else:
        # Показываем все заявления работников, принадлежащих текущему пользователю
        vacation_requests = VacationRequest.objects.filter(worker__user=request.user).select_related('worker').prefetch_related('family_members').defer('price').order_by('-created_at')
        material_assistance_requests = MaterialAssistanceRequest.objects.filter(worker__user=request.user).select_related('worker').order_by('-created_at')
        coal_requests = CoalRequest.objects.filter(worker__user=request.user).select_related('worker').order_by('-created_at')
        funeral_requests = FuneralRequest.objects.filter(worker__user=request.user).select_related('worker').order_by('-created_at')
    
    # Получаем информацию о лимитах (для админа лимит не нужен)
    if user_is_admin:
        zhartas_limit = None
        zhartas_used_places = 0
        zhartas_remaining_places = 999999  # Неограниченно для админа
        shakhter_limit = None
        shakhter_used_places = 0
        shakhter_remaining_places = 999999  # Неограниченно для админа
    else:
        zhartas_limit, created = VacationLimit.get_or_create_limit(request.user, 'zhartas')
        zhartas_used_places = zhartas_limit.get_used_places()
        zhartas_remaining_places = zhartas_limit.get_remaining_places()
        
        shakhter_limit, created = VacationLimit.get_or_create_limit(request.user, 'shakhter')
        shakhter_used_places = shakhter_limit.get_used_places()
        shakhter_remaining_places = shakhter_limit.get_remaining_places()
    
    # Получаем данные для ведомости Жартас
    period_start, period_end = get_statement_period()
    
    # Получаем все ведомости для выбора периода
    if user_is_admin:
        all_zhartas_statements = Statement.objects.filter(resort='zhartas').order_by('-period_start')
        all_shakhter_statements = Statement.objects.filter(resort='shakhter').order_by('-period_start')
    else:
        all_zhartas_statements = Statement.objects.filter(
            user=request.user,
            resort='zhartas'
        ).order_by('-period_start')
        
        all_shakhter_statements = Statement.objects.filter(
            user=request.user,
            resort='shakhter'
        ).order_by('-period_start')
    
    # Проверяем, выбран ли конкретный период через GET параметр
    selected_period_start = request.GET.get('period_start')
    if selected_period_start:
        try:
            period_start = date.fromisoformat(selected_period_start)
            # Вычисляем period_end для выбранного периода
            period_end = get_period_end_for_start(period_start)
        except (ValueError, TypeError):
            # Если невалидная дата, используем текущий период
            period_start, period_end = get_statement_period()
    else:
        # Используем текущий период по умолчанию
        period_start, period_end = get_statement_period()
    
    # Получаем или создаем ведомость для периода Жартас (для админа не создаем ведомость)
    if user_is_admin:
        zhartas_statement = None
    else:
        zhartas_statement = get_or_create_statement_for_period(request.user, period_start, period_end, 'zhartas')
    
    # Получаем путевки для выбранного периода и только не отмененные
    if user_is_admin:
        zhartas_vacations = VacationRequest.objects.filter(
            resort='zhartas',
            start_date__gte=period_start,
            start_date__lte=period_end,
            is_rejected=False
        ).select_related('worker', 'user').prefetch_related('family_members').defer('price').order_by('worker__full_name')
    else:
        zhartas_vacations = VacationRequest.objects.filter(
            user=request.user,
            resort='zhartas',
            start_date__gte=period_start,
            start_date__lte=period_end,
            is_rejected=False
        ).select_related('worker').prefetch_related('family_members').defer('price').order_by('worker__full_name')
    
    # Подготавливаем данные для таблицы ведомости Жартас
    zhartas_statement_data = []
    zhartas_total_sum = 0
    for idx, vacation in enumerate(zhartas_vacations, 1):
        people_count = vacation.get_places_count()
        days = vacation.get_duration_days()
        bed_days = people_count * days
        price = get_vacation_price_float(vacation)
        zhartas_total_sum += price
        
        zhartas_statement_data.append({
            'number': idx,
            'full_name': vacation.worker.full_name,
            'personnel_number': vacation.worker.personnel_number,
            'vouchers_count': people_count,
            'bed_days': bed_days,
            'price': price,
            'vacation_id': vacation.id,  # ID путевки для перехода к отчету
            'worker_id': vacation.worker.id,  # ID работника для перехода к карточке
            'user_account': vacation.user.username if user_is_admin else None,  # Аккаунт для админа
        })
    
    # Получаем или создаем ведомость для периода Шахтер (для админа не создаем ведомость)
    if user_is_admin:
        shakhter_statement = None
    else:
        shakhter_statement = get_or_create_statement_for_period(request.user, period_start, period_end, 'shakhter')
    
    # Получаем путевки Шахтер для выбранного периода и только не отмененные
    if user_is_admin:
        shakhter_vacations = VacationRequest.objects.filter(
            resort='shakhter',
            start_date__gte=period_start,
            start_date__lte=period_end,
            is_rejected=False
        ).select_related('worker', 'user').prefetch_related('family_members').defer('price').order_by('worker__full_name')
    else:
        shakhter_vacations = VacationRequest.objects.filter(
            user=request.user,
            resort='shakhter',
            start_date__gte=period_start,
            start_date__lte=period_end,
            is_rejected=False
        ).select_related('worker').prefetch_related('family_members').defer('price').order_by('worker__full_name')
    
    # Подготавливаем данные для таблицы ведомости Шахтер
    shakhter_statement_data = []
    shakhter_total_sum = 0
    for idx, vacation in enumerate(shakhter_vacations, 1):
        people_count = vacation.get_places_count()
        days = vacation.get_duration_days()
        bed_days = people_count * days
        price = get_vacation_price_float(vacation)
        shakhter_total_sum += price
        
        shakhter_statement_data.append({
            'number': idx,
            'full_name': vacation.worker.full_name,
            'personnel_number': vacation.worker.personnel_number,
            'vouchers_count': people_count,
            'bed_days': bed_days,
            'price': price,
            'vacation_id': vacation.id,  # ID путевки для перехода к отчету
            'worker_id': vacation.worker.id,  # ID работника для перехода к карточке
            'user_account': vacation.user.username if user_is_admin else None,  # Аккаунт для админа
        })

    # Для админа нет модели ведомости, поэтому показываем вычисляемый статус периода
    if user_is_admin:
        today = timezone.now().date()
        is_current_period = period_start <= today <= period_end
        statement_status = 'active' if is_current_period else 'closed'
        statement_status_display = 'Ведется' if is_current_period else 'Закрыт'
        zhartas_statement_status = statement_status
        zhartas_statement_status_display = statement_status_display
        shakhter_statement_status = statement_status
        shakhter_statement_status_display = statement_status_display
    else:
        zhartas_statement_status = zhartas_statement.status
        zhartas_statement_status_display = zhartas_statement.get_status_display()
        shakhter_statement_status = shakhter_statement.status
        shakhter_statement_status_display = shakhter_statement.get_status_display()
    
    context = {
        'workers': workers,
        'workers_count': workers_count,
        'workers_page': workers_page,
        'all_workers_count': all_workers.count(),
        'search_query': search_query,
        'worker_form': worker_form,
        'vacation_requests': vacation_requests,
        'material_assistance_requests': material_assistance_requests,
        'coal_requests': coal_requests,
        'funeral_requests': funeral_requests,
        'material_assistance_form': MaterialAssistanceRequestForm(),
        'coal_request_form': CoalRequestForm(),
        'funeral_request_form': FuneralRequestForm(),
        'zhartas_limit': zhartas_limit,
        'zhartas_used_places': zhartas_used_places,
        'zhartas_remaining_places': zhartas_remaining_places,
        'shakhter_limit': shakhter_limit,
        'shakhter_used_places': shakhter_used_places,
        'shakhter_remaining_places': shakhter_remaining_places,
        'user_is_admin': user_is_admin,
        'zhartas_statement_data': zhartas_statement_data,
        'zhartas_statement_total_sum': zhartas_total_sum,
        'zhartas_statement': zhartas_statement,
        'all_zhartas_statements': all_zhartas_statements,
        'shakhter_statement_data': shakhter_statement_data,
        'shakhter_statement_total_sum': shakhter_total_sum,
        'shakhter_statement': shakhter_statement,
        'all_shakhter_statements': all_shakhter_statements,
        'zhartas_statement_status': zhartas_statement_status,
        'zhartas_statement_status_display': zhartas_statement_status_display,
        'shakhter_statement_status': shakhter_statement_status,
        'shakhter_statement_status_display': shakhter_statement_status_display,
        'statement_period_start': period_start,
        'statement_period_end': period_end,
    }
    return render(request, 'main/index.html', context)


@login_required
def worker_detail(request, worker_id):
    """Получение детальной информации о работнике для модального окна"""
    user_is_admin = is_admin(request.user)
    if user_is_admin:
        worker = get_object_or_404(Worker, id=worker_id)
    else:
        worker = get_object_or_404(Worker, id=worker_id, user=request.user)
    
    family_members = worker.family_members.all()

    data = {
        'id': worker.id,
        'full_name': worker.full_name,
        'personnel_number': worker.personnel_number or '',
        'inn': worker.inn or '—',
        'status': worker.get_status_display(),
        'is_union_member': 'Да' if worker.is_union_member else 'Нет',
        'department': worker.department,
        'position': worker.position,
        'is_contract_member': 'Да' if worker.is_contract_member else 'Нет',
        'phone': worker.phone or '—',
        'address': worker.address or '—',
        'id_number': worker.id_number or '—',
        'id_issue_date': worker.id_issue_date.strftime('%d.%m.%Y') if worker.id_issue_date else '—',
        'id_issued_by': worker.id_issued_by or '—',
        'has_benefits': 'Да' if worker.has_benefits else 'Нет',
        'benefits_file': reverse('main:download_worker_file', args=[worker.id, 'benefits']) if worker.benefits_file else None,
        'benefits_file_name': worker.benefits_file.name.split('/')[-1] if worker.benefits_file else None,
        'benefits_name': worker.benefits_name or '—',
        'has_miner_glory': 'Да' if worker.has_miner_glory else 'Нет',
        'miner_glory_file': reverse('main:download_worker_file', args=[worker.id, 'miner_glory']) if worker.miner_glory_file else None,
        'miner_glory_file_name': worker.miner_glory_file.name.split('/')[-1] if worker.miner_glory_file else None,
        'house_passport_file': reverse('main:download_worker_file', args=[worker.id, 'house_passport']) if worker.house_passport_file else None,
        'house_passport_file_name': worker.house_passport_file.name.split('/')[-1] if worker.house_passport_file else None,
        'pensioner_id_file': reverse('main:download_worker_file', args=[worker.id, 'pensioner_id']) if worker.pensioner_id_file else None,
        'pensioner_id_file_name': worker.pensioner_id_file.name.split('/')[-1] if worker.pensioner_id_file else None,
        'account_20_digit': worker.account_20_digit or '—',
        'current_account': worker.current_account or '—',
        'is_dead': 'Да' if worker.is_dead else 'Нет',
        'death_certificate_file': reverse('main:download_worker_file', args=[worker.id, 'death_certificate']) if worker.death_certificate_file else None,
        'death_certificate_file_name': worker.death_certificate_file.name.split('/')[-1] if worker.death_certificate_file else None,
        'family_members': [
            {
                'id': fm.id,
                'full_name': fm.full_name,
                'relationship': fm.get_relationship_display(),
                'relationship_code': fm.relationship,
                'id_number': fm.id_number or '—',
                'id_issue_date': fm.id_issue_date.strftime('%d.%m.%Y') if fm.id_issue_date else '—',
                'id_issued_by': fm.id_issued_by or '—',
                'birth_date': fm.birth_date.strftime('%Y-%m-%d') if fm.birth_date else None,
                'age': fm.get_age() if fm.birth_date else None,
            }
            for fm in family_members
        ]
    }
    
    return JsonResponse(data)


@login_required
def worker_edit(request, worker_id):
    """Редактирование работника"""
    user_is_admin = is_admin(request.user)
    if user_is_admin:
        worker = get_object_or_404(Worker, id=worker_id)
    else:
        worker = get_object_or_404(Worker, id=worker_id, user=request.user)
    
    if request.method == 'POST':
        worker_form = WorkerForm(request.POST, request.FILES, instance=worker)
        if worker_form.is_valid():
            # Валидируем все записи членов семьи перед сохранением,
            # чтобы не удалить существующие данные при частично невалидном вводе.
            family_count_raw = request.POST.get('family_count', 0)
            try:
                family_count = max(int(family_count_raw), 0)
            except (TypeError, ValueError):
                family_count = 0

            valid_family_forms = []
            invalid_family_forms = []

            for i in range(family_count):
                family_full_name = request.POST.get(f'family_{i}_full_name', '').strip()
                if family_full_name:
                    family_form = FamilyMemberForm({
                        'full_name': family_full_name,
                        'relationship': request.POST.get(f'family_{i}_relationship', ''),
                        'id_number': request.POST.get(f'family_{i}_id_number', ''),
                        'id_issue_date': request.POST.get(f'family_{i}_id_issue_date', '') or None,
                        'id_issued_by': request.POST.get(f'family_{i}_id_issued_by', ''),
                        'birth_date': request.POST.get(f'family_{i}_birth_date', '') or None,
                    })
                    if family_form.is_valid():
                        valid_family_forms.append(family_form)
                    else:
                        invalid_family_forms.append((i + 1, family_form))

            if invalid_family_forms:
                for member_number, family_form in invalid_family_forms:
                    for field_name, errors in family_form.errors.items():
                        field_label = family_form.fields[field_name].label if field_name in family_form.fields else field_name
                        for error in errors:
                            messages.error(request, f'Член семьи #{member_number}: {field_label} - {error}')
                messages.error(request, 'Исправьте ошибки в данных членов семьи и повторите сохранение.')
            else:
                with transaction.atomic():
                    worker = worker_form.save()
                    worker.family_members.all().delete()
                    for family_form in valid_family_forms:
                        family_member = family_form.save(commit=False)
                        family_member.worker = worker
                        family_member.save()

                messages.success(request, f'Работник {worker.full_name} успешно обновлен!')
                return redirect(f"{reverse('main:index')}?tab=workers")
    else:
        worker_form = WorkerForm(instance=worker)
    
    # Получаем членов семьи для формы
    family_members = worker.family_members.all()
    
    context = {
        'worker': worker,
        'worker_form': worker_form,
        'family_members': family_members,
    }
    return render(request, 'main/worker_edit.html', context)


@login_required
def worker_delete(request, worker_id):
    """Удаление работника"""
    user_is_admin = is_admin(request.user)
    if user_is_admin:
        worker = get_object_or_404(Worker, id=worker_id)
    else:
        worker = get_object_or_404(Worker, id=worker_id, user=request.user)
    
    if request.method == 'POST':
        worker_name = worker.full_name
        worker.delete()
        return JsonResponse({'success': True, 'message': f'Работник {worker_name} успешно удален!'})
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def search_workers(request):
    """Поиск работников для автодополнения и таблицы"""
    query = request.GET.get('q', '').strip()
    user_is_admin = is_admin(request.user)
    
    # Для админа показываем всех работников, для обычного пользователя - только своих
    if user_is_admin:
        workers = Worker.objects.all().select_related('user')
    else:
        workers = Worker.objects.filter(user=request.user)
    
    if query:
        # SQLite не поддерживает регистронезависимый поиск для кириллицы через __icontains
        # Поэтому получаем всех работников и фильтруем в Python
        query_lower = query.lower()
        workers_list = list(workers)
        workers_filtered = []
        for worker in workers_list:
            if (query_lower in (worker.full_name or '').lower() or
                query_lower in (worker.personnel_number or '').lower() or
                query_lower in (worker.inn or '').lower() or
                query_lower in (worker.department or '').lower() or
                query_lower in (worker.position or '').lower() or
                query_lower in (worker.phone or '').lower()):
                workers_filtered.append(worker.id)
        workers = workers.filter(id__in=workers_filtered)
    else:
        # Если запрос пустой, возвращаем всех работников (для обновления таблицы)
        pass
    
    # Ограничиваем количество для автодополнения, но не для таблицы
    # Если запрос есть - это автодополнение, если нет - это обновление таблицы
    if query:
        workers = workers[:20]
    
    results = []
    for worker in workers:
        # Аккуратно получаем логин пользователя, т.к. у части работников user может быть пустым
        user_account = None
        if user_is_admin and getattr(worker, 'user', None):
            user_account = worker.user.username
        
        results.append({
            'id': worker.id,
            'full_name': worker.full_name,
            'personnel_number': worker.personnel_number or '',
            'inn': worker.inn or '',
            'status': worker.status,
            'status_display': worker.get_status_display(),
            'department': worker.department or '',
            'position': worker.position or '',
            'phone': worker.phone or '+7',
            'is_dead': bool(worker.is_dead),
            'user_account': user_account,  # Аккаунт для админа (если есть связь с User)
            # Подсказки по счетам из карточки работника
            'card_account': getattr(worker, 'account_20_digit', '') or '',
            'current_account': getattr(worker, 'current_account', '') or '',
        })
    
    return JsonResponse({'results': results})


@login_required
def get_worker_with_family(request, worker_id):
    """Получение данных работника с членами семьи"""
    user_is_admin = is_admin(request.user)
    if user_is_admin:
        worker = get_object_or_404(Worker, id=worker_id)
    else:
        worker = get_object_or_404(Worker, id=worker_id, user=request.user)
    family_members = worker.family_members.all()
    
    data = {
        'id': worker.id,
        'full_name': worker.full_name,
        'personnel_number': worker.personnel_number or '',
        'inn': worker.inn or '',
        'status': worker.get_status_display(),
        'status_code': worker.status,  # Добавляем код статуса для проверки
        'department': worker.department,
        'position': worker.position,
        'phone': worker.phone or '',
        'address': worker.address or '',
        'family_members': [
            {
                'id': fm.id,
                'full_name': fm.full_name,
                'relationship': fm.get_relationship_display(),
                'id_number': fm.id_number or '',
                'id_issue_date': fm.id_issue_date.strftime('%d.%m.%Y') if fm.id_issue_date else '',
                'id_issued_by': fm.id_issued_by or '',
            }
            for fm in family_members
        ]
    }
    
    return JsonResponse(data)


@login_required
def create_vacation_request(request):
    """Создание заявления на путевку"""
    if request.method == 'POST':
        worker_id = request.POST.get('worker_id')
        
        if not worker_id:
            messages.error(request, 'Не выбран работник!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        user_is_admin = is_admin(request.user)
        
        try:
            if user_is_admin:
                worker = Worker.objects.get(id=worker_id)
            else:
                worker = Worker.objects.get(id=worker_id, user=request.user)
        except Worker.DoesNotExist:
            messages.error(request, 'Работник не найден!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Получаем данные из формы
        resort = request.POST.get('resort')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        custom_price_raw = request.POST.get('custom_price', '')
        
        # Проверка: пенсионеры не могут создавать заявления на Балхаш и Дискавери
        if worker.is_pensioner_like() and resort in ['balkhash', 'discovery']:
            resort_name = dict(VacationRequest.RESORT_CHOICES).get(resort, resort)
            messages.error(request, f'Пенсионеры не могут создавать заявления на курорт "{resort_name}"!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Валидация данных
        if not resort:
            messages.error(request, 'Не выбран курорт!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        if not start_date_str or not end_date_str:
            messages.error(request, 'Не указаны даты поездки!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Получаем и валидируем сезоны для ДОЦ "Орленок"
        seasons = []
        if resort == 'orlenok':
            seasons = request.POST.getlist('seasons')
            if not seasons:
                messages.error(request, 'Для ДОЦ "Орленок" необходимо выбрать хотя бы один сезон!')
                return redirect(f"{reverse('main:index')}?tab=applications")
            # Преобразуем в список чисел и валидируем
            try:
                seasons = [int(s) for s in seasons if s.isdigit()]
                if not seasons or not all(1 <= s <= 4 for s in seasons):
                    messages.error(request, 'Сезоны должны быть числами от 1 до 4!')
                    return redirect(f"{reverse('main:index')}?tab=applications")
            except (ValueError, TypeError):
                messages.error(request, 'Неверный формат сезонов!')
                return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Преобразуем строки в объекты date
        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError) as date_error:
            messages.error(request, f'Неверный формат даты: {str(date_error)}')
            return redirect(f"{reverse('main:index')}?tab=applications")

        if end_date < start_date:
            messages.error(request, 'Дата окончания не может быть раньше даты начала!')
            return redirect(f"{reverse('main:index')}?tab=applications")

        if start_date.year < 2000 or end_date.year < 2000:
            messages.error(request, 'Год в дате поездки должен быть не ранее 2000!')
            return redirect(f"{reverse('main:index')}?tab=applications")

        trip_days = (end_date - start_date).days + 1
        if trip_days > 31:
            messages.error(request, 'Длительность путевки не может превышать 31 день!')
            return redirect(f"{reverse('main:index')}?tab=applications")

        try:
            custom_price = parse_optional_custom_price(custom_price_raw, resort)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Получаем список выбранных членов семьи (нужно для всех пользователей)
        family_member_ids = request.POST.getlist('family_members')

        # Работник едет? (по умолчанию да)
        worker_goes = request.POST.get('worker_goes') in ('on', '1', 'true', 'True', 'да', 'Да')

        if not worker_goes and (not family_member_ids or len(family_member_ids) == 0):
            messages.error(request, 'Необходимо выбрать хотя бы одного отдыхающего: работник или члены семьи.')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Проверяем возраст детей/внуков
        if family_member_ids:
            family_members = FamilyMember.objects.filter(
                id__in=family_member_ids,
                worker=worker
            )
            
            for fm in family_members:
                # Проверяем только детей и внуков/внучек
                if fm.is_child_or_grandchild():
                    if not fm.birth_date:
                        messages.error(
                            request,
                            f'Для {fm.get_relationship_display().lower()} {fm.full_name} необходимо указать дату рождения!'
                        )
                        return redirect(f"{reverse('main:index')}?tab=applications")
                    
                    age = fm.get_age()
                    if age is None:
                        continue
                    
                    # Для ДОЦ "Орленок" - проверка на 14 лет
                    if resort == 'orlenok' and age >= 14:
                        messages.error(
                            request,
                            f'{fm.get_relationship_display()} {fm.full_name} не проходит по возрасту для ДОЦ "Орленок" (возраст {age} лет, требуется до 14 лет).'
                        )
                        return redirect(f"{reverse('main:index')}?tab=applications")
                    
                    # Для "Дискавери" - проверка на 18 лет и обязательный файл
                    if resort == 'discovery' and age >= 18:
                        study_certificate = request.FILES.get('study_certificate_file')
                        if not study_certificate:
                            messages.error(
                                request,
                                f'Для {fm.get_relationship_display().lower()} {fm.full_name} старше 18 лет (возраст {age} лет) на курорт "Дискавери" необходимо прикрепить справку об очном обучении!'
                            )
                            return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Проверяем лимит (для админа лимит не нужен)
        if not user_is_admin:
            from main.models import VacationLimit
            limit, created = VacationLimit.get_or_create_limit(request.user, resort)
            
            # Подсчитываем количество мест для нового заявления
            new_places = (1 if worker_goes else 0) + len(family_member_ids)  # работник (если едет) + члены семьи
            
            used_places = limit.get_used_places()
            remaining_places = limit.get_remaining_places()
            
            if new_places > remaining_places:
                resort_name = dict(VacationRequest.RESORT_CHOICES).get(resort, resort)
                messages.error(
                    request, 
                    f'Превышен лимит на путевки для {resort_name}! Доступно мест: {remaining_places}, требуется: {new_places}. '
                    f'Использовано: {used_places}/{limit.limit}'
                )
                return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Создаем заявление напрямую
        try:
            # Получаем файл справки об очном обучении (если есть)
            study_certificate_file = request.FILES.get('study_certificate_file')
            
            vacation = VacationRequest.objects.create(
                user=request.user,
                worker=worker,
                resort=resort,
                start_date=start_date,
                end_date=end_date,
                worker_goes=worker_goes,
                study_certificate_file=study_certificate_file,
                seasons=seasons
            )
            
            # Добавляем выбранных членов семьи
            if family_member_ids:
                family_members = FamilyMember.objects.filter(
                    id__in=family_member_ids,
                    worker=worker
                )
                vacation.family_members.set(family_members)
            
            # Рассчитываем и сохраняем цену
            calculated_price = vacation.calculate_price()
            final_price = custom_price if custom_price is not None else calculated_price
            if final_price is not None:
                vacation.price = final_price
                vacation.save()
            
            messages.success(request, f'Заявление на путевку для {worker.full_name} успешно создано!')
            # Переходим на вкладку отчетов и передаем параметры для автозагрузки файла
            return redirect(f"{reverse('main:index')}?tab=reports&auto_download=vacation&request_id={vacation.id}")
        except Exception as e:
            messages.error(request, f'Ошибка при создании заявления: {str(e)}')
            return redirect(f"{reverse('main:index')}?tab=applications")
    
    return redirect(f"{reverse('main:index')}?tab=applications")


@login_required
def vacation_request_detail(request, request_id):
    """Получение детальной информации о заявлении для модального окна"""
    user_is_admin = is_admin(request.user)
    if user_is_admin:
        vacation = get_object_or_404(VacationRequest.objects.defer('price'), id=request_id)
    else:
        vacation = get_object_or_404(VacationRequest.objects.defer('price'), id=request_id, worker__user=request.user)
    
    family_members = vacation.family_members.all()
    
    calculated_price = vacation.calculate_price()
    effective_price = get_vacation_effective_price(vacation)
    display_price = float(effective_price) if effective_price is not None else None
    is_custom_price = (
        vacation.resort in ('zhartas', 'shakhter')
        and effective_price is not None
        and calculated_price is not None
        and effective_price != calculated_price
    )
    
    # Генерируем предпросмотр заявления
    preview_html = generate_vacation_request_preview(vacation)
    
    data = {
        'id': vacation.id,
        'type': 'Путевка',
        'study_certificate_file': vacation.study_certificate_file.url if vacation.study_certificate_file else None,
        'study_certificate_file_name': vacation.study_certificate_file.name.split('/')[-1] if vacation.study_certificate_file else None,
        'worker': {
            'id': vacation.worker.id,  # ID работника для перехода к карточке
            'full_name': vacation.worker.full_name,
            'personnel_number': vacation.worker.personnel_number or '',
            'inn': vacation.worker.inn or '—',
            'status': vacation.worker.get_status_display(),
            'department': vacation.worker.department,
            'position': vacation.worker.position,
            'phone': vacation.worker.phone or '—',
            'address': vacation.worker.address or '—',
        },
        'vacation_details': {
            'resort': vacation.get_resort_display(),
            'resort_code': vacation.resort,
            'start_date': vacation.start_date.strftime('%d.%m.%Y'),
            'start_date_iso': vacation.start_date.strftime('%Y-%m-%d'),
            'end_date': vacation.end_date.strftime('%d.%m.%Y'),
            'end_date_iso': vacation.end_date.strftime('%Y-%m-%d'),
            'duration_days': vacation.get_duration_days(),
            'status': vacation.get_status(),
            'status_text': vacation.get_status_display_text(),
            'price': display_price,
            'price_is_custom': bool(is_custom_price),
            'price_per_day': VacationRequest.get_price_per_day(vacation.resort),
            'people_count': vacation.get_places_count(),
            'worker_goes': bool(getattr(vacation, 'worker_goes', True)),
            'seasons': vacation.seasons or [],
        },
        'family_members': [
            {
                'id': fm.id,
                'full_name': fm.full_name,
                'relationship': fm.get_relationship_display(),
                'id_number': fm.id_number or '—',
                'id_issue_date': fm.id_issue_date.strftime('%d.%m.%Y') if fm.id_issue_date else '—',
                'id_issued_by': fm.id_issued_by or '—',
            }
            for fm in family_members
        ],
        'selected_family_ids': [fm.id for fm in family_members],
        'is_rejected': vacation.is_rejected,
        'created_at': vacation.created_at.strftime('%d.%m.%Y %H:%M'),
        'preview_html': preview_html,
        'can_download': True,  # Теперь доступно для всех курортов
    }
    
    return JsonResponse(data)


@login_required
def update_vacation_request(request, request_id):
    """Обновление заявления (отказ от поездки)"""
    user_is_admin = is_admin(request.user)
    if user_is_admin:
        vacation = get_object_or_404(VacationRequest.objects.defer('price'), id=request_id)
    else:
        vacation = get_object_or_404(VacationRequest.objects.defer('price'), id=request_id, worker__user=request.user)
    
    if request.method == 'POST':
        is_rejected = request.POST.get('is_rejected') == 'true'
        vacation.is_rejected = is_rejected
        vacation.save()
        
        status = 'отказано' if is_rejected else 'подтверждено'
        messages.success(request, f'Статус заявления изменен на "{status}"')
        return redirect(f"{reverse('main:index')}?tab=reports")
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def edit_vacation_request(request, request_id):
    """Редактирование параметров уже созданного заявления на путёвку"""
    user_is_admin = is_admin(request.user)
    if user_is_admin:
        vacation = get_object_or_404(VacationRequest.objects.defer('price'), id=request_id)
    else:
        vacation = get_object_or_404(VacationRequest.objects.defer('price'), id=request_id, worker__user=request.user)

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # Нельзя редактировать отменённые/отклонённые
    if vacation.is_rejected or vacation.request_status == 'inactive' or (vacation.worker.is_pensioner_like() and vacation.worker.is_dead):
        return JsonResponse({'error': 'Редактирование недоступно для неактивных/отменённых заявлений'}, status=400)

    payload = {}
    if request.content_type and 'application/json' in request.content_type:
        try:
            import json
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            payload = {}
    else:
        payload = request.POST

    resort = (payload.get('resort') or '').strip()
    start_date_str = payload.get('start_date')
    end_date_str = payload.get('end_date')
    seasons = payload.get('seasons') or []
    worker_goes = payload.get('worker_goes')
    family_member_ids = payload.get('family_members') or []
    custom_price_raw = payload.get('custom_price')

    # Приводим типы
    worker_goes = _parse_bool(worker_goes) if 'worker_goes' in payload else True
    if isinstance(seasons, str):
        seasons = [seasons]
    if isinstance(family_member_ids, str):
        family_member_ids = [family_member_ids]

    try:
        family_member_ids = [int(x) for x in family_member_ids if str(x).strip().isdigit()]
    except Exception:
        family_member_ids = []

    if not resort:
        return JsonResponse({'error': 'Не выбран курорт'}, status=400)

    # Проверка: пенсионеры не могут Балхаш/Дискавери
    if vacation.worker.is_pensioner_like() and resort in ['balkhash', 'discovery']:
        resort_name = dict(VacationRequest.RESORT_CHOICES).get(resort, resort)
        return JsonResponse({'error': f'Пенсионеры не могут выбирать курорт \"{resort_name}\"'}, status=400)

    # Сезоны Орлёнок
    if resort == 'orlenok':
        if not seasons or len(seasons) == 0:
            return JsonResponse({'error': 'Для ДОЦ \"Орленок\" необходимо выбрать хотя бы один сезон'}, status=400)
        try:
            seasons = [int(s) for s in seasons if str(s).isdigit()]
            if not seasons or not all(1 <= s <= 4 for s in seasons):
                return JsonResponse({'error': 'Сезоны должны быть числами от 1 до 4'}, status=400)
        except Exception:
            return JsonResponse({'error': 'Неверный формат сезонов'}, status=400)
    else:
        seasons = []

    # Даты
    try:
        from datetime import datetime
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except Exception:
        return JsonResponse({'error': 'Неверный формат дат'}, status=400)

    if end_date < start_date:
        return JsonResponse({'error': 'Дата окончания не может быть раньше даты начала'}, status=400)

    if start_date.year < 2000 or end_date.year < 2000:
        return JsonResponse({'error': 'Год в дате поездки должен быть не ранее 2000'}, status=400)

    trip_days = (end_date - start_date).days + 1
    if trip_days > 31:
        return JsonResponse({'error': 'Длительность путевки не может превышать 31 день'}, status=400)

    try:
        custom_price = parse_optional_custom_price(custom_price_raw, resort)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    # Хотя бы один отдыхающий
    if not worker_goes and len(family_member_ids) == 0:
        return JsonResponse({'error': 'Необходимо выбрать хотя бы одного отдыхающего'}, status=400)

    # Валидируем членов семьи + возрастные ограничения
    family_members = FamilyMember.objects.filter(id__in=family_member_ids, worker=vacation.worker)

    for fm in family_members:
        if fm.is_child_or_grandchild():
            if not fm.birth_date:
                return JsonResponse({'error': f'Для {fm.get_relationship_display().lower()} {fm.full_name} необходимо указать дату рождения'}, status=400)
            age = fm.get_age()
            if age is None:
                continue
            if resort == 'orlenok' and age >= 14:
                return JsonResponse({'error': f'{fm.get_relationship_display()} {fm.full_name} не проходит по возрасту для ДОЦ \"Орленок\" (возраст {age} лет, требуется до 14 лет)'}, status=400)
            if resort == 'discovery' and age >= 18:
                if not vacation.study_certificate_file:
                    return JsonResponse({'error': f'Для {fm.get_relationship_display().lower()} {fm.full_name} старше 18 лет на курорт "Дискавери" необходимо прикрепить справку об очном обучении (отредактируйте заявление с приложением файла)'}, status=400)

    # Применяем изменения
    vacation.resort = resort
    vacation.start_date = start_date
    vacation.end_date = end_date
    vacation.worker_goes = worker_goes
    vacation.seasons = seasons
    vacation.family_members.set(family_members)

    # Пересчитываем цену
    calculated_price = vacation.calculate_price()
    vacation.price = custom_price if custom_price is not None else calculated_price
    vacation.save()

    return JsonResponse({'success': True})


def generate_vacation_request_preview(vacation):
    """Генерация HTML предпросмотра заявления"""
    days = vacation.get_duration_days()
    people_count = vacation.get_places_count()
    resort_name = vacation.get_resort_display()
    start_date_str = vacation.start_date.strftime('%d.%m.%Y')
    effective_price = get_vacation_effective_price(vacation)
    price_str = f"{int(effective_price)}" if effective_price else "—"
    
    # Информация об удостоверении личности
    id_info = ''
    if vacation.worker.id_number:
        id_info = vacation.worker.id_number
    if vacation.worker.id_issue_date:
        id_info += f', {vacation.worker.id_issue_date.strftime("%d.%m.%Y")}'
    if vacation.worker.id_issued_by:
        id_info += f', {vacation.worker.id_issued_by}'
    
    # Члены семьи
    family_names = ''
    if vacation.family_members.exists():
        family_names = ', '.join([fm.full_name for fm in vacation.family_members.all()])
    
    # Формируем текст просьбы с учетом сезонов для ДОЦ "Орленок"
    seasons_display = vacation.get_seasons_display()
    if vacation.resort == 'orlenok' and seasons_display:
        request_text = f'Прошу выделить {people_count} путевку(ки) в {resort_name} на {seasons_display}'
    else:
        request_text = f'Прошу выделить {people_count} путевку(ки) в {resort_name}'
    
    # Для Жартас и Шахтер - полный шаблон, для остальных - упрощенный
    header_line_1, header_line_2 = get_vacation_header_lines(vacation)
    if vacation.resort in ['zhartas', 'shakhter']:
        preview = f'''
    <div class="vacation-request-preview">
        <div class="preview-header-right">
            <div>{header_line_1}</div>
            <div>{header_line_2}</div>
        </div>
        <div class="preview-applicant-right">
            <div>от {vacation.worker.full_name}</div>
            <div>профессия {vacation.worker.position}</div>
            <div>подразделение {vacation.worker.department}</div>
            <div>таб.№ {vacation.worker.personnel_number}</div>
            <div>Телефон/моб. {vacation.worker.phone or "—"}</div>
        </div>
        <div class="preview-title-center">
            <strong>ЗАЯВЛЕНИЕ</strong>
        </div>
        <div class="preview-body">
            <div>{request_text}</div>
            <div>Сроком {days} дней с {start_date_str} года.</div>
                <div>Отпуск с «______» ______ 201__ г..</div>
            {f'<div>{family_names} (членам семьи)</div>' if family_names else ''}
            <div>Прошу внести стоимость путевки (ок) {price_str} в сумме тенге.</div>
            <div>Я, {vacation.worker.full_name} обязуюсь использовать выделенную и выданную мне на Предприятии льготную путевку в количестве {people_count} штук, в {resort_name} по личному и целевому назначению.</div>
            <div>Я предупрежден, что в случае передачи льготной путевки (-ок) постороннему или другому лицу, а также в случае отказа без уважительной причины от предоставленной мне путевки (-ок) требуется оплата <strong>полной стоимости</strong> путевки по предъявлению Работодателя.</div>
            <div>С условиями оплаты я согласен.</div>
                <div>({id_info or "—"})</div>
        </div>
        <div class="preview-signatures-right">
            <div>Дата ________</div>
            <div>Подпись Работника________</div>
            <div>Подпись ответственного лица________</div>
        </div>
        <div class="preview-note">
            <em>Примечание: Заявление по прилагаемой форме пишется собственноручно заявителем при оформлении документов на поручение льготной путевки в санатории и дом отдыха. Подпись заявителя заверяется ответственным лицом за реализацию, распределение и выдачу путевок в структурном подразделении.</em>
        </div>
    </div>
    '''
    else:
        # Упрощенный шаблон для остальных курортов
        preview = f'''
        <div class="vacation-request-preview">
            <div class="preview-header-right">
                <div>{header_line_1}</div>
                <div>{header_line_2}</div>
            </div>
            <div class="preview-applicant-right">
                <div>от {vacation.worker.full_name}</div>
                <div>профессия {vacation.worker.position}</div>
                <div>подразделение {vacation.worker.department}</div>
                <div>таб.№ {vacation.worker.personnel_number}</div>
                <div>Телефон/моб. {vacation.worker.phone or "—"}</div>
            </div>
            <div class="preview-title-center">
                <strong>ЗАЯВЛЕНИЕ</strong>
            </div>
            <div class="preview-body">
                <div>{request_text}</div>
                <div>Сроком {days} дней с {start_date_str} года.</div>
                <div>Отпуск с «______» ______ 201__ г..</div>
                {f'<div>({id_info})</div>' if id_info else ''}
            </div>
            <div class="preview-signatures-right">
                <div>Дата ________</div>
                <div>Подпись Работника________</div>
                <div>Подпись ответственного лица________</div>
        </div>
    </div>
    '''
    return preview


def generate_vacation_request_docx(vacation):
    """Генерация Word документа для заявления на путевку (Жартас и Шахтер)"""
    doc = Document()
    
    # Настройка полей страницы для компактности
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Настройка стилей
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(11)
    # Убираем интервалы между параграфами
    paragraph_format = style.paragraph_format
    paragraph_format.space_before = Pt(0)
    paragraph_format.space_after = Pt(0)
    paragraph_format.line_spacing = 1.0
    
    # Заголовок справа
    header_line_1, header_line_2 = get_vacation_header_lines(vacation)
    header_para = doc.add_paragraph()
    header_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header_run = header_para.add_run(f'{header_line_1}\n{header_line_2}')
    header_run.font.size = Pt(9)
    
    # Данные заявителя справа
    applicant_para = doc.add_paragraph()
    applicant_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    applicant_info = f'от {vacation.worker.full_name}\nпрофессия {vacation.worker.position}\nподразделение {vacation.worker.department}\nтаб.№ {vacation.worker.personnel_number}\nТелефон/моб. {vacation.worker.phone or "—"}'
    applicant_run = applicant_para.add_run(applicant_info)
    applicant_run.font.size = Pt(9)
    
    # Пустая строка
    doc.add_paragraph()
    
    # ЗАЯВЛЕНИЕ по центру
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run('ЗАЯВЛЕНИЕ')
    title_run.font.size = Pt(13)
    title_run.bold = True
    
    # Пустая строка
    doc.add_paragraph()
    
    # Текст заявления
    days = vacation.get_duration_days()
    people_count = vacation.get_places_count()
    resort_name = vacation.get_resort_display()
    start_date_str = vacation.start_date.strftime('%d.%m.%Y')
    effective_price = get_vacation_effective_price(vacation)
    price_str = f"{int(effective_price)}" if effective_price else "—"
    
    # Формируем текст просьбы с учетом сезонов для ДОЦ "Орленок"
    seasons_display = vacation.get_seasons_display()
    if vacation.resort == 'orlenok' and seasons_display:
        request_text = f'Прошу выделить {people_count} путевку(ки) в {resort_name} на {seasons_display}'
    else:
        request_text = f'Прошу выделить {people_count} путевку(ки) в {resort_name}'
    
    # Формируем текст заявления с сохранением структуры строк (точно как в предпросмотре)
    request_para1 = doc.add_paragraph()
    request_para1.add_run(request_text)
    
    request_para2 = doc.add_paragraph()
    request_para2.add_run(f'Сроком {days} дней с {start_date_str} года.')
    
    request_para3 = doc.add_paragraph()
    request_para3.add_run('Отпуск с «______» ______ 201__ г..')
    
    # Члены семьи (если есть) - сразу после строки "Отпуск с..."
    if vacation.family_members.exists():
        family_para = doc.add_paragraph()
        family_names = ', '.join([fm.full_name for fm in vacation.family_members.all()])
        family_para.add_run(f'{family_names} (членам семьи)')
    
    # Просьба о внесении стоимости путевки
    request_para4 = doc.add_paragraph()
    request_para4.add_run(f'Прошу внести стоимость путевки (ок) {price_str} в сумме тенге.')
    
    # Я, ФИО обязуюсь
    request_para5 = doc.add_paragraph()
    request_para5.add_run(f'Я, {vacation.worker.full_name} обязуюсь использовать выделенную и выданную мне на Предприятии льготную путевку в количестве {people_count} штук, в {resort_name} по личному и целевому назначению.')
    
    # Предупреждение
    request_para6 = doc.add_paragraph()
    warning_text = 'Я предупрежден, что в случае передачи льготной путевки (-ок) постороннему или другому лицу, а также в случае отказа без уважительной причины от предоставленной мне путевки (-ок) требуется оплата '
    warning_run1 = request_para6.add_run(warning_text)
    bold_text = request_para6.add_run('полной стоимости')
    bold_text.bold = True
    warning_run2 = request_para6.add_run(' путевки по предъявлению Работодателя.')
    
    # Согласие
    request_para7 = doc.add_paragraph()
    request_para7.add_run('С условиями оплаты я согласен.')
    
    # Удостоверение личности (в скобках, как в предпросмотре)
    id_info = ''
    if vacation.worker.id_number:
        id_info = vacation.worker.id_number
    if vacation.worker.id_issue_date:
        id_info += f', {vacation.worker.id_issue_date.strftime("%d.%m.%Y")}'
    if vacation.worker.id_issued_by:
        id_info += f', {vacation.worker.id_issued_by}'
    
    request_para8 = doc.add_paragraph()
    request_para8.add_run(f'({id_info or "—"})')
    
    # Добавляем пустые строки, чтобы переместить подписи и примечание вниз того же листа
    for _ in range(15):  # Добавляем достаточно пустых строк
        empty_para = doc.add_paragraph()
        empty_para.paragraph_format.space_after = Pt(0)
        empty_para.paragraph_format.space_before = Pt(0)
    
    # Подписи справа (внизу страницы)
    signature_para1 = doc.add_paragraph()
    signature_para1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    signature_para1.add_run('Дата ________')
    
    signature_para2 = doc.add_paragraph()
    signature_para2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    signature_para2.add_run('Подпись Работника________')
    
    signature_para3 = doc.add_paragraph()
    signature_para3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    signature_para3.add_run('Подпись ответственного лица________')
    
    # Примечание (увеличенный размер шрифта)
    doc.add_paragraph()
    note_para = doc.add_paragraph()
    note_run = note_para.add_run('Примечание: Заявление по прилагаемой форме пишется собственноручно заявителем при оформлении документов на поручение льготной путевки в санатории и дом отдыха. Подпись заявителя заверяется ответственным лицом за реализацию, распределение и выдачу путевок в структурном подразделении.')
    note_run.font.size = Pt(10)
    note_run.italic = True
    
    # Сохраняем в BytesIO
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    return buffer


def generate_vacation_request_docx_standard(vacation):
    """Генерация Word документа для стандартного заявления на путевку (для всех курортов кроме Жартас и Шахтер)"""
    doc = Document()
    
    # Настройка полей страницы
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Настройка стилей
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(11)
    
    # Заголовок справа
    header_line_1, header_line_2 = get_vacation_header_lines(vacation)
    header_para = doc.add_paragraph()
    header_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header_run = header_para.add_run(f'{header_line_1}\n{header_line_2}')
    header_run.font.size = Pt(9)
    
    # Данные заявителя справа
    applicant_para = doc.add_paragraph()
    applicant_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    applicant_info = f'от {vacation.worker.full_name}\nпрофессия {vacation.worker.position}\nподразделение {vacation.worker.department}\nтаб.№ {vacation.worker.personnel_number}\nТелефон/моб. {vacation.worker.phone or "—"}'
    applicant_run = applicant_para.add_run(applicant_info)
    applicant_run.font.size = Pt(9)
    
    # Пустая строка
    doc.add_paragraph()
    
    # ЗАЯВЛЕНИЕ по центру
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run('ЗАЯВЛЕНИЕ')
    title_run.font.size = Pt(13)
    title_run.bold = True
    
    # Пустая строка
    doc.add_paragraph()
    
    # Текст заявления с автоматическим заполнением
    days = vacation.get_duration_days()
    people_count = vacation.get_places_count()
    resort_name = vacation.get_resort_display()
    start_date_str = vacation.start_date.strftime('%d.%m.%Y')
    
    # Формируем текст просьбы с учетом сезонов для ДОЦ "Орленок"
    seasons_display = vacation.get_seasons_display()
    if vacation.resort == 'orlenok' and seasons_display:
        request_text = f'Прошу выделить {people_count} путевку(ки) в {resort_name} на {seasons_display}'
    else:
        request_text = f'Прошу выделить {people_count} путевку(ки) в {resort_name}'
    
    # Автоматическое заполнение: %кол-во путевок% и %курорт%
    request_para1 = doc.add_paragraph()
    request_para1.add_run(request_text)
    
    # Автоматическое заполнение: %кол-во дней% и %дата начала путевки%
    request_para2 = doc.add_paragraph()
    request_para2.add_run(f'Сроком {days} дней с {start_date_str} года.')
    
    # Отпуск (оставляем пустым для заполнения вручную)
    request_para3 = doc.add_paragraph()
    request_para3.add_run('Отпуск с «______» ______ 201__ г..')
    
    # Автоматическое заполнение: %(№ удостоверения личности, когда и кем выдано)%
    id_info = ''
    if vacation.worker.id_number:
        id_info = vacation.worker.id_number
        if vacation.worker.id_issue_date:
            id_info += f', {vacation.worker.id_issue_date.strftime("%d.%m.%Y")}'
        if vacation.worker.id_issued_by:
            id_info += f', {vacation.worker.id_issued_by}'
    
    if id_info:
        request_para4 = doc.add_paragraph()
        request_para4.add_run(f'({id_info})')
    
    # Пустая строка
    doc.add_paragraph()
    
    # Подписи справа
    signature_para1 = doc.add_paragraph()
    signature_para1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    signature_para1.add_run('Дата ________')
    
    signature_para2 = doc.add_paragraph()
    signature_para2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    signature_para2.add_run('Подпись Работника________')
    
    signature_para3 = doc.add_paragraph()
    signature_para3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    signature_para3.add_run('Подпись ответственного лица________')
    
    # Сохраняем в BytesIO
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    return buffer


@login_required
def download_vacation_request(request, request_id):
    """Скачивание печатного заявления в Word"""
    if is_admin(request.user):
        vacation = get_object_or_404(VacationRequest.objects.defer('price'), id=request_id)
    else:
        vacation = get_object_or_404(VacationRequest.objects.defer('price'), id=request_id, worker__user=request.user)
    
    # Выбираем шаблон в зависимости от курорта
    if vacation.resort in ['zhartas', 'shakhter']:
        buffer = generate_vacation_request_docx(vacation)
    else:
        buffer = generate_vacation_request_docx_standard(vacation)
    
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    resort_name = vacation.get_resort_display()
    # Убираем пробелы из имени файла
    worker_name_clean = vacation.worker.full_name.replace(' ', '_')
    filename = f"Заявление_на_путевку_{resort_name}_{worker_name_clean}_{vacation.start_date.strftime('%d.%m.%Y')}.docx"
    # Правильная кодировка имени файла для кириллицы
    # Используем транслитерацию для максимальной совместимости с браузерами
    safe_filename = transliterate_filename(filename)
    # Используем только транслитерированное имя для гарантированной работы во всех браузерах
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    
    return response


@login_required
def download_study_certificate(request, request_id):
    """Скачивание справки об очном обучении"""
    if is_admin(request.user):
        vacation = get_object_or_404(VacationRequest.objects.defer('price'), id=request_id)
    else:
        vacation = get_object_or_404(VacationRequest.objects.defer('price'), id=request_id, worker__user=request.user)
    
    if not vacation.study_certificate_file:
        messages.error(request, 'Справка об очном обучении не найдена!')
        return redirect(f"{reverse('main:index')}?tab=reports")
    
    response = FileResponse(
        vacation.study_certificate_file.open('rb'),
        content_type='application/octet-stream'
    )
    
    filename = vacation.study_certificate_file.name.split('/')[-1]
    safe_filename = transliterate_filename(filename)
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    
    return response


@login_required
def set_vacation_limit(request):
    """Установка или увеличение лимита на путевки"""
    if request.method == 'POST':
        new_limit = request.POST.get('limit')
        resort = request.POST.get('resort', 'zhartas')  # По умолчанию Жартас
        
        # Проверяем, что resort валидный
        if resort not in ['zhartas', 'shakhter']:
            messages.error(request, 'Некорректный курорт!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        try:
            new_limit = int(new_limit)
            if new_limit < 0:
                raise ValueError("Лимит не может быть отрицательным")
        except (ValueError, TypeError):
            messages.error(request, 'Некорректное значение лимита!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        limit, created = VacationLimit.get_or_create_limit(request.user, resort)
        
        resort_name = dict(VacationLimit.RESORT_CHOICES).get(resort, resort)
        
        if created or limit.limit == 0:
            # Первая установка лимита
            limit.limit = new_limit
            limit.is_initial = True
            limit.save()
            messages.success(request, f'Лимит для {resort_name} установлен: {new_limit} мест')
        else:
            # Увеличение лимита
            if new_limit < limit.limit:
                messages.error(request, f'Можно только увеличить лимит! Текущий лимит для {resort_name}: {limit.limit}')
                return redirect(f"{reverse('main:index')}?tab=applications")
            
            limit.limit = new_limit
            limit.is_initial = False
            limit.save()
            messages.success(request, f'Лимит для {resort_name} увеличен до: {new_limit} мест')
        
        return redirect(f"{reverse('main:index')}?tab=applications")
    
    return redirect(f"{reverse('main:index')}?tab=applications")


@login_required
def generate_zhartas_statement_excel(request):
    """Генерация Excel файла ведомости путевок за Жартас"""
    user_is_admin = is_admin(request.user)
    
    # Проверяем, выбран ли конкретный период через GET параметр
    selected_period_start = request.GET.get('period_start')
    if selected_period_start:
        try:
            period_start = date.fromisoformat(selected_period_start)
            # Вычисляем period_end для выбранного периода
            period_end = get_period_end_for_start(period_start)
        except (ValueError, TypeError):
            # Если невалидная дата, используем текущий период
            period_start, period_end = get_statement_period()
    else:
        # Используем текущий период по умолчанию
        period_start, period_end = get_statement_period()
    
    # Получаем все путевки за Жартас в выбранном периоде
    if user_is_admin:
        vacations = VacationRequest.objects.filter(
            resort='zhartas',
            start_date__gte=period_start,
            start_date__lte=period_end,
            is_rejected=False
        ).select_related('worker', 'user').prefetch_related('family_members').defer('price').order_by('worker__full_name')
    else:
        vacations = VacationRequest.objects.filter(
            user=request.user,
            resort='zhartas',
            start_date__gte=period_start,
            start_date__lte=period_end,
            is_rejected=False
        ).select_related('worker').prefetch_related('family_members').defer('price').order_by('worker__full_name')
    
    # Создаем Excel файл
    wb = Workbook()
    ws = wb.active
    ws.title = safe_excel_sheet_title(
        f"Ведомость Жартас {period_start.strftime('%d.%m.%Y')}-{period_end.strftime('%d.%m.%Y')}"
    )
    
    # Стили - улучшенные
    header_fill = PatternFill(start_color=EXCEL_HEADER_COLOR, end_color=EXCEL_HEADER_COLOR, fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12, name='Arial')
    title_font = Font(bold=True, size=18, color="FFFFFF", name='Arial')
    border_style = Border(
        left=Side(style='thin', color=EXCEL_BORDER_COLOR),
        right=Side(style='thin', color=EXCEL_BORDER_COLOR),
        top=Side(style='thin', color=EXCEL_BORDER_COLOR),
        bottom=Side(style='thin', color=EXCEL_BORDER_COLOR)
    )
    center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    right_alignment = Alignment(horizontal='right', vertical='center', wrap_text=True)
    
    # Заголовок
    ws.merge_cells('A1:F1')
    title_cell = ws['A1']
    title_cell.value = f'Ведомость путевок за Жартас с {period_start.strftime("%d.%m.%Y")} по {period_end.strftime("%d.%m.%Y")}'
    title_cell.font = title_font
    title_cell.fill = header_fill
    title_cell.alignment = center_alignment
    title_cell.border = border_style
    ws.row_dimensions[1].height = 35
    
    # Заголовки таблицы
    headers = ['Порядковый номер', 'ФИО', 'Табельный номер', 'Количество путевок', 'Койка/дней', 'Сумма путевки']
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_alignment
        cell.border = border_style
    
    # Данные
    row_num = 4
    total_sum = 0
    
    for vacation in vacations:
        # Порядковый номер
        ws.cell(row=row_num, column=1, value=row_num - 3).alignment = center_alignment

        # ФИО
        ws.cell(row=row_num, column=2, value=vacation.worker.full_name)
        
        # Табельный номер
        ws.cell(row=row_num, column=3, value=vacation.worker.personnel_number).alignment = center_alignment
        
        # Количество путевок (только работник, без членов семьи) - всегда 1
        ws.cell(row=row_num, column=4, value=1).alignment = center_alignment
        
        # Койка/дней (количество путевок включая членов семьи * количество дней)
        people_count = vacation.get_places_count()
        days = vacation.get_duration_days()
        bed_days = people_count * days
        ws.cell(row=row_num, column=5, value=bed_days).alignment = center_alignment
        
        # Сумма путевки
        price = get_vacation_price_float(vacation)
        ws.cell(row=row_num, column=6, value=price).alignment = right_alignment
        ws.cell(row=row_num, column=6).number_format = EXCEL_CURRENCY_FORMAT
        total_sum += price
        
        # Применяем границы
        max_col = 6
        for col in range(1, max_col + 1):
            ws.cell(row=row_num, column=col).border = border_style
        
        row_num += 1
    
    # Итоговая строка
    total_fill = PatternFill(start_color=EXCEL_TOTAL_FILL_COLOR, end_color=EXCEL_TOTAL_FILL_COLOR, fill_type="solid")
    total_font = Font(bold=True, size=12, name='Arial')
    
    ws.merge_cells(f'A{row_num}:E{row_num}')
    total_sum_col = 6
    
    total_cell = ws[f'A{row_num}']
    total_cell.value = 'ИТОГО:'
    total_cell.font = total_font
    total_cell.alignment = right_alignment
    total_cell.border = border_style
    total_cell.fill = total_fill
    
    total_sum_cell = ws.cell(row=row_num, column=total_sum_col)
    total_sum_cell.value = total_sum
    total_sum_cell.font = total_font
    total_sum_cell.alignment = right_alignment
    total_sum_cell.number_format = EXCEL_CURRENCY_FORMAT
    total_sum_cell.border = border_style
    total_sum_cell.fill = total_fill
    
    # Применяем границы ко всем ячейкам итоговой строки
    max_col = 6
    for col in range(1, max_col + 1):
        ws.cell(row=row_num, column=col).border = border_style
        if col < max_col:
            ws.cell(row=row_num, column=col).fill = total_fill
    
    # Настройка ширины колонок
    ws.column_dimensions['A'].width = 18
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 18
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 18

    max_col = 6
    ws.auto_filter.ref = f"A3:{get_column_letter(max_col)}{max(row_num - 1, 3)}"
    ws.freeze_panes = 'A4'
    
    # Сохраняем в BytesIO
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"Ведомость_Жартас_{period_start.strftime('%d.%m.%Y')}-{period_end.strftime('%d.%m.%Y')}.xlsx"
    # Правильная кодировка имени файла для кириллицы
    # Используем транслитерацию для максимальной совместимости с браузерами
    safe_filename = transliterate_filename(filename)
    # Используем только транслитерированное имя для гарантированной работы во всех браузерах
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    
    return response


@login_required
def generate_shakhter_statement_excel(request):
    """Генерация Excel файла ведомости путевок за Шахтер"""
    user_is_admin = is_admin(request.user)
    
    # Проверяем, выбран ли конкретный период через GET параметр
    selected_period_start = request.GET.get('period_start')
    if selected_period_start:
        try:
            period_start = date.fromisoformat(selected_period_start)
            # Вычисляем period_end для выбранного периода
            period_end = get_period_end_for_start(period_start)
        except (ValueError, TypeError):
            # Если невалидная дата, используем текущий период
            period_start, period_end = get_statement_period()
    else:
        # Используем текущий период по умолчанию
        period_start, period_end = get_statement_period()
    
    # Получаем все путевки за Шахтер в выбранном периоде (только не отмененные)
    if user_is_admin:
        vacations = VacationRequest.objects.filter(
            resort='shakhter',
            start_date__gte=period_start,
            start_date__lte=period_end,
            is_rejected=False
        ).select_related('worker', 'user').prefetch_related('family_members').defer('price').order_by('worker__full_name')
    else:
        vacations = VacationRequest.objects.filter(
            user=request.user,
            resort='shakhter',
            start_date__gte=period_start,
            start_date__lte=period_end,
            is_rejected=False
        ).select_related('worker').prefetch_related('family_members').defer('price').order_by('worker__full_name')
    
    # Создаем Excel файл
    wb = Workbook()
    ws = wb.active
    ws.title = safe_excel_sheet_title(
        f"Ведомость Шахтер {period_start.strftime('%d.%m.%Y')}-{period_end.strftime('%d.%m.%Y')}"
    )
    
    # Стили - улучшенные
    header_fill = PatternFill(start_color=EXCEL_HEADER_COLOR, end_color=EXCEL_HEADER_COLOR, fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12, name='Arial')
    title_font = Font(bold=True, size=18, color="FFFFFF", name='Arial')
    border_style = Border(
        left=Side(style='thin', color=EXCEL_BORDER_COLOR),
        right=Side(style='thin', color=EXCEL_BORDER_COLOR),
        top=Side(style='thin', color=EXCEL_BORDER_COLOR),
        bottom=Side(style='thin', color=EXCEL_BORDER_COLOR)
    )
    center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    right_alignment = Alignment(horizontal='right', vertical='center', wrap_text=True)
    
    # Заголовок
    ws.merge_cells('A1:F1')
    title_cell = ws['A1']
    title_cell.value = f'Ведомость путевок за Шахтер с {period_start.strftime("%d.%m.%Y")} по {period_end.strftime("%d.%m.%Y")}'
    title_cell.font = title_font
    title_cell.fill = header_fill
    title_cell.alignment = center_alignment
    title_cell.border = border_style
    ws.row_dimensions[1].height = 35
    
    # Заголовки таблицы
    headers = ['Порядковый номер', 'ФИО', 'Табельный номер', 'Количество путевок', 'Койка/дней', 'Сумма путевки']
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_alignment
        cell.border = border_style
    ws.row_dimensions[3].height = 30
    
    # Данные
    row_num = 4
    total_sum = 0
    
    for vacation in vacations:
        # Порядковый номер
        ws.cell(row=row_num, column=1, value=row_num - 3).alignment = center_alignment
        
        # ФИО
        ws.cell(row=row_num, column=2, value=vacation.worker.full_name)
        
        # Табельный номер
        ws.cell(row=row_num, column=3, value=vacation.worker.personnel_number).alignment = center_alignment
        
        # Количество путевок (только работник, без членов семьи) - всегда 1
        ws.cell(row=row_num, column=4, value=1).alignment = center_alignment
        
        # Койка/дней (количество путевок включая членов семьи * количество дней)
        people_count = vacation.get_places_count()
        days = vacation.get_duration_days()
        bed_days = people_count * days
        ws.cell(row=row_num, column=5, value=bed_days).alignment = center_alignment
        
        # Сумма путевки
        price = get_vacation_price_float(vacation)
        ws.cell(row=row_num, column=6, value=price).alignment = right_alignment
        ws.cell(row=row_num, column=6).number_format = EXCEL_CURRENCY_FORMAT
        total_sum += price
        
        # Применяем границы
        max_col = 6
        for col in range(1, max_col + 1):
            ws.cell(row=row_num, column=col).border = border_style
        
        row_num += 1
    
    # Итоговая строка
    total_fill = PatternFill(start_color=EXCEL_TOTAL_FILL_COLOR, end_color=EXCEL_TOTAL_FILL_COLOR, fill_type="solid")
    total_font = Font(bold=True, size=12, name='Arial')
    
    ws.merge_cells(f'A{row_num}:E{row_num}')
    total_sum_col = 6
    max_col = 6
    
    total_cell = ws[f'A{row_num}']
    total_cell.value = 'ИТОГО:'
    total_cell.font = total_font
    total_cell.alignment = right_alignment
    total_cell.border = border_style
    total_cell.fill = total_fill
    
    total_sum_cell = ws.cell(row=row_num, column=total_sum_col)
    total_sum_cell.value = total_sum
    total_sum_cell.font = total_font
    total_sum_cell.alignment = right_alignment
    total_sum_cell.number_format = EXCEL_CURRENCY_FORMAT
    total_sum_cell.border = border_style
    total_sum_cell.fill = total_fill
    
    # Применяем границы ко всем ячейкам итоговой строки
    for col in range(1, max_col + 1):
        ws.cell(row=row_num, column=col).border = border_style
        if col < max_col:
            ws.cell(row=row_num, column=col).fill = total_fill
    
    # Настройка ширины колонок
    ws.column_dimensions['A'].width = 18
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 18
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 18

    ws.auto_filter.ref = f"A3:{get_column_letter(max_col)}{max(row_num - 1, 3)}"
    ws.freeze_panes = 'A4'
    
    # Сохраняем в BytesIO
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"Ведомость_Шахтер_{period_start.strftime('%d.%m.%Y')}-{period_end.strftime('%d.%m.%Y')}.xlsx"
    # Правильная кодировка имени файла для кириллицы
    # Используем транслитерацию для максимальной совместимости с браузерами
    safe_filename = transliterate_filename(filename)
    # Используем только транслитерированное имя для гарантированной работы во всех браузерах
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    
    return response


@login_required
def download_worker_file(request, worker_id, file_type):
    """Скачивание файла работника (льготы, шахтерская слава, техпаспорт дома, удостоверение пенсионера, справка о смерти)"""
    user_is_admin = is_admin(request.user)
    if user_is_admin:
        worker = get_object_or_404(Worker, id=worker_id)
    else:
        worker = get_object_or_404(Worker, id=worker_id, user=request.user)
    
    file_field = None
    if file_type == 'benefits':
        if not worker.benefits_file:
            messages.error(request, 'Файл не найден в базе данных')
            return redirect(f"{reverse('main:index')}?tab=workers")
        file_field = worker.benefits_file
    elif file_type == 'miner_glory':
        if not worker.miner_glory_file:
            messages.error(request, 'Файл не найден в базе данных')
            return redirect(f"{reverse('main:index')}?tab=workers")
        file_field = worker.miner_glory_file
    elif file_type == 'house_passport':
        if not worker.house_passport_file:
            messages.error(request, 'Файл не найден в базе данных')
            return redirect(f"{reverse('main:index')}?tab=workers")
        file_field = worker.house_passport_file
    elif file_type == 'pensioner_id':
        if not worker.pensioner_id_file:
            messages.error(request, 'Файл не найден в базе данных')
            return redirect(f"{reverse('main:index')}?tab=workers")
        file_field = worker.pensioner_id_file
    elif file_type == 'death_certificate':
        if not worker.death_certificate_file:
            messages.error(request, 'Файл не найден в базе данных')
            return redirect(f"{reverse('main:index')}?tab=workers")
        file_field = worker.death_certificate_file
    else:
        messages.error(request, 'Неверный тип файла')
        return redirect(f"{reverse('main:index')}?tab=workers")
    
    if not file_field or not file_field.name:
        messages.error(request, 'Файл не найден на сервере')
        return redirect(f"{reverse('main:index')}?tab=workers")
    
    # Проверяем существование файла
    file_path = None
    try:
        file_path = file_field.path
        if not os.path.exists(file_path):
            print(f"DEBUG: Файл не существует по пути: {file_path}")
            print(f"DEBUG: Имя файла в БД: {file_field.name}")
            messages.error(request, f'Файл не найден на сервере. Путь: {file_path}')
            return redirect(f"{reverse('main:index')}?tab=workers")
    except (ValueError, AttributeError) as e:
        # Если path недоступен (например, файл хранится в S3), пробуем открыть напрямую
        print(f"DEBUG: Не удалось получить path, пробуем открыть напрямую. Ошибка: {str(e)}")
        print(f"DEBUG: Имя файла в БД: {file_field.name}")
    
    filename = file_field.name.split('/')[-1]
    safe_filename = transliterate_filename(filename)
    
    try:
        # Пробуем открыть файл
        file_handle = file_field.open('rb')
        response = FileResponse(
            file_handle,
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
        return response
    except FileNotFoundError as e:
        print(f"DEBUG: FileNotFoundError: {str(e)}")
        print(f"DEBUG: Путь файла: {file_path}")
        print(f"DEBUG: Имя файла в БД: {file_field.name}")
        messages.error(request, 'Файл не найден на сервере. Возможно, файл был удален или перемещен.')
        return redirect(f"{reverse('main:index')}?tab=workers")
    except (IOError, OSError) as e:
        print(f"DEBUG: IOError/OSError: {str(e)}")
        print(f"DEBUG: Путь файла: {file_path}")
        print(f"DEBUG: Имя файла в БД: {file_field.name}")
        messages.error(request, f'Ошибка при открытии файла: {str(e)}')
        return redirect(f"{reverse('main:index')}?tab=workers")
    except Exception as e:
        print(f"DEBUG: Неожиданная ошибка: {str(e)}")
        print(f"DEBUG: Тип ошибки: {type(e).__name__}")
        print(f"DEBUG: Путь файла: {file_path}")
        print(f"DEBUG: Имя файла в БД: {file_field.name}")
        messages.error(request, f'Ошибка при загрузке файла: {str(e)}')
        return redirect(f"{reverse('main:index')}?tab=workers")


@login_required
def create_material_assistance_request(request):
    """Создание заявления на материальную помощь"""
    if request.method == 'POST':
        print(f"DEBUG: POST данные: {dict(request.POST)}")
        worker_id = request.POST.get('worker_id')
        
        if not worker_id:
            messages.error(request, 'Не выбран работник!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        user_is_admin = is_admin(request.user)
        
        try:
            if user_is_admin:
                worker = Worker.objects.get(id=worker_id)
            else:
                worker = Worker.objects.get(id=worker_id, user=request.user)
        except Worker.DoesNotExist:
            messages.error(request, 'Работник не найден!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Получаем данные из формы
        assistance_type = request.POST.get('assistance_type')
        account_type = (request.POST.get('account_type') or '').strip()
        account_number = (request.POST.get('account_number') or '').strip().upper().replace(' ', '')
        if account_number == 'KZ':
            account_number = ''
        # Для пенсионеров может быть скрытое поле, проверяем оба варианта
        amount = request.POST.get('amount', '0')
        if not amount or amount == '':
            amount = '0'
        
        # Валидация данных
        if not assistance_type:
            messages.error(request, 'Не выбран вид помощи!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        account_choices = dict(MaterialAssistanceRequest.ACCOUNT_TYPE_CHOICES)
        if account_type not in account_choices:
            account_type = '20_digit'
        if not account_number:
            if account_type == '20_digit':
                account_number = (worker.account_20_digit or '').strip()
            else:
                account_number = (worker.current_account or '').strip()
        if not account_number and account_type == '20_digit':
            account_number = (worker.current_account or '').strip()
            account_type = 'current' if account_number else account_type
        elif not account_number and account_type == 'current':
            account_number = (worker.account_20_digit or '').strip()
            account_type = '20_digit' if account_number else account_type

        if worker.is_pensioner_like():
            if not account_number:
                messages.error(request, 'Не указан номер счета! Заполните счет в карточке работника или в заявлении.')
                return redirect(f"{reverse('main:index')}?tab=applications")
            if not account_number.startswith('KZ'):
                messages.error(request, 'Номер счета должен начинаться с KZ!')
                return redirect(f"{reverse('main:index')}?tab=applications")
            if len(account_number) != 20:
                messages.error(request, 'Номер счета должен содержать KZ и 18 цифр (всего 20 символов)!')
                return redirect(f"{reverse('main:index')}?tab=applications")
            digits = account_number[2:]
            if not digits.isdigit() or len(digits) != 18:
                messages.error(request, 'После KZ должны быть только 18 цифр!')
                return redirect(f"{reverse('main:index')}?tab=applications")
        elif account_number:
            if not account_number.startswith('KZ'):
                messages.error(request, 'Номер счета должен начинаться с KZ!')
                return redirect(f"{reverse('main:index')}?tab=applications")
            if len(account_number) != 20:
                messages.error(request, 'Номер счета должен содержать KZ и 18 цифр (всего 20 символов)!')
                return redirect(f"{reverse('main:index')}?tab=applications")
            digits = account_number[2:]
            if not digits.isdigit() or len(digits) != 18:
                messages.error(request, 'После KZ должны быть только 18 цифр!')
                return redirect(f"{reverse('main:index')}?tab=applications")

        # Запрет дублей и взаимоисключение для пенсионеров: уголь ↔ лекарства (на лечение)
        if worker.is_pensioner_like():
            # Дубли (даже если пытались заполнить дважды) — блокируем повторное оформление
            if MaterialAssistanceRequest.objects.filter(worker=worker, assistance_type=assistance_type).exists():
                messages.error(
                    request,
                    'Повторное оформление запрещено: для этого пенсионера уже существует заявление на материальную помощь.'
                )
                return redirect(f"{reverse('main:index')}?tab=applications")

            # Взаимоисключение: если есть уголь — нельзя "на лечение", и наоборот
            if assistance_type == 'treatment' and CoalRequest.objects.filter(worker=worker).exists():
                messages.error(
                    request,
                    'Нельзя оформить материальную помощь (лекарства), потому что для этого пенсионера уже есть заявление на уголь.'
                )
                return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Для пенсионеров сумма не требуется (будет 0)
        if not worker.is_pensioner_like():
            if not amount or float(amount) <= 0:
                messages.error(request, 'Не указана сумма или сумма должна быть больше нуля!')
                return redirect(f"{reverse('main:index')}?tab=applications")
        else:
            # Для пенсионеров устанавливаем сумму 0
            amount = '0'
        
        # Создаем заявление
        try:
            # Преобразуем amount в Decimal
            from decimal import Decimal
            amount_decimal = Decimal(str(amount))
            
            print(f"DEBUG: Создание заявления - worker_id={worker_id}, assistance_type={assistance_type}, amount={amount_decimal}")
            
            with transaction.atomic():
                material_assistance = MaterialAssistanceRequest.objects.create(
                    user=request.user,
                    worker=worker,
                    assistance_type=assistance_type,
                    amount=amount_decimal,
                    account_type=account_type,
                    account_number=account_number,
                    account_file=request.FILES.get('account_file'),
                )
            
            print(f"DEBUG: Заявление создано успешно, ID={material_assistance.id}")
            
            messages.success(request, f'Заявление на материальную помощь для {worker.full_name} успешно создано!')
            
            # Автоматически скачиваем печатное заявление
            try:
                buffer = generate_material_assistance_docx(material_assistance)
                response = HttpResponse(
                    buffer.getvalue(),
                    content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
                assistance_type_display = material_assistance.get_assistance_type_display()
                # Убираем пробелы из имени файла
                worker_name_clean = worker.full_name.replace(' ', '_')
                assistance_type_clean = assistance_type_display.replace(' ', '_')
                # Для пенсионеров используем специальное название
                if worker.is_pensioner_like():
                    filename = f"Заявление_на_материальную_помощь_на_лечение_{worker_name_clean}_{date.today().strftime('%d.%m.%Y')}.docx"
                else:
                    filename = f"Заявление_на_материальную_помощь_{assistance_type_clean}_{worker_name_clean}_{date.today().strftime('%d.%m.%Y')}.docx"
                # Правильная кодировка имени файла для кириллицы
                # Используем транслитерацию для максимальной совместимости с браузерами
                safe_filename = transliterate_filename(filename)
                # Используем только транслитерированное имя для гарантированной работы во всех браузерах
                response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
                return response
            except Exception as doc_error:
                print(f"DEBUG: Ошибка при генерации документа: {str(doc_error)}")
                # Если ошибка при генерации документа, все равно редиректим на страницу с сообщением об успехе
                return redirect(f"{reverse('main:index')}?tab=applications")
            
        except Exception as e:
            import traceback
            print(f"DEBUG: Ошибка при создании заявления: {str(e)}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            messages.error(request, f'Ошибка при создании заявления: {str(e)}')
            return redirect(f"{reverse('main:index')}?tab=applications")
    
    return redirect(f"{reverse('main:index')}?tab=applications")


def generate_material_assistance_docx(material_assistance):
    """Генерация Word документа заявления на материальную помощь"""
    doc = Document()
    
    # Настройка страницы
    section = doc.sections[0]
    section.page_height = Inches(11.69)  # A4
    section.page_width = Inches(8.27)
    section.left_margin = Inches(0.79)
    section.right_margin = Inches(0.79)
    section.top_margin = Inches(0.79)
    section.bottom_margin = Inches(0.79)
    
    # Проверяем, является ли работник пенсионером
    is_pensioner = material_assistance.worker.is_pensioner_like()
    is_treatment = material_assistance.assistance_type == 'treatment'
    
    if is_pensioner and is_treatment:
        # Шаблон для пенсионеров "на лечение"
        # Шапка (справа вверху)
        header_para = doc.add_paragraph()
        header_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        header_run = header_para.add_run(
            'Директору ____________________\n'
            '____________________\n'
            'Председателю профсоюза ____________________\n'
            '____________________'
        )
        header_run.font.size = Pt(10)
        
        # Пустая строка
        doc.add_paragraph()
        
        # Информация о заявителе (справа под шапкой)
        applicant_para = doc.add_paragraph()
        applicant_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        applicant_info = f'от {material_assistance.worker.full_name}\nпрофессия {material_assistance.worker.position}\nподразделение {material_assistance.worker.department}\nтаб.№ {material_assistance.worker.personnel_number}\nТелефон/моб. {material_assistance.worker.phone or "—"}\nИИН {material_assistance.worker.inn or "—"}'
        applicant_run = applicant_para.add_run(applicant_info)
        applicant_run.font.size = Pt(9)
        
        # Заголовок "ЗАЯВЛЕНИЕ" по центру
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_para.add_run('ЗАЯВЛЕНИЕ')
        title_run.font.size = Pt(14)
        title_run.font.bold = True
        
        # Пустая строка
        doc.add_paragraph()
        
        # Текст заявления
        request_para = doc.add_paragraph()
        request_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        request_text = 'Прошу оказать материальную помощь на лечение'
        request_run = request_para.add_run(request_text)
        request_run.font.size = Pt(12)
        
        # Пустые строки для заполнения
        doc.add_paragraph()
        doc.add_paragraph()
        
        # Дата и подпись (справа внизу)
        date_para = doc.add_paragraph()
        date_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        date_run = date_para.add_run('Дата ___________')
        date_run.font.size = Pt(12)
        
        doc.add_paragraph()
        
        signature_para = doc.add_paragraph()
        signature_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        signature_run = signature_para.add_run('Подпись ___________')
        signature_run.font.size = Pt(12)
    else:
        # Обычный шаблон
        # Шапка (справа вверху)
        header_para = doc.add_paragraph()
        header_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        header_run = header_para.add_run(
            'Директору ____________________\n'
            '____________________\n'
            'Председателю профсоюза ____________________\n'
            '____________________'
        )
        header_run.font.size = Pt(10)
        
        # Пустая строка
        doc.add_paragraph()
        
        # Информация о заявителе (справа под шапкой)
        applicant_para = doc.add_paragraph()
        applicant_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        applicant_info = f'от {material_assistance.worker.full_name}\nпрофессия {material_assistance.worker.position}\nподразделение {material_assistance.worker.department}\nтаб.№ {material_assistance.worker.personnel_number}\nТелефон/моб. {material_assistance.worker.phone or "—"}\nИИН {material_assistance.worker.inn or "—"}'
        applicant_run = applicant_para.add_run(applicant_info)
        applicant_run.font.size = Pt(9)
        
        # Заголовок "ЗАЯВЛЕНИЕ" по центру
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_para.add_run('ЗАЯВЛЕНИЕ')
        title_run.font.size = Pt(14)
        title_run.font.bold = True
        
        # Пустая строка
        doc.add_paragraph()
        
        # Текст заявления
        request_para = doc.add_paragraph()
        request_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        assistance_type_display = material_assistance.get_assistance_type_display()
        request_text = f'Прошу оказать материальную помощь {assistance_type_display}'
        request_run = request_para.add_run(request_text)
        request_run.font.size = Pt(12)
        
        # Пустые строки для заполнения
        doc.add_paragraph()
        doc.add_paragraph()
        
        # Дата и подпись (справа внизу)
        date_para = doc.add_paragraph()
        date_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        date_run = date_para.add_run('Дата ___________')
        date_run.font.size = Pt(12)
        
        doc.add_paragraph()
        
        signature_para = doc.add_paragraph()
        signature_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        signature_run = signature_para.add_run('Подпись ___________')
        signature_run.font.size = Pt(12)
    
    # Сохраняем в BytesIO
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    return buffer


def generate_material_assistance_preview(material_assistance):
    """Генерация HTML предпросмотра заявления на материальную помощь"""
    # Проверяем, является ли работник пенсионером
    is_pensioner = material_assistance.worker.is_pensioner_like()
    is_treatment = material_assistance.assistance_type == 'treatment'
    
    # Информация о заявителе
    applicant_info = f'от {material_assistance.worker.full_name}<br>профессия {material_assistance.worker.position}<br>подразделение {material_assistance.worker.department}<br>таб.№ {material_assistance.worker.personnel_number}<br>Телефон/моб. {material_assistance.worker.phone or "—"}<br>ИИН {material_assistance.worker.inn or "—"}'
    
    # Текст заявления
    if is_pensioner and is_treatment:
        request_text = 'Прошу оказать материальную помощь на лечение'
    else:
        assistance_type_display = material_assistance.get_assistance_type_display()
        request_text = f'Прошу оказать материальную помощь {assistance_type_display}'
    
    preview = f'''
    <div class="vacation-request-preview">
        <div class="preview-header-right">
            <div>Директору ____________________</div>
            <div>____________________</div>
            <div>Председателю профсоюза ____________________</div>
            <div>____________________</div>
        </div>
        <div class="preview-applicant-right">
            {applicant_info}
        </div>
        
        <div class="preview-title-center">
            <strong>ЗАЯВЛЕНИЕ</strong>
        </div>
        
        <div class="preview-body">
            <div>{request_text}</div>
        </div>
        
        <div class="preview-signatures-right">
            <div>Дата ___________</div>
            <div>Подпись ___________</div>
        </div>
    </div>
    '''
    return preview


@login_required
def material_assistance_detail(request, request_id):
    """Получение детальной информации о заявлении на материальную помощь"""
    user_is_admin = is_admin(request.user)
    if user_is_admin:
        material_assistance = get_object_or_404(MaterialAssistanceRequest, id=request_id)
    else:
        material_assistance = get_object_or_404(MaterialAssistanceRequest, id=request_id, worker__user=request.user)
    
    # Генерируем предпросмотр заявления (для совместимости legacy-интерфейса)
    preview_html = generate_material_assistance_preview(material_assistance)

    if material_assistance.account_type == '20_digit':
        display_account_number = material_assistance.account_number or material_assistance.worker.account_20_digit or '—'
    else:
        display_account_number = material_assistance.account_number or material_assistance.worker.current_account or '—'
    
    data = {
        'id': material_assistance.id,
        'type': 'Материальная помощь',
        'worker': {
            'id': material_assistance.worker.id,
            'full_name': material_assistance.worker.full_name,
            'personnel_number': material_assistance.worker.personnel_number or '',
            'inn': material_assistance.worker.inn or '—',
            'status': material_assistance.worker.get_status_display(),
            'department': material_assistance.worker.department,
            'position': material_assistance.worker.position,
            'phone': material_assistance.worker.phone or '—',
            'address': material_assistance.worker.address or '—',
        },
        'assistance_details': {
            'assistance_type': material_assistance.get_assistance_type_display(),
            'assistance_type_code': material_assistance.assistance_type,
            'amount': float(material_assistance.amount),
            'account_type': material_assistance.get_account_type_display(),
            'account_type_code': material_assistance.account_type,
            'account_number': display_account_number,
            'account_file_url': material_assistance.account_file.url if material_assistance.account_file else None,
            'account_file_name': material_assistance.account_file.name.split('/')[-1] if material_assistance.account_file else None,
            'status': material_assistance.get_status(),
            'status_text': material_assistance.get_status_display_text(),
        },
        'created_at': material_assistance.created_at.strftime('%d.%m.%Y %H:%M'),
        'preview_html': preview_html,
    }
    
    return JsonResponse(data)


@login_required
def download_material_assistance(request, request_id):
    """Скачивание печатного заявления на материальную помощь в Word"""
    if is_admin(request.user):
        material_assistance = get_object_or_404(MaterialAssistanceRequest, id=request_id)
    else:
        material_assistance = get_object_or_404(MaterialAssistanceRequest, id=request_id, worker__user=request.user)
    
    buffer = generate_material_assistance_docx(material_assistance)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    assistance_type_display = material_assistance.get_assistance_type_display()
    # Убираем пробелы из имени файла
    worker_name_clean = material_assistance.worker.full_name.replace(' ', '_')
    assistance_type_clean = assistance_type_display.replace(' ', '_')
    # Для пенсионеров используем специальное название
    if material_assistance.worker.is_pensioner_like():
        filename = f"Заявление_на_материальную_помощь_на_лечение_{worker_name_clean}_{date.today().strftime('%d.%m.%Y')}.docx"
    else:
        filename = f"Заявление_на_материальную_помощь_{assistance_type_clean}_{worker_name_clean}_{date.today().strftime('%d.%m.%Y')}.docx"
    # Правильная кодировка имени файла для кириллицы
    # Используем транслитерацию для максимальной совместимости с браузерами
    safe_filename = transliterate_filename(filename)
    # Используем только транслитерированное имя для гарантированной работы во всех браузерах
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    
    return response


@login_required
def create_coal_request(request):
    """Создание заявления на денежную компенсацию за льготный уголь"""
    if request.method == 'POST':
        worker_id = request.POST.get('worker_id')
        
        if not worker_id:
            messages.error(request, 'Не выбран работник!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        user_is_admin = is_admin(request.user)
        
        try:
            if user_is_admin:
                worker = Worker.objects.get(id=worker_id)
            else:
                worker = Worker.objects.get(id=worker_id, user=request.user)
        except Worker.DoesNotExist:
            messages.error(request, 'Работник не найден!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Запрет дублей и взаимоисключение: уголь ↔ лекарства (матпомощь на лечение)
        if CoalRequest.objects.filter(worker=worker).exists():
            messages.error(
                request,
                'Повторное оформление запрещено: для этого работника уже существует заявление на уголь.'
            )
            return redirect(f"{reverse('main:index')}?tab=applications")

        if worker.is_pensioner_like() and MaterialAssistanceRequest.objects.filter(
            worker=worker,
            worker__status__in=Worker.PENSIONER_STATUS_CODES,
            assistance_type='treatment',
        ).exists():
            messages.error(
                request,
                'Нельзя оформить заявление на уголь, потому что для этого пенсионера уже есть заявление на материальную помощь (лекарства).'
            )
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Получаем данные из формы
        account_type = (request.POST.get('account_type') or '').strip()
        account_number = (request.POST.get('account_number') or '').strip().upper().replace(' ', '')
        if account_number == 'KZ':
            account_number = ''
        
        # Валидация данных
        account_choices = dict(CoalRequest.ACCOUNT_TYPE_CHOICES)
        if account_type not in account_choices:
            account_type = '20_digit'

        if not account_number:
            if account_type == '20_digit':
                account_number = (worker.account_20_digit or '').strip()
            else:
                account_number = (worker.current_account or '').strip()
        if not account_number and account_type == '20_digit':
            account_number = (worker.current_account or '').strip()
            account_type = 'current' if account_number else account_type
        elif not account_number and account_type == 'current':
            account_number = (worker.account_20_digit or '').strip()
            account_type = '20_digit' if account_number else account_type

        if not account_number:
            messages.error(request, 'Не указан номер счета! Заполните счет в карточке работника или в заявлении.')
            return redirect(f"{reverse('main:index')}?tab=applications")
        if not account_number.startswith('KZ'):
            messages.error(request, 'Номер счета должен начинаться с KZ!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        if len(account_number) != 20:
            messages.error(request, 'Номер счета должен содержать KZ и 18 цифр (всего 20 символов)!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        digits = account_number[2:]
        if not digits.isdigit() or len(digits) != 18:
            messages.error(request, 'После KZ должны быть только 18 цифр!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Создаем заявление
        try:
            # Сохраняем файлы в карточку работника
            worker_updated = False
            if 'passport_file' in request.FILES:
                worker.house_passport_file = request.FILES['passport_file']
                worker_updated = True
            if 'pensioner_id_file' in request.FILES:
                worker.pensioner_id_file = request.FILES['pensioner_id_file']
                worker_updated = True
            if worker_updated:
                worker.save()
            
            # Создаем заявление (файлы уже сохранены в карточке работника)
            coal_request = CoalRequest.objects.create(
                user=request.user,
                worker=worker,
                account_type=account_type,
                account_number=account_number,
                account_file=request.FILES.get('account_file'),
            )
            
            messages.success(request, f'Заявление на уголь для {worker.full_name} успешно создано!')
            # Переходим на вкладку отчетов и передаем параметры для автозагрузки файла
            return redirect(f"{reverse('main:index')}?tab=reports&auto_download=coal&request_id={coal_request.id}")
            
        except Exception as e:
            messages.error(request, f'Ошибка при создании заявления: {str(e)}')
            return redirect(f"{reverse('main:index')}?tab=applications")
    
    return redirect(f"{reverse('main:index')}?tab=applications")


def generate_coal_request_docx(coal_request):
    """Генерация Word документа для заявления на уголь"""
    doc = Document()
    
    # Настройка полей страницы
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Настройка стилей
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(11)
    
    # Шапка справа
    header_para = doc.add_paragraph()
    header_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header_run = header_para.add_run(
        'Директору ____________________\n'
        '____________________\n'
        'Председателю профсоюза ____________________\n'
        '____________________'
    )
    header_run.font.size = Pt(10)
    
    # Данные заявителя справа (автоматическое заполнение)
    applicant_para = doc.add_paragraph()
    applicant_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    applicant_info = f'от {coal_request.worker.full_name}\nтаб.№ {coal_request.worker.personnel_number}\nТелефон/моб. {coal_request.worker.phone or "—"}'
    applicant_run = applicant_para.add_run(applicant_info)
    applicant_run.font.size = Pt(9)
    
    # Пустая строка
    doc.add_paragraph()
    
    # ЗАЯВЛЕНИЕ по центру
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run('ЗАЯВЛЕНИЕ')
    title_run.font.size = Pt(13)
    title_run.bold = True
    
    # Пустая строка
    doc.add_paragraph()
    
    # Текст заявления (автоматическое заполнение)
    request_para = doc.add_paragraph()
    request_para.add_run('Прошу выделить выплатить денежную компенсацию за льготный уголь.')
    
    # Пустая строка
    doc.add_paragraph()
    
    # Подписи справа
    signature_para1 = doc.add_paragraph()
    signature_para1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    signature_para1.add_run('Дата ________')
    
    signature_para2 = doc.add_paragraph()
    signature_para2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    signature_para2.add_run('Подпись ________')
    
    # Сохраняем в BytesIO
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    return buffer


@login_required
def coal_request_detail(request, request_id):
    """Получение детальной информации о заявлении на уголь"""
    user_is_admin = is_admin(request.user)
    if user_is_admin:
        coal_request = get_object_or_404(CoalRequest, id=request_id)
    else:
        coal_request = get_object_or_404(CoalRequest, id=request_id, worker__user=request.user)
    
    # Генерируем предпросмотр заявления (с обработкой ошибок)
    try:
        preview_html = generate_coal_request_preview(coal_request)
    except Exception as e:
        import traceback
        print(f"DEBUG: Ошибка при генерации предпросмотра для заявления на уголь: {str(e)}")
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        preview_html = '<div class="error">Ошибка при генерации предпросмотра</div>'
    
    # Безопасное получение URL файлов (даже если работник мертв)
    # Определяем отображаемый счет
    if coal_request.account_type == '20_digit':
        display_account_number = coal_request.account_number or coal_request.worker.account_20_digit or '—'
    else:
        display_account_number = coal_request.account_number or coal_request.worker.current_account or '—'

    data = {
        'id': coal_request.id,
        'type': 'Заявление на уголь',
        'worker': {
            'id': coal_request.worker.id,
            'full_name': coal_request.worker.full_name,
            'personnel_number': coal_request.worker.personnel_number or '',
            'inn': coal_request.worker.inn or '—',
            'status': coal_request.worker.get_status_display(),
            'department': coal_request.worker.department,
            'position': coal_request.worker.position,
            'phone': coal_request.worker.phone or '—',
            'address': coal_request.worker.address or '—',
            'is_dead': 'Да' if coal_request.worker.is_dead else 'Нет',
        },
        'coal_details': {
            'account_type': coal_request.get_account_type_display(),
            'account_type_code': coal_request.account_type,
            'account_number': display_account_number,
            'account_file_url': coal_request.account_file.url if coal_request.account_file else None,
            'account_file_name': coal_request.account_file.name.split('/')[-1] if coal_request.account_file else None,
            'status': coal_request.get_status(),
            'status_text': coal_request.get_status_display_text(),
            'has_passport_file': bool(coal_request.worker.house_passport_file),
            'passport_file_url': reverse('main:download_worker_file', args=[coal_request.worker.id, 'house_passport']) if coal_request.worker.house_passport_file else None,
            'passport_file_name': coal_request.worker.house_passport_file.name.split('/')[-1] if coal_request.worker.house_passport_file else None,
            'has_pensioner_id_file': bool(coal_request.worker.pensioner_id_file),
            'pensioner_id_file_url': reverse('main:download_worker_file', args=[coal_request.worker.id, 'pensioner_id']) if coal_request.worker.pensioner_id_file else None,
            'pensioner_id_file_name': coal_request.worker.pensioner_id_file.name.split('/')[-1] if coal_request.worker.pensioner_id_file else None,
        },
        'created_at': coal_request.created_at.strftime('%d.%m.%Y %H:%M'),
        'preview_html': preview_html,
    }
    
    return JsonResponse(data)


def generate_coal_request_preview(coal_request):
    """Генерация HTML предпросмотра заявления на уголь"""
    preview = f'''
    <div class="vacation-request-preview">
        <div class="preview-header-right">
            <div>Директору ____________________</div>
            <div>____________________</div>
            <div>Председателю профсоюза ____________________</div>
            <div>____________________</div>
        </div>
        <div class="preview-applicant-right">
            <div>от {coal_request.worker.full_name}</div>
            <div>таб.№ {coal_request.worker.personnel_number}</div>
            <div>Телефон/моб. {coal_request.worker.phone or "—"}</div>
        </div>
        <div class="preview-title-center">
            <strong>ЗАЯВЛЕНИЕ</strong>
        </div>
        <div class="preview-body">
            <div>Прошу выделить выплатить денежную компенсацию за льготный уголь.</div>
        </div>
        <div class="preview-signatures-right">
            <div>Дата ________</div>
            <div>Подпись ________</div>
        </div>
    </div>
    '''
    return preview


@login_required
def download_coal_request(request, request_id):
    """Скачивание печатного заявления на уголь в Word"""
    if is_admin(request.user):
        coal_request = get_object_or_404(CoalRequest, id=request_id)
    else:
        coal_request = get_object_or_404(CoalRequest, id=request_id, worker__user=request.user)
    
    buffer = generate_coal_request_docx(coal_request)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    # Убираем пробелы из имени файла
    worker_name_clean = coal_request.worker.full_name.replace(' ', '_')
    filename = f"Заявление_на_уголь_{worker_name_clean}_{date.today().strftime('%d.%m.%Y')}.docx"
    # Правильная кодировка имени файла для кириллицы
    # Используем транслитерацию для максимальной совместимости с браузерами
    safe_filename = transliterate_filename(filename)
    # Используем только транслитерированное имя для гарантированной работы во всех браузерах
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    
    return response


@login_required
def create_funeral_request(request):
    """Создание заявления на погребение пенсионеров"""
    if request.method == 'POST':
        worker_id = request.POST.get('worker_id')
        
        if not worker_id:
            messages.error(request, 'Не выбран пенсионер!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        user_is_admin = is_admin(request.user)
        
        try:
            if user_is_admin:
                worker = Worker.objects.get(id=worker_id)
            else:
                worker = Worker.objects.get(id=worker_id, user=request.user)
        except Worker.DoesNotExist:
            messages.error(request, 'Пенсионер не найден!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Проверяем, что работник - пенсионер
        if not worker.is_pensioner_like():
            messages.error(request, 'Заявление на погребение может подать только для пенсионера!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Получаем данные из формы
        applicant_full_name = request.POST.get('applicant_full_name', '').strip()
        applicant_inn = request.POST.get('applicant_inn', '').strip()
        account_type = (request.POST.get('account_type') or '').strip()
        account_number = (request.POST.get('account_number') or '').strip().upper().replace(' ', '')
        if account_number == 'KZ':
            account_number = ''
        death_date_raw = request.POST.get('death_date', '').strip()
        
        # Валидация данных
        if not applicant_full_name:
            messages.error(request, 'Не указано ФИО заявителя!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        if not applicant_inn:
            messages.error(request, 'Не указан ИИН заявителя!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Валидация ИИН
        cleaned_inn = ''.join(c for c in applicant_inn if c.isdigit())
        if len(cleaned_inn) != 12:
            messages.error(request, 'ИИН должен содержать 12 цифр!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        
        account_choices = dict(FuneralRequest.ACCOUNT_TYPE_CHOICES)
        if account_type not in account_choices:
            account_type = '20_digit'
        if not account_number:
            if account_type == '20_digit':
                account_number = (worker.account_20_digit or '').strip()
            else:
                account_number = (worker.current_account or '').strip()
        if not account_number and account_type == '20_digit':
            account_number = (worker.current_account or '').strip()
            account_type = 'current' if account_number else account_type
        elif not account_number and account_type == 'current':
            account_number = (worker.account_20_digit or '').strip()
            account_type = '20_digit' if account_number else account_type

        if not account_number:
            messages.error(request, 'Не указан номер счета! Заполните счет в карточке пенсионера или в заявлении.')
            return redirect(f"{reverse('main:index')}?tab=applications")
        if not account_number.startswith('KZ'):
            messages.error(request, 'Номер счета должен начинаться с KZ!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        if len(account_number) != 20:
            messages.error(request, 'Номер счета должен содержать KZ и 18 цифр (всего 20 символов)!')
            return redirect(f"{reverse('main:index')}?tab=applications")
        digits = account_number[2:]
        if not digits.isdigit() or len(digits) != 18:
            messages.error(request, 'После KZ должны быть только 18 цифр!')
            return redirect(f"{reverse('main:index')}?tab=applications")

        death_date = None
        if death_date_raw:
            try:
                death_date = datetime.strptime(death_date_raw, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Некорректная дата смерти пенсионера!')
                return redirect(f"{reverse('main:index')}?tab=applications")
            if death_date > date.today():
                messages.error(request, 'Дата смерти не может быть в будущем!')
                return redirect(f"{reverse('main:index')}?tab=applications")
        
        # Создаем заявление
        try:
            # Сохраняем данные о смерти в карточку работника
            worker_updated = False
            if 'death_certificate_file' in request.FILES:
                worker.death_certificate_file = request.FILES['death_certificate_file']
                worker_updated = True
            if death_date:
                worker.death_date = death_date
                worker_updated = True
            if worker_updated:
                worker.is_dead = True  # Помечаем пенсионера как мертвого
                worker.save()
            
            # Создаем заявление
            funeral_request = FuneralRequest.objects.create(
                user=request.user,
                worker=worker,
                applicant_full_name=applicant_full_name,
                applicant_inn=cleaned_inn,
                account_type=account_type,
                account_number=account_number,
                account_file=request.FILES.get('account_file'),
                recipient_account_file=request.FILES.get('recipient_account_file'),
            )
            
            # Обрабатываем удостоверение заявителя
            if 'applicant_id_file' in request.FILES:
                funeral_request.applicant_id_file = request.FILES['applicant_id_file']
                funeral_request.save()
            
            messages.success(request, f'Заявление на погребение для {worker.full_name} успешно создано!')
            messages.warning(request, 'ВНИМАНИЕ: Пенсионер помечен как умерший!')
            # Переходим на вкладку отчетов и передаем параметры для автозагрузки файла
            return redirect(f"{reverse('main:index')}?tab=reports&auto_download=funeral&request_id={funeral_request.id}")
            
        except Exception as e:
            messages.error(request, f'Ошибка при создании заявления: {str(e)}')
            return redirect(f"{reverse('main:index')}?tab=applications")
    
    return redirect(f"{reverse('main:index')}?tab=applications")


def generate_funeral_request_docx(funeral_request):
    """Генерация Word документа для заявления на погребение"""
    doc = Document()
    
    # Настройка полей страницы
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Настройка стилей
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(11)
    
    # Шапка справа
    header_para = doc.add_paragraph()
    header_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header_run = header_para.add_run(
        'Директору ____________________\n'
        '____________________\n'
        'Председателю профсоюза ____________________\n'
        '____________________'
    )
    header_run.font.size = Pt(10)
    
    # Данные заявителя справа (автоматическое заполнение)
    applicant_para = doc.add_paragraph()
    applicant_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    applicant_info = f'от {funeral_request.applicant_full_name}\nИИН {funeral_request.applicant_inn}'
    applicant_run = applicant_para.add_run(applicant_info)
    applicant_run.font.size = Pt(9)
    
    # Пустая строка
    doc.add_paragraph()
    
    # ЗАЯВЛЕНИЕ по центру
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run('ЗАЯВЛЕНИЕ')
    title_run.font.size = Pt(13)
    title_run.bold = True
    
    # Пустая строка
    doc.add_paragraph()
    
    # Текст заявления (автоматическое заполнение с ФИО пенсионера)
    request_para = doc.add_paragraph()
    request_para.add_run(f'Прошу выделить выплатить денежную компенсацию на погребение пенсионера {funeral_request.worker.full_name}.')
    
    # Пустая строка
    doc.add_paragraph()
    
    # Подписи справа
    signature_para1 = doc.add_paragraph()
    signature_para1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    signature_para1.add_run('Дата ________')
    
    signature_para2 = doc.add_paragraph()
    signature_para2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    signature_para2.add_run('Подпись ________')
    
    # Сохраняем в BytesIO
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    return buffer


@login_required
def funeral_request_detail(request, request_id):
    """Получение детальной информации о заявлении на погребение"""
    user_is_admin = is_admin(request.user)
    if user_is_admin:
        funeral_request = get_object_or_404(FuneralRequest, id=request_id)
    else:
        funeral_request = get_object_or_404(FuneralRequest, id=request_id, worker__user=request.user)
    
    # Генерируем предпросмотр заявления
    preview_html = generate_funeral_request_preview(funeral_request)
    
    data = {
        'id': funeral_request.id,
        'type': 'Заявление на погребение',
        'worker': {
            'id': funeral_request.worker.id,
            'full_name': funeral_request.worker.full_name,
            'personnel_number': funeral_request.worker.personnel_number or '',
            'inn': funeral_request.worker.inn or '—',
            'status': funeral_request.worker.get_status_display(),
            'department': funeral_request.worker.department,
            'position': funeral_request.worker.position,
            'phone': funeral_request.worker.phone or '—',
            'address': funeral_request.worker.address or '—',
            'is_dead': 'Да' if funeral_request.worker.is_dead else 'Нет',
            'death_date': funeral_request.worker.death_date.strftime('%d.%m.%Y') if funeral_request.worker.death_date else '—',
        },
        'funeral_details': {
            'applicant_full_name': funeral_request.applicant_full_name,
            'applicant_inn': funeral_request.applicant_inn,
            'account_type': funeral_request.get_account_type_display(),
            'account_type_code': funeral_request.account_type,
            'account_number': (
                funeral_request.account_number
                or funeral_request.worker.account_20_digit
                or funeral_request.worker.current_account
                or '—'
            ),
            'account_file_url': funeral_request.account_file.url if funeral_request.account_file else None,
            'account_file_name': funeral_request.account_file.name.split('/')[-1] if funeral_request.account_file else None,
            'recipient_account_file_url': funeral_request.recipient_account_file.url if funeral_request.recipient_account_file else None,
            'recipient_account_file_name': funeral_request.recipient_account_file.name.split('/')[-1] if funeral_request.recipient_account_file else None,
            'death_date': funeral_request.worker.death_date.strftime('%d.%m.%Y') if funeral_request.worker.death_date else '—',
            'death_date_iso': funeral_request.worker.death_date.strftime('%Y-%m-%d') if funeral_request.worker.death_date else '',
            'status': funeral_request.get_status(),
            'status_text': funeral_request.get_status_display_text(),
            'has_applicant_id_file': bool(funeral_request.applicant_id_file),
            'applicant_id_file_url': funeral_request.applicant_id_file.url if funeral_request.applicant_id_file else None,
            'applicant_id_file_name': funeral_request.applicant_id_file.name.split('/')[-1] if funeral_request.applicant_id_file else None,
            'has_death_certificate_file': bool(funeral_request.worker.death_certificate_file),
            'death_certificate_file_url': reverse('main:download_worker_file', args=[funeral_request.worker.id, 'death_certificate']) if funeral_request.worker.death_certificate_file else None,
            'death_certificate_file_name': funeral_request.worker.death_certificate_file.name.split('/')[-1] if funeral_request.worker.death_certificate_file else None,
        },
        'created_at': funeral_request.created_at.strftime('%d.%m.%Y %H:%M'),
        'preview_html': preview_html,
    }
    
    return JsonResponse(data)


def generate_funeral_request_preview(funeral_request):
    """Генерация HTML предпросмотра заявления на погребение"""
    preview = f'''
    <div class="vacation-request-preview">
        <div class="preview-header-right">
            <div>Директору ____________________</div>
            <div>председателю профсоюза ____________________</div>
        </div>
        <div class="preview-applicant-right">
            <div>от {funeral_request.applicant_full_name}</div>
            <div>ИИН {funeral_request.applicant_inn}</div>
        </div>
        <div class="preview-title-center">
            <strong>ЗАЯВЛЕНИЕ</strong>
        </div>
        <div class="preview-body">
            <div>Прошу выделить выплатить денежную компенсацию на погребение пенсионера {funeral_request.worker.full_name}.</div>
        </div>
        <div class="preview-signatures-right">
            <div>Дата ________</div>
            <div>Подпись ________</div>
        </div>
    </div>
    '''
    return preview


@login_required
def download_funeral_request(request, request_id):
    """Скачивание печатного заявления на погребение в Word"""
    if is_admin(request.user):
        funeral_request = get_object_or_404(FuneralRequest, id=request_id)
    else:
        funeral_request = get_object_or_404(FuneralRequest, id=request_id, worker__user=request.user)
    
    buffer = generate_funeral_request_docx(funeral_request)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    # Убираем пробелы из имени файла
    worker_name_clean = funeral_request.worker.full_name.replace(' ', '_')
    applicant_name_clean = funeral_request.applicant_full_name.replace(' ', '_')
    filename = f"Заявление_на_погребение_пенсионера_{worker_name_clean}_заявитель_{applicant_name_clean}_{date.today().strftime('%d.%m.%Y')}.docx"
    # Правильная кодировка имени файла для кириллицы
    # Используем транслитерацию для максимальной совместимости с браузерами
    safe_filename = transliterate_filename(filename)
    # Используем только транслитерированное имя для гарантированной работы во всех браузерах
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    
    return response


def get_coal_compensation_period():
    """Получает текущий период списка: с 1 по 30 число текущего месяца."""
    return get_statement_period()


@login_required
def coal_compensation_list(request):
    """Отображение списка компенсации за уголь"""
    user_is_admin = is_admin(request.user)
    selected_user_id = get_admin_selected_user_id(request)
    worker_category = get_worker_category_filter(request)
    account_type_filter = get_account_type_filter(request)
    
    period_start, period_end = get_requested_period(request, get_coal_compensation_period)
    
    # Получаем все заявления на уголь в выбранном периоде
    if user_is_admin:
        coal_requests = CoalRequest.objects.filter(
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('worker', 'user').order_by('worker__full_name')
        if selected_user_id:
            coal_requests = coal_requests.filter(worker__user_id=selected_user_id)
    else:
        coal_requests = CoalRequest.objects.filter(
            worker__user=request.user,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('worker').order_by('worker__full_name')

    coal_requests = apply_worker_category_filter(coal_requests, worker_category)
    coal_requests = apply_request_account_type_filter(coal_requests, account_type_filter)
    
    # Подготавливаем данные для таблицы
    compensation_data = []
    for idx, coal_request in enumerate(coal_requests, 1):
        worker = coal_request.worker
        
        # Получаем счет (карточный или текущий)
        if coal_request.account_type == '20_digit':
            account_number = coal_request.account_number or worker.account_20_digit or ''
        else:
            account_number = coal_request.account_number or worker.current_account or ''
        
        # Получаем льготы (если у пенсионера есть льготы, указываем название)
        # Для умерших пенсионеров не показываем льготы
        benefits = ''
        if not bool(worker.is_dead) and bool(worker.has_benefits) and worker.benefits_name:
            benefits = worker.benefits_name
        
        compensation_data.append({
            'number': idx,
            'full_name': worker.full_name,
            'inn': worker.inn or '',
            'worker_status': worker.status,
            'worker_status_display': worker.get_status_display(),
            'account_number': account_number,
            'bank': 'Народный Банк',
            'benefits': benefits,
            'accrued': str(coal_request.accrued) if coal_request.accrued else '',
            'ipn': str(coal_request.ipn) if coal_request.ipn else '',
            'to_pay': str(coal_request.to_pay) if coal_request.to_pay else '',
            'coal_request_id': coal_request.id,
            'is_issued': bool(getattr(coal_request, 'is_issued', False)),
            'worker_id': worker.id,
            'user_account': coal_request.user.username if user_is_admin else None,  # Аккаунт для админа
            'has_benefits': bool(worker.has_benefits) and not bool(worker.is_dead),  # Для расчета ИПН (если умер - не учитывать льготы)
            'is_dead': bool(worker.is_dead),  # Статус умершего
        })
    
    # Получаем все периоды для выбора
    all_periods = []
    if user_is_admin:
        all_coal_requests = CoalRequest.objects.all().order_by('-created_at')
        if selected_user_id:
            all_coal_requests = all_coal_requests.filter(worker__user_id=selected_user_id)
    else:
        all_coal_requests = CoalRequest.objects.filter(worker__user=request.user).order_by('-created_at')
    periods_set = set()
    for req in all_coal_requests:
        req_date = req.created_at.date()
        period_start_item = normalize_period_start(req_date)
        periods_set.add(period_start_item)
    
    all_periods = sorted(list(periods_set), reverse=True)
    
    # Определяем статус списка
    today = timezone.now().date()
    if today >= period_start and today <= period_end:
        status = 'active'  # Ведется
        status_display = 'Ведется'
    else:
        status = 'closed'  # Закрыт
        status_display = 'Закрыт'
    
    unissued_count = coal_requests.filter(is_issued=False).count() if hasattr(CoalRequest, 'is_issued') else None

    context = {
        'compensation_data': compensation_data,
        'period_start': period_start,
        'period_end': period_end,
        'all_periods': all_periods,
        'status': status,
        'status_display': status_display,
    }
    
    return JsonResponse({
        'compensation_data': compensation_data,
        'period_start': period_start.strftime('%d.%m.%Y'),
        'period_end': period_end.strftime('%d.%m.%Y'),
        'all_periods': [p.strftime('%Y-%m-%d') for p in all_periods],
        'status': status,
        'status_display': status_display,
        'total_count': len(compensation_data),
        'unissued_count': unissued_count,
        'worker_category': worker_category,
        'account_type_filter': account_type_filter,
    })


@login_required
def generate_coal_compensation_excel(request):
    """Генерация Excel файла списка компенсации за уголь"""
    user_is_admin = is_admin(request.user)
    selected_user_id = get_admin_selected_user_id(request)
    enterprise_name = get_print_enterprise_name(request, selected_user_id)
    worker_category = get_worker_category_filter(request)
    account_type_filter = get_account_type_filter(request)
    
    period_start, period_end = get_requested_period(request, get_coal_compensation_period)
    
    # Получаем все заявления на уголь в выбранном периоде
    if user_is_admin:
        coal_requests = CoalRequest.objects.filter(
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('worker', 'user').order_by('worker__full_name')
        if selected_user_id:
            coal_requests = coal_requests.filter(worker__user_id=selected_user_id)
    else:
        coal_requests = CoalRequest.objects.filter(
            worker__user=request.user,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('worker').order_by('worker__full_name')

    coal_requests = apply_worker_category_filter(coal_requests, worker_category)
    coal_requests = apply_request_account_type_filter(coal_requests, account_type_filter)

    # Ведомость на выдачу: только НЕвыданные
    if request.GET.get('only_unissued') in ('1', 'true', 'True'):
        coal_requests = coal_requests.filter(is_issued=False)
    
    # Создаем Excel файл
    wb = Workbook()
    ws = wb.active
    ws.title = safe_excel_sheet_title(
        f"Список компенсации {period_start.strftime('%d.%m.%Y')}-{period_end.strftime('%d.%m.%Y')}"
    )
    
    # Стили - улучшенные
    header_fill = PatternFill(start_color=EXCEL_HEADER_COLOR, end_color=EXCEL_HEADER_COLOR, fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12, name='Arial')
    title_font = Font(bold=True, size=18, color="FFFFFF", name='Arial')
    border_style = Border(
        left=Side(style='thin', color=EXCEL_BORDER_COLOR),
        right=Side(style='thin', color=EXCEL_BORDER_COLOR),
        top=Side(style='thin', color=EXCEL_BORDER_COLOR),
        bottom=Side(style='thin', color=EXCEL_BORDER_COLOR)
    )
    center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left_alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    right_alignment = Alignment(horizontal='right', vertical='center', wrap_text=True)
    
    # Красивый заголовок
    ws.merge_cells('A1:I1')
    title_cell = ws['A1']
    title_cell.value = f'СПИСОК КОМПЕНСАЦИИ ЗА УГОЛЬ'
    title_cell.font = title_font
    title_cell.fill = header_fill
    title_cell.alignment = center_alignment
    title_cell.border = border_style
    ws.row_dimensions[1].height = 35
    
    # Период
    ws.merge_cells('A2:I2')
    period_cell = ws['A2']
    period_cell.value = (
        f'Период: с {period_start.strftime("%d.%m.%Y")} по {period_end.strftime("%d.%m.%Y")}\n'
        f'Предприятие: {enterprise_name}\n'
        f'Вид помощи: Компенсация за уголь'
    )
    period_cell.font = Font(bold=True, size=12, name='Arial')
    period_cell.alignment = center_alignment
    period_cell.border = border_style
    ws.row_dimensions[2].height = 36
    
    # Статус
    today = timezone.now().date()
    if today >= period_start and today <= period_end:
        status_text = 'Статус: Ведется'
        status_fill = PatternFill(start_color=EXCEL_STATUS_ACTIVE_COLOR, end_color=EXCEL_STATUS_ACTIVE_COLOR, fill_type="solid")
    else:
        status_text = 'Статус: Закрыт'
        status_fill = PatternFill(start_color=EXCEL_STATUS_CLOSED_COLOR, end_color=EXCEL_STATUS_CLOSED_COLOR, fill_type="solid")
    
    ws.merge_cells('A3:I3')
    status_cell = ws['A3']
    status_cell.value = status_text
    status_cell.font = Font(bold=True, size=12, color="FFFFFF", name='Arial')
    status_cell.fill = status_fill
    status_cell.alignment = center_alignment
    status_cell.border = border_style
    ws.row_dimensions[3].height = 25
    
    # Пустая строка
    ws.row_dimensions[4].height = 5
    
    # Заголовки таблицы
    headers = ['№', 'ФИО', 'ИИН', 'Счет карты', 'Банк', 'Льготы', 'Начислено', 'ИПН', 'К выплате']
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_alignment
        cell.border = border_style
    ws.row_dimensions[5].height = 30
    
    # Данные
    row_num = 6
    
    for coal_request in coal_requests:
        worker = coal_request.worker
        
        # Порядковый номер
        ws.cell(row=row_num, column=1, value=row_num - 5).alignment = center_alignment
        
        # ФИО
        ws.cell(row=row_num, column=2, value=worker.full_name).alignment = left_alignment
        
        # ИИН
        ws.cell(row=row_num, column=3, value=worker.inn or '').alignment = center_alignment
        
        # Счет (карточный или текущий)
        if coal_request.account_type == '20_digit':
            account_number = coal_request.account_number or worker.account_20_digit or ''
        else:
            account_number = coal_request.account_number or worker.current_account or ''
        ws.cell(row=row_num, column=4, value=account_number).alignment = left_alignment
        
        # Банк (всегда Народный Банк)
        ws.cell(row=row_num, column=5, value='Народный Банк').alignment = center_alignment
        
        # Льготы (для умерших пенсионеров не показываем льготы)
        benefits = ''
        if not bool(worker.is_dead) and bool(worker.has_benefits) and worker.benefits_name:
            benefits = worker.benefits_name
        ws.cell(row=row_num, column=6, value=benefits).alignment = left_alignment
        
        # Начислено
        accrued_value = coal_request.accrued if coal_request.accrued else ''
        ws.cell(row=row_num, column=7, value=accrued_value).alignment = right_alignment
        ws.cell(row=row_num, column=7).number_format = EXCEL_CURRENCY_FORMAT
        
        # ИПН
        ipn_value = coal_request.ipn if coal_request.ipn else ''
        ws.cell(row=row_num, column=8, value=ipn_value).alignment = right_alignment
        ws.cell(row=row_num, column=8).number_format = EXCEL_CURRENCY_FORMAT
        
        # К выплате
        to_pay_value = coal_request.to_pay if coal_request.to_pay else ''
        ws.cell(row=row_num, column=9, value=to_pay_value).alignment = right_alignment
        ws.cell(row=row_num, column=9).number_format = EXCEL_CURRENCY_FORMAT
        
        # Применяем границы
        max_col = 9
        for col in range(1, max_col + 1):
            ws.cell(row=row_num, column=col).border = border_style
        
        row_num += 1
    
    # Итоговая строка
    total_accrued = sum(float(cr.accrued) if cr.accrued else 0 for cr in coal_requests)
    total_ipn = sum(float(cr.ipn) if cr.ipn else 0 for cr in coal_requests)
    total_to_pay = sum(float(cr.to_pay) if cr.to_pay else 0 for cr in coal_requests)
    
    total_fill = PatternFill(start_color=EXCEL_TOTAL_FILL_COLOR, end_color=EXCEL_TOTAL_FILL_COLOR, fill_type="solid")
    total_font = Font(bold=True, size=12, name='Arial')
    
    ws.cell(row=row_num, column=1, value='ИТОГО:').font = total_font
    ws.cell(row=row_num, column=1).alignment = right_alignment
    ws.merge_cells(f'A{row_num}:F{row_num}')
    ws.cell(row=row_num, column=7, value=total_accrued).font = total_font
    ws.cell(row=row_num, column=7).alignment = right_alignment
    ws.cell(row=row_num, column=7).number_format = EXCEL_CURRENCY_FORMAT
    ws.cell(row=row_num, column=8, value=total_ipn).font = total_font
    ws.cell(row=row_num, column=8).alignment = right_alignment
    ws.cell(row=row_num, column=8).number_format = EXCEL_CURRENCY_FORMAT
    ws.cell(row=row_num, column=9, value=total_to_pay).font = total_font
    ws.cell(row=row_num, column=9).alignment = right_alignment
    ws.cell(row=row_num, column=9).number_format = EXCEL_CURRENCY_FORMAT
    
    max_col = 9
    for col in range(1, max_col + 1):
        ws.cell(row=row_num, column=col).border = border_style
        ws.cell(row=row_num, column=col).fill = total_fill
    
    # Настройка ширины колонок
    ws.column_dimensions['A'].width = 8  # №
    ws.column_dimensions['B'].width = 35  # ФИО
    ws.column_dimensions['C'].width = 15  # ИИН
    ws.column_dimensions['D'].width = 25  # Счет карты
    ws.column_dimensions['E'].width = 18  # Банк
    ws.column_dimensions['F'].width = 25  # Льготы
    ws.column_dimensions['G'].width = 15  # Начислено
    ws.column_dimensions['H'].width = 15  # ИПН
    ws.column_dimensions['I'].width = 15  # К выплате
    
    # Высота строк
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 25
    ws.row_dimensions[3].height = 25
    ws.row_dimensions[4].height = 6
    ws.row_dimensions[5].height = 30

    max_col = 9
    ws.auto_filter.ref = f"A5:{get_column_letter(max_col)}{max(row_num - 1, 5)}"
    ws.freeze_panes = 'A6'
    
    # Сохраняем в BytesIO
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"Список_компенсации_за_уголь_{period_start.strftime('%d.%m.%Y')}-{period_end.strftime('%d.%m.%Y')}.xlsx"
    safe_filename = transliterate_filename(filename)
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    
    return response


@login_required
def bonus_payment_list(request):
    """Отображение списка на доплату за 3 степени к наградным знакам"""
    user_is_admin = is_admin(request.user)
    selected_user_id = get_admin_selected_user_id(request)
    worker_category = get_worker_category_filter(request)
    account_type_filter = get_account_type_filter(request)
    
    period_start, period_end = get_requested_period(request, get_coal_compensation_period)
    
    # Определяем, является ли выбранный период текущим
    today = timezone.now().date()
    is_current_period = (today >= period_start and today <= period_end)
    
    # Получаем всех живых пенсионеров с шахтерской/трудовой славой.
    if user_is_admin:
        base_query = Worker.objects.filter(
            status__in=Worker.PENSIONER_STATUS_CODES,
            has_miner_glory=True,
            is_dead=False,
        ).select_related('user')
        if selected_user_id:
            base_query = base_query.filter(user_id=selected_user_id)
        
        if not is_current_period:
            base_query = base_query.filter(
                bonus_period_start__isnull=False,
                bonus_period_start__gte=period_start,
                bonus_period_start__lte=period_end,
            )
        
        workers = apply_worker_category_filter(base_query, worker_category, status_field='status').order_by('full_name')
    else:
        base_query = Worker.objects.filter(
            user=request.user,
            status__in=Worker.PENSIONER_STATUS_CODES,
            has_miner_glory=True,
            is_dead=False,
        )
        
        if not is_current_period:
            base_query = base_query.filter(
                bonus_period_start__isnull=False,
                bonus_period_start__gte=period_start,
                bonus_period_start__lte=period_end,
            )
        
        workers = apply_worker_category_filter(base_query, worker_category, status_field='status').order_by('full_name')
    
    # Подготавливаем данные для таблицы
    bonus_data = []
    for idx, worker in enumerate(workers, 1):
        # Получаем счет карты из заявлений на уголь или погребение
        account_number = ''
        # Сначала проверяем заявления на уголь
        if user_is_admin:
            coal_request = CoalRequest.objects.filter(worker=worker).order_by('-created_at').first()
        else:
            coal_request = CoalRequest.objects.filter(worker__user=request.user, worker=worker).order_by('-created_at').first()
        
        resolved_account_type = ''
        if coal_request:
            if coal_request.account_type == '20_digit':
                account_number = coal_request.account_number or worker.account_20_digit or ''
                resolved_account_type = '20_digit'
            else:
                account_number = coal_request.account_number or worker.current_account or ''
                resolved_account_type = 'current'
        else:
            # Проверяем заявления на погребение (хотя для живых их не должно быть)
            if user_is_admin:
                funeral_request = FuneralRequest.objects.filter(worker=worker).order_by('-created_at').first()
            else:
                funeral_request = FuneralRequest.objects.filter(worker__user=request.user, worker=worker).order_by('-created_at').first()
            
            if funeral_request:
                if funeral_request.account_type == '20_digit':
                    account_number = funeral_request.account_number or ''
                    resolved_account_type = '20_digit'
                else:
                    account_number = funeral_request.account_number or worker.current_account or ''
                    resolved_account_type = 'current'
            else:
                # Используем account_20_digit из карточки работника
                account_number = worker.account_20_digit or worker.current_account or ''
                resolved_account_type = '20_digit' if worker.account_20_digit else ('current' if worker.current_account else '')

        if account_type_filter in {'20_digit', 'current'} and resolved_account_type != account_type_filter:
            continue
        
        # Получаем льготы (если у пенсионера есть льготы, указываем название)
        # Для умерших пенсионеров не показываем льготы
        benefits = ''
        if not bool(worker.is_dead) and bool(worker.has_benefits) and worker.benefits_name:
            benefits = worker.benefits_name
        
        # Показываем начисления только если сохраненный период попадает в выбранный диапазон.
        bonus_accrued = None
        bonus_ipn = None
        bonus_to_pay = None
        if worker.bonus_period_start and period_start <= worker.bonus_period_start <= period_end:
            bonus_accrued = worker.bonus_accrued
            bonus_ipn = worker.bonus_ipn
            bonus_to_pay = worker.bonus_to_pay
        
        bonus_data.append({
            'number': idx,
            'full_name': worker.full_name,
            'inn': worker.inn or '',
            'worker_status': worker.status,
            'worker_status_display': worker.get_status_display(),
            'account_number': account_number,
            'bank': 'Народный Банк',
            'benefits': benefits,
            'accrued': str(bonus_accrued) if bonus_accrued else '',
            'ipn': str(bonus_ipn) if bonus_ipn else '',
            'to_pay': str(bonus_to_pay) if bonus_to_pay else '',
            'worker_id': worker.id,
            'user_account': worker.user.username if user_is_admin else None,  # Аккаунт для админа
            'has_benefits': bool(worker.has_benefits) and not bool(worker.is_dead),  # Для расчета ИПН (если умер - не учитывать льготы)
            'is_dead': bool(worker.is_dead),  # Статус умершего
        })
    
    # Получаем все периоды для выбора (генерируем на основе текущей даты и предыдущих месяцев)
    all_periods = []
    today = timezone.now().date()
    
    # Генерируем периоды: текущий и 11 предыдущих месяцев (с 1 числа).
    for i in range(12):
        period_year = today.year
        period_month = today.month - i
        while period_month <= 0:
            period_month += 12
            period_year -= 1
        all_periods.append(date(period_year, period_month, 1))
    
    all_periods = sorted(list(set(all_periods)), reverse=True)
    
    # Определяем статус списка
    today = timezone.now().date()
    if today >= period_start and today <= period_end:
        status = 'active'  # Ведется
        status_display = 'Ведется'
    else:
        status = 'closed'  # Закрыт
        status_display = 'Закрыт'
    
    return JsonResponse({
        'bonus_data': bonus_data,
        'period_start': period_start.strftime('%d.%m.%Y'),
        'period_end': period_end.strftime('%d.%m.%Y'),
        'all_periods': [p.strftime('%Y-%m-%d') for p in all_periods],
        'status': status,
        'status_display': status_display,
        'worker_category': worker_category,
        'account_type_filter': account_type_filter,
    })


@login_required
def generate_bonus_payment_excel(request):
    """Генерация Excel файла списка на доплату за 3 степени к наградным знакам"""
    user_is_admin = is_admin(request.user)
    selected_user_id = get_admin_selected_user_id(request)
    enterprise_name = get_print_enterprise_name(request, selected_user_id)
    worker_category = get_worker_category_filter(request)
    account_type_filter = get_account_type_filter(request)
    
    period_start, period_end = get_requested_period(request, get_coal_compensation_period)
    
    # Определяем, является ли выбранный период текущим
    today = timezone.now().date()
    is_current_period = (today >= period_start and today <= period_end)
    
    # Получаем всех живых пенсионеров с шахтерской/трудовой славой.
    if user_is_admin:
        base_query = Worker.objects.filter(
            status__in=Worker.PENSIONER_STATUS_CODES,
            has_miner_glory=True,
            is_dead=False,
        ).select_related('user')
        if selected_user_id:
            base_query = base_query.filter(user_id=selected_user_id)
        
        if not is_current_period:
            base_query = base_query.filter(
                bonus_period_start__isnull=False,
                bonus_period_start__gte=period_start,
                bonus_period_start__lte=period_end,
            )
        
        workers = apply_worker_category_filter(base_query, worker_category, status_field='status').order_by('full_name')
    else:
        base_query = Worker.objects.filter(
            user=request.user,
            status__in=Worker.PENSIONER_STATUS_CODES,
            has_miner_glory=True,
            is_dead=False,
        )
        
        if not is_current_period:
            base_query = base_query.filter(
                bonus_period_start__isnull=False,
                bonus_period_start__gte=period_start,
                bonus_period_start__lte=period_end,
            )
        
        workers = apply_worker_category_filter(base_query, worker_category, status_field='status').order_by('full_name')
    
    # Создаем Excel файл
    wb = Workbook()
    ws = wb.active
    ws.title = safe_excel_sheet_title(
        f"Список на доплату {period_start.strftime('%d.%m.%Y')}-{period_end.strftime('%d.%m.%Y')}"
    )
    
    # Стили - улучшенные
    header_fill = PatternFill(start_color=EXCEL_HEADER_COLOR, end_color=EXCEL_HEADER_COLOR, fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12, name='Arial')
    title_font = Font(bold=True, size=18, color="FFFFFF", name='Arial')
    border_style = Border(
        left=Side(style='thin', color=EXCEL_BORDER_COLOR),
        right=Side(style='thin', color=EXCEL_BORDER_COLOR),
        top=Side(style='thin', color=EXCEL_BORDER_COLOR),
        bottom=Side(style='thin', color=EXCEL_BORDER_COLOR)
    )
    center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left_alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    right_alignment = Alignment(horizontal='right', vertical='center', wrap_text=True)
    
    # Красивый заголовок
    ws.merge_cells('A1:I1')
    title_cell = ws['A1']
    title_cell.value = f'СПИСОК НА ДОПЛАТУ ЗА 3 СТЕПЕНИ К НАГРАДНЫМ ЗНАКАМ'
    title_cell.font = title_font
    title_cell.fill = header_fill
    title_cell.alignment = center_alignment
    title_cell.border = border_style
    ws.row_dimensions[1].height = 35
    
    # Период
    ws.merge_cells('A2:I2')
    period_cell = ws['A2']
    period_cell.value = (
        f'Период: с {period_start.strftime("%d.%m.%Y")} по {period_end.strftime("%d.%m.%Y")}\n'
        f'Предприятие: {enterprise_name}\n'
        f'Вид помощи: Доплата за 3 степени'
    )
    period_cell.font = Font(bold=True, size=12, name='Arial')
    period_cell.alignment = center_alignment
    period_cell.border = border_style
    ws.row_dimensions[2].height = 36
    
    # Статус
    today = timezone.now().date()
    if today >= period_start and today <= period_end:
        status_text = 'Статус: Ведется'
        status_fill = PatternFill(start_color=EXCEL_STATUS_ACTIVE_COLOR, end_color=EXCEL_STATUS_ACTIVE_COLOR, fill_type="solid")
    else:
        status_text = 'Статус: Закрыт'
        status_fill = PatternFill(start_color=EXCEL_STATUS_CLOSED_COLOR, end_color=EXCEL_STATUS_CLOSED_COLOR, fill_type="solid")
    
    ws.merge_cells('A3:I3')
    status_cell = ws['A3']
    status_cell.value = status_text
    status_cell.font = Font(bold=True, size=12, color="FFFFFF", name='Arial')
    status_cell.fill = status_fill
    status_cell.alignment = center_alignment
    status_cell.border = border_style
    ws.row_dimensions[3].height = 25
    
    # Пустая строка
    ws.row_dimensions[4].height = 5
    
    # Заголовки таблицы
    headers = ['№', 'ФИО', 'ИИН', 'Счет карты', 'Банк', 'Льготы', 'Начислено', 'ИПН', 'К выплате']
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_alignment
        cell.border = border_style
    ws.row_dimensions[5].height = 30
    
    # Данные
    row_num = 6
    
    display_index = 1
    total_accrued = 0.0
    total_ipn = 0.0
    total_to_pay = 0.0
    for worker in workers:
        # Получаем счет карты
        account_number = ''
        resolved_account_type = ''
        coal_qs = CoalRequest.objects.filter(worker=worker)
        if not user_is_admin:
            coal_qs = coal_qs.filter(worker__user=request.user)
        coal_request = coal_qs.order_by('-created_at').first()
        
        if coal_request:
            if coal_request.account_type == '20_digit':
                account_number = coal_request.account_number or worker.account_20_digit or ''
                resolved_account_type = '20_digit'
            else:
                account_number = coal_request.account_number or worker.current_account or ''
                resolved_account_type = 'current'
        else:
            funeral_qs = FuneralRequest.objects.filter(worker=worker)
            if not user_is_admin:
                funeral_qs = funeral_qs.filter(worker__user=request.user)
            funeral_request = funeral_qs.order_by('-created_at').first()
            
            if funeral_request:
                if funeral_request.account_type == '20_digit':
                    account_number = funeral_request.account_number or ''
                    resolved_account_type = '20_digit'
                else:
                    account_number = funeral_request.account_number or worker.current_account or ''
                    resolved_account_type = 'current'
            else:
                account_number = worker.account_20_digit or worker.current_account or ''
                resolved_account_type = '20_digit' if worker.account_20_digit else ('current' if worker.current_account else '')

        if account_type_filter in {'20_digit', 'current'} and resolved_account_type != account_type_filter:
            continue
        
        # Показываем начисления только если сохраненный период попадает в выбранный диапазон.
        bonus_accrued = None
        bonus_ipn = None
        bonus_to_pay = None
        if worker.bonus_period_start and period_start <= worker.bonus_period_start <= period_end:
            bonus_accrued = worker.bonus_accrued
            bonus_ipn = worker.bonus_ipn
            bonus_to_pay = worker.bonus_to_pay
        if bonus_accrued:
            total_accrued += float(bonus_accrued)
        if bonus_ipn:
            total_ipn += float(bonus_ipn)
        if bonus_to_pay:
            total_to_pay += float(bonus_to_pay)
        
        # Порядковый номер
        ws.cell(row=row_num, column=1, value=display_index).alignment = center_alignment
        
        # ФИО
        ws.cell(row=row_num, column=2, value=worker.full_name).alignment = left_alignment
        
        # ИИН
        ws.cell(row=row_num, column=3, value=worker.inn or '').alignment = center_alignment
        
        # Счет карты
        ws.cell(row=row_num, column=4, value=account_number).alignment = left_alignment
        
        # Банк (всегда Народный Банк)
        ws.cell(row=row_num, column=5, value='Народный Банк').alignment = center_alignment
        
        # Льготы (для умерших пенсионеров не показываем льготы)
        benefits = ''
        if not bool(worker.is_dead) and bool(worker.has_benefits) and worker.benefits_name:
            benefits = worker.benefits_name
        ws.cell(row=row_num, column=6, value=benefits).alignment = left_alignment
        
        # Начислено
        accrued_value = bonus_accrued if bonus_accrued else ''
        ws.cell(row=row_num, column=7, value=accrued_value).alignment = right_alignment
        ws.cell(row=row_num, column=7).number_format = EXCEL_CURRENCY_FORMAT
        
        # ИПН
        ipn_value = bonus_ipn if bonus_ipn else ''
        ws.cell(row=row_num, column=8, value=ipn_value).alignment = right_alignment
        ws.cell(row=row_num, column=8).number_format = EXCEL_CURRENCY_FORMAT
        
        # К выплате
        to_pay_value = bonus_to_pay if bonus_to_pay else ''
        ws.cell(row=row_num, column=9, value=to_pay_value).alignment = right_alignment
        ws.cell(row=row_num, column=9).number_format = EXCEL_CURRENCY_FORMAT
        
        # Применяем границы
        max_col = 9
        for col in range(1, max_col + 1):
            ws.cell(row=row_num, column=col).border = border_style
        
        row_num += 1
        display_index += 1
    
    # Итоговая строка
    
    ws.cell(row=row_num, column=1, value='ИТОГО:').font = Font(bold=True)
    ws.cell(row=row_num, column=1).alignment = right_alignment
    ws.merge_cells(f'A{row_num}:F{row_num}')
    ws.cell(row=row_num, column=7, value=total_accrued).font = Font(bold=True)
    ws.cell(row=row_num, column=7).alignment = right_alignment
    ws.cell(row=row_num, column=7).number_format = EXCEL_CURRENCY_FORMAT
    ws.cell(row=row_num, column=8, value=total_ipn).font = Font(bold=True)
    ws.cell(row=row_num, column=8).alignment = right_alignment
    ws.cell(row=row_num, column=8).number_format = EXCEL_CURRENCY_FORMAT
    ws.cell(row=row_num, column=9, value=total_to_pay).font = Font(bold=True)
    ws.cell(row=row_num, column=9).alignment = right_alignment
    ws.cell(row=row_num, column=9).number_format = EXCEL_CURRENCY_FORMAT

    max_col = 9
    total_fill = PatternFill(start_color=EXCEL_TOTAL_FILL_COLOR, end_color=EXCEL_TOTAL_FILL_COLOR, fill_type="solid")
    for col in range(1, max_col + 1):
        ws.cell(row=row_num, column=col).border = border_style
        ws.cell(row=row_num, column=col).fill = total_fill
    
    # Настройка ширины колонок
    ws.column_dimensions['A'].width = 8  # №
    ws.column_dimensions['B'].width = 35  # ФИО
    ws.column_dimensions['C'].width = 15  # ИИН
    ws.column_dimensions['D'].width = 25  # Счет карты
    ws.column_dimensions['E'].width = 18  # Банк
    ws.column_dimensions['F'].width = 25  # Льготы
    ws.column_dimensions['G'].width = 15  # Начислено
    ws.column_dimensions['H'].width = 15  # ИПН
    ws.column_dimensions['I'].width = 15  # К выплате
    
    # Высота строк
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 25
    ws.row_dimensions[3].height = 25
    ws.row_dimensions[5].height = 30

    ws.auto_filter.ref = f"A5:{get_column_letter(max_col)}{max(row_num - 1, 5)}"
    ws.freeze_panes = 'A6'
    
    # Сохраняем в BytesIO
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"Список_на_доплату_за_3_степени_{period_start.strftime('%d.%m.%Y')}-{period_end.strftime('%d.%m.%Y')}.xlsx"
    safe_filename = transliterate_filename(filename)
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    
    return response


@login_required
def funeral_services_list(request):
    """Отображение списка ритуальных услуг"""
    user_is_admin = is_admin(request.user)
    selected_user_id = get_admin_selected_user_id(request)
    worker_category = get_worker_category_filter(request)
    account_type_filter = get_account_type_filter(request)
    
    period_start, period_end = get_requested_period(request, get_coal_compensation_period)
    
    # Получаем все заявления на погребение в выбранном периоде
    if user_is_admin:
        funeral_requests = FuneralRequest.objects.filter(
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('worker', 'user').order_by('worker__full_name')
        if selected_user_id:
            funeral_requests = funeral_requests.filter(worker__user_id=selected_user_id)
    else:
        funeral_requests = FuneralRequest.objects.filter(
            worker__user=request.user,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('worker').order_by('worker__full_name')

    funeral_requests = apply_worker_category_filter(funeral_requests, worker_category)
    funeral_requests = apply_request_account_type_filter(funeral_requests, account_type_filter)
    
    # Подготавливаем данные для таблицы
    funeral_data = []
    for idx, funeral_request in enumerate(funeral_requests, 1):
        worker = funeral_request.worker
        # Получаем счет карты
        account_number = ''
        if funeral_request.account_type == '20_digit':
            account_number = funeral_request.account_number or worker.account_20_digit or ''
        else:
            account_number = funeral_request.account_number or worker.current_account or ''
        
        funeral_data.append({
            'number': idx,
            'applicant_full_name': funeral_request.applicant_full_name,
            'applicant_inn': funeral_request.applicant_inn,
            'worker_status': worker.status,
            'worker_status_display': worker.get_status_display(),
            'account_number': account_number,
            'pensioner_full_name': worker.full_name,
            'bank': 'Народный Банк',
            'to_pay': str(funeral_request.to_pay) if funeral_request.to_pay else '',
            'funeral_request_id': funeral_request.id,
            'worker_id': worker.id,
            'user_account': funeral_request.user.username if user_is_admin else None,  # Аккаунт для админа
        })
    
    # Получаем все периоды для выбора
    all_periods = []
    if user_is_admin:
        all_funeral_requests = FuneralRequest.objects.all().order_by('-created_at')
        if selected_user_id:
            all_funeral_requests = all_funeral_requests.filter(worker__user_id=selected_user_id)
    else:
        all_funeral_requests = FuneralRequest.objects.filter(worker__user=request.user).order_by('-created_at')
    periods_set = set()
    for req in all_funeral_requests:
        req_date = req.created_at.date()
        period_start_item = normalize_period_start(req_date)
        periods_set.add(period_start_item)
    
    all_periods = sorted(list(periods_set), reverse=True)
    
    # Определяем статус списка
    today = timezone.now().date()
    if today >= period_start and today <= period_end:
        status = 'active'  # Ведется
        status_display = 'Ведется'
    else:
        status = 'closed'  # Закрыт
        status_display = 'Закрыт'
    
    return JsonResponse({
        'funeral_data': funeral_data,
        'period_start': period_start.strftime('%d.%m.%Y'),
        'period_end': period_end.strftime('%d.%m.%Y'),
        'all_periods': [p.strftime('%Y-%m-%d') for p in all_periods],
        'status': status,
        'status_display': status_display,
        'worker_category': worker_category,
        'account_type_filter': account_type_filter,
    })


@login_required
def generate_funeral_services_excel(request):
    """Генерация Excel файла списка ритуальных услуг"""
    user_is_admin = is_admin(request.user)
    selected_user_id = get_admin_selected_user_id(request)
    enterprise_name = get_print_enterprise_name(request, selected_user_id)
    worker_category = get_worker_category_filter(request)
    account_type_filter = get_account_type_filter(request)
    
    period_start, period_end = get_requested_period(request, get_coal_compensation_period)
    
    # Получаем все заявления на погребение в выбранном периоде
    if user_is_admin:
        funeral_requests = FuneralRequest.objects.filter(
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('worker', 'user').order_by('worker__full_name')
        if selected_user_id:
            funeral_requests = funeral_requests.filter(worker__user_id=selected_user_id)
    else:
        funeral_requests = FuneralRequest.objects.filter(
            worker__user=request.user,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('worker').order_by('worker__full_name')

    funeral_requests = apply_worker_category_filter(funeral_requests, worker_category)
    funeral_requests = apply_request_account_type_filter(funeral_requests, account_type_filter)
    
    # Создаем Excel файл
    wb = Workbook()
    ws = wb.active
    ws.title = safe_excel_sheet_title(
        f"Список ритуальных услуг {period_start.strftime('%d.%m.%Y')}-{period_end.strftime('%d.%m.%Y')}"
    )
    
    # Стили - улучшенные
    header_fill = PatternFill(start_color=EXCEL_HEADER_COLOR, end_color=EXCEL_HEADER_COLOR, fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12, name='Arial')
    title_font = Font(bold=True, size=18, color="FFFFFF", name='Arial')
    border_style = Border(
        left=Side(style='thin', color=EXCEL_BORDER_COLOR),
        right=Side(style='thin', color=EXCEL_BORDER_COLOR),
        top=Side(style='thin', color=EXCEL_BORDER_COLOR),
        bottom=Side(style='thin', color=EXCEL_BORDER_COLOR)
    )
    center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left_alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    right_alignment = Alignment(horizontal='right', vertical='center', wrap_text=True)
    
    # Красивый заголовок
    ws.merge_cells('A1:G1')
    title_cell = ws['A1']
    title_cell.value = f'СПИСОК РИТУАЛЬНЫХ УСЛУГ'
    title_cell.font = title_font
    title_cell.fill = header_fill
    title_cell.alignment = center_alignment
    title_cell.border = border_style
    ws.row_dimensions[1].height = 35
    
    # Период
    ws.merge_cells('A2:G2')
    period_cell = ws['A2']
    period_cell.value = (
        f'Период: с {period_start.strftime("%d.%m.%Y")} по {period_end.strftime("%d.%m.%Y")}\n'
        f'Предприятие: {enterprise_name}\n'
        f'Вид помощи: Ритуальные услуги'
    )
    period_cell.font = Font(bold=True, size=12, name='Arial')
    period_cell.alignment = center_alignment
    period_cell.border = border_style
    ws.row_dimensions[2].height = 36
    
    # Статус
    today = timezone.now().date()
    if today >= period_start and today <= period_end:
        status_text = 'Статус: Ведется'
        status_fill = PatternFill(start_color=EXCEL_STATUS_ACTIVE_COLOR, end_color=EXCEL_STATUS_ACTIVE_COLOR, fill_type="solid")
    else:
        status_text = 'Статус: Закрыт'
        status_fill = PatternFill(start_color=EXCEL_STATUS_CLOSED_COLOR, end_color=EXCEL_STATUS_CLOSED_COLOR, fill_type="solid")
    
    ws.merge_cells('A3:G3')
    status_cell = ws['A3']
    status_cell.value = status_text
    status_cell.font = Font(bold=True, size=12, color="FFFFFF", name='Arial')
    status_cell.fill = status_fill
    status_cell.alignment = center_alignment
    status_cell.border = border_style
    ws.row_dimensions[3].height = 25
    
    # Пустая строка
    ws.row_dimensions[4].height = 5
    
    # Заголовки таблицы
    headers = ['№', 'ФИО ЗАЯВИТЕЛЯ', 'ИИН ЗАЯВИТЕЛЯ', 'СЧЕТ КАРТЫ', 'ФИО ПЕНСИОНЕРА', 'БАНК', 'К ВЫПЛАТЕ']
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_alignment
        cell.border = border_style
    ws.row_dimensions[5].height = 30
    
    # Данные
    row_num = 6
    
    for funeral_request in funeral_requests:
        # Получаем счет карты
        account_number = ''
        if funeral_request.account_type == '20_digit':
            account_number = funeral_request.account_number or funeral_request.worker.account_20_digit or ''
        else:
            account_number = funeral_request.account_number or funeral_request.worker.current_account or ''
        
        # Порядковый номер
        ws.cell(row=row_num, column=1, value=row_num - 5).alignment = center_alignment
        
        # ФИО заявителя
        ws.cell(row=row_num, column=2, value=funeral_request.applicant_full_name).alignment = left_alignment
        
        # ИИН заявителя
        ws.cell(row=row_num, column=3, value=funeral_request.applicant_inn).alignment = center_alignment
        
        # Счет карты
        ws.cell(row=row_num, column=4, value=account_number).alignment = left_alignment
        
        # ФИО пенсионера
        ws.cell(row=row_num, column=5, value=funeral_request.worker.full_name).alignment = left_alignment
        
        # Банк (всегда Народный Банк)
        ws.cell(row=row_num, column=6, value='Народный Банк').alignment = center_alignment
        
        # К выплате
        to_pay_value = funeral_request.to_pay if funeral_request.to_pay else ''
        ws.cell(row=row_num, column=7, value=to_pay_value).alignment = right_alignment
        ws.cell(row=row_num, column=7).number_format = EXCEL_CURRENCY_FORMAT
        
        # Применяем границы
        max_col = 7
        for col in range(1, max_col + 1):
            ws.cell(row=row_num, column=col).border = border_style
        
        row_num += 1
    
    # Итоговая строка
    total_to_pay = sum(float(fr.to_pay) if fr.to_pay else 0 for fr in funeral_requests)
    
    total_fill = PatternFill(start_color=EXCEL_TOTAL_FILL_COLOR, end_color=EXCEL_TOTAL_FILL_COLOR, fill_type="solid")
    total_font = Font(bold=True, size=12, name='Arial')
    
    ws.cell(row=row_num, column=1, value='ИТОГО:').font = total_font
    ws.cell(row=row_num, column=1).alignment = right_alignment
    ws.merge_cells(f'A{row_num}:F{row_num}')
    ws.cell(row=row_num, column=7, value=total_to_pay).font = total_font
    ws.cell(row=row_num, column=7).alignment = right_alignment
    ws.cell(row=row_num, column=7).number_format = EXCEL_CURRENCY_FORMAT
    
    max_col = 7
    for col in range(1, max_col + 1):
        ws.cell(row=row_num, column=col).border = border_style
        ws.cell(row=row_num, column=col).fill = total_fill
    
    # Настройка ширины колонок
    ws.column_dimensions['A'].width = 8  # №
    ws.column_dimensions['B'].width = 30  # ФИО ЗАЯВИТЕЛЯ
    ws.column_dimensions['C'].width = 15  # ИИН ЗАЯВИТЕЛЯ
    ws.column_dimensions['D'].width = 25  # СЧЕТ КАРТЫ
    ws.column_dimensions['E'].width = 30  # ФИО ПЕНСИОНЕРА
    ws.column_dimensions['F'].width = 18  # БАНК
    ws.column_dimensions['G'].width = 15  # К ВЫПЛАТЕ
    
    # Высота строк
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 25
    ws.row_dimensions[3].height = 25
    ws.row_dimensions[5].height = 30

    ws.auto_filter.ref = f"A5:{get_column_letter(max_col)}{max(row_num - 1, 5)}"
    ws.freeze_panes = 'A6'
    
    # Сохраняем в BytesIO
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"Список_ритуальных_услуг_{period_start.strftime('%d.%m.%Y')}-{period_end.strftime('%d.%m.%Y')}.xlsx"
    safe_filename = transliterate_filename(filename)
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    
    return response


@login_required
def pensioner_material_assistance_list(request):
    """Отображение списка материальной помощи пенсионерам"""
    user_is_admin = is_admin(request.user)
    selected_user_id = get_admin_selected_user_id(request)
    worker_category = get_worker_category_filter(request)
    account_type_filter = get_account_type_filter(request)
    
    period_start, period_end = get_requested_period(request, get_coal_compensation_period)
    
    # Получаем все заявления на материальную помощь для пенсионеров (на лечение) в выбранном периоде
    if user_is_admin:
        material_requests = MaterialAssistanceRequest.objects.filter(
            worker__status__in=Worker.PENSIONER_STATUS_CODES,
            assistance_type='treatment',
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('worker', 'user').order_by('worker__full_name')
        if selected_user_id:
            material_requests = material_requests.filter(worker__user_id=selected_user_id)
    else:
        material_requests = MaterialAssistanceRequest.objects.filter(
            user=request.user,
            worker__status__in=Worker.PENSIONER_STATUS_CODES,
            assistance_type='treatment',
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('worker').order_by('worker__full_name')

    material_requests = apply_worker_category_filter(material_requests, worker_category)
    material_requests = apply_request_account_type_filter(material_requests, account_type_filter)
    
    # Подготавливаем данные для таблицы
    assistance_data = []
    for idx, material_request in enumerate(material_requests, 1):
        worker = material_request.worker
        
        # Получаем счет карты из заявлений на уголь или погребение
        account_number = ''
        # Сначала проверяем заявления на уголь
        if user_is_admin:
            coal_request = CoalRequest.objects.filter(worker=worker).order_by('-created_at').first()
        else:
            coal_request = CoalRequest.objects.filter(worker__user=request.user, worker=worker).order_by('-created_at').first()
        
        if coal_request:
            if coal_request.account_type == '20_digit':
                account_number = coal_request.account_number or worker.account_20_digit or ''
            else:
                account_number = coal_request.account_number or worker.current_account or ''
        else:
            # Проверяем заявления на погребение
            if user_is_admin:
                funeral_request = FuneralRequest.objects.filter(worker=worker).order_by('-created_at').first()
            else:
                funeral_request = FuneralRequest.objects.filter(worker__user=request.user, worker=worker).order_by('-created_at').first()
            
            if funeral_request:
                if funeral_request.account_type == '20_digit':
                    account_number = funeral_request.account_number or worker.account_20_digit or ''
                else:
                    account_number = funeral_request.account_number or worker.current_account or ''
            else:
                # Используем account_20_digit из карточки работника
                account_number = worker.account_20_digit or worker.current_account or ''
        
        # Получаем льготы (если у пенсионера есть льготы, указываем название)
        # Для умерших пенсионеров не показываем льготы
        benefits = ''
        if not bool(worker.is_dead) and bool(worker.has_benefits) and worker.benefits_name:
            benefits = worker.benefits_name
        
        assistance_data.append({
            'number': idx,
            'full_name': worker.full_name,
            'inn': worker.inn or '',
            'worker_status': worker.status,
            'worker_status_display': worker.get_status_display(),
            'account_number': account_number,
            'bank': 'Народный Банк',
            'benefits': benefits,
            'accrued': str(material_request.accrued) if material_request.accrued else '',
            'ipn': str(material_request.ipn) if material_request.ipn else '',
            'to_pay': str(material_request.to_pay) if material_request.to_pay else '',
            'material_request_id': material_request.id,
            'is_issued': bool(getattr(material_request, 'is_issued', False)),
            'worker_id': worker.id,
            'user_account': material_request.user.username if user_is_admin else None,  # Аккаунт для админа
            'has_benefits': bool(worker.has_benefits) and not bool(worker.is_dead),  # Для расчета ИПН (если умер - не учитывать льготы)
            'is_dead': bool(worker.is_dead),  # Статус умершего
        })
    
    # Получаем все периоды для выбора
    all_periods = []
    if user_is_admin:
        all_material_requests = MaterialAssistanceRequest.objects.filter(
            worker__status__in=Worker.PENSIONER_STATUS_CODES,
            assistance_type='treatment'
        ).order_by('-created_at')
        if selected_user_id:
            all_material_requests = all_material_requests.filter(worker__user_id=selected_user_id)
    else:
        all_material_requests = MaterialAssistanceRequest.objects.filter(
            user=request.user,
            worker__status__in=Worker.PENSIONER_STATUS_CODES,
            assistance_type='treatment'
        ).order_by('-created_at')
    
    periods_set = set()
    for req in all_material_requests:
        req_date = req.created_at.date()
        period_start_item = normalize_period_start(req_date)
        periods_set.add(period_start_item)
    
    all_periods = sorted(list(periods_set), reverse=True)
    
    # Определяем статус списка
    today = timezone.now().date()
    if today >= period_start and today <= period_end:
        status = 'active'  # Ведется
        status_display = 'Ведется'
    else:
        status = 'closed'  # Закрыт
        status_display = 'Закрыт'
    
    unissued_count = material_requests.filter(is_issued=False).count() if hasattr(MaterialAssistanceRequest, 'is_issued') else None

    return JsonResponse({
        'assistance_data': assistance_data,
        'period_start': period_start.strftime('%d.%m.%Y'),
        'period_end': period_end.strftime('%d.%m.%Y'),
        'all_periods': [p.strftime('%Y-%m-%d') for p in all_periods],
        'status': status,
        'status_display': status_display,
        'total_count': len(assistance_data),
        'unissued_count': unissued_count,
        'worker_category': worker_category,
        'account_type_filter': account_type_filter,
    })


@login_required
def material_assistance_registry_list(request):
    """Реестр (таблица) всех заявлений на материальную помощь"""
    user_is_admin = is_admin(request.user)
    selected_user_id = get_admin_selected_user_id(request)
    worker_category = get_worker_category_filter(request)
    account_type_filter = get_account_type_filter(request)

    period_start, period_end = get_requested_period(request, get_coal_compensation_period)

    if user_is_admin:
        material_requests = MaterialAssistanceRequest.objects.filter(
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('worker', 'user').order_by('worker__full_name')
        if selected_user_id:
            material_requests = material_requests.filter(worker__user_id=selected_user_id)
    else:
        material_requests = MaterialAssistanceRequest.objects.filter(
            worker__user=request.user,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('worker').order_by('worker__full_name')

    material_requests = apply_worker_category_filter(material_requests, worker_category)
    material_requests = apply_request_account_type_filter(material_requests, account_type_filter)

    registry_data = []
    for idx, req in enumerate(material_requests, 1):
        worker = req.worker
        if req.account_type == '20_digit':
            account_number = req.account_number or worker.account_20_digit or ''
        else:
            account_number = req.account_number or worker.current_account or ''

        registry_data.append({
            'number': idx,
            'full_name': worker.full_name,
            'inn': worker.inn or '',
            'worker_status': worker.status,
            'worker_status_display': worker.get_status_display(),
            'account_number': account_number,
            'assistance_type': req.get_assistance_type_display(),
            'amount': str(req.amount) if req.amount is not None else '',
            'status': req.get_status(),
            'status_text': req.get_status_display_text(),
            'created_at': req.created_at.strftime('%d.%m.%Y'),
            'material_request_id': req.id,
            'worker_id': worker.id,
            'user_account': req.user.username if user_is_admin else None,
            'is_issued': bool(getattr(req, 'is_issued', False)),
        })

    # периоды для селектора
    if user_is_admin:
        all_requests = MaterialAssistanceRequest.objects.all().order_by('-created_at')
        if selected_user_id:
            all_requests = all_requests.filter(worker__user_id=selected_user_id)
    else:
        all_requests = MaterialAssistanceRequest.objects.filter(worker__user=request.user).order_by('-created_at')

    periods_set = set()
    for req in all_requests:
        req_date = req.created_at.date()
        period_start_item = normalize_period_start(req_date)
        periods_set.add(period_start_item)

    all_periods = sorted(list(periods_set), reverse=True)

    today = timezone.now().date()
    if today >= period_start and today <= period_end:
        status = 'active'
        status_display = 'Ведется'
    else:
        status = 'closed'
        status_display = 'Закрыт'

    unissued_count = material_requests.filter(is_issued=False).count() if hasattr(MaterialAssistanceRequest, 'is_issued') else None

    return JsonResponse({
        'registry_data': registry_data,
        'period_start': period_start.strftime('%d.%m.%Y'),
        'period_end': period_end.strftime('%d.%m.%Y'),
        'all_periods': [p.strftime('%Y-%m-%d') for p in all_periods],
        'status': status,
        'status_display': status_display,
        'total_count': len(registry_data),
        'unissued_count': unissued_count,
        'worker_category': worker_category,
        'account_type_filter': account_type_filter,
    })


@login_required
def generate_material_assistance_registry_excel(request):
    """Excel-экспорт реестра материальной помощи"""
    user_is_admin = is_admin(request.user)
    selected_user_id = get_admin_selected_user_id(request)
    enterprise_name = get_print_enterprise_name(request, selected_user_id)
    worker_category = get_worker_category_filter(request)
    account_type_filter = get_account_type_filter(request)

    period_start, period_end = get_requested_period(request, get_coal_compensation_period)

    if user_is_admin:
        material_requests = MaterialAssistanceRequest.objects.filter(
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('worker', 'user').order_by('worker__full_name')
        if selected_user_id:
            material_requests = material_requests.filter(worker__user_id=selected_user_id)
    else:
        material_requests = MaterialAssistanceRequest.objects.filter(
            worker__user=request.user,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('worker').order_by('worker__full_name')

    material_requests = apply_worker_category_filter(material_requests, worker_category)
    material_requests = apply_request_account_type_filter(material_requests, account_type_filter)

    today = timezone.now().date()
    is_active_period = period_start <= today <= period_end

    wb = Workbook()
    ws = wb.active
    ws.title = safe_excel_sheet_title("Реестр матпомощи")

    headers = ['№', 'ФИО', 'ИИН', 'Счет карты', 'Вид помощи', 'Сумма', 'Статус', 'Дата создания', 'Выдано']

    total_columns = len(headers)
    amount_column = headers.index('Сумма') + 1

    header_fill = PatternFill(start_color=EXCEL_HEADER_COLOR, end_color=EXCEL_HEADER_COLOR, fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11, name='Arial')
    title_font = Font(bold=True, color="FFFFFF", size=16, name='Arial')
    border_style = Border(
        left=Side(style='thin', color=EXCEL_BORDER_COLOR),
        right=Side(style='thin', color=EXCEL_BORDER_COLOR),
        top=Side(style='thin', color=EXCEL_BORDER_COLOR),
        bottom=Side(style='thin', color=EXCEL_BORDER_COLOR)
    )
    center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left_alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    right_alignment = Alignment(horizontal='right', vertical='center', wrap_text=True)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_columns)
    ws.cell(row=1, column=1, value='РЕЕСТР МАТЕРИАЛЬНОЙ ПОМОЩИ').font = title_font
    ws.cell(row=1, column=1).fill = header_fill
    ws.cell(row=1, column=1).alignment = center_alignment
    ws.cell(row=1, column=1).border = border_style
    ws.row_dimensions[1].height = 32

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=total_columns)
    ws.cell(
        row=2,
        column=1,
        value=(
            f'Период: с {period_start.strftime("%d.%m.%Y")} по {period_end.strftime("%d.%m.%Y")}\n'
            f'Предприятие: {enterprise_name}\n'
            f'Вид помощи: Реестр материальной помощи'
        ),
    ).font = Font(bold=True, size=11, name='Arial')
    ws.cell(row=2, column=1).alignment = center_alignment
    ws.cell(row=2, column=1).border = border_style
    ws.row_dimensions[2].height = 34

    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=total_columns)
    ws.cell(row=3, column=1, value=f'Статус: {"Ведется" if is_active_period else "Закрыт"}').font = Font(bold=True, color="FFFFFF", size=11, name='Arial')
    ws.cell(row=3, column=1).fill = PatternFill(
        start_color=EXCEL_STATUS_ACTIVE_COLOR if is_active_period else EXCEL_STATUS_CLOSED_COLOR,
        end_color=EXCEL_STATUS_ACTIVE_COLOR if is_active_period else EXCEL_STATUS_CLOSED_COLOR,
        fill_type="solid",
    )
    ws.cell(row=3, column=1).alignment = center_alignment
    ws.cell(row=3, column=1).border = border_style
    ws.row_dimensions[3].height = 22

    ws.row_dimensions[4].height = 6

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col_num, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_alignment
        cell.border = border_style
    ws.row_dimensions[5].height = 26

    from decimal import Decimal

    row_num = 6
    total_amount = Decimal('0')
    for idx, req in enumerate(material_requests, 1):
        worker = req.worker
        if req.account_type == '20_digit':
            account_number = req.account_number or worker.account_20_digit or ''
        else:
            account_number = req.account_number or worker.current_account or ''

        col = 1
        ws.cell(row=row_num, column=col, value=idx).alignment = center_alignment
        col += 1
        ws.cell(row=row_num, column=col, value=worker.full_name).alignment = left_alignment
        col += 1
        ws.cell(row=row_num, column=col, value=worker.inn or '').alignment = center_alignment
        col += 1
        ws.cell(row=row_num, column=col, value=account_number).alignment = left_alignment
        col += 1
        ws.cell(row=row_num, column=col, value=req.get_assistance_type_display()).alignment = left_alignment
        col += 1

        amount_value = float(req.amount) if req.amount is not None else None
        ws.cell(row=row_num, column=col, value=amount_value).alignment = right_alignment
        ws.cell(row=row_num, column=col).number_format = EXCEL_CURRENCY_FORMAT
        if req.amount is not None:
            total_amount += req.amount
        col += 1

        ws.cell(row=row_num, column=col, value=req.get_status_display_text()).alignment = center_alignment
        col += 1
        ws.cell(row=row_num, column=col, value=req.created_at.strftime('%d.%m.%Y')).alignment = center_alignment
        col += 1
        ws.cell(row=row_num, column=col, value='Да' if getattr(req, 'is_issued', False) else 'Нет').alignment = center_alignment

        for border_col in range(1, total_columns + 1):
            ws.cell(row=row_num, column=border_col).border = border_style
        row_num += 1

    ws.cell(row=row_num, column=1, value='ИТОГО:').font = Font(bold=True, size=11, name='Arial')
    ws.cell(row=row_num, column=1).alignment = right_alignment
    if amount_column > 1:
        ws.merge_cells(start_row=row_num, start_column=1, end_row=row_num, end_column=amount_column - 1)
    ws.cell(row=row_num, column=amount_column, value=float(total_amount)).font = Font(bold=True, size=11, name='Arial')
    ws.cell(row=row_num, column=amount_column).alignment = right_alignment
    ws.cell(row=row_num, column=amount_column).number_format = EXCEL_CURRENCY_FORMAT

    for border_col in range(1, total_columns + 1):
        cell = ws.cell(row=row_num, column=border_col)
        cell.border = border_style
        cell.fill = PatternFill(start_color=EXCEL_TOTAL_FILL_COLOR, end_color=EXCEL_TOTAL_FILL_COLOR, fill_type="solid")

    widths = {
        'A': 8,   # №
        'B': 34,  # ФИО
        'C': 16,  # ИИН
        'D': 25,  # Счет карты
        'E': 30,  # Вид помощи
        'F': 16,  # Сумма
        'G': 22,  # Статус
        'H': 16,  # Дата создания
        'I': 12,  # Выдано
    }

    for column_letter, width in widths.items():
        ws.column_dimensions[column_letter].width = width

    ws.auto_filter.ref = f"A5:{get_column_letter(total_columns)}{max(row_num - 1, 5)}"
    ws.freeze_panes = 'A6'

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"Реестр_матпомощи_{period_start.strftime('%d.%m.%Y')}-{period_end.strftime('%d.%m.%Y')}.xlsx"
    safe_filename = transliterate_filename(filename)
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    return response


@login_required
def generate_pensioner_material_assistance_excel(request):
    """Генерация Excel файла списка материальной помощи пенсионерам"""
    user_is_admin = is_admin(request.user)
    selected_user_id = get_admin_selected_user_id(request)
    enterprise_name = get_print_enterprise_name(request, selected_user_id)
    worker_category = get_worker_category_filter(request)
    account_type_filter = get_account_type_filter(request)
    
    period_start, period_end = get_requested_period(request, get_coal_compensation_period)
    
    # Получаем все заявления на материальную помощь для пенсионеров (на лечение) в выбранном периоде
    if user_is_admin:
        material_requests = MaterialAssistanceRequest.objects.filter(
            worker__status__in=Worker.PENSIONER_STATUS_CODES,
            assistance_type='treatment',
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('worker', 'user').order_by('worker__full_name')
        if selected_user_id:
            material_requests = material_requests.filter(worker__user_id=selected_user_id)
    else:
        material_requests = MaterialAssistanceRequest.objects.filter(
            user=request.user,
            worker__status__in=Worker.PENSIONER_STATUS_CODES,
            assistance_type='treatment',
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('worker').order_by('worker__full_name')

    material_requests = apply_worker_category_filter(material_requests, worker_category)
    material_requests = apply_request_account_type_filter(material_requests, account_type_filter)

    # Ведомость на выдачу: только НЕвыданные
    if request.GET.get('only_unissued') in ('1', 'true', 'True'):
        material_requests = material_requests.filter(is_issued=False)
    
    # Создаем Excel файл
    wb = Workbook()
    ws = wb.active
    ws.title = safe_excel_sheet_title(
        f"Список материальной помощи {period_start.strftime('%d.%m.%Y')}-{period_end.strftime('%d.%m.%Y')}"
    )
    
    # Стили - улучшенные
    header_fill = PatternFill(start_color=EXCEL_HEADER_COLOR, end_color=EXCEL_HEADER_COLOR, fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12, name='Arial')
    title_font = Font(bold=True, size=18, color="FFFFFF", name='Arial')
    border_style = Border(
        left=Side(style='thin', color=EXCEL_BORDER_COLOR),
        right=Side(style='thin', color=EXCEL_BORDER_COLOR),
        top=Side(style='thin', color=EXCEL_BORDER_COLOR),
        bottom=Side(style='thin', color=EXCEL_BORDER_COLOR)
    )
    center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left_alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    right_alignment = Alignment(horizontal='right', vertical='center', wrap_text=True)
    
    # Красивый заголовок
    ws.merge_cells('A1:I1')
    title_cell = ws['A1']
    title_cell.value = f'СПИСОК МАТЕРИАЛЬНОЙ ПОМОЩИ ПЕНСИОНЕРАМ'
    title_cell.font = title_font
    title_cell.fill = header_fill
    title_cell.alignment = center_alignment
    title_cell.border = border_style
    ws.row_dimensions[1].height = 35
    
    # Период
    ws.merge_cells('A2:I2')
    period_cell = ws['A2']
    period_cell.value = (
        f'Период: с {period_start.strftime("%d.%m.%Y")} по {period_end.strftime("%d.%m.%Y")}\n'
        f'Предприятие: {enterprise_name}\n'
        f'Вид помощи: Материальная помощь пенсионерам'
    )
    period_cell.font = Font(bold=True, size=12, name='Arial')
    period_cell.alignment = center_alignment
    period_cell.border = border_style
    ws.row_dimensions[2].height = 36
    
    # Статус
    today = timezone.now().date()
    if today >= period_start and today <= period_end:
        status_text = 'Статус: Ведется'
        status_fill = PatternFill(start_color=EXCEL_STATUS_ACTIVE_COLOR, end_color=EXCEL_STATUS_ACTIVE_COLOR, fill_type="solid")
    else:
        status_text = 'Статус: Закрыт'
        status_fill = PatternFill(start_color=EXCEL_STATUS_CLOSED_COLOR, end_color=EXCEL_STATUS_CLOSED_COLOR, fill_type="solid")
    
    ws.merge_cells('A3:I3')
    status_cell = ws['A3']
    status_cell.value = status_text
    status_cell.font = Font(bold=True, size=12, color="FFFFFF", name='Arial')
    status_cell.fill = status_fill
    status_cell.alignment = center_alignment
    status_cell.border = border_style
    ws.row_dimensions[3].height = 25
    
    # Пустая строка
    ws.row_dimensions[4].height = 5
    
    # Заголовки таблицы
    headers = ['№', 'ФИО', 'ИИН', 'СЧЕТ КАРТЫ', 'БАНК', 'ЛЬГОТЫ', 'НАЧИСЛЕНО', 'ИПН', 'К ВЫПЛАТЕ']
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_alignment
        cell.border = border_style
    ws.row_dimensions[5].height = 30
    
    # Данные
    row_num = 6
    
    for material_request in material_requests:
        worker = material_request.worker
        
        # Получаем счет карты
        account_number = ''
        coal_qs = CoalRequest.objects.filter(worker=worker)
        if not user_is_admin:
            coal_qs = coal_qs.filter(worker__user=request.user)
        coal_request = coal_qs.order_by('-created_at').first()
        
        if coal_request:
            if coal_request.account_type == '20_digit':
                account_number = coal_request.account_number or worker.account_20_digit or ''
            else:
                account_number = coal_request.account_number or worker.current_account or ''
        else:
            funeral_qs = FuneralRequest.objects.filter(worker=worker)
            if not user_is_admin:
                funeral_qs = funeral_qs.filter(worker__user=request.user)
            funeral_request = funeral_qs.order_by('-created_at').first()
            
            if funeral_request:
                if funeral_request.account_type == '20_digit':
                    account_number = funeral_request.account_number or worker.account_20_digit or ''
                else:
                    account_number = funeral_request.account_number or worker.current_account or ''
            else:
                account_number = worker.account_20_digit or worker.current_account or ''
        
        # Порядковый номер
        ws.cell(row=row_num, column=1, value=row_num - 5).alignment = center_alignment
        
        # ФИО
        ws.cell(row=row_num, column=2, value=worker.full_name).alignment = left_alignment
        
        # ИИН
        ws.cell(row=row_num, column=3, value=worker.inn or '').alignment = center_alignment
        
        # Счет карты
        ws.cell(row=row_num, column=4, value=account_number).alignment = left_alignment
        
        # Банк (всегда Народный Банк)
        ws.cell(row=row_num, column=5, value='Народный Банк').alignment = center_alignment
        
        # Льготы (для умерших пенсионеров не показываем льготы)
        benefits = ''
        if not bool(worker.is_dead) and bool(worker.has_benefits) and worker.benefits_name:
            benefits = worker.benefits_name
        ws.cell(row=row_num, column=6, value=benefits).alignment = left_alignment
        
        # Начислено
        accrued_value = material_request.accrued if material_request.accrued else ''
        ws.cell(row=row_num, column=7, value=accrued_value).alignment = right_alignment
        ws.cell(row=row_num, column=7).number_format = EXCEL_CURRENCY_FORMAT
        
        # ИПН
        ipn_value = material_request.ipn if material_request.ipn else ''
        ws.cell(row=row_num, column=8, value=ipn_value).alignment = right_alignment
        ws.cell(row=row_num, column=8).number_format = EXCEL_CURRENCY_FORMAT
        
        # К выплате
        to_pay_value = material_request.to_pay if material_request.to_pay else ''
        ws.cell(row=row_num, column=9, value=to_pay_value).alignment = right_alignment
        ws.cell(row=row_num, column=9).number_format = EXCEL_CURRENCY_FORMAT
        
        # Применяем границы
        max_col = 9
        for col in range(1, max_col + 1):
            ws.cell(row=row_num, column=col).border = border_style
        
        row_num += 1
    
    # Итоговая строка
    total_accrued = sum(float(mr.accrued) if mr.accrued else 0 for mr in material_requests)
    total_ipn = sum(float(mr.ipn) if mr.ipn else 0 for mr in material_requests)
    total_to_pay = sum(float(mr.to_pay) if mr.to_pay else 0 for mr in material_requests)
    
    ws.cell(row=row_num, column=1, value='ИТОГО:').font = Font(bold=True)
    ws.cell(row=row_num, column=1).alignment = right_alignment
    ws.merge_cells(f'A{row_num}:F{row_num}')
    ws.cell(row=row_num, column=7, value=total_accrued).font = Font(bold=True)
    ws.cell(row=row_num, column=7).alignment = right_alignment
    ws.cell(row=row_num, column=7).number_format = EXCEL_CURRENCY_FORMAT
    ws.cell(row=row_num, column=8, value=total_ipn).font = Font(bold=True)
    ws.cell(row=row_num, column=8).alignment = right_alignment
    ws.cell(row=row_num, column=8).number_format = EXCEL_CURRENCY_FORMAT
    ws.cell(row=row_num, column=9, value=total_to_pay).font = Font(bold=True)
    ws.cell(row=row_num, column=9).alignment = right_alignment
    ws.cell(row=row_num, column=9).number_format = EXCEL_CURRENCY_FORMAT

    max_col = 9
    total_fill = PatternFill(start_color=EXCEL_TOTAL_FILL_COLOR, end_color=EXCEL_TOTAL_FILL_COLOR, fill_type="solid")
    for col in range(1, max_col + 1):
        ws.cell(row=row_num, column=col).border = border_style
        ws.cell(row=row_num, column=col).fill = total_fill
    
    # Настройка ширины колонок
    ws.column_dimensions['A'].width = 8  # №
    ws.column_dimensions['B'].width = 35  # ФИО
    ws.column_dimensions['C'].width = 15  # ИИН
    ws.column_dimensions['D'].width = 25  # Счет карты
    ws.column_dimensions['E'].width = 18  # Банк
    ws.column_dimensions['F'].width = 25  # Льготы
    ws.column_dimensions['G'].width = 15  # Начислено
    ws.column_dimensions['H'].width = 15  # ИПН
    ws.column_dimensions['I'].width = 15  # К выплате
    
    # Высота строк
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 25
    ws.row_dimensions[3].height = 25
    ws.row_dimensions[5].height = 30

    ws.auto_filter.ref = f"A5:{get_column_letter(max_col)}{max(row_num - 1, 5)}"
    ws.freeze_panes = 'A6'
    
    # Сохраняем в BytesIO
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"Список_материальной_помощи_пенсионерам_{period_start.strftime('%d.%m.%Y')}-{period_end.strftime('%d.%m.%Y')}.xlsx"
    safe_filename = transliterate_filename(filename)
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    
    return response


@login_required
def update_coal_compensation_payment(request, request_id):
    """Обновление значений начислено, ИПН, к выплате для заявления на уголь"""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    if request.method == 'POST':
        try:
            coal_request = CoalRequest.objects.get(id=request_id)
            accrued = request.POST.get('accrued', '').strip()
            ipn = request.POST.get('ipn', '').strip()
            to_pay = request.POST.get('to_pay', '').strip()
            
            from decimal import Decimal, InvalidOperation
            
            if accrued:
                try:
                    accrued_value = Decimal(accrued)
                    coal_request.accrued = accrued_value
                    # Если умер - не учитывать льготы, всегда считать ИПН
                    if bool(coal_request.worker.is_dead) or not bool(coal_request.worker.has_benefits):
                        coal_request.ipn = accrued_value * Decimal('0.10')
                        coal_request.to_pay = accrued_value - coal_request.ipn
                    else:
                        coal_request.ipn = Decimal('0.00')
                        coal_request.to_pay = accrued_value
                except (InvalidOperation, ValueError):
                    return JsonResponse({'error': 'Неверное значение начислено'}, status=400)
            else:
                coal_request.accrued = None
            
            if ipn:
                try:
                    coal_request.ipn = Decimal(ipn)
                    if coal_request.accrued:
                        coal_request.to_pay = coal_request.accrued - coal_request.ipn
                except (InvalidOperation, ValueError):
                    return JsonResponse({'error': 'Неверное значение ИПН'}, status=400)
            else:
                coal_request.ipn = None
            
            if to_pay:
                try:
                    coal_request.to_pay = Decimal(to_pay)
                except (InvalidOperation, ValueError):
                    return JsonResponse({'error': 'Неверное значение к выплате'}, status=400)
            else:
                coal_request.to_pay = None
            
            coal_request.save()
            
            return JsonResponse({
                'success': True,
                'accrued': str(coal_request.accrued) if coal_request.accrued else '',
                'ipn': str(coal_request.ipn) if coal_request.ipn else '',
                'to_pay': str(coal_request.to_pay) if coal_request.to_pay else '',
            })
        except CoalRequest.DoesNotExist:
            return JsonResponse({'error': 'Заявление не найдено'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def update_bonus_payment(request, worker_id):
    """Обновление значений начислено, ИПН, к выплате для списка на доплату за 3 степени"""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    if request.method == 'POST':
        try:
            worker = Worker.objects.get(id=worker_id)
            period_start_str = request.POST.get('period_start', '').strip()
            accrued = request.POST.get('accrued', '').strip()
            ipn = request.POST.get('ipn', '').strip()
            to_pay = request.POST.get('to_pay', '').strip()
            
            if not period_start_str:
                return JsonResponse({'error': 'Не указан период'}, status=400)
            
            try:
                period_start = date.fromisoformat(period_start_str)
            except (ValueError, TypeError):
                return JsonResponse({'error': 'Неверный формат даты периода'}, status=400)
            
            from decimal import Decimal, InvalidOperation
            
            worker.bonus_period_start = period_start
            
            if accrued:
                try:
                    accrued_value = Decimal(accrued)
                    worker.bonus_accrued = accrued_value
                    # Если умер - не учитывать льготы, всегда считать ИПН
                    if bool(worker.is_dead) or not bool(worker.has_benefits):
                        worker.bonus_ipn = accrued_value * Decimal('0.10')
                        worker.bonus_to_pay = accrued_value - worker.bonus_ipn
                    else:
                        worker.bonus_ipn = Decimal('0.00')
                        worker.bonus_to_pay = accrued_value
                except (InvalidOperation, ValueError):
                    return JsonResponse({'error': 'Неверное значение начислено'}, status=400)
            else:
                worker.bonus_accrued = None
            
            if ipn:
                try:
                    worker.bonus_ipn = Decimal(ipn)
                    if worker.bonus_accrued:
                        worker.bonus_to_pay = worker.bonus_accrued - worker.bonus_ipn
                except (InvalidOperation, ValueError):
                    return JsonResponse({'error': 'Неверное значение ИПН'}, status=400)
            else:
                worker.bonus_ipn = None
            
            if to_pay:
                try:
                    worker.bonus_to_pay = Decimal(to_pay)
                except (InvalidOperation, ValueError):
                    return JsonResponse({'error': 'Неверное значение к выплате'}, status=400)
            else:
                worker.bonus_to_pay = None
            
            worker.save()
            
            return JsonResponse({
                'success': True,
                'accrued': str(worker.bonus_accrued) if worker.bonus_accrued else '',
                'ipn': str(worker.bonus_ipn) if worker.bonus_ipn else '',
                'to_pay': str(worker.bonus_to_pay) if worker.bonus_to_pay else '',
            })
        except Worker.DoesNotExist:
            return JsonResponse({'error': 'Работник не найден'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def update_funeral_services_payment(request, request_id):
    """Обновление значения к выплате для заявления на погребение"""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    if request.method == 'POST':
        try:
            funeral_request = FuneralRequest.objects.get(id=request_id)
            to_pay = request.POST.get('to_pay', '').strip()
            
            from decimal import Decimal, InvalidOperation
            
            if to_pay:
                try:
                    funeral_request.to_pay = Decimal(to_pay)
                except (InvalidOperation, ValueError):
                    return JsonResponse({'error': 'Неверное значение к выплате'}, status=400)
            else:
                funeral_request.to_pay = None
            
            funeral_request.save()
            
            return JsonResponse({
                'success': True,
                'to_pay': str(funeral_request.to_pay) if funeral_request.to_pay else '',
            })
        except FuneralRequest.DoesNotExist:
            return JsonResponse({'error': 'Заявление не найдено'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def update_pensioner_material_assistance_payment(request, request_id):
    """Обновление значений начислено, ИПН, к выплате для заявления на материальную помощь пенсионерам"""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    if request.method == 'POST':
        try:
            material_request = MaterialAssistanceRequest.objects.get(id=request_id)
            accrued = request.POST.get('accrued', '').strip()
            ipn = request.POST.get('ipn', '').strip()
            to_pay = request.POST.get('to_pay', '').strip()
            
            from decimal import Decimal, InvalidOperation
            
            if accrued:
                try:
                    accrued_value = Decimal(accrued)
                    material_request.accrued = accrued_value
                    # Если умер - не учитывать льготы, всегда считать ИПН
                    if bool(material_request.worker.is_dead) or not bool(material_request.worker.has_benefits):
                        material_request.ipn = accrued_value * Decimal('0.10')
                        material_request.to_pay = accrued_value - material_request.ipn
                    else:
                        material_request.ipn = Decimal('0.00')
                        material_request.to_pay = accrued_value
                except (InvalidOperation, ValueError):
                    return JsonResponse({'error': 'Неверное значение начислено'}, status=400)
            else:
                material_request.accrued = None
            
            if ipn:
                try:
                    material_request.ipn = Decimal(ipn)
                    if material_request.accrued:
                        material_request.to_pay = material_request.accrued - material_request.ipn
                except (InvalidOperation, ValueError):
                    return JsonResponse({'error': 'Неверное значение ИПН'}, status=400)
            else:
                material_request.ipn = None
            
            if to_pay:
                try:
                    material_request.to_pay = Decimal(to_pay)
                except (InvalidOperation, ValueError):
                    return JsonResponse({'error': 'Неверное значение к выплате'}, status=400)
            else:
                material_request.to_pay = None
            
            material_request.save()
            
            return JsonResponse({
                'success': True,
                'accrued': str(material_request.accrued) if material_request.accrued else '',
                'ipn': str(material_request.ipn) if material_request.ipn else '',
                'to_pay': str(material_request.to_pay) if material_request.to_pay else '',
            })
        except MaterialAssistanceRequest.DoesNotExist:
            return JsonResponse({'error': 'Заявление не найдено'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def reject_vacation_request(request, request_id):
    """Отказать по заявлению на путевку (перевод в единый статус Неактивно/Отклонено)"""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    vacation = get_object_or_404(VacationRequest.objects.defer('price'), id=request_id)
    vacation.request_status = 'inactive'
    vacation.save(update_fields=['request_status', 'updated_at'])
    return JsonResponse({'success': True, 'status': vacation.get_status(), 'status_text': vacation.get_status_display_text()})


@login_required
def reject_material_assistance_request(request, request_id):
    """Отказать по заявлению на материальную помощь (единый статус Неактивно/Отклонено)"""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    material_request = get_object_or_404(MaterialAssistanceRequest, id=request_id)
    material_request.request_status = 'inactive'
    material_request.save(update_fields=['request_status', 'updated_at'])
    return JsonResponse({'success': True, 'status': material_request.get_status(), 'status_text': material_request.get_status_display_text()})


@login_required
def reject_coal_request(request, request_id):
    """Отказать по заявлению на уголь (единый статус Неактивно/Отклонено)"""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    coal_request = get_object_or_404(CoalRequest, id=request_id)
    coal_request.request_status = 'inactive'
    coal_request.save(update_fields=['request_status', 'updated_at'])
    return JsonResponse({'success': True, 'status': coal_request.get_status(), 'status_text': coal_request.get_status_display_text()})


@login_required
def reject_funeral_request(request, request_id):
    """Отказать по заявлению на погребение (единый статус Неактивно/Отклонено)"""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    funeral_request = get_object_or_404(FuneralRequest, id=request_id)
    funeral_request.request_status = 'inactive'
    funeral_request.save(update_fields=['request_status', 'updated_at'])
    return JsonResponse({'success': True, 'status': funeral_request.get_status(), 'status_text': funeral_request.get_status_display_text()})


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    s = str(value).strip().lower()
    return s in ('1', 'true', 'yes', 'да', 'y', 'on')


def _request_payload(request):
    if request.content_type and 'application/json' in request.content_type:
        try:
            import json
            data = json.loads(request.body.decode('utf-8') or '{}')
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return request.POST


def _validate_kz_account_number(account_number):
    account_number = _normalize_kz_account(account_number)
    if not account_number:
        return 'Не указан номер счета'
    if not account_number.startswith('KZ'):
        return 'Номер счета должен начинаться с KZ'
    if len(account_number) != 20:
        return 'Номер счета должен содержать KZ и 18 цифр'
    if not account_number[2:].isdigit():
        return 'После KZ должны быть только цифры'
    return None


def _normalize_kz_account(value):
    raw = (value or '').upper().replace(' ', '')
    if raw in ('', 'KZ'):
        return ''
    if raw.startswith('KZ'):
        return raw
    digits = ''.join(ch for ch in raw if ch.isdigit())
    return f'KZ{digits}' if digits else ''


def _resolve_account_type_and_number_from_worker(worker, requested_type, requested_number, allowed_choices):
    account_type = (requested_type or '').strip()
    account_number = _normalize_kz_account(requested_number)

    if account_type not in allowed_choices:
        if _normalize_kz_account(worker.account_20_digit):
            account_type = '20_digit'
        elif _normalize_kz_account(worker.current_account):
            account_type = 'current'
        else:
            account_type = '20_digit'

    if not account_number:
        if account_type == '20_digit':
            account_number = _normalize_kz_account(worker.account_20_digit)
        else:
            account_number = _normalize_kz_account(worker.current_account)

    if not account_number and account_type == '20_digit':
        account_number = _normalize_kz_account(worker.current_account)
        account_type = 'current' if account_number else account_type
    elif not account_number and account_type == 'current':
        account_number = _normalize_kz_account(worker.account_20_digit)
        account_type = '20_digit' if account_number else account_type

    return account_type, account_number


@login_required
def edit_material_assistance_request(request, request_id):
    """Редактирование заявления на материальную помощь."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user_is_admin = is_admin(request.user)
    if user_is_admin:
        material_request = get_object_or_404(MaterialAssistanceRequest, id=request_id)
    else:
        material_request = get_object_or_404(MaterialAssistanceRequest, id=request_id, worker__user=request.user)

    if material_request.request_status == 'inactive':
        return JsonResponse({'error': 'Неактивное заявление нельзя редактировать'}, status=400)

    payload = _request_payload(request)

    assistance_type = (payload.get('assistance_type') or material_request.assistance_type or '').strip()
    allowed_choices = dict(MaterialAssistanceRequest.ACCOUNT_TYPE_CHOICES)
    account_type, account_number = _resolve_account_type_and_number_from_worker(
        material_request.worker,
        payload.get('account_type') or material_request.account_type,
        payload.get('account_number') or material_request.account_number,
        allowed_choices,
    )
    amount_raw = payload.get('amount')

    if assistance_type not in dict(MaterialAssistanceRequest.ASSISTANCE_TYPE_CHOICES):
        return JsonResponse({'error': 'Некорректный вид помощи'}, status=400)
    if account_type not in allowed_choices:
        return JsonResponse({'error': 'Некорректный тип счета'}, status=400)

    worker = material_request.worker
    if worker.is_pensioner_like():
        account_error = _validate_kz_account_number(account_number)
        if account_error:
            return JsonResponse({'error': account_error}, status=400)
        if assistance_type != 'treatment':
            return JsonResponse({'error': 'Для пенсионеров доступна только помощь на лечение'}, status=400)
        amount_decimal = Decimal('0')
    else:
        # Для работников поля счета скрыты, но если счет найден/введен, сохраняем его.
        if account_number:
            account_error = _validate_kz_account_number(account_number)
            if account_error:
                return JsonResponse({'error': account_error}, status=400)
        if amount_raw in (None, ''):
            amount_raw = material_request.amount
        try:
            amount_decimal = Decimal(str(amount_raw))
        except (InvalidOperation, TypeError, ValueError):
            return JsonResponse({'error': 'Некорректная сумма'}, status=400)
        if amount_decimal <= 0:
            return JsonResponse({'error': 'Сумма должна быть больше 0'}, status=400)

    material_request.assistance_type = assistance_type
    material_request.amount = amount_decimal
    material_request.account_type = account_type
    material_request.account_number = account_number
    material_request.save(update_fields=['assistance_type', 'amount', 'account_type', 'account_number', 'updated_at'])

    return JsonResponse({'success': True})


@login_required
def edit_coal_request(request, request_id):
    """Редактирование заявления на уголь."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user_is_admin = is_admin(request.user)
    if user_is_admin:
        coal_request = get_object_or_404(CoalRequest, id=request_id)
    else:
        coal_request = get_object_or_404(CoalRequest, id=request_id, worker__user=request.user)

    if coal_request.request_status == 'inactive':
        return JsonResponse({'error': 'Неактивное заявление нельзя редактировать'}, status=400)

    payload = _request_payload(request)
    allowed_choices = dict(CoalRequest.ACCOUNT_TYPE_CHOICES)
    account_type, account_number = _resolve_account_type_and_number_from_worker(
        coal_request.worker,
        payload.get('account_type') or coal_request.account_type,
        payload.get('account_number') or coal_request.account_number,
        allowed_choices,
    )

    if account_type not in allowed_choices:
        return JsonResponse({'error': 'Некорректный тип счета'}, status=400)
    account_error = _validate_kz_account_number(account_number)
    if account_error:
        return JsonResponse({'error': account_error}, status=400)

    coal_request.account_type = account_type
    coal_request.account_number = account_number
    coal_request.save(update_fields=['account_type', 'account_number', 'updated_at'])

    return JsonResponse({'success': True})


@login_required
def edit_funeral_request(request, request_id):
    """Редактирование заявления на погребение."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user_is_admin = is_admin(request.user)
    if user_is_admin:
        funeral_request = get_object_or_404(FuneralRequest, id=request_id)
    else:
        funeral_request = get_object_or_404(FuneralRequest, id=request_id, worker__user=request.user)

    if funeral_request.request_status == 'inactive':
        return JsonResponse({'error': 'Неактивное заявление нельзя редактировать'}, status=400)

    payload = _request_payload(request)
    applicant_full_name = (payload.get('applicant_full_name') or funeral_request.applicant_full_name or '').strip()
    applicant_inn = ''.join(c for c in (payload.get('applicant_inn') or funeral_request.applicant_inn or '') if c.isdigit())
    allowed_choices = dict(FuneralRequest.ACCOUNT_TYPE_CHOICES)
    account_type, account_number = _resolve_account_type_and_number_from_worker(
        funeral_request.worker,
        payload.get('account_type') or funeral_request.account_type,
        payload.get('account_number') or funeral_request.account_number,
        allowed_choices,
    )
    death_date_raw = (payload.get('death_date') or '').strip()

    if not applicant_full_name:
        return JsonResponse({'error': 'Не указано ФИО заявителя'}, status=400)
    if len(applicant_inn) != 12:
        return JsonResponse({'error': 'ИИН должен содержать 12 цифр'}, status=400)
    if account_type not in allowed_choices:
        return JsonResponse({'error': 'Некорректный тип счета'}, status=400)
    account_error = _validate_kz_account_number(account_number)
    if account_error:
        return JsonResponse({'error': account_error}, status=400)

    death_date = None
    if death_date_raw:
        try:
            death_date = datetime.strptime(death_date_raw, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Некорректная дата смерти пенсионера'}, status=400)
        if death_date > date.today():
            return JsonResponse({'error': 'Дата смерти не может быть в будущем'}, status=400)

    worker = funeral_request.worker
    if death_date is not None:
        worker.death_date = death_date
        worker.is_dead = True
        worker.save(update_fields=['death_date', 'is_dead', 'updated_at'])

    funeral_request.applicant_full_name = applicant_full_name
    funeral_request.applicant_inn = applicant_inn
    funeral_request.account_type = account_type
    funeral_request.account_number = account_number
    funeral_request.save(update_fields=['applicant_full_name', 'applicant_inn', 'account_type', 'account_number', 'updated_at'])

    return JsonResponse({'success': True})


@login_required
def toggle_coal_request_issued(request, request_id):
    """Флажок 'Выдать/Выдано' для списка угля (только админ)"""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    coal_request = get_object_or_404(CoalRequest, id=request_id)

    is_issued = None
    if request.content_type and 'application/json' in request.content_type:
        try:
            import json
            payload = json.loads(request.body.decode('utf-8') or '{}')
            is_issued = payload.get('is_issued')
        except Exception:
            is_issued = None
    if is_issued is None:
        is_issued = request.POST.get('is_issued')

    coal_request.is_issued = _parse_bool(is_issued)
    coal_request.save(update_fields=['is_issued', 'updated_at'])

    return JsonResponse({'success': True, 'is_issued': bool(coal_request.is_issued)})


@login_required
def toggle_pensioner_material_assistance_issued(request, request_id):
    """Флажок 'Выдать/Выдано' для списка матпомощи пенсионерам (только админ)"""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    material_request = get_object_or_404(MaterialAssistanceRequest, id=request_id)

    is_issued = None
    if request.content_type and 'application/json' in request.content_type:
        try:
            import json
            payload = json.loads(request.body.decode('utf-8') or '{}')
            is_issued = payload.get('is_issued')
        except Exception:
            is_issued = None
    if is_issued is None:
        is_issued = request.POST.get('is_issued')

    material_request.is_issued = _parse_bool(is_issued)
    material_request.save(update_fields=['is_issued', 'updated_at'])

    return JsonResponse({'success': True, 'is_issued': bool(material_request.is_issued)})


@login_required
def delete_vacation_request(request, request_id):
    """Удаление заявления на путёвку."""
    if request.method not in ('POST', 'DELETE'):
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    if is_admin(request.user):
        vacation = get_object_or_404(VacationRequest.objects.defer('price'), id=request_id)
    else:
        vacation = get_object_or_404(VacationRequest.objects.defer('price'), id=request_id, worker__user=request.user)

    vacation.delete()
    return JsonResponse({'success': True})


@login_required
def delete_coal_request(request, request_id):
    """Удаление заявления на уголь."""
    if request.method not in ('POST', 'DELETE'):
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    if is_admin(request.user):
        coal_request = get_object_or_404(CoalRequest, id=request_id)
    else:
        coal_request = get_object_or_404(CoalRequest, id=request_id, worker__user=request.user)
    coal_request.delete()
    return JsonResponse({'success': True})


@login_required
def delete_material_assistance_request(request, request_id):
    """Удаление заявления на материальную помощь."""
    if request.method not in ('POST', 'DELETE'):
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    if is_admin(request.user):
        material_request = get_object_or_404(MaterialAssistanceRequest, id=request_id)
    else:
        material_request = get_object_or_404(MaterialAssistanceRequest, id=request_id, worker__user=request.user)
    material_request.delete()
    return JsonResponse({'success': True})


@login_required
def delete_funeral_request(request, request_id):
    """Удаление заявления на погребение."""
    if request.method not in ('POST', 'DELETE'):
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    if is_admin(request.user):
        funeral_request = get_object_or_404(FuneralRequest, id=request_id)
    else:
        funeral_request = get_object_or_404(FuneralRequest, id=request_id, worker__user=request.user)
    funeral_request.delete()
    return JsonResponse({'success': True})
