from django.urls import path
from . import views

urlpatterns = [
    path('get-command/', views.get_command, name='get_command'),
    path('mark-executed/', views.mark_executed, name='mark_executed'),
    path('location/', views.send_location, name='send_location'),
]