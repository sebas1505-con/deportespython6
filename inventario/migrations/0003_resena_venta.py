import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResenaVenta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado_llegada', models.CharField(
                    choices=[('bien', 'Llegó bien'), ('mal_estado', 'Llegó en mal estado'), ('no_llego', 'No llegó')],
                    max_length=20,
                )),
                ('comentario', models.TextField(blank=True, default='')),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('venta', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='resena',
                    to='inventario.venta',
                )),
            ],
        ),
    ]
