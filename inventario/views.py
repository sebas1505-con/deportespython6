from django.shortcuts import render, redirect, get_object_or_404
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from .models import (Producto, TallaProducto, Venta, Movimiento, Reporte, DetalleVentaProductos, Pedido, Sugerencia, RespuestaSugerencia, ResenaVenta)
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

# ── Helpers ──────────────────────────────────────────────────────────────────

def _perfil_completo(usuario):
    """Devuelve True si el usuario tiene los datos mínimos para comprar."""
    return all([
        usuario.first_name and usuario.first_name.strip(),
        usuario.telefono   and usuario.telefono.strip(),
        usuario.tipo_documento,
        usuario.cedula     and usuario.cedula.strip(),
    ])

# ── Catálogo y productos ──────────────────────────────────────────────────────

def catalogo(request):
    categoria = request.GET.get('categoria')
    base = Producto.objects.filter(descontinuado=False).exclude(imagen='').exclude(imagen__isnull=True)
    if categoria:
        productos = base.filter(categoria__iexact=categoria)
    else:
        productos = base
    return render(request, 'catalogo.html', {'productos': productos})

def catalogo_categoria(request, categoria):
    cat = categoria.upper()
    if cat == 'HOMBRE':
        categorias = ['HOMBRE', 'MIXTO']
    elif cat == 'MUJER':
        categorias = ['MUJER', 'MIXTO']
    else:
        categorias = ['MIXTO']
    productos = Producto.objects.filter(categoria__in=categorias, descontinuado=False).exclude(imagen='').exclude(imagen__isnull=True)
    for p in productos:
        p.stock_total = sum(t.stock for t in TallaProducto.objects.filter(producto=p))
    return render(request, 'catalogo_categoria.html', {
        'productos': productos,
        'categoria': cat,
    })

def mis_compras(request):
    try:
        usuario_id = request.session.get('usuario_id')
        usuario = Usuario.objects.get(id=usuario_id)
        cliente = Cliente.objects.get(usuario=usuario)
        compras = (Venta.objects
                   .filter(cliente=cliente)
                   .prefetch_related('detalleventaproductos_set__producto')
                   .select_related('resena')
                   .order_by('-fecha_venta'))
    except (Cliente.DoesNotExist, Usuario.DoesNotExist):
        compras = []

    return render(request, 'usuarios/mis_compras.html', {'compras': compras})


