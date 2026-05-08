from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0013_make_correo_optional'),
    ]

    operations = [
        migrations.AlterField(
            model_name='movimiento',
            name='talla',
            field=models.CharField(blank=True, default='', max_length=5),
        ),
        migrations.AlterField(
            model_name='movimiento',
            name='tipo_movimiento',
            field=models.CharField(
                choices=[('entrada', 'Entrada'), ('salida', 'Salida'), ('evento', 'Evento')],
                default='entrada',
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name='movimiento',
            name='cantidad',
            field=models.IntegerField(default=0),
        ),
    ]
