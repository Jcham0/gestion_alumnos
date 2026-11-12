from django.contrib import admin

from .models import Alumno, Asignatura, Matricula, Nota


@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = (
        'apellidos',
        'nombre',
        'email',
        'fecha_nacimiento',
        'activo',
        'usuario',
    )
    search_fields = ('nombre', 'apellidos', 'email')
    list_filter = ('activo', 'fecha_nacimiento')


@admin.register(Asignatura)
class AsignaturaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'curso', 'creditos')
    search_fields = ('codigo', 'nombre', 'curso')
    list_filter = ('curso', 'creditos')


@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'asignatura', 'anio_academico')
    search_fields = (
        'alumno__nombre',
        'alumno__apellidos',
        'alumno__email',
        'asignatura__nombre',
        'asignatura__codigo',
    )
    list_filter = ('anio_academico', 'asignatura')


@admin.register(Nota)
class NotaAdmin(admin.ModelAdmin):
    list_display = ('matricula', 'evaluacion', 'valor', 'fecha')
    search_fields = (
        'matricula__alumno__nombre',
        'matricula__alumno__apellidos',
        'matricula__asignatura__nombre',
        'matricula__asignatura__codigo',
    )
    list_filter = ('evaluacion', 'fecha')