def guardar_resena(request, venta_id):
    if request.method != 'POST':
        return redirect('mis_compras')

    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    try:
        usuario = Usuario.objects.get(id=usuario_id)
        cliente = Cliente.objects.get(usuario=usuario)
        venta = Venta.objects.get(id=venta_id, cliente=cliente)
    except (Usuario.DoesNotExist, Cliente.DoesNotExist, Venta.DoesNotExist):
        return redirect('mis_compras')

    if venta.estado not in ('Entregado', 'completada'):
        return redirect('mis_compras')

    estado_llegada = request.POST.get('estado_llegada', '')
    comentario = request.POST.get('comentario', '').strip()

    if estado_llegada not in ('bien', 'mal_estado', 'no_llego'):
        return redirect('mis_compras')

    ResenaVenta.objects.update_or_create(
        venta=venta,
        defaults={'estado_llegada': estado_llegada, 'comentario': comentario},
    )
    return redirect('mis_compras')

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

            columnas_requeridas = {'nombre', 'precio', 'descripcion'}
            if not columnas_requeridas.issubset(set(df.columns.str.lower())):
                messages.error(request, "El archivo debe tener las columnas: nombre, precio, descripcion")
                return redirect('carga_masiva')

            df.columns = df.columns.str.lower().str.strip()
            creados = 0
            actualizados = 0
            errores = []

            for i, fila in df.iterrows():
                try:
                    nombre_limpio = str(fila['nombre']).strip()
                    categoria = str(fila.get('categoria', 'MIXTO')).upper().strip()
                    if categoria not in ['HOMBRE', 'MUJER', 'MIXTO']:
                        categoria = 'MIXTO'
                    precio = fila['precio']
                    descripcion = str(fila.get('descripcion', '')).strip()

                    # Buscar producto existente por nombre (evita duplicados)
                    producto = Producto.objects.filter(nombre__iexact=nombre_limpio).first()
                    if producto:
                        producto.precio = precio
                        if descripcion:
                            producto.descripcion = descripcion
                        producto.categoria = categoria
                        producto.save()
                        actualizados += 1
                    else:
                        producto = Producto.objects.create(
                            nombre      = nombre_limpio,
                            precio      = precio,
                            descripcion = descripcion,
                            categoria   = categoria,
                            imagen      = '',
                        )
                        creados += 1

                    # Crear o actualizar talla/stock
                    talla_val = str(fila.get('talla', '')).strip().upper() if 'talla' in df.columns else ''
                    stock_val = fila.get('stock', 0) if 'stock' in df.columns else 0
                    stock_int = int(stock_val) if str(stock_val) not in ('nan', '', 'None') else 0
                    if talla_val:
                        TallaProducto.objects.update_or_create(
                            producto=producto,
                            talla=talla_val,
                            defaults={'stock': stock_int},
                        )

                    # Recalcular stock_total
                    producto.stock_total = sum(t.stock for t in TallaProducto.objects.filter(producto=producto))
                    producto.save()

                except Exception as e_fila:
                    errores.append(f"Fila {i+2}: {e_fila}")

            if creados:
                messages.success(request, f"✅ {creados} producto(s) nuevo(s) creado(s) correctamente.")
            if actualizados:
                messages.info(request, f"🔄 {actualizados} producto(s) existente(s) actualizado(s) (sin duplicar).")
            if errores:
                messages.warning(request, f"⚠ Errores en {len(errores)} fila(s): {' | '.join(errores[:5])}")

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
        tipo        = request.POST.get("tipo_movimiento")
        motivo      = request.POST.get("motivo", "")
        proveedor   = request.POST.get("proveedor", "")
        tallas_raw  = request.POST.get("tallas_data", "[]")

        producto = get_object_or_404(Producto, id=producto_id)

        try:
            pares   = json.loads(tallas_raw)
            creados = 0
            for par in pares:
                talla    = par.get("talla", "").strip()
                cantidad = int(par.get("cantidad", 0))
                if not talla or cantidad <= 0:
                    continue
                Movimiento.objects.create(
                    producto=producto,
                    talla=talla,
                    cantidad=cantidad,
                    tipo_movimiento=tipo,
                    motivo=motivo,
                    proveedor=proveedor,
                    nombre_producto=producto.nombre,
                )
                creados += 1
            if creados:
                messages.success(request, f"✅ {creados} movimiento(s) registrado(s) — {producto.nombre}.")
            else:
                messages.error(request, "Selecciona al menos una talla con cantidad válida.")
        except Exception as e:
            messages.error(request, f"Error: {e}")

        return redirect('panel_admin')

    return render(request, 'productos/movimiento_nuevo.html', {'productos': productos_qs})


_TALLAS_STD_ADULTO = ['S', 'M', 'L', 'XL']
_TALLAS_STD_NINO   = ['6', '8', '10', '12', '14', '16', '18']

def productos(request):
    from django.db.models import Count
    prods = Producto.objects.prefetch_related('tallas').annotate(
        num_ventas=Count('detalleventaproductos', distinct=True)
    ).all()
    for p in prods:
        tallas_qs = list(p.tallas.all())
        por_nombre = {t.talla: t for t in tallas_qs}
        p.stock_total = sum(t.stock for t in tallas_qs)
        p.tiene_ventas = p.num_ventas > 0

        def _row(nombre):
            t = por_nombre.get(nombre)
            return {'nombre': nombre, 'stock': t.stock if t else 0,
                    'existe': t is not None, 'id': t.id if t else None}

        p.tallas_adulto = [_row(n) for n in _TALLAS_STD_ADULTO]
        p.tallas_nino   = [_row(n) for n in _TALLAS_STD_NINO]
        p.tallas_faltantes = sum(
            1 for row in p.tallas_adulto + p.tallas_nino
            if not row['existe'] or row['stock'] == 0
        )
    return render(request, 'productos/productos.html', {'productos': prods})


