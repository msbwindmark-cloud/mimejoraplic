from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='core_dashboard'),
    path('upload/', views.document_upload, name='core_document_upload'),
    path('documents/<uuid:doc_id>/', views.document_detail, name='core_document_detail'),
    path('documents/<uuid:doc_id>/sign/', views.document_sign, name='core_document_sign'),
    path('documents/<uuid:doc_id>/analyze/', views.document_analyze, name='core_document_analyze'),
    path('documents/<uuid:doc_id>/trigger/', views.trigger_create, name='core_trigger_create'),
    path('documents/<uuid:doc_id>/geofence/', views.geofence_create, name='core_geofence_create'),
    path('documents/<uuid:doc_id>/witness/', views.witness_create, name='core_witness_create'),
    path('triggers/', views.triggers_list, name='core_triggers_list'),
    path('triggers/<uuid:trigger_id>/checkin/', views.trigger_checkin, name='core_trigger_checkin'),
    path('witness/<uuid:session_id>/', views.witness_join, name='witness_join'),
    path('witness/<uuid:session_id>/complete/', views.witness_complete, name='witness_complete'),
    path('verify/', views.verify_document, name='core_verify_document'),
    path('api/docs/', views.api_docs, name='core_api_docs'),
    path('load-demo-data/', views.load_demo_data, name='core_load_demo_data'),
    path('dismiss-demo-mode/', views.dismiss_demo_mode, name='core_dismiss_demo_mode'),
    path('dismiss-onboarding/', views.dismiss_onboarding, name='core_dismiss_onboarding'),
]
