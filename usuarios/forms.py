from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from datetime import date
from .models import Usuario, Administrador, Reporte

class RegistroClienteForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    confirmar_password = forms.CharField(widget=forms.PasswordInput, label="Confirmar Contraseña")
    direccion = forms.CharField(max_length=255, label="Dirección")
    fecha_nacimiento = forms.DateField(widget=forms.DateInput(attrs={'type':'date'}), required=False)
    barrio = forms.CharField(max_length=50, required=False)

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'first_name', 'telefono', 'fecha_nacimiento', 'barrio']

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirmar_password"):
            raise forms.ValidationError("Las contraseñas no coinciden")
        return cleaned_data

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.password = make_password(self.cleaned_data['password'])
        usuario.rol = "CLIENTE"
        if commit:
            usuario.save()
        return usuario

class RepartidorForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    confirmar = forms.CharField(widget=forms.PasswordInput, label="Confirmar Contraseña")

    placa = forms.CharField(max_length=10)
    vehiculo = forms.CharField(max_length=20)

    class Meta:
        model = Usuario
        fields = [
            'username',
            'email',
            'first_name',
            'telefono',
            'fecha_nacimiento',
            'barrio',
            'password',
            'cedula'
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'})
        }

    # Validaciones
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirmar"):
            raise forms.ValidationError("Las contraseñas no coinciden")
        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if Usuario.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo ya está registrado.")
        return email

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.password = make_password(self.cleaned_data['password'])  # encriptar
        usuario.rol = 'REPARTIDOR'
        if commit:
            usuario.save()
        return usuario

class AdminForm(forms.ModelForm):
    username = forms.CharField(max_length=50)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=50)
    password = forms.CharField(widget=forms.PasswordInput)
    confirmar_password = forms.CharField(widget=forms.PasswordInput)
    codigo = forms.CharField(max_length=10)

    class Meta:
        model = Administrador
        fields = ['codigo']

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo')
        if codigo != "ADM-000":
            raise forms.ValidationError("Código de administrador inválido")
        return codigo

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirmar_password"):
            raise forms.ValidationError("Las contraseñas no coinciden")
        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if Usuario.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo ya está registrado.")
        return email

    def save(self, commit=True):
        usuario = Usuario(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            first_name=self.cleaned_data['first_name'],
            password=make_password(self.cleaned_data['password']),
            rol='ADMIN'
        )
        if commit:
            usuario.save()
            admin = super().save(commit=False)
            admin.usuario = usuario
            admin.save()
        return usuario
        
class CompraForm(forms.Form):
    cant_producto = forms.IntegerField(label="Cantidad de productos", initial=1, widget=forms.NumberInput(attrs={'readonly': 'readonly'}))
    
    METODOS_ENVIO = [
        ('domicilio', 'Domicilio'),
    ]
    metodo_envio = forms.ChoiceField(label="Método de envío", choices=METODOS_ENVIO, widget=forms.Select)
    
    total_venta = forms.DecimalField(label="Total de la venta", max_digits=10, decimal_places=2, widget=forms.NumberInput(attrs={'readonly': 'readonly'}))
    
    METODOS_PAGO = [
        ('', 'Seleccionar...'),
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
    ]
    metodo_pago = forms.ChoiceField(label="Método de pago", choices=METODOS_PAGO, required=True)
    
    direccion_envio = forms.CharField(label="Dirección de envío", max_length=255)
    telefono_contacto = forms.CharField(label="Teléfono de contacto", max_length=20)
    observaciones = forms.CharField(label="Observaciones", widget=forms.Textarea(attrs={'rows': 3, 'cols': 30}), required=False)

class SeleccionTallaForm(forms.Form):
    TALLAS = [
        ('', '-- Selecciona una talla --'),
        ('S', 'S - pequeña'),
        ('M', 'M - Mediana'),
        ('L', 'L - Larga'),
        ('XL', 'XL - Extra Larga'),
    ]
    talla = forms.ChoiceField(label="Selecciona tu talla", choices=TALLAS, required=False)
    
class ReportesForm(forms.ModelForm):
    class Meta:
        model = Reporte
        fields = ['fecha_inicio', 'fecha_fin']

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")
        hoy = date.today()

        if fecha_inicio and fecha_inicio > hoy:
            raise ValidationError("La fecha de inicio no puede ser posterior a la fecha actual")

        if fecha_fin and fecha_fin > hoy:
            raise ValidationError("La fecha de fin no puede ser posterior a la fecha actual")

        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise ValidationError("La fecha de inicio no puede ser posterior a la fecha de fin")

        return cleaned_data