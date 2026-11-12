from io import BytesIO

import pandas as pd
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, TemplateView

from academico.mixins import (
    ProfesorRequiredMixin,
    es_alumno,
    puede_gestionar_academico,
)
from academico.models import Alumno

from .forms import FiltrosEstadisticasForm, ImportarNotasCSVForm
from .services import (
    calcular_media_por_asignatura,
    calcular_porcentaje_aprobados,
    detectar_valores_atipicos_iqr,
    obtener_dataframe_boletin,
    importar_notas_csv,
    obtener_dataframe_notas,
    obtener_ranking_alumnos,
)


class ProfesorAccessMixin(LoginRequiredMixin, ProfesorRequiredMixin):
    """Restringe los informes y la importación a Profesor y superusuario."""


class ImportarNotasView(ProfesorAccessMixin, FormView):
    """Recibe el CSV y muestra el resumen del servicio de importación."""

    form_class = ImportarNotasCSVForm
    template_name = 'reportes/importar_notas.html'
    success_url = reverse_lazy('reportes:importar_notas')

    def form_valid(self, form):
        try:
            resumen = importar_notas_csv(form.cleaned_data['archivo'])
        except ValueError as error:
            form.add_error('archivo', str(error))
            return self.form_invalid(form)

        messages.success(
            self.request,
            (
                f'Importación finalizada: {resumen.importadas} notas importadas '
                f'y {resumen.total_rechazadas} filas rechazadas.'
            ),
        )
        return self.render_to_response(
            self.get_context_data(form=form, resumen=resumen)
        )


class EstadisticasNotasView(ProfesorAccessMixin, TemplateView):
    """Presenta y exporta informes de notas con filtros opcionales."""

    template_name = 'reportes/estadisticas.html'

    def get_dataframe(self):
        formulario = FiltrosEstadisticasForm(self.request.GET)
        if not formulario.is_valid():
            return formulario, pd.DataFrame(
                columns=['alumno', 'asignatura', 'evaluacion', 'valor', 'anio']
            )

        asignatura = formulario.cleaned_data['asignatura']
        dataframe = obtener_dataframe_notas(
            asignatura_id=asignatura.pk if asignatura else None,
            anio=formulario.cleaned_data['anio'] or None,
        )
        return formulario, dataframe

    def get(self, request, *args, **kwargs):
        formato = request.GET.get('export')
        if formato:
            formulario, dataframe = self.get_dataframe()
            if not formulario.is_valid():
                return self.render_to_response(
                    self.get_context_data(form=formulario)
                )
            if formato == 'csv':
                respuesta = HttpResponse(
                    dataframe.to_csv(index=False).encode('utf-8-sig'),
                    content_type='text/csv; charset=utf-8',
                )
                respuesta['Content-Disposition'] = (
                    'attachment; filename="informe_notas.csv"'
                )
                return respuesta
            if formato == 'xlsx':
                salida = BytesIO()
                with pd.ExcelWriter(salida, engine='openpyxl') as escritor:
                    dataframe.to_excel(
                        escritor,
                        sheet_name='Notas',
                        index=False,
                    )
                    calcular_media_por_asignatura(dataframe).to_excel(
                        escritor,
                        sheet_name='Medias',
                        index=False,
                    )
                    calcular_porcentaje_aprobados(dataframe).to_excel(
                        escritor,
                        sheet_name='Aprobados',
                        index=False,
                    )
                    obtener_ranking_alumnos(dataframe).to_excel(
                        escritor,
                        sheet_name='Ranking',
                        index=False,
                    )
                    detectar_valores_atipicos_iqr(dataframe).to_excel(
                        escritor,
                        sheet_name='Atipicos',
                        index=False,
                    )
                respuesta = HttpResponse(
                    salida.getvalue(),
                    content_type=(
                        'application/vnd.openxmlformats-officedocument.'
                        'spreadsheetml.sheet'
                    ),
                )
                respuesta['Content-Disposition'] = (
                    'attachment; filename="informe_notas.xlsx"'
                )
                return respuesta
            return HttpResponseBadRequest('Formato de exportación desconocido.')

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        formulario, dataframe = self.get_dataframe()

        contexto.update(
            {
                'form': formulario,
                'notas': dataframe.to_dict('records'),
                'alumnos': Alumno.objects.order_by('apellidos', 'nombre'),
                'medias': calcular_media_por_asignatura(dataframe).to_dict(
                    'records'
                ),
                'aprobados': calcular_porcentaje_aprobados(
                    dataframe
                ).to_dict('records'),
                'ranking': obtener_ranking_alumnos(dataframe).to_dict(
                    'records'
                ),
                'atipicos': detectar_valores_atipicos_iqr(
                    dataframe
                ).to_dict('records'),
            }
        )
        return contexto


class BoletinAlumnoCSVView(LoginRequiredMixin, View):
    """Descarga el boletín propio o permite a Profesor seleccionar un alumno."""

    def get(self, request, *_args, **_kwargs):
        if puede_gestionar_academico(request.user):
            alumno_id = request.GET.get('alumno')
            if not alumno_id:
                return HttpResponseBadRequest(
                    'Selecciona un alumno para descargar su boletín.'
                )
            try:
                alumno_id = int(alumno_id)
            except ValueError:
                return HttpResponseBadRequest('El identificador no es válido.')
            alumno = get_object_or_404(Alumno, pk=alumno_id)
        elif es_alumno(request.user):
            if 'alumno' in request.GET:
                raise PermissionDenied
            try:
                alumno = request.user.perfil_alumno
            except Alumno.DoesNotExist as error:
                raise PermissionDenied from error
        else:
            raise PermissionDenied

        dataframe = obtener_dataframe_boletin(alumno.pk)
        respuesta = HttpResponse(
            dataframe.to_csv(index=False).encode('utf-8-sig'),
            content_type='text/csv; charset=utf-8',
        )
        respuesta['Content-Disposition'] = (
            f'attachment; filename="boletin_alumno_{alumno.pk}.csv"'
        )
        return respuesta
