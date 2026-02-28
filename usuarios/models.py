from django.db import models

class Usuario(models.Model):
    usuario = models.CharField(max_length=30, unique=True)
    correo = models.EmailField(unique=True)
    clave = models.CharField(max_length=255)
    rol = models.CharField(max_length=20)

    def __str__(self):
        return self.usuario


class Cliente(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=50)
    direccion = models.CharField(max_length=50, blank=True, null=True)
    fechaNacimiento = models.DateField(blank=True, null=True)
    barrio = models.CharField(max_length=30, blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.nombre