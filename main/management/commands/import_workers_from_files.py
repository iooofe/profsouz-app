from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings

from pathlib import Path
from datetime import datetime

from main.models import Worker

from docx import Document


class Command(BaseCommand):
    help = (
        "Импортирует работников из файлов в папке 'работники' в корне проекта.\n"
        "Ожидаются файлы .docx с таблицей, где первая строка — заголовки столбцов."
    )

    # Возможные варианты названий столбцов -> поле Worker / служебные поля
    HEADER_MAP = {
        "full_name": ["фио", "ф.и.о", "ф. и. о."],
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
        "position": ["должность", "профессия"],
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
        "АБАЙСКАЯ": "ш. Абайская",
        "КАЗАХСТАНСКАЯ": "Ш. Казахстанская",
        "КОСТЕНКО": "ш. Костенко",
        "КПТУ": "КПТУ",
        "КУЗЕМБАЕВА": "ш. Кузембаева",
        "ЛЕНИНА": "Ш. Ленина",
        "САРАНСКАЯ": "ш. Саранская",
        "ТЕНТЕКСКАЯ": "ш. Тентекская",
        "ШАХТИНСКАЯ": "ш. Шахтинская",
        "УСШМД": "УСШМД",
        "УТТ": "УТТ",
        "ЦОФ ВОСТОЧНАЯ": "Цоф Восточная",
        "ЭНЕРГОУГОЛЬ": "Энергоуголь",
        # Остальные файлы (например, сводные списки) обрабатываются отдельно при необходимости
    }

    def handle(self, *args, **options):
        base_dir = Path(settings.BASE_DIR)

        # Ищем папку "работники" независимо от лишних пробелов в имени
        workers_dir = None
        for item in base_dir.iterdir():
            if item.is_dir() and item.name.strip() == "работники":
                workers_dir = item
                break

        if not workers_dir:
            self.stdout.write(
                self.style.ERROR(
                    f"Папка 'работники' не найдена в {base_dir}. Убедитесь, что она существует."
                )
            )
            return

        files = sorted(workers_dir.glob("*.docx"))
        if not files:
            self.stdout.write(
                self.style.WARNING(
                    f"В папке {workers_dir} не найдено файлов .docx для импорта"
                )
            )
            return

        total_created = 0
        total_updated = 0

        for file_path in files:
            stem = file_path.stem.strip()
            username = self.FILE_USER_MAP.get(stem)
            if not username:
                self.stdout.write(
                    self.style.WARNING(
                        f"Пропускаю файл {file_path.name}: нет соответствующего пользователя в FILE_USER_MAP"
                    )
                )
                continue

            user, _ = User.objects.get_or_create(username=username)
            self.stdout.write(
                self.style.NOTICE(f"\nОбработка файла {file_path.name} для пользователя {username}")
            )

            created, updated = self._import_from_docx(file_path, user)
            total_created += created
            total_updated += updated

        self.stdout.write(
            self.style.SUCCESS(
                f"\nИмпорт завершен. Создано работников: {total_created}, обновлено: {total_updated}"
            )
        )

    def _normalize_header(self, text: str) -> str:
        return (text or "").strip().lower().replace("\n", " ")

    def _build_column_index(self, header_row):
        """
        Строит mapping: служебное_имя -> индекс столбца.
        """
        header_texts = [self._normalize_header(c.text) for c in header_row.cells]
        col_index = {}

        for field, variants in self.HEADER_MAP.items():
            for i, h in enumerate(header_texts):
                if not h:  # Пропускаем пустые заголовки
                    continue
                # Более гибкий поиск: проверяем, содержит ли заголовок любой из вариантов
                for variant in variants:
                    # Точное совпадение
                    if h == variant:
                        col_index[field] = i
                        break
                    # Частичное совпадение (вариант содержится в заголовке)
                    if variant in h:
                        col_index[field] = i
                        break
                    # Обратное совпадение (заголовок содержится в варианте, если вариант длиннее)
                    if len(variant) > 3 and h in variant:
                        col_index[field] = i
                        break
                if field in col_index:
                    break

        return col_index

    def _get_cell(self, row, idx_map, key):
        idx = idx_map.get(key)
        if idx is None:
            return ""
        cells = row.cells
        if idx >= len(cells):
            return ""
        return cells[idx].text.strip()

    def _parse_union_flag(self, union_date_str: str) -> bool:
        """
        Если в ячейке с датой присоединения что‑то есть — считаем, что человек присоединен.
        Конкретный формат даты не важен, важен факт наличия значения.
        """
        if not union_date_str:
            return False
        # Пытаемся распознать дату, но это не обязательно
        for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                datetime.strptime(union_date_str.strip(), fmt)
                return True
            except ValueError:
                continue
        # Если формат не распознан, но строка не пустая — все равно считаем "Да"
        return True

    def _detect_status(self, status_str: str) -> str:
        """
        Определяем статус работника (worker/pensioner) по тексту в соответствующем столбце.
        По умолчанию — worker.
        """
        s = (status_str or "").strip().lower()
        if "пенсион" in s:
            return "pensioner"
        return "worker"

    def _import_from_docx(self, path: Path, user: User):
        """
        Ищем подходящую таблицу во всех таблицах файла и импортируем строки.
        Подходящая таблица — где есть хотя бы заголовки для табельного номера
        и ФИО (одним столбцом или как фамилия+имя(+отчество)) и есть данные.
        Учитываем, что первая строка в таблице может быть не заголовком
        (например, «шахта АБАЙСКАЯ»), поэтому ищем заголовок среди первых строк.
        """
        doc = Document(str(path))
        if not doc.tables:
            self.stdout.write(
                self.style.WARNING(f"  В файле {path.name} нет таблиц, пропускаю")
            )
            return 0, 0

        total_created = 0
        total_updated = 0
        any_table_processed = False

        for table in doc.tables:
            if len(table.rows) < 2:
                continue

            first_row_cells = table.rows[0].cells
            
            # Ищем строку-заголовок среди первых 5 строк таблицы
            header_row = None
            col_index = {}
            start_data_row_idx = 1

            max_header_search = min(5, len(table.rows))
            for i in range(max_header_search):
                candidate_row = table.rows[i]
                candidate_idx_map = self._build_column_index(candidate_row)

                has_personnel = "personnel_number" in candidate_idx_map
                has_full = "full_name" in candidate_idx_map
                has_split_name = (
                    "last_name" in candidate_idx_map and "first_name" in candidate_idx_map
                )

                if has_personnel and (has_full or has_split_name):
                    header_row = candidate_row
                    col_index = candidate_idx_map
                    start_data_row_idx = i + 1
                    break

            # Если не нашли строку заголовка по текстам, пробуем типовой формат:
            # колонки: № | таб.№ | фамилия | имя | отчество | должность | ... | дата вступления
            if not header_row:
                found_typical_format = False
                typical_start_row = 1
                
                # Если таблица имеет хотя бы 3 колонки, пытаемся обработать
                # (уменьшил до 3, так как минимально нужны: №, таб.№, фамилия)
                if len(first_row_cells) >= 3:
                    # Пробуем найти заголовок в первых строках по ключевым словам
                    
                    # Проверяем первые 5 строк на наличие заголовка
                    for check_row_idx in range(min(5, len(table.rows))):
                        check_row = table.rows[check_row_idx]
                        check_cells = [c.text.strip().lower() for c in check_row.cells]
                        # Ищем наличие слов "таб" и "фамилия" или "имя" в разных колонках
                        has_tab_word = any("таб" in cell for cell in check_cells)
                        has_name_words = any(
                            any(word in cell for word in ["фамилия", "имя", "отчество", "фио"])
                            for cell in check_cells
                        )
                        if has_tab_word and has_name_words:
                            # Это похоже на заголовок, используем следующую строку как начало данных
                            typical_start_row = check_row_idx + 1
                            found_typical_format = True
                            break
                    
                    # Если не нашли заголовок, определяем начало данных по содержимому
                    if not found_typical_format:
                        # Проверяем первые 3 строки, чтобы определить, где начинаются данные
                        for check_row_idx in range(min(3, len(table.rows))):
                            check_row = table.rows[check_row_idx]
                            check_cells = check_row.cells
                            if len(check_cells) >= 3:
                                # Проверяем вторую и третью колонки на наличие цифр (табельный номер)
                                col1_text = check_cells[1].text.strip() if len(check_cells) > 1 else ""
                                col2_text = check_cells[2].text.strip() if len(check_cells) > 2 else ""
                                # Если во второй или третьей колонке есть цифры - это данные
                                has_digits = (
                                    (col1_text and any(c.isdigit() for c in col1_text[:3])) or
                                    (col2_text and any(c.isdigit() for c in col2_text[:3]))
                                )
                                # Проверяем, что это не заголовок (нет слов "таб", "фамилия" и т.д.)
                                row_text_lower = " ".join([c.text.strip().lower() for c in check_cells[:5]])
                                is_not_header = not any(word in row_text_lower for word in ["таб", "фамилия", "имя", "отчество", "фио", "№"])
                                
                                if has_digits and is_not_header:
                                    # Это данные, начинаем с этой строки
                                    typical_start_row = check_row_idx
                                    found_typical_format = True
                                    break
                    
                    # Если все еще не определили, пробуем начать со второй строки (первая может быть заголовком)
                    if not found_typical_format:
                        typical_start_row = 1
                        found_typical_format = True
                
                # Если нашли типовой формат или просто есть достаточно колонок, пробуем стандартный формат по позициям
                # Обрабатываем если есть хотя бы 3 колонки
                if found_typical_format or len(first_row_cells) >= 3:
                    any_table_processed = True
                    created = 0
                    updated = 0

                    for row in table.rows[typical_start_row:]:
                        cells = row.cells
                        if len(cells) < 2:
                            continue
                        
                        # Пробуем разные варианты позиций столбцов
                        # Вариант 1: № | таб.№ | фамилия | имя | отчество
                        personnel_number = ""
                        last_name = ""
                        first_name = ""
                        middle_name = ""
                        
                        # Табельный номер может быть в колонке 0, 1 или 2
                        # Сначала проверяем колонку 1 (вторая колонка, после №)
                        if len(cells) > 1:
                            col1 = cells[1].text.strip()
                            # Если в колонке 1 есть цифры - это табельный номер
                            if col1 and any(c.isdigit() for c in col1[:5]):
                                personnel_number = col1
                                if len(cells) > 2:
                                    last_name = cells[2].text.strip()
                                if len(cells) > 3:
                                    first_name = cells[3].text.strip()
                                if len(cells) > 4:
                                    middle_name = cells[4].text.strip()
                            # Иначе проверяем колонку 2
                            elif len(cells) > 2:
                                col2 = cells[2].text.strip()
                                if col2 and any(c.isdigit() for c in col2[:5]):
                                    personnel_number = col2
                                    if len(cells) > 3:
                                        last_name = cells[3].text.strip()
                                    if len(cells) > 4:
                                        first_name = cells[4].text.strip()
                                    if len(cells) > 5:
                                        middle_name = cells[5].text.strip()
                                else:
                                    # Стандартный вариант: колонка 1 = таб.№, колонка 2 = фамилия
                                    personnel_number = col1 if col1 else ""
                                    last_name = col2 if col2 else ""
                                    if len(cells) > 3:
                                        first_name = cells[3].text.strip()
                                    if len(cells) > 4:
                                        middle_name = cells[4].text.strip()
                            else:
                                # Если только 2 колонки, пробуем: колонка 0 = таб.№, колонка 1 = ФИО
                                if len(cells) > 0:
                                    col0 = cells[0].text.strip()
                                    if col0 and any(c.isdigit() for c in col0[:5]):
                                        personnel_number = col0
                                    if len(cells) > 1:
                                        # Пробуем разбить ФИО на части
                                        full_name_text = cells[1].text.strip()
                                        if full_name_text:
                                            name_parts = full_name_text.split()
                                            if len(name_parts) >= 1:
                                                last_name = name_parts[0]
                                            if len(name_parts) >= 2:
                                                first_name = name_parts[1]
                                            if len(name_parts) >= 3:
                                                middle_name = name_parts[2]
                        
                        full_name = " ".join(
                            part
                            for part in [last_name, first_name, middle_name]
                            if part
                        ).strip()

                        # Пропускаем пустые строки или строки без данных
                        if not full_name and not personnel_number:
                            continue
                        
                        # Пропускаем строки, которые похожи на заголовки
                        if full_name and any(word in full_name.lower() for word in ["таб", "фамилия", "имя", "отчество", "фио", "№", "номер"]):
                            continue

                        position = cells[5].text.strip() if len(cells) > 5 else ""
                        # дата присоединения обычно в последней колонке
                        union_date_str = cells[-1].text.strip() if cells else ""

                        status = "worker"
                        is_union_member = self._parse_union_flag(union_date_str)

                        worker_defaults = {
                            "full_name": full_name,
                            "inn": "",
                            "status": status,
                            "is_union_member": is_union_member,
                            "department": "",
                            "position": position,
                            "is_contract_member": is_union_member,
                            "phone": "",
                            "address": "",
                        }

                        worker, was_created = Worker.objects.update_or_create(
                            user=user,
                            personnel_number=personnel_number,
                            defaults=worker_defaults,
                        )

                        if was_created:
                            created += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"  ✓ Создан работник {worker.full_name} ({personnel_number})"
                                )
                            )
                        else:
                            updated += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  ↻ Обновлен работник {worker.full_name} ({personnel_number})"
                                )
                            )

                    total_created += created
                    total_updated += updated
                continue

            any_table_processed = True
            created = 0
            updated = 0

            for row in table.rows[start_data_row_idx:]:
                if has_full:
                    full_name = self._get_cell(row, col_index, "full_name")
                else:
                    last_name = self._get_cell(row, col_index, "last_name")
                    first_name = self._get_cell(row, col_index, "first_name")
                    middle_name = self._get_cell(row, col_index, "middle_name")
                    full_name = " ".join(
                        part
                        for part in [last_name, first_name, middle_name]
                        if part
                    ).strip()

                personnel_number = self._get_cell(row, col_index, "personnel_number")

                if not full_name and not personnel_number:
                    continue

                inn = self._get_cell(row, col_index, "inn")
                department = self._get_cell(row, col_index, "department")
                position = self._get_cell(row, col_index, "position")
                status_text = self._get_cell(row, col_index, "status")
                union_date_str = self._get_cell(row, col_index, "union_date")
                address = self._get_cell(row, col_index, "address")
                phone = self._get_cell(row, col_index, "phone")

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

                worker, was_created = Worker.objects.update_or_create(
                    user=user,
                    personnel_number=personnel_number,
                    defaults=worker_defaults,
                )

                if was_created:
                    created += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Создан работник {worker.full_name} ({personnel_number})"
                        )
                    )
                else:
                    updated += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ↻ Обновлен работник {worker.full_name} ({personnel_number})"
                        )
                    )

            total_created += created
            total_updated += updated

        if not any_table_processed:
            self.stdout.write(
                self.style.WARNING(
                    f"  В файле {path.name} не найдены обязательные столбцы (ФИО/Табельный), пропускаю"
                )
            )

        return total_created, total_updated


