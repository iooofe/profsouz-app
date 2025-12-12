from django import forms
from .models import Worker, FamilyMember, VacationRequest, MaterialAssistanceRequest, CoalRequest, FuneralRequest


class LoginForm(forms.Form):
    username = forms.CharField(
        label='Логин',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Введите логин',
            'autocomplete': 'username',
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


class FamilyMemberForm(forms.ModelForm):
    class Meta:
        model = FamilyMember
        fields = ['full_name', 'relationship', 'id_number', 'id_issue_date', 'id_issued_by']
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
        }


class WorkerForm(forms.ModelForm):
    class Meta:
        model = Worker
        fields = [
            'full_name', 'personnel_number', 'inn', 'status', 'is_union_member',
            'department', 'position', 'is_contract_member',
            'phone', 'address', 'id_number', 'id_issue_date', 'id_issued_by',
            'has_benefits', 'benefits_file', 'benefits_name',
            'has_miner_glory', 'miner_glory_file',
            'house_passport_file', 'pensioner_id_file', 'account_20_digit',
            'is_dead', 'death_certificate_file'
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
            }),
            'id_issue_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
            'id_issued_by': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Кем выдано',
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
                'placeholder': 'KZ12345678901234567890',
                'maxlength': '22',
            }),
        }
    
    def clean_account_number(self):
        account_number = self.cleaned_data.get('account_number')
        account_type = self.cleaned_data.get('account_type')
        
        if account_type == '20_digit':
            if not account_number:
                raise forms.ValidationError('Необходимо указать номер 20-значного счета')
            if not account_number.startswith('KZ'):
                raise forms.ValidationError('Номер счета должен начинаться с KZ')
            if len(account_number) != 22:
                raise forms.ValidationError('Номер счета должен содержать KZ и 20 цифр (всего 22 символа)')
            # Проверяем, что после KZ идут только цифры
            digits = account_number[2:]
            if not digits.isdigit():
                raise forms.ValidationError('После KZ должны быть только цифры')
        
        return account_number


class FuneralRequestForm(forms.ModelForm):
    # Добавляем поля для файлов, которые не в модели, но нужны для загрузки
    applicant_id_file = forms.FileField(required=True, widget=forms.FileInput(attrs={'class': 'form-input'}))
    death_certificate_file = forms.FileField(required=True, widget=forms.FileInput(attrs={'class': 'form-input'}))
    
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
                'placeholder': 'KZ12345678901234567890',
                'maxlength': '22',
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
        
        if account_type == '20_digit':
            if not account_number:
                raise forms.ValidationError('Необходимо указать номер 20-значного счета')
            if not account_number.startswith('KZ'):
                raise forms.ValidationError('Номер счета должен начинаться с KZ')
            if len(account_number) != 22:
                raise forms.ValidationError('Номер счета должен содержать KZ и 20 цифр (всего 22 символа)')
            # Проверяем, что после KZ идут только цифры
            digits = account_number[2:]
            if not digits.isdigit():
                raise forms.ValidationError('После KZ должны быть только цифры')
        
        return account_number
