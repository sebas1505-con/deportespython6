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
    stock_total = models.IntegerField(default=0) 
    descontinuado = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class TallaProducto(models.Model):
    TALLAS = [
        # Adulto
        ('S',  'S'),
        ('M',  'M'),
        ('L',  'L'),
        ('XL', 'XL'),
        # Niño por talla numérica
        ('6',  'Talla 6'),
        ('8',  'Talla 8'),
        ('10', 'Talla 10'),
        ('12', 'Talla 12'),
        ('14', 'Talla 14'),
        ('16', 'Talla 16'),
        ('18', 'Talla 18'),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='tallas')
    talla    = models.CharField(max_length=5, choices=TALLAS)
    stock    = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.producto.nombre} — Talla {self.talla}"


class Inventario(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    stock = models.IntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    estado_producto = models.TextField()

    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

class Movimiento(models.Model):
    producto = models.ForeignKey(
        Producto,
        on_delete=models.SET_NULL,   # ← antes era CASCADE
        null=True, blank=True        # ← agregar esto
    )
    talla           = models.CharField(max_length=5)
    nombre_producto = models.CharField(max_length=100, blank=True)  # ← nuevo campo para guardar el nombre
    tipo_movimiento = models.CharField(
        max_length=10,
        choices=[("entrada", "Entrada"), ("salida", "Salida")],
        default="entrada"
    )
    cantidad  = models.IntegerField()
    motivo    = models.TextField(blank=True, null=True)
    proveedor = models.CharField(max_length=100, blank=True, default='')
    fecha     = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.producto and not self.nombre_producto:
            self.nombre_producto = self.producto.nombre

        talla_producto, _ = TallaProducto.objects.get_or_create(
            producto=self.producto,
            talla=self.talla,
            defaults={'stock': 0}
        )
        if self.tipo_movimiento == "entrada":
            talla_producto.stock += self.cantidad
        elif self.tipo_movimiento == "salida":
            talla_producto.stock -= self.cantidad
        talla_producto.save()

        # Recalcular stock_total sumando todas las tallas
        if self.producto:
            total = self.producto.tallas.aggregate(
                t=models.Sum('stock')
            )['t'] or 0
            Producto.objects.filter(pk=self.producto.pk).update(stock_total=total)

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

class Sugerencia(models.Model):

    nombre  = models.CharField(max_length=100)
    correo  = models.EmailField(blank=True, default='')
    mensaje = models.TextField()
    fecha   = models.DateTimeField(auto_now_add=True)

class RespuestaSugerencia(models.Model):
    sugerencia = models.ForeignKey(
        Sugerencia,
        on_delete=models.CASCADE,
        related_name='respuestas'
    )
    mensaje = models.TextField()
    es_admin = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Respuesta a sugerencia {self.sugerencia.id}"

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
    valor_domicilio = models.DecimalField(max_digits=10, decimal_places=2, default=5000)

    def __str__(self):
        return f"Pedido {self.id} - {self.producto}"
