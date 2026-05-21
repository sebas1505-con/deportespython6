from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Administrador, Cliente, Reporte, Usuario


class UsuarioModelTest(TestCase):
    def test_usuario_str_returns_username(self):
        usuario = Usuario.objects.create(
            username='juan123',
            email='juan@example.com',
            first_name='Juan',
            password='pass123',
            rol='CLIENTE',
            telefono='3001234567',
            is_active=True,
        )
        self.assertEqual(str(usuario), 'juan123')

    def test_cliente_str_returns_cliente_label(self):
        usuario = Usuario.objects.create(
            username='maria456',
            email='maria@example.com',
            first_name='María',
            password='pass123',
            rol='CLIENTE',
            telefono='3007654321',
            is_active=True,
        )
        cliente = Cliente.objects.create(usuario=usuario, direccion='Calle Falsa 123')
        self.assertEqual(str(cliente), 'Cliente: maria456')

    def test_administrador_str_returns_admin_label(self):
        usuario = Usuario.objects.create(
            username='admin1',
            email='admin1@example.com',
            first_name='Admin',
            password='adminpass',
            rol='ADMIN',
            telefono='3000000000',
            is_active=True,
        )
        admin = Administrador.objects.create(usuario=usuario, codigo='ADMIN001')
        self.assertEqual(str(admin), 'Admin: admin1')


class ReporteModelTest(TestCase):
    def test_reporte_clean_fails_when_fecha_fin_is_before_fecha_inicio(self):
        hoy = date.today()
        reporte = Reporte(
            fecha_inicio=hoy,
            fecha_fin=hoy - timedelta(days=1),
            total_ventas=0,
            total_productos_vendidos=0,
        )
        with self.assertRaises(ValidationError):
            reporte.clean()
