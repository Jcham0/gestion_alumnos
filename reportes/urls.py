from django.urls import path

from .views import (
    BoletinAlumnoCSVView,
    EstadisticasNotasView,
    ImportarNotasView,
)

app_name = 'reportes'

urlpatterns = [
    path(
        'informes/',
        EstadisticasNotasView.as_view(),
        name='informes',
    ),
    path(
        'notas/estadisticas/',
        EstadisticasNotasView.as_view(),
        name='estadisticas',
    ),
    path(
        'boletin/',
        BoletinAlumnoCSVView.as_view(),
        name='boletin_alumno',
    ),
    path(
        'notas/importar/',
        ImportarNotasView.as_view(),
        name='importar_notas',
    ),
]
