from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.http import JsonResponse
from django.views.static import serve
import os

def health_check(request):
    from django.db import connection
    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False
    return JsonResponse({'status': 'ok', 'db': db_ok, 'app': 'Deportes360'})

def handler404_view(request, exception):
    from django.shortcuts import render
    return render(request, 'PaginaNo.html', status=404)

def handler500_view(request):
    from django.shortcuts import render
    return render(request, 'PaginaNo.html', status=500)

handler404 = handler404_view
handler500 = handler500_view

def serve_video(request, filename):
    video_dir = os.path.join(settings.BASE_DIR, 'static', 'videos')
    return serve(request, filename, document_root=video_dir)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health'),
    path('static/videos/<str:filename>', serve_video, name='serve_video'),
    path('', include('usuarios.urls')),
    path('', include('inventario.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
