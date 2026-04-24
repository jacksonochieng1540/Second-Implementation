from django.urls import path
from . import views

urlpatterns = [
    path('register-face/', views.register_face, name='register_face'),
    path('face-login/', views.face_login, name='face_login'),
]