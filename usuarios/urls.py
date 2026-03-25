from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', views.index, name='index'),
    path('quienes/', views.quienes, name='quienes'),
    path('contacto/', views.contacto, name='contacto'),
    path('login/', views.login_view, name='login'),
    path('registro/', views.registro_cliente, name='registro'),
    path('menu/', views.menu, name='menu'),
    path('crear-repartidor/', views.crear_repartidor, name='crear-repartidor'),
    path('usuario/', views.usuario, name='usuario'),
    path('sinacceso/', views.sinacceso, name='sinacceso'),
    path('repartidor/', views.repartidor, name='repartidor'),
    path('logout/', views.logout_view, name='logout'),
    path('sugerencias/', views.sugerencias, name='sugerencias'),
    path('crear-admin/', views.crear_admin, name='crear_admin'),
    path('panel-admin/', views.admin, name='panel_admin'),
    path('contactousu/', views.contactousu, name='contactousu'),
    path('paginaNo/', views.paginaNo, name='paginaNo'),
    path('actualizar/', views.actualizar_usuario, name='actualizar_usuario'),
    path('perfil/', views.perfil_usuario, name='perfil'),
    path('eliminar-usuario/<int:id>/', views.eliminar_usuario, name='eliminar_usuario'),
    path('restablecer/', views.restablecer_password, name='restablecer'),
    path('nueva_contrasena/<str:token>/', views.nueva_contrasena, name='nueva_contrasena'),
    path('nueva_contrasena/', views.nueva_contrasena, name='nueva_contrasena_sin_token'),
    path("prueba-correo/", views.prueba_correo),
    path('api/barrios-bogota/', views.barrios_bogota, name='api_barrios'),
    path("panel-sugerencias/", views.panel_sugerencias, name="panel_sugerencias"),
    path('tomar_pedido/<int:id>/', views.tomar_pedido, name='tomar_pedido'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)