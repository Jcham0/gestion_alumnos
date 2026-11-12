from django import forms

from academico.models import Asignatura, Matricula


class ImportarNotasCSVForm(forms.Form):
    """Formulario para subir el archivo CSV de notas."""

    archivo = forms.FileField(
        label='Archivo CSV',
        help_text=(
            'Columnas requeridas: email_alumno, codigo_asignatura, '
            'evaluacion y valor.'
        ),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data['archivo']
        if not archivo.name.lower().endswith('.csv'):
            raise forms.ValidationError('El archivo debe tener extensión .csv.')
        return archivo


class FiltrosEstadisticasForm(forms.Form):
    """Permite filtrar las estadísticas por asignatura y año académico."""

    asignatura = forms.ModelChoiceField(
        queryset=Asignatura.objects.none(),
        required=False,
        empty_label='Todas las asignaturas',
        label='Asignatura',
    )
    anio = forms.ChoiceField(
        choices=(),
        required=False,
        label='Año académico',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['asignatura'].queryset = Asignatura.objects.order_by(
            'curso',
            'nombre',
        )
        anios = (
            Matricula.objects.order_by()
            .values_list('anio_academico', flat=True)
            .distinct()
            .order_by('-anio_academico')
        )
        self.fields['anio'].choices = [('', 'Todos los años')] + [
            (anio, anio) for anio in anios
        ]
