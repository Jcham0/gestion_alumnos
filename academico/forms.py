from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.forms import ModelForm

from .models import Alumno, Asignatura, Matricula, Nota


class RegistroAlumnoForm(UserCreationForm):
    """Formulario de alta con correo obligatorio y único."""

    email = forms.EmailField(
        label='Correo electrónico',
        required=True,
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username', 'email')

    def clean_email(self):
        """Impide registrar un correo ya utilizado, sin distinguir mayúsculas."""
        email = self.cleaned_data['email']
        usuario = get_user_model().objects.filter(email__iexact=email)
        if self.instance.pk:
            usuario = usuario.exclude(pk=self.instance.pk)
        if usuario.exists():
            raise forms.ValidationError(
                'Ya existe una cuenta con este correo electrónico.'
            )
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Nombre de usuario'
        self.fields['password1'].label = 'Contraseña'
        self.fields['password2'].label = 'Confirmar contraseña'


class AlumnoForm(ModelForm):
    """Formulario para crear y editar los datos académicos de un alumno."""

    class Meta:
        model = Alumno
        fields = (
            'nombre',
            'apellidos',
            'email',
            'fecha_nacimiento',
            'activo',
        )
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
        }


class AsignaturaForm(ModelForm):
    """Formulario para crear y editar asignaturas."""

    class Meta:
        model = Asignatura
        fields = ('nombre', 'codigo', 'curso', 'creditos')


class MatriculaForm(ModelForm):
    """Formulario para crear y editar matrículas."""

    class Meta:
        model = Matricula
        fields = ('alumno', 'asignatura', 'anio_academico')
        labels = {
            'alumno': 'Alumno',
            'asignatura': 'Asignatura',
            'anio_academico': 'Año académico',
        }


class NotaForm(ModelForm):
    """Formulario para registrar una nota sin duplicar evaluaciones."""

    class Meta:
        model = Nota
        fields = ('matricula', 'evaluacion', 'valor', 'fecha')
        labels = {
            'matricula': 'Matrícula',
            'evaluacion': 'Evaluación',
            'valor': 'Nota (0-10)',
            'fecha': 'Fecha',
        }
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        datos = super().clean()
        matricula = datos.get('matricula')
        evaluacion = datos.get('evaluacion')
        valor = datos.get('valor')

        if valor is not None and not 0 <= valor <= 10:
            self.add_error('valor', 'La nota debe estar entre 0 y 10.')

        if (
            matricula is not None
            and evaluacion is not None
            and Nota.objects.filter(
                matricula=matricula,
                evaluacion=evaluacion,
            ).exists()
        ):
            self.add_error(
                'evaluacion',
                'Ya existe una nota para esta evaluación y matrícula.',
            )

        return datos
