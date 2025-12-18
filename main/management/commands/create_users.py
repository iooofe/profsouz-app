from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Создает предустановленных пользователей для системы'

    def handle(self, *args, **options):
        # Усложненные пароли без спецсимволов (латиница с заглавными буквами и цифры)
        users_data = [
            ('КПТУ', 'change-me'),
            ('УТТ', 'change-me'),
            ('Ш. Ленина', 'change-me'),
            ('Ш. Казахстанская', 'change-me'),
            ('ш. Костенко', 'change-me'),
            ('ш. Тентекская', 'change-me'),
            ('ш. Шахтинская', 'change-me'),
            ('ш. Абайская', 'change-me'),
            ('ш. Саранская', 'change-me'),
            ('ш. Кузембаева', 'change-me'),
            ('Энергоуголь', 'change-me'),
            ('ТОО Куpылыш мет', 'change-me'),
            ('УСШМД', 'change-me'),
            ('Цоф Восточная', 'change-me'),
            ('ГУ', 'change-me'),
            ('АДМИН', 'change-me'),
        ]

        created_count = 0
        updated_count = 0

        for username, password in users_data:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                user.save()
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Создан пользователь: {username}')
                )
            else:
                user.set_password(password)
                user.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Обновлен пароль для: {username}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nГотово! Создано: {created_count}, Обновлено: {updated_count}'
            )
        )

