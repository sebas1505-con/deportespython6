from django.shortcuts import render, redirect, get_object_or_404
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from .models import (Producto, TallaProducto, Venta, Movimiento,Reporte, DetalleVentaProductos, Pedido)
from .forms import CompraForm, ReportesForm, MovimientoForm
from usuarios.models import Usuario, Cliente, Repartidor
from django.contrib.auth.decorators import login_required
from reportlab.lib.styles import getSampleStyleSheet
from django.core.exceptions import ValidationError
from django.contrib import messages
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
import os
from decimal import Decimal
from rest_framework import viewsets

# ── Catálogo y productos ──────────────────────────────────────────────────────

def catalogo(request):
    categoria = request.GET.get('categoria')  # lee el parámetro de la URL
    if categoria:
        productos = Producto.objects.filter(categoria__iexact=categoria)
    else:
        productos = Producto.objects.all()

    return render(request, 'catalogo.html', {'productos': productos})

def catalogo_categoria(request, categoria):
    productos = Producto.objects.filter(categoria__iexact=categoria)
    return render(request, 'catalogo_categoria.html', {
        'productos': productos,
        'categoria': categoria
    })

def mis_compras(request):
    try:
        cliente = Cliente.objects.get(usuario=request)
        compras = Venta.objects.filter(cliente=cliente)
    except Cliente.DoesNotExist:
        compras = []

    return render(request, 'mis_compras.html', {'compras': compras})
     

def productos(request):
    productos = Producto.objects.all()
    return render(request, 'productos/productos.html', {'productos': productos})

def detalle_producto(request, id):
    producto = get_object_or_404(Producto, id=id)
    tallas = TallaProducto.objects.filter(producto=producto)
    stock_total = sum(t.stock for t in tallas)
    return render(request, 'productos/producto-detalle.html', {
        'producto': producto,
        'tallas': tallas,
        'stock_total': stock_total
    })

def producto_nuevo(request):
    if request.method == "POST":
        producto = Producto.objects.create(
            nombre=request.POST.get("nombre"),
            precio=request.POST.get("precio"),
            descripcion=request.POST.get("descripcion"),
            categoria=request.POST.get("categoria"),
            imagen=request.FILES.get("imagen"),
        )
        for talla, key in [('S', 'stock_s'), ('M', 'stock_m'), ('L', 'stock_l'), ('XL', 'stock_xl')]:
            stock = int(request.POST.get(key, 0))
            if stock > 0:
                TallaProducto.objects.create(producto=producto, talla=talla, stock=stock)
        messages.success(request, "Producto creado correctamente")
        return redirect('productos')
    return render(request, 'productos/producto_nuevo.html')

def producto_editar(request, id):
    producto = get_object_or_404(Producto, id=id)
    if request.method == "POST":
        producto.nombre      = request.POST.get("nombre")
        producto.precio      = request.POST.get("precio")
        producto.descripcion = request.POST.get("descripcion")
        producto.categoria   = request.POST.get("categoria")
        if request.FILES.get("imagen"):
            producto.imagen = request.FILES.get("imagen")
        producto.save()
        return redirect('productos')
    return render(request, 'productos/producto_editar.html', {'producto': producto})

def producto_eliminar(request, id):
    producto = get_object_or_404(Producto, id=id)
    producto.delete()
    return redirect('inventario')


# ── Inventario y movimientos ──────────────────────────────────────────────────

def inventario(request):
    productos = Producto.objects.all()
    return render(request, 'inventario.html', {'productos': productos})

def registrar_movimiento(request):
    productos = Producto.objects.all()
    if request.method == "POST":
        producto = get_object_or_404(Producto, id=request.POST.get("producto"))
        try:
            Movimiento.objects.create(
                producto=producto,
                talla=request.POST.get("talla"),
                cantidad=int(request.POST.get("cantidad")),
                tipo_movimiento=request.POST.get("tipo_movimiento"),
                proveedor=request.POST.get("proveedor", "")
            )
            messages.success(request, "Movimiento registrado correctamente")
        except ValidationError as e:
            messages.error(request, f"Error: {e.message}")
        return redirect('movimientos')
    return render(request, 'movimientos.html', {'productos': productos})


# ── Carrito ───────────────────────────────────────────────────────────────────

