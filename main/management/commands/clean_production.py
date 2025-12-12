from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
import os
import shutil
from pathlib import Path
from django.conf import settings
from main.models import (
    Worker, FamilyMember, VacationRequest, MaterialAssistanceRequest,
    CoalRequest, FuneralRequest, Statement, VacationLimit
)
from django.db import transaction


class Command(BaseCommand):
    help = 'Очищает все тестовые данные: работников, отчеты, ведомости, списки и все прикрепленные файлы. Подготавливает проект к продакшену.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Подтвердить удаление всех данных (без этого флага команда только покажет что будет удалено)',
        )

    def handle(self, *args, **options):
        confirm = options['confirm']
        
        if not confirm:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  ВНИМАНИЕ: Эта команда удалит ВСЕ данные!\n'
                'Будут удалены:\n'
                '  - Все работники и члены их семей\n'
                '  - Все заявления (путевки, материальная помощь, уголь, погребение)\n'
                '  - Все ведомости\n'
                '  - Все лимиты\n'
                '  - Все прикрепленные файлы\n\n'
                'Если вы уверены, запустите команду с флагом --confirm:\n'
                '  python manage.py clean_production --confirm\n'
            ))
            return
        
        self.stdout.write(self.style.WARNING('\n🗑️  Начинаю очистку всех данных...\n'))
        
        try:
            with transaction.atomic():
                # 1. Удаляем все заявления (они связаны с работниками через CASCADE)
                self.stdout.write('Удаление заявлений...')
                
                vacation_count = VacationRequest.objects.count()
                VacationRequest.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Удалено заявлений на путевки: {vacation_count}'))
                
                material_count = MaterialAssistanceRequest.objects.count()
                MaterialAssistanceRequest.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Удалено заявлений на материальную помощь: {material_count}'))
                
                coal_count = CoalRequest.objects.count()
                CoalRequest.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Удалено заявлений на уголь: {coal_count}'))
                
                funeral_count = FuneralRequest.objects.count()
                FuneralRequest.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Удалено заявлений на погребение: {funeral_count}'))
                
                # 2. Удаляем все ведомости
                statement_count = Statement.objects.count()
                Statement.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Удалено ведомостей: {statement_count}'))
                
                # 3. Удаляем все лимиты
                limit_count = VacationLimit.objects.count()
                VacationLimit.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Удалено лимитов: {limit_count}'))
                
                # 4. Удаляем всех работников (это автоматически удалит и членов семьи через CASCADE)
                worker_count = Worker.objects.count()
                family_count = FamilyMember.objects.count()
                Worker.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Удалено работников: {worker_count}'))
                self.stdout.write(self.style.SUCCESS(f'  ✓ Удалено членов семьи: {family_count}'))
                
                self.stdout.write(self.style.SUCCESS('\n✓ Все записи из базы данных успешно удалены!\n'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Ошибка при удалении данных: {str(e)}'))
            return
        
        # 5. Удаляем все файлы из media/
        self.stdout.write('Удаление прикрепленных файлов...')
        media_root = Path(settings.MEDIA_ROOT)
        
        if media_root.exists():
            try:
                # Список всех директорий с файлами
                directories_to_clean = [
                    'benefits',
                    'miner_glory',
                    'coal',
                    'funeral',
                ]
                
                deleted_files = 0
                deleted_dirs = 0
                
                for dir_name in directories_to_clean:
                    dir_path = media_root / dir_name
                    if dir_path.exists():
                        # Подсчитываем файлы
                        file_count = sum(1 for _ in dir_path.rglob('*') if _.is_file())
                        deleted_files += file_count
                        
                        # Удаляем директорию со всем содержимым
                        shutil.rmtree(dir_path)
                        deleted_dirs += 1
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Удалена директория {dir_name}/ ({file_count} файлов)'))
                
                # Удаляем все остальные файлы в корне media (если есть)
                for item in media_root.iterdir():
                    if item.is_file():
                        item.unlink()
                        deleted_files += 1
                    elif item.is_dir() and item.name not in directories_to_clean:
                        shutil.rmtree(item)
                        deleted_dirs += 1
                
                self.stdout.write(self.style.SUCCESS(f'\n✓ Удалено файлов: {deleted_files}'))
                self.stdout.write(self.style.SUCCESS(f'✓ Удалено директорий: {deleted_dirs}'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'\n❌ Ошибка при удалении файлов: {str(e)}'))
                self.stdout.write(self.style.WARNING('  Возможно, некоторые файлы уже были удалены.'))
        
        # 6. Создаем необходимые директории заново
        self.stdout.write('\nСоздание необходимых директорий...')
        try:
            for dir_name in directories_to_clean:
                dir_path = media_root / dir_name
                dir_path.mkdir(parents=True, exist_ok=True)
                # Создаем .gitkeep чтобы директории сохранились в git
                (dir_path / '.gitkeep').touch(exist_ok=True)
            
            self.stdout.write(self.style.SUCCESS('✓ Все необходимые директории созданы'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  Предупреждение при создании директорий: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('✅ Проект успешно подготовлен к продакшену!'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
        
        self.stdout.write(self.style.WARNING('\n⚠️  Рекомендации для продакшена:\n'))
        self.stdout.write('  1. Установите DEBUG = False в settings.py')
        self.stdout.write('  2. Настройте ALLOWED_HOSTS в settings.py')
        self.stdout.write('  3. Сгенерируйте новый SECRET_KEY')
        self.stdout.write('  4. Настройте безопасные настройки (SSL, CSRF_COOKIE_SECURE и т.д.)')
        self.stdout.write('  5. Создайте пользователей командой: python manage.py create_users')
        self.stdout.write('  6. Соберите статические файлы: python manage.py collectstatic\n')

