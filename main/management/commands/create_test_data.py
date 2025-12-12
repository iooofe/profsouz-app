from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from main.models import Worker, FamilyMember, VacationRequest, Statement
import random


class Command(BaseCommand):
    help = 'Создает тестовые данные: работников, ведомости и отчеты'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Имя пользователя для создания тестовых данных',
            default='АДМИН'
        )

    def handle(self, *args, **options):
        username = options['user']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Пользователь {username} не найден!'))
            return
        
        self.stdout.write(f'Создание тестовых данных для пользователя {username}...')
        
        # Список тестовых работников
        test_workers_data = [
            {
                'full_name': 'Иванов Иван Иванович',
                'personnel_number': '1001',
                'inn': '123456789012',
                'status': 'worker',
                'is_union_member': True,
                'department': 'Цех №1',
                'position': 'Слесарь',
                'is_contract_member': True,
                'phone': '+7 (777) 111-22-33',
                'address': 'г. Караганда, ул. Ленина, д. 1, кв. 1',
                'id_number': '123456789',
                'id_issue_date': date(2010, 1, 15),
                'id_issued_by': 'МВД РК',
                'family_members': [
                    {'full_name': 'Иванова Мария Ивановна', 'relationship': 'spouse', 'id_number': '987654321', 'id_issue_date': date(2010, 2, 20), 'id_issued_by': 'МВД РК'},
                    {'full_name': 'Иванов Петр Иванович', 'relationship': 'child', 'id_number': '111222333', 'id_issue_date': date(2015, 5, 10), 'id_issued_by': 'МВД РК'},
                ]
            },
            {
                'full_name': 'Петров Петр Петрович',
                'personnel_number': '1002',
                'inn': '234567890123',
                'status': 'worker',
                'is_union_member': True,
                'department': 'Цех №2',
                'position': 'Токарь',
                'is_contract_member': True,
                'phone': '+7 (777) 222-33-44',
                'address': 'г. Караганда, ул. Казахстанская, д. 5, кв. 10',
                'id_number': '234567890',
                'id_issue_date': date(2008, 3, 20),
                'id_issued_by': 'МВД РК',
                'family_members': [
                    {'full_name': 'Петрова Анна Петровна', 'relationship': 'spouse', 'id_number': '888777666', 'id_issue_date': date(2009, 4, 15), 'id_issued_by': 'МВД РК'},
                ]
            },
            {
                'full_name': 'Сидоров Сидор Сидорович',
                'personnel_number': '1003',
                'inn': '345678901234',
                'status': 'pensioner',
                'is_union_member': True,
                'department': 'Цех №1',
                'position': 'Мастер',
                'is_contract_member': True,
                'phone': '+7 (777) 333-44-55',
                'address': 'г. Караганда, ул. Абайская, д. 10, кв. 5',
                'id_number': '345678901',
                'id_issue_date': date(2005, 6, 10),
                'id_issued_by': 'МВД РК',
                'family_members': []
            },
            {
                'full_name': 'Кузнецова Елена Владимировна',
                'personnel_number': '1004',
                'inn': '456789012345',
                'status': 'worker',
                'is_union_member': False,
                'department': 'Цех №3',
                'position': 'Бухгалтер',
                'is_contract_member': True,
                'phone': '+7 (777) 444-55-66',
                'address': 'г. Караганда, ул. Саранская, д. 15, кв. 20',
                'id_number': '456789012',
                'id_issue_date': date(2012, 7, 25),
                'id_issued_by': 'МВД РК',
                'family_members': [
                    {'full_name': 'Кузнецов Дмитрий Сергеевич', 'relationship': 'spouse', 'id_number': '777888999', 'id_issue_date': date(2011, 8, 30), 'id_issued_by': 'МВД РК'},
                    {'full_name': 'Кузнецова София Дмитриевна', 'relationship': 'child', 'id_number': '222333444', 'id_issue_date': date(2018, 9, 5), 'id_issued_by': 'МВД РК'},
                    {'full_name': 'Кузнецов Артем Дмитриевич', 'relationship': 'child', 'id_number': '333444555', 'id_issue_date': date(2020, 10, 12), 'id_issued_by': 'МВД РК'},
                ]
            },
            {
                'full_name': 'Смирнов Алексей Николаевич',
                'personnel_number': '1005',
                'inn': '567890123456',
                'status': 'worker',
                'is_union_member': True,
                'department': 'Цех №2',
                'position': 'Инженер',
                'is_contract_member': False,
                'phone': '+7 (777) 555-66-77',
                'address': 'г. Караганда, ул. Кузембаева, д. 20, кв. 15',
                'id_number': '567890123',
                'id_issue_date': date(2009, 11, 18),
                'id_issued_by': 'МВД РК',
                'family_members': []
            },
        ]
        
        # Создаем работников
        created_workers = []
        for worker_data in test_workers_data:
            family_members_data = worker_data.pop('family_members', [])
            
            worker, created = Worker.objects.get_or_create(
                user=user,
                personnel_number=worker_data['personnel_number'],
                defaults=worker_data
            )
            
            if created:
                created_workers.append(worker)
                
                # Создаем членов семьи
                for fm_data in family_members_data:
                    FamilyMember.objects.get_or_create(
                        worker=worker,
                        id_number=fm_data['id_number'],
                        defaults=fm_data
                    )
                
                self.stdout.write(self.style.SUCCESS(f'Создан работник: {worker.full_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Работник уже существует: {worker.full_name}'))
                created_workers.append(worker)
        
        # Создаем тестовые ведомости за прошлые месяцы
        today = timezone.now().date()
        
        # Создаем ведомости за последние 3 месяца
        for month_offset in range(1, 4):
            # Вычисляем период (20 число месяца по 19 число следующего)
            if today.month - month_offset <= 0:
                period_start = date(today.year - 1, 12 + today.month - month_offset, 20)
            else:
                period_start = date(today.year, today.month - month_offset, 20)
            
            # Вычисляем конец периода (19 число следующего месяца)
            if period_start.month == 12:
                period_end = date(period_start.year + 1, 1, 19)
            else:
                period_end = date(period_start.year, period_start.month + 1, 19)
            
            # Ведомость Жартас
            zhartas_statement, created = Statement.objects.get_or_create(
                user=user,
                period_start=period_start,
                resort='zhartas',
                defaults={
                    'period_end': period_end,
                    'status': 'closed' if period_end < today else 'active',
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Создана ведомость Жартас: {period_start} - {period_end}'))
            else:
                # Обновляем статус, если период истек
                if period_end < today and zhartas_statement.status != 'closed':
                    zhartas_statement.status = 'closed'
                    zhartas_statement.save()
            
            # Ведомость Шахтер
            shakhter_statement, created = Statement.objects.get_or_create(
                user=user,
                period_start=period_start,
                resort='shakhter',
                defaults={
                    'period_end': period_end,
                    'status': 'closed' if period_end < today else 'active',
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Создана ведомость Шахтер: {period_start} - {period_end}'))
            else:
                # Обновляем статус, если период истек
                if period_end < today and shakhter_statement.status != 'closed':
                    shakhter_statement.status = 'closed'
                    shakhter_statement.save()
        
        # Создаем тестовые заявления на путевки
        resorts = ['zhartas', 'shakhter']
        
        # Создаем заявления за последние 3 месяца
        for month_offset in range(3):
            # Вычисляем период (20 число месяца по 19 число следующего)
            if today.month - month_offset <= 0:
                period_start = date(today.year - 1, 12 + today.month - month_offset, 20)
            else:
                period_start = date(today.year, today.month - month_offset, 20)
            
            # Вычисляем конец периода (19 число следующего месяца)
            if period_start.month == 12:
                period_end = date(period_start.year + 1, 1, 19)
            else:
                period_end = date(period_start.year, period_start.month + 1, 19)
            
            # Создаем несколько заявлений в каждом периоде (по 2-3 на каждого работника)
            for worker in created_workers[:3]:  # Берем первых 3 работников
                for _ in range(random.randint(1, 2)):  # 1-2 заявления на работника
                    resort = random.choice(resorts)
                    
                    # Генерируем случайные даты в пределах периода
                    days_in_period = (period_end - period_start).days
                    start_offset = random.randint(0, max(0, days_in_period - 10))
                    start_date = period_start + timedelta(days=start_offset)
                    end_date = start_date + timedelta(days=random.randint(3, 7))
                    
                    # Проверяем, что даты в пределах периода
                    if end_date > period_end:
                        end_date = period_end
                        start_date = end_date - timedelta(days=random.randint(3, 7))
                        if start_date < period_start:
                            start_date = period_start
                    
                    # Создаем заявление
                    vacation = VacationRequest.objects.create(
                        user=user,
                        worker=worker,
                        resort=resort,
                        start_date=start_date,
                        end_date=end_date,
                        is_rejected=random.choice([True, False]) if month_offset > 0 else False,  # Старые могут быть отменены
                    )
                    
                    # Добавляем случайных членов семьи
                    family_members = worker.family_members.all()
                    if family_members.exists() and random.choice([True, False]):
                        selected_family = random.sample(list(family_members), min(2, len(family_members)))
                        vacation.family_members.set(selected_family)
                    
                    # Рассчитываем и сохраняем цену
                    calculated_price = vacation.calculate_price()
                    if calculated_price:
                        vacation.price = calculated_price
                        vacation.save()
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'Создано заявление: {worker.full_name} - {resort} ({start_date} - {end_date})'
                    ))
        
        self.stdout.write(self.style.SUCCESS('\nТестовые данные успешно созданы!'))

