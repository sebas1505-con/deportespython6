from django.shortcuts import render, redirect 
from .forms import RegistroForm
from .forms import RepartidorForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login
from .models import Usuario, Cliente


def index(request):
    return render(request, 'index.html')

def quienes(request):
    return render(request, 'quienes.html')

def contacto(request):
    return render(request, 'contacto.html')

def menu(request):
    return render(request, 'menu.html')

def sinacceso(request):
    return render(request, 'sinacceso.html')

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

def logout_view(request):
    request.session.flush()
    return redirect('login')

def usuario(request):
    if not request.session.get('usuario_id'):
        return redirect('sinacceso')

    usuario = Usuario.objects.get(id=request.session['usuario_id'])
    cliente = Cliente.objects.get(usuario=usuario)

    return render(request, 'usuario.html', {
        'cliente': cliente
    })

def carrito(request):

    carrito = request.session.get('carrito', [])

    if request.method == 'POST':

        if 'eliminar' in request.POST:
            index = int(request.POST['eliminar'])
            if 0 <= index < len(carrito):
                carrito.pop(index)

        if 'vaciar' in request.POST:
            carrito = []

        request.session['carrito'] = carrito
        return redirect('carrito')

    total = sum(float(p['precio']) for p in carrito)

    return render(request, 'carrito.html', {
        'productos': carrito,
        'total': total
    })

def repartidor(request):
    if not request.session.get('cliente_id'):
        return redirect('sinacceso')

    if request.session.get('rol') != 'repartidor':
        return redirect('sinacceso')

    # Simulación de pedidos pendientes
    ventas_pendientes = []

    return render(request, 'repartidor.html', {
        'nombre': request.session.get('nombre'),
        'ventas_pendientes': ventas_pendientes
    })



def registro_cliente(request):
    if request.method == 'POST':
        usuario_txt = request.POST.get('usuario')
        correo_txt = request.POST.get('correo')
        clave_txt = request.POST.get('clave')
        confirmar = request.POST.get('confirmar')
        nombre = request.POST.get('nombre')
        telefono = request.POST.get('telefono')
        direccion = request.POST.get('direccion')
        fechaNacimiento = request.POST.get('fechaNacimiento')
        barrio = request.POST.get('barrio')

        if clave_txt != confirmar:
            messages.error(request, "Las contraseñas no coinciden")
            return redirect('registro')

        usuario = Usuario.objects.create(
            usuario=usuario_txt,
            correo=correo_txt,
            clave=clave_txt,
            rol='usuario'
        )

        Cliente.objects.create(
            usuario=usuario,
            nombre=nombre,
            telefono=telefono,
            direccion=direccion,
            fechaNacimiento=fechaNacimiento,
            barrio=barrio
        )

        messages.success(request, "Registro exitoso")
        return redirect('login')

    return render(request, 'registro.html')

def crear_repartidor(request):
    if request.method == 'POST':
        form = RepartidorForm(request.POST)
        if form.is_valid():
            repartidor = form.save(commit=False)
            repartidor.rol = 'repartidor'
            repartidor.save()
            request.session['cliente_id'] = repartidor.id
            request.session['rol'] = repartidor.rol

            return redirect('repartidor') 
    else:
        form = RepartidorForm()

    return render(request, 'crear-repartidor.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        correo = request.POST.get('correo')
        clave = request.POST.get('clave')

        try:
            usuario = Usuario.objects.get(correo=correo, clave=clave)

            request.session['usuario_id'] = usuario.id
            request.session['rol'] = usuario.rol

            if usuario.rol == 'usuario':
                return redirect('usuario')

        except Usuario.DoesNotExist:
            messages.error(request, "Credenciales incorrectas")

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