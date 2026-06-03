from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({'status': 'ok', 'app': 'Deportes360'})

def handler404_view(request, exception):
    from django.shortcuts import render
    return render(request, 'PaginaNo.html', status=404)

def handler500_view(request):
    from django.shortcuts import render
    return render(request, 'PaginaNo.html', status=500)

handler404 = handler404_view
handler500 = handler500_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health'),
    path('', include('usuarios.urls')),
    path('', include('inventario.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
