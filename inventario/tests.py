from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.hashers import make_password
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Producto, Venta, Pedido, Sugerencia, RespuestaSugerencia
from inventario.models import (Producto, TallaProducto, Venta, Movimiento, Pedido, Sugerencia, RespuestaSugerencia, DetalleVentaProductos, Reporte)
from usuarios.models import Usuario, Cliente, Repartidor
import json

# =========================================================
# MODELOS
# =========================================================

def agregar_al_carrito(request, producto_id):

    producto = get_object_or_404(
        Producto,
        id=producto_id
    )

    carrito = request.session.get('carrito', [])

    carrito.append(producto.id)

    request.session['carrito'] = carrito

    return redirect('catalogo')


def generar_factura(request, venta_id):

    venta = get_object_or_404(
        Venta,
        id=venta_id
    )

    response = HttpResponse(
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        f'attachment; filename="factura_{venta.id}.pdf"'
    )

    response.write("Factura PDF")

    return response


def producto_discontinuar(request, producto_id):

    producto = get_object_or_404(
        Producto,
        id=producto_id
    )

    producto.discontinuado = True
    producto.save()

    return redirect('catalogo')


def pedidos(request):

    pedidos = Pedido.objects.all()

    return render(
        request,
        'usuarios/pedidos.html',
        {'pedidos': pedidos}
    )

class ProductoModelTest(TestCase):

    def setUp(self):
        self.producto = Producto.objects.create(
            nombre="Nike",
            precio=100000,
            descripcion="Producto test",
            categoria="FUTBOL"
        )

    def test_producto_str(self):
        self.assertEqual(str(self.producto), "Nike")

    def test_producto_precio(self):
        self.assertEqual(self.producto.precio, 100000)

    def test_producto_categoria(self):
        self.assertEqual(self.producto.categoria, "FUTBOL")

    def test_producto_descontinuado_false(self):
        self.assertFalse(self.producto.descontinuado)

    def test_producto_save(self):
        self.assertTrue(Producto.objects.filter(nombre="Nike").exists())


class TallaProductoModelTest(TestCase):

    def setUp(self):
        self.producto = Producto.objects.create(
            nombre="Adidas",
            precio=100
        )

        self.talla = TallaProducto.objects.create(
            producto=self.producto,
            talla="M",
            stock=10
        )

    def test_talla_stock(self):
        self.assertEqual(self.talla.stock, 10)

    def test_talla_producto(self):
        self.assertEqual(self.talla.producto.nombre, "Adidas")


class MovimientoModelTest(TestCase):

    def setUp(self):
        self.producto = Producto.objects.create(
            nombre="Puma",
            precio=100
        )

    def test_movimiento_entrada(self):
        Movimiento.objects.create(
            producto=self.producto,
            talla="M",
            tipo_movimiento="entrada",
            cantidad=5
        )

        self.assertEqual(Movimiento.objects.count(), 1)

    def test_movimiento_salida(self):
        Movimiento.objects.create(
            producto=self.producto,
            talla="L",
            tipo_movimiento="salida",
            cantidad=2
        )

        self.assertEqual(Movimiento.objects.count(), 1)


class UsuarioModelTest(TestCase):

    def setUp(self):
        self.usuario = Usuario.objects.create(
            username="juan",
            password=make_password("123")
        )

    def test_usuario_str(self):
        self.assertEqual(str(self.usuario), "juan")


class ClienteModelTest(TestCase):

    def setUp(self):
        self.usuario = Usuario.objects.create(
            username="cliente"
        )

        self.cliente = Cliente.objects.create(
            usuario=self.usuario
        )

    def test_cliente_usuario(self):
        self.assertEqual(self.cliente.usuario.username, "cliente")