def carrito(request):
    carrito = request.session.get('carrito', {})

    if request.method == 'POST':

        if 'eliminar' in request.POST:
            carrito.pop(request.POST.get('eliminar'), None)
            request.session['carrito'] = carrito

        elif 'vaciar' in request.POST:
            carrito.clear()
            request.session['carrito'] = carrito

        elif 'accion' in request.POST:
            accion = request.POST.get('accion')

            if accion.startswith('aumentar_'):
                key = accion.replace('aumentar_', '')
                if key in carrito:
                    carrito[key]['cantidad'] += 1

            elif accion.startswith('disminuir_'):
                key = accion.replace('disminuir_', '')
                if key in carrito:
                    carrito[key]['cantidad'] -= 1
                    if carrito[key]['cantidad'] <= 0:
                        carrito.pop(key)

            request.session['carrito'] = carrito

        elif 'finalizar' in request.POST:

            for key, item in carrito.items():
                producto_id = int(key.split('_')[0])
                talla = item['talla']

                producto = get_object_or_404(Producto, id=producto_id)
                talla_obj = get_object_or_404(TallaProducto, producto=producto, talla=talla)

                if item['cantidad'] > talla_obj.stock:
                    return render(request, 'stock_insuficiente.html', {
                        'producto_nombre': producto.nombre,
                        'talla': talla,
                        'stock_disponible': talla_obj.stock
                    })

            return redirect('formulario_compra')
    total = sum(item['precio'] * item['cantidad'] for item in carrito.values())

    return render(request, 'productos/carrito.html', {
        'productos': carrito,
        'total': total
    })

def agregar_al_carrito(request, id):
    carrito = request.session.get('carrito', {})
    producto = get_object_or_404(Producto, id=id)
    if request.method == 'POST':
        talla = request.POST.get('talla')
        key = f"{id}_{talla}"
        if key in carrito:
            carrito[key]['cantidad'] += 1
        else:
            carrito[key] = {
                'nombre': producto.nombre,
                'precio': float(producto.precio),
                'imagen': producto.imagen.url if producto.imagen else '',
                'talla': talla,
                'cantidad': 1
            }
        request.session['carrito'] = carrito
    return redirect('carrito')


# ── Compra y factura ──────────────────────────────────────────────────────────

def formulario_compra(request):
    carrito = request.session.get('carrito', {})
    cantidad_total = sum(item['cantidad'] for item in carrito.values())
    total_venta    = sum(item['precio'] * item['cantidad'] for item in carrito.values())

    usuario_id = request.session.get('usuario_id')
    usuario    = Usuario.objects.get(id=usuario_id) if usuario_id else None
    cliente    = Cliente.objects.get(usuario=usuario) if usuario else None

    if request.method == 'POST':
        form = CompraForm(request.POST)

        if form.is_valid():
            metodo_pago = form.cleaned_data['metodo_pago']

            # Guardar datos en sesión
            request.session['compra'] = {
                'carrito': carrito,
                'cantidad_total': cantidad_total,
                'total_venta': total_venta,
                'metodo_envio': form.cleaned_data['metodo_envio'],
                'metodo_pago': metodo_pago,
                'direccion_envio': form.cleaned_data['direccion_envio'],
                'telefono_contacto': form.cleaned_data['telefono_contacto'],
                'observaciones': form.cleaned_data.get('observaciones', ''),
            }

            # 🔥 Flujo según método de pago
            if metodo_pago == 'PAGO_EN_LINEA':
                # Redirige al flujo PSE
                return redirect('pse')

            else:  # CONTRA_ENTREGA
                # Guardar la venta en BD
                venta = Venta.objects.create(
                    cliente=cliente,
                    cantProducto=cantidad_total,
                    metodoEnvio=form.cleaned_data['metodo_envio'],
                    totalVenta=total_venta,
                    metodo_de_pago='CONTRA_ENTREGA',
                    direccionEnvio=form.cleaned_data['direccion_envio'],
                    telefonoContacto=form.cleaned_data['telefono_contacto'],
                    observaciones=form.cleaned_data.get('observaciones', '')
                )

                # Crear pedidos y actualizar stock
                for key, item in carrito.items():
                    producto_id = key.split('_')[0]
                    producto = Producto.objects.get(id=int(producto_id))
                    Pedido.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=item['cantidad'],
                        total=item['precio'] * item['cantidad'],
                        estado="Pendiente",
                        usuario=usuario
                    )

                    talla = item['talla']
                    talla_obj = TallaProducto.objects.get(producto=producto, talla=talla)
                    talla_obj.stock -= item['cantidad']
                    talla_obj.save()

                # Limpiar carrito
                request.session['carrito'] = {}
                return redirect('factura', venta_id=venta.id)

    else:
        form = CompraForm(initial={
            'cant_producto': cantidad_total,
            'total_venta': total_venta,
            'metodo_pago': 'CONTRA_ENTREGA'
        })

    return render(request, 'productos/formulario_compra.html', {
        'form': form,
        'cliente': cliente,
        'productos': carrito,
        'total': total_venta
    })

