from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from datetime import date

class Producto(models.Model):
    CATEGORIAS = [
        ("HOMBRE", "Hombre"),
        ("MUJER", "Mujer"),
        ("MIXTO", "Mixto"),
    ]

    nombre = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.TextField()
    imagen = models.ImageField(upload_to='productos/')
    categoria = models.CharField(max_length=10, choices=CATEGORIAS, default="MIXTO")

    @property
    def stock_total(self):
        return sum(t.stock for t in self.tallas.all())

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class TallaProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='tallas')
    talla = models.CharField(max_length=5)
    stock = models.IntegerField()

    def __str__(self):
        return f"{self.producto.nombre} - {self.talla}"


class Inventario(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    stock = models.IntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    estado_producto = models.TextField()

    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

class Movimiento(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    talla = models.CharField(max_length=5)
    cantidad = models.IntegerField()
    fecha = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        talla_producto, _ = TallaProducto.objects.get_or_create(
            producto=self.producto,
            talla=self.talla,
            defaults={'stock': 0}
        )
        talla_producto.stock += self.cantidad
        talla_producto.save()
        super().save(*args, **kwargs)


class Proveedor(models.Model):
    fecha_registro = models.DateField(null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    direccion = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Proveedor {self.id}"


class Venta(models.Model):
    cliente = models.ForeignKey('usuarios.Cliente', on_delete=models.CASCADE, related_name='inventario_ventas')
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
    talla = models.CharField(max_length=5)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha_inicio_descuento = models.DateField(null=True, blank=True)
    fecha_fin_descuento = models.DateField(null=True, blank=True)


class Envio(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE)
    repartidor = models.ForeignKey('usuarios.Repartidor', on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, default="Pendiente")
    fecha_envio = models.DateField()
    metodo_envio = models.CharField(max_length=25)

    def __str__(self):
        return f"Envio {self.id} - {self.estado}"


class Asignacion(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='inventario_asignaciones')
    repartidor = models.ForeignKey(
        'usuarios.Repartidor',
        on_delete=models.CASCADE,
        related_name="inventario_asignaciones"
    )
    estado = models.CharField(max_length=20, default="pendiente")


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


class Pedido(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, null=True, blank=True, related_name="pedidos")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=50)
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE)
    repartidor = models.ForeignKey('usuarios.Repartidor', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Pedido {self.id} - {self.producto}"
