from django.shortcuts import render, redirect, get_object_or_404
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from .models import (Producto, TallaProducto, Venta, Movimiento,Reporte, DetalleVentaProductos, Pedido, Sugerencia, RespuestaSugerencia)
from .forms import CompraForm, ReportesForm, MovimientoForm
from usuarios.models import Usuario, Cliente, Repartidor
from django.contrib.auth.hashers import make_password
from reportlab.lib.styles import getSampleStyleSheet
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.contrib.auth.hashers import check_password
from rest_framework import viewsets
from django.contrib import messages
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
import urllib.parse
import openpyxl
import os
import pandas as pd
import json
from decimal import Decimal
import pytz

# ── Catálogo y productos ──────────────────────────────────────────────────────

def catalogo(request):
    categoria = request.GET.get('categoria')
    if categoria:
        productos = Producto.objects.filter(
            categoria__iexact=categoria,
            descontinuado=False    
        )
    else:
        productos = Producto.objects.filter(
            descontinuado=False    # ← y esto
        )
    return render(request, 'catalogo.html', {'productos': productos})

def catalogo_categoria(request, categoria):
    productos = Producto.objects.filter(
        categoria__iexact=categoria,
        descontinuado=False    # ← agrega esto
    )
    return render(request, 'catalogo_categoria.html', {
        'productos': productos,
        'categoria': categoria
    })

def mis_compras(request):
    try:
        usuario_id = request.session.get('usuario_id')  # 🔥 este es el correcto
        usuario = Usuario.objects.get(id=usuario_id)

        cliente = Cliente.objects.get(usuario=usuario)
        compras = Venta.objects.filter(cliente=cliente)

    except (Cliente.DoesNotExist, Usuario.DoesNotExist):
        compras = []

    return render(request, 'usuarios/mis_compras.html', {'compras': compras})

def carga_masiva_productos(request):
    if request.method == 'POST':
        archivo = request.FILES.get('archivo')

        if not archivo:
            messages.error(request, "Debe subir un archivo.")
            return redirect('carga_masiva')

        # validar que sea excel
        if not archivo.name.endswith(('.xlsx', '.xls')):
            messages.error(request, "Solo se permiten archivos Excel (.xlsx, .xls)")
            return redirect('carga_masiva')

        try:
            df = pd.read_excel(archivo)

            for _, fila in df.iterrows():
                Producto.objects.create(
                    nombre=fila['nombre'],
                    precio=fila['precio'],
                    stock=fila['stock'],
                    descripcion=fila['descripcion']
                )

            messages.success(request, "Productos cargados correctamente")

        except Exception as e:
            messages.error(request, f"Error al procesar el archivo: {e}")

        return redirect('carga_masiva')

    return redirect('panel_admin')

def panel_admin(request):
    ultimos_pedidos = Pedido.objects.order_by('-fecha_pedido')[:10]
    usuarios = Usuario.objects.all()
    productos = Producto.objects.all()
    ventas = Venta.objects.all()
    movimientos = Movimiento.objects.order_by('-fecha')[:20]  # últimos 20 movimientos
    sugerencias = Sugerencia.objects.all()

    return render(request, 'admin/panel_admin.html', {
        'ultimos_pedidos': ultimos_pedidos,
        'usuarios': usuarios,
        'productos': productos,
        'ventas': ventas,
        'movimientos': movimientos,
        'sugerencias': sugerencias,
    })

def movimiento_nuevo(request):
    productos_qs = Producto.objects.prefetch_related('tallas').order_by('nombre')

    if request.method == "POST":
        producto_id = request.POST.get("producto")
        talla       = request.POST.get("talla")
        tipo        = request.POST.get("tipo_movimiento")
        cantidad    = int(request.POST.get("cantidad", 0))
        motivo      = request.POST.get("motivo", "")
        proveedor   = request.POST.get("proveedor", "")

        producto = get_object_or_404(Producto, id=producto_id)

        try:
            Movimiento.objects.create(
                producto=producto,
                talla=talla,
                cantidad=cantidad,
                tipo_movimiento=tipo,
                motivo=motivo,
                proveedor=proveedor,
            )
            messages.success(request, f"Movimiento registrado: {tipo} de {cantidad} uds — {producto.nombre} talla {talla}.")
        except Exception as e:
            messages.error(request, f"Error: {e}")

        return redirect('panel_admin')   # ← vuelve al panel

    return render(request, 'productos/movimiento_nuevo.html', {'productos': productos_qs})


