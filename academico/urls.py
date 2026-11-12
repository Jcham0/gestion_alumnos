from django.urls import path

from . import views

app_name = 'academico'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path(
        'panel/alumno/',
        views.PanelAlumnoView.as_view(),
        name='panel_alumno',
    ),
    path(
        'panel/profesor/',
        views.PanelProfesorView.as_view(),
        name='panel_profesor',
    ),
    path('registro/', views.registro, name='registro'),
    # CRUD de alumnos
    path('alumnos/', views.AlumnoListView.as_view(), name='alumno_lista'),
    path('alumnos/nuevo/', views.AlumnoCreateView.as_view(), name='alumno_crear'),
    path(
        'alumnos/<int:pk>/editar/',
        views.AlumnoUpdateView.as_view(),
        name='alumno_editar',
    ),
    path(
        'alumnos/<int:pk>/eliminar/',
        views.AlumnoDeleteView.as_view(),
        name='alumno_eliminar',
    ),
    # CRUD de asignaturas
    path(
        'asignaturas/',
        views.AsignaturaListView.as_view(),
        name='asignatura_lista',
    ),
    path(
        'asignaturas/nueva/',
        views.AsignaturaCreateView.as_view(),
        name='asignatura_crear',
    ),
    path(
        'asignaturas/<int:pk>/editar/',
        views.AsignaturaUpdateView.as_view(),
        name='asignatura_editar',
    ),
    path(
        'asignaturas/<int:pk>/eliminar/',
        views.AsignaturaDeleteView.as_view(),
        name='asignatura_eliminar',
    ),
    # CRUD de matrículas y registro de notas
    path(
        'matriculas/',
        views.MatriculaListView.as_view(),
        name='matricula_lista',
    ),
    path(
        'matriculas/nueva/',
        views.MatriculaCreateView.as_view(),
        name='matricula_crear',
    ),
    path(
        'matriculas/<int:pk>/editar/',
        views.MatriculaUpdateView.as_view(),
        name='matricula_editar',
    ),
    path(
        'matriculas/<int:pk>/eliminar/',
        views.MatriculaDeleteView.as_view(),
        name='matricula_eliminar',
    ),
    path('notas/nueva/', views.NotaCreateView.as_view(), name='nota_crear'),
]
