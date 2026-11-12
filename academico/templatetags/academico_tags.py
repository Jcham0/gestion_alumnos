from django import template

from academico.mixins import es_alumno, puede_gestionar_academico

register = template.Library()


@register.simple_tag
def acceso_gestion_academica(usuario):
    """Devuelve si el usuario puede ver la navegación de gestión."""
    return puede_gestionar_academico(usuario)


register.simple_tag(es_alumno)
