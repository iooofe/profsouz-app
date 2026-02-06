from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from django.db.models import Q
from datetime import date


def validate_phone_kz(value):
    """Валидация казахстанского номера телефона"""
    if not value:
        return
    # Убираем все нецифровые символы кроме +
    cleaned = ''.join(c for c in value if c.isdigit() or c == '+')
    # Проверяем форматы: +7XXXXXXXXXX, 8XXXXXXXXXX, 7XXXXXXXXXX
    if cleaned.startswith('+7') and len(cleaned) == 12:
        return
    elif cleaned.startswith('8') and len(cleaned) == 11:
        return
    elif cleaned.startswith('7') and len(cleaned) == 11:
        return
    else:
        from django.core.exceptions import ValidationError
        raise ValidationError('Номер телефона должен быть в формате: +7XXXXXXXXXX, 8XXXXXXXXXX или 7XXXXXXXXXX')


def validate_inn_kz(value):
    """Валидация ИНН Казахстана (12 цифр)"""
    if not value:
        return
    # Убираем все нецифровые символы
    cleaned = ''.join(c for c in value if c.isdigit())
    if len(cleaned) != 12:
        from django.core.exceptions import ValidationError
        raise ValidationError('ИНН должен содержать 12 цифр')


class Worker(models.Model):
    STATUS_CHOICES = [
        ('worker', 'Работник'),
        ('pensioner', 'Пенсионер'),
    ]
    
    YES_NO_CHOICES = [
        (True, 'Да'),
        (False, 'Нет'),
    ]
    
    # Связь с пользователем
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workers', verbose_name='Пользователь', null=True, blank=True)
    
    # Основная информация
    full_name = models.CharField('ФИО', max_length=200)
    personnel_number = models.CharField('Табельный номер', max_length=50, null=True, blank=True)
    inn = models.CharField('ИНН', max_length=12, blank=True, validators=[validate_inn_kz])
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='worker')
    is_union_member = models.BooleanField('Член профсоюза', choices=YES_NO_CHOICES, default=False)
    department = models.CharField('Участок', max_length=200)
    position = models.CharField('Должность', max_length=200)
    is_contract_member = models.BooleanField('Присоединен к кол. договору', choices=YES_NO_CHOICES, default=False)
    
    # Контактная информация
    phone = models.CharField(
        'Телефон',
        max_length=20,
        validators=[validate_phone_kz],
        blank=True
    )
    address = models.TextField('Адрес', blank=True)
    
    # Удостоверение личности
    id_number = models.CharField('Удостоверение личности', max_length=50)
    id_issue_date = models.DateField('Дата выдачи удо', null=True, blank=True)
    id_issued_by = models.CharField('Кем выдано удо', max_length=200, blank=True)
    
    # Поля для пенсионеров
    has_benefits = models.BooleanField('Льготы', choices=YES_NO_CHOICES, default=False, null=True, blank=True)
    benefits_file = models.FileField('Файл подтверждающий льготы', upload_to='benefits/', null=True, blank=True)
    benefits_name = models.CharField('Название льготы', max_length=200, blank=True)
    has_miner_glory = models.BooleanField('Шахтерская слава или трудовая слава', choices=YES_NO_CHOICES, default=False, null=True, blank=True)
    miner_glory_file = models.FileField('Файл подтверждающий шахтерскую/трудовую славу', upload_to='miner_glory/', null=True, blank=True)
    # Поля для заявления на уголь / счетов
    house_passport_file = models.FileField('Копия технического паспорта дома', upload_to='coal/passports/', null=True, blank=True)
    pensioner_id_file = models.FileField('Копия удостоверения пенсионера', upload_to='coal/pensioner_ids/', null=True, blank=True)
    account_20_digit = models.CharField('Карточный счет (KZ + 18 цифр)', max_length=25, blank=True)  # KZ + 18 цифр = 20 символов
    current_account = models.CharField('Текущий счет (KZ + 18 цифр)', max_length=25, blank=True)
    # Поля для заявления на погребение
    is_dead = models.BooleanField('Пенсионер мертв?', choices=YES_NO_CHOICES, default=False, null=True, blank=True)
    death_certificate_file = models.FileField('Справка о смерти', upload_to='funeral/death_certificates/', null=True, blank=True)
    # Поля для списка на доплату за 3 степени (хранятся по периодам)
    bonus_accrued = models.DecimalField('Начислено (доплата 3 степени)', max_digits=10, decimal_places=2, null=True, blank=True)
    bonus_ipn = models.DecimalField('ИПН (доплата 3 степени)', max_digits=10, decimal_places=2, null=True, blank=True)
    bonus_to_pay = models.DecimalField('К выплате (доплата 3 степени)', max_digits=10, decimal_places=2, null=True, blank=True)
    bonus_period_start = models.DateField('Период начала (доплата 3 степени)', null=True, blank=True)
    
    # Метаданные
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Работник'
        verbose_name_plural = 'Работники'
        ordering = ['full_name']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'personnel_number'],
                condition=Q(personnel_number__isnull=False) & ~Q(personnel_number=''),
                name='uniq_worker_user_personnel_number_not_blank',
            )
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.personnel_number or '—'})"


