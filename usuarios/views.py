from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from .models import Usuario, Cliente, Repartidor, Producto
from .forms import AdminForm, RepartidorForm, SeleccionTallaForm, RegistroClienteForm, CompraForm, ReportesForm
from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpResponse
from reportlab.pdfgen import canvas 
from django.core.mail import EmailMessage
import uuid

def index(request):
    usuario_id = request.session.get('usuario_id')
    usuario = None
    if usuario_id:
        usuario = Usuario.objects.get(id=usuario_id)
    return render(request, 'index.html', {
        'usuario': usuario
    })

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

def catalogo(request):
    return render(request, 'catalogo.html')

def detalle_pedido(request):
    return render(request, 'detalle_pedido.html')

def sugerencias(request):
    return render(request, 'sugerencias.html')

def contactousu(request):
    return render(request, 'contactousu.html')

def paginaNo(request):
    return render(request, 'paginaNo.html')

def crear_admin(request):
    return render(request, 'crear_admin.html')

def reportesVentas(request):
    return render(request, "productos/reportes_ventas.html")

def logout_view(request):
    request.session.flush()
    return redirect('login')

def inventario(request):
    
    productos = Producto.objects.all()
    
    return render(request, 'inventario.html', {'productos': productos})

def agregar_stock(request, id):
    
    producto = get_object_or_404(Producto, id=id)
    
    if request.method == 'POST':
        cantidad = int(request.POST['cantidad'])
        
        producto.stock += cantidad
        producto.save()
        
        return redirect('inventario')
    
    return render(request, 'agregar_stock.html', {'producto': producto})

def agregar_producto(request):
    
    if request.method == 'POST':
        
        nombre = request.POST['nombre']
        cantidad = int(request.POST['cantidad'])
        precio = float(request.POST['precio'])
    
        Producto.objects.create(nombre=nombre, stock=cantidad, precio=precio)
        
        return redirect('inventario')
    
def producto_editar(request, id):
    
    producto = get_object_or_404(Producto, id=id)
    
    if request.method == 'POST':
        producto.nombre = request.POST.get('nombre')
        producto.stock = int(request.POST.get('stock'))
        producto.precio = float(request.POST.get('precio'))
        
        producto.save()
        
        return redirect('inventario')
    
    return render(request, 'productos/producto_editar.html', {'producto': producto})

def productos(request):

    lista_productos = PRODUCTOS.values()

    return render(request, "productos/productos.html", {
        "productos": lista_productos
    })

def producto_nuevo(request):
    return render(request, "productos/producto_nuevo.html")

def producto_eliminar(request, id):
    producto = get_object_or_404(Producto, id=id)
    producto.delete()
    return redirect('inventario')

def eliminar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    usuario.delete()
    return redirect('panel_admin')

def admin(request):
    usuarios = Usuario.objects.all()
    return render(request, 'admin.html', {
        'usuarios': usuarios
    })

