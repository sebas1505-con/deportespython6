from django.urls import path
from . import views

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
    path('restablecer/', views.restablecer_password, name='restablecer'),
    path('sugerencias/', views.sugerencias, name='sugerencias'),
    path('recuperar-contraseña/', views.recuperar_contraseña, name='recuperar_contraseña'),
    path('productos/', views.productos, name='productos'),
    path('pedidos/', views.pedidos, name='pedidos'),
    path('inventario/', views.inventario, name='inventario'),
    path('crear-admin/', views.crear_admin, name='crear_admin'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('admin/', views.panel_admin, name='admin'),
    path('detalle-pedido/', views.detalle_pedido, name='detalle_pedido'),
    path('carrito/', views.carrito, name='carrito'),
]