def productos(request):
    productos = Producto.objects.all()
    for producto in productos:
        tallas = TallaProducto.objects.filter(producto=producto)
        producto.stock_total = sum(t.stock for t in tallas)  # cálculo dinámico
    return render(request, 'productos/productos.html', {'productos': productos})


def detalle_producto(request, id):
    producto = get_object_or_404(Producto, id=id, descontinuado=False)  # ← agrega descontinuado=False
    tallas   = TallaProducto.objects.filter(producto=producto)
    stock_total = sum(t.stock for t in tallas)
    return render(request, 'productos/producto-detalle.html', {
        'producto':   producto,
        'tallas':     tallas,
        'stock_total': stock_total
    })

def producto_nuevo(request):
    if request.method == 'POST':
        nombre      = request.POST.get('nombre')
        precio      = request.POST.get('precio')
        descripcion = request.POST.get('descripcion', '')
        categoria   = request.POST.get('categoria', '')
        imagen      = request.FILES.get('imagen')

        producto = Producto.objects.create(
            nombre=nombre, precio=precio,
            descripcion=descripcion, categoria=categoria,
            imagen=imagen
        )

        # Tallas adulto
        for talla, campo in [('S','stock_s'),('M','stock_m'),('L','stock_l'),('XL','stock_xl')]:
            stock = int(request.POST.get(campo, 0) or 0)
            if stock > 0:
                TallaProducto.objects.create(producto=producto, talla=talla, stock=stock)

        # Tallas niño
        for talla in ['2', '4', '6', '8', '10', '12']:
            stock = int(request.POST.get(f'stock_{talla}', 0) or 0)
            if stock > 0:
                TallaProducto.objects.create(producto=producto, talla=talla, stock=stock)

        messages.success(request, f'Producto "{nombre}" creado correctamente.')
        return redirect('panel_admin')

    return redirect('panel_admin')

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

def movimientos(request, id):
    producto = get_object_or_404(Producto, id=id)
    movimientos = Movimiento.objects.filter(producto=producto).order_by('-fecha')
    return render(request, 'productos/movimientos.html', {
        'producto': producto,
        'movimientos': movimientos
    })

def responder_sugerencia(request, sugerencia_id):
    sugerencia = get_object_or_404(Sugerencia, id=sugerencia_id)
    if request.method == 'POST':
        mensaje = request.POST.get('mensaje', '').strip()
        if mensaje:
            RespuestaSugerencia.objects.create(
                sugerencia=sugerencia,
                mensaje=mensaje,
                es_admin=True
            )
            return JsonResponse({'ok': True, 'mensaje': mensaje})
    return JsonResponse({'ok': False})

# Vista del panel de sugerencias con chat
def panel_sugerencias_chat(request):
    sugerencias = Sugerencia.objects.all().order_by('-fecha')
    return render(request, 'panel_sugerencias.html', {'sugerencias': sugerencias})

def producto_eliminar(request, id):
    producto = get_object_or_404(Producto, id=id)
    producto.delete()
    messages.success(request, "Producto eliminado correctamente")
    return redirect('productos')  # <- usa el name de la URL de productos


# ── Inventario y movimientos ──────────────────────────────────────────────────

def inventario(request):
    productos = Producto.objects.all()
    return render(request, 'productos/inventario.html', {'productos': productos})

def producto_eliminar(request, id):
    producto = get_object_or_404(Producto, id=id)

    for talla in producto.tallas.all():
        if talla.stock > 0:
            Movimiento.objects.create(
                producto        = producto,
                nombre_producto = producto.nombre,   # ← guardar nombre
                talla           = talla.talla,
                tipo_movimiento = 'salida',
                cantidad        = talla.stock,
                motivo          = f'Producto "{producto.nombre}" eliminado del sistema',
            )

    producto.delete()
    messages.success(request, "Producto eliminado correctamente.")
    return redirect('productos')

