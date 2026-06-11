from django.db import models

class Usuario(models.Model):
    ROLES = [
        ('CLIENTE', 'Cliente'),
        ('REPARTIDOR', 'Repartidor'),
        ('ADMIN', 'Administrador'),
    ]
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    password = models.CharField(max_length=128)
    rol = models.CharField(max_length=15, choices=ROLES)
    telefono = models.CharField(max_length=20)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    barrio = models.CharField(max_length=50, null=True, blank=True)
    tipo_documento = models.CharField(max_length=5, null=True, blank=True)
    cedula = models.CharField(max_length=20, unique=True, null=True, blank=True)
    localidad = models.CharField(max_length=50, null=True, blank=True)
    token_recuperacion = models.CharField(max_length=100, null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.username


class Cliente(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    direccion = models.CharField(max_length=100)

    def __str__(self):
        return f"Cliente: {self.usuario.username}"

class Repartidor(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    placa = models.CharField(max_length=10, blank=True, null=True)
    vehiculo = models.CharField(max_length=20)

    def __str__(self):
        return f"Repartidor: {self.usuario.username}"


class Administrador(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=15)

    def __str__(self):
        return f"Admin: {self.usuario.username}"


class NotificacionRepartidor(models.Model):
    """Modelo para registros de repartidores pendientes de aprobación"""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ]
    
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='notificacion_repartidor')
    vehiculo = models.CharField(max_length=20)
    placa = models.CharField(max_length=10, blank=True, null=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"Notificación - {self.usuario.username} ({self.estado})"
    
    class Meta:
        ordering = ['-fecha_solicitud']




class Asignacion(models.Model):
    venta = models.ForeignKey('inventario.Venta', on_delete=models.CASCADE)
    repartidor = models.ForeignKey(
        'Repartidor',
        on_delete=models.CASCADE,
        related_name="usuarios_asignaciones"  
    )
    estado = models.CharField(max_length=20, default="pendiente")
   

