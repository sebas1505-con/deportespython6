from email.mime.image import MIMEImage
from inventario.models import Producto, Pedido, Movimiento, Venta, TallaProducto,DetalleVentaProductos, RespuestaSugerencia
from .models import Usuario, Cliente, Repartidor, Sugerencia, Administrador, Pedido, DetalleVentaProductos 
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from .forms import RegistroClienteForm, RepartidorForm
from .barrios import BARRIOS_BOGOTA
from django.core.mail import EmailMessage
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum, F
from django.utils.text import slugify
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models.functions import TruncDate
from django.db.models import Sum, Count
from datetime import date, timedelta
from django.db.models import Count, Avg, Sum
from django.db.models.functions import TruncDate, TruncMonth
import pandas as pd
import requests
import pandas as pd
import json
import uuid
import io

# ── Páginas generales ─────────────────────────────────────────────────────────

def index(request):
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.get(id=usuario_id) if usuario_id else None
    from inventario.models import Producto
    productos = Producto.objects.filter(descontinuado=False)[:6]
    return render(request, 'index.html', {
        'usuario': usuario,
        'productos': productos
    })

def quienes(request):
    return render(request, 'quienes.html')

def contacto(request):
    return render(request, 'contacto.html')

def contactousu(request):
    return render(request, 'contactousu.html')

def menu(request):
    return render(request, 'menu.html')

def sinacceso(request):
    return render(request, 'sinacceso.html')

def paginaNo(request):
    return render(request, 'paginaNo.html')


# ── Autenticación ─────────────────────────────────────────────────────────────

def login_view(request):
    if request.method == 'POST':
        correo = request.POST.get('correo')
        clave = request.POST.get('clave')
        try:
            usuario = Usuario.objects.get(email=correo)
            if check_password(clave, usuario.password):
                request.session['usuario_id'] = usuario.id
                request.session['rol'] = usuario.rol
                if usuario.rol == 'CLIENTE':
                    return redirect('usuario')
                elif usuario.rol == 'REPARTIDOR':
                    return redirect('repartidor')
                elif usuario.rol == 'ADMIN':
                    return redirect('panel_admin')
            else:
                messages.error(request, "Contraseña incorrecta")
        except Usuario.DoesNotExist:
            messages.error(request, "Usuario no registrado")
    return render(request, 'login.html')

def logout_view(request):
    request.session.flush()
    return redirect('login')


# ── Registro ──────────────────────────────────────────────────────────────────

def registro_cliente(request):
    if request.method == 'POST':
        first_name         = request.POST.get('first_name', '').strip()
        email              = request.POST.get('email', '').strip()
        username           = request.POST.get('username', '').strip()
        password           = request.POST.get('password', '')
        confirmar_password = request.POST.get('confirmar_password', '')
        telefono           = request.POST.get('telefono', '').strip()

        if password != confirmar_password:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('registro')

        if Usuario.objects.filter(username=username).exists():
            messages.error(request, 'Ese nombre de usuario ya está en uso.')
            return redirect('registro')

        if Usuario.objects.filter(email=email).exists():
            messages.error(request, 'Ese correo ya está registrado.')
            return redirect('registro')

        Usuario.objects.create(
            first_name = first_name,
            email      = email,
            username   = username,
            password   = make_password(password),
            telefono   = telefono,
            rol        = 'CLIENTE',
        )
        messages.success(request, '✅ Cuenta creada. Ya puedes iniciar sesión.')
        return redirect('login')

    return render(request, 'registro.html')

def crear_repartidor(request):

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        email      = request.POST.get('email', '').strip()
        username   = request.POST.get('username', '').strip()
        telefono   = request.POST.get('telefono', '').strip()
        password   = request.POST.get('password', '')
        confirmar  = request.POST.get('confirmar', '')
        vehiculo   = request.POST.get('vehiculo', '').strip()
        placa      = request.POST.get('placa', '').strip()

        if password != confirmar:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('crear_repartidor')

        if len(password) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
            return redirect('crear_repartidor')

        if Usuario.objects.filter(username=username).exists():
            messages.error(request, 'Ese nombre de usuario ya está en uso.')
            return redirect('crear_repartidor')

        if Usuario.objects.filter(email=email).exists():
            messages.error(request, 'Ese correo ya está registrado.')
            return redirect('crear_repartidor')

        usuario = Usuario.objects.create(
            first_name = first_name,
            email      = email,
            username   = username,
            password   = make_password(password),
            telefono   = telefono,
            rol        = 'REPARTIDOR',
        )

        Repartidor.objects.create(
            usuario = usuario,
            vehiculo = vehiculo,
            placa    = placa,
        )

        messages.success(request, '✅ Registro exitoso. Ya puedes iniciar sesión.')
        return redirect('login')

    return render(request, 'crear-repartidor.html', {})

