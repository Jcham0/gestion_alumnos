from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Avg, Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import (
    AlumnoForm,
    AsignaturaForm,
    MatriculaForm,
    NotaForm,
    RegistroAlumnoForm,
)
from .mixins import (
    AlumnoRequiredMixin,
    ProfesorRequiredMixin,
    es_alumno,
    puede_gestionar_academico,
)
from .models import Alumno, Asignatura, Matricula, Nota


@login_required
def inicio(request):
    """Envía a cada usuario autenticado al panel que le corresponde."""
    if puede_gestionar_academico(request.user):
        return redirect('academico:panel_profesor')
    if es_alumno(request.user):
        return redirect('academico:panel_alumno')
    return render(request, 'academico/inicio.html')


@require_http_methods(['GET', 'POST'])
def registro(request):
    """Registra una cuenta y la incorpora al grupo Alumno."""
    if request.method == 'POST':
        form = RegistroAlumnoForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                usuario = form.save()
                grupo_alumno = Group.objects.get(name='Alumno')
                usuario.groups.add(grupo_alumno)
                alumno = (
                    Alumno.objects.filter(
                        email__iexact=usuario.email, usuario__isnull=True
                    )
                    .order_by('pk')
                    .first()
                )
                if alumno is not None:
                    alumno.usuario = usuario
                    alumno.save(update_fields=['usuario'])

            messages.success(
                request,
                'Tu cuenta se ha creado correctamente. Ya puedes iniciar sesión.',
            )
            return redirect('login')
    else:
        form = RegistroAlumnoForm()

    return render(request, 'academico/registro.html', {'form': form})


class ProfesorAccessMixin(LoginRequiredMixin, ProfesorRequiredMixin):
    """Restringe las vistas de gestión académica al grupo Profesor."""


class AlumnoAccessMixin(LoginRequiredMixin, AlumnoRequiredMixin):
    """Restringe el panel personal a usuarios del grupo Alumno."""


class PanelProfesorView(ProfesorAccessMixin, TemplateView):
    """Muestra accesos rápidos para el trabajo del profesorado."""

    template_name = 'academico/panel_profesor.html'


class PanelAlumnoView(AlumnoAccessMixin, ListView):
    """Lista únicamente las matrículas del perfil del usuario actual."""

    template_name = 'academico/panel_alumno.html'
    context_object_name = 'matriculas'

    def get_queryset(self):
        return (
            Matricula.objects.filter(alumno__usuario=self.request.user)
            .select_related('asignatura')
            .prefetch_related('notas')
            .annotate(media=Avg('notas__valor'))
        )


class AlumnoListView(ProfesorAccessMixin, ListView):
    """Lista alumnos con búsqueda y paginación."""

    model = Alumno
    template_name = 'academico/alumno_list.html'
    context_object_name = 'alumnos'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        consulta = self.request.GET.get('q', '').strip()
        if consulta:
            queryset = queryset.filter(
                Q(nombre__icontains=consulta)
                | Q(apellidos__icontains=consulta)
                | Q(email__icontains=consulta)
            )
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['consulta'] = self.request.GET.get('q', '').strip()
        return contexto


class AlumnoCreateView(ProfesorAccessMixin, SuccessMessageMixin, CreateView):
    """Crea un alumno sin permitir asignar su usuario desde el formulario."""

    model = Alumno
    form_class = AlumnoForm
    template_name = 'academico/alumno_form.html'
    success_url = reverse_lazy('academico:alumno_lista')
    success_message = 'Alumno creado correctamente.'


class AlumnoUpdateView(ProfesorAccessMixin, SuccessMessageMixin, UpdateView):
    """Edita los datos de un alumno sin cambiar su cuenta asociada."""

    model = Alumno
    form_class = AlumnoForm
    template_name = 'academico/alumno_form.html'
    success_url = reverse_lazy('academico:alumno_lista')
    success_message = 'Alumno actualizado correctamente.'


