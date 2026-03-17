from django.shortcuts import render, redirect 
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Usuario, Cliente, Repartidor
from .forms import AdminForm, RepartidorForm, SeleccionTallaForm, RegistroClienteForm, CompraForm
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password

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

def productos(request):
    return render(request, 'productos.html')

def pedidos(request):
    return render(request, 'pedidos.html')

def inventario(request):
    return render(request, 'inventario.html')

def crear_admin(request):
    return render(request, 'crear_admin.html')

def catalogo(request):
    return render(request, 'catalogo.html')

def panel_admin(request):
    return render(request, 'admin/panel.html')

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

def logout_view(request):
    request.session.flush()
    return redirect('login')

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

    return render(request, 'usuarios/perfil.html', {"usuario": usuario})

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
            slug = request.POST['eliminar']
            if slug in carrito:
                del carrito[slug]

        if 'vaciar' in request.POST:
            carrito = {}

        request.session['carrito'] = carrito
        return redirect('carrito')

    total = sum(item['precio'] * item['cantidad'] for item in carrito.values())

    return render(request, 'productos/carrito.html', {
        'productos': carrito,
        'total': total,
        'cantidad': sum(item['cantidad'] for item in carrito.values())
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
                messages.success(request, f"¡Bienvenido {usuario.first_name}!")

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
            usuario = Usuario.objects.get(correo=correo)

            # 🔥 Aquí luego puedes enviar email real
            messages.success(request, "Se envió un correo de recuperación (simulado).")

        except Usuario.DoesNotExist:
            messages.error(request, "El correo no está registrado.")

        return redirect('restablecer')

    return render(request, 'restablecer.html')

def formulario_compra(request):

    carrito = request.session.get('carrito', {})

    cantidad = sum(item['cantidad'] for item in carrito.values())
    total = sum(item['precio'] * item['cantidad'] for item in carrito.values())

    if request.method == 'POST':
        form = CompraForm(request.POST)

        if form.is_valid():
            return redirect('carrito')

    else:
        form = CompraForm(initial={
            'cant_producto': cantidad,
            'total_venta': total,
        })

    return render(request, 'productos/formulario_compra.html', {'form': form})

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

def registrar_admin(request):
    if request.method == "POST":
        form = AdminForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.rol = "ADMIN"
            usuario.set_password(form.cleaned_data['password'])
            usuario.is_staff = True
            usuario.is_superuser = True
            usuario.save()
            return redirect("login")
    else:
        form = AdminForm()

    return render(request, "registro_admin.html", {"form": form})