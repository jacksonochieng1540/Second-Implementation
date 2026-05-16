from django.urls import path
from . import views

urlpatterns = [
    
    path('latest-location/', views.get_latest_location, name='latest_location'),
    path('location-history/', views.get_location_history, name='location_history'),
    
    
    path('', views.dashboard_home, name='dashboard_home'),
    
    
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('api/immobilize/<int:vehicle_id>/', views.immobilize_engine, name='immobilize_engine'),
    path('api/enable/<int:vehicle_id>/', views.enable_engine, name='enable_engine'),
    path('api/grant-access/<int:vehicle_id>/', views.grant_emergency_access, name='grant_access'),
    path('api/location/<int:vehicle_id>/', views.get_vehicle_location_api, name='get_vehicle_location'),
]