def usuario(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')

    if not usuario_id or rol != "CLIENTE":
        return redirect("sinacceso")

    usuario = Usuario.objects.get(id=usuario_id)

    return render(request, "usuario.html", {"usuario": usuario})

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

    # Simulación de pedidos pendientes
    ventas_pendientes = []

    usuario = Usuario.objects.get(id=usuario_id)

    return render(request, 'repartidor.html', {
        'nombre': usuario.first_name,
        'ventas_pendientes': ventas_pendientes
    })


def carrito(request):

    carrito = request.session.get('carrito', {})

    if request.method == 'POST':

        if 'eliminar' in request.POST:
            slug = request.POST.get('eliminar')
            carrito.pop(slug, None)

        if 'vaciar' in request.POST:
            carrito = {}

        request.session['carrito'] = carrito
        return redirect('carrito')

    cantidad = sum(item['cantidad'] for item in carrito.values())
    total = sum(item['precio'] * item['cantidad'] for item in carrito.values())

    return render(request, 'productos/carrito.html', {
        'productos': carrito,
        'total': total,
        'cantidad': cantidad
    })

def registro_cliente(request):
    if request.method == "POST":
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.rol = "CLIENTE"
            usuario.password = make_password(form.cleaned_data['password'])

            # 👇 AGREGA ESTO
            usuario.is_staff = False
            usuario.is_superuser = False
            usuario.is_active = True

            usuario.save()

            Cliente.objects.create(
                usuario=usuario,
                direccion=form.cleaned_data['direccion']
            )

            messages.success(request, "¡Registro exitoso! Ya puedes iniciar sesión.")
            return redirect("login")
        else:
            # Para ver qué falla
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
            # Encriptar la contraseña
            usuario.password = make_password(form.cleaned_data['password'])
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

    total = sum(item['precio'] * item['cantidad'] for item in carrito.values())

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
        cliente = Usuario.objects.get(id=usuario_id)
    else:
        cliente = None

    if request.method == 'POST':
        form = CompraForm(request.POST)

        if form.is_valid():
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

PRODUCTOS = {
    'camiseta': {
        'nombre': 'Camiseta DryFit Deportiva',
        'precio': 59900,
        'imagen': 'images/camiseta.png',
        'descripcion': 'Material de alta calidad que se adapta a tu cuerpo.',
        'caracteristicas': [
            '✨ Soporte medio-alto',
            '💨 Material transpirable',
            '📏 Tallas: S, M, L, XL',
            '🎨 Color: Negro',
        ],
        'benefits': ['Envíos', 'Pago contra entrega', 'Garantía oficial'],
        'galeria': ['images/camiseta.png', 'images/camiseta2.png', 'images/camiseta3.png']
    },
    'buzo': {
        'nombre': 'Buzo Hombre Deportivo',
        'precio': 75000,
        'imagen': 'images/buzo-hombre.png',
        'descripcion': 'Comodidad máxima para tus ejercicios.',
        'caracteristicas': [
            '✨ Soporte medio-alto',
            '💨 Material transpirable',
            '📏 Tallas: S, M, L, XL',
            '🎨 Color: Negro',
        ],
        'benefits': ['Envíos', 'Pago contra entrega', 'Garantía oficial'],
        'galeria': ['images/buzo-hombre.png']
    },
    'sudadera': {
        'nombre': 'Sudadera Clásica Unisex',
        'precio': 99000,
        'imagen': 'images/sudadera.png',
        'descripcion': 'Sudadera cómoda para uso diario y deporte.',
        'caracteristicas': [
            '💨 Material transpirable',
            '📏 Tallas: S, M, L, XL',
            '🎨 Color: Gris y Negro',
        ],
        'benefits': ['Envíos', 'Pago contra entrega', 'Garantía oficial'],
        'galeria': ['images/sudadera.png']
    },
    'leggings': {
        'nombre': 'Leggings Deportivos Mujer',
        'precio': 85000,
        'imagen': 'images/leggings.png',
        'descripcion': 'Leggings flexibles y cómodos para entrenar.',
        'caracteristicas': [
            '💨 Material transpirable',
            '📏 Tallas: S, M, L',
            '🎨 Color: Negro, Azul',
        ],
        'benefits': ['Envíos', 'Pago contra entrega', 'Garantía oficial'],
        'galeria': ['images/leggings.png']
    },
    'chaqueta': {
        'nombre': 'Chaqueta Rompevientos',
        'precio': 135000,
        'imagen': 'images/chaqueta.png',
        'descripcion': 'Protección contra viento y lluvia ligera.',
        'caracteristicas': [
            '💨 Material resistente al viento',
            '📏 Tallas: S, M, L, XL',
            '🎨 Color: Azul, Negro',
        ],
        'benefits': ['Envíos', 'Pago contra entrega', 'Garantía oficial'],
        'galeria': ['images/chaqueta.png']
    },
    'short': {
        'nombre': 'Short Deportivo Hombre',
        'precio': 49000,
        'imagen': 'images/short.png',
        'descripcion': 'Short ligero para entrenamientos.',
        'caracteristicas': [
            '💨 Material transpirable',
            '📏 Tallas: S, M, L, XL',
            '🎨 Color: Negro, Gris',
        ],
        'benefits': ['Envíos', 'Pago contra entrega', 'Garantía oficial'],
        'galeria': ['images/short.png']
    },
    'top': {
        'nombre': 'Top Deportivo Mujer',
        'precio': 60000,
        'imagen': 'images/top.png',
        'descripcion': 'Top cómodo y transpirable para deporte.',
        'caracteristicas': [
            '💨 Material transpirable',
            '📏 Tallas: S, M, L',
            '🎨 Color: Azul, Rosa',
        ],
        'benefits': ['Envíos', 'Pago contra entrega', 'Garantía oficial'],
        'galeria': ['images/top.png']
    },
    'conjunto-mujer': {
        'nombre': 'Conjunto Deportivo Mujer',
        'precio': 149000,
        'imagen': 'images/conjunto-mujer.png',
        'descripcion': 'Conjunto completo para entrenamientos.',
        'caracteristicas': [
            '💨 Material transpirable',
            '📏 Tallas: S, M, L',
            '🎨 Color: Negro y Rosa',
        ],
        'benefits': ['Envíos', 'Pago contra entrega', 'Garantía oficial'],
        'galeria': ['images/conjunto-mujer.png']
    },
}


def producto_detalle(request, slug):

    carrito = request.session.get('carrito', {})

    # asegurar que sea diccionario
    if isinstance(carrito, list):
        carrito = {}

    producto = PRODUCTOS.get(slug)
    if not producto:
        return redirect('catalogo')

    from .forms import SeleccionTallaForm

    if request.method == 'POST':
        form = SeleccionTallaForm(request.POST)

        if form.is_valid():
            talla = form.cleaned_data['talla']

            if slug in carrito:
                carrito[slug]['cantidad'] += 1
            else:
                carrito[slug] = {
                 'nombre': producto['nombre'],
                 'precio': producto['precio'],
                 'imagen': producto['imagen'],   
                 'talla': talla,
                 'cantidad': 1
}

            request.session['carrito'] = carrito
            return redirect('carrito')

    else:
        form = SeleccionTallaForm()

    context = {
        'form': form,
        'producto': producto,
        'carrito_cantidad': sum(item['cantidad'] for item in carrito.values())
    }

    return render(request, 'productos/producto-detalle.html', context)

def agregar_al_carrito(request, producto_id):
    carrito = request.session.get('carrito', [])

    producto = PRODUCTOS.get(producto_id)
    if producto:
        carrito.append(producto)  
        request.session['carrito'] = carrito

    return redirect('carrito')

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

        if contrasena != confirmar:
            return render(request, "crear_admin.html", {"error": "Las contraseñas no coinciden"})

        CODIGOS_VALIDOS = [ "ADM-123", "ADM-456"]
        if codigo not in CODIGOS_VALIDOS:
            return render(request, "crear_admin.html", {"error": "Código incorrecto"})

        if Usuario.objects.filter(username=usuario).exists():
            return render(request, "crear_admin.html", {"error": "El usuario ya existe"})

        Usuario.objects.create(
            username=usuario,
            email=correo,
            telefono=telefono,
            password=make_password(contrasena),
            rol="ADMIN",
            first_name=first_name,
            fecha_nacimiento=fecha_nacimiento if fecha_nacimiento else None,
            barrio=barrio,
            is_staff=True,
            is_superuser=True
        )

        return redirect("login")

    return render(request, "crear_admin.html")

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
        from_email="juancerquera104@gmail.com",
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
            # 🔐 ENCRIPTAR CONTRASEÑA
            usuario.password = make_password(password1)

            usuario.token_recuperacion = None

            usuario.save()

            print("✅ CONTRASEÑA ACTUALIZADA")

            messages.success(request, 'Contraseña actualizada correctamente.')
            return redirect('login')

    return render(request, 'usuarios/nueva_contrasena.html')

def restablecer_password(request):

    if request.method == 'POST':

        email = request.POST.get('email')
        print("📧 EMAIL:", email)

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

            print("✅ CORREO ENVIADO")

        else:
            print("❌ NO EXISTE USUARIO")

        messages.success(request, "Si el correo existe, se enviará un enlace.")
        return redirect('restablecer')

    return render(request, 'restablecer.html')