def crear_admin(request):
    if request.method == "POST":
        usuario_val    = request.POST.get("usuario")
        correo         = request.POST.get("correo")
        telefono       = request.POST.get("telefono")
        codigo         = request.POST.get("codigo")
        contrasena     = request.POST.get("contrasena")
        confirmar      = request.POST.get("confirmar")
        first_name     = request.POST.get("first_name")
        fecha_nac      = request.POST.get("fecha_nacimiento")
        barrio         = request.POST.get("barrio")
        localidad      = request.POST.get("localidad")
        tipo_documento = request.POST.get("tipo_documento")
        cedula         = request.POST.get("cedula")

        if contrasena != confirmar:
            return render(request, "crear_admin.html", {"error": "Las contraseñas no coinciden"})
        if codigo not in ["ADM-123", "ADM-456"]:
            return render(request, "crear_admin.html", {"error": "Código incorrecto"})
        if Usuario.objects.filter(username=usuario_val).exists():
            return render(request, "crear_admin.html", {"error": "El usuario ya existe"})
        if Usuario.objects.filter(cedula=cedula).exists():
            return render(request, "crear_admin.html", {"error": "La cédula ya está registrada"})

        usuario = Usuario.objects.create(
            username=usuario_val,
            email=correo,
            telefono=telefono,
            password=make_password(contrasena),
            rol="ADMIN",
            first_name=first_name,
            fecha_nacimiento=fecha_nac if fecha_nac else None,
            barrio=barrio,
            localidad=localidad,
            tipo_documento=tipo_documento,
            cedula=cedula,
            is_staff=True,
            is_superuser=True
        )
        Administrador.objects.create(codigo=codigo, usuario=usuario)
        return redirect("panel_admin")
    return render(request, "crear_admin.html")


# ── Dashboards por rol ────────────────────────────────────────────────────────