class FamilyMember(models.Model):
    RELATIONSHIP_CHOICES = [
        ('spouse', 'Супруг(а)'),
        ('child', 'Ребенок'),
        ('parent', 'Родитель'),
        ('sibling', 'Брат/Сестра'),
        ('grandchild', 'Внук/Внучка'),
        ('other', 'Другое'),
    ]
    
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='family_members', verbose_name='Работник')
    full_name = models.CharField('ФИО', max_length=200)
    relationship = models.CharField('Степень родства', max_length=20, choices=RELATIONSHIP_CHOICES)
    id_number = models.CharField('Удостоверение личности', max_length=50, blank=True)
    id_issue_date = models.DateField('Дата выдачи удо', null=True, blank=True)
    id_issued_by = models.CharField('Кем выдано удо', max_length=200, blank=True)
    birth_date = models.DateField('Дата рождения', null=True, blank=True, help_text='Обязательно для детей и внуков/внучек')
    
    def get_age(self):
        """Возвращает возраст члена семьи"""
        if not self.birth_date:
            return None
        from datetime import date
        today = date.today()
        age = today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return age
    
    def is_child_or_grandchild(self):
        """Проверяет, является ли член семьи ребенком или внуком/внучкой"""
        return self.relationship in ['child', 'grandchild']
    
    class Meta:
        verbose_name = 'Член семьи'
        verbose_name_plural = 'Члены семьи'
        ordering = ['full_name']
    
    def __str__(self):
        return f"{self.full_name} ({self.get_relationship_display()})"


REQUEST_STATUS_CHOICES = [
    ('active', 'Активно'),
    ('inactive', 'Неактивно/Отклонено'),
]


