from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from datetime import date
from .models import Usuario, Administrador

class RegistroClienteForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    confirmar_password = forms.CharField(widget=forms.PasswordInput, label="Confirmar Contraseña")
    direccion = forms.CharField(max_length=255, label="Dirección")
    fecha_nacimiento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
    input_formats=['%Y-%m-%d'], required=False
)
    barrio = forms.CharField(max_length=50, required=False)

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'first_name', 'password', 'telefono', 'fecha_nacimiento', 'barrio', 'tipo_documento', 'cedula', 'localidad']

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
        fields = ['username', 'email', 'first_name', 'telefono', 'fecha_nacimiento', 'barrio', 'password', 'cedula' ]
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
        usuario.password = make_password(self.cleaned_data['password'])  
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
        