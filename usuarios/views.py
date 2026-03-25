from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import EmailMessage
from django.contrib import messages
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
import uuid
from .models import Usuario, Cliente, Repartidor, Sugerencia
from .forms import RegistroClienteForm, RepartidorForm
from .barrios import BARRIOS_BOGOTA


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

        if contrasena != confirmar:
            return render(request, "crear_admin.html", {"error": "Las contraseñas no coinciden"})
        if codigo not in ["ADM-123", "ADM-456"]:
            return render(request, "crear_admin.html", {"error": "Código incorrecto"})
        if Usuario.objects.filter(username=usuario_val).exists():
            return render(request, "crear_admin.html", {"error": "El usuario ya existe"})
        if Usuario.objects.filter(cedula=cedula).exists():
            return render(request, "crear_admin.html", {"error": "La cédula ya está registrada"})

        Usuario.objects.create(
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
        return redirect("login")
    return render(request, "crear_admin.html")


# ── Dashboards por rol ────────────────────────────────────────────────────────

def usuario(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    if not usuario_id or rol != "CLIENTE":
        return redirect("sinacceso")
    usuario = Usuario.objects.get(id=usuario_id)
    # Importa Producto aquí para no crear dependencia circular en el módulo
    from inventario.models import Producto
    productos = Producto.objects.all()
    return render(request, "usuario.html", {"usuario": usuario, "productos": productos})

def admin(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    if not usuario_id or rol != 'ADMIN':
        return redirect('sinacceso')
    usuarios = Usuario.objects.all()
    from inventario.models import Producto
    productos = Producto.objects.all()
    return render(request, 'productos/admin.html', {'usuarios': usuarios, 'productos': productos})

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
            form.save()
            return redirect('perfil')
    else:
        form = RegistroClienteForm(instance=usuario)
    return render(request, 'usuarios/actualizar_usuario.html', {'form': form})

def eliminar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    usuario.delete()
    return redirect('panel_admin')


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