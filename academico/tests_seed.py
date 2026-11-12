from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase

from academico.management.commands import seed_datos
from academico.models import Alumno, Asignatura, Matricula, Nota
from reportes.services import importar_notas_csv


class SeedDatosCommandTests(TestCase):
    """Comprueba el comando de seed, la limpieza selectiva y su CSV."""

    def setUp(self):
        self.directorio_temporal = TemporaryDirectory()
        self.addCleanup(self.directorio_temporal.cleanup)
        self.ruta_csv = Path(self.directorio_temporal.name) / 'notas.csv'
        self.parche_ruta_csv = patch.object(
            seed_datos,
            'RUTA_CSV_PRUEBA',
            self.ruta_csv,
        )
        self.parche_ruta_csv.start()
        self.addCleanup(self.parche_ruta_csv.stop)

    def ejecutar_seed(self, *args, **opciones):
        salida = StringIO()
        call_command('seed_datos', *args, stdout=salida, **opciones)
        return salida.getvalue()

    def test_crea_n_alumnos_datos_relacionados_usuarios_y_credenciales(self):
        salida = self.ejecutar_seed(3)

        alumnos_seed = Alumno.objects.filter(
            email__startswith=seed_datos.PREFIJO_EMAIL
        )
        asignaturas_seed = Asignatura.objects.filter(
            codigo__startswith=seed_datos.PREFIJO_CODIGO
        )
        self.assertEqual(alumnos_seed.count(), 3)
        self.assertEqual(asignaturas_seed.count(), 5)
        total_matriculas = Matricula.objects.filter(
            alumno__in=alumnos_seed
        ).count()
        total_notas = Nota.objects.filter(
            matricula__alumno__in=alumnos_seed
        ).count()
        self.assertGreater(total_matriculas, 3)
        self.assertGreater(total_notas, 0)
        self.assertTrue(self.ruta_csv.exists())

        modelo_usuario = get_user_model()
        usuario_profesor = modelo_usuario.objects.get(username='seed_profesor')
        usuario_alumno = modelo_usuario.objects.get(username='seed_alumno')
        self.assertQuerySetEqual(
            usuario_profesor.groups.order_by('name'),
            ['Profesor'],
            transform=lambda grupo: grupo.name,
        )
        self.assertQuerySetEqual(
            usuario_alumno.groups.order_by('name'),
            ['Alumno'],
            transform=lambda grupo: grupo.name,
        )
        self.assertIsNotNone(usuario_alumno.perfil_alumno)
        for username, etiqueta in zip(
            seed_datos.USUARIOS_PRUEBA,
            ('Profesor', 'Alumno'),
            strict=True,
        ):
            linea_credencial = next(
                linea
                for linea in salida.splitlines()
                if linea.startswith(f'{etiqueta}: {username} / ')
            )
            password = linea_credencial.rsplit(' / ', maxsplit=1)[1]
            self.assertTrue(
                modelo_usuario.objects.get(username=username).check_password(
                    password
                )
            )

        datos = pd.read_csv(self.ruta_csv, dtype=str, keep_default_na=False)
        self.assertEqual(
            list(datos.columns),
            ['email_alumno', 'codigo_asignatura', 'evaluacion', 'valor'],
        )
        self.assertEqual(len(datos), 6)
        self.assertEqual(datos.iloc[0].to_dict(), datos.iloc[1].to_dict())
        self.assertEqual(datos.iloc[2]['email_alumno'], '')
        self.assertEqual(datos.iloc[3]['valor'], '10.50')
        self.assertEqual(datos.iloc[4]['email_alumno'], 'no-existe@example.com')
        self.assertEqual(datos.iloc[5]['valor'], '')

        with self.ruta_csv.open(encoding='utf-8') as archivo:
            resumen = importar_notas_csv(archivo)
        self.assertEqual(resumen.importadas, 1)
        self.assertEqual(resumen.total_rechazadas, 5)
        motivos = [rechazo.motivo for rechazo in resumen.rechazadas]
        self.assertTrue(any('duplicada en el CSV' in motivo for motivo in motivos))
        self.assertTrue(any('nulos o vacíos' in motivo for motivo in motivos))
        self.assertTrue(any('entre 0 y 10' in motivo for motivo in motivos))
        self.assertTrue(any('No existe un alumno' in motivo for motivo in motivos))

    def test_limpiar_borra_solo_entidades_del_seed_y_recrea_n_datos(self):
        self.ejecutar_seed(2)
        alumno_manual = Alumno.objects.create(
            nombre='Manual',
            apellidos='Conservado',
            email='manual@example.com',
            fecha_nacimiento='2000-01-01',
        )
        asignatura_manual = Asignatura.objects.create(
            nombre='Asignatura manual',
            codigo='MANUAL',
            curso='1º',
            creditos=3,
        )

        self.ejecutar_seed(1, limpiar=True)

        self.assertEqual(
            Alumno.objects.filter(
                email__startswith=seed_datos.PREFIJO_EMAIL
            ).count(),
            1,
        )
        self.assertEqual(
            Asignatura.objects.filter(
                codigo__startswith=seed_datos.PREFIJO_CODIGO
            ).count(),
            5,
        )
        self.assertTrue(Alumno.objects.filter(pk=alumno_manual.pk).exists())
        self.assertTrue(
            Asignatura.objects.filter(pk=asignatura_manual.pk).exists()
        )
        self.assertEqual(
            get_user_model().objects.filter(
                username__in=seed_datos.USUARIOS_PRUEBA
            ).count(),
            2,
        )

    def test_rechaza_cantidad_no_positiva_antes_de_limpiar(self):
        self.ejecutar_seed(1)

        with self.assertRaises(CommandError):
            self.ejecutar_seed(0, limpiar=True)

        self.assertEqual(
            Alumno.objects.filter(
                email__startswith=seed_datos.PREFIJO_EMAIL
            ).count(),
            1,
        )