def detalle_producto(request, id):
    producto = get_object_or_404(Producto, id=id, descontinuado=False)
    tallas   = TallaProducto.objects.filter(producto=producto)
    stock_total = sum(t.stock for t in tallas)
    if stock_total == 0:
        messages.error(request, 'Este producto está agotado.')
        return redirect('catalogo')
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

        try:
            precio_num = float(precio)
        except (TypeError, ValueError):
            messages.error(request, 'El precio debe ser un número válido.')
            return redirect('panel_admin')

        if precio_num < 1000:
            messages.error(request, 'El precio mínimo es $1.000. Ingresa un precio válido.')
            return redirect('panel_admin')

        if precio_num > 9_999_999:
            messages.error(request, 'El precio no puede superar $9.999.999. Verifica el valor ingresado.')
            return redirect('panel_admin')

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
        precio_raw = request.POST.get("precio")
        try:
            precio_num = float(precio_raw)
        except (TypeError, ValueError):
            messages.error(request, 'El precio debe ser un número válido.')
            return render(request, 'productos/producto_editar.html', {'producto': producto})

        if precio_num < 1000:
            messages.error(request, 'El precio mínimo es $1.000. Ingresa un precio válido.')
            return render(request, 'productos/producto_editar.html', {'producto': producto})

        if precio_num > 9_999_999:
            messages.error(request, 'El precio no puede superar $9.999.999. Verifica el valor ingresado.')
            return render(request, 'productos/producto_editar.html', {'producto': producto})

        producto.nombre      = request.POST.get("nombre")
        producto.precio      = precio_num
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

# ── Inventario y movimientos ──────────────────────────────────────────────────

def inventario(request):
    productos = Producto.objects.all()
    return render(request, 'productos/inventario.html', {'productos': productos})

