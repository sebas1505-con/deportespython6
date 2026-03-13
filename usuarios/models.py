from django.db import models
from django.contrib.auth.models import AbstractUser

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

    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

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
    talla = models.CharField(max_length=10)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.CharField(max_length=50)
    imagen = models.ImageField(upload_to="productos/", null=True, blank=True)

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

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad}"

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

class Movimiento(models.Model):
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE)
    tipo_movimiento = models.CharField(max_length=10, choices=[("salida", "Salida"), ("entrada", "Entrada")])
    cantidad = models.IntegerField()
    observacion = models.TextField()
    dinero_gastado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dinero_ganado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_producto_venta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    proveedor = models.ForeignKey("Proveedor", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.tipo_movimiento} - {self.cantidad}"

class Proveedor(models.Model):
    fecha_registro = models.DateField(null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    direccion = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Proveedor {self.id}"
