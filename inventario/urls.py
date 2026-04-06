from django.urls import path, include
from . import views

urlpatterns = [
    path('pse/', views.pse, name='pse'),
    path("registrar_pse/", views.registrar_pse, name="registrar_pse"),
    path('confirmar_compra', views.confirmar_compra, name='confirmar_compra'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('catalogo/<str:categoria>/', views.catalogo_categoria, name='catalogo_categoria'),
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
    path('factura/<int:venta_id>/', views.factura, name='factura'),
    path('factura1/<int:venta_id>/', views.factura1, name='factura1'),
    path('factura_pdf/<int:venta_id>/', views.generar_factura, name='factura_pdf'),
    path('generar-pdf/', views.generar_pdf, name='generar_pdf'),
    path('reportes-ventas/', views.reportesVentas, name='reportesVentas'),
    path('mis-compras/', views.mis_compras, name='mis_compras'),
    path('validar-pago/', views.validar_pse, name='validar_pse'),
    path(
        'stock-insuficiente/<int:producto_id>/<str:talla>/<int:stock_disponible>/',
        views.stock_insuficiente,
        name='stock_insuficiente'
    ),
    path('carga-masiva/', views.carga_masiva_productos, name='carga_masiva'),
]