def producto_eliminar(request, id):
    producto = get_object_or_404(Producto, id=id)

    if DetalleVentaProductos.objects.filter(producto=producto).exists():
        messages.error(
            request,
            f'No se puede eliminar "{producto.nombre}" porque está asociado a una o más ventas registradas.'
        )
        return redirect('productos')

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

    nombre_prod = producto.nombre
    producto.delete()

    Movimiento.objects.create(
        tipo_movimiento='evento',
        nombre_producto=f'Producto eliminado: {nombre_prod}',
        motivo=f'El producto "{nombre_prod}" fue eliminado del sistema.',
    )

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

            elif accion.startswith('set_'):
                key = accion.replace('set_', '')
                if key in carrito:
                    try:
                        qty = int(request.POST.get('nueva_cant', 1))
                        if qty > 0:
                            # Respetar el stock disponible
                            try:
                                pid = int(key.split('_')[0])
                                talla = carrito[key].get('talla', '')
                                stock = TallaProducto.objects.get(
                                    producto_id=pid, talla=talla).stock
                                qty = min(qty, stock)
                            except TallaProducto.DoesNotExist:
                                pass
                            carrito[key]['cantidad'] = max(1, qty)
                        else:
                            carrito.pop(key)
                    except (ValueError, TypeError):
                        pass

            request.session['carrito'] = carrito

        elif 'finalizar' in request.POST:

            # Verificar que el usuario tenga perfil completo
            usuario_id = request.session.get('usuario_id')
            usuario_fin = Usuario.objects.filter(id=usuario_id).first() if usuario_id else None
            if not usuario_fin:
                messages.error(request, 'Debes iniciar sesión para realizar una compra.')
                return redirect('login')
            if not _perfil_completo(usuario_fin):
                messages.error(request,
                    'Debes completar tu perfil antes de comprar. '
                    'Necesitamos tu nombre, teléfono, tipo de documento y cédula.')
                return redirect('perfil_incompleto')

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

    usuario_id = request.session.get('usuario_id')
    usuario_carrito = Usuario.objects.filter(id=usuario_id).first() if usuario_id else None
    perfil_ok = usuario_carrito and _perfil_completo(usuario_carrito)

    # Tallas disponibles y stock por producto
    pids_en_carrito = set()
    for key in carrito:
        try:
            pids_en_carrito.add(int(key.split('_')[0]))
        except (ValueError, IndexError):
            pass

    # {pid: {talla: stock}}
    stock_por_producto = {}
    for pid in pids_en_carrito:
        stock_por_producto[pid] = {
            t.talla: t.stock
            for t in TallaProducto.objects.filter(producto_id=pid)
        }

    # Enriquecer carrito con producto_id, tallas disponibles y stock límite
    carrito_enriquecido = {}
    for key, item in carrito.items():
        try:
            pid = int(key.split('_')[0])
        except (ValueError, IndexError):
            pid = None
        stocks = stock_por_producto.get(pid, {})
        talla_item = item.get('talla', '')
        stock_disp = stocks.get(talla_item, 0)
        tallas_disp = [t for t, s in stocks.items() if s > 0 and t != talla_item]
        carrito_enriquecido[key] = dict(item, producto_id=pid,
                                        tallas_disp=tallas_disp,
                                        stock_disp=stock_disp)

    return render(request, 'productos/carrito.html', {
        'productos': carrito_enriquecido,
        'total': total,
        'perfil_incompleto': usuario_carrito and not perfil_ok,
    })