def registrar_pse(request):
    if request.method == "POST":
        usuario_id = request.session.get('usuario_id')
        usuario = Usuario.objects.get(id=usuario_id)
        cliente = Cliente.objects.get(usuario=usuario)

        # Normalizar el totalVenta
        total_str = request.POST.get("totalVenta", "0").replace(",", ".")
        total_decimal = Decimal(total_str)

        venta = Venta.objects.create(
            cliente=cliente,
            cantProducto=request.POST.get("cantProducto"),
            metodoEnvio=request.POST.get("metodoEnvio"),
            totalVenta=total_decimal,
            metodo_de_pago=request.POST.get("metodo_de_pago"),
            direccionEnvio=request.POST.get("direccionEnvio"),
            telefonoContacto=request.POST.get("telefonoContacto"),
            observaciones=request.POST.get("observaciones")
        )

        # Crear detalles desde el carrito
        carrito = request.session.get("carrito", {})
        for key, item in carrito.items():
            producto_id = key.split("_")[0]
            producto = Producto.objects.get(id=int(producto_id))
            DetalleVentaProductos.objects.create(
                venta=venta,
                producto=producto,
                talla=item["talla"],
                cantidad=item["cantidad"],
                precio_unitario=item["precio"],
                subtotal=item["precio"] * item["cantidad"]
            )

        # limpiar carrito
        request.session["carrito"] = {}

        return redirect("factura", venta_id=venta.id)


def pse(request):
    compra = request.session.get('compra')

    if not compra:
        return redirect('carrito')

    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.get(id=usuario_id)
    cliente = Cliente.objects.get(usuario=usuario)

    return render(request, 'productos/pse.html', {
        'total': compra['total_venta'],
        'cantidad_total': compra['cantidad_total'],
        'cliente': cliente,
        'compra': compra,
        'venta_ref': '123456'  # puedes hacerlo dinámico
    })

def confirmar_compra(request):
    if request.method == 'POST':
        compra = request.session.get('compra')

        if not compra:
            return redirect('carrito')

        # 👉 AQUÍ puedes guardar la venta en BD (luego lo hacemos pro)

        # limpiar carrito
        request.session['carrito'] = {}
        request.session['compra'] = {}

        return redirect('carrito')  # o donde quieras

    return redirect('carrito')

def stock_insuficiente(request, producto_id, talla, stock_disponible):
    producto = get_object_or_404(Producto, id=producto_id)
    return render(request, 'productos/stock_insuficiente.html', {
        'producto_nombre': producto.nombre,
        'talla': talla,
        'stock_disponible': stock_disponible
    })

def factura(request, venta_id):
    venta    = get_object_or_404(Venta, id=venta_id)
    detalles = DetalleVentaProductos.objects.filter(venta=venta)
    return render(request, 'productos/factura.html', {
        'venta': venta,
        'detalles': detalles,
        'cliente': venta.cliente,
        'total': venta.totalVenta
    })

def generar_factura(request, venta_id):
    venta    = get_object_or_404(Venta, id=venta_id)
    detalles = DetalleVentaProductos.objects.filter(venta=venta)
    cliente  = venta.cliente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="factura_{venta.id}.pdf"'
    doc      = SimpleDocTemplate(response)
    elementos = []
    estilos  = getSampleStyleSheet()

    ruta_logo = os.path.join(settings.BASE_DIR, 'static/images/logo.png')
    if os.path.exists(ruta_logo):
        elementos.append(Image(ruta_logo, width=120, height=60))

    elementos.append(Spacer(1, 10))
    elementos.append(Paragraph("Factura - Deportes 360", estilos['Title']))
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"Cliente: {cliente.usuario.first_name}", estilos['Normal']))
    elementos.append(Paragraph(f"Dirección: {cliente.direccion}", estilos['Normal']))
    elementos.append(Paragraph(f"Teléfono: {venta.telefonoContacto}", estilos['Normal']))
    elementos.append(Spacer(1, 20))

    datos = [["Producto", "Talla", "Cantidad", "Precio Unitario", "Subtotal"]]
    for d in detalles:
        datos.append([d.producto.nombre, d.talla, str(d.cantidad),
                      f"${d.precio_unitario}", f"${d.subtotal}"])

    tabla = Table(datos)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"Total: ${venta.totalVenta}", estilos['Heading2']))
    doc.build(elementos)
    return response


