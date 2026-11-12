"""Crea datos de prueba para probar las funciones académicas."""

import secrets
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from random import SystemRandom

import pandas as pd
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from academico.models import Alumno, Asignatura, Matricula, Nota


PREFIJO_EMAIL = 'seed.alumno.'
PREFIJO_CODIGO = 'SEED'
USUARIOS_PRUEBA = ('seed_profesor', 'seed_alumno')
RUTA_CSV_PRUEBA = (
    Path(__file__).resolve().parents[3] / 'datos' / 'notas_prueba_errores.csv'
)
ASIGNATURAS_PRUEBA = (
    ('Matemáticas de prueba', '1º', 6),
    ('Lengua de prueba', '1º', 5),
    ('Ciencias de prueba', '2º', 6),
    ('Historia de prueba', '2º', 4),
    ('Inglés de prueba', '3º', 5),
)


class Command(BaseCommand):
    """Genera perfiles, matrículas, notas, cuentas y un CSV de errores."""

    help = 'Genera datos de prueba para el proyecto de gestión académica.'

    def add_arguments(self, parser):
        parser.add_argument(
            'cantidad',
            nargs='?',
            type=int,
            default=10,
            help='Número de alumnos a generar (por defecto: 10).',
        )
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Elimina solo los datos identificados como creados por este comando.',
        )

    @transaction.atomic
    def handle(self, *_args, **opciones):
        cantidad = opciones['cantidad']
        if cantidad < 1:
            raise CommandError('La cantidad de alumnos debe ser mayor que cero.')

        if opciones['limpiar']:
            self._limpiar_datos_de_prueba()

        grupo_profesor, _ = Group.objects.get_or_create(name='Profesor')
        grupo_alumno, _ = Group.objects.get_or_create(name='Alumno')
        _, clave_profesor = self._crear_usuario(
            USUARIOS_PRUEBA[0],
            'profesor@example.com',
            grupo_profesor,
        )
        usuario_alumno, clave_alumno = self._crear_usuario(
            USUARIOS_PRUEBA[1],
            'alumno@example.com',
            grupo_alumno,
        )
        asignaturas = self._crear_asignaturas()
        alumnos = self._crear_alumnos(cantidad, usuario_alumno)
        matriculas, matricula_csv = self._crear_matriculas_y_notas(
            alumnos,
            asignaturas,
        )
        self._crear_csv_prueba(matricula_csv)

        self.stdout.write(self.style.SUCCESS('Datos de prueba creados.'))
        self.stdout.write(f'Alumnos creados: {len(alumnos)}')
        self.stdout.write(f'Asignaturas de prueba: {len(asignaturas)}')
        self.stdout.write(f'Matrículas creadas: {matriculas}')
        self.stdout.write(f'CSV de errores: {RUTA_CSV_PRUEBA}')
        self.stdout.write('Credenciales (se regeneran en cada ejecución):')
        self.stdout.write(f'Profesor: {USUARIOS_PRUEBA[0]} / {clave_profesor}')
        self.stdout.write(f'Alumno: {USUARIOS_PRUEBA[1]} / {clave_alumno}')

    def _limpiar_datos_de_prueba(self):
        """Borra exclusivamente entidades marcadas con prefijos reservados."""
        Alumno.objects.filter(email__startswith=PREFIJO_EMAIL).delete()
        Asignatura.objects.filter(codigo__startswith=PREFIJO_CODIGO).delete()
        get_user_model().objects.filter(username__in=USUARIOS_PRUEBA).delete()

    def _crear_usuario(self, username, email, grupo):
        """Crea o restablece una cuenta reservada y asigna su único grupo."""
        modelo_usuario = get_user_model()
        usuario, _ = modelo_usuario.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'is_active': True,
            },
        )
        clave = secrets.token_urlsafe(18)
        usuario.email = email
        usuario.is_active = True
        usuario.is_staff = False
        usuario.is_superuser = False
        usuario.set_password(clave)
        usuario.save()
        usuario.groups.set([grupo])
        return usuario, clave

    def _crear_asignaturas(self):
        """Crea el conjunto fijo de asignaturas identificadas como prueba."""
        asignaturas = []
        for indice, (nombre, curso, creditos) in enumerate(
            ASIGNATURAS_PRUEBA,
            start=1,
        ):
            asignatura, _ = Asignatura.objects.get_or_create(
                codigo=f'{PREFIJO_CODIGO}{indice:03}',
                defaults={
                    'nombre': nombre,
                    'curso': curso,
                    'creditos': creditos,
                },
            )
            asignaturas.append(asignatura)
        return asignaturas

    def _crear_alumnos(self, cantidad, usuario_alumno):
        """Añade perfiles de prueba con correo reservado y único."""
        aleatorio = SystemRandom()
        alumnos = []
        indice = 1
        perfil_alumno_asignado = Alumno.objects.filter(
            usuario=usuario_alumno
        ).exists()
        while len(alumnos) < cantidad:
            email = f'{PREFIJO_EMAIL}{indice:05}@example.com'
            indice += 1
            if Alumno.objects.filter(email=email).exists():
                continue

            hoy = timezone.localdate()
            nacimiento = hoy - timedelta(days=aleatorio.randint(16 * 365, 25 * 365))
            alumno = Alumno.objects.create(
                nombre=aleatorio.choice(
                    ('Ana', 'Beatriz', 'Carlos', 'Daniela', 'Elena', 'Fernando')
                ),
                apellidos=(
                    f'{aleatorio.choice(("García", "López", "Martín", "Pérez"))} '
                    f'{aleatorio.choice(("Ruiz", "Sánchez", "Torres", "Vega"))}'
                ),
                email=email,
                fecha_nacimiento=nacimiento,
                activo=True,
                usuario=usuario_alumno if not perfil_alumno_asignado else None,
            )
            perfil_alumno_asignado = True
            alumnos.append(alumno)
        return alumnos

    def _crear_matriculas_y_notas(self, alumnos, asignaturas):
        """Genera matrículas y calificaciones aleatorias sin repetir evaluación."""
        aleatorio = SystemRandom()
        total_matriculas = 0
        matricula_para_csv = None
        evaluaciones = tuple(Nota.TipoEvaluacion.values)
        anios = ('2025-2026', '2026-2027')

        for indice_alumno, alumno in enumerate(alumnos):
            if indice_alumno == 0:
                elegidas = [
                    asignaturas[0],
                    *aleatorio.sample(asignaturas[1:], k=aleatorio.randint(1, 3)),
                ]
            else:
                elegidas = aleatorio.sample(
                    asignaturas,
                    k=aleatorio.randint(2, len(asignaturas)),
                )

            for indice_asignatura, asignatura in enumerate(elegidas):
                anio = aleatorio.choice(anios)
                matricula = Matricula.objects.create(
                    alumno=alumno,
                    asignatura=asignatura,
                    anio_academico=anio,
                )
                total_matriculas += 1
                if indice_alumno == 0 and indice_asignatura == 0:
                    matricula_para_csv = matricula

                candidatas = [
                    evaluacion
                    for evaluacion in evaluaciones
                    if matricula != matricula_para_csv
                    or evaluacion != Nota.TipoEvaluacion.FINAL
                ]
                for evaluacion in aleatorio.sample(
                    candidatas,
                    k=aleatorio.randint(1, len(candidatas)),
                ):
                    Nota.objects.create(
                        matricula=matricula,
                        evaluacion=evaluacion,
                        valor=Decimal(aleatorio.randint(0, 1000)) / 100,
                        fecha=timezone.localdate()
                        - timedelta(days=aleatorio.randint(0, 365)),
                    )

        return total_matriculas, matricula_para_csv

    def _crear_csv_prueba(self, matricula):
        """Escribe filas válidas e inválidas para probar la importación CSV."""
        if matricula is None:
            raise CommandError('No se pudo preparar una matrícula para el CSV.')
        filas = {
            'email_alumno': [
                matricula.alumno.email,
                matricula.alumno.email,
                '',
                matricula.alumno.email,
                'no-existe@example.com',
                matricula.alumno.email,
            ],
            'codigo_asignatura': [
                matricula.asignatura.codigo,
                matricula.asignatura.codigo,
                matricula.asignatura.codigo,
                matricula.asignatura.codigo,
                matricula.asignatura.codigo,
                matricula.asignatura.codigo,
            ],
            'evaluacion': ['final', 'final', '1ª', '2ª', 'final', 'final'],
            'valor': ['8.50', '8.50', '7.00', '10.50', '6.00', ''],
        }
        RUTA_CSV_PRUEBA.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(filas).to_csv(RUTA_CSV_PRUEBA, index=False)