def agregar_al_carrito(request, producto_id):
    carrito = request.session.get('carrito', {})
    producto = Producto.objects.get(id=producto_id)
    if request.method == 'POST':
        talla = request.POST.get('talla')
        key = f"{producto_id}_{talla}"
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
    usuario = Usuario.objects.filter(id=usuario_id).first() if usuario_id else None

    if not usuario:
        messages.error(request, 'Debes iniciar sesión para realizar una compra.')
        return redirect('login')

    if not _perfil_completo(usuario):
        messages.error(request,
            'Debes completar tu perfil antes de comprar. '
            'Necesitamos tu nombre, teléfono, tipo de documento y cédula.')
        return redirect('perfil_incompleto')

    cliente = Cliente.objects.filter(usuario=usuario).first()

    if not cliente:
        cliente = Cliente.objects.create(usuario=usuario)

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

            # Descontar stock de la talla
            try:
                talla_obj = TallaProducto.objects.get(producto=producto, talla=item["talla"])
                talla_obj.stock = max(0, talla_obj.stock - item["cantidad"])
                talla_obj.save()
            except TallaProducto.DoesNotExist:
                pass

            # Crear pedido para repartidor
            Pedido.objects.create(
                venta=venta,
                producto=producto,
                cantidad=item["cantidad"],
                total=Decimal(str(item["precio"])) * item["cantidad"],
                estado="Disponible",
                usuario=usuario
            )

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

        usuario_id = request.session.get('usuario_id')
        usuario = Usuario.objects.get(id=usuario_id)
        cliente = Cliente.objects.filter(usuario=usuario).first()
        if not cliente:
            cliente = Cliente.objects.create(usuario=usuario, direccion='')

        carrito = compra.get('carrito', {})

        venta = Venta.objects.create(
            cliente=cliente,
            cantProducto=compra['cantidad_total'],
            metodoEnvio=compra['metodo_envio'],
            totalVenta=compra['total_venta'],
            metodo_de_pago=compra['metodo_pago'],
            direccionEnvio=compra['direccion_envio'],
            telefonoContacto=compra['telefono_contacto'],
            observaciones=compra.get('observaciones', '')
        )

        for key, item in carrito.items():
            producto_id = key.split('_')[0]
            producto = Producto.objects.get(id=int(producto_id))

            DetalleVentaProductos.objects.create(
                venta=venta,
                producto=producto,
                talla=item['talla'],
                cantidad=item['cantidad'],
                precio_unitario=item['precio'],
                subtotal=item['precio'] * item['cantidad']
            )

            try:
                talla_obj = TallaProducto.objects.get(producto=producto, talla=item['talla'])
                talla_obj.stock = max(0, talla_obj.stock - item['cantidad'])
                talla_obj.save()
            except TallaProducto.DoesNotExist:
                pass

            Pedido.objects.create(
                venta=venta,
                producto=producto,
                cantidad=item['cantidad'],
                total=Decimal(str(item['precio'])) * item['cantidad'],
                estado='Disponible',
                usuario=usuario
            )

        request.session['carrito'] = {}
        request.session['compra'] = {}
        return redirect('factura', venta_id=venta.id)

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
    venta = get_object_or_404(Venta, id=venta_id)
    detalles = DetalleVentaProductos.objects.filter( venta=venta)
    cliente = venta.cliente
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="factura_{venta.id}.pdf"'
    )
    doc = SimpleDocTemplate(response)
    elementos = []
    estilos = getSampleStyleSheet()
    ruta_logo = os.path.join( settings.BASE_DIR, 'static/images/logo.png')
    if os.path.exists(ruta_logo):
        logo = Image(ruta_logo, width=120, height=60)
        elementos.append(logo)
    elementos.append(Spacer(1, 10))
    elementos.append(Paragraph("Factura - Deportes 360",estilos['Title']))
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"Cliente: {cliente.usuario.first_name}", estilos['Normal']))
    elementos.append(Paragraph(f"Dirección: {cliente.direccion}",estilos['Normal']))
    elementos.append(Paragraph(f"Teléfono: {venta.telefonoContacto}", estilos['Normal']))
    elementos.append(Spacer(1, 20))
    datos = [["Producto", "Talla", "Cantidad", "Precio Unitario", "Subtotal"]]
    for d in detalles:
        datos.append([d.producto.nombre, d.talla, str(d.cantidad), f"${d.precio_unitario}", f"${d.subtotal}" ])
    tabla = Table(datos)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append( Paragraph(f"Total: ${venta.totalVenta}", estilos['Heading2']))
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

    if not _perfil_completo(repartidor.usuario):
        messages.error(request, 'Debes completar tu perfil antes de tomar pedidos.')
        return redirect('repartidor')

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

def producto_discontinuar(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
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
    sug = get_object_or_404(Sugerencia, id=sugerencia_id)

    respuestas = []
    for r in sug.respuestas.all():
        respuestas.append({
            'mensaje':  r.mensaje,
            'es_admin': r.es_admin,
            'hora':     r.fecha.strftime('%d/%m/%Y %H:%M'),
        })

    return JsonResponse({
        'ok':         True,
        'nombre':     sug.nombre or 'Anónimo',
        'texto':      sug.mensaje,
        'fecha':      sug.fecha.strftime('%d/%m/%Y %H:%M'),
        'respuestas': respuestas,
    })

def sugerencias_lista(request):
    sugerencias = Sugerencia.objects.all().order_by('-fecha')
    data = []
    for s in sugerencias:
        ultima = s.respuestas.order_by('-fecha').first()
        last_msg = ultima.mensaje if ultima else s.mensaje
        data.append({
            'id':      s.id,
            'nombre':  s.nombre or 'Anónimo',
            'texto':   s.mensaje,
            'preview': (last_msg or '')[:60],
            'fecha':   s.fecha.strftime('%d/%m/%Y %H:%M'),
        })
    return JsonResponse({'sugerencias': data})

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