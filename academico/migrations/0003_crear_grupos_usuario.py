from django.db import migrations


def crear_grupos(apps, schema_editor):
    """Crea los grupos requeridos sin alterar grupos ya existentes."""
    grupo = apps.get_model('auth', 'Group')
    administrador = schema_editor.connection.alias
    for nombre in ('Profesor', 'Alumno'):
        grupo.objects.using(administrador).get_or_create(name=nombre)


def conservar_grupos(_apps, _schema_editor):
    """No elimina grupos que podrían tener usuarios o permisos asignados."""


class Migration(migrations.Migration):

    dependencies = [
        ('academico', '0002_alumno_usuario'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(crear_grupos, conservar_grupos),
    ]
