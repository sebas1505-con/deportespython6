<<<<<<< HEAD
from django.shortcuts import render, redirect, get_object_or_404
=======
from django.shortcuts import render, redirect,get_object_or_404, redirect
from .models import Usuario, Cliente, Repartidor, Producto, TallaProducto, Venta, Sugerencia, Movimiento, Pedido
from .forms import AdminForm, RepartidorForm, SeleccionTallaForm, RegistroClienteForm, CompraForm, ReportesForm, MovimientoForm
>>>>>>> db314d50cd58dd5270c04317f8f98067ca62c3f0
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import EmailMessage
from django.contrib import messages
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
<<<<<<< HEAD
=======
from django.conf import settings
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.contrib import messages
from django.core.exceptions import ValidationError
import os
>>>>>>> db314d50cd58dd5270c04317f8f98067ca62c3f0
import uuid
from .models import Usuario, Cliente, Repartidor, Sugerencia, Administrador
from .forms import RegistroClienteForm, RepartidorForm
from .barrios import BARRIOS_BOGOTA
from inventario.models import Producto


# ── Páginas generales ─────────────────────────────────────────────────────────

def index(request):
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.get(id=usuario_id) if usuario_id else None
    return render(request, 'index.html', {'usuario': usuario})

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


<<<<<<< HEAD
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

=======
def reportesVentas(request):
    ventas = Venta.objects.all().select_related('cliente__usuario').order_by('-fecha_venta')
    
    return render(request, "productos/reportes_ventas.html", {
        'ventas': ventas
    })

def panel_sugerencias(request):
    sugerencias = Sugerencia.objects.all().order_by('-fecha')
    
    return render(request, "panel_sugerencias.html", {
        'sugerencias': sugerencias
    })
    
>>>>>>> db314d50cd58dd5270c04317f8f98067ca62c3f0
def logout_view(request):
    request.session.flush()
    return redirect('login')


<<<<<<< HEAD
# ── Registro ──────────────────────────────────────────────────────────────────
=======
def catalogo(request):
    productos = Producto.objects.all()
    return render(request, 'catalogo.html', {
        'productos': productos
    })

