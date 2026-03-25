from django.db import models
from django.core.exceptions import ValidationError
from datetime import date


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
    placa = models.CharField(max_length=10)
    vehiculo = models.CharField(max_length=20)

    def __str__(self):
        return f"Repartidor: {self.usuario.username}"


class Administrador(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=15)

    def __str__(self):
        return f"Admin: {self.usuario.username}"


class Sugerencia(models.Model):
    nombre = models.CharField(max_length=100, blank=True, null=True)
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sugerencia de {self.nombre or 'Anónimo'} - {self.fecha.strftime('%Y-%m-%d')}"