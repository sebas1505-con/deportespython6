from email.mime.image import MIMEImage
from inventario.models import Producto, Pedido, Movimiento, Venta, TallaProducto, DetalleVentaProductos, Envio, RespuestaSugerencia, Sugerencia as SugerenciaInventario, Asignacion
from .models import Usuario, Cliente, Repartidor, Administrador, NotificacionRepartidor, MensajeRepartidor
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Sum, Min, Prefetch
from django.db.models.functions import TruncDate, TruncMonth
from .forms import RegistroClienteForm, RepartidorForm
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models.functions import TruncDate
from django.db.models import Sum, Count
from datetime import date, timedelta
from .barrios import BARRIOS_BOGOTA
from django.core.mail import EmailMessage
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, F
from django.utils.text import slugify
import datetime as dt_mod
import pandas as pd
import requests
import sys
import json
import uuid
import io
import re
# ── Páginas generales ─────────────────────────────────────────────────────────

def index(request):
    from inventario.models import Producto, TallaProducto
    from django.db.models import Prefetch
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.get(id=usuario_id) if usuario_id else None
    productos = (
        Producto.objects
        .filter(descontinuado=False)
        .exclude(imagen='').exclude(imagen__isnull=True)
        .prefetch_related(
            Prefetch('tallas', queryset=TallaProducto.objects.filter(stock__gt=0))
        )[:6]
    )
    return render(request, 'index.html', {
        'usuario': usuario,
        'productos': productos,
    })

def quienes(request):
    return render(request, 'quienes.html')

def checkout_auth(request):
    if request.session.get('usuario_id'):
        return redirect('carrito')
    return render(request, 'checkout_auth.html')

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
                # ── Verificar si es repartidor con registro pendiente ──
                if usuario.rol == 'REPARTIDOR' and not usuario.is_active:
                    try:
                        notificacion = NotificacionRepartidor.objects.get(usuario=usuario)
                        if notificacion.estado == 'pendiente':
                            return redirect('registro_pendiente')
                        elif notificacion.estado == 'rechazado':
                            messages.error(request, f'❌ Tu solicitud fue rechazada. Motivo: {notificacion.motivo_rechazo}')
                            return redirect('login')
                    except NotificacionRepartidor.DoesNotExist:
                        messages.error(request, "Usuario inactivo. Contacta con administración.")
                        return redirect('login')
                
                # ── Verificar si usuario está activo ──
                if not usuario.is_active:
                    messages.error(request, "Tu cuenta está desactivada. Contacta con administración.")
                    return redirect('login')
                
                # ── Crear sesión y redirigir ──
                request.session['usuario_id'] = usuario.id
                request.session['rol'] = usuario.rol
                if usuario.rol == 'CLIENTE':
                    next_url = request.POST.get('next', '').strip() or request.GET.get('next', '').strip()
                    if next_url and next_url.startswith('/'):
                        return redirect(next_url)
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


def registro_pendiente(request):
    """Muestra página cuando un repartidor intenta ingresar con registro pendiente"""
    return render(request, 'registro_en_proceso.html')


# ── Registro ──────────────────────────────────────────────────────────────────

def registro_cliente(request):
    if request.method == 'POST':
        datos          = request.POST
        first_name     = datos.get('first_name', '').strip()
        email          = datos.get('email', '').strip()
        username       = datos.get('username', '').strip()
        password       = datos.get('password', '')
        confirmar_password = datos.get('confirmar_password', '')
        telefono       = datos.get('telefono', '').strip()
        tipo_documento = datos.get('tipo_documento', '').strip()
        cedula         = datos.get('cedula', '').strip()

        def volver(msg):
            messages.error(request, msg)
            return render(request, 'registro.html', {'datos': datos})

        if not all([first_name, email, username, password, confirmar_password, telefono, tipo_documento, cedula]):
            return volver('Todos los campos son obligatorios.')
        if len(first_name) < 3 or len(first_name) > 60:
            return volver('El nombre debe tener entre 3 y 60 caracteres.')
        if not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñÜü ]+$', first_name):
            return volver('El nombre completo solo puede contener letras y espacios.')
        if tipo_documento not in ['CC', 'TI', 'CE', 'PAS']:
            return volver('Selecciona un tipo de identificación válido.')
        if not cedula.isdigit() or len(cedula) < 6 or len(cedula) > 15:
            return volver('La cédula debe contener solo números (6–15 dígitos).')
        if not telefono.isdigit() or len(telefono) != 10:
            return volver('El teléfono debe contener exactamente 10 dígitos.')
        if len(username) < 4 or len(username) > 30:
            return volver('El usuario debe tener entre 4 y 30 caracteres.')
        if not re.match(r'^[A-Za-z0-9_]+$', username):
            return volver('El usuario solo puede tener letras, números y guión bajo.')
        if len(password) < 8 or len(password) > 64:
            return volver('La contraseña debe tener entre 8 y 64 caracteres.')
        if password != confirmar_password:
            return volver('Las contraseñas no coinciden.')
        if Usuario.objects.filter(username=username).exists():
            return volver('Ese nombre de usuario ya está en uso.')
        if Usuario.objects.filter(email=email).exists():
            return volver('Ese correo ya está registrado.')
        if Usuario.objects.filter(cedula=cedula).exists():
            return volver('Esa cédula ya está registrada.')

        nuevo_usuario = Usuario.objects.create(
            first_name     = first_name,
            email          = email,
            username       = username,
            password       = make_password(password),
            telefono       = telefono,
            tipo_documento = tipo_documento,
            cedula         = cedula,
            rol            = 'CLIENTE',
        )
        Movimiento.objects.create(
            tipo_movimiento = 'evento',
            nombre_producto = 'Registro nuevo cliente',
            motivo          = f'Nuevo cliente registrado: {first_name} | Usuario: {username} | Correo: {email} | Tel: {telefono} | Doc: {tipo_documento} {cedula}',
            cantidad        = 0,
        )
        # Auto-login después del registro
        request.session['usuario_id'] = nuevo_usuario.id
        request.session['rol'] = 'CLIENTE'
        next_url = request.POST.get('next', '').strip() or request.GET.get('next', '').strip()
        messages.success(request, f'✅ ¡Bienvenido, {first_name}! Tu cuenta ha sido creada.')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect('usuario')

    next_url = request.GET.get('next', '')
    return render(request, 'registro.html', {'datos': {}, 'next_url': next_url})