class VacationRequest(models.Model):
    """Заявление на путевку"""
    RESORT_CHOICES = [
        ('orlenok', 'ДОЦ "Орленок"'),
        ('zhartas', 'Санаторий "Жартас"'),
        ('balkhash', 'Санаторий "Балхаш"'),
        ('discovery', '"Дискавери"'),
        ('shakhter', 'Дом отдыха "Шахтер"'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vacation_requests', verbose_name='Пользователь')
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='vacation_requests', verbose_name='Работник')
    family_members = models.ManyToManyField(FamilyMember, blank=True, verbose_name='Члены семьи')
    resort = models.CharField('Курорт', max_length=50, choices=RESORT_CHOICES)
    start_date = models.DateField('Дата начала поездки')
    end_date = models.DateField('Дата окончания поездки')
    price = models.DecimalField('Цена путевки', max_digits=10, decimal_places=2, null=True, blank=True)
    is_rejected = models.BooleanField('Отказ от поездки', default=False)
    request_status = models.CharField('Статус заявления', max_length=20, choices=REQUEST_STATUS_CHOICES, default='active')
    worker_goes = models.BooleanField('Работник едет', default=True)
    seasons = models.JSONField('Сезоны (для ДОЦ "Орленок")', default=list, blank=True, help_text='Список сезонов: 1, 2, 3, 4')
    study_certificate_file = models.FileField('Справка об очном обучении', upload_to='vacation/study_certificates/', null=True, blank=True, help_text='Обязательно для детей/внуков старше 18 лет')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Заявление на путевку'
        verbose_name_plural = 'Заявления на путевки'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Путевка {self.worker.full_name} - {self.get_resort_display()}"
    
    def get_duration_days(self):
        """Возвращает количество дней поездки"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0
    
    def get_status(self):
        """Возвращает статус путевки в зависимости от даты"""
        if self.request_status == 'inactive':
            return 'inactive'

        if self.is_rejected:
            return 'cancelled'
        
        # Если пенсионер умер, все его заявления неактивны
        if self.worker.status == 'pensioner' and self.worker.is_dead:
            return 'cancelled'
        
        from django.utils import timezone
        today = timezone.now().date()
        
        if today < self.start_date:
            return 'pending'  # В ожидании
        elif today >= self.start_date and today <= self.end_date:
            return 'active'  # Идет
        else:
            return 'completed'  # Окончена
    
    def get_status_display_text(self):
        """Возвращает текстовое представление статуса"""
        status = self.get_status()
        status_map = {
            'cancelled': 'Отменена',
            'inactive': 'Неактивно/Отклонено',
            'pending': 'В ожидании',
            'active': 'Идет',
            'completed': 'Окончена',
        }
        return status_map.get(status, 'Неизвестно')
    
    def get_places_count(self):
        """Возвращает количество мест, занимаемых этой путевкой"""
        if self.is_rejected:
            return 0
        # Если пенсионер умер, все его заявления неактивны и не занимают места
        if self.worker.status == 'pensioner' and self.worker.is_dead:
            return 0
        # 1 место за работника (если едет) + 1 место за каждого члена семьи
        worker_places = 1 if getattr(self, 'worker_goes', True) else 0
        return worker_places + self.family_members.count()
    
    @staticmethod
    def get_price_per_day(resort):
        """Возвращает цену за день для курорта"""
        prices = {
            'zhartas': 2066,  # Санаторий "Жартас"
            'shakhter': 1857,  # Дом отдыха "Шахтер"
            'orlenok': 0,  # Цена не указана
            'balkhash': 0,  # Цена не указана
            'discovery': 0,  # Цена не указана
        }
        return prices.get(resort, 0)
    
    def calculate_price(self):
        """Рассчитывает цену путевки"""
        price_per_day = self.get_price_per_day(self.resort)
        if price_per_day == 0:
            return None
        
        days = self.get_duration_days()
        people_count = self.get_places_count()
        
        return price_per_day * days * people_count
    
    def get_seasons_display(self):
        """Возвращает форматированную строку сезонов для ДОЦ 'Орленок'"""
        if self.resort != 'orlenok':
            return None
        
        if not self.seasons or len(self.seasons) == 0:
            return None
        
        # Сортируем сезоны
        sorted_seasons = sorted([int(s) for s in self.seasons if str(s).isdigit()])
        
        if len(sorted_seasons) == 0:
            return None
        
        # Форматируем: "1 сезон" или "1, 2, 3 сезоны"
        seasons_str = ', '.join(str(s) for s in sorted_seasons)
        if len(sorted_seasons) == 1:
            return f"{seasons_str} сезон"
        else:
            return f"{seasons_str} сезоны"


class MaterialAssistanceRequest(models.Model):
    """Заявление на материальную помощь"""
    ASSISTANCE_TYPE_CHOICES = [
        ('sick_leave', 'Больничный лист'),
        ('childbirth', 'Рождение ребенка'),
        ('funeral', 'Погребение близких родственников'),
        ('treatment', 'На лечение'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='material_assistance_requests', verbose_name='Пользователь')
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='material_assistance_requests', verbose_name='Работник')
    assistance_type = models.CharField('Вид помощи', max_length=50, choices=ASSISTANCE_TYPE_CHOICES)
    amount = models.DecimalField('Сумма', max_digits=10, decimal_places=2)
    request_status = models.CharField('Статус заявления', max_length=20, choices=REQUEST_STATUS_CHOICES, default='active')
    is_issued = models.BooleanField('Выдано', default=False)
    accrued = models.DecimalField('Начислено', max_digits=10, decimal_places=2, null=True, blank=True)
    ipn = models.DecimalField('ИПН', max_digits=10, decimal_places=2, null=True, blank=True)
    to_pay = models.DecimalField('К выплате', max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Заявление на материальную помощь'
        verbose_name_plural = 'Заявления на материальную помощь'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Материальная помощь {self.worker.full_name} - {self.get_assistance_type_display()}"
    
    def get_status(self):
        """Возвращает статус заявления"""
        if self.request_status == 'inactive':
            return 'inactive'
        # Если пенсионер умер, все его заявления неактивны
        if self.worker.status == 'pensioner' and self.worker.is_dead:
            return 'cancelled'
        return 'active'
    
    def get_status_display_text(self):
        """Возвращает текстовое представление статуса"""
        status = self.get_status()
        status_map = {
            'cancelled': 'Отменено',
            'inactive': 'Неактивно/Отклонено',
            'active': 'Активно',
        }
        return status_map.get(status, 'Неизвестно')


class CoalRequest(models.Model):
    """Заявление на денежную компенсацию за льготный уголь"""
    ACCOUNT_TYPE_CHOICES = [
        ('20_digit', 'Карточный счет'),
        ('current', 'Текущий счет'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coal_requests', verbose_name='Пользователь')
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='coal_requests', verbose_name='Работник')
    account_type = models.CharField('Тип счета', max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    account_number = models.CharField('Номер счета', max_length=25, blank=True)  # KZ + 20 цифр = 22 символа (для совместимости, но данные хранятся в Worker)
    request_status = models.CharField('Статус заявления', max_length=20, choices=REQUEST_STATUS_CHOICES, default='active')
    is_issued = models.BooleanField('Выдано', default=False)
    accrued = models.DecimalField('Начислено', max_digits=10, decimal_places=2, null=True, blank=True)
    ipn = models.DecimalField('ИПН', max_digits=10, decimal_places=2, null=True, blank=True)
    to_pay = models.DecimalField('К выплате', max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Заявление на уголь'
        verbose_name_plural = 'Заявления на уголь'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Заявление на уголь {self.worker.full_name} - {self.created_at.strftime('%d.%m.%Y')}"
    
    def get_status(self):
        """Возвращает статус заявления"""
        if self.request_status == 'inactive':
            return 'inactive'
        # Если пенсионер умер, все его заявления неактивны
        if self.worker.status == 'pensioner' and self.worker.is_dead:
            return 'cancelled'
        return 'active'
    
    def get_status_display_text(self):
        """Возвращает текстовое представление статуса"""
        status = self.get_status()
        status_map = {
            'cancelled': 'Отменено',
            'inactive': 'Неактивно/Отклонено',
            'active': 'Активно',
        }
        return status_map.get(status, 'Неизвестно')


class FuneralRequest(models.Model):
    """Заявление на погребение пенсионеров"""
    ACCOUNT_TYPE_CHOICES = [
        ('20_digit', 'Карточный счет'),
        ('current', 'Текущий счет'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='funeral_requests', verbose_name='Пользователь')
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='funeral_requests', verbose_name='Пенсионер')
    applicant_full_name = models.CharField('ФИО заявителя', max_length=200)
    applicant_inn = models.CharField('ИИН заявителя', max_length=12, validators=[validate_inn_kz])
    applicant_id_file = models.FileField('Удостоверение заявителя', upload_to='funeral/applicant_ids/', null=True, blank=True)
    account_type = models.CharField('Тип счета', max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    account_number = models.CharField('Номер счета', max_length=25, blank=True)  # KZ + 20 цифр = 22 символа
    to_pay = models.DecimalField('К выплате', max_digits=10, decimal_places=2, null=True, blank=True)
    request_status = models.CharField('Статус заявления', max_length=20, choices=REQUEST_STATUS_CHOICES, default='active')
    
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Заявление на погребение'
        verbose_name_plural = 'Заявления на погребение'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Заявление на погребение {self.worker.full_name} - {self.created_at.strftime('%d.%m.%Y')}"
    
    def get_status(self):
        """Возвращает статус заявления"""
        if self.request_status == 'inactive':
            return 'inactive'
        # Если пенсионер умер, все его заявления неактивны
        if self.worker.status == 'pensioner' and self.worker.is_dead:
            return 'cancelled'
        return 'active'
    
    def get_status_display_text(self):
        """Возвращает текстовое представление статуса"""
        status = self.get_status()
        status_map = {
            'cancelled': 'Отменено',
            'inactive': 'Неактивно/Отклонено',
            'active': 'Активно',
        }
        return status_map.get(status, 'Неизвестно')


class VacationLimit(models.Model):
    """Лимит на путевки для пользователя"""
    RESORT_CHOICES = [
        ('zhartas', 'Санаторий "Жартас"'),
        ('shakhter', 'Дом отдыха "Шахтер"'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vacation_limits', verbose_name='Пользователь')
    resort = models.CharField('Курорт', max_length=50, choices=RESORT_CHOICES, default='zhartas')
    limit = models.PositiveIntegerField('Лимит', default=0)
    period_start = models.DateField('Начало периода (18 число месяца)')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    is_initial = models.BooleanField('Первоначальная установка', default=True)
    
    class Meta:
        verbose_name = 'Лимит на путевки'
        verbose_name_plural = 'Лимиты на путевки'
        unique_together = [['user', 'period_start', 'resort']]
        ordering = ['-period_start']
    
    def __str__(self):
        return f"Лимит {self.user.username} - {self.get_resort_display()} - {self.period_start}: {self.limit}"
    
    @staticmethod
    def get_current_period_start():
        """Возвращает дату начала текущего периода (18 число текущего месяца)"""
        from django.utils import timezone
        from datetime import date
        
        today = timezone.now().date()
        # Если сегодня до 18 числа, период начался 18 числа прошлого месяца
        if today.day < 18:
            if today.month == 1:
                period_start = date(today.year - 1, 12, 18)
            else:
                period_start = date(today.year, today.month - 1, 18)
        else:
            # Если сегодня 18 или позже, период начался 18 числа текущего месяца
            period_start = date(today.year, today.month, 18)
        
        return period_start
    
    @staticmethod
    def get_or_create_limit(user, resort='zhartas'):
        """Получает или создает лимит для текущего периода и указанного курорта"""
        period_start = VacationLimit.get_current_period_start()
        limit, created = VacationLimit.objects.get_or_create(
            user=user,
            period_start=period_start,
            resort=resort,
            defaults={'limit': 0, 'is_initial': True}
        )
        return limit, created
    
    def get_used_places(self):
        """Возвращает количество использованных мест в текущем периоде для данного курорта"""
        period_start = self.period_start
        # Период заканчивается 17 числа следующего месяца
        if period_start.month == 12:
            period_end = date(period_start.year + 1, 1, 17)
        else:
            period_end = date(period_start.year, period_start.month + 1, 17)
        
        # Получаем все неотмененные заявления в этом периоде для данного курорта
        requests = VacationRequest.objects.filter(
            user=self.user,
            resort=self.resort,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end,
            is_rejected=False
        )
        
        total_places = 0
        for request in requests:
            total_places += request.get_places_count()
        
        return total_places
    
    def get_remaining_places(self):
        """Возвращает количество оставшихся мест"""
        used = self.get_used_places()
        return max(0, self.limit - used)
    
    def can_increase(self):
        """Проверяет, можно ли увеличить лимит (только если он уже был установлен)"""
        return not self.is_initial or self.limit > 0


class Statement(models.Model):
    """Ведомость путевок"""
    STATUS_CHOICES = [
        ('active', 'Ведется'),
        ('closed', 'Закрыта'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='statements', verbose_name='Пользователь')
    period_start = models.DateField('Начало периода (20 число месяца)')
    period_end = models.DateField('Конец периода (19 число следующего месяца)')
    resort = models.CharField('Курорт', max_length=50, default='zhartas')
    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Ведомость'
        verbose_name_plural = 'Ведомости'
        unique_together = [['user', 'period_start', 'resort']]
        ordering = ['-period_start']
    
    def __str__(self):
        return f"Ведомость {self.user.username} - {self.period_start} ({self.get_status_display()})"
    
    @staticmethod
    def get_or_create_statement(user, period_start, period_end, resort='zhartas'):
        """Получает или создает ведомость для периода"""
        statement, created = Statement.objects.get_or_create(
            user=user,
            period_start=period_start,
            resort=resort,
            defaults={
                'period_end': period_end,
                'status': 'active',
            }
        )
        return statement, created
    
    @staticmethod
    def close_expired_statements():
        """Закрывает истекшие ведомости"""
        from django.utils import timezone
        today = timezone.now().date()
        Statement.objects.filter(
            period_end__lt=today,
            status='active'
        ).update(status='closed')
