from django.contrib.auth.mixins import UserPassesTestMixin


def puede_gestionar_academico(usuario):
    """Indica si el usuario es profesor o superusuario."""
    return usuario.is_authenticated and (
        usuario.is_superuser
        or usuario.groups.filter(name='Profesor').exists()
    )


def es_alumno(usuario):
    """Indica si el usuario pertenece al grupo Alumno."""
    return usuario.is_authenticated and usuario.groups.filter(name='Alumno').exists()


class ProfesorRequiredMixin(UserPassesTestMixin):
    """Permite el acceso a profesores y superusuarios."""

    def test_func(self):
        return puede_gestionar_academico(self.request.user)


class AlumnoRequiredMixin(UserPassesTestMixin):
    """Permite el acceso únicamente a usuarios del grupo Alumno."""

    def test_func(self):
        return es_alumno(self.request.user)