def admin(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    
    if not usuario_id or rol != 'ADMIN':
        return redirect('sinacceso')
    
    usuarios = Usuario.objects.all()
    productos = Producto.objects.all()
    
    ultimos_pedidos = Pedido.objects.all().select_related('venta__cliente__usuario').order_by('-fecha_pedido')[:10]
    
    return render(request, 'admin.html', {
        'usuarios': usuarios,
        'productos': productos,
        'ultimos_pedidos': ultimos_pedidos
    })

def usuario(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    productos = Producto.objects.all()

    if not usuario_id or rol != "CLIENTE":
        return redirect("sinacceso")

    usuario = Usuario.objects.get(id=usuario_id)

    return render(request, "usuario.html", {
        "usuario": usuario,
        "productos": productos   
    })

def eliminar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    usuario.delete()
    return redirect('panel_admin')

def producto_eliminar(request, id):
    producto = get_object_or_404(Producto, id=id)
    producto.delete()
    return redirect('panel_admin')

def productos(request):
    productos = Producto.objects.all()
    return render(request, 'productos/productos.html', {
        'productos': productos
    })


def detalle_producto(request, id):
    producto = get_object_or_404(Producto, id=id)

    tallas = TallaProducto.objects.filter(producto=producto)

    # 🔥 calcular total
    stock_total = sum(t.stock for t in tallas)

    return render(request, 'productos/producto-detalle.html', {
        'producto': producto,
        'tallas': tallas,
        'stock_total': stock_total
    })

def producto_detalle(request, id):
    producto = get_object_or_404(Producto, id=id)

    carrito = request.session.get('carrito', {})
    carrito_cantidad = sum(item['cantidad'] for item in carrito.values()) if carrito else 0

    from .forms import SeleccionTallaForm

    if request.method == 'POST':
        form = SeleccionTallaForm(request.POST)

        if form.is_valid():
            talla = form.cleaned_data['talla']

            if str(producto.id) in carrito:
                carrito[str(producto.id)]['cantidad'] += 1
            else:
                carrito[str(producto.id)] = {
                    'nombre': producto.nombre,
                    'precio': float(producto.precio),
                    'imagen': producto.imagen.url,
                    'talla': talla,
                    'cantidad': 1
                }

            request.session['carrito'] = carrito
            return redirect('carrito')

    else:
        form = SeleccionTallaForm()

    return render(request, 'productos/producto-detalle.html', {
        'producto': producto,
        'form': form,
        'carrito_cantidad': carrito_cantidad
    })

def sugerencias(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        texto = request.POST.get("texto")

        if texto: 
            Sugerencia.objects.create(nombre=nombre, texto=texto)
            messages.success(request, "¡Gracias por tu sugerencia!")
            return redirect("sugerencias")  
        else:
            messages.error(request, "Debes escribir una sugerencia.")

    return render(request, "sugerencias.html")

def producto_nuevo(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        precio = request.POST.get("precio")
        descripcion = request.POST.get("descripcion")
        categoria = request.POST.get("categoria")
        imagen = request.FILES.get("imagen")

        stock_s = int(request.POST.get("stock_s", 0))
        stock_m = int(request.POST.get("stock_m", 0))
        stock_l = int(request.POST.get("stock_l", 0))
        stock_xl = int(request.POST.get("stock_xl", 0))

        producto = Producto.objects.create(
            nombre=nombre,
            precio=precio,
            descripcion=descripcion,
            categoria=categoria,
            imagen=imagen,
        )

        if stock_s > 0:
            TallaProducto.objects.create(producto=producto, talla='S', stock=stock_s)

        if stock_m > 0:
            TallaProducto.objects.create(producto=producto, talla='M', stock=stock_m)

        if stock_l > 0:
            TallaProducto.objects.create(producto=producto, talla='L', stock=stock_l)
        
        if stock_xl > 0:
            TallaProducto.objects.create(producto=producto, talla='XL', stock=stock_xl)

        messages.success(request, "Producto creado correctamente")
        return redirect('productos')

    return render(request, 'productos/producto_nuevo.html')

def agregar_producto(request):
    
    if request.method == 'POST':
        
        nombre = request.POST['nombre']
        cantidad = int(request.POST['cantidad'])
        precio = float(request.POST['precio'])
    
        Producto.objects.create(nombre=nombre, stock=cantidad, precio=precio)
        
        return redirect('panel_admin')


def registrar_movimiento(request):
    productos = Producto.objects.all()

    if request.method == "POST":
        producto_id = request.POST.get("producto")
        talla = request.POST.get("talla")
        cantidad = int(request.POST.get("cantidad"))
        tipo_movimiento = request.POST.get("tipo_movimiento")
        proveedor = request.POST.get("proveedor", "")

        producto = Producto.objects.get(id=producto_id)
        
        try:
            Movimiento.objects.create(
                producto=producto,
                talla=talla,
                cantidad=cantidad,
                tipo_movimiento=tipo_movimiento,
                proveedor=proveedor
            )
            messages.success(request, "Movimiento registrado correctamente")
        except ValidationError as e:
            messages.error(request, f" Error: {e.message}")
            
        return redirect('movimientos')

    return render(request, 'movimientos.html', {
        'productos': productos
    })
    
def producto_editar(request, id):
    producto = get_object_or_404(Producto, id=id)

    if request.method == "POST":
        producto.nombre = request.POST.get("nombre")
        producto.precio = request.POST.get("precio")
        producto.descripcion = request.POST.get("descripcion")
        producto.categoria = request.POST.get("categoria")

        if request.FILES.get("imagen"):
            producto.imagen = request.FILES.get("imagen")

        producto.save()

        return redirect('productos')

    return render(request, 'productos/producto_editar.html', {
        'producto': producto
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

def perfil_usuario(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')

    if not usuario_id or rol != "CLIENTE":
        return redirect("sinacceso")

    usuario = Usuario.objects.get(id=usuario_id)

    return render(request, 'usuarios/perfil.html', {"user": usuario})

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

    ventas_pendientes = Pedido.objects.filter(estado='Disponible', repartidor=None).select_related('venta__cliente__usuario')
    
    pedidos_activos = Pedido.objects.filter(
        repartidor=repartidor_obj, estado='En camino'
    ).select_related('venta__cliente__usuario')
    
    mis_pedidos = Pedido.objects.filter(
        repartidor=repartidor_obj, estado='Entregado'
    ).select_related('venta__cliente__usuario')


    return render(request, 'repartidor.html', {
        'Nombre': usuario.first_name,
        'ventas_pendientes': ventas_pendientes,
        'mis_pedidos': mis_pedidos,
        'repartidor': repartidor_obj,
        'pedidos_activos': pedidos_activos,

    })

def carrito(request):
    carrito = request.session.get('carrito', {})

    if request.method == 'POST':

        # ELIMINAR
        if 'eliminar' in request.POST:
            key = request.POST.get('eliminar')
            carrito.pop(key, None)

        # VACIAR
        elif 'vaciar' in request.POST:
            carrito.clear()

        # AUMENTAR / DISMINUIR
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

    # calcular total
    total = sum(item['precio'] * item['cantidad'] for item in carrito.values())

    return render(request, 'productos/carrito.html', {
        'productos': carrito,
        'total': total
    })
>>>>>>> db314d50cd58dd5270c04317f8f98067ca62c3f0

def registro_cliente(request):
    if request.method == "POST":
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            Cliente.objects.create(
                usuario=usuario,
                direccion=form.cleaned_data['direccion']
            )
            messages.success(request, "¡Registro exitoso! Ya puedes iniciar sesión.")
            return redirect("login")
        else:
            print(form.errors)
    else:
        form = RegistroClienteForm()
    return render(request, "registro.html", {"form": form})

def crear_repartidor(request):
    if request.method == "POST":
        form = RepartidorForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            usuario.rol = "REPARTIDOR"
            usuario.password = make_password(form.cleaned_data['password'])
            usuario.tipo_documento = request.POST.get('tipo_documento')
            usuario.save()
            Repartidor.objects.create(
                usuario=usuario,
                placa=form.cleaned_data['placa'],
                vehiculo=form.cleaned_data['vehiculo']
            )
            messages.success(request, "¡Registro exitoso! Ya puedes iniciar sesión.")
            return redirect("login")
    else:
        form = RepartidorForm()
    return render(request, "crear-repartidor.html", {"form": form})

def crear_admin(request):
    if request.method == "POST":
        usuario_val = request.POST.get("usuario")
        correo      = request.POST.get("correo")
        telefono    = request.POST.get("telefono")
        codigo      = request.POST.get("codigo")
        contrasena  = request.POST.get("contrasena")
        confirmar   = request.POST.get("confirmar")
        first_name  = request.POST.get("first_name")
        fecha_nacimiento = request.POST.get("fecha_nacimiento")
        barrio      = request.POST.get("barrio")
        localidad   = request.POST.get("localidad")
        tipo_documento = request.POST.get("tipo_documento")
        cedula      = request.POST.get("cedula")

        # Validaciones
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
            fecha_nacimiento=fecha_nacimiento if fecha_nacimiento else None,
            barrio=barrio,
            localidad=localidad,
            tipo_documento=tipo_documento,
            cedula=cedula,
            is_staff=True,
            is_superuser=True
        )
        Administrador.objects.create(
            codigo=codigo,
            usuario=usuario
        )

        return redirect("login")
    return render(request, "crear_admin.html")


# ── Dashboards por rol ────────────────────────────────────────────────────────

def usuario(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    if not usuario_id or rol != "CLIENTE":
        return redirect("sinacceso")
    usuario = Usuario.objects.get(id=usuario_id)
    categoria = request.GET.get("categoria")

    if categoria == "HOMBRE":
        productos = Producto.objects.filter(categoria__in=["HOMBRE", "MIXTO"])
    elif categoria == "MUJER":
        productos = Producto.objects.filter(categoria__in=["MUJER", "MIXTO"])
    elif categoria == "MIXTO":
        productos = Producto.objects.filter(categoria="MIXTO")
    else:
        productos = Producto.objects.all()

    return render(request, "usuario.html", {
        "usuario": usuario,
        "productos": productos
    })


<<<<<<< HEAD
def admin(request):
=======
def formulario_compra(request):

    carrito = request.session.get('carrito', {})
    cantidad = sum(item['cantidad'] for item in carrito.values())
    total = sum(item['precio'] * item['cantidad'] for item in carrito.values())

>>>>>>> db314d50cd58dd5270c04317f8f98067ca62c3f0
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    if not usuario_id or rol != 'ADMIN':
        return redirect('sinacceso')
    usuarios = Usuario.objects.all()
    from inventario.models import Producto
    productos = Producto.objects.all()
    return render(request, 'productos/admin.html', {'usuarios': usuarios, 'productos': productos})

<<<<<<< HEAD
def repartidor(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    if not usuario_id or rol != 'REPARTIDOR':
        return redirect('sinacceso')
    usuario = Usuario.objects.get(id=usuario_id)
    return render(request, 'repartidor.html', {
        'nombre': usuario.first_name,
        'ventas_pendientes': []
    })
=======
    if usuario_id:
        try:
            cliente = Cliente.objects.get(usuario__id=usuario_id)
        except Cliente.DoesNotExist:
            return redirect('carrito')
>>>>>>> db314d50cd58dd5270c04317f8f98067ca62c3f0

def tomar_pedido(request, id):
    if request.method == "POST":
        from inventario.models import Venta
        venta = Venta.objects.get(id=id)
        venta.estado = "En camino"
        venta.save()
        messages.success(request, "Pedido tomado correctamente")
    return redirect('repartidor')


# ── Perfil y configuración de cuenta ─────────────────────────────────────────

def perfil_usuario(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    if not usuario_id or rol != "CLIENTE":
        return redirect("sinacceso")
    usuario = Usuario.objects.get(id=usuario_id)
    return render(request, 'usuarios/perfil.html', {"user": usuario})

def actualizar_usuario(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    if not usuario_id or rol != "CLIENTE":
        return redirect("sinacceso")
    usuario = Usuario.objects.get(id=usuario_id)
    if request.method == 'POST':
        form = RegistroClienteForm(request.POST, instance=usuario)
        if form.is_valid():
<<<<<<< HEAD
            form.save()
            return redirect('perfil')
=======
            
            venta = Venta.objects.create(
                cliente=cliente,
                cantProducto=cantidad,
                metodoEnvio=form.cleaned_data['metodo_envio'],
                totalVenta=total,
                metodo_de_pago=form.cleaned_data['metodo_pago'],
                direccionEnvio=form.cleaned_data['direccion_envio'],
                telefonoContacto=form.cleaned_data['telefono_contacto'],
                observaciones=form.cleaned_data.get('observaciones', ''),
                estado='Pendiente'
            )
            
            Pedido.objects.create(venta=venta)

            for key, item in carrito.items():

                producto_id = key.split('_')[0]
                talla = item['talla']

                producto = Producto.objects.get(id=int(producto_id))
                talla_obj = producto.tallas.get(talla=talla)

                if talla_obj.stock >= item['cantidad']:
                    talla_obj.stock -= item['cantidad']
                    talla_obj.save()
                else:
                    venta.delete()
                    return HttpResponse("Stock insuficiente")
                
            request.session['venta_id'] = venta.id
            request.session['carrito'] = {}

            return redirect('factura')

>>>>>>> db314d50cd58dd5270c04317f8f98067ca62c3f0
    else:
        form = RegistroClienteForm(instance=usuario)
    return render(request, 'usuarios/actualizar_usuario.html', {'form': form})

<<<<<<< HEAD
def eliminar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    usuario.delete()
    return redirect('panel_admin')
=======
    return render(request, 'productos/formulario_compra.html', {
        'form': form,
        'cliente': cliente,
        'productos': carrito,
        'total': total
    })
    
## pediddos en general

def pedidos_disponibles(request):
    usuario_id = request.session.get('usuario_id')

    try:
        repartidor = Repartidor.objects.get(usuario__id=usuario_id)
    except Repartidor.DoesNotExist:
        return redirect('login')

    # Pedidos sin repartidor asignado
    pedidos = Pedido.objects.filter(estado='Disponible', repartidor=None).select_related('venta__cliente')

    return render(request, 'pedidos/pedidos_disponibles.html', {
        'pedidos': pedidos,
        'repartidor': repartidor
    })


def tomar_pedido(request, pedido_id):
    usuario_id = request.session.get('usuario_id')

    try:
        repartidor = Repartidor.objects.get(usuario__id=usuario_id)
    except Repartidor.DoesNotExist:
        return redirect('login')

    pedido = get_object_or_404(Pedido, id=pedido_id, estado='Disponible', repartidor=None)
    pedido.repartidor = repartidor
    pedido.estado = 'En camino'
    pedido.save()

    return redirect('mis_pedidos')


def mis_pedidos(request):
    usuario_id = request.session.get('usuario_id')

    try:
        repartidor = Repartidor.objects.get(usuario__id=usuario_id)
    except Repartidor.DoesNotExist:
        return redirect('repartidor')

    ventas_pendientes = Pedido.objects.filter(
        estado='Disponible', repartidor=None
    ).select_related('venta__cliente__usuario')
    
    pedidos_activos = Pedido.objects.filter(
        repartidor=repartidor, estado='En camino'
    ).select_related('venta__cliente__usuario')
    
    mis_pedidos_qs = Pedido.objects.filter(
        repartidor=repartidor, estado='Entregado'
    ).select_related('venta__cliente__usuario').order_by('-fecha_pedido')

    return render(request, 'repartidor.html', {
        'Nombre': repartidor.usuario.first_name,
        'ventas_pendientes': ventas_pendientes,
        'pedidos_activos': pedidos_activos,
        'mis_pedidos': mis_pedidos_qs,
        'repartidor': repartidor,
    })

def entregar_pedido(request, pedido_id):
    usuario_id = request.session.get('usuario_id')

    try:
        repartidor = Repartidor.objects.get(usuario__id=usuario_id)
    except Repartidor.DoesNotExist:
        return redirect('login')

    pedido = get_object_or_404(Pedido, id=pedido_id, repartidor=repartidor)
    pedido.estado = 'Entregado'
    pedido.save()

    # Actualizar también el estado de la venta
    pedido.venta.estado = 'Entregado'
    pedido.venta.save()

    return redirect('repartidor')
>>>>>>> db314d50cd58dd5270c04317f8f98067ca62c3f0


# ── Sugerencias ───────────────────────────────────────────────────────────────

def sugerencias(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        texto = request.POST.get("texto")
        if texto:
            Sugerencia.objects.create(nombre=nombre, texto=texto)
            messages.success(request, "¡Gracias por tu sugerencia!")
            return redirect("sugerencias")
        else:
            messages.error(request, "Debes escribir una sugerencia.")
    return render(request, "sugerencias.html")

def panel_sugerencias(request):
    sugerencias = Sugerencia.objects.all().order_by('-fecha')
    return render(request, "sugerencias.html", {"sugerencias": sugerencias})


# ── Recuperación de contraseña ────────────────────────────────────────────────

<<<<<<< HEAD
def restablecer_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            messages.error(request, "Debes ingresar un correo.")
            return redirect('restablecer')
=======
        ventas = Venta.objects.filter(
            fecha_venta__date__range=[fecha_inicio, fecha_fin]
            ).select_related('cliente__usuario')
>>>>>>> db314d50cd58dd5270c04317f8f98067ca62c3f0

        usuario = Usuario.objects.filter(email__iexact=email.strip().lower()).first()
        if usuario:
            token = str(uuid.uuid4())
            usuario.token_recuperacion = token
            usuario.save()
            enlace = f"http://127.0.0.1:8000/nueva_contrasena/{token}/"
            cuerpo = f"""
<html><body style="font-family:Arial,sans-serif;">
<h2>Recuperar Contraseña - Deportes360</h2>
<p>Hola <strong>{usuario.first_name or 'Usuario'}</strong>,</p>
<p>Haz clic en el siguiente enlace para restablecer tu contraseña:</p>
<a href="{enlace}" style="background:#3b82f6;color:#fff;padding:12px 24px;
   text-decoration:none;border-radius:6px;">Restablecer contraseña</a>
<p style="margin-top:20px;color:#999;font-size:12px;">
   Si no solicitaste este cambio, ignora este correo.</p>
</body></html>"""
            correo = EmailMessage(
                subject="Recuperación de contraseña",
                body=cuerpo,
                from_email="juancerquera104@gmail.com",
                to=[usuario.email],
            )
            correo.content_subtype = "html"
            correo.send(fail_silently=False)

<<<<<<< HEAD
        messages.success(request, "El correo se envió exitosamente.")
        return redirect('restablecer')
    return render(request, 'restablecer.html')
=======
        p = canvas.Canvas(response)
        p.drawString(100, 800, f"Reporte de Ventas desde {fecha_inicio} hasta {fecha_fin}")

        y = 750
        for venta in ventas:
            texto = f"ID: {venta.id} | Cliente: {venta.cliente.usuario.username} | Total: ${venta.totalVenta} | Fecha: {venta.fecha_venta.strftime('%d/%m/%Y')}"
            p.drawString(50, y, texto)
            y -= 20
            if y < 50:  
                p.showPage()
                y = 800

        p.showPage()
        p.save()
        return response
        
    return redirect('reportesVentas')
    
def prueba_correo(request):
    correo = EmailMessage(
        subject="Prueba de correo",
        body="Este es un correo de prueba desde Django.",
        from_email="Soporte Deportes360 <tucorreo@gmail.com>",
        to=["juancerquera104@gmail.com"], 
    )
    correo.send(fail_silently=False)  
    return HttpResponse("Correo enviado correctamente")

def nueva_contrasena(request, token):
    print("🔐 TOKEN RECIBIDO:", token)

    usuario = Usuario.objects.filter(token_recuperacion=token).first()
>>>>>>> db314d50cd58dd5270c04317f8f98067ca62c3f0

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
def barrios_bogota(request):
    localidad = request.GET.get('localidad')
    data = BARRIOS_BOGOTA
    if localidad:
        data = [b for b in data if b['localidad'].lower() == localidad.lower()]
    return Response(data)


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