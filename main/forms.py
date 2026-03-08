from django import forms
from django.contrib.auth.models import User
from .models import Worker, FamilyMember, VacationRequest, MaterialAssistanceRequest, CoalRequest, FuneralRequest


class LoginForm(forms.Form):
    username = forms.ChoiceField(
        label='Аккаунт',
        choices=[],
        widget=forms.Select(attrs={
            'class': 'form-input',
        })
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Введите пароль',
            'autocomplete': 'current-password',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Подтягиваем все аккаунты из базы и заполняем выпадающий список
        users = User.objects.all().order_by('username')
        self.fields['username'].choices = [(u.username, u.username) for u in users]


class FamilyMemberForm(forms.ModelForm):
    class Meta:
        model = FamilyMember
        fields = ['full_name', 'relationship', 'id_number', 'id_issue_date', 'id_issued_by', 'birth_date']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'ФИО',
            }),
            'relationship': forms.Select(attrs={
                'class': 'form-input',
            }),
            'id_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Номер удостоверения',
            }),
            'id_issue_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
            'id_issued_by': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Кем выдано',
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
            'has_benefits': forms.Select(attrs={
                'class': 'form-input',
            }),
            'has_miner_glory': forms.Select(attrs={
                'class': 'form-input',
            }),
            'is_dead': forms.Select(attrs={
                'class': 'form-input',
            }),
        }


class WorkerForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Табельный номер может отсутствовать (например, при переходе в САП)
        if 'personnel_number' in self.fields:
            self.fields['personnel_number'].required = False
            self.fields['personnel_number'].help_text = 'Можно оставить пустым (если табельного номера нет).'
        if not self.instance.pk:
            self.fields['phone'].initial = '+7'
            self.fields['account_20_digit'].initial = 'KZ'
            self.fields['current_account'].initial = 'KZ'

    def clean_personnel_number(self):
        personnel_number = self.cleaned_data.get('personnel_number')
        if personnel_number is None:
            return None
        personnel_number = str(personnel_number).strip()
        return personnel_number or None

    class Meta:
        model = Worker
        fields = [
            'full_name', 'personnel_number', 'inn', 'status', 'is_union_member',
            'department', 'position', 'is_contract_member',
            'phone', 'address', 'id_number', 'id_issue_date', 'id_issued_by',
            'has_benefits', 'benefits_file', 'benefits_name',
            'has_miner_glory', 'miner_glory_file',
            'house_passport_file', 'pensioner_id_file', 'account_20_digit', 'current_account',
            'enterprise_subdivision', 'regress_100_active', 'regress_29_active', 'regress_15_active',
            'is_dead', 'death_date', 'death_certificate_file'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Введите ФИО',
            }),
            'personnel_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Табельный номер',
            }),
            'inn': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'ИНН (12 цифр)',
                'maxlength': '12',
            }),
            'status': forms.Select(attrs={
                'class': 'form-input',
            }),
            'is_union_member': forms.Select(attrs={
                'class': 'form-input',
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Участок',
            }),
            'position': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Должность',
            }),
            'is_contract_member': forms.Select(attrs={
                'class': 'form-input',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+7 (XXX) XXX-XX-XX',
                'type': 'tel',
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-input form-textarea',
                'placeholder': 'Адрес',
                'rows': 3,
            }),
            'id_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Номер удостоверения',
                'required': True,
            }),
            'id_issue_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
            'id_issued_by': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Кем выдано',
            }),
            'death_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
            'enterprise_subdivision': forms.Select(attrs={
                'class': 'form-input',
            }),
        }


