from django.contrib import admin
from .models import (
    Venta, DetalleVentaProductos, Envio,
    Producto, TallaProducto, Movimiento,
    Proveedor, Reporte, Pedido, ResenaVenta,
    Sugerencia, RespuestaSugerencia, Asignacion,
)


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'cliente', 'fecha_venta', 'estado',
        'cantProducto', 'totalVenta', 'metodo_de_pago', 'metodoEnvio',
    )
    list_filter = ('estado', 'metodo_de_pago', 'metodoEnvio', 'fecha_venta')
    search_fields = ('cliente__usuario__username', 'cliente__usuario__email', 'id')
    ordering = ('-fecha_venta',)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'precio', 'categoria', 'stock_total', 'descontinuado')
    list_filter = ('categoria', 'descontinuado')
    search_fields = ('nombre',)

    def delete_model(self, request, obj):
        if DetalleVentaProductos.objects.filter(producto=obj).exists():
            self.message_user(
                request,
                f'No se puede eliminar "{obj.nombre}" porque está asociado a una o más ventas registradas.',
                level='error',
            )
            return
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        con_ventas = [
            p.nombre for p in queryset
            if DetalleVentaProductos.objects.filter(producto=p).exists()
        ]
        if con_ventas:
            self.message_user(
                request,
                f'No se pueden eliminar los siguientes productos porque tienen ventas: {", ".join(con_ventas)}.',
                level='error',
            )
            return
        super().delete_queryset(request, queryset)


@admin.register(TallaProducto)
class TallaProductoAdmin(admin.ModelAdmin):
    list_display = ('id', 'producto', 'talla', 'stock')
    list_filter = ('talla',)
    search_fields = ('producto__nombre',)


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_producto', 'talla', 'tipo_movimiento', 'cantidad', 'fecha')
    list_filter = ('tipo_movimiento', 'fecha')
    search_fields = ('nombre_producto',)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'producto', 'cantidad', 'total', 'estado', 'fecha_pedido', 'usuario')
    list_filter = ('estado',)
    search_fields = ('usuario__username', 'producto__nombre')


@admin.register(ResenaVenta)
class ResenaVentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'venta', 'estado_llegada', 'fecha')
    list_filter = ('estado_llegada',)


@admin.register(Sugerencia)
class SugerenciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'correo', 'fecha')
    search_fields = ('nombre', 'correo')


admin.site.register(Proveedor)
admin.site.register(Reporte)
admin.site.register(Asignacion)
admin.site.register(RespuestaSugerencia)
