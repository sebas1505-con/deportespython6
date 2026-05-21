from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from usuarios.models import Cliente, Repartidor, Usuario
from .models import Movimiento, Pedido, Proveedor, Producto, Reporte, TallaProducto, Venta


class ProductoModelTest(TestCase):
    def test_producto_str_returns_nombre(self):
        producto = Producto.objects.create(
            nombre='Camiseta',
            precio=Decimal('100.00'),
            descripcion='Camiseta deportiva',
            imagen='productos/camiseta.jpg',
        )
        self.assertEqual(str(producto), 'Camiseta')

    def test_producto_save_generates_slug(self):
        producto = Producto.objects.create(
            nombre='Camiseta Negra',
            precio=Decimal('120.00'),
            descripcion='Camiseta negra',
            imagen='productos/camiseta_negra.jpg',
        )
        self.assertEqual(producto.slug, 'camiseta-negra')


class MovimientoModelTest(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create(
            username='usuario1',
            email='usuario1@example.com',
            first_name='Usuario',
            password='pass123',
            rol='CLIENTE',
            telefono='3001112222',
            is_active=True,
        )
        self.producto = Producto.objects.create(
            nombre='Zapatilla',
            precio=Decimal('200.00'),
            descripcion='Zapatilla deportiva',
            imagen='productos/zapatilla.jpg',
        )

    def test_movimiento_entrada_crea_talla_producto_y_actualiza_stock_total(self):
        movimiento = Movimiento.objects.create(
            producto=self.producto,
            talla='M',
            tipo_movimiento='entrada',
            cantidad=5,
            proveedor='Proveedor A',
        )
        self.assertEqual(movimiento.nombre_producto, 'Zapatilla')

        talla_producto = TallaProducto.objects.get(producto=self.producto, talla='M')
        self.assertEqual(talla_producto.stock, 5)

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_total, 5)

    def test_movimiento_salida_resta_stock_total(self):
        Movimiento.objects.create(
            producto=self.producto,
            talla='L',
            tipo_movimiento='entrada',
            cantidad=10,
            proveedor='Proveedor B',
        )
        salida = Movimiento.objects.create(
            producto=self.producto,
            talla='L',
            tipo_movimiento='salida',
            cantidad=4,
            proveedor='Proveedor B',
        )

        tamaño = TallaProducto.objects.get(producto=self.producto, talla='L')
        self.assertEqual(tamaño.stock, 6)

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_total, 6)
        self.assertEqual(salida.nombre_producto, 'Zapatilla')

    def test_movimiento_evento_no_modifica_stock_total(self):
        Movimiento.objects.create(
            producto=self.producto,
            talla='S',
            tipo_movimiento='evento',
            cantidad=0,
            proveedor='Proveedor C',
            nombre_producto='Zapatilla'
        )

        self.assertFalse(TallaProducto.objects.filter(producto=self.producto, talla='S').exists())
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_total, 0)


class OtrosModelTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create(
            username='cliente1',
            email='cliente1@example.com',
            first_name='Cliente',
            password='pass123',
            rol='CLIENTE',
            telefono='3001231234',
            is_active=True,
        )
        self.cliente = Cliente.objects.create(usuario=self.usuario, direccion='Av. Siempre Viva 742')
        self.producto = Producto.objects.create(
            nombre='Pantalón',
            precio=Decimal('150.00'),
            descripcion='Pantalón deportivo',
            imagen='productos/pantalon.jpg',
        )
        self.repartidor_usuario = Usuario.objects.create(
            username='repartidor1',
            email='repartidor1@example.com',
            first_name='Repartidor',
            password='pass123',
            rol='REPARTIDOR',
            telefono='3005556666',
            is_active=True,
        )
        self.repartidor = Repartidor.objects.create(
            usuario=self.repartidor_usuario,
            placa='ABC123',
            vehiculo='Moto'
        )

    def test_venta_str(self):
        venta = Venta.objects.create(
            cliente=self.cliente,
            cantProducto=1,
            metodoEnvio='Domicilio',
            totalVenta=Decimal('150.00'),
            metodo_de_pago='Efectivo',
            direccionEnvio='Av. Falsa 123',
            telefonoContacto='3001231234',
            observaciones='Sin observaciones',
        )
        self.assertIn('Venta', str(venta))
        self.assertIn('cliente1', str(venta))

    def test_pedido_str(self):
        venta = Venta.objects.create(
            cliente=self.cliente,
            cantProducto=2,
            metodoEnvio='Recoger',
            totalVenta=Decimal('300.00'),
            metodo_de_pago='Tarjeta',
            direccionEnvio='Av. Falsa 123',
            telefonoContacto='3001231234',
            observaciones='',
        )
        pedido = Pedido.objects.create(
            venta=venta,
            producto=self.producto,
            cantidad=2,
            total=Decimal('300.00'),
            estado='Pendiente',
            usuario=self.usuario,
            valor_domicilio=Decimal('5000.00'),
        )
        self.assertIn('Pedido', str(pedido))
        self.assertIn('Pantalón', str(pedido))

    def test_proveedor_str(self):
        proveedor = Proveedor.objects.create(
            fecha_registro=date.today(),
            telefono='3008887777',
            direccion='Calle 10'
        )
        self.assertEqual(str(proveedor), f'Proveedor {proveedor.id}')

    def test_reporte_clean_invalid_dates(self):
        hoy = date.today()
        reporte = Reporte(
            fecha_inicio=hoy,
            fecha_fin=hoy - timedelta(days=1),
            total_ventas=Decimal('0.00'),
            total_productos_vendidos=0,
        )
        with self.assertRaises(ValidationError):
            reporte.clean()
