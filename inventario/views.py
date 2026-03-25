from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from rest_framework.decorators import api_view
from rest_framework.response import Response
import os

from .models import Producto, TallaProducto, Venta, Movimiento, Reporte
from .forms import CompraForm, SeleccionTallaForm, ReportesForm, MovimientoForm
from usuarios.models import Usuario

def catalogo(request):
    productos = Producto.objects.all()
    return render(request, 'catalogo.html', {'productos': productos})


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


def inventario(request):
    productos = Producto.objects.all()
    return render(request, 'inventario.html', {'productos': productos})

def pedidos(request):
    # lógica para mostrar pedidos
    return render(request, 'productos/pedidos.html')

def producto_nuevo(request):
    if request.method == "POST":
        producto = Producto.objects.create(
            nombre=request.POST.get("nombre"),
            precio=request.POST.get("precio"),
            descripcion=request.POST.get("descripcion"),
            imagen=request.FILES.get("imagen"),
        )
        for talla, key in [('S', 'stock_s'), ('M', 'stock_m'), ('L', 'stock_l')]:
            stock = int(request.POST.get(key, 0))
            if stock > 0:
                TallaProducto.objects.create(producto=producto, talla=talla, stock=stock)
        return redirect('productos')
    return render(request, 'productos/producto_nuevo.html')


def producto_editar(request, id):
    producto = get_object_or_404(Producto, id=id)
    if request.method == "POST":
        producto.nombre = request.POST.get("nombre")
        producto.precio = request.POST.get("precio")
        producto.descripcion = request.POST.get("descripcion")
        if request.FILES.get("imagen"):
            producto.imagen = request.FILES.get("imagen")
        producto.save()
        return redirect('productos')
    return render(request, 'productos/producto_editar.html', {'producto': producto})


def producto_eliminar(request, id):
    producto = get_object_or_404(Producto, id=id)
    producto.delete()
    return redirect('inventario')


def registrar_movimiento(request):
    productos = Producto.objects.all()
    if request.method == "POST":
        producto = get_object_or_404(Producto, id=request.POST.get("producto"))
        Movimiento.objects.create(
            producto=producto,
            talla=request.POST.get("talla"),
            cantidad=int(request.POST.get("cantidad"))
        )
        return redirect('movimientos')
    return render(request, 'movimientos.html', {'productos': productos})


def carrito(request):
    carrito = request.session.get('carrito', {})
    if request.method == 'POST':
        if 'eliminar' in request.POST:
            carrito.pop(request.POST.get('eliminar'), None)
        elif 'vaciar' in request.POST:
            carrito.clear()
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
    total = sum(item['precio'] * item['cantidad'] for item in carrito.values())
    return render(request, 'productos/carrito.html', {'productos': carrito, 'total': total})


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


def formulario_compra(request):
    carrito = request.session.get('carrito', {})
    cantidad_total = sum(item['cantidad'] for item in carrito.values())
    total_venta = sum(item['precio'] * item['cantidad'] for item in carrito.values())
    usuario_id = request.session.get('usuario_id')
    cliente = Usuario.objects.get(id=usuario_id) if usuario_id else None

    if request.method == 'POST':
        form = CompraForm(request.POST)
        if form.is_valid():
            for key, item in carrito.items():
                producto_id = key.split('_')[0]
                talla = item['talla']
                producto = get_object_or_404(Producto, id=int(producto_id))
                talla_obj = get_object_or_404(TallaProducto, producto=producto, talla=talla)
                if talla_obj.stock >= item['cantidad']:
                    talla_obj.stock -= item['cantidad']
                    talla_obj.save()
                else:
                    return redirect('stock_insuficiente',
                                    producto_id=producto.id,
                                    talla=talla,
                                    stock_disponible=talla_obj.stock)
            request.session['carrito'] = {}
            return redirect('factura')
    else:
        form = CompraForm(initial={'cant_producto': cantidad_total, 'total_venta': total_venta})

    return render(request, 'productos/formulario_compra.html', {
        'form': form, 'cliente': cliente, 'productos': carrito, 'total': total_venta
    })


def stock_insuficiente(request, producto_id, talla, stock_disponible):
    producto = get_object_or_404(Producto, id=producto_id)
    return render(request, 'productos/stock_insuficiente.html', {
        'producto_nombre': producto.nombre,
        'talla': talla,
        'stock_disponible': stock_disponible
    })


def factura(request):
    carrito = request.session.get('carrito', {})
    usuario_id = request.session.get('usuario_id')
    cliente = Usuario.objects.get(id=usuario_id)
    total = sum(float(item['precio']) * item['cantidad'] for item in carrito.values())
    return render(request, 'productos/factura.html', {
        'cliente': cliente, 'productos': carrito, 'total': total
    })


def generar_pdf(request):
    form = ReportesForm(request.GET)
    if form.is_valid():
        fecha_inicio = form.cleaned_data['fecha_inicio']
        fecha_fin = form.cleaned_data['fecha_fin']
        ventas = Venta.objects.filter(fecha__range=[fecha_inicio, fecha_fin])
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="reporte.pdf"'
        p = canvas.Canvas(response)
        p.drawString(100, 800, f"Reporte de Ventas desde {fecha_inicio} hasta {fecha_fin}")
        y = 750
        for venta in ventas:
            p.drawString(50, y, f"ID: {venta.id} | Total: ${venta.totalVenta}")
            y -= 20
            if y < 50:
                p.showPage()
                y = 800
        p.showPage()
        p.save()
        return response
    messages.error(request, "Fechas inválidas.")
    return render(request, 'reportes.html', {'form': form})


def generar_factura(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="factura.pdf"'
    doc = SimpleDocTemplate(response)
    elementos = []
    estilos = getSampleStyleSheet()
    ruta_logo = os.path.join(settings.BASE_DIR, 'static/images/logo.png')
    if os.path.exists(ruta_logo):
        elementos.append(Image(ruta_logo, width=120, height=60))
    elementos.append(Spacer(1, 10))
    elementos.append(Paragraph("Factura - Deportes 360", estilos['Title']))
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph("Cliente: Luis", estilos['Normal']))
    elementos.append(Paragraph("Fecha: 22/03/2026", estilos['Normal']))
    elementos.append(Spacer(1, 20))
    datos = [["Producto", "Talla", "Cantidad", "Precio"], ["Camiseta", "M", "2", "$120.000"]]
    tabla = Table(datos)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph("Total: $120.000", estilos['Heading2']))
    doc.build(elementos)
    return response


def reportesVentas(request):
    return render(request, "productos/reportes_ventas.html")