# ── Pedidos y repartidores ────────────────────────────────────────────────────

def pedidos(request):
    return render(request, 'productos/pedidos.html')


def pedidos_disponibles(request):
    usuario_id = request.session.get('usuario_id')
    try:
        repartidor = Repartidor.objects.get(usuario__id=usuario_id)
    except Repartidor.DoesNotExist:
        return redirect('login')

    pedidos = Pedido.objects.filter(estado='Disponible', repartidor=None)\
                            .select_related('venta__cliente__usuario')

    return render(request, 'pedidos/pedidos_disponibles.html', {
        'pedidos': pedidos,
        'repartidor': repartidor
    })


def tomar_pedido(request, pedido_id):
    usuario_id = request.session.get('usuario_id')
    repartidor = get_object_or_404(Repartidor, usuario__id=usuario_id)

    pedido = get_object_or_404(Pedido, id=pedido_id, estado='Disponible', repartidor=None)
    pedido.repartidor = repartidor
    pedido.estado = 'En camino'
    pedido.save()

    messages.success(request, "Pedido tomado correctamente.")
    return redirect('mis_pedidos')


def mis_pedidos(request):
    usuario_id = request.session.get('usuario_id')
    repartidor = get_object_or_404(Repartidor, usuario__id=usuario_id)

    ventas_pendientes = Pedido.objects.filter(estado='Disponible', repartidor=None)\
                                      .select_related('venta__cliente__usuario')
    pedidos_activos   = Pedido.objects.filter(repartidor=repartidor, estado='En camino')\
                                      .select_related('venta__cliente__usuario')
    mis_pedidos_qs    = Pedido.objects.filter(repartidor=repartidor, estado='Entregado')\
                                      .select_related('venta__cliente__usuario')\
                                      .order_by('-fecha_pedido')

    return render(request, 'repartidor.html', {
        'Nombre': repartidor.usuario.first_name,
        'ventas_pendientes': ventas_pendientes,
        'pedidos_activos': pedidos_activos,
        'mis_pedidos': mis_pedidos_qs,
        'repartidor': repartidor,
    })


def entregar_pedido(request, pedido_id):
    usuario_id = request.session.get('usuario_id')
    repartidor = get_object_or_404(Repartidor, usuario__id=usuario_id)

    pedido = get_object_or_404(Pedido, id=pedido_id, repartidor=repartidor, estado='En camino')
    pedido.estado = 'Entregado'
    pedido.save()

    if pedido.venta:
        pedido.venta.estado = 'Entregado'
        pedido.venta.save()

    messages.success(request, "Pedido marcado como entregado.")
    return redirect('repartidor')


# ── Reportes ──────────────────────────────────────────────────────────────────

def reportesVentas(request):
    ventas = Venta.objects.all()\
                  .select_related('cliente__usuario')\
                  .order_by('-fecha_venta')
    return render(request, "productos/reportes_ventas.html", {'ventas': ventas})

def generar_pdf(request):
    form = ReportesForm(request.GET)
    if form.is_valid():
        fecha_inicio = form.cleaned_data['fecha_inicio']
        fecha_fin    = form.cleaned_data['fecha_fin']
        ventas = Venta.objects.filter(
            fecha_venta__date__range=[fecha_inicio, fecha_fin]
        ).select_related('cliente__usuario')

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="reporte.pdf"'
        p = canvas.Canvas(response)
        p.drawString(100, 800, f"Reporte de Ventas: {fecha_inicio} → {fecha_fin}")
        y = 750
        for venta in ventas:
            texto = (f"ID: {venta.id} | "
                     f"Cliente: {venta.cliente.usuario.username} | "
                     f"Total: ${venta.totalVenta} | "
                     f"Fecha: {venta.fecha_venta.strftime('%d/%m/%Y')}")
            p.drawString(50, y, texto)
            y -= 20
            if y < 50:
                p.showPage()
                y = 800
        p.showPage()
        p.save()
        return response

    messages.error(request, "Fechas inválidas.")
    return redirect('reportesVentas')