class VacationRequestForm(forms.ModelForm):
    class Meta:
        model = VacationRequest
        fields = ['worker', 'resort', 'start_date', 'end_date']
        widgets = {
            'worker': forms.HiddenInput(),
            'resort': forms.Select(attrs={
                'class': 'form-input',
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
        }


class MaterialAssistanceRequestForm(forms.ModelForm):
    class Meta:
        model = MaterialAssistanceRequest
        fields = ['worker', 'assistance_type', 'amount']
        widgets = {
            'worker': forms.HiddenInput(),
            'assistance_type': forms.Select(attrs={
                'class': 'form-input',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Введите сумму',
                'step': '0.01',
                'min': '0',
            }),
        }


class CoalRequestForm(forms.ModelForm):
    # Добавляем поля для файлов, которые не в модели, но нужны для загрузки
    passport_file = forms.FileField(required=True, widget=forms.FileInput(attrs={'class': 'form-input'}))
    pensioner_id_file = forms.FileField(required=True, widget=forms.FileInput(attrs={'class': 'form-input'}))
    
    class Meta:
        model = CoalRequest
        fields = ['worker', 'account_type', 'account_number']
        widgets = {
            'worker': forms.HiddenInput(),
            'account_type': forms.Select(attrs={
                'class': 'form-input',
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'KZ1234567890123456780',
                'maxlength': '20',
            }),
        }
    
    def clean_account_number(self):
        account_number = self.cleaned_data.get('account_number')
        account_type = self.cleaned_data.get('account_type')
        
        # Для любого типа счета требуется IBAN формата KZ + 18 цифр
        if account_type:
            if not account_number:
                raise forms.ValidationError('Необходимо указать номер счета')
            if not account_number.startswith('KZ'):
                raise forms.ValidationError('Номер счета должен начинаться с KZ')
            if len(account_number) != 20:
                raise forms.ValidationError('Номер счета должен содержать KZ и 18 цифр (всего 20 символов)')
            # Проверяем, что после KZ идут только цифры
            digits = account_number[2:]
            if not digits.isdigit() or len(digits) != 18:
                raise forms.ValidationError('После KZ должны быть только 18 цифр')
        
        return account_number


class FuneralRequestForm(forms.ModelForm):
    # Добавляем поля для файлов, которые не в модели, но нужны для загрузки
    applicant_id_file = forms.FileField(required=True, widget=forms.FileInput(attrs={'class': 'form-input'}))
    death_certificate_file = forms.FileField(required=True, widget=forms.FileInput(attrs={'class': 'form-input'}))
    recipient_account_file = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-input'}))
    
    class Meta:
        model = FuneralRequest
        fields = ['worker', 'applicant_full_name', 'applicant_inn', 'account_type', 'account_number']
        widgets = {
            'worker': forms.HiddenInput(),
            'applicant_full_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Введите ФИО заявителя',
            }),
            'applicant_inn': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'ИИН (12 цифр)',
                'maxlength': '12',
            }),
            'account_type': forms.Select(attrs={
                'class': 'form-input',
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'KZ1234567890123456780',
                'maxlength': '20',
            }),
        }
    
    def clean_applicant_inn(self):
        inn = self.cleaned_data.get('applicant_inn')
        if inn:
            # Убираем все нецифровые символы
            cleaned = ''.join(c for c in inn if c.isdigit())
            if len(cleaned) != 12:
                raise forms.ValidationError('ИИН должен содержать 12 цифр')
            return cleaned
        return inn
    
    def clean_account_number(self):
        account_number = self.cleaned_data.get('account_number')
        account_type = self.cleaned_data.get('account_type')
        
        # Для любого типа счета требуется IBAN формата KZ + 18 цифр
        if account_type:
            if not account_number:
                raise forms.ValidationError('Необходимо указать номер счета')
            if not account_number.startswith('KZ'):
                raise forms.ValidationError('Номер счета должен начинаться с KZ')
            if len(account_number) != 20:
                raise forms.ValidationError('Номер счета должен содержать KZ и 18 цифр (всего 20 символов)')
            # Проверяем, что после KZ идут только цифры
            digits = account_number[2:]
            if not digits.isdigit() or len(digits) != 18:
                raise forms.ValidationError('После KZ должны быть только 18 цифр')
        
        return account_number
