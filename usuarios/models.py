from django.core.exceptions import ValidationError
from datetime import date
from django.db import models
from django.utils.text import slugify


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


class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.TextField()
    imagen = models.ImageField(upload_to='productos/')

    @property
    def stock_total(self):
        return sum(t.stock for t in self.tallas.all())

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre
    
class Inventario(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    stock = models.IntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    estado_producto = models.TextField()
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.producto.nombre} - Stock: {self.stock}"

class Venta(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    cantProducto = models.IntegerField()
    metodoEnvio = models.CharField(max_length=50)
    totalVenta = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_de_pago = models.CharField(max_length=50)
    direccionEnvio = models.CharField(max_length=255)
    telefonoContacto = models.CharField(max_length=20)
    observaciones = models.TextField(null=True, blank=True)
    fecha_venta = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, default="Pendiente")

    def __str__(self):
        return f"Venta {self.id} - Cliente: {self.cliente.usuario.username}"

class DetalleVentaProductos(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fecha_inicio_descuento = models.DateField(null=True, blank=True)
    fecha_fin_descuento = models.DateField(null=True, blank=True)
    
class Movimiento(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    talla = models.CharField(max_length=5)
    cantidad = models.IntegerField()
    fecha = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        from .models import TallaProducto

        talla_producto, creado = TallaProducto.objects.get_or_create(
            producto=self.producto,
            talla=self.talla,
            defaults={'stock': 0}
        )

        talla_producto.stock += self.cantidad
        talla_producto.save()

        super().save(*args, **kwargs)
    
class Envio(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE)
    repartidor = models.ForeignKey(Repartidor, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, default="Pendiente")
    fecha_envio = models.DateField()
    metodo_envio = models.CharField(max_length=25)

    def __str__(self):
        return f"Envio {self.id} - {self.estado}"

class Asignacion(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE)
    repartidor = models.ForeignKey(Repartidor, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, default="pendiente")

    def __str__(self):
        return f"Asignación {self.id} - {self.estado}"
   
class Proveedor(models.Model):
    fecha_registro = models.DateField(null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    direccion = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Proveedor {self.id}"
    
class Reporte(models.Model):
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    total_ventas = models.DecimalField(max_digits=10, decimal_places=2)
    total_productos_vendidos = models.IntegerField()
    
    def clean(self):
        hoy = date.today()

        if self.fecha_inicio < hoy:
            raise ValidationError("La fecha de inicio no puede ser anterior a hoy")

        if self.fecha_fin < hoy:
            raise ValidationError("La fecha de fin no puede ser anterior a hoy")

        if self.fecha_fin < self.fecha_inicio:
            raise ValidationError("La fecha fin no puede ser menor que la fecha inicio")

    def __str__(self):
        return f"Reporte {self.id} - {self.fecha_inicio} a {self.fecha_fin}"
    
class Sugerencia(models.Model):
    nombre = models.CharField(max_length=100, blank=True, null=True)
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sugerencia de {self.nombre or 'Anónimo'} - {self.fecha.strftime('%Y-%m-%d')}"

class TallaProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='tallas')
    talla = models.CharField(max_length=5)
    stock = models.IntegerField()

    def __str__(self):
        return f"{self.producto.nombre} - {self.talla}"    