class PedidoModelTest(TestCase):

    def setUp(self):
        self.usuario = Usuario.objects.create(username="juan")

        self.producto = Producto.objects.create(
            nombre="Balon",
            precio=100
        )

        self.pedido = Pedido.objects.create(
            producto=self.producto,
            cantidad=2,
            total=200,
            estado="Disponible",
            usuario=self.usuario
        )

    def test_pedido_estado(self):
        self.assertEqual(self.pedido.estado, "Disponible")

    def test_pedido_total(self):
        self.assertEqual(self.pedido.total, 200)


# =========================================================
# VIEWS
# =========================================================

class CatalogoViewTest(TestCase):

    def setUp(self):
        self.client = Client()

        Producto.objects.create(
            nombre="Nike",
            precio=100,
            descontinuado=False
        )

    def test_catalogo_status(self):
        response = self.client.get(reverse('catalogo'))
        self.assertEqual(response.status_code, 200)

    def test_catalogo_template(self):
        response = self.client.get(reverse('catalogo'))
        self.assertTemplateUsed(response, 'catalogo.html')

    def test_catalogo_context(self):
        response = self.client.get(reverse('catalogo'))
        self.assertIn('productos', response.context)

    def test_catalogo_filtra_descontinuados(self):

        Producto.objects.create(
            nombre="Oculto",
            precio=100,
            descontinuado=True
        )

        response = self.client.get(reverse('catalogo'))

        productos = response.context['productos']

        self.assertEqual(productos.count(), 1)


class ProductosViewTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.producto = Producto.objects.create(
            nombre="Guayos",
            precio=100
        )

    def test_productos_status(self):
        response = self.client.get(reverse('productos'))
        self.assertEqual(response.status_code, 200)

    def test_detalle_producto_status(self):
        response = self.client.get(
            reverse('detalle_producto', args=[self.producto.id])
        )

        self.assertEqual(response.status_code, 200)

    def test_detalle_producto_404(self):
        response = self.client.get(
            reverse('detalle_producto', args=[999])
        )

        self.assertEqual(response.status_code, 404)

    def test_productos_template(self):
        response = self.client.get(reverse('productos'))
        self.assertTemplateUsed(response, 'productos/productos.html')


# =========================================================
# CARRITO
# =========================================================

class CarritoTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.producto = Producto.objects.create(
            nombre="Balón",
            precio=50000
        )

    def test_carrito_status(self):
        response = self.client.get(reverse('carrito'))
        self.assertEqual(response.status_code, 200)

    def test_agregar_al_carrito(self):

        self.client.post(
            reverse('agregar_al_carrito', args=[self.producto.id]),
            {'talla': 'M'}
        )

        carrito = self.client.session['carrito']

        self.assertEqual(len(carrito), 1)

    def test_vaciar_carrito(self):

        session = self.client.session

        session['carrito'] = {
            '1_M': {
                'nombre': 'Balón',
                'precio': 100,
                'cantidad': 1,
                'talla': 'M'
            }
        }

        session.save()

        self.client.post(reverse('carrito'), {
            'vaciar': '1'
        })

        session = self.client.session

        self.assertEqual(session['carrito'], {})

    def test_eliminar_producto_carrito(self):

        session = self.client.session

        session['carrito'] = {
            '1_M': {
                'nombre': 'Balón',
                'precio': 100,
                'cantidad': 1,
                'talla': 'M'
            }
        }

        session.save()

        self.client.post(reverse('carrito'), {
            'eliminar': '1_M'
        })

        session = self.client.session

        self.assertEqual(session['carrito'], {})


# =========================================================
# COMPRA
# =========================================================