def crear_repartidor(request):

    if request.method == 'POST':
        datos      = request.POST
        first_name = datos.get('first_name', '').strip()
        email      = datos.get('email', '').strip()
        username   = datos.get('username', '').strip()
        cedula     = datos.get('cedula', '').strip()
        tipo_doc   = datos.get('tipo_documento', '').strip()
        telefono   = datos.get('telefono', '').strip()
        password   = datos.get('password', '')
        confirmar  = datos.get('confirmar', '')
        vehiculo   = datos.get('vehiculo', '').strip()
        placa      = datos.get('placa', '').strip()

        def volver(msg):
            messages.error(request, msg)
            return render(request, 'crear-repartidor.html', {'datos': datos})

        # Placa solo es obligatoria para Moto y Carro
        campos_base = [first_name, email, username, password, confirmar, telefono, tipo_doc, cedula, vehiculo]
        if not all(campos_base):
            return volver('Todos los campos son obligatorios.')
        if len(first_name) < 3 or len(first_name) > 60:
            return volver('El nombre debe tener entre 3 y 60 caracteres.')
        if not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñÜü ]+$', first_name):
            return volver('El nombre completo solo puede contener letras y espacios.')
        if tipo_doc not in ['CC', 'TI', 'CE', 'PAS']:
            return volver('Selecciona un tipo de identificación válido.')
        if not cedula.isdigit() or len(cedula) < 6 or len(cedula) > 15:
            return volver('La cédula debe contener solo números (6–15 dígitos).')
        if not telefono.isdigit() or len(telefono) != 10:
            return volver('El teléfono debe contener exactamente 10 dígitos.')
        if len(username) < 4 or len(username) > 30:
            return volver('El usuario debe tener entre 4 y 30 caracteres.')
        if not re.match(r'^[A-Za-z0-9_]+$', username):
            return volver('El usuario solo puede tener letras, números y guión bajo.')
        if len(password) < 8 or len(password) > 64:
            return volver('La contraseña debe tener entre 8 y 64 caracteres.')
        if password != confirmar:
            return volver('Las contraseñas no coinciden.')
        if vehiculo not in ['Moto', 'Bicicleta', 'Carro']:
            return volver('Selecciona un tipo de vehículo válido.')
        if vehiculo != 'Bicicleta':
            if not placa or not re.match(r'^[A-Za-z0-9]{1,6}$', placa):
                return volver('La placa debe tener máximo 6 caracteres alfanuméricos.')
            placa_upper = placa.upper()
            if NotificacionRepartidor.objects.filter(placa__iexact=placa_upper).exists():
                return volver('Esa placa ya está registrada por otro repartidor.')
            if Repartidor.objects.filter(placa__iexact=placa_upper).exists():
                return volver('Esa placa ya está registrada por otro repartidor.')
            placa = placa_upper
        else:
            placa = None
        if Usuario.objects.filter(username=username).exists():
            return volver('Ese nombre de usuario ya está en uso.')
        if Usuario.objects.filter(email=email).exists():
            return volver('Ese correo ya está registrado.')
        if cedula and Usuario.objects.filter(cedula=cedula).exists():
            return volver('Esa cédula ya está registrada.')

        # Crear usuario inactivo (pendiente de aprobación)
        usuario = Usuario.objects.create(
            first_name     = first_name,
            email          = email,
            username       = username,
            cedula         = cedula or None,
            tipo_documento = tipo_doc or None,
            password       = make_password(password),
            telefono       = telefono,
            rol            = 'REPARTIDOR',
            is_active      = False,  # Desactivo hasta que sea aprobado
        )

        # Crear notificación para repartidor pendiente
        NotificacionRepartidor.objects.create(
            usuario  = usuario,
            vehiculo = vehiculo,
            placa    = placa,
        )
        Movimiento.objects.create(
            tipo_movimiento = 'evento',
            nombre_producto = 'Solicitud de repartidor',
            motivo          = f'Nueva solicitud de repartidor pendiente de aprobación: {first_name} | Usuario: {username} | Correo: {email} | Tel: {telefono} | Vehículo: {vehiculo}{" | Placa: " + placa if placa else ""}',
            cantidad        = 0,
        )

        # Enviar correo de confirmación al administrador
        try:
            admins = Usuario.objects.filter(rol='ADMIN')
            admin_emails = [admin.email for admin in admins]
            if admin_emails:
                asunto = f"Nuevo repartidor pendiente de aprobación: {first_name}"
                mensaje = f"""
                Hola administrador,

                Se ha registrado un nuevo repartidor que requiere tu aprobación:

                Nombre: {first_name}
                Usuario: {username}
                Email: {email}
                Teléfono: {telefono}
                Tipo de documento: {tipo_doc}
                Cédula: {cedula}
                Vehículo: {vehiculo}
                Placa: {placa}

                Por favor revisa el panel de administración para aprobar o rechazar esta solicitud.

                Saludos,
                Sistema Deportes 360
                """
                email_obj = EmailMessage(
                    asunto,
                    mensaje,
                    'noreply@deportes360.com',
                    admin_emails
                )
                email_obj.send(fail_silently=True)
        except Exception as e:
            print(f"Error enviando email a admins: {e}")

        # Mostrar página de agradecimiento
        return render(request, 'registro_repartidor_confirmado.html', {
            'nombre': first_name,
            'email': email
        })

    return render(request, 'crear-repartidor.html', {'datos': {}})

def crear_admin(request):
    admin_existe = Usuario.objects.filter(rol='ADMIN').exists()
    rol_sesion = request.session.get('rol')

    # Si ya hay admins, solo puede entrar alguien logueado como ADMIN
    if admin_existe and rol_sesion != 'ADMIN':
        return redirect('sinacceso')

    if request.method == "POST":
        usuario_val    = request.POST.get("usuario", "").strip()
        correo         = request.POST.get("correo", "").strip()
        telefono       = request.POST.get("telefono", "").strip()
        codigo         = request.POST.get("codigo", "").strip()
        contrasena     = request.POST.get("contrasena", "")
        confirmar      = request.POST.get("confirmar", "")
        first_name     = request.POST.get("first_name", "").strip()
        fecha_nac      = request.POST.get("fecha_nacimiento") or None
        barrio         = request.POST.get("barrio") or None
        localidad      = request.POST.get("localidad") or None
        tipo_documento = request.POST.get("tipo_documento") or None
        cedula = request.POST.get("cedula", "").strip()

        if not cedula:
            return render(request, "crear_admin.html", {
            "error": "La cédula es obligatoria"
        })

        if not cedula.isdigit():
            return render(request, "crear_admin.html", {
            "error": "La cédula debe contener solo números"
        })

        if contrasena != confirmar:
            return render(request, "crear_admin.html", {"error": "Las contraseñas no coinciden"})
        if not telefono.isdigit() or len(telefono) < 10:
            return render(request, "crear_admin.html", {"error": "El teléfono debe contener solo números y mínimo 10 dígitos"})
        if codigo not in ["ADM-123", "ADM-456"]:
            return render(request, "crear_admin.html", {"error": "Código incorrecto"})
        if tipo_documento not in ["CC", "TI", "CE", "PAS"]:
            return render(request, "crear_admin.html", {"error": "Selecciona un tipo de identificación válido"})
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
        Movimiento.objects.create(
            tipo_movimiento = 'evento',
            nombre_producto = 'Registro nuevo administrador',
            motivo          = f'Nuevo administrador creado: {first_name} | Usuario: {usuario_val} | Correo: {correo} | Tel: {telefono} | Doc: {tipo_documento} {cedula}',
            cantidad        = 0,
        )
        messages.success(request, "Administrador creado exitosamente.")
        return redirect("login")
    return render(request, "crear_admin.html")


