from django.shortcuts import render, redirect,get_object_or_404, redirect
from .models import Usuario, Cliente, Repartidor, Producto, TallaProducto, Venta, Sugerencia, Movimiento, Pedido
from .forms import AdminForm, RepartidorForm, SeleccionTallaForm, RegistroClienteForm, CompraForm, ReportesForm, MovimientoForm
from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpResponse
from reportlab.pdfgen import canvas 
from django.core.mail import EmailMessage
from .barrios import BARRIOS_BOGOTA 
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.contrib import messages
import os
import uuid

def quienes(request):
    return render(request, 'quienes.html')

def contacto(request):
    return render(request, 'contacto.html')

def menu(request):
    return render(request, 'menu.html')

def sinacceso(request):
    return render(request, "sinacceso.html")

def recuperar_contraseña(request):
    return render(request, 'recuperar_contraseña.html')

def pedidos(request):
    return render(request, 'pedidos.html')

def reportes_admin(request):
    return render(request, 'productos/reportes_admin.html')

def detalle_pedido(request):
    return render(request, 'detalle_pedido.html')

def contactousu(request):
    return render(request, 'contactousu.html')

def paginaNo(request):
    return render(request, 'paginaNo.html')

def crear_admin(request):
    return render(request, 'crear_admin.html')

def reportesVentas(request):
    return render(request, "productos/reportes_ventas.html")

def panel_sugerencias(request):
    sugerencias = Sugerencia.objects.all().order_by('-fecha')
    return render(request, "panel_sugerencias.html", {"sugerencias": sugerencias})

def logout_view(request):
    request.session.flush()
    return redirect('login')

def index(request):
    usuario_id = request.session.get('usuario_id')
    usuario = None
    if usuario_id:
        usuario = Usuario.objects.get(id=usuario_id)
    return render(request, 'index.html', {
        'usuario': usuario
    })

def catalogo(request):
    productos = Producto.objects.all()
    return render(request, 'catalogo.html', {
        'productos': productos
    })

