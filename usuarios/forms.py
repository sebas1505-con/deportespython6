from django import forms
from .models import Cliente

class RegistroForm(forms.ModelForm):

    class Meta:
        model = Cliente
        fields = [
            'nombre',
            'direccion',
            'fechaNacimiento',
            'barrio',
            'telefono'
        ]
        widgets = {
            'fechaNacimiento': forms.DateInput(attrs={'type': 'date'})
        }
    def clean(self):
        cleaned_data = super().clean()
        clave = cleaned_data.get("clave")
        confirmar = cleaned_data.get("confirmar")

        if clave != confirmar:
            raise forms.ValidationError("Las contraseñas no coinciden")

        return cleaned_data

class RepartidorForm(forms.Form):
    nombre = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Ingresa tu nombre completo'}))
    correo = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'ejemplo@correo.com'}))
    usuario = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Crea tu usuario'}))
    contrasena = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Crea una contraseña'}))
    contrasenaConfirmacion = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Repite tu contraseña'}))
    placa = forms.CharField(max_length=10, widget=forms.TextInput(attrs={'placeholder': 'Ejemplo SFQ-072'}))
    telefono = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'placeholder': '+57 300 000 0000'}))
    vehiculo = forms.ChoiceField(choices=[('', '-- Selecciona tu vehículo --'), ('moto', 'Moto'), ('carro', 'Carro')])
    fecha = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