def usuario(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    if not usuario_id or rol != "CLIENTE":
        return redirect("sinacceso")

    usuario = Usuario.objects.get(id=usuario_id)
    categoria = request.GET.get("categoria")

    from inventario.models import Producto
    if categoria == "HOMBRE":
        productos = Producto.objects.filter(categoria__in=["HOMBRE", "MIXTO"], descontinuado=False)
    elif categoria == "MUJER":
        productos = Producto.objects.filter(categoria__in=["MUJER", "MIXTO"], descontinuado=False)
    elif categoria == "MIXTO":
        productos = Producto.objects.filter(categoria="MIXTO", descontinuado=False)
    else:
        productos = Producto.objects.filter(descontinuado=False) 

    return render(request, "usuario.html", {"usuario": usuario, "productos": productos})

def catalogoindex(request):
    categoria = request.GET.get('categoria')  # lee el parámetro de la URL
    if categoria:
        productos = Producto.objects.filter(categoria__iexact=categoria)
    else:
        productos = Producto.objects.all()

    return render(request, 'catalogoindex.html', {'productos': productos})

def admin(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    if not usuario_id or rol != 'ADMIN':
        return redirect('sinacceso')

    hoy = date.today()

    # ── Carga masiva ─────────────────────────────────────────────────────────
    if request.method == "POST" and request.FILES.get("archivo"):
        archivo = request.FILES["archivo"]
        tipo_carga = request.POST.get("tipo_carga", "productos")
        try:
            if archivo.name.endswith(".csv"):
                df = pd.read_csv(io.TextIOWrapper(archivo.file, encoding="utf-8"))
            elif archivo.name.endswith(".xlsx"):
                df = pd.read_excel(archivo)
            else:
                messages.error(request, "Solo se permiten archivos CSV o Excel")
                return redirect("panel_admin")

            if tipo_carga == "productos":
                columnas = ["id", "nombre", "slug", "precio", "descripcion", "imagen", "categoria"]
                if not all(col in df.columns for col in columnas):
                    messages.error(request, "El archivo no tiene las columnas requeridas para productos")
                    return redirect("panel_admin")
                for _, fila in df.iterrows():
                    Producto.objects.update_or_create(
                        id=int(fila["id"]),
                        defaults={
                            "nombre":      str(fila["nombre"]),
                            "slug":        slugify(f"{fila['nombre']}-{fila['id']}"),
                            "precio":      float(fila["precio"]),
                            "descripcion": str(fila["descripcion"]),
                            "categoria":   str(fila["categoria"]).upper(),
                            "imagen":      fila["imagen"] if fila["imagen"] else None,
                        }
                    )
                messages.success(request, "✅ Productos cargados correctamente")

            elif tipo_carga == "stock":
                columnas = ["id", "talla", "stock", "producto_id"]
                if not all(col in df.columns for col in columnas):
                    messages.error(request, "El archivo no tiene las columnas requeridas para stock")
                    return redirect("panel_admin")
                for _, fila in df.iterrows():
                    if int(fila["stock"]) < 0:
                        messages.warning(request, f"Stock negativo en producto {fila['producto_id']} - talla {fila['talla']}")
                        continue
                    TallaProducto.objects.update_or_create(
                        id=int(fila["id"]),
                        defaults={
                            "talla":       str(fila["talla"]),
                            "stock":       int(fila["stock"]),
                            "producto_id": int(fila["producto_id"]),
                        }
                    )
                messages.success(request, "✅ Stock cargado correctamente")

        except Exception as e:
            messages.error(request, f"Error al procesar archivo: {e}")
        return redirect("panel_admin")

    # ── Fechas con filtro GET ─────────────────────────────────────────────────
    fecha_inicio = request.GET.get('fecha_inicio') or hoy.replace(day=1).strftime('%Y-%m-%d')
    fecha_fin    = request.GET.get('fecha_fin')    or hoy.strftime('%Y-%m-%d')

    # ── Movimientos ───────────────────────────────────────────────────────────
    movimientos_qs   = Movimiento.objects.select_related('producto').prefetch_related('producto__tallas').order_by('-fecha')
    total_entradas   = movimientos_qs.filter(tipo_movimiento='entrada').count()
    total_salidas    = movimientos_qs.filter(tipo_movimiento='salida').count()
    unidades_entrada = movimientos_qs.filter(tipo_movimiento='entrada').aggregate(t=Sum('cantidad'))['t'] or 0
    unidades_salida  = movimientos_qs.filter(tipo_movimiento='salida').aggregate(t=Sum('cantidad'))['t'] or 0

    # ── Ventas filtradas ──────────────────────────────────────────────────────
    ventas = Venta.objects.select_related('cliente__usuario').order_by('-fecha_venta')
    if fecha_inicio:
        ventas = ventas.filter(fecha_venta__date__gte=fecha_inicio)
    if fecha_fin:
        ventas = ventas.filter(fecha_venta__date__lte=fecha_fin)

    cantidad_ventas   = ventas.count()
    total_general     = ventas.aggregate(t=Sum('totalVenta'))['t'] or 0
    clientes_unicos   = ventas.values('cliente').distinct().count()
    ticket_avg        = ventas.aggregate(Avg('totalVenta'))['totalVenta__avg'] or 0
    unidades_vendidas = ventas.aggregate(t=Sum('cantProducto'))['t'] or 0
    ventas_pse        = ventas.filter(metodo_de_pago__in=['PSE', 'PAGO_EN_LINEA']).count()
    ventas_ce         = ventas.exclude(metodo_de_pago__in=['PSE', 'PAGO_EN_LINEA']).count()

    # ── Gráfico evolución por fecha ───────────────────────────────────────────
    ventas_por_fecha = (
        ventas.annotate(dia=TruncDate('fecha_venta'))
              .values('dia')
              .annotate(total=Sum('totalVenta'), cantidad=Count('id'))
              .order_by('dia')
    )
    fechas_ventas  = json.dumps([str(v['dia']) for v in ventas_por_fecha])
    totales_ventas = json.dumps([float(v['total']) for v in ventas_por_fecha])
    cant_ventas    = json.dumps([v['cantidad'] for v in ventas_por_fecha])

    # ── Gráfico top productos ─────────────────────────────────────────────────
    ventas_por_producto = (
        DetalleVentaProductos.objects
        .filter(
            venta__fecha_venta__date__gte=fecha_inicio,
            venta__fecha_venta__date__lte=fecha_fin,
        )
        .values('producto__nombre')
        .annotate(total=Sum('subtotal'))
        .order_by('-total')[:10]
    )
    nombres_productos = json.dumps([v['producto__nombre'] for v in ventas_por_producto])
    totales_productos = json.dumps([float(v['total']) for v in ventas_por_producto])

    # ── Top productos para tabla ──────────────────────────────────────────────
    top_raw = (
        DetalleVentaProductos.objects
        .filter(
            venta__fecha_venta__date__gte=fecha_inicio,
            venta__fecha_venta__date__lte=fecha_fin,
        )
        .values('producto__nombre')
        .annotate(total_unidades=Sum('cantidad'), total_ingresos=Sum('subtotal'))
        .order_by('-total_ingresos')[:10]
    )
    total_ingresos_global = float(total_general) if total_general else 1
    top_productos = [
        {
            'nombre':         p['producto__nombre'],
            'total_unidades': p['total_unidades'],
            'total_ingresos': float(p['total_ingresos'] or 0),
            'porcentaje':     round(min(float(p['total_ingresos'] or 0) / total_ingresos_global * 100, 100), 1),
        }
        for p in top_raw
    ]

    # ── Resumen mensual (últimos 12 meses) ────────────────────────────────────
    desde_12 = hoy - timedelta(days=365)
    por_mes = (
        Venta.objects.filter(fecha_venta__date__gte=desde_12)
        .annotate(mes=TruncMonth('fecha_venta'))
        .values('mes')
        .annotate(
            cantidad=Count('id'),
            total=Sum('totalVenta'),
            ticket=Avg('totalVenta'),
            clientes=Count('cliente', distinct=True),
        )
        .order_by('mes')
    )
    meses_es = [
        'Enero','Febrero','Marzo','Abril','Mayo','Junio',
        'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'
    ]
    meses_data = json.dumps([
        {
            'label':    meses_es[m['mes'].month - 1] + ' ' + str(m['mes'].year),
            'cantidad': m['cantidad'],
            'total':    float(m['total'] or 0),
            'ticket':   float(m['ticket'] or 0),
            'clientes': m['clientes'],
        }
        for m in por_mes
    ])

    # ── Resto de datos ────────────────────────────────────────────────────────
    ultimos_pedidos = Pedido.objects.select_related(
        'usuario', 'producto', 'venta__cliente__usuario'
    ).order_by('-fecha_pedido')[:10]

    usuarios    = Usuario.objects.all()
    sugerencias = Sugerencia.objects.all().order_by('-fecha')
    productos   = Producto.objects.prefetch_related('tallas').all()

    return render(request, 'productos/admin.html', {
        # generales
        'ultimos_pedidos':   ultimos_pedidos,
        'usuarios':          usuarios,
        'ventas':            ventas,
        'movimientos':       movimientos_qs,
        'sugerencias':       sugerencias,
        'productos':         productos,
        # métricas ventas
        'cantidad_ventas':   cantidad_ventas,
        'total_general':     total_general,
        'clientes_unicos':   clientes_unicos,
        'ticket_promedio':   round(float(ticket_avg), 0),
        'unidades_vendidas': unidades_vendidas,
        'ventas_pse':        ventas_pse or 0,  
        'ventas_ce':         ventas_ce  or 0,   
        'top_productos':     top_productos,
        # métricas movimientos
        'total_entradas':    total_entradas,
        'total_salidas':     total_salidas,
        'unidades_entrada':  unidades_entrada,
        'unidades_salida':   unidades_salida,
        # gráficos JSON
        'fechas_ventas':     fechas_ventas,
        'totales_ventas':    totales_ventas,
        'cant_ventas':       cant_ventas,
        'nombres_productos': nombres_productos,
        'totales_productos': totales_productos,
        'meses_data':        meses_data,
    })

def perfil_admin(request):

    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    if not usuario_id or rol != 'ADMIN':
        return redirect('sinacceso')

    admin = get_object_or_404(Usuario, id=usuario_id)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        # ── Guardar perfil ──────────────────────────────────────
        if accion == 'perfil':
            admin.first_name    = request.POST.get('first_name', admin.first_name).strip()
            admin.email         = request.POST.get('email', admin.email).strip()
            admin.telefono      = request.POST.get('telefono', admin.telefono).strip()
            admin.barrio        = request.POST.get('barrio', '').strip() or None
            admin.localidad     = request.POST.get('localidad', '').strip() or None
            admin.tipo_documento= request.POST.get('tipo_documento', '').strip() or None
            admin.cedula        = request.POST.get('cedula', '').strip() or None

            fecha_nac = request.POST.get('fecha_nacimiento', '')
            if fecha_nac:
                try:
                    from datetime import datetime
                    admin.fecha_nacimiento = datetime.strptime(fecha_nac, '%Y-%m-%d').date()
                except ValueError:
                    pass

            # Cambiar username solo si no existe ya
            nuevo_username = request.POST.get('username', admin.username).strip()
            if nuevo_username != admin.username:
                if Usuario.objects.filter(username=nuevo_username).exclude(id=admin.id).exists():
                    messages.error(request, 'Ese nombre de usuario ya está en uso.')
                    return redirect('perfil_admin')
                admin.username = nuevo_username

            admin.save()
            messages.success(request, '✅ Perfil actualizado correctamente.')
            return redirect('perfil_admin')

        # ── Cambiar contraseña ──────────────────────────────────
        elif accion == 'password':
            pwd_actual    = request.POST.get('password_actual', '')
            pwd_nueva     = request.POST.get('password_nueva', '')
            pwd_confirmar = request.POST.get('password_confirmar', '')

            if not check_password(pwd_actual, admin.password):
                messages.error(request, 'La contraseña actual no es correcta.')
                return redirect('perfil_admin')

            if len(pwd_nueva) < 8:
                messages.error(request, 'La nueva contraseña debe tener al menos 8 caracteres.')
                return redirect('perfil_admin')

            if pwd_nueva != pwd_confirmar:
                messages.error(request, 'Las contraseñas nuevas no coinciden.')
                return redirect('perfil_admin')

            admin.password = make_password(pwd_nueva)
            admin.save()
            messages.success(request, '✅ Contraseña cambiada correctamente.')
            return redirect('perfil_admin')

    # ── Stats para el panel ──────────────────────────────────────
    total_ventas   = Venta.objects.count()
    total_usuarios = Usuario.objects.count()
    total_productos = Producto.objects.filter(descontinuado=False).count()

    return render(request, 'usuarios/perfil_admin.html', {
        'admin':           admin,
        'total_ventas':    total_ventas,
        'total_usuarios':  total_usuarios,
        'total_productos': total_productos,
    })

def repartidor(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    if not usuario_id or rol != 'REPARTIDOR':
        return redirect('sinacceso')

    try:
        repartidor_obj = Repartidor.objects.get(usuario__id=usuario_id)
    except Repartidor.DoesNotExist:
        return redirect('sinacceso')

    usuario = Usuario.objects.get(id=usuario_id)

    ventas_pendientes = Pedido.objects.filter(estado='Disponible', repartidor=None)\
                              .select_related('venta__cliente__usuario')
    pedidos_activos   = Pedido.objects.filter(repartidor=repartidor_obj, estado='En camino')\
                              .select_related('venta__cliente__usuario')
    mis_pedidos       = Pedido.objects.filter(repartidor=repartidor_obj, estado='Entregado')\
                              .select_related('venta__cliente__usuario')

    # Ganancias
    total_ganancias = mis_pedidos.aggregate(
        total=Sum('valor_domicilio')
    )['total'] or 0

    return render(request, 'repartidor.html', {
        'Nombre':            usuario.first_name,
        'usuario':           usuario,
        'repartidor':        repartidor_obj,
        'ventas_pendientes': ventas_pendientes,
        'pedidos_activos':   pedidos_activos,
        'mis_pedidos':       mis_pedidos,
        'total_ganancias':   total_ganancias,
    })


# ── Perfil y cuenta ───────────────────────────────────────────────────────────

def perfil_usuario(request):

    usuario_id = request.session.get('usuario_id')
    rol        = request.session.get('rol')
    if not usuario_id or rol != 'CLIENTE':
        return redirect('sinacceso')

    usuario = get_object_or_404(Usuario, id=usuario_id)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'perfil':
            usuario.first_name     = request.POST.get('first_name', '').strip() or usuario.first_name
            usuario.email          = request.POST.get('email', '').strip() or usuario.email
            usuario.telefono       = request.POST.get('telefono', '').strip()
            usuario.tipo_documento = request.POST.get('tipo_documento', '').strip() or None
            usuario.cedula         = request.POST.get('cedula', '').strip() or None
            usuario.localidad      = request.POST.get('localidad', '').strip() or None
            usuario.barrio         = request.POST.get('barrio', '').strip() or None

            fecha_nac = request.POST.get('fecha_nacimiento', '')
            if fecha_nac:
                try:
                    from datetime import datetime
                    usuario.fecha_nacimiento = datetime.strptime(fecha_nac, '%Y-%m-%d').date()
                except ValueError:
                    pass

            usuario.save()
            messages.success(request, '✅ Perfil actualizado correctamente.')
            return redirect('perfil')          # ← antes: 'usuario.html'

        elif accion == 'password':
            pwd_actual    = request.POST.get('password_actual', '')
            pwd_nueva     = request.POST.get('password_nueva', '')
            pwd_confirmar = request.POST.get('password_confirmar', '')

            if not check_password(pwd_actual, usuario.password):
                messages.error(request, 'La contraseña actual no es correcta.')
                return redirect('perfil')      # ← antes: 'perfil_usuario'

            if len(pwd_nueva) < 8:
                messages.error(request, 'La nueva contraseña debe tener al menos 8 caracteres.')
                return redirect('perfil')      # ← antes: 'perfil_usuario'

            if pwd_nueva != pwd_confirmar:
                messages.error(request, 'Las contraseñas nuevas no coinciden.')
                return redirect('perfil')      # ← antes: 'perfil_usuario'

            usuario.password = make_password(pwd_nueva)
            usuario.save()
            messages.success(request, '✅ Contraseña cambiada correctamente.')
            return redirect('perfil')          # ← antes: 'perfil_usuario'

    campos = [
        usuario.first_name, usuario.email, usuario.telefono,
        usuario.tipo_documento, usuario.cedula,
        usuario.localidad, usuario.barrio, usuario.fecha_nacimiento,
    ]
    completados = sum(1 for c in campos if c)
    progreso    = round(completados / len(campos) * 100)

    localidades = [
        'Usaquén', 'Chapinero', 'Santa Fe', 'San Cristóbal', 'Usme',
        'Tunjuelito', 'Bosa', 'Kennedy', 'Fontibón', 'Engativá', 'Suba',
        'Barrios Unidos', 'Teusaquillo', 'Los Mártires', 'Antonio Nariño',
        'Puente Aranda', 'La Candelaria', 'Rafael Uribe Uribe',
        'Ciudad Bolívar', 'Sumapaz',
    ]

    return render(request, 'usuarios/perfil.html', {
        'usuario':     usuario,
        'progreso':    progreso,
        'localidades': localidades,
    })

def perfil_repartidor(request):

    usuario_id = request.session.get('usuario_id')
    rol        = request.session.get('rol')
    if not usuario_id or rol != 'REPARTIDOR':
        return redirect('sinacceso')

    usuario    = get_object_or_404(Usuario, id=usuario_id)
    repartidor = get_object_or_404(Repartidor, usuario=usuario)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        # ── Guardar perfil ──────────────────────────────────────
        if accion == 'perfil':
            usuario.first_name     = request.POST.get('first_name', '').strip() or usuario.first_name
            usuario.email          = request.POST.get('email', '').strip() or usuario.email
            usuario.telefono       = request.POST.get('telefono', '').strip()
            usuario.tipo_documento = request.POST.get('tipo_documento', '').strip() or None
            usuario.cedula         = request.POST.get('cedula', '').strip() or None
            usuario.localidad      = request.POST.get('localidad', '').strip() or None

            fecha_nac = request.POST.get('fecha_nacimiento', '')
            if fecha_nac:
                try:
                    from datetime import datetime
                    usuario.fecha_nacimiento = datetime.strptime(fecha_nac, '%Y-%m-%d').date()
                except ValueError:
                    pass

            # Vehículo y placa
            vehiculo = request.POST.get('vehiculo', '').strip()
            placa    = request.POST.get('placa', '').strip()
            if vehiculo:
                repartidor.vehiculo = vehiculo
            if placa:
                repartidor.placa = placa

            usuario.save()
            repartidor.save()
            messages.success(request, '✅ Perfil actualizado correctamente.')
            return redirect('perfil_repartidor')

        # ── Cambiar contraseña ──────────────────────────────────
        elif accion == 'password':
            pwd_actual    = request.POST.get('password_actual', '')
            pwd_nueva     = request.POST.get('password_nueva', '')
            pwd_confirmar = request.POST.get('password_confirmar', '')

            if not check_password(pwd_actual, usuario.password):
                messages.error(request, 'La contraseña actual no es correcta.')
                return redirect('perfil_repartidor')

            if len(pwd_nueva) < 8:
                messages.error(request, 'La nueva contraseña debe tener al menos 8 caracteres.')
                return redirect('perfil_repartidor')

            if pwd_nueva != pwd_confirmar:
                messages.error(request, 'Las contraseñas nuevas no coinciden.')
                return redirect('perfil_repartidor')

            usuario.password = make_password(pwd_nueva)
            usuario.save()
            messages.success(request, '✅ Contraseña cambiada correctamente.')
            return redirect('perfil_repartidor')

    # ── Progreso del perfil ──────────────────────────────────────
    campos = [
        usuario.first_name, usuario.email, usuario.telefono,
        usuario.tipo_documento, usuario.cedula, usuario.localidad,
        usuario.fecha_nacimiento, repartidor.vehiculo, repartidor.placa,
    ]
    completados = sum(1 for c in campos if c)
    progreso    = round(completados / len(campos) * 100)

    localidades = [
        'Usaquén', 'Chapinero', 'Santa Fe', 'San Cristóbal', 'Usme',
        'Tunjuelito', 'Bosa', 'Kennedy', 'Fontibón', 'Engativá', 'Suba',
        'Barrios Unidos', 'Teusaquillo', 'Los Mártires', 'Antonio Nariño',
        'Puente Aranda', 'La Candelaria', 'Rafael Uribe Uribe',
        'Ciudad Bolívar', 'Sumapaz',
    ]

    return render(request, 'usuarios/perfil_repartidor.html', {
        'usuario':     usuario,
        'repartidor':  repartidor,
        'progreso':    progreso,
        'localidades': localidades,
    })

def actualizar_usuario(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    if not usuario_id or rol != "CLIENTE":
        return redirect("sinacceso")
    usuario = Usuario.objects.get(id=usuario_id)
    if request.method == 'POST':
        form = RegistroClienteForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            return redirect('perfil')
    else:
        form = RegistroClienteForm(instance=usuario)
    return render(request, 'usuarios/actualizar_usuario.html', {'form': form})

def eliminar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    usuario.delete()
    return redirect('panel_admin')

def pedidos_disponibles(request):
    pedidos = Pedido.objects.filter(estado__in=['disponible', 'Pendiente'] )
    return render(request, 'usuarios/pedidos_disponibles.html', {'pedidos': pedidos})

def tomar_pedido(request, pedido_id):
    usuario_id = request.session.get('usuario_id')
    repartidor_obj = get_object_or_404(Repartidor, usuario__id=usuario_id)
    pedido = get_object_or_404(Pedido, id=pedido_id)
    pedido.estado = 'En camino'  
    pedido.repartidor = repartidor_obj  
    pedido.save()
    messages.success(request, "Pedido tomado correctamente.")
    return redirect('repartidor')

def entregar_pedido(request, pedido_id):
    usuario_id = request.session.get('usuario_id')
    repartidor_obj = get_object_or_404(Repartidor, usuario__id=usuario_id)
    pedido = get_object_or_404(Pedido, id=pedido_id, repartidor=repartidor_obj)
    pedido.estado = 'Entregado'  
    pedido.save()
    messages.success(request, "Pedido marcado como entregado.")
    return redirect('repartidor')

def mis_pedidos(request):
    pedidos = Pedido.objects.filter(repartidor=request.user, estado='Entregado')
    return render(request, 'usuarios/repartidor.html', {'mis_pedidos': pedidos})

def detalle_pedido(request, pedido_id):
    usuario_id = request.session.get('usuario_id')
    try:
        repartidor = Repartidor.objects.get(usuario__id=usuario_id)
    except Repartidor.DoesNotExist:
        return redirect('login')

    pedido = get_object_or_404(Pedido, id=pedido_id)
    venta = pedido.venta
    detalles = DetalleVentaProductos.objects.filter(venta_id=venta.id)

    return render(request, 'detalle_pedido.html', {
        'pedido': pedido,
        'venta': venta,
        'repartidor': repartidor,
        'detalles': detalles,
    })

# ── Sugerencias ───────────────────────────────────────────────────────────────

def sugerencias(request):
    from django.http import JsonResponse

    usuario_id = request.session.get('usuario_id')
    usuario = get_object_or_404(Usuario, id=usuario_id)
    nombre = usuario.first_name or usuario.username

    if request.method == 'POST':
        texto         = request.POST.get('texto', '').strip()
        sugerencia_id = request.POST.get('sugerencia_id')

        if sugerencia_id:
            # Respuesta a conversación existente
            sug = get_object_or_404(Sugerencia, id=sugerencia_id)
            RespuestaSugerencia.objects.create(
                sugerencia = sug,
                mensaje    = texto,
                es_admin   = False
            )
            return JsonResponse({'ok': True, 'mensaje': texto})

        # Nueva sugerencia — reusar la existente si ya tiene una
        if texto:
            sug_existente = Sugerencia.objects.filter(nombre=nombre).first()
            if sug_existente:
                # Agregar como respuesta a la conversación existente
                RespuestaSugerencia.objects.create(
                    sugerencia = sug_existente,
                    mensaje    = texto,
                    es_admin   = False
                )
            else:
                # Crear nueva solo si no existe ninguna
                Sugerencia.objects.create(
                    nombre  = nombre,
                    texto   = texto,
                )
            messages.success(request, '✅ Mensaje enviado.')
        return redirect('sugerencias')

    
    mi_sugerencia = Sugerencia.objects.filter(
        nombre=nombre
    ).order_by('-fecha').first()

    return render(request, 'sugerencias.html', {
        'mi_sugerencia': mi_sugerencia,
        'usuario':       usuario,
    })

def panel_sugerencias(request):
    sugerencias = Sugerencia.objects.all().order_by('-fecha')
    return render(request, "panel_sugerencias.html", {"sugerencias": sugerencias})

# ── Recuperación de contraseña ────────────────────────────────────────────────

def restablecer_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            messages.error(request, "Debes ingresar un correo.")
            return redirect('restablecer')

        usuario = Usuario.objects.filter(email__iexact=email.strip().lower()).first()
        if usuario:
            token = str(uuid.uuid4())
            usuario.token_recuperacion = token
            usuario.save()
            enlace = f"http://127.0.0.1:8000/nueva_contrasena/{token}/"
        cuerpo = f"""
<html>
  <body style="font-family:Arial,sans-serif; background:#f5f5f5; padding:20px;">
    <div style="max-width:600px; margin:auto; border-radius:10px; overflow:hidden;
                box-shadow:0 4px 12px rgba(0,0,0,0.1);">

      <!-- Encabezado con fondo deportivo -->
      <div style="background-image:url('https://upload.wikimedia.org/wikipedia/commons/5/51/Football_pitch.jpg');
                  background-size:cover; background-position:center; padding:30px; text-align:center; color:#fff;">
        <img src="https://tuservidor.com/static/images/pelota-futbol.png"
            alt="Balón" width="70" style="margin-bottom:10px;">
        <h2 style="margin:0;">Recuperar Contraseña</h2>
        <p style="margin:0;">Deportes360</p>
      </div>

      <!-- Contenido -->
      <div style="background:#fff; padding:30px; text-align:center;">
        <p style="font-size:16px; color:#333;">
          Hola <strong>{usuario.first_name or 'Jugador'}</strong>,
        </p>
        <p style="font-size:15px; color:#555;">
          Haz clic en el botón para restablecer tu contraseña y volver al a iniar sesion:
        </p>
        <a href="{enlace}" style="display:inline-block; background:#3b82f6; color:#fff;
           padding:14px 28px; border-radius:6px; text-decoration:none; font-weight:bold;
           margin-top:20px;">Restablecer Contraseña</a>
        <p style="margin-top:25px; font-size:12px; color:#999;">
          Si no solicitaste este cambio, ignora este correo.
        </p>
      </div>
    </div>
  </body>
</html>
"""



        correo = EmailMessage(
                subject="Recuperación de contraseña",
                body=cuerpo,
                from_email="juancerquera104@gmail.com",
                to=[usuario.email],
            )
        correo.content_subtype = "html"
        correo.send(fail_silently=False)

        messages.success(request, "El correo se envió exitosamente.")
        return redirect('restablecer')
    return render(request, 'restablecer.html')

def nueva_contrasena(request, token=None):
    usuario = Usuario.objects.filter(token_recuperacion=token).first() if token else None
    if not usuario:
        messages.error(request, 'Enlace inválido o expirado.')
        return redirect('login')

    if request.method == "POST":
        password1 = request.POST.get('password')
        password2 = request.POST.get('confirm_password')
        if not password1 or not password2:
            messages.error(request, 'Completa ambos campos.')
        elif password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
        elif len(password1) < 6:
            messages.error(request, 'Debe tener mínimo 6 caracteres.')
        else:
            usuario.password = make_password(password1)
            usuario.token_recuperacion = None
            usuario.save()
            messages.success(request, 'Contraseña actualizada correctamente.')
            return redirect('login')
    return render(request, 'usuarios/nueva_contrasena.html')


# ── API ───────────────────────────────────────────────────────────────────────

@api_view(['GET'])
def localidades_bogota(request):
    try:
        url = "https://www.datos.gov.co/resource/93dx-5ayx.json"
        params = {
            "$select": "localidad_nombre",
            "$group": "localidad_nombre",
            "$order": "localidad_nombre ASC",
            "$limit": 25
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        localidades = [{"nombre": item["localidad_nombre"]} for item in data if "localidad_nombre" in item]
        return Response(localidades)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
def barrios_bogota(request):
    localidad = request.GET.get('localidad', '')
    try:
        url = "https://bogota-laburbano.opendatasoft.com/api/records/1.0/search/"
        params = {
            "dataset": "poligonos-barrios",
            "q": localidad,
            "facet": "localidad",
            "refine.localidad": localidad,
            "rows": 200,
            "fields": "nombre_bar,localidad"
        }
        response = requests.get(url, params=params, timeout=8)
        data = response.json()
        
        barrios = sorted(set(
            r["fields"]["nombre_bar"]
            for r in data.get("records", [])
            if "nombre_bar" in r.get("fields", {})
        ))
        
        return Response([{"nombre": b} for b in barrios])

    except Exception:
        # Fallback a tu lista local si la API falla
        from .barrios import BARRIOS_BOGOTA
        barrios_locales = [
            {"nombre": b["nombre"]}
            for b in BARRIOS_BOGOTA
            if b["localidad"].lower() == localidad.lower()
        ]
        return Response(barrios_locales)

# ── Utilidades ────────────────────────────────────────────────────────────────

def prueba_correo(request):
    correo = EmailMessage(
        subject="Prueba de correo",
        body="Este es un correo de prueba desde Django.",
        from_email="Soporte Deportes360 <tucorreo@gmail.com>",
        to=["juancerquera104@gmail.com"],
    )
    correo.send(fail_silently=False)
    return HttpResponse("Correo enviado correctamente")