def admin(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    usuarios = Usuario.objects.all()
    productos = Producto.objects.all()

    if not usuario_id or rol != 'ADMIN':
        return redirect('sinacceso')
    
    usuario = Usuario.objects.get(id=usuario_id)
    
    return render(request, 'admin.html', {'usuarios': usuarios, 'productos': productos})

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
    return redirect('inventario')

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

def panel_repartidor(request):
    ventas_pendientes = Venta.objects.all()

    print("VENTAS:", ventas_pendientes)

    return render(request, 'usuario/repartidor.html', {
        'ventas_pendientes': ventas_pendientes,
        'Nombre': request.user.username
    })

def tomar_pedido(request, id):
    if request.method == "POST":
        venta = Venta.objects.get(id=id)
        venta.estado = "En camino"
        venta.save()

        messages.success(request, "Pedido tomado correctamente")

    return redirect('repartidor')    

def producto_nuevo(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        precio = request.POST.get("precio")
        descripcion = request.POST.get("descripcion")
        imagen = request.FILES.get("imagen")

        stock_s = int(request.POST.get("stock_s", 0))
        stock_m = int(request.POST.get("stock_m", 0))
        stock_l = int(request.POST.get("stock_l", 0))

        producto = Producto.objects.create(
            nombre=nombre,
            precio=precio,
            descripcion=descripcion,
            imagen=imagen,
        )

        if stock_s > 0:
            TallaProducto.objects.create(producto=producto, talla='S', stock=stock_s)

        if stock_m > 0:
            TallaProducto.objects.create(producto=producto, talla='M', stock=stock_m)

        if stock_l > 0:
            TallaProducto.objects.create(producto=producto, talla='L', stock=stock_l)

        return redirect('productos')

    return render(request, 'productos/producto_nuevo.html')

def agregar_producto(request):
    
    if request.method == 'POST':
        
        nombre = request.POST['nombre']
        cantidad = int(request.POST['cantidad'])
        precio = float(request.POST['precio'])
    
        Producto.objects.create(nombre=nombre, stock=cantidad, precio=precio)
        
        return redirect('inventario')

def inventario(request):
    productos = Producto.objects.all()
    return render(request, 'inventario.html', {'productos': productos})

def registrar_movimiento(request):
    productos = Producto.objects.all()

    if request.method == "POST":
        producto_id = request.POST.get("producto")
        talla = request.POST.get("talla")
        cantidad = int(request.POST.get("cantidad"))

        producto = Producto.objects.get(id=producto_id)

        Movimiento.objects.create(
            producto=producto,
            talla=talla,
            cantidad=cantidad
        )

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
        producto.stock = request.POST.get("stock")

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
    
    mis_pedidos = Pedido.objects.filter(
        repartidor=repartidor_obj, estado='Entregado'
    ).select_related('venta__cliente__usuario')

    return render(request, 'repartidor.html', {
        'Nombre': usuario.first_name,
        'ventas_pendientes': ventas_pendientes,
        'mis_pedidos': mis_pedidos,
        'repartidor': repartidor_obj,
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
        usuario = request.POST.get("usuario")
        correo = request.POST.get("correo")
        telefono = request.POST.get("telefono")
        codigo = request.POST.get("codigo")
        contrasena = request.POST.get("contrasena")
        confirmar = request.POST.get("confirmar")
        first_name = request.POST.get("first_name")
        fecha_nacimiento = request.POST.get("fecha_nacimiento")
        barrio = request.POST.get("barrio")
        localidad = request.POST.get("localidad")
        tipo_documento = request.POST.get("tipo_documento")
        cedula = request.POST.get("cedula")

        # VALIDACIONES
        if contrasena != confirmar:
            return render(request, "crear_admin.html", {"error": "Las contraseñas no coinciden"})

        CODIGOS_VALIDOS = ["ADM-123", "ADM-456"]
        if codigo not in CODIGOS_VALIDOS:
            return render(request, "crear_admin.html", {"error": "Código incorrecto"})

        if Usuario.objects.filter(username=usuario).exists():
            return render(request, "crear_admin.html", {"error": "El usuario ya existe"})

        if Usuario.objects.filter(cedula=cedula).exists():
            return render(request, "crear_admin.html", {"error": "La cédula ya está registrada"})

        Usuario.objects.create(
            username=usuario,
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

        return redirect("login")

    return render(request, "crear_admin.html")

def login_view(request):
    if request.method == 'POST':
        correo = request.POST.get('correo')
        clave = request.POST.get('clave')

        try:
            usuario = Usuario.objects.get(email=correo)

            if check_password(clave, usuario.password):
                # iniciar sesión
                request.session['usuario_id'] = usuario.id
                request.session['rol'] = usuario.rol

                if usuario.rol == 'CLIENTE':
                    return redirect('usuario')
                elif usuario.rol == 'REPARTIDOR':
                    return redirect('repartidor')
                elif usuario.rol == 'ADMIN':
                     return redirect('panel_admin')
                else:
                    return redirect('login')
            else:
                messages.error(request, "Contraseña incorrecta")

        except Usuario.DoesNotExist:
            messages.error(request, "Usuario no registrado")

    return render(request, 'login.html')

def factura(request):

    carrito = request.session.get('carrito', {})

    usuario_id = request.session.get('usuario_id')

    cliente = Usuario.objects.get(id=usuario_id)

    total = sum(float(item['precio']) * item['cantidad'] for item in carrito.values())

    return render(request, 'productos/factura.html', {
        'cliente': cliente,
        'productos': carrito,
        'total': total
    })


def formulario_compra(request):

    carrito = request.session.get('carrito', {})
    cantidad = sum(item['cantidad'] for item in carrito.values())
    total = sum(item['precio'] * item['cantidad'] for item in carrito.values())

    usuario_id = request.session.get('usuario_id')

    if usuario_id:
        try:
            cliente = Cliente.objects.get(usuario__id=usuario_id)
        except Cliente.DoesNotExist:
            return redirect('carrito')

    if request.method == 'POST':
        form = CompraForm(request.POST)

        if form.is_valid():
            
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

    else:
        form = CompraForm(initial={
            'cant_producto': cantidad,
            'total_venta': total,
        })

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

    pedidos = Pedido.objects.filter(repartidor=repartidor).select_related('venta__cliente__usuario').order_by('-fecha_pedido')

    ventas_pendientes = Pedido.objects.filter(
        estado='Disponible', repartidor=None
    ).select_related('venta__cliente__usuario')

    return render(request, 'repartidor.html', {
        'Nombre': repartidor.usuario.first_name,
        'mis_pedidos': pedidos,
        'ventas_pendientes': ventas_pendientes,
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

    return redirect('mis_pedidos')

def cargar_productos():
    datos = [
        {
            "nombre": "Camiseta DryFit Deportiva",
            "precio": 59900,
            "descripcion": "Material de alta calidad que se adapta a tu cuerpo.",
            "imagen": "productos/camiseta.png"
        },
        {
            "nombre": "Buzo Hombre Deportivo",
            "precio": 75000,
            "descripcion": "Comodidad máxima para tus ejercicios.",
            "imagen": "productos/buzo-hombre.png"
        },
    ]

    for d in datos:
        Producto.objects.create(**d)

@api_view(['GET'])
def barrios_bogota(request):
    localidad = request.GET.get('localidad')

    data = BARRIOS_BOGOTA

    if localidad:
        data = [b for b in data if b['localidad'].lower() == localidad.lower()]

    return Response(data)

def agregar_al_carrito(request, id):
    carrito = request.session.get('carrito', {})

    producto = get_object_or_404(Producto, id=id)

    if request.method == 'POST':
        talla = request.POST.get('talla')

        # clave única por producto + talla
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
            texto = f"ID: {venta.id} | Cliente: {venta.cliente} | Total: ${venta.total} | Fecha: {venta.fecha}"
            p.drawString(50, y, texto)
            y -= 20
            if y < 50:  
                p.showPage()
                y = 800

        p.showPage()
        p.save()
        return response
    else:
        messages.error(request, "Fechas inválidas. Por favor corrige e intenta de nuevo.")
        return render(request, 'reportes.html', {'form': form})
    
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

    datos = [
        ["Producto", "Talla", "Cantidad", "Precio"],
        ["Camiseta", "M", "2", "$120.000"],
    ]

    tabla = Table(datos)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.black),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph("Total: $120.000", estilos['Heading2']))
    doc.build(elementos)

    return response

def restablecer_password(request):

    if request.method == 'POST':

        email = request.POST.get('email')
        print(" EMAIL:", email)

        if not email:
            messages.error(request, "Debes ingresar un correo.")
            return redirect('restablecer')

        email = email.strip().lower()

        usuario = Usuario.objects.filter(email__iexact=email).first()

        if usuario:
            print("✅ USUARIO ENCONTRADO:", usuario.email)

            token = str(uuid.uuid4())
            usuario.token_recuperacion = token
            usuario.save()

            enlace = f"http://127.0.0.1:8000/nueva_contrasena/{token}/"

            cuerpo = f"""
<html>
<body style="margin:0; padding:0; background:#0f172a; font-family:Arial, sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a; padding:40px 0;">
<tr>
<td align="center">

<!-- CONTENEDOR -->
<table width="600" style="background:#ffffff; border-radius:15px; overflow:hidden; box-shadow:0 10px 30px rgba(0,0,0,0.2);">

    <!-- IMAGEN HEADER -->
    <tr>
        <td>
            <img src="https://images.unsplash.com/photo-1517836357463-d25dfeac3438"
                 width="100%" style="display:block;">
        </td>
    </tr>

    <!-- CONTENIDO -->
    <tr>
        <td style="padding:40px; text-align:center;">

            <h1 style="color:#0f172a; margin-bottom:10px;">
                 Recuperar Contraseña
            </h1>

            <p style="color:#555; font-size:16px;">
                Hola <strong>{usuario.first_name or "Usuario"}</strong>
            </p>

            <p style="color:#777; font-size:15px; line-height:1.6;">
                Recibimos una solicitud para restablecer tu contraseña.
                Haz clic en el botón de abajo para continuar.
            </p>

            <!-- BOTÓN -->
            <a href="{enlace}"
            style="
                display:inline-block;
                margin-top:25px;
                background:linear-gradient(135deg,#3b82f6,#1d4ed8);
                color:#fff;
                padding:14px 30px;
                text-decoration:none;
                border-radius:8px;
                font-weight:bold;
                font-size:16px;
                box-shadow:0 5px 15px rgba(59,130,246,0.4);
            ">
                Restablecer contraseña 
            </a>

            <p style="margin-top:30px; color:#999; font-size:13px;">
                Si no solicitaste este cambio, puedes ignorar este correo.
            </p>

        </td>
    </tr>

    <!-- FOOTER -->
    <tr>
        <td style="background:#f1f5f9; padding:20px; text-align:center; font-size:12px; color:#888;">
            © 2026 Deportes360 • Todos los derechos reservados
        </td>
    </tr>

</table>

</td>
</tr>
</table>

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

        else:
            print("❌ NO EXISTE USUARIO")

        messages.success(request, "el correo se envio exitosamente.")
        return redirect('restablecer')

    return render(request, 'restablecer.html')