def reportes_admin(request):
    from django.db.models import Sum, Count, Avg
    from django.db.models.functions import TruncDate, TruncMonth
    from datetime import date, timedelta

    hoy = date.today()
    fecha_inicio_default = hoy.replace(day=1).strftime('%Y-%m-%d')
    fecha_fin_default    = hoy.strftime('%Y-%m-%d')

    fecha_inicio = request.GET.get('fecha_inicio', fecha_inicio_default)
    fecha_fin    = request.GET.get('fecha_fin',    fecha_fin_default)

    ventas = Venta.objects.select_related('cliente__usuario').order_by('-fecha_venta')
    if fecha_inicio:
        ventas = ventas.filter(fecha_venta__date__gte=fecha_inicio)
    if fecha_fin:
        ventas = ventas.filter(fecha_venta__date__lte=fecha_fin)

    cantidad_ventas   = ventas.count()
    total_general     = float(ventas.aggregate(t=Sum('totalVenta'))['t'] or 0)
    clientes_unicos   = ventas.values('cliente').distinct().count()
    ticket_avg        = float(ventas.aggregate(Avg('totalVenta'))['totalVenta__avg'] or 0)
    unidades_vendidas = int(ventas.aggregate(t=Sum('cantProducto'))['t'] or 0)

    ventas_por_fecha = (
        ventas.annotate(dia=TruncDate('fecha_venta'))
              .values('dia')
              .annotate(total=Sum('totalVenta'), cantidad=Count('id'))
              .order_by('dia')
    )
    fechas_ventas  = [str(v['dia']) for v in ventas_por_fecha]
    totales_ventas = [float(v['total']) for v in ventas_por_fecha]
    cant_ventas    = [v['cantidad'] for v in ventas_por_fecha]

    top_raw = (
        DetalleVentaProductos.objects
        .filter(venta__in=ventas)
        .values('producto__nombre')
        .annotate(total_unidades=Sum('cantidad'), total_ingresos=Sum('subtotal'))
        .order_by('-total_ingresos')[:10]
    )
    nombres_productos = [p['producto__nombre'] for p in top_raw]
    totales_productos = [float(p['total_ingresos'] or 0) for p in top_raw]
    total_top = sum(totales_productos) or 1
    top_productos = [
        {
            'nombre':         p['producto__nombre'],
            'total_unidades': p['total_unidades'],
            'total_ingresos': float(p['total_ingresos'] or 0),
            'porcentaje':     round(float(p['total_ingresos'] or 0) / total_top * 100, 1),
        }
        for p in top_raw
    ]

    ventas_pse = ventas.filter(metodo_de_pago__in=['PSE', 'PAGO_EN_LINEA']).count()
    ventas_ce  = ventas.exclude(metodo_de_pago__in=['PSE', 'PAGO_EN_LINEA']).count()

    desde_12 = hoy - timedelta(days=365)
    por_mes = (
        Venta.objects.filter(fecha_venta__date__gte=desde_12)
        .annotate(mes=TruncMonth('fecha_venta'))
        .values('mes')
        .annotate(cantidad=Count('id'), total=Sum('totalVenta'), ticket=Avg('totalVenta'), clientes=Count('cliente', distinct=True))
        .order_by('mes')
    )
    meses_es = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
    meses_data = [
        {
            'label':    meses_es[m['mes'].month - 1] + ' ' + str(m['mes'].year),
            'cantidad': m['cantidad'],
            'total':    float(m['total'] or 0),
            'ticket':   float(m['ticket'] or 0),
            'clientes': m['clientes'],
        }
        for m in por_mes
    ]

    return render(request, 'productos/reportes_admin.html', {
        'ventas':               ventas,
        'cantidad_ventas':      cantidad_ventas,
        'total_general':        total_general,
        'clientes_unicos':      clientes_unicos,
        'ticket_promedio':      round(ticket_avg, 0),
        'unidades_vendidas':    unidades_vendidas,
        'top_productos':        top_productos,
        'ventas_pse':           ventas_pse,
        'ventas_ce':            ventas_ce,
        'fecha_inicio_default': fecha_inicio_default,
        'fecha_fin_default':    fecha_fin_default,
        'fechas_ventas':        json.dumps(fechas_ventas),
        'totales_ventas':       json.dumps(totales_ventas),
        'cant_ventas':          json.dumps(cant_ventas),
        'nombres_productos':    json.dumps(nombres_productos),
        'totales_productos':    json.dumps(totales_productos),
        'meses_data':           json.dumps(meses_data),
    })

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
                    return render(request, 'productos/stock_insuficiente.html', {
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

def agregar_producto(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        cantidad = request.POST.get("cantidad")
        precio = request.POST.get("precio")

        Producto.objects.create(
            nombre=nombre,
            precio=precio,
            descripcion="",
            categoria="MIXTO"
        )
        messages.success(request, "Producto agregado correctamente")
        return redirect('inventario')
    return redirect('inventario')

def producto_tallas_eliminar(request):
    if request.method == 'POST':
        talla_ids  = request.POST.getlist('talla_ids')
        producto_id = request.POST.get('producto_id')

        for talla_id in talla_ids:
            talla = get_object_or_404(TallaProducto, id=talla_id)
            if talla.stock > 0:
                Movimiento.objects.create(
                    producto        = talla.producto,
                    nombre_producto = talla.producto.nombre,
                    talla           = talla.talla,
                    tipo_movimiento = 'salida',
                    cantidad        = talla.stock,
                    motivo          = f'Talla {talla.talla} eliminada manualmente',
                )
            talla.delete()

        messages.success(request, 'Tallas eliminadas correctamente.')
        return redirect('productos')
    
def producto_talla_eliminar(request, talla_id):
    talla = get_object_or_404(TallaProducto, id=talla_id)

    if talla.stock > 0:
        Movimiento.objects.create(
            producto        = talla.producto,
            nombre_producto = talla.producto.nombre,
            talla           = talla.talla,
            tipo_movimiento = 'salida',
            cantidad        = talla.stock,
            motivo          = f'Talla {talla.talla} eliminada manualmente del producto "{talla.producto.nombre}"',
        )

    nombre_talla = talla.talla
    talla.delete()
    messages.success(request, f'Talla {nombre_talla} eliminada correctamente.')
    return redirect('productos')


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

    # 🔥 CREAR DETALLE (ESTO TE FALTABA)
                    DetalleVentaProductos.objects.create(
                        venta=venta,
                        producto=producto,
                        talla=item['talla'],
                        cantidad=item['cantidad'],
                        precio_unitario=item['precio'],
                        subtotal=item['precio'] * item['cantidad']
                    )

    # Pedido para repartidor
                    Pedido.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=item['cantidad'],
                        total=item['precio'] * item['cantidad'],
                        estado="Disponible",  # 🔥 aprovecha y arregla esto
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

def validar_pse(request):
    if request.method == "POST":
        data = json.loads(request.body)

        password_input = data.get("password")

        # 🔥 Obtener usuario logueado desde sesión
        usuario_id = request.session.get('usuario_id')

        if not usuario_id:
            return JsonResponse({"ok": False, "error": "Usuario no autenticado"})

        from usuarios.models import Usuario
        usuario = Usuario.objects.get(id=usuario_id)

        # 🔥 SOLO valida contraseña
        if check_password(password_input, usuario.password):
            return JsonResponse({"ok": True})
        else:
            return JsonResponse({"ok": False, "error": "Contraseña incorrecta"})

    return JsonResponse({"ok": False})

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

def factura1(request, venta_id):
    venta    = get_object_or_404(Venta, id=venta_id)
    detalles = DetalleVentaProductos.objects.filter(venta=venta)
    return render(request, 'usuarios/factura1.html', {
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

    ventas_pendientes = Pedido.objects.filter(
        estado='Disponible', repartidor=None
    ).select_related('venta__cliente__usuario')

    pedidos_activos = Pedido.objects.filter(
        repartidor=repartidor, estado='En camino'
    ).select_related('venta__cliente__usuario')

    mis_pedidos_qs = Pedido.objects.filter(
        repartidor=repartidor, estado='Entregado'
    ).select_related('venta__cliente__usuario').order_by('-fecha_pedido')

    total_ganancias = sum(p.valor_domicilio for p in mis_pedidos_qs)

    # Mensaje WhatsApp pre-armado
    mensaje_wa = urllib.parse.quote(
        "¡Hola! Soy el repartidor de Deportes 360. "
        "Ya voy en camino con su pedido, pronto lo estaré entregando. 🚀"
    )

    return render(request, 'repartidor.html', {
        'Nombre':            repartidor.usuario.first_name,
        'usuario':           repartidor.usuario,
        'repartidor':        repartidor,
        'ventas_pendientes': ventas_pendientes,
        'pedidos_activos':   pedidos_activos,
        'mis_pedidos':       mis_pedidos_qs,
        'total_ganancias':   total_ganancias,
        'mensaje_wa':        mensaje_wa,
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

def producto_discontinuar(request, id):
    producto = get_object_or_404(Producto, id=id)
    if request.method == 'POST':
        producto.descontinuado = True   # ← con 's', igual que el modelo
        producto.save()
        messages.success(request, f'"{producto.nombre}" fue descontinuado correctamente.')
    return redirect('productos')

def producto_reactivar(request, id):
    producto = get_object_or_404(Producto, id=id)
    if request.method == 'POST':
        producto.descontinuado = False  # ← con 's'
        producto.save()
        messages.success(request, f'"{producto.nombre}" fue reactivado correctamente.')
    return redirect('productos')

def responder_sugerencia(request, sugerencia_id):
    sugerencia = get_object_or_404(Sugerencia, id=sugerencia_id)
    if request.method == 'POST':
        mensaje = request.POST.get('mensaje', '').strip()
        if mensaje:
            RespuestaSugerencia.objects.create(
                sugerencia=sugerencia,
                mensaje=mensaje,
                es_admin=True
            )
            return JsonResponse({'ok': True, 'mensaje': mensaje})
    return JsonResponse({'ok': False})

def sugerencia_respuestas(request, sugerencia_id):
    
    bogota = pytz.timezone('America/Bogota')
    sug = get_object_or_404(Sugerencia, id=sugerencia_id)
    
    respuestas = []
    for r in sug.respuestas.all():
        fecha_bogota = r.fecha.astimezone(bogota)
        respuestas.append({
            'mensaje':  r.mensaje,
            'es_admin': r.es_admin,
            'hora':     fecha_bogota.strftime('%d/%m/%Y %H:%M'),
        })
    
    fecha_sug = sug.fecha.astimezone(bogota)
    return JsonResponse({
        'ok':         True,
        'texto':      sug.texto,
        'fecha':      fecha_sug.strftime('%d/%m/%Y %H:%M'),
        'respuestas': respuestas,
    })

def exportar_excel(request):
    from datetime import date

    fecha_inicio = request.GET.get('fecha_inicio') or None
    fecha_fin    = request.GET.get('fecha_fin') or None

    ventas = Venta.objects.select_related('cliente__usuario').all()
    if fecha_inicio:
        ventas = ventas.filter(fecha_venta__date__gte=fecha_inicio)
    if fecha_fin:
        ventas = ventas.filter(fecha_venta__date__lte=fecha_fin)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ventas"
    ws.append(["ID", "Cliente", "Método de pago", "Dirección", "Cantidad", "Total", "Fecha"])

    for v in ventas:
        ws.append([
            v.id,
            v.cliente.usuario.username,
            v.metodo_de_pago,
            v.direccionEnvio,
            v.cantProducto,
            float(v.totalVenta),
            v.fecha_venta.replace(tzinfo=None).strftime("%d/%m/%Y %H:%M"),
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="ventas.xlsx"'
    wb.save(response)
    return response

def generar_pdf(request):
    from datetime import date
    from django.db.models import Sum, Count, Avg
    from django.db.models.functions import TruncDate
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    import io

    # ── Formato de números ────────────────────────────────────────
    def fmt(numero):
        try:
            return '${:,.0f}'.format(float(numero)).replace(',', '.')
        except:
            return '$0'

    def pct(parte, total):
        try:
            return f'{float(parte) / float(total) * 100:.1f}%' if float(total) else '0%'
        except:
            return '0%'

    # ── Fechas ────────────────────────────────────────────────────
    fecha_inicio = request.GET.get('fecha_inicio') or None
    fecha_fin    = request.GET.get('fecha_fin') or None

    hoy = date.today()
    if not fecha_inicio:
        fecha_inicio = hoy.replace(day=1).strftime('%Y-%m-%d')
    if not fecha_fin:
        fecha_fin = hoy.strftime('%Y-%m-%d')

    # ── Datos ─────────────────────────────────────────────────────
    ventas = Venta.objects.filter(
        fecha_venta__date__range=[fecha_inicio, fecha_fin]
    ).select_related('cliente__usuario').order_by('fecha_venta')

    cantidad_ventas   = ventas.count()
    total_general     = float(ventas.aggregate(t=Sum('totalVenta'))['t'] or 0)
    ticket_promedio   = float(ventas.aggregate(Avg('totalVenta'))['totalVenta__avg'] or 0)
    clientes_unicos   = ventas.values('cliente').distinct().count()
    unidades_vendidas = int(ventas.aggregate(t=Sum('cantProducto'))['t'] or 0)
    ventas_pse        = ventas.filter(metodo_de_pago__in=['PSE', 'PAGO_EN_LINEA']).count()
    ventas_ce         = ventas.exclude(metodo_de_pago__in=['PSE', 'PAGO_EN_LINEA']).count()

    top_raw = (
        DetalleVentaProductos.objects
        .filter(
            venta__fecha_venta__date__gte=fecha_inicio,
            venta__fecha_venta__date__lte=fecha_fin,
        )
        .values('producto__nombre')
        .annotate(unidades=Sum('cantidad'), ingresos=Sum('subtotal'))
        .order_by('-ingresos')[:10]
    )

    ventas_por_dia = (
        ventas.annotate(dia=TruncDate('fecha_venta'))
              .values('dia')
              .annotate(total=Sum('totalVenta'), cant=Count('id'))
              .order_by('dia')
    )

    # ── Estilos ───────────────────────────────────────────────────
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        leftMargin=1.5*cm, rightMargin=1.5*cm
    )

    styles   = getSampleStyleSheet()
    ROJO     = colors.HexColor('#d40000')
    NEGRO    = colors.HexColor('#0d0d0d')
    GRIS     = colors.HexColor('#f3f4f6')
    GRIS2    = colors.HexColor('#6b7280')
    VERDE    = colors.HexColor('#16a34a')
    AZUL     = colors.HexColor('#2563eb')
    BORDE    = colors.HexColor('#e5e7eb')

    st_seccion = ParagraphStyle(
        'sec', fontSize=12, textColor=ROJO,
        fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6
    )
    st_normal = ParagraphStyle(
        'nor', fontSize=9, textColor=NEGRO,
        fontName='Helvetica', leading=13
    )
    st_pie = ParagraphStyle(
        'pie', fontSize=8, textColor=GRIS2,
        fontName='Helvetica', alignment=TA_CENTER
    )
    st_bold9 = ParagraphStyle(
        'b9', fontSize=9, textColor=NEGRO,
        fontName='Helvetica-Bold', leading=13
    )

    def th(texto):
        """Celda de encabezado de tabla"""
        return Paragraph(f'<font color="white"><b>{texto}</b></font>', st_normal)

    def td(texto, bold=False, align='left', color=None):
        """Celda normal de tabla"""
        col = color.hexval() if color else '#0d0d0d'
        estilo = st_bold9 if bold else st_normal
        return Paragraph(f'<font color="{col}">{texto}</font>', estilo)

    ESTILO_TABLA = [
        ('BACKGROUND',     (0, 0), (-1, 0), NEGRO),
        ('TEXTCOLOR',      (0, 0), (-1, 0), colors.white),
        ('FONTNAME',       (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GRIS]),
        ('GRID',           (0, 0), (-1, -1), 0.3, BORDE),
        ('TOPPADDING',     (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING',  (0, 0), (-1, -1), 7),
        ('LEFTPADDING',    (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',   (0, 0), (-1, -1), 10),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
    ]

    elems = []

    # ══ ENCABEZADO ════════════════════════════════════════════════
    header_data = [[
        Paragraph(
            '<font name="Helvetica-Bold" size="20" color="#0d0d0d">DEPORTES 360</font><br/>'
            '<font size="9" color="#d40000">Reporte de Ventas</font>',
            styles['Normal']
        ),
        Paragraph(
            f'<font size="9" color="#6b7280">'
            f'Período: <b>{fecha_inicio}</b> → <b>{fecha_fin}</b><br/>'
            f'Generado el: {hoy.strftime("%d/%m/%Y")}</font>',
            ParagraphStyle('rr', fontSize=9, alignment=TA_RIGHT)
        ),
    ]]
    t_header = Table(header_data, colWidths=[10*cm, 7.8*cm])
    t_header.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW',     (0, 0), (-1,  0), 2, ROJO),
        ('BOTTOMPADDING', (0, 0), (-1,  0), 10),
        ('TOPPADDING',    (0, 0), (-1,  0), 4),
    ]))
    elems.append(t_header)
    elems.append(Spacer(1, 0.5*cm))

    # ══ MÉTRICAS ══════════════════════════════════════════════════
    elems.append(Paragraph('Resumen General', st_seccion))

    def metric_box(lbl, val, color=NEGRO):
        return Table(
            [[Paragraph(f'<font size="8" color="#6b7280">{lbl}</font>', styles['Normal'])],
             [Paragraph(f'<font size="16" color="{color.hexval()}"><b>{val}</b></font>', styles['Normal'])]],
            colWidths=[3.5*cm]
        )

    t_metrics = Table([[
        metric_box('TOTAL VENTAS',    str(cantidad_ventas),  ROJO),
        metric_box('VALOR TOTAL',     fmt(total_general),    NEGRO),
        metric_box('TICKET PROMEDIO', fmt(ticket_promedio),  NEGRO),
        metric_box('CLIENTES ÚNICOS', str(clientes_unicos),  AZUL),
        metric_box('UNIDADES VEND.',  str(unidades_vendidas),VERDE),
    ]], colWidths=[3.56*cm]*5)
    t_metrics.setStyle(TableStyle([
        ('BOX',            (0, 0), (-1, -1), 0.5, BORDE),
        ('INNERGRID',      (0, 0), (-1, -1), 0.5, BORDE),
        ('BACKGROUND',     (0, 0), (-1, -1), GRIS),
        ('TOPPADDING',     (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING',  (0, 0), (-1, -1), 10),
        ('LEFTPADDING',    (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',   (0, 0), (-1, -1), 10),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elems.append(t_metrics)
    elems.append(Spacer(1, 0.3*cm))

    # ══ MÉTODOS DE PAGO ═══════════════════════════════════════════
    elems.append(Paragraph('Métodos de Pago', st_seccion))
    t_metodos = Table([
        [th('Método'),         th('Cantidad'), th('Porcentaje')],
        [td('PSE / En línea'), td(str(ventas_pse), bold=True, color=AZUL),  td(pct(ventas_pse, cantidad_ventas))],
        [td('Contra entrega'), td(str(ventas_ce),  bold=True, color=ROJO),  td(pct(ventas_ce,  cantidad_ventas))],
        [td('Total', bold=True), td(str(cantidad_ventas), bold=True), td('100%')],
    ], colWidths=[9*cm, 4*cm, 4.8*cm])
    t_metodos.setStyle(TableStyle(ESTILO_TABLA + [
        ('BACKGROUND',  (0, 3), (-1, 3), colors.HexColor('#f0f0f0')),
        ('FONTNAME',    (0, 3), (-1, 3), 'Helvetica-Bold'),
    ]))
    elems.append(t_metodos)

    # ══ TOP PRODUCTOS ═════════════════════════════════════════════
    elems.append(Paragraph('Top 10 Productos Más Vendidos', st_seccion))
    if list(top_raw):
        filas = [[th('#'), th('Producto'), th('Unidades'), th('Ingresos'), th('% del total')]]
        for i, prod in enumerate(top_raw, 1):
            ing = float(prod['ingresos'] or 0)
            filas.append([
                td(str(i)),
                td(prod['producto__nombre']),
                td(str(prod['unidades']), bold=True),
                td(fmt(ing), bold=True, color=VERDE),
                td(pct(ing, total_general)),
            ])
        t_prod = Table(filas, colWidths=[1*cm, 8.5*cm, 2.5*cm, 3.5*cm, 2.3*cm])
        t_prod.setStyle(TableStyle(ESTILO_TABLA))
        elems.append(t_prod)
    else:
        elems.append(Paragraph('Sin datos de productos para este período.', st_normal))

    # ══ VENTAS POR DÍA ════════════════════════════════════════════
    dias_lista = list(ventas_por_dia)
    if dias_lista:
        elems.append(Paragraph('Ventas por Día', st_seccion))
        filas_dia = [[th('Fecha'), th('Nº Ventas'), th('Total del día')]]
        for v in dias_lista:
            filas_dia.append([
                td(v['dia'].strftime('%d/%m/%Y')),
                td(str(v['cant']), bold=True),
                td(fmt(v['total']), bold=True, color=ROJO),
            ])
        t_dias = Table(filas_dia, colWidths=[5*cm, 4.5*cm, 8.3*cm])
        t_dias.setStyle(TableStyle(ESTILO_TABLA))
        elems.append(t_dias)

    # ══ LISTADO COMPLETO DE VENTAS ════════════════════════════════
    elems.append(Paragraph('Listado Completo de Ventas', st_seccion))
    filas_v = [[
        th('ID'), th('Cliente'), th('Método'),
        th('Cant.'), th('Total'), th('Estado'), th('Fecha'),
    ]]
    for v in ventas:
        metodo = 'PSE' if v.metodo_de_pago in ['PSE', 'PAGO_EN_LINEA'] else 'C.Entrega'
        estado = v.estado or '—'
        color_est = VERDE if 'Entregado' in estado or 'completada' in estado else (ROJO if 'cancelada' in estado else NEGRO)
        filas_v.append([
            td(f'#{v.id}'),
            td(v.cliente.usuario.username),
            td(metodo, color=AZUL if metodo == 'PSE' else None),
            td(str(v.cantProducto)),
            td(fmt(v.totalVenta), bold=True),
            td(estado, color=color_est),
            td(v.fecha_venta.strftime('%d/%m/%Y')),
        ])

    t_ventas = Table(
        filas_v,
        colWidths=[1.3*cm, 4.5*cm, 2.5*cm, 1.5*cm, 3*cm, 3*cm, 2.5*cm]
    )
    t_ventas.setStyle(TableStyle(ESTILO_TABLA + [
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elems.append(t_ventas)

    # ══ PIE ═══════════════════════════════════════════════════════
    elems.append(Spacer(1, 0.6*cm))
    elems.append(HRFlowable(width='100%', thickness=1.5, color=ROJO))
    elems.append(Spacer(1, 0.2*cm))
    elems.append(Paragraph(
        f'Deportes 360  ·  Reporte generado el {hoy.strftime("%d/%m/%Y")}  ·  '
        f'Período: {fecha_inicio} → {fecha_fin}  ·  '
        f'Total ventas: {cantidad_ventas}  ·  Valor: {fmt(total_general)}',
        st_pie
    ))

    # ══ GENERAR ═══════════════════════════════════════════════════
    doc.build(elems)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="reporte_deportes360_{fecha_inicio}_{fecha_fin}.pdf"'
    )
    return response