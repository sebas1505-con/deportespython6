from django.shortcuts import render, redirect, get_list_or_404,get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Usuario, Cliente, Repartidor, Producto
from .forms import AdminForm, RepartidorForm, SeleccionTallaForm, RegistroClienteForm, CompraForm
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpResponse
from reportlab.pdfgen import canvas 
from django.core.mail import EmailMessage

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

def restablecer_password(request):
    if request.method == 'POST':
        correo = request.POST.get('correo')

        try:
            usuario = Usuario.objects.get(email=correo)

            cuerpo = f"Hola {usuario.first_name}, haz clic en el siguiente enlace para restablecer tu contraseña: http://localhost:8000/reset/{usuario.id}/"

            email = EmailMessage(
                subject="Recuperación de contraseña",
                body=cuerpo,
                from_email="tu_correo@gmail.com",
                to=[correo],
            )
            email.encoding = 'utf-8'
            email.send(fail_silently=False)

            messages.success(request, "Se envió un correo de recuperación.")
        except Usuario.DoesNotExist:
            messages.error(request, "El correo no está registrado.")

        return redirect('restablecer')

    return render(request, 'restablecer.html')

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
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte.pdf"'

    p = canvas.Canvas(response)
    p.drawString(100, 750, "Reporte generado desde Django")
    p.showPage()
    p.save()

    return response

def prueba_correo(request):
    correo = EmailMessage(
        subject="Recuperación de contraseña",  
        body="Haz clic en el enlace para restablecer tu contraseña.",
        from_email="tu_correo@gmail.com",
        to=["destinatario@ejemplo.com"],
    )
    correo.content_subtype = "plain"  
    correo.encoding = "utf-8"         
    correo.send()
    return HttpResponse("Correo enviado")