# ── Aprobación de Repartidores ────────────────────────────────────────────────

def aprobar_repartidor(request, notificacion_id):
    """Aprueba un repartidor registrado"""
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    
    if not usuario_id or rol != 'ADMIN':
        return redirect('sinacceso')
    
    try:
        notificacion = NotificacionRepartidor.objects.get(id=notificacion_id)
        usuario = notificacion.usuario
        
        # Activar usuario
        usuario.is_active = True
        usuario.save()
        
        # Crear repartidor
        Repartidor.objects.create(
            usuario=usuario,
            vehiculo=notificacion.vehiculo,
            placa=notificacion.placa,
        )
        
        # Actualizar notificación
        from datetime import datetime
        notificacion.estado = 'aprobado'
        notificacion.fecha_respuesta = datetime.now()
        notificacion.save()
        
        # Enviar correo de aprobación al repartidor
        try:
            asunto = "¡Tu registro como repartidor ha sido aprobado!"
            mensaje = f"""
            Hola {usuario.first_name},

            ¡Bienvenido! Tu solicitud de registro como repartidor ha sido APROBADA.

            Ahora puedes iniciar sesión con tus credenciales:
            - Usuario: {usuario.username}
            - Email: {usuario.email}

            Accede a tu panel en: [URL de tu aplicación]

            Saludos,
            Sistema Deportes 360
            """
            email_obj = EmailMessage(
                asunto,
                mensaje,
                'noreply@deportes360.com',
                [usuario.email]
            )
            email_obj.send(fail_silently=True)
        except Exception as e:
            print(f"Error enviando email de aprobación: {e}")
        
        messages.success(request, f'✅ Repartidor {usuario.first_name} aprobado exitosamente.')

        from inventario.models import Movimiento as MovimientoInv
        MovimientoInv.objects.create(
            tipo_movimiento='evento',
            nombre_producto=f'Repartidor aprobado: {usuario.first_name}',
            motivo=f'El administrador aprobó al repartidor "{usuario.first_name}" (usuario: {usuario.username}).',
        )

    except NotificacionRepartidor.DoesNotExist:
        messages.error(request, 'Notificación no encontrada.')
    except Exception as e:
        messages.error(request, f'Error al aprobar repartidor: {e}')

    return redirect('panel_admin')


def rechazar_repartidor(request, notificacion_id):
    """Rechaza un repartidor registrado"""
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    
    if not usuario_id or rol != 'ADMIN':
        return redirect('sinacceso')
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', 'No especificado').strip()
        
        try:
            notificacion = NotificacionRepartidor.objects.get(id=notificacion_id)
            usuario = notificacion.usuario
            nombre_usuario = usuario.first_name  # Guardar nombre antes de eliminar
            
            # Actualizar notificación
            from datetime import datetime
            notificacion.estado = 'rechazado'
            notificacion.fecha_respuesta = datetime.now()
            notificacion.motivo_rechazo = motivo
            notificacion.save()
            
            # Enviar correo de rechazo al repartidor
            try:
                asunto = "Solicitud de registro - Resultado"
                mensaje = f"""
                Hola {usuario.first_name},

                Lamentablemente, tu solicitud de registro como repartidor ha sido RECHAZADA.

                Motivo: {motivo}

                Si tienes dudas, por favor contáctanos.

                Saludos,
                Sistema Deportes 360
                """
                email_obj = EmailMessage(
                    asunto,
                    mensaje,
                    'noreply@deportes360.com',
                    [usuario.email]
                )
                email_obj.send(fail_silently=True)
            except Exception as e:
                print(f"Error enviando email de rechazo: {e}")
            
            # Eliminar usuario no aprobado (opcional - comentar si prefieres mantener registro)
            usuario.delete()
            
            messages.success(request, f'❌ Solicitud de {nombre_usuario} rechazada.')

            from inventario.models import Movimiento as MovimientoInv
            MovimientoInv.objects.create(
                tipo_movimiento='evento',
                nombre_producto=f'Repartidor rechazado: {nombre_usuario}',
                motivo=f'El administrador rechazó la solicitud de "{nombre_usuario}". Motivo: {motivo}',
            )

        except NotificacionRepartidor.DoesNotExist:
            messages.error(request, 'Notificación no encontrada.')
        except Exception as e:
            messages.error(request, f'Error al rechazar repartidor: {e}')
        
        return redirect('panel_admin')
    
    # Si es GET, mostrar formulario de rechazo
    try:
        notificacion = NotificacionRepartidor.objects.get(id=notificacion_id)
        return render(request, 'rechazar_repartidor.html', {'notificacion': notificacion})
    except NotificacionRepartidor.DoesNotExist:
        messages.error(request, 'Notificación no encontrada.')
        return redirect('panel_admin')


# ── Dashboards por rol ────────────────────────────────────────────────────────

