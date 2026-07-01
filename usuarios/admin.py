from django.contrib import admin
from .models import (
    Usuario, Cliente, Repartidor, Administrador,
    NotificacionRepartidor, Asignacion, MensajeRepartidor,
)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'rol', 'is_active', 'is_staff')
    list_filter = ('rol', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'cedula')


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'direccion')
    search_fields = ('usuario__username', 'usuario__email')


@admin.register(Repartidor)
class RepartidorAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'vehiculo', 'placa')
    search_fields = ('usuario__username',)


@admin.register(NotificacionRepartidor)
class NotificacionRepartidorAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'estado', 'fecha_solicitud', 'fecha_respuesta')
    list_filter = ('estado',)
    search_fields = ('usuario__username',)


admin.site.register(Administrador)
admin.site.register(Asignacion)
admin.site.register(MensajeRepartidor)
