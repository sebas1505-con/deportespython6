from django.urls import path
from . import views
from .views import stock_insuficiente

urlpatterns = [
    path('catalogo/', views.catalogo, name='catalogo'),
    path('pedidos/', views.pedidos, name='pedidos'),
    path('productos/', views.productos, name='productos'),
    path('producto/<int:id>/', views.detalle_producto, name='detalle_producto'),
    path('inventario/', views.inventario, name='inventario'),
    path('producto-nuevo/', views.producto_nuevo, name='producto_nuevo'),
    path('producto-editar/<int:id>/', views.producto_editar, name='producto_editar'),
    path('producto-eliminar/<int:id>/', views.producto_eliminar, name='producto_eliminar'),
    path('movimientos/', views.registrar_movimiento, name='movimientos'),
    path('carrito/', views.carrito, name='carrito'),
    path('agregar-carrito/<int:id>/', views.agregar_al_carrito, name='agregar_carrito'),
    path('formulario_compra/', views.formulario_compra, name='formulario_compra'),
    path('factura/', views.factura, name='factura'),
    path('factura/pdf/', views.generar_factura, name='factura_pdf'),
    path('generar-pdf/', views.generar_pdf, name='generar_pdf'),
    path('reportes-ventas/', views.reportesVentas, name='reportesVentas'),
    path('stock-insuficiente/<int:producto_id>/<str:talla>/<int:stock_disponible>/',
         views.stock_insuficiente, name='stock_insuficiente'),
]