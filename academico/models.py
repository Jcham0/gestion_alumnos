from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Alumno(models.Model):
    """Representa a una persona inscrita en el sistema académico."""

    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    fecha_nacimiento = models.DateField()
    activo = models.BooleanField(default=True)
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='perfil_alumno',
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ('apellidos', 'nombre')

    def __str__(self):
        return f'{self.apellidos}, {self.nombre}'


class Asignatura(models.Model):
    """Representa una asignatura ofrecida en un curso."""

    nombre = models.CharField(max_length=150)
    codigo = models.CharField(max_length=20, unique=True)
    curso = models.CharField(max_length=100)
    creditos = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ('curso', 'nombre')

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'


class Matricula(models.Model):
    """Vincula a un alumno con una asignatura en un año académico."""

    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.CASCADE,
        related_name='matriculas',
    )
    asignatura = models.ForeignKey(
        Asignatura,
        on_delete=models.CASCADE,
        related_name='matriculas',
    )
    anio_academico = models.CharField(max_length=9)

    class Meta:
        ordering = ('-anio_academico', 'alumno_id', 'asignatura_id')
        constraints = [
            models.UniqueConstraint(
                fields=('alumno', 'asignatura', 'anio_academico'),
                name='matricula_alumno_asignatura_anio_uniq',
            ),
        ]

    def __str__(self):
        return (
            f'{self.alumno} - {self.asignatura} '
            f'({self.anio_academico})'
        )


class Nota(models.Model):
    """Registra una calificación de una evaluación de matrícula."""

    class TipoEvaluacion(models.TextChoices):
        PRIMERA = '1ª', '1ª'
        SEGUNDA = '2ª', '2ª'
        FINAL = 'final', 'Final'

    matricula = models.ForeignKey(
        Matricula,
        on_delete=models.CASCADE,
        related_name='notas',
    )
    evaluacion = models.CharField(
        max_length=5,
        choices=TipoEvaluacion.choices,
    )
    valor = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal('0')),
            MaxValueValidator(Decimal('10')),
        ],
    )
    fecha = models.DateField()

    class Meta:
        ordering = ('fecha', 'pk')

    def __str__(self):
        return f'{self.matricula} - {self.get_evaluacion_display()}: {self.valor}'