class CompraTest(TestCase):

    def setUp(self):

        self.client = Client()

        self.usuario = Usuario.objects.create(
            username="juan",
            password=make_password("123")
        )

        self.cliente_user = Cliente.objects.create(
            usuario=self.usuario
        )

        session = self.client.session
        session['usuario_id'] = self.usuario.id
        session['carrito'] = {}
        session.save()

    def test_formulario_compra_status(self):

        response = self.client.get(
            reverse('formulario_compra')
        )

        self.assertEqual(response.status_code, 200)

    def test_pse_status(self):

        session = self.client.session

        session['compra'] = {
            'total_venta': 1000,
            'cantidad_total': 1
        }

        session.save()

        response = self.client.get(reverse('pse'))

        self.assertEqual(response.status_code, 200)

    def test_confirmar_compra_redirect(self):

        response = self.client.post(
            reverse('confirmar_compra')
        )

        self.assertEqual(response.status_code, 302)


# =========================================================
# FACTURA
# =========================================================

class FacturaTest(TestCase):

    def setUp(self):

        self.client = Client()

        usuario = Usuario.objects.create(username="juan")

        cliente = Cliente.objects.create(usuario=usuario)

        self.venta = Venta.objects.create(
            cliente=cliente,
            cantProducto=1,
            totalVenta=1000
        )

    def test_factura_status(self):

        response = self.client.get(
            reverse('factura', args=[self.venta.id])
        )

        self.assertEqual(response.status_code, 200)

    def test_factura1_status(self):

        response = self.client.get(
            reverse('factura1', args=[self.venta.id])
        )

        self.assertEqual(response.status_code, 200)

    def test_generar_factura_pdf(self):

        response = self.client.get(
            reverse('generar_factura', args=[self.venta.id])
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response['Content-Type'],
            'application/pdf'
        )


# =========================================================
# PDF Y EXCEL
# =========================================================

class ExportacionesTest(TestCase):

    def setUp(self):
        self.client = Client()

    def test_exportar_excel(self):

        response = self.client.get(
            reverse('exportar_excel')
        )

        self.assertEqual(response.status_code, 200)

    def test_generar_pdf(self):

        response = self.client.get(
            reverse('generar_pdf')
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response['Content-Type'],
            'application/pdf'
        )


# =========================================================
# INVENTARIO
# =========================================================

class InventarioTest(TestCase):

    def setUp(self):

        self.client = Client()

        self.producto = Producto.objects.create(
            nombre="Adidas",
            precio=100
        )

    def test_inventario_status(self):

        response = self.client.get(
            reverse('inventario')
        )

        self.assertEqual(response.status_code, 200)

    def test_producto_eliminar(self):

        response = self.client.get(
            reverse('producto_eliminar', args=[self.producto.id])
        )

        self.assertEqual(response.status_code, 302)

    def test_producto_reactivar(self):

        self.producto.descontinuado = True
        self.producto.save()

        response = self.client.post(
            reverse('producto_reactivar', args=[self.producto.id])
        )

        self.assertEqual(response.status_code, 302)

    def test_producto_discontinuar(self):

        response = self.client.post(
            reverse('producto_discontinuar', args=[self.producto.id])
        )

        self.assertEqual(response.status_code, 302)


# =========================================================
# SUGERENCIAS
# =========================================================

class SugerenciasTest(TestCase):

    def setUp(self):

        self.client = Client()

        self.sugerencia = Sugerencia.objects.create(
            nombre="Juan",
            mensaje="Hola"
        )

    def test_sugerencias_lista(self):

        response = self.client.get(
            reverse('sugerencias_lista')
        )

        self.assertEqual(response.status_code, 200)

    def test_responder_sugerencia(self):

        response = self.client.post(
            reverse('responder_sugerencia',
            args=[self.sugerencia.id]),
            {'mensaje': 'Respuesta'}
        )

        self.assertEqual(response.status_code, 200)

    def test_sugerencia_respuestas(self):

        response = self.client.get(
            reverse('sugerencia_respuestas',
            args=[self.sugerencia.id])
        )

        self.assertEqual(response.status_code, 200)


# =========================================================
# PEDIDOS
# =========================================================

