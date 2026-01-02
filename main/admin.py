from django.contrib import admin
from .models import Worker, FamilyMember, VacationRequest, VacationLimit, Statement, MaterialAssistanceRequest


class FamilyMemberInline(admin.TabularInline):
    model = FamilyMember
    extra = 1
    fields = ['full_name', 'relationship', 'id_number', 'id_issue_date', 'id_issued_by']


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'personnel_number', 'inn', 'status', 'department', 'position', 'is_union_member', 'user']
    list_filter = ['status', 'is_union_member', 'is_contract_member', 'department', 'user']
    search_fields = ['full_name', 'personnel_number', 'inn', 'department', 'position', 'phone']
    inlines = [FamilyMemberInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'full_name', 'personnel_number', 'inn', 'status', 'is_union_member', 'department', 'position', 'is_contract_member')
        }),
        ('Контактная информация', {
            'fields': ('phone', 'address')
        }),
        ('Удостоверение личности', {
            'fields': ('id_number', 'id_issue_date', 'id_issued_by')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


@admin.register(FamilyMember)
class FamilyMemberAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'worker', 'relationship', 'id_number']
    list_filter = ['relationship']
    search_fields = ['full_name', 'worker__full_name', 'id_number']


@admin.register(VacationRequest)
class VacationRequestAdmin(admin.ModelAdmin):
    list_display = ['worker', 'resort', 'start_date', 'end_date', 'is_rejected', 'created_at', 'user']
    list_filter = ['resort', 'is_rejected', 'created_at', 'user']
    search_fields = ['worker__full_name', 'worker__personnel_number']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['family_members']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


@admin.register(VacationLimit)
class VacationLimitAdmin(admin.ModelAdmin):
    list_display = ['user', 'resort', 'period_start', 'limit', 'is_initial', 'created_at']
    list_filter = ['resort', 'period_start', 'is_initial', 'user']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Statement)
class StatementAdmin(admin.ModelAdmin):
    list_display = ['user', 'resort', 'period_start', 'period_end', 'status', 'created_at']
    list_filter = ['status', 'resort', 'period_start', 'user']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(MaterialAssistanceRequest)
class MaterialAssistanceRequestAdmin(admin.ModelAdmin):
    list_display = ['worker', 'assistance_type', 'amount', 'created_at', 'user']
    list_filter = ['assistance_type', 'created_at', 'user']
    search_fields = ['worker__full_name', 'worker__personnel_number']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)
