from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('worker/<int:worker_id>/', views.worker_detail, name='worker_detail'),
    path('worker/<int:worker_id>/edit/', views.worker_edit, name='worker_edit'),
    path('worker/<int:worker_id>/delete/', views.worker_delete, name='worker_delete'),
    path('api/search-workers/', views.search_workers, name='search_workers'),
    path('api/worker/<int:worker_id>/family/', views.get_worker_with_family, name='get_worker_with_family'),
    path('vacation-request/create/', views.create_vacation_request, name='create_vacation_request'),
    path('vacation-request/<int:request_id>/', views.vacation_request_detail, name='vacation_request_detail'),
    path('vacation-request/<int:request_id>/update/', views.update_vacation_request, name='update_vacation_request'),
    path('vacation-request/<int:request_id>/download/', views.download_vacation_request, name='download_vacation_request'),
    path('vacation-limit/set/', views.set_vacation_limit, name='set_vacation_limit'),
    path('statement/zhartas/excel/', views.generate_zhartas_statement_excel, name='generate_zhartas_statement_excel'),
    path('statement/shakhter/excel/', views.generate_shakhter_statement_excel, name='generate_shakhter_statement_excel'),
    path('worker/<int:worker_id>/file/<str:file_type>/', views.download_worker_file, name='download_worker_file'),
    path('material-assistance/create/', views.create_material_assistance_request, name='create_material_assistance_request'),
    path('material-assistance/<int:request_id>/', views.material_assistance_detail, name='material_assistance_detail'),
    path('material-assistance/<int:request_id>/download/', views.download_material_assistance, name='download_material_assistance'),
    path('coal-request/create/', views.create_coal_request, name='create_coal_request'),
    path('coal-request/<int:request_id>/', views.coal_request_detail, name='coal_request_detail'),
    path('coal-request/<int:request_id>/download/', views.download_coal_request, name='download_coal_request'),
    path('funeral-request/create/', views.create_funeral_request, name='create_funeral_request'),
    path('funeral-request/<int:request_id>/', views.funeral_request_detail, name='funeral_request_detail'),
    path('funeral-request/<int:request_id>/download/', views.download_funeral_request, name='download_funeral_request'),
    path('coal-compensation/list/', views.coal_compensation_list, name='coal_compensation_list'),
    path('coal-compensation/excel/', views.generate_coal_compensation_excel, name='generate_coal_compensation_excel'),
    path('bonus-payment/list/', views.bonus_payment_list, name='bonus_payment_list'),
    path('bonus-payment/excel/', views.generate_bonus_payment_excel, name='generate_bonus_payment_excel'),
    path('funeral-services/list/', views.funeral_services_list, name='funeral_services_list'),
    path('funeral-services/excel/', views.generate_funeral_services_excel, name='generate_funeral_services_excel'),
    path('pensioner-material-assistance/list/', views.pensioner_material_assistance_list, name='pensioner_material_assistance_list'),
    path('pensioner-material-assistance/excel/', views.generate_pensioner_material_assistance_excel, name='generate_pensioner_material_assistance_excel'),
    # API для обновления значений в списках (только для админа)
    path('api/coal-compensation/<int:request_id>/update-payment/', views.update_coal_compensation_payment, name='update_coal_compensation_payment'),
    path('api/bonus-payment/<int:worker_id>/update-payment/', views.update_bonus_payment, name='update_bonus_payment'),
    path('api/funeral-services/<int:request_id>/update-payment/', views.update_funeral_services_payment, name='update_funeral_services_payment'),
    path('api/pensioner-material-assistance/<int:request_id>/update-payment/', views.update_pensioner_material_assistance_payment, name='update_pensioner_material_assistance_payment'),
]

