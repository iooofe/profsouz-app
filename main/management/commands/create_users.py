from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from pathlib import Path
from datetime import datetime
from main.models import Worker
import openpyxl
import os
import secrets
import string


class Command(BaseCommand):
    help = (
        "Создает пользователей из Excel файлов в папке 'работники'.\n"
        "Название файла (без расширения) = имя аккаунта.\n"
        "В каждом аккаунте создаются все работники из соответствующего файла."
    )

    # Возможные варианты названий столбцов -> поле Worker
    HEADER_MAP = {
        "full_name": ["фио", "ф.и.о", "ф. и. о.", "ф.и.о."],
        "last_name": ["фамилия", "фамил", "фам"],
        "first_name": ["имя", "имен"],
        "middle_name": ["отчество", "отчеств", "отч"],
        "personnel_number": [
            "табельный",
            "таб. номер",
            "таб.№",
            "таб №",
            "таб. №",
            "таб№",
            "таб.",
            "табельный номер",
            "табельный №",
            "табельный№",
            "таб",
            "№ таб",
        ],
        "inn": ["иин", "инн"],
        "department": ["участок", "подразделение", "цех"],
        "position": ["должность", "профессия", "штатная должность"],
        "status": ["категория", "статус"],
        "union_date": [
            "дата присоединения",
            "дата присоеденения",
            "дата вступления",
            "дата вступа",
        ],
        "address": ["адрес"],
        "phone": ["телефон", "моб. телефон", "тел./моб."],
    }

    # Соответствие имени файла пользователю в системе
    FILE_USER_MAP = {
        "УМТС и 1": "УМТС",
        "УМТС": "УМТС",
        "УСШМД": "УСШМД",
        "УТТ": "УТТ",
        "ЦОФ Восточная": "Цоф Восточная",
        "ЦОФ ВОСТОЧНАЯ": "Цоф Восточная",
        "ш.Абайская": "ш. Абайская",
        "ш.АБАЙСКАЯ": "ш. Абайская",
        "ш.Казахстанская": "Ш. Казахстанская",
        "ш.КАЗАХСТАНСКАЯ": "Ш. Казахстанская",
        "ш.Костенко": "ш. Костенко",
        "ш.КОСТЕНКО": "ш. Костенко",
        "ш.Кузембаева": "ш. Кузембаева",
        "ш.КУЗЕМБАЕВА": "ш. Кузембаева",
        "ш.Ленина": "Ш. Ленина",
        "ш.ЛЕНИНА": "Ш. Ленина",
        "ш.Саранская": "ш. Саранская",
        "ш.САРАНСКАЯ": "ш. Саранская",
        "ш.Тентекская": "ш. Тентекская",
        "ш.ТЕНТЕКСКАЯ": "ш. Тентекская",
        "ш.Шахтинская": "ш. Шахтинская",
        "ш.ШАХТИНСКАЯ": "ш. Шахтинская",
    }

    # Частые ключевые слова должностей, чтобы не путать их с ФИО.
    POSITION_KEYWORDS = (
        "должност",
        "горн",
        "подзем",
        "проходчик",
        "слесар",
        "электрослесар",
        "электровоз",
        "машинист",
        "мастер",
        "начальник",
        "заместител",
        "инженер",
        "оператор",
        "водител",
        "гроз",
        "гргв",
        "лаборант",
        "диспетчер",
        "бригадир",
        "механик",
        "охран",
        "дежурн",
    )

    def handle(self, *args, **options):
        # Сначала создаем заранее определенных пользователей
        users_data = [
            ('КПТУ',),
            ('УТТ',),
            ('Ш. Ленина',),
            ('Ш. Казахстанская',),
            ('ш. Костенко',),
            ('ш. Тентекская',),
            ('ш. Шахтинская',),
            ('ш. Абайская',),
            ('ш. Саранская',),
            ('ш. Кузембаева',),
            ('Энергоуголь',),
            ('ТОО Куpылыш мет',),
            ('УСШМД',),
            ('Цоф Восточная',),
            ('УМТС',),
            ('ГУ',),
            ('АДМИН',),
        ]

        total_users_created = 0
        total_users_updated = 0

        default_password = os.getenv('PROFSOUZ_DEFAULT_PASSWORD')
        admin_password = os.getenv('PROFSOUZ_ADMIN_PASSWORD')

        def _generate_password(length=16):
            alphabet = string.ascii_letters + string.digits
            return ''.join(secrets.choice(alphabet) for _ in range(length))

        # Создаем всех заранее определенных пользователей
        for (username,) in users_data:
            user, created = User.objects.get_or_create(username=username)
            if created:
                if username == 'АДМИН':
                    password = admin_password or _generate_password(20)
                else:
                    password = default_password or _generate_password(16)
                user.set_password(password)
                user.save()
                total_users_created += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Создан пользователь: {username}')
                )
                # ВАЖНО: пароль выводим только при создании (не сохраняем в коде)
                self.stdout.write(self.style.WARNING(f'  Пароль для "{username}": {password}'))
            else:
                self.stdout.write(
                    self.style.WARNING(f'↻ Пользователь уже существует: {username} (пароль не изменён)')
                )

        # Теперь импортируем работников из Excel файлов
        base_dir = Path(settings.BASE_DIR)

        # Ищем папку "работники" независимо от лишних пробелов в имени
        workers_dir = None
        for item in base_dir.iterdir():
            if item.is_dir() and item.name.strip() == "работники":
                workers_dir = item
                break

        if not workers_dir:
            self.stdout.write(
                self.style.WARNING(
                    f"\nПапка 'работники' не найдена в {base_dir}. Пропускаю импорт работников."
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nГотово! Пользователей: создано {total_users_created}, обновлено {total_users_updated}"
                )
            )
            return

        files = sorted(workers_dir.glob("*.xlsx"))
        if not files:
            self.stdout.write(
                self.style.WARNING(
                    f"\nВ папке {workers_dir} не найдено файлов .xlsx для импорта"
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nГотово! Пользователей: создано {total_users_created}, обновлено {total_users_updated}"
                )
            )
            return

        total_workers_created = 0
        total_workers_updated = 0

        for file_path in files:
            # Название файла (без расширения)
            file_name = file_path.stem.strip()
            
            # Находим соответствующего пользователя по маппингу
            username = self.FILE_USER_MAP.get(file_name)
            
            if not username:
                self.stdout.write(
                    self.style.WARNING(
                        f"\nПропускаю файл {file_path.name}: нет соответствующего пользователя в FILE_USER_MAP"
                    )
                )
                continue

            # Получаем пользователя (он должен быть уже создан выше)
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f"\nПользователь {username} не найден! Пропускаю файл {file_path.name}"
                    )
                )
                continue

            # Импортируем работников из файла
            self.stdout.write(
                self.style.NOTICE(f"\nОбработка файла {file_path.name} для пользователя {username}")
            )

            created, updated = self._import_from_excel(file_path, user)
            total_workers_created += created
            total_workers_updated += updated

        self.stdout.write(
            self.style.SUCCESS(
                f"\nГотово! Пользователей: создано {total_users_created}, обновлено {total_users_updated}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Работников: создано {total_workers_created}, обновлено {total_workers_updated}"
            )
        )

    def _normalize_header(self, text):
        """Нормализует текст заголовка для сравнения"""
        if text is None:
            return ""
        return str(text).strip().lower().replace("\n", " ")

    def _build_column_index(self, header_row):
        """Строит mapping: служебное_имя -> индекс столбца"""
        header_texts = [self._normalize_header(cell) for cell in header_row]
        col_index = {}

        for field, variants in self.HEADER_MAP.items():
            for i, h in enumerate(header_texts):
                if not h:
                    continue
                for variant in variants:
                    if (
                        h == variant
                        or (len(variant) >= 3 and variant in h)
                        or (len(variant) > 3 and len(h) > 2 and h in variant)
                    ):
                        col_index[field] = i
                        break
                if field in col_index:
                    break

        return col_index

    def _get_cell_value(self, row, idx_map, key):
        """Получает значение ячейки по ключу"""
        idx = idx_map.get(key)
        if idx is None or idx >= len(row):
            return ""
        return self._to_text(row[idx])

    def _to_text(self, value):
        """Универсальное безопасное преобразование значения ячейки в строку."""
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%d.%m.%Y")
        if isinstance(value, (int, float)):
            if isinstance(value, float) and value.is_integer():
                return f"{int(value)}"
            if isinstance(value, float):
                return f"{value:.0f}"
            return str(value)
        return str(value).strip()

    def _parse_union_flag(self, union_date_str):
        """Определяет, является ли работник членом профсоюза по дате присоединения"""
        if not union_date_str:
            return False
        union_date_str = str(union_date_str).strip()
        if not union_date_str:
            return False
        # Пытаемся распознать дату
        for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                datetime.strptime(union_date_str, fmt)
                return True
            except ValueError:
                continue
        # Если формат не распознан, но строка не пустая — считаем "Да"
        return True

    def _detect_status(self, status_str):
        """Определяет статус работника по тексту (с поддержкой регрессников)."""
        if not status_str:
            return "worker"
        s = str(status_str).strip().lower()
        if "регресс" in s and "пенсион" in s:
            return "regressnik_pensioner"
        if "регресс" in s and ("работ" in s or "рабоч" in s):
            return "regressnik_worker"
        if "регресс" in s:
            return "regressnik"
        if "пенсион" in s:
            return "pensioner"
        return "worker"

    def _normalize_personnel_number(self, value):
        """Нормализует табельный номер, сохраняя только корректный текстовый вид."""
        text = self._to_text(value)
        if not text:
            return ""
        text = text.replace('\xa0', '').replace(' ', '').replace(',', '')
        if text.endswith('.0'):
            text = text[:-2]
        if text.endswith('.'):
            text = text[:-1]
        return text.strip()

    def _looks_like_name_value(self, value):
        """Похоже ли значение на часть ФИО."""
        text = (value or "").strip()
        if not text:
            return False
        if any(ch.isdigit() for ch in text):
            return False
        if self._looks_like_position_value(text):
            return False
        lowered = text.lower()
        if any(word in lowered for word in ("таб", "фам", "имя", "отче", "должност", "дата", "вступ")):
            return False
        return any(ch.isalpha() for ch in text)

    def _looks_like_position_value(self, value):
        """Похоже ли значение на должность/профессию, а не на ФИО."""
        text = (value or "").strip()
        if not text:
            return False
        lowered = text.lower()
        return any(keyword in lowered for keyword in self.POSITION_KEYWORDS)

    def _looks_like_person_full_name(self, value):
        """Похоже ли значение именно на ФИО работника."""
        text = (value or "").strip()
        if not text:
            return False
        if self._looks_like_position_value(text):
            return False
        words = [w for w in text.split() if w]
        if len(words) < 2:
            return False
        return self._looks_like_name_value(text)

    def _name_quality(self, full_name):
        """Оценка качества ФИО: чем больше слов и длина, тем лучше."""
        text = (full_name or "").strip()
        if not text:
            return 0
        words = [w for w in text.split() if w]
        if not words:
            return 0
        return len(words) * 10 + len(text)

    def _guess_full_name_from_row(self, row, col_index):
        """
        Пытается найти в строке неразмеченный столбец с полным ФИО.
        Полезно для файлов, где заголовок у колонки ФИО пустой.
        """
        best_name = ""
        best_score = 0
        personnel_idx = col_index.get("personnel_number")
        first_name_hint = self._get_cell_value(row, col_index, "first_name").split(" ")[0].strip().lower()
        middle_name_hint = self._get_cell_value(row, col_index, "middle_name").split(" ")[0].strip().lower()

        for idx, raw in enumerate(row):
            if idx == personnel_idx:
                continue
            text = self._to_text(raw)
            if not self._looks_like_name_value(text):
                continue
            words = [w for w in text.split() if w]
            if len(words) < 2:
                continue
            lowered_words = [w.lower() for w in words]
            # Если есть подсказки из отдельных колонок имени/отчества, убеждаемся, что кандидат их содержит.
            if first_name_hint and first_name_hint not in lowered_words:
                continue
            if middle_name_hint and middle_name_hint not in lowered_words:
                continue
            score = self._name_quality(text)
            if score > best_score:
                best_name = text
                best_score = score

        return best_name

    def _is_better_full_name(self, incoming_name, current_name):
        """Определяет, стоит ли заменять текущее ФИО новым."""
        incoming_name = (incoming_name or "").strip()
        current_name = (current_name or "").strip()
        if not incoming_name:
            return False
        if not current_name:
            return True
        incoming_is_name = self._looks_like_person_full_name(incoming_name)
        current_is_name = self._looks_like_person_full_name(current_name)

        # Если текущее значение похоже на должность, а новое — на ФИО, заменяем.
        if incoming_is_name and not current_is_name:
            return True
        if not incoming_is_name and current_is_name:
            return False

        return self._name_quality(incoming_name) > self._name_quality(current_name)

    def _select_best_sheet(self, workbook):
        """
        Выбирает лучший лист для импорта по качеству найденных заголовков.
        Это критично для файлов, где Лист1 имеет неполные заголовки.
        """
        best_ws = None
        best_score = -1
        best_rows = -1

        for sheet_name in workbook.sheetnames:
            ws = workbook[sheet_name]
            if ws.max_row < 2:
                continue

            max_header_search = min(10, ws.max_row)
            sheet_score = 0
            for i in range(1, max_header_search + 1):
                row = [cell.value for cell in ws[i]]
                idx_map = self._build_column_index(row)
                if i < max_header_search:
                    next_row = [cell.value for cell in ws[i + 1]]
                    next_map = self._build_column_index(next_row)
                    for key, value in next_map.items():
                        if key not in idx_map:
                            idx_map[key] = value

                score = 0
                if "personnel_number" in idx_map:
                    score += 4
                if "full_name" in idx_map:
                    score += 4
                if "last_name" in idx_map and "first_name" in idx_map:
                    score += 3
                if "position" in idx_map:
                    score += 1
                if "union_date" in idx_map:
                    score += 1
                if score > sheet_score:
                    sheet_score = score

            if (
                sheet_score > best_score
                or (sheet_score == best_score and ws.max_row > best_rows)
            ):
                best_ws = ws
                best_score = sheet_score
                best_rows = ws.max_row

        return best_ws

    def _merge_worker_fields(self, worker, incoming_fields, user):
        """
        Безопасное обновление: не затираем заполненные поля пустыми значениями,
        а только дополняем недостающую информацию.
        """
        changed = False

        incoming_name = (incoming_fields.get("full_name") or "").strip()
        current_name = (worker.full_name or "").strip()
        if self._is_better_full_name(incoming_name, current_name):
            worker.full_name = incoming_name
            changed = True

        incoming_inn = ''.join(ch for ch in str(incoming_fields.get("inn") or "") if ch.isdigit())
        current_inn = ''.join(ch for ch in str(worker.inn or "") if ch.isdigit())
        if len(incoming_inn) == 12 and len(current_inn) != 12:
            worker.inn = incoming_inn
            changed = True

        for field in ("department", "position", "phone", "address"):
            incoming_value = (incoming_fields.get(field) or "").strip()
            current_value = (getattr(worker, field) or "").strip()
            if incoming_value and not current_value:
                setattr(worker, field, incoming_value)
                changed = True

        # Статус повышаем по приоритету (не откатываем к менее информативному).
        status_priority = {
            "worker": 10,
            "regressnik_worker": 20,
            "regressnik": 25,
            "pensioner": 30,
            "regressnik_pensioner": 40,
        }
        incoming_status = (incoming_fields.get("status") or "").strip()
        current_status = (worker.status or "worker").strip()
        if incoming_status in status_priority and status_priority.get(incoming_status, 0) > status_priority.get(current_status, 0):
            worker.status = incoming_status
            changed = True

        # Флаги членства обновляем только в сторону True.
        if incoming_fields.get("is_union_member") and not worker.is_union_member:
            worker.is_union_member = True
            changed = True
        if incoming_fields.get("is_contract_member") and not worker.is_contract_member:
            worker.is_contract_member = True
            changed = True

        if not worker.user_id:
            worker.user = user
            changed = True

        return changed

    def _import_from_excel(self, path: Path, user: User):
        """Импортирует работников из Excel файла"""
        try:
            # Используем data_only=True для получения вычисленных значений
            # Это важно для формул, но может потерять точность для больших чисел
            # Поэтому для табельных номеров будем читать напрямую из ячейки
            wb = openpyxl.load_workbook(str(path), data_only=True)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  Ошибка при открытии файла {path.name}: {e}")
            )
            return 0, 0

        # Выбираем наиболее корректный лист по качеству заголовков.
        ws = self._select_best_sheet(wb)

        if not ws:
            self.stdout.write(
                self.style.WARNING(f"  В файле {path.name} нет данных, пропускаю")
            )
            return 0, 0

        # Ищем строку-заголовок среди первых 10 строк (увеличили для файлов с пустыми строками)
        header_row_idx = None
        col_index = {}

        max_header_search = min(10, ws.max_row)
        for i in range(1, max_header_search + 1):
            row = [cell.value for cell in ws[i]]
            candidate_idx_map = self._build_column_index(row)

            # Проверяем, может быть заголовок разбит на две строки
            if i < max_header_search:
                next_row = [cell.value for cell in ws[i + 1]]
                next_row_map = self._build_column_index(next_row)
                # Объединяем индексы из двух строк
                for key, value in next_row_map.items():
                    if key not in candidate_idx_map:
                        candidate_idx_map[key] = value

            has_personnel = "personnel_number" in candidate_idx_map
            has_full = "full_name" in candidate_idx_map
            has_split_name = (
                "last_name" in candidate_idx_map and "first_name" in candidate_idx_map
            )

            if has_personnel and (has_full or has_split_name):
                header_row_idx = i
                col_index = candidate_idx_map
                break
            # Также принимаем, если есть хотя бы табельный номер и одно из полей имени
            elif has_personnel and (has_full or "first_name" in candidate_idx_map or "last_name" in candidate_idx_map):
                header_row_idx = i
                col_index = candidate_idx_map
                break

        # Если не нашли заголовок, пробуем найти по ключевым словам в любой строке
        if not header_row_idx:
            for i in range(1, max_header_search + 1):
                row = [cell.value for cell in ws[i]]
                row_text = " ".join([self._normalize_header(str(c)) for c in row if c])
                
                has_tab_word = "таб" in row_text
                has_name_words = any(word in row_text for word in ["фамилия", "имя", "отчество", "фио"])
                
                if has_tab_word or has_name_words:
                    # Пробуем построить индекс из этой строки
                    candidate_idx_map = self._build_column_index(row)
                    # Если нашли хотя бы табельный номер или имя/фамилию
                    if "personnel_number" in candidate_idx_map or "first_name" in candidate_idx_map or "last_name" in candidate_idx_map:
                        header_row_idx = i
                        col_index = candidate_idx_map
                        break

        # Если все еще не нашли, пробуем определить по структуре данных
        # Ищем строку, где во второй колонке есть число (табельный номер)
        if not header_row_idx:
            for i in range(1, min(10, ws.max_row)):
                row = [cell.value for cell in ws[i]]
                if len(row) >= 2:
                    # Проверяем, есть ли во второй колонке число (табельный номер)
                    second_col = row[1]
                    if second_col and isinstance(second_col, (int, float)):
                        # Проверяем, что это не заголовок (нет текста "таб" в строке)
                        row_text = " ".join([self._normalize_header(str(c)) for c in row[:5] if c])
                        if "таб" not in row_text.lower() and not any(word in row_text for word in ["фамилия", "имя", "отчество"]):
                            # Это похоже на данные, заголовок должен быть выше
                            # Ищем заголовок в предыдущих строках
                            for j in range(max(1, i-3), i):
                                prev_row = [cell.value for cell in ws[j]]
                                prev_row_text = " ".join([self._normalize_header(str(c)) for c in prev_row[:5] if c])
                                if any(word in prev_row_text for word in ["таб", "фамилия", "имя", "отчество", "фио", "№"]):
                                    header_row_idx = j
                                    col_index = self._build_column_index(prev_row)
                                    break
                            if header_row_idx:
                                break

        # Если не нашли столбцы в заголовках, пробуем определить по структуре данных
        if not col_index or "personnel_number" not in col_index:
            # Ищем строку с данными (где во второй колонке число - табельный номер)
            search_start = header_row_idx + 1 if header_row_idx else 1
            search_end = min(search_start + 10, ws.max_row + 1)
            
            for i in range(search_start, search_end):
                row = [cell.value for cell in ws[i]]
                if len(row) >= 2:
                    # Проверяем колонки на наличие табельного номера
                    # Табельный номер обычно больше 1000 и находится во второй или третьей колонке
                    # Первая колонка (индекс 0) обычно содержит порядковый номер (1, 2, 3...)
                    personnel_col = None
                    
                    # Проверяем колонку 1 (вторая колонка)
                    if len(row) > 1 and row[1] and isinstance(row[1], (int, float)):
                        num_val = float(row[1]) if isinstance(row[1], float) else int(row[1])
                        # Если число больше 1000, это скорее всего табельный номер
                        if num_val >= 1000:
                            personnel_col = 1
                    
                    # Если не нашли в колонке 1, проверяем колонку 2
                    if personnel_col is None and len(row) > 2 and row[2] and isinstance(row[2], (int, float)):
                        num_val = float(row[2]) if isinstance(row[2], float) else int(row[2])
                        if num_val >= 1000:
                            personnel_col = 2
                    
                    # Если нашли табельный номер и есть фамилия в следующей колонке
                    if personnel_col is not None and len(row) > personnel_col + 1 and row[personnel_col + 1] and isinstance(row[personnel_col + 1], str):
                        # Определяем структуру по позициям
                        if not col_index:
                            col_index = {}
                        col_index["personnel_number"] = personnel_col
                        
                        # Фамилия обычно в следующей колонке после табельного номера
                        if "last_name" not in col_index and len(row) > personnel_col + 1:
                            col_index["last_name"] = personnel_col + 1
                        if "first_name" not in col_index and len(row) > personnel_col + 2:
                            col_index["first_name"] = personnel_col + 2
                        if "middle_name" not in col_index and len(row) > personnel_col + 3:
                            col_index["middle_name"] = personnel_col + 3
                        if "position" not in col_index and len(row) > personnel_col + 5:
                            col_index["position"] = personnel_col + 5
                        if "union_date" not in col_index and len(row) > personnel_col + 6:
                            col_index["union_date"] = personnel_col + 6
                        # Обновляем header_row_idx, если он не был найден
                        if not header_row_idx:
                            header_row_idx = i - 1 if i > 1 else 1
                        break

        if not col_index or "personnel_number" not in col_index:
            self.stdout.write(
                self.style.WARNING(
                    f"  В файле {path.name} не найдены обязательные столбцы (ФИО/Табельный), пропускаю"
                )
            )
            return 0, 0

        total_created = 0
        total_updated = 0

        # Обрабатываем строки данных (начиная со строки после заголовка)
        # Если заголовки были разбиты на две строки, начинаем с третьей строки после первого заголовка
        start_data_row = header_row_idx + 1
        # Проверяем следующую строку после заголовка - если она тоже похожа на заголовок, пропускаем её
        if start_data_row <= ws.max_row:
            next_row = [cell.value for cell in ws[start_data_row]]
            next_row_text = " ".join([self._normalize_header(str(c)) for c in next_row[:5] if c])
            if any(word in next_row_text for word in ["таб", "фамилия", "имя", "отчество", "фио", "вступления"]):
                start_data_row += 1
        
        for row_idx in range(start_data_row, ws.max_row + 1):
            # Читаем строку напрямую из worksheet для сохранения точности
            row = [cell.value for cell in ws[row_idx]]
            
            if len(row) < 2:
                continue

            # Получаем/собираем ФИО. Если заголовки кривые, пытаемся восстановить ФИО по содержимому строки.
            has_full = "full_name" in col_index
            if has_full:
                full_name = self._get_cell_value(row, col_index, "full_name")
            else:
                last_name = self._get_cell_value(row, col_index, "last_name")
                first_name = self._get_cell_value(row, col_index, "first_name")
                middle_name = self._get_cell_value(row, col_index, "middle_name")

                # Частый кейс: у колонки "фамилия" пустой заголовок, но она стоит перед "имя".
                if not last_name and "first_name" in col_index:
                    first_name_idx = col_index.get("first_name")
                    if isinstance(first_name_idx, int) and first_name_idx > 0 and first_name_idx - 1 < len(row):
                        candidate_last_name = self._to_text(row[first_name_idx - 1])
                        if self._looks_like_name_value(candidate_last_name):
                            last_name = candidate_last_name

                full_name = " ".join(part for part in [last_name, first_name, middle_name] if part).strip()

            # Если собралось неполное ФИО, пытаемся взять лучший вариант из неразмеченных колонок.
            guessed_full_name = self._guess_full_name_from_row(row, col_index)
            if self._is_better_full_name(guessed_full_name, full_name):
                full_name = guessed_full_name

            # Получаем табельный номер напрямую из ячейки, чтобы сохранить точность
            personnel_number = ""
            personnel_idx = col_index.get("personnel_number")
            if personnel_idx is not None:
                # Получаем значение напрямую из ячейки Excel для максимальной точности
                try:
                    cell = ws[row_idx][personnel_idx]
                    raw_value = cell.value
                    
                    if raw_value is not None:
                        # Для чисел используем безопасное преобразование с сохранением всех цифр
                        if isinstance(raw_value, int):
                            # Целое число - просто преобразуем в строку
                            personnel_number = str(raw_value)
                        elif isinstance(raw_value, float):
                            # Float - проверяем, что это целое число
                            if raw_value.is_integer():
                                # Преобразуем в int, затем в строку для сохранения всех цифр
                                personnel_number = str(int(raw_value))
                            else:
                                # Если не целое, используем форматирование без десятичных
                                # Используем форматирование без научной нотации
                                personnel_number = f"{raw_value:.0f}".rstrip('0').rstrip('.')
                        else:
                            # Для строк и других типов
                            personnel_number = str(raw_value).strip()
                            # Убираем точку в конце, если она есть (например, "1152." -> "1152")
                            if personnel_number.endswith('.'):
                                personnel_number = personnel_number[:-1]
                            # Убираем пробелы и другие лишние символы
                            personnel_number = personnel_number.replace(' ', '').replace(',', '')
                    
                    # Проверка: если табельный номер меньше 1000, это может быть порядковый номер
                    # Попробуем следующую колонку, если она содержит число >= 1000
                    if personnel_number:
                        try:
                            num_val = int(personnel_number)
                            if num_val < 1000 and len(row) > personnel_idx + 1:
                                # Проверяем следующую колонку
                                next_cell = ws[row_idx][personnel_idx + 1]
                                if next_cell.value and isinstance(next_cell.value, (int, float)):
                                    next_val = int(next_cell.value) if isinstance(next_cell.value, int) else int(next_cell.value) if next_cell.value.is_integer() else 0
                                    if next_val >= 1000:
                                        # Это скорее всего табельный номер
                                        personnel_number = str(next_val)
                                        # Обновляем индекс для будущих строк
                                        col_index["personnel_number"] = personnel_idx + 1
                        except (ValueError, TypeError):
                            pass
                            
                except (IndexError, AttributeError, TypeError) as e:
                    # Fallback на обычное чтение из row
                    if personnel_idx < len(row):
                        raw_value = row[personnel_idx]
                        if raw_value is not None:
                            if isinstance(raw_value, int):
                                personnel_number = str(raw_value)
                            elif isinstance(raw_value, float):
                                if raw_value.is_integer():
                                    personnel_number = str(int(raw_value))
                                else:
                                    personnel_number = f"{raw_value:.0f}".rstrip('0').rstrip('.')
                            else:
                                personnel_number = str(raw_value).strip()
                                if personnel_number.endswith('.'):
                                    personnel_number = personnel_number[:-1]
                                personnel_number = personnel_number.replace(' ', '').replace(',', '')
                            
                            # Проверка: если табельный номер меньше 1000, пробуем следующую колонку
                            if personnel_number:
                                try:
                                    num_val = int(personnel_number)
                                    if num_val < 1000 and len(row) > personnel_idx + 1:
                                        next_val = row[personnel_idx + 1]
                                        if next_val and isinstance(next_val, (int, float)):
                                            next_num = int(next_val) if isinstance(next_val, int) else int(next_val) if next_val.is_integer() else 0
                                            if next_num >= 1000:
                                                personnel_number = str(next_num)
                                                col_index["personnel_number"] = personnel_idx + 1
                                except (ValueError, TypeError):
                                    pass

            personnel_number = self._normalize_personnel_number(personnel_number)

            # Пропускаем пустые строки (нужен хотя бы табельный номер или ФИО)
            if not full_name and not personnel_number:
                continue

            # Пропускаем строки, которые похожи на заголовки
            if full_name and any(
                word in full_name.lower()
                for word in ["таб", "фамилия", "имя", "отчество", "фио", "№", "номер"]
            ):
                continue

            # Пропускаем строки без табельного номера (он обязателен)
            if not personnel_number:
                continue

            # Получаем остальные поля
            inn = self._get_cell_value(row, col_index, "inn")
            department = self._get_cell_value(row, col_index, "department")
            position = self._get_cell_value(row, col_index, "position")
            status_text = self._get_cell_value(row, col_index, "status")
            union_date_str = self._get_cell_value(row, col_index, "union_date")
            address = self._get_cell_value(row, col_index, "address")
            phone = self._get_cell_value(row, col_index, "phone")

            status = self._detect_status(status_text)
            is_union_member = self._parse_union_flag(union_date_str)

            worker_defaults = {
                "full_name": full_name,
                "inn": inn or "",
                "status": status,
                "is_union_member": is_union_member,
                "department": department or "",
                "position": position or "",
                "is_contract_member": is_union_member,
                "phone": phone or "",
                "address": address or "",
            }

            # Обновляем существующего работника только дополнением пустых полей,
            # не перезаписывая заполненные значения пустыми из файла.
            worker = Worker.objects.filter(user=user, personnel_number=personnel_number).first()

            # Если есть "осиротевшая" запись без привязки к пользователю, забираем ее вместо создания дубля.
            if not worker:
                orphan_worker = Worker.objects.filter(user__isnull=True, personnel_number=personnel_number).first()
                if orphan_worker:
                    worker = orphan_worker
                    worker.user = user

            if not worker:
                worker = Worker.objects.create(
                    user=user,
                    personnel_number=personnel_number,
                    full_name=(worker_defaults.get("full_name") or "").strip(),
                    inn=''.join(ch for ch in str(worker_defaults.get("inn") or "") if ch.isdigit())[:12],
                    status=worker_defaults.get("status") or "worker",
                    is_union_member=bool(worker_defaults.get("is_union_member")),
                    department=(worker_defaults.get("department") or "").strip(),
                    position=(worker_defaults.get("position") or "").strip(),
                    is_contract_member=bool(worker_defaults.get("is_contract_member")),
                    phone=(worker_defaults.get("phone") or "").strip(),
                    address=(worker_defaults.get("address") or "").strip(),
                )
                total_created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Создан работник {worker.full_name} ({personnel_number})"
                    )
                )
            else:
                changed = self._merge_worker_fields(worker, worker_defaults, user)
                if changed:
                    worker.save()
                    total_updated += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ↻ Обновлен работник {worker.full_name} ({personnel_number})"
                        )
                    )

        return total_created, total_updated
