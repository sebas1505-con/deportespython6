from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('usuarios.urls')), 

]