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
<<<<<<< HEAD
=======
    path('productos/', views.productos, name='productos'),
    path('pedidos/disponibles/', views.pedidos_disponibles, name='pedidos_disponibles'),
    path('pedidos/tomar/<int:pedido_id>/', views.tomar_pedido, name='tomar_pedido'),
    path('pedidos/mis-pedidos/', views.mis_pedidos, name='mis_pedidos'),
    path('pedidos/entregar/<int:pedido_id>/', views.entregar_pedido, name='entregar_pedido'),
>>>>>>> db314d50cd58dd5270c04317f8f98067ca62c3f0
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
<<<<<<< HEAD
    path('tomar_pedido/<int:id>/', views.tomar_pedido, name='tomar_pedido'),
=======
    path("producto/<int:id>/", views.detalle_producto, name="detalle_producto"),
    path('agregar-carrito/<int:id>/', views.agregar_al_carrito, name='agregar_carrito'),
>>>>>>> db314d50cd58dd5270c04317f8f98067ca62c3f0

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)