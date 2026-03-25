from django import forms
from django.core.exceptions import ValidationError
from datetime import date
from .models import Reporte, Movimiento, Producto


class CompraForm(forms.Form):
    cant_producto = forms.IntegerField(
        label="Cantidad de productos", initial=1,
        widget=forms.NumberInput(attrs={'readonly': 'readonly'})
    )
    METODOS_ENVIO = [('domicilio', 'Domicilio')]
    metodo_envio = forms.ChoiceField(label="Método de envío", choices=METODOS_ENVIO)
    total_venta = forms.DecimalField(
        label="Total de la venta", max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={'readonly': 'readonly'})
    )
    METODOS_PAGO = [
        ('', 'Seleccionar...'),
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
    ]
    metodo_pago = forms.ChoiceField(label="Método de pago", choices=METODOS_PAGO, required=True)
    direccion_envio = forms.CharField(label="Dirección de envío", max_length=255)
    telefono_contacto = forms.CharField(label="Teléfono de contacto", max_length=20)
    observaciones = forms.CharField(
        label="Observaciones",
        widget=forms.Textarea(attrs={'rows': 3, 'cols': 30}),
        required=False
    )


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


class MovimientoForm(forms.ModelForm):
    class Meta:
        model = Movimiento
        fields = ['producto', 'cantidad']

    def clean_cantidad(self):
        cantidad = self.cleaned_data['cantidad']
        if cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a cero")
        return cantidad