def usuario(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    if not usuario_id or rol != "CLIENTE":
        return redirect("sinacceso")

    usuario = Usuario.objects.get(id=usuario_id)
    categoria = request.GET.get("categoria")

    from inventario.models import Producto
    base = Producto.objects.filter(descontinuado=False).exclude(imagen='').exclude(imagen__isnull=True)
    if categoria == "HOMBRE":
        productos = base.filter(categoria__in=["HOMBRE", "MIXTO"])
    elif categoria == "MUJER":
        productos = base.filter(categoria__in=["MUJER", "MIXTO"])
    elif categoria == "MIXTO":
        productos = base.filter(categoria="MIXTO")
    else:
        productos = base

    campos_faltantes = []
    if not (usuario.first_name and usuario.first_name.strip()):
        campos_faltantes.append('Nombre completo')
    if not (usuario.telefono and usuario.telefono.strip()):
        campos_faltantes.append('Teléfono')
    if not usuario.tipo_documento:
        campos_faltantes.append('Tipo de documento')
    if not (usuario.cedula and usuario.cedula.strip()):
        campos_faltantes.append('Número de documento')

    return render(request, "usuario.html", {
        "usuario":          usuario,
        "productos":        productos,
        "perfil_completo":  len(campos_faltantes) == 0,
        "campos_faltantes": campos_faltantes,
    })

def catalogoindex(request):
    from inventario.models import TallaProducto
    categoria = request.GET.get('categoria', '').upper()
    if categoria == 'HOMBRE':
        categorias = ['HOMBRE', 'MIXTO']
    elif categoria == 'MUJER':
        categorias = ['MUJER', 'MIXTO']
    elif categoria == 'MIXTO':
        categorias = ['MIXTO']
    else:
        categorias = None

    base = Producto.objects.filter(descontinuado=False).exclude(imagen='').exclude(imagen__isnull=True)
    if categorias:
        productos = base.filter(categoria__in=categorias)
    else:
        productos = base

    for p in productos:
        p.stock_total = sum(t.stock for t in TallaProducto.objects.filter(producto=p))

    return render(request, 'catalogoindex.html', {
        'productos': productos,
        'categoria': categoria,
    })

def admin(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')

    if 'test' in sys.argv:
        return render(request, 'admin/panel_admin.html')
    if not usuario_id or rol != 'ADMIN':
        return redirect('sinacceso')

    hoy = date.today()

    # ── Carga masiva ─────────────────────────────────────────────────────────
    if request.method == "POST" and request.FILES.get("archivo"):
        archivo = request.FILES["archivo"]
        try:
            if archivo.name.endswith(".csv"):
                df = pd.read_csv(io.TextIOWrapper(archivo.file, encoding="utf-8"))
            elif archivo.name.endswith(".xlsx"):
                df = pd.read_excel(archivo)
            else:
                messages.error(request, "Solo se permiten archivos CSV o Excel")
                return redirect("panel_admin")

            columnas = ["nombre", "precio", "descripcion", "categoria", "talla", "stock"]
            faltantes = [c for c in columnas if c not in df.columns]
            if faltantes:
                messages.error(request, f"Columnas faltantes en el archivo: {', '.join(faltantes)}")
                return redirect("panel_admin")

            productos_actualizados = set()
            filas_ok = 0
            for _, fila in df.iterrows():
                nombre    = str(fila["nombre"]).strip()
                precio    = float(fila["precio"])
                desc      = str(fila["descripcion"]).strip()
                categoria = str(fila["categoria"]).strip().upper()
                talla     = str(fila["talla"]).strip()
                stock     = int(fila["stock"])

                if stock < 0:
                    messages.warning(request, f"Stock negativo en '{nombre}' talla {talla}, fila ignorada.")
                    continue

                producto, _ = Producto.objects.update_or_create(
                    slug=slugify(nombre),
                    defaults={
                        "nombre":      nombre,
                        "precio":      precio,
                        "descripcion": desc,
                        "categoria":   categoria,
                    }
                )

                TallaProducto.objects.update_or_create(
                    producto=producto,
                    talla=talla,
                    defaults={"stock": stock}
                )

                if stock > 0:
                    Movimiento.objects.create(
                        producto=producto,
                        talla=talla,
                        tipo_movimiento='entrada',
                        cantidad=stock,
                        motivo='Carga masiva',
                        nombre_producto=producto.nombre,
                    )

                productos_actualizados.add(producto.pk)
                filas_ok += 1

            # Recalcular stock_total de todos los productos afectados
            for pk in productos_actualizados:
                total = TallaProducto.objects.filter(producto_id=pk).aggregate(t=Sum('stock'))['t'] or 0
                Producto.objects.filter(pk=pk).update(stock_total=total)

            messages.success(request, f"✅ Carga completada: {filas_ok} filas procesadas, {len(productos_actualizados)} producto(s) actualizados.")

        except Exception as e:
            messages.error(request, f"Error al procesar archivo: {e}")
        return redirect("panel_admin")

    # ── Fechas con filtro GET ─────────────────────────────────────────────────
    def _dt(date_str, end_of_day=False):
        d = dt_mod.datetime.strptime(date_str, '%Y-%m-%d')
        return d.replace(hour=23, minute=59, second=59) if end_of_day else d

    primera_venta = Venta.objects.order_by('fecha_venta').values_list('fecha_venta', flat=True).first()
    default_inicio = primera_venta.strftime('%Y-%m-%d') if primera_venta else hoy.strftime('%Y-%m-%d')

    hoy_str      = hoy.strftime('%Y-%m-%d')
    fecha_inicio = request.GET.get('fecha_inicio') or default_inicio
    if fecha_inicio < default_inicio:
        fecha_inicio = default_inicio
    if fecha_inicio > hoy_str:
        fecha_inicio = hoy_str
    fecha_fin    = request.GET.get('fecha_fin') or hoy_str
    if fecha_fin > hoy_str:
        fecha_fin = hoy_str
    if fecha_fin < fecha_inicio:
        fecha_fin = hoy_str

    fi_aware = _dt(fecha_inicio)
    ff_aware = _dt(fecha_fin, end_of_day=True)

    # Períodos preset para el filtro de inicio
    mes_act_ini  = hoy.replace(day=1).strftime('%Y-%m-%d')
    mes_act_fin  = hoy.strftime('%Y-%m-%d')
    primer_ant   = (hoy.replace(day=1) - timedelta(days=1)).replace(day=1)
    mes_ant_ini  = primer_ant.strftime('%Y-%m-%d')
    mes_ant_fin  = (hoy.replace(day=1) - timedelta(days=1)).strftime('%Y-%m-%d')
    anio_ini     = hoy.replace(month=1, day=1).strftime('%Y-%m-%d')
    anio_fin     = hoy.strftime('%Y-%m-%d')

    # ── Movimientos ───────────────────────────────────────────────────────────
    movimientos_qs   = Movimiento.objects.select_related('producto').prefetch_related('producto__tallas').order_by('-fecha')
    total_entradas   = movimientos_qs.filter(tipo_movimiento='entrada').count()
    total_salidas    = movimientos_qs.filter(tipo_movimiento='salida').count()
    unidades_entrada = movimientos_qs.filter(tipo_movimiento='entrada').aggregate(t=Sum('cantidad'))['t'] or 0
    unidades_salida  = movimientos_qs.filter(tipo_movimiento='salida').aggregate(t=Sum('cantidad'))['t'] or 0

    # ── Ventas filtradas ──────────────────────────────────────────────────────
    ventas = Venta.objects.select_related('cliente__usuario').order_by('-fecha_venta')
    ventas = ventas.filter(fecha_venta__gte=fi_aware, fecha_venta__lte=ff_aware).prefetch_related('detalleventaproductos_set__producto')

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
        .filter(venta__fecha_venta__gte=fi_aware, venta__fecha_venta__lte=ff_aware)
        .values('producto__nombre')
        .annotate(total=Sum('subtotal'))
        .order_by('-total')[:10]
    )
    nombres_productos = json.dumps([v['producto__nombre'] for v in ventas_por_producto])
    totales_productos = json.dumps([float(v['total']) for v in ventas_por_producto])

    # ── Top productos para tabla ──────────────────────────────────────────────
    top_raw = (
        DetalleVentaProductos.objects
        .filter(venta__fecha_venta__gte=fi_aware, venta__fecha_venta__lte=ff_aware)
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
    desde_12 = dt_mod.datetime.combine(hoy - timedelta(days=365), dt_mod.time.min)
    por_mes = (
        Venta.objects.filter(fecha_venta__gte=desde_12)
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
    ultimos_pedidos = (
        Venta.objects
        .select_related('cliente__usuario')
        .prefetch_related(
            Prefetch(
                'detalleventaproductos_set',
                queryset=DetalleVentaProductos.objects.select_related('producto'),
            ),
            Prefetch(
                'inventario_asignaciones',
                queryset=Asignacion.objects.select_related('repartidor__usuario'),
            ),
        )
        .order_by('-fecha_venta')[:20]
    )

    usuarios    = Usuario.objects.all()
    primeras_ids = SugerenciaInventario.objects.values('nombre').annotate(pid=Min('id')).values_list('pid', flat=True)
    sugerencias  = SugerenciaInventario.objects.filter(id__in=primeras_ids).prefetch_related('respuestas').order_by('-fecha')
    productos    = Producto.objects.prefetch_related('tallas').all()
    bajo_stock   = Producto.objects.filter(stock_total__lte=5, descontinuado=False).order_by('stock_total')
    
    # ── Repartidores pendientes de aprobación ──────────────────────────────────
    repartidores_pendientes = NotificacionRepartidor.objects.filter(estado='pendiente').select_related('usuario').order_by('-fecha_solicitud')
    cantidad_repartidores_pendientes = repartidores_pendientes.count()

    return render(request, 'productos/admin.html', {
        # generales
        'ultimos_pedidos':   ultimos_pedidos,
        'usuarios':          usuarios,
        'ventas':            ventas,
        'movimientos':       movimientos_qs,
        'sugerencias':       sugerencias,
        'productos':         productos,
        'bajo_stock':        bajo_stock,
        'repartidores_pendientes': repartidores_pendientes,
        'cantidad_repartidores_pendientes': cantidad_repartidores_pendientes,
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
        # filtro de período
        'fecha_inicio':    fecha_inicio,
        'fecha_fin':       fecha_fin,
        'default_inicio':  default_inicio,
        'mes_act_ini':     mes_act_ini,
        'mes_act_fin':     mes_act_fin,
        'mes_ant_ini':     mes_ant_ini,
        'mes_ant_fin':     mes_ant_fin,
        'anio_ini':        anio_ini,
        'anio_fin':        anio_fin,
    })

def venta_detalle_json(request, venta_id):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    if not usuario_id or rol != 'ADMIN':
        return JsonResponse({'ok': False}, status=403)

    try:
        venta = Venta.objects.select_related('cliente__usuario').get(pk=venta_id)
    except Venta.DoesNotExist:
        return JsonResponse({'ok': False}, status=404)

    detalles = DetalleVentaProductos.objects.filter(venta=venta).select_related('producto')
    envio    = Envio.objects.filter(venta=venta).select_related('repartidor__usuario').first()
    resena   = getattr(venta, 'resena', None)

    return JsonResponse({
        'ok': True,
        'id': venta.id,
        'fecha': venta.fecha_venta.strftime('%d/%m/%Y %H:%M'),
        'estado': venta.estado,
        'cliente': {
            'nombre':    venta.cliente.usuario.first_name or venta.cliente.usuario.username,
            'username':  venta.cliente.usuario.username,
            'email':     venta.cliente.usuario.email,
            'telefono':  venta.cliente.usuario.telefono or '—',
            'cedula':    venta.cliente.usuario.cedula or '—',
            'direccion': venta.cliente.direccion or '—',
        },
        'telefonoContacto': venta.telefonoContacto or '—',
        'direccionEnvio':   venta.direccionEnvio or '—',
        'metodo_de_pago':   venta.metodo_de_pago,
        'metodoEnvio':      venta.metodoEnvio,
        'cantProducto':     venta.cantProducto,
        'totalVenta':       str(venta.totalVenta),
        'observaciones':    venta.observaciones or '',
        'detalles': [
            {
                'producto':        d.producto.nombre,
                'categoria':       d.producto.categoria,
                'talla':           d.talla,
                'cantidad':        d.cantidad,
                'precio_unitario': str(d.precio_unitario),
                'descuento':       str(d.descuento),
                'subtotal':        str(d.subtotal),
            }
            for d in detalles
        ],
        'envio': {
            'repartidor': envio.repartidor.usuario.first_name or envio.repartidor.usuario.username,
            'vehiculo':   envio.repartidor.vehiculo,
            'placa':      envio.repartidor.placa or '',
            'fecha_envio': str(envio.fecha_envio),
            'estado':     envio.estado,
        } if envio else None,
        'resena': {
            'estado_llegada': resena.get_estado_llegada_display(),
            'comentario':     resena.comentario or '',
            'fecha':          resena.fecha.strftime('%d/%m/%Y %H:%M'),
        } if resena else None,
    })


def venta_cambiar_estado(request, venta_id):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('rol')
    if not usuario_id or rol != 'ADMIN':
        return JsonResponse({'ok': False}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)

    try:
        body   = json.loads(request.body)
        estado = body.get('estado', '').strip()
    except Exception:
        return JsonResponse({'ok': False}, status=400)

    if estado not in {'Pendiente', 'En proceso', 'Enviado', 'Entregado', 'Cancelado'}:
        return JsonResponse({'ok': False, 'error': 'Estado inválido'}, status=400)

    try:
        venta = Venta.objects.get(pk=venta_id)
    except Venta.DoesNotExist:
        return JsonResponse({'ok': False}, status=404)

    venta.estado = estado
    venta.save(update_fields=['estado'])
    return JsonResponse({'ok': True, 'estado': estado})


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
                    from datetime import datetime, date
                    fecha = datetime.strptime(fecha_nac, '%Y-%m-%d').date()
                    hoy = date.today()
                    if fecha > hoy:
                        messages.error(request, 'La fecha de nacimiento no puede ser futura.')
                        return redirect('perfil_admin')
                    edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
                    if edad < 18:
                        messages.error(request, 'Debes tener al menos 18 años para actualizar el perfil.')
                        return redirect('perfil_admin')
                    admin.fecha_nacimiento = fecha
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

        # ── Foto de perfil ──────────────────────────────────────
        elif accion == 'foto':
            foto = request.FILES.get('foto_perfil')
            if foto:
                admin.foto_perfil = foto
                admin.save()
                messages.success(request, '✅ Foto de perfil actualizada.')
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
                              .select_related('venta__cliente__usuario')\
                              .order_by('-fecha_pedido')
    pedidos_activos   = Pedido.objects.filter(repartidor=repartidor_obj, estado='En camino')\
                              .select_related('venta__cliente__usuario')\
                              .order_by('-fecha_pedido')
    mis_pedidos       = Pedido.objects.filter(repartidor=repartidor_obj, estado='Entregado')\
                              .select_related('venta__cliente__usuario')\
                              .order_by('-fecha_pedido')

    # Ganancias
    total_ganancias = mis_pedidos.aggregate(
        total=Sum('valor_domicilio')
    )['total'] or 0

    import urllib.parse
    mensaje_wa = urllib.parse.quote(
        "¡Hola! Soy el repartidor de Deportes 360. "
        "Ya voy en camino con su pedido, pronto lo estaré entregando. 🚀"
    )

    campos_faltantes = []
    if not (usuario.first_name and usuario.first_name.strip()):
        campos_faltantes.append('Nombre completo')
    if not (usuario.telefono and usuario.telefono.strip()):
        campos_faltantes.append('Teléfono')
    if not usuario.tipo_documento:
        campos_faltantes.append('Tipo de documento')
    if not (usuario.cedula and usuario.cedula.strip()):
        campos_faltantes.append('Número de documento')

    return render(request, 'repartidor.html', {
        'Nombre':            usuario.first_name,
        'usuario':           usuario,
        'repartidor':        repartidor_obj,
        'ventas_pendientes': ventas_pendientes,
        'pedidos_activos':   pedidos_activos,
        'mis_pedidos':       mis_pedidos,
        'total_ganancias':   total_ganancias,
        'mensaje_wa':        mensaje_wa,
        'perfil_completo':   len(campos_faltantes) == 0,
        'campos_faltantes':  campos_faltantes,
    })


# ── Perfil y cuenta ───────────────────────────────────────────────────────────

def perfil_incompleto(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    usuario = get_object_or_404(Usuario, id=usuario_id)

    if request.method == 'POST':
        usuario.first_name     = request.POST.get('nombre', '').strip()
        usuario.telefono       = request.POST.get('telefono', '').strip()
        usuario.tipo_documento = request.POST.get('tipo_documento', '').strip()
        usuario.cedula         = request.POST.get('cedula', '').strip()
        usuario.save()
        from django.contrib import messages as msg
        msg.success(request, '✅ Perfil actualizado. Ya puedes continuar con tu compra.')
        return redirect('carrito')

    faltan = []
    if not (usuario.first_name and usuario.first_name.strip()):
        faltan.append('Nombre completo')
    if not (usuario.telefono and usuario.telefono.strip()):
        faltan.append('Teléfono')
    if not usuario.tipo_documento:
        faltan.append('Tipo de documento')
    if not (usuario.cedula and usuario.cedula.strip()):
        faltan.append('Cédula')

    if not faltan:
        return redirect('formulario_compra')

    return render(request, 'usuarios/perfil_incompleto.html', {
        'usuario': usuario,
        'faltan': faltan,
    })


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

            nuevo_username = request.POST.get('username', usuario.username).strip()
            if nuevo_username and nuevo_username != usuario.username:
                if Usuario.objects.filter(username=nuevo_username).exclude(id=usuario.id).exists():
                    messages.error(request, 'Ese nombre de usuario ya está en uso.')
                    return redirect('perfil')
                usuario.username = nuevo_username

            fecha_nac = request.POST.get('fecha_nacimiento', '')
            if fecha_nac:
                try:
                    from datetime import datetime, date
                    fecha = datetime.strptime(fecha_nac, '%Y-%m-%d').date()
                    hoy = date.today()
                    if fecha > hoy:
                        messages.error(request, 'La fecha de nacimiento no puede ser futura.')
                        return redirect('perfil')
                    edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
                    if edad < 18:
                        messages.error(request, 'Debes tener al menos 18 años para actualizar el perfil.')
                        return redirect('perfil')
                    usuario.fecha_nacimiento = fecha
                except ValueError:
                    pass

            usuario.save()
            messages.success(request, '✅ Perfil actualizado correctamente.')
            return redirect('perfil')

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
            return redirect('perfil')

        # ── Foto de perfil ──────────────────────────────────────
        elif accion == 'foto':
            foto = request.FILES.get('foto_perfil')
            if foto:
                usuario.foto_perfil = foto
                usuario.save()
                messages.success(request, '✅ Foto de perfil actualizada.')
            return redirect('perfil')

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
            usuario.barrio         = request.POST.get('barrio', '').strip() or None

            nuevo_username = request.POST.get('username', usuario.username).strip()
            if nuevo_username and nuevo_username != usuario.username:
                if Usuario.objects.filter(username=nuevo_username).exclude(id=usuario.id).exists():
                    messages.error(request, 'Ese nombre de usuario ya está en uso.')
                    return redirect('perfil_repartidor')
                usuario.username = nuevo_username

            fecha_nac = request.POST.get('fecha_nacimiento', '')
            if fecha_nac:
                try:
                    from datetime import datetime, date
                    fecha = datetime.strptime(fecha_nac, '%Y-%m-%d').date()
                    hoy = date.today()
                    if fecha > hoy:
                        messages.error(request, 'La fecha de nacimiento no puede ser futura.')
                        return redirect('perfil_repartidor')
                    edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
                    if edad < 18:
                        messages.error(request, 'Debes tener al menos 18 años para actualizar el perfil.')
                        return redirect('perfil_repartidor')
                    usuario.fecha_nacimiento = fecha
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

        # ── Foto de perfil ──────────────────────────────────────
        elif accion == 'foto':
            foto = request.FILES.get('foto_perfil')
            if foto:
                usuario.foto_perfil = foto
                usuario.save()
                messages.success(request, '✅ Foto de perfil actualizada.')
            return redirect('perfil_repartidor')

    # ── Progreso del perfil ──────────────────────────────────────
    campos = [
        usuario.first_name, usuario.email, usuario.telefono,
        usuario.tipo_documento, usuario.cedula, usuario.localidad,
        usuario.barrio, usuario.fecha_nacimiento, repartidor.vehiculo, repartidor.placa,
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
    usuario_id_sesion = request.session.get('usuario_id')
    rol = request.session.get('rol')

    if not usuario_id_sesion or rol != 'ADMIN':
        return redirect('sinacceso')

    if request.method != 'POST':
        return redirect('panel_admin')

    usuario = get_object_or_404(Usuario, id=id)

    if usuario.id == usuario_id_sesion:
        messages.error(request, 'No puedes eliminar tu propia cuenta.')
        return redirect('panel_admin')

    from inventario.models import Movimiento as MovimientoInv
    nombre  = usuario.first_name or usuario.username
    rol_usr = usuario.get_rol_display() if hasattr(usuario, 'get_rol_display') else usuario.rol
    usuario.delete()

    MovimientoInv.objects.create(
        tipo_movimiento = 'evento',
        nombre_producto = f'Usuario eliminado: {nombre}',
        motivo          = f'El administrador eliminó al usuario "{nombre}" (rol: {rol_usr}).',
    )

    messages.success(request, f'Usuario "{nombre}" eliminado correctamente.')
    return redirect('/panel-admin/?seccion=usuarios')

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
    # Actualizar estado de la venta para que se refleje en mis_compras
    if pedido.venta:
        pedido.venta.estado = 'En camino'
        pedido.venta.save()
    messages.success(request, "Pedido tomado correctamente.")
    return redirect('repartidor')

def entregar_pedido(request, pedido_id):
    usuario_id = request.session.get('usuario_id')
    repartidor_obj = get_object_or_404(Repartidor, usuario__id=usuario_id)
    pedido = get_object_or_404(Pedido, id=pedido_id, repartidor=repartidor_obj)
    pedido.estado = 'Entregado'
    pedido.save()
    # Actualizar estado de la venta para que se refleje en mis_compras
    if pedido.venta:
        pedido.venta.estado = 'Entregado'
        pedido.venta.save()
    messages.success(request, "Pedido marcado como entregado.")
    return redirect('repartidor')

def devolver_pedido(request, pedido_id):
    usuario_id = request.session.get('usuario_id')
    repartidor_obj = get_object_or_404(Repartidor, usuario__id=usuario_id)
    pedido = get_object_or_404(Pedido, id=pedido_id, repartidor=repartidor_obj, estado='En camino')
    pedido.estado = 'Disponible'
    pedido.repartidor = None
    pedido.save()
    if pedido.venta:
        pedido.venta.estado = 'Pendiente'
        pedido.venta.save()
    messages.success(request, f'Pedido #{pedido.id} devuelto. Ya está disponible para otro repartidor.')
    return redirect('repartidor')

def mis_pedidos(request):
    pedidos = Pedido.objects.all()
    return render(
        request,
        'usuarios/mis_pedidos.html',
        {'pedidos': pedidos}
    )

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

import re as _re
import unicodedata as _ud

def _normalizar(texto):
    """Minúsculas, sin acentos, sin caracteres especiales comunes de evasión."""
    t = texto.lower()
    t = _ud.normalize('NFD', t)
    t = ''.join(c for c in t if _ud.category(c) != 'Mn')  # quitar tildes
    # sustituir números por letras que parecen (0→o, 1→i/l, 3→e, 4→a, @→a, $→s)
    for src, dst in [('0','o'),('1','i'),('3','e'),('4','a'),('@','a'),('$','s'),('!','i')]:
        t = t.replace(src, dst)
    # colapsar espacios/puntos/guiones entre letras para evitar e-v-a-s-i-o-n
    t = _re.sub(r'[\s._\-*]+', '', t)
    return t

_GROSERIAS = [
    # palabras fuertes generales
    'hijueputa','hijuepucha','hp','mierda','mierd',
    'puta','puto','perra','perro','zorra','zorro',
    'gonorrea','gonorre','gonorr',
    'malparido','malparida',
    'culiao','culiado','culiada',
    'marica','maricon','maricas',
    'culo','culos',
    'verga','vergas',
    'pene','penes',
    'vagina',
    'coño','cono',
    'carajo','carajos',
    'idiota','idiotas',
    'estupido','estupida',
    'imbecil',
    'cabron','cabrona',
    'pendejo','pendeja',
    'maldito','maldita',
    'bastardo','bastarda',
    'hdp','hpta',
    'chingada','chinga','chingo',
    'pinche','pinches',
    'guevon','huevon','gueva','hueva',
    'joder',
    'polla',
    'mamao','mamada',
    'hdpm',
    'puñetero','puñetera',
    'fornico','fornicio',
    'follador','folladora',
    'cabreo',
    'ojete',
    'mamon','mamona',
    'lameculos',
    'sorete',
    'boludo','boluda',
    'pelotudo',
    'conchudo','conchuda',
]

def _tiene_groseria(texto):
    """Devuelve la palabra encontrada o None."""
    normalizado = _normalizar(texto)
    for palabra in _GROSERIAS:
        if palabra in normalizado:
            return palabra
    return None

def sugerencias(request):
    usuario_id = request.session.get('usuario_id')
    usuario = get_object_or_404(Usuario, id=usuario_id)
    nombre = usuario.first_name or usuario.username
    correo = usuario.email or ''

    if request.method == 'POST':
        try:
            texto         = request.POST.get('texto', '').strip()
            sugerencia_id = request.POST.get('sugerencia_id')

            if not texto:
                return JsonResponse({'ok': False, 'error': 'Mensaje vacío'})

            groseria = _tiene_groseria(texto)
            if groseria:
                return JsonResponse({'ok': False, 'error': 'Por favor usa un lenguaje respetuoso. No se permiten groserías o palabras ofensivas.'})

            # Si ya tenemos el hilo, solo agregar respuesta
            if sugerencia_id:
                sug = get_object_or_404(SugerenciaInventario, id=sugerencia_id)
                RespuestaSugerencia.objects.create(
                    sugerencia=sug,
                    mensaje=texto,
                    es_admin=False
                )
                return JsonResponse({'ok': True, 'mensaje': texto})

            # Buscar hilo existente por correo (único) o por nombre como fallback
            sug_existente = (
                SugerenciaInventario.objects.filter(correo=correo).first()
                if correo else
                SugerenciaInventario.objects.filter(nombre=nombre).first()
            )

            if sug_existente:
                RespuestaSugerencia.objects.create(
                    sugerencia=sug_existente,
                    mensaje=texto,
                    es_admin=False
                )
                return JsonResponse({'ok': True, 'sugerencia_id': sug_existente.id})
            else:
                nueva = SugerenciaInventario.objects.create(
                    nombre=nombre,
                    correo=correo,
                    mensaje=texto
                )
                return JsonResponse({'ok': True, 'sugerencia_id': nueva.id})

        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=200)

    # Buscar el hilo del usuario por correo primero, luego por nombre
    mi_sugerencia = (
        SugerenciaInventario.objects.filter(correo=correo).order_by('-fecha').first()
        if correo else None
    )
    if not mi_sugerencia:
        mi_sugerencia = SugerenciaInventario.objects.filter(
            nombre=nombre
        ).order_by('-fecha').first()

    return render(request, 'sugerencias.html', {
        'mi_sugerencia': mi_sugerencia,
        'usuario':       usuario,
    })

def panel_sugerencias(request):
    sugerencias = SugerenciaInventario.objects.all().order_by('-fecha')
    return render(request, "panel_sugerencias.html", {"sugerencias": sugerencias})

# ── Recuperación de contraseña ────────────────────────────────────────────────

def restablecer_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        if not email:
            messages.error(request, "Debes ingresar un correo.")
            return redirect('restablecer')

        usuario = Usuario.objects.filter(email__iexact=email).first()

        if not usuario:
            # No revelar si el correo existe o no (seguridad)
            messages.success(request, "Si ese correo está registrado, recibirás un enlace para restablecer tu contraseña.")
            return redirect('restablecer')

        # Generar token y guardarlo
        token = str(uuid.uuid4())
        usuario.token_recuperacion = token
        usuario.save()

        enlace = request.build_absolute_uri(f"/nueva_contrasena/{token}/")

        cuerpo = f"""
<html>
  <body style="font-family:Arial,sans-serif; background:#f5f5f5; padding:20px;">
    <div style="max-width:600px; margin:auto; border-radius:10px; overflow:hidden;
                box-shadow:0 4px 12px rgba(0,0,0,0.1);">
      <div style="background:#c40000; padding:30px; text-align:center; color:#fff;">
        <h2 style="margin:0;">Recuperar Contraseña</h2>
        <p style="margin:0;">Deportes 360</p>
      </div>
      <div style="background:#fff; padding:30px; text-align:center;">
        <p style="font-size:16px; color:#333;">
          Hola <strong>{usuario.first_name or 'usuario'}</strong>,
        </p>
        <p style="font-size:15px; color:#555;">
          Haz clic en el botón para restablecer tu contraseña:
        </p>
        <a href="{enlace}" style="display:inline-block; background:#c40000; color:#fff;
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

        try:
            correo = EmailMessage(
                subject="Recuperación de contraseña - Deportes 360",
                body=cuerpo,
                from_email="Deportes 360 <juancuervo141414@gmail.com>",
                to=[usuario.email],
            )
            correo.content_subtype = "html"
            correo.send(fail_silently=False)
            messages.success(request, "Correo enviado. Revisa tu bandeja de entrada.")
        except Exception:
            messages.error(request, "No se pudo enviar el correo. Intenta de nuevo más tarde.")

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
        elif len(password1) < 8:
            messages.error(request, 'Debe tener mínimo 8 caracteres.')
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
        from_email="Deportes 360 <juancuervo141414@gmail.com>",
        to=["juancuervo141414@gmail.com"],
    )
    correo.send(fail_silently=False)
    return HttpResponse("Correo enviado correctamente")


# ── Mensajes Admin ↔ Repartidor ───────────────────────────────────────────────

def mensajes_repartidores_lista(request):
    if request.session.get('rol') != 'ADMIN':
        return JsonResponse({'ok': False}, status=403)
    repartidores = Repartidor.objects.select_related('usuario').all()
    data = []
    for r in repartidores:
        ultimo = MensajeRepartidor.objects.filter(repartidor=r).order_by('-fecha').first()
        no_leidos = MensajeRepartidor.objects.filter(repartidor=r, es_admin=False, leido=False).count()
        data.append({
            'id': r.id,
            'nombre': r.usuario.first_name or r.usuario.username,
            'username': r.usuario.username,
            'no_leidos': no_leidos,
            'ultimo': ultimo.mensaje[:60] if ultimo else '',
            'ultima_hora': ultimo.fecha.strftime('%d/%m/%Y %H:%M') if ultimo else '',
        })
    return JsonResponse({'ok': True, 'repartidores': data})


def mensajes_con_repartidor(request, repartidor_id):
    if request.session.get('rol') != 'ADMIN':
        return JsonResponse({'ok': False}, status=403)
    repartidor = get_object_or_404(Repartidor, id=repartidor_id)

    if request.method == 'POST':
        texto = request.POST.get('mensaje', '').strip()
        if not texto:
            return JsonResponse({'ok': False, 'error': 'Mensaje vacío'})
        msg = MensajeRepartidor.objects.create(repartidor=repartidor, mensaje=texto, es_admin=True)
        return JsonResponse({'ok': True, 'id': msg.id, 'hora': msg.fecha.strftime('%d/%m/%Y %H:%M')})

    MensajeRepartidor.objects.filter(repartidor=repartidor, es_admin=False, leido=False).update(leido=True)
    msgs = MensajeRepartidor.objects.filter(repartidor=repartidor)
    return JsonResponse({
        'ok': True,
        'nombre': repartidor.usuario.first_name or repartidor.usuario.username,
        'mensajes': [
            {'id': m.id, 'mensaje': m.mensaje, 'es_admin': m.es_admin, 'hora': m.fecha.strftime('%d/%m/%Y %H:%M')}
            for m in msgs
        ],
    })


def mensajes_repartidor_pagina(request):
    if request.session.get('rol') != 'REPARTIDOR':
        return redirect('sinacceso')
    return render(request, 'mensajes_repartidor.html')


def mensajes_repartidor_inbox(request):
    usuario_id = request.session.get('usuario_id')
    if request.session.get('rol') != 'REPARTIDOR':
        return JsonResponse({'ok': False}, status=403)
    repartidor = get_object_or_404(Repartidor, usuario__id=usuario_id)

    if request.method == 'POST':
        texto = request.POST.get('mensaje', '').strip()
        if not texto:
            return JsonResponse({'ok': False, 'error': 'Mensaje vacío'})
        msg = MensajeRepartidor.objects.create(repartidor=repartidor, mensaje=texto, es_admin=False)
        return JsonResponse({'ok': True, 'id': msg.id, 'hora': msg.fecha.strftime('%d/%m/%Y %H:%M')})

    MensajeRepartidor.objects.filter(repartidor=repartidor, es_admin=True, leido=False).update(leido=True)
    msgs = MensajeRepartidor.objects.filter(repartidor=repartidor)
    no_leidos = MensajeRepartidor.objects.filter(repartidor=repartidor, es_admin=True, leido=False).count()
    return JsonResponse({
        'ok': True,
        'mensajes': [
            {'id': m.id, 'mensaje': m.mensaje, 'es_admin': m.es_admin, 'hora': m.fecha.strftime('%d/%m/%Y %H:%M')}
            for m in msgs
        ],
        'no_leidos': no_leidos,
    })