class PedidosTest(TestCase):

    def setUp(self):

        self.client = Client()

        self.usuario = Usuario.objects.create(
            username="repartidor"
        )

        self.repartidor = Repartidor.objects.create(
            usuario=self.usuario
        )

        self.producto = Producto.objects.create(
            nombre="Balón",
            precio=100
        )

        self.pedido = Pedido.objects.create(
            producto=self.producto,
            cantidad=1,
            total=100,
            estado='Disponible',
            usuario=self.usuario
        )

        session = self.client.session
        session['usuario_id'] = self.usuario.id
        session.save()

    def test_pedidos_disponibles(self):

        response = self.client.get(
            reverse('pedidos_disponibles')
        )

        self.assertEqual(response.status_code, 200)

    def test_tomar_pedido(self):

        response = self.client.get(
            reverse('tomar_pedido',
            args=[self.pedido.id])
        )

        self.assertEqual(response.status_code, 302)

    def test_mis_pedidos(self):

        response = self.client.get(
            reverse('mis_pedidos')
        )

        self.assertEqual(response.status_code, 200)


# =========================================================
# REPORTES
# =========================================================

class ReportesTest(TestCase):

    def setUp(self):

        self.client = Client()

    def test_reportes_admin(self):

        response = self.client.get(
            reverse('reportes_admin')
        )

        self.assertEqual(response.status_code, 200)

    def test_reportes_ventas(self):

        response = self.client.get(
            reverse('reportesVentas')
        )

        self.assertEqual(response.status_code, 200)


# =========================================================
# VALIDAR PSE
# =========================================================

class ValidarPseTest(TestCase):

    def setUp(self):

        self.client = Client()

        self.usuario = Usuario.objects.create(
            username="juan",
            password=make_password("123")
        )

        session = self.client.session
        session['usuario_id'] = self.usuario.id
        session.save()

    def test_validar_pse_password_correcta(self):

        response = self.client.post(
            reverse('validar_pse'),
            data=json.dumps({
                'password': '123'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

    def test_validar_pse_password_incorrecta(self):

        response = self.client.post(
            reverse('validar_pse'),
            data=json.dumps({
                'password': 'incorrecta'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)


# =========================================================
# ADMIN
# =========================================================

class PanelAdminTest(TestCase):

    def setUp(self):

        session = self.client.session
        session['usuario_id'] = 1
        session['rol'] = 'ADMIN'
        session.save()

    def test_panel_admin_status(self):

        response = self.client.get(
            reverse('panel_admin')
        )

        self.assertEqual(response.status_code, 200)

    def test_panel_admin_template(self):

        response = self.client.get(
            reverse('panel_admin')
        )

        self.assertTemplateUsed(
            response,
            'productos/admin.html'
        )


# =========================================================
# MOVIMIENTOS VIEW
# =========================================================

class MovimientoViewsTest(TestCase):

    def setUp(self):

        self.client = Client()

        self.producto = Producto.objects.create(
            nombre="Nike",
            precio=100
        )

    def test_movimiento_nuevo_get(self):

        response = self.client.get(
            reverse('movimiento_nuevo')
        )

        self.assertEqual(response.status_code, 200)

    def test_movimientos_view(self):

        response = self.client.get(
            reverse('movimientos',
            args=[self.producto.id])
        )

        self.assertEqual(response.status_code, 200)


# =========================================================
# EXTRA TESTS
# =========================================================

class ExtraTests(TestCase):

    def setUp(self):

        self.client = Client()

    def test_catalogo_categoria(self):

        response = self.client.get('/catalogo/FUTBOL/')

        self.assertIn(response.status_code, [200, 404])

    def test_pedidos_view(self):

        response = self.client.get(
            reverse('pedidos')
        )

        self.assertEqual(response.status_code, 200)

    def test_stock_insuficiente(self):

        producto = Producto.objects.create(
            nombre="Nike",
            precio=100
        )

        response = self.client.get(
            reverse(
                'stock_insuficiente',
                args=[producto.id, 'M', 2]
            )
        )

        self.assertEqual(response.status_code, 200)