class AlumnoDeleteView(ProfesorAccessMixin, DeleteView):
    """Elimina un alumno y sus matrículas y notas dependientes."""

    model = Alumno
    template_name = 'academico/alumno_confirm_delete.html'
    success_url = reverse_lazy('academico:alumno_lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Alumno eliminado correctamente.')
        return response


class AsignaturaListView(ProfesorAccessMixin, ListView):
    """Lista asignaturas con búsqueda y paginación."""

    model = Asignatura
    template_name = 'academico/asignatura_list.html'
    context_object_name = 'asignaturas'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        consulta = self.request.GET.get('q', '').strip()
        if consulta:
            queryset = queryset.filter(
                Q(nombre__icontains=consulta) | Q(codigo__icontains=consulta)
            )
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['consulta'] = self.request.GET.get('q', '').strip()
        return contexto


class AsignaturaCreateView(
    ProfesorAccessMixin,
    SuccessMessageMixin,
    CreateView,
):
    """Crea una asignatura."""

    model = Asignatura
    form_class = AsignaturaForm
    template_name = 'academico/asignatura_form.html'
    success_url = reverse_lazy('academico:asignatura_lista')
    success_message = 'Asignatura creada correctamente.'


class AsignaturaUpdateView(
    ProfesorAccessMixin,
    SuccessMessageMixin,
    UpdateView,
):
    """Actualiza una asignatura."""

    model = Asignatura
    form_class = AsignaturaForm
    template_name = 'academico/asignatura_form.html'
    success_url = reverse_lazy('academico:asignatura_lista')
    success_message = 'Asignatura actualizada correctamente.'


class AsignaturaDeleteView(ProfesorAccessMixin, DeleteView):
    """Elimina una asignatura y sus matrículas y notas dependientes."""

    model = Asignatura
    template_name = 'academico/asignatura_confirm_delete.html'
    success_url = reverse_lazy('academico:asignatura_lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Asignatura eliminada correctamente.')
        return response


class MatriculaListView(ProfesorAccessMixin, ListView):
    """Lista las matrículas con los datos relacionados."""

    model = Matricula
    template_name = 'academico/matricula_list.html'
    context_object_name = 'matriculas'
    paginate_by = 10

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related('alumno', 'asignatura')
            .prefetch_related('notas')
        )


class MatriculaCreateView(
    ProfesorAccessMixin,
    SuccessMessageMixin,
    CreateView,
):
    """Crea una matrícula."""

    model = Matricula
    form_class = MatriculaForm
    template_name = 'academico/matricula_form.html'
    success_url = reverse_lazy('academico:matricula_lista')
    success_message = 'Matrícula creada correctamente.'


class MatriculaUpdateView(
    ProfesorAccessMixin,
    SuccessMessageMixin,
    UpdateView,
):
    """Edita una matrícula."""

    model = Matricula
    form_class = MatriculaForm
    template_name = 'academico/matricula_form.html'
    success_url = reverse_lazy('academico:matricula_lista')
    success_message = 'Matrícula actualizada correctamente.'


class MatriculaDeleteView(ProfesorAccessMixin, DeleteView):
    """Elimina una matrícula y las notas asociadas."""

    model = Matricula
    template_name = 'academico/matricula_confirm_delete.html'
    success_url = reverse_lazy('academico:matricula_lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Matrícula eliminada correctamente.')
        return response


class NotaCreateView(
    ProfesorAccessMixin,
    SuccessMessageMixin,
    CreateView,
):
    """Registra una nota en una matrícula."""

    model = Nota
    form_class = NotaForm
    template_name = 'academico/nota_form.html'
    success_url = reverse_lazy('academico:matricula_lista')
    success_message = 'Nota registrada correctamente.'

    def get_initial(self):
        inicial = super().get_initial()
        matricula_id = self.request.GET.get('matricula')
        if matricula_id:
            inicial['matricula'] = matricula_id
        return inicial
