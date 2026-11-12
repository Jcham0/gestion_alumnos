from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .forms import NotaForm, RegistroAlumnoForm
from .mixins import ProfesorRequiredMixin
from .models import Alumno, Asignatura, Matricula, Nota


class ModelosAcademicosTests(TestCase):
    """Comprueba las reglas principales de los modelos académicos."""

    def setUp(self):
        self.alumno = Alumno.objects.create(
            nombre='Ana',
            apellidos='García López',
            email='ana@example.com',
            fecha_nacimiento=date(2005, 4, 12),
        )
        self.asignatura = Asignatura.objects.create(
            nombre='Matemáticas',
            codigo='MAT101',
            curso='1º',
            creditos=6,
        )
        self.matricula = Matricula.objects.create(
            alumno=self.alumno,
            asignatura=self.asignatura,
            anio_academico='2026-2027',
        )

    def test_representaciones_y_relaciones_inversas(self):
        nota = Nota.objects.create(
            matricula=self.matricula,
            evaluacion=Nota.TipoEvaluacion.PRIMERA,
            valor=Decimal('8.50'),
            fecha=date(2026, 12, 1),
        )

        self.assertEqual(str(self.alumno), 'García López, Ana')
        self.assertEqual(str(self.asignatura), 'MAT101 - Matemáticas')
        self.assertIn('2026-2027', str(self.matricula))
        self.assertIn('1ª: 8.50', str(nota))
        self.assertEqual(self.alumno.matriculas.get(), self.matricula)
        self.assertEqual(self.asignatura.matriculas.get(), self.matricula)
        self.assertEqual(self.matricula.notas.get(), nota)

    def test_email_y_codigo_de_asignatura_son_unicos(self):
        alumno_duplicado = Alumno(
            nombre='Otro',
            apellidos='Alumno',
            email=self.alumno.email,
            fecha_nacimiento=date(2004, 1, 1),
        )
        asignatura_duplicada = Asignatura(
            nombre='Otra asignatura',
            codigo=self.asignatura.codigo,
            curso='2º',
            creditos=5,
        )

        with self.assertRaises(ValidationError):
            alumno_duplicado.full_clean()
        with self.assertRaises(ValidationError):
            asignatura_duplicada.full_clean()

    def test_restricciones_unicas_se_aplican_en_la_base_de_datos(self):
        casos = (
            lambda: Alumno.objects.create(
                nombre='Duplicada',
                apellidos='Correo',
                email=self.alumno.email,
                fecha_nacimiento=date(2004, 1, 1),
            ),
            lambda: Asignatura.objects.create(
                nombre='Duplicada',
                codigo=self.asignatura.codigo,
                curso='2º',
                creditos=5,
            ),
            lambda: Matricula.objects.create(
                alumno=self.alumno,
                asignatura=self.asignatura,
                anio_academico='2026-2027',
            ),
        )

        for crear_registro in casos:
            with self.subTest(crear_registro=crear_registro):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        crear_registro()

    def test_no_se_repite_matricula_del_mismo_alumno_y_asignatura_en_el_anio(self):
        matricula_duplicada = Matricula(
            alumno=self.alumno,
            asignatura=self.asignatura,
            anio_academico='2026-2027',
        )

        with self.assertRaises(ValidationError):
            matricula_duplicada.full_clean()

    def test_nota_acepta_los_limites_y_rechaza_valores_fuera_de_rango(self):
        for valor_valido in (Decimal('0'), Decimal('10')):
            nota = Nota(
                matricula=self.matricula,
                evaluacion=Nota.TipoEvaluacion.FINAL,
                valor=valor_valido,
                fecha=date(2027, 6, 20),
            )
            nota.full_clean()

        for valor_invalido in (Decimal('-0.01'), Decimal('10.01')):
            nota = Nota(
                matricula=self.matricula,
                evaluacion=Nota.TipoEvaluacion.FINAL,
                valor=valor_invalido,
                fecha=date(2027, 6, 20),
            )
            with self.assertRaises(ValidationError):
                nota.full_clean()

    def test_nota_rechaza_evaluacion_no_contemplada(self):
        nota = Nota(
            matricula=self.matricula,
            evaluacion='extra',
            valor=Decimal('7.00'),
            fecha=date(2027, 6, 20),
        )

        with self.assertRaises(ValidationError):
            nota.full_clean()

    def test_orden_predeterminado_de_alumnos(self):
        Alumno.objects.create(
            nombre='Beatriz',
            apellidos='Alvarez',
            email='beatriz@example.com',
            fecha_nacimiento=date(2006, 2, 3),
        )

        self.assertEqual(
            list(Alumno.objects.values_list('apellidos', flat=True)),
            ['Alvarez', 'García López'],
        )


class AccesoYRegistroTests(TestCase):
    """Comprueba el login, logout y alta segura de cuentas de alumno."""

    def test_raiz_redirige_al_inicio_y_sin_sesion_termina_en_login(self):
        respuesta = self.client.get('/', follow=True)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.request['PATH_INFO'], '/accounts/login/')

    def test_prefijos_principales_cargan_sin_404(self):
        for ruta in ('/academico/', '/reportes/', '/accounts/'):
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(ruta, follow=True)
                self.assertEqual(respuesta.status_code, 200)

    def test_urls_de_login_y_redireccion_configuradas_existen(self):
        self.assertEqual(reverse(settings.LOGIN_URL), '/accounts/login/')
        self.assertEqual(reverse(settings.LOGIN_REDIRECT_URL), '/academico/')

    def test_base_carga_estilos_y_muestra_navegacion_publica(self):
        respuesta = self.client.get('/accounts/login/')

        self.assertContains(respuesta, '/static/css/styles.css')
        self.assertContains(respuesta, 'Iniciar sesión')
        self.assertContains(respuesta, 'Crear cuenta')
        self.assertNotContains(respuesta, 'Cerrar sesión')

    def test_navegacion_identifica_el_rol_de_alumno(self):
        usuario = get_user_model().objects.create_user(
            username='alumna',
            password='R0busta!Clave_2026',
        )
        usuario.groups.add(Group.objects.get(name='Alumno'))
        self.client.force_login(usuario)

        respuesta = self.client.get('/academico/', follow=True)

        self.assertEqual(
            respuesta.request['PATH_INFO'],
            reverse('academico:panel_alumno'),
        )
        self.assertContains(respuesta, 'role-alumno">Alumno</span>')
        self.assertNotContains(respuesta, 'role-profesor">Profesor</span>')
        self.assertContains(respuesta, 'Cerrar sesión')
        self.assertNotContains(respuesta, '>Alumnos</a>')
        self.assertNotContains(respuesta, '>Importar notas</a>')

    def test_navegacion_identifica_profesor_y_limita_admin_a_staff(self):
        usuario = get_user_model().objects.create_user(
            username='profesor',
            password='R0busta!Clave_2026',
        )
        usuario.groups.add(Group.objects.get(name='Profesor'))
        self.client.force_login(usuario)

        respuesta = self.client.get('/academico/', follow=True)

        self.assertEqual(
            respuesta.request['PATH_INFO'],
            reverse('academico:panel_profesor'),
        )
        self.assertContains(respuesta, 'role-profesor">Profesor</span>')
        self.assertEqual(respuesta.content.count(b'>Alumnos</a>'), 1)
        self.assertEqual(respuesta.content.count(b'>Asignaturas</a>'), 1)
        self.assertEqual(respuesta.content.count(b'>Matr\xc3\xadculas</a>'), 1)
        self.assertEqual(respuesta.content.count(b'>Importar notas</a>'), 1)
        self.assertNotContains(respuesta, 'Administración')

        usuario.groups.add(Group.objects.get(name='Alumno'))
        respuesta_varios_grupos = self.client.get('/academico/', follow=True)
        self.assertEqual(
            respuesta_varios_grupos.content.count(b'role-profesor'),
            1,
        )
        self.assertNotContains(respuesta_varios_grupos, 'role-alumno')
        self.assertEqual(
            respuesta_varios_grupos.content.count(b'>Alumnos</a>'),
            1,
        )

        usuario.is_staff = True
        usuario.save(update_fields=['is_staff'])
        respuesta_staff = self.client.get('/academico/', follow=True)
        self.assertContains(respuesta_staff, 'Administración')

    def test_superusuario_sin_grupo_ve_menu_y_accede_a_gestion(self):
        usuario = get_user_model().objects.create_superuser(
            username='administrador',
            email='admin@example.com',
            password='R0busta!Clave_2026',
        )
        self.client.force_login(usuario)

        respuesta_menu = self.client.get('/academico/', follow=True)
        self.assertContains(respuesta_menu, 'Superusuario')
        self.assertContains(respuesta_menu, '>Alumnos</a>')
        self.assertContains(respuesta_menu, '>Importar notas</a>')
        self.assertEqual(self.client.get('/academico/alumnos/').status_code, 200)
        self.assertEqual(
            self.client.get('/reportes/notas/importar/').status_code,
            200,
        )

    def test_usuario_sin_grupo_no_ve_menu_ni_accede_a_gestion(self):
        usuario = get_user_model().objects.create_user(
            username='sin_grupo',
            password='R0busta!Clave_2026',
        )
        self.client.force_login(usuario)

        respuesta_menu = self.client.get('/academico/')
        self.assertContains(respuesta_menu, 'class="role-badge">Usuario</span>')
        self.assertNotContains(respuesta_menu, '>Alumnos</a>')
        self.assertNotContains(respuesta_menu, '>Importar notas</a>')
        self.assertEqual(self.client.get('/academico/alumnos/').status_code, 403)
        self.assertEqual(
            self.client.get('/reportes/notas/importar/').status_code,
            403,
        )

    def test_alumno_no_accede_a_vistas_de_gestion(self):
        usuario = get_user_model().objects.create_user(
            username='alumna_sin_gestion',
            password='R0busta!Clave_2026',
        )
        usuario.groups.add(Group.objects.get(name='Alumno'))
        self.client.force_login(usuario)

        self.assertEqual(self.client.get('/academico/alumnos/').status_code, 403)
        self.assertEqual(
            self.client.get('/reportes/notas/importar/').status_code,
            403,
        )

    def test_panel_alumno_muestra_solo_sus_matriculas_y_notas(self):
        usuario = get_user_model().objects.create_user(
            username='panel_alumna',
            password='R0busta!Clave_2026',
        )
        usuario.groups.add(Group.objects.get(name='Alumno'))
        alumno = Alumno.objects.create(
            nombre='Ana',
            apellidos='García',
            email='panel_ana@example.com',
            fecha_nacimiento=date(2005, 4, 12),
            usuario=usuario,
        )
        asignatura = Asignatura.objects.create(
            nombre='Matemáticas privadas',
            codigo='MAT-PANEL-A',
            curso='1º',
            creditos=6,
        )
        matricula = Matricula.objects.create(
            alumno=alumno,
            asignatura=asignatura,
            anio_academico='2025-2026',
        )
        Nota.objects.create(
            matricula=matricula,
            evaluacion=Nota.TipoEvaluacion.PRIMERA,
            valor=Decimal('6.00'),
            fecha=date(2025, 12, 1),
        )
        Nota.objects.create(
            matricula=matricula,
            evaluacion=Nota.TipoEvaluacion.FINAL,
            valor=Decimal('10.00'),
            fecha=date(2026, 6, 1),
        )

        otro_usuario = get_user_model().objects.create_user(
            username='otra_panel_alumna',
            password='R0busta!Clave_2026',
        )
        otro_usuario.groups.add(Group.objects.get(name='Alumno'))
        otro_alumno = Alumno.objects.create(
            nombre='Beatriz',
            apellidos='López',
            email='panel_beatriz@example.com',
            fecha_nacimiento=date(2006, 2, 3),
            usuario=otro_usuario,
        )
        otra_asignatura = Asignatura.objects.create(
            nombre='Asignatura ajena',
            codigo='MAT-PANEL-B',
            curso='2º',
            creditos=5,
        )
        otra_matricula = Matricula.objects.create(
            alumno=otro_alumno,
            asignatura=otra_asignatura,
            anio_academico='2025-2026',
        )
        Nota.objects.create(
            matricula=otra_matricula,
            evaluacion=Nota.TipoEvaluacion.FINAL,
            valor=Decimal('2.00'),
            fecha=date(2026, 6, 1),
        )

        self.client.force_login(usuario)
        respuesta = self.client.get(
            reverse('academico:panel_alumno'),
            {'alumno': otro_alumno.pk},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Matemáticas privadas')
        self.assertContains(respuesta, '6,00')
        self.assertContains(respuesta, '10,00')
        self.assertContains(respuesta, '8,00')
        self.assertNotContains(respuesta, 'Asignatura ajena')
        self.assertNotContains(respuesta, '2.00')
        matriculas = list(respuesta.context['matriculas'])
        self.assertEqual([item.pk for item in matriculas], [matricula.pk])
        self.assertEqual(matriculas[0].media, Decimal('8'))

    def test_panel_alumno_sin_perfil_no_expone_datos_y_exige_grupo(self):
        usuario = get_user_model().objects.create_user(
            username='alumna_sin_perfil',
            password='R0busta!Clave_2026',
        )
        usuario.groups.add(Group.objects.get(name='Alumno'))
        self.client.force_login(usuario)

        respuesta = self.client.get(reverse('academico:panel_alumno'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'No hay asignaturas asociadas')
        self.assertEqual(list(respuesta.context['matriculas']), [])

        profesor = get_user_model().objects.create_user(
            username='profesor_panel',
            password='R0busta!Clave_2026',
        )
        profesor.groups.add(Group.objects.get(name='Profesor'))
        self.client.force_login(profesor)
        respuesta_profesor = self.client.get(
            reverse('academico:panel_alumno')
        )
        self.assertEqual(respuesta_profesor.status_code, 403)

    def test_panel_profesor_muestra_accesos_rapidos_y_requiere_permiso(self):
        profesor = get_user_model().objects.create_user(
            username='profesor_inicio',
            password='R0busta!Clave_2026',
        )
        profesor.groups.add(Group.objects.get(name='Profesor'))
        self.client.force_login(profesor)

        respuesta = self.client.get(reverse('academico:panel_profesor'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Gestionar alumnos')
        self.assertContains(respuesta, 'Gestionar asignaturas')
        self.assertContains(respuesta, 'Gestionar matrículas')
        self.assertContains(respuesta, 'Registrar una nota')
        self.assertContains(respuesta, 'Importar notas CSV')

        usuario = get_user_model().objects.create_user(
            username='usuario_sin_panel',
            password='R0busta!Clave_2026',
        )
        self.client.force_login(usuario)
        respuesta_no_autorizada = self.client.get(
            reverse('academico:panel_profesor')
        )
        self.assertEqual(respuesta_no_autorizada.status_code, 403)

    def test_inicio_redirige_al_panel_segun_el_rol_y_prioriza_profesor(self):
        casos = (
            ('login_alumna', 'Alumno', 'panel_alumno'),
            ('login_profesor', 'Profesor', 'panel_profesor'),
        )
        for username, grupo, panel in casos:
            with self.subTest(grupo=grupo):
                usuario = get_user_model().objects.create_user(
                    username=username,
                    password='R0busta!Clave_2026',
                )
                usuario.groups.add(Group.objects.get(name=grupo))
                if grupo == 'Profesor':
                    usuario.groups.add(Group.objects.get(name='Alumno'))

                respuesta = self.client.post(
                    reverse('login'),
                    {
                        'username': username,
                        'password': 'R0busta!Clave_2026',
                    },
                    follow=True,
                )

                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(
                    respuesta.request['PATH_INFO'],
                    reverse(f'academico:{panel}'),
                )
                self.client.logout()

    def test_login_y_registro_renderizan_plantillas_con_enlace_de_alta(self):
        respuesta_login = self.client.get('/accounts/login/')
        respuesta_registro = self.client.get('/academico/registro/')

        self.assertTemplateUsed(respuesta_login, 'registration/login.html')
        self.assertContains(respuesta_login, 'Crear cuenta')
        self.assertContains(respuesta_login, 'csrfmiddlewaretoken')
        self.assertTemplateUsed(respuesta_registro, 'academico/registro.html')
        self.assertTemplateUsed(respuesta_registro, 'base.html')

    def test_formulario_pide_email_y_no_expone_campos_de_grupo(self):
        formulario = RegistroAlumnoForm()

        self.assertTrue(formulario.fields['email'].required)
        self.assertNotIn('groups', formulario.fields)

    def test_migracion_crea_grupos_alumno_y_profesor(self):
        self.assertTrue(Group.objects.filter(name='Alumno').exists())
        self.assertTrue(Group.objects.filter(name='Profesor').exists())

    def test_registro_crea_usuario_en_grupo_alumno_y_muestra_confirmacion(self):
        grupo_profesor = Group.objects.get(name='Profesor')

        respuesta = self.client.post(
            '/academico/registro/',
            {
                'username': 'alumna',
                'email': 'alumna@example.com',
                'password1': 'R0busta!Clave_2026',
                'password2': 'R0busta!Clave_2026',
                'groups': str(grupo_profesor.pk),
            },
            follow=True,
        )

        usuario = get_user_model().objects.get(username='alumna')
        self.assertRedirects(respuesta, '/accounts/login/')
        self.assertContains(respuesta, 'Tu cuenta se ha creado correctamente')
        self.assertQuerySetEqual(
            usuario.groups.order_by('name'),
            ['Alumno'],
            transform=lambda grupo: grupo.name,
        )
        self.assertFalse(usuario.groups.filter(name='Profesor').exists())

    def test_registro_enlaza_alumno_existente_con_el_mismo_email(self):
        alumno = Alumno.objects.create(
            nombre='Ana',
            apellidos='García',
            email='alumna@example.com',
            fecha_nacimiento=date(2005, 4, 12),
        )

        respuesta = self.client.post(
            '/academico/registro/',
            {
                'username': 'alumna',
                'email': 'ALUMNA@example.com',
                'password1': 'R0busta!Clave_2026',
                'password2': 'R0busta!Clave_2026',
            },
        )

        self.assertRedirects(respuesta, '/accounts/login/')
        alumno.refresh_from_db()
        self.assertEqual(alumno.usuario.username, 'alumna')

    def test_registro_no_reemplaza_usuario_ya_enlazado_al_alumno(self):
        usuario_original = get_user_model().objects.create_user(
            username='original',
            email='original@example.com',
            password='R0busta!Clave_2026',
        )
        alumno = Alumno.objects.create(
            nombre='Ana',
            apellidos='García',
            email='alumna@example.com',
            fecha_nacimiento=date(2005, 4, 12),
            usuario=usuario_original,
        )

        respuesta = self.client.post(
            '/academico/registro/',
            {
                'username': 'alumna_nueva',
                'email': 'alumna@example.com',
                'password1': 'R0busta!Clave_2026',
                'password2': 'R0busta!Clave_2026',
            },
        )

        self.assertRedirects(respuesta, '/accounts/login/')
        alumno.refresh_from_db()
        self.assertEqual(alumno.usuario, usuario_original)

    def test_mixin_permite_profesor_y_superusuario(self):
        usuario = get_user_model().objects.create_user(
            username='docente',
            password='R0busta!Clave_2026',
        )
        request = RequestFactory().get('/')
        request.user = usuario
        mixin = ProfesorRequiredMixin()
        mixin.request = request

        self.assertFalse(mixin.test_func())
        usuario.groups.add(Group.objects.get(name='Profesor'))
        self.assertTrue(mixin.test_func())
        usuario.groups.clear()
        usuario.is_superuser = True
        self.assertTrue(mixin.test_func())

    def test_registro_rechaza_correo_ya_utilizado_sin_distinguir_mayusculas(self):
        get_user_model().objects.create_user(
            username='existente',
            email='persona@example.com',
            password='R0busta!Clave_2026',
        )

        respuesta = self.client.post(
            '/academico/registro/',
            {
                'username': 'nueva',
                'email': 'PERSONA@example.com',
                'password1': 'R0busta!Clave_2026',
                'password2': 'R0busta!Clave_2026',
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta,
            'Ya existe una cuenta con este correo electrónico.',
        )
        self.assertFalse(
            get_user_model().objects.filter(username='nueva').exists()
        )

    def test_login_y_logout_usan_las_redirecciones_configuradas(self):
        usuario = get_user_model().objects.create_user(
            username='alumna',
            email='alumna@example.com',
            password='R0busta!Clave_2026',
        )

        respuesta_login = self.client.post(
            '/accounts/login/',
            {'username': usuario.username, 'password': 'R0busta!Clave_2026'},
        )

        self.assertRedirects(respuesta_login, '/academico/')
        respuesta_logout = self.client.post('/accounts/logout/')
        self.assertRedirects(respuesta_logout, '/accounts/login/')


class CRUDAlumnoTests(TestCase):
    """Comprueba permisos y operaciones del CRUD de alumnos."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo_profesor = Group.objects.get(name='Profesor')
        cls.grupo_alumno = Group.objects.get(name='Alumno')

    def setUp(self):
        self.profesor = get_user_model().objects.create_user(
            username='profesor_crud',
            password='R0busta!Clave_2026',
        )
        self.profesor.groups.add(self.grupo_profesor)
        self.alumno_usuario = get_user_model().objects.create_user(
            username='alumno_crud',
            password='R0busta!Clave_2026',
        )
        self.alumno_usuario.groups.add(self.grupo_alumno)
        self.alumno = Alumno.objects.create(
            nombre='Ana',
            apellidos='García',
            email='ana@example.com',
            fecha_nacimiento=date(2005, 4, 12),
        )
        self.client.force_login(self.profesor)

    def datos_alumno(self, **cambios):
        datos = {
            'nombre': 'Luis',
            'apellidos': 'Pérez',
            'email': 'luis@example.com',
            'fecha_nacimiento': '2004-03-15',
            'activo': 'on',
        }
        datos.update(cambios)
        return datos

    def test_usuario_anonimo_es_enviado_al_login(self):
        self.client.logout()

        respuesta = self.client.get(reverse('academico:alumno_lista'))

        self.assertRedirects(
            respuesta,
            f'{reverse("login")}?next={reverse("academico:alumno_lista")}',
        )

    def test_usuario_que_no_es_profesor_recibe_403(self):
        self.client.force_login(self.alumno_usuario)

        for nombre_url, argumentos in (
            ('academico:alumno_lista', ()),
            ('academico:alumno_crear', ()),
            ('academico:alumno_editar', (self.alumno.pk,)),
            ('academico:alumno_eliminar', (self.alumno.pk,)),
        ):
            with self.subTest(vista=nombre_url):
                respuesta = self.client.get(reverse(nombre_url, args=argumentos))
                self.assertEqual(respuesta.status_code, 403)

    def test_lista_busca_por_nombre_apellidos_o_email(self):
        for consulta in ('Ana', 'García', 'ana@example.com'):
            with self.subTest(consulta=consulta):
                respuesta = self.client.get(
                    reverse('academico:alumno_lista'),
                    {'q': consulta},
                )

                self.assertContains(respuesta, 'ana@example.com')
                self.assertEqual(
                    list(respuesta.context['alumnos']),
                    [self.alumno],
                )

    def test_lista_pagina_de_diez_elementos_y_conserva_busqueda(self):
        for indice in range(11):
            Alumno.objects.create(
                nombre=f'Nombre{indice}',
                apellidos=f'Apellido{indice}',
                email=f'persona{indice}@example.com',
                fecha_nacimiento=date(2000, 1, 1),
            )

        respuesta = self.client.get(
            reverse('academico:alumno_lista'),
            {'q': 'example.com'},
        )

        self.assertEqual(len(respuesta.context['alumnos']), 10)
        self.assertTrue(respuesta.context['is_paginated'])
        self.assertContains(respuesta, 'q=example.com')
        self.assertContains(respuesta, 'page=2')

    def test_crear_y_editar_alumno_sin_cambiar_usuario(self):
        respuesta_crear = self.client.post(
            reverse('academico:alumno_crear'),
            self.datos_alumno(usuario=self.alumno_usuario.pk),
            follow=True,
        )

        nuevo_alumno = Alumno.objects.get(email='luis@example.com')
        self.assertContains(respuesta_crear, 'Alumno creado correctamente.')
        self.assertIsNone(nuevo_alumno.usuario)

        respuesta_editar = self.client.post(
            reverse('academico:alumno_editar', args=(self.alumno.pk,)),
            self.datos_alumno(
                nombre='Ana María',
                email='ana@example.com',
                usuario=self.alumno_usuario.pk,
            ),
            follow=True,
        )

        self.assertContains(
            respuesta_editar,
            'Alumno actualizado correctamente.',
        )
        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.nombre, 'Ana María')
        self.assertIsNone(self.alumno.usuario)

    def test_borrado_get_solo_confirma_y_post_elimina_matriculas_y_notas(self):
        asignatura = Asignatura.objects.create(
            nombre='Matemáticas',
            codigo='MAT-CRUD',
            curso='1º',
            creditos=6,
        )
        matricula = Matricula.objects.create(
            alumno=self.alumno,
            asignatura=asignatura,
            anio_academico='2025-2026',
        )
        nota = Nota.objects.create(
            matricula=matricula,
            evaluacion=Nota.TipoEvaluacion.FINAL,
            valor=Decimal('8.50'),
            fecha=date(2026, 6, 1),
        )

        respuesta_confirmacion = self.client.get(
            reverse('academico:alumno_eliminar', args=(self.alumno.pk,))
        )
        self.assertContains(respuesta_confirmacion, 'notas asociadas')
        self.assertTrue(Alumno.objects.filter(pk=self.alumno.pk).exists())

        respuesta_borrado = self.client.post(
            reverse('academico:alumno_eliminar', args=(self.alumno.pk,)),
            follow=True,
        )

        self.assertContains(respuesta_borrado, 'Alumno eliminado correctamente.')
        self.assertFalse(Alumno.objects.filter(pk=self.alumno.pk).exists())
        self.assertFalse(Matricula.objects.filter(pk=matricula.pk).exists())
        self.assertFalse(Nota.objects.filter(pk=nota.pk).exists())


class CRUDAsignaturaTests(TestCase):
    """Comprueba permisos y operaciones del CRUD de asignaturas."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo_profesor = Group.objects.get(name='Profesor')
        cls.grupo_alumno = Group.objects.get(name='Alumno')

    def setUp(self):
        self.profesor = get_user_model().objects.create_user(
            username='profesor_asignaturas',
            password='R0busta!Clave_2026',
        )
        self.profesor.groups.add(self.grupo_profesor)
        self.alumno_usuario = get_user_model().objects.create_user(
            username='alumno_asignaturas',
            password='R0busta!Clave_2026',
        )
        self.alumno_usuario.groups.add(self.grupo_alumno)
        self.asignatura = Asignatura.objects.create(
            nombre='Matemáticas',
            codigo='MAT101',
            curso='1º',
            creditos=6,
        )
        self.client.force_login(self.profesor)

    def datos_asignatura(self, **cambios):
        datos = {
            'nombre': 'Historia',
            'codigo': 'HIS101',
            'curso': '1º',
            'creditos': 5,
        }
        datos.update(cambios)
        return datos

    def test_rutas_asignatura_tienen_nombres_coherentes(self):
        self.assertEqual(reverse('academico:asignatura_lista'), '/academico/asignaturas/')
        self.assertEqual(reverse('academico:asignatura_crear'), '/academico/asignaturas/nueva/')
        self.assertEqual(
            reverse('academico:asignatura_editar', args=(self.asignatura.pk,)),
            f'/academico/asignaturas/{self.asignatura.pk}/editar/',
        )
        self.assertEqual(
            reverse('academico:asignatura_eliminar', args=(self.asignatura.pk,)),
            f'/academico/asignaturas/{self.asignatura.pk}/eliminar/',
        )

    def test_usuario_anonimo_es_enviado_al_login(self):
        self.client.logout()

        respuesta = self.client.get(reverse('academico:asignatura_lista'))

        self.assertRedirects(
            respuesta,
            f'{reverse("login")}?next={reverse("academico:asignatura_lista")}',
        )

    def test_usuario_que_no_es_profesor_recibe_403_en_todas_las_vistas(self):
        self.client.force_login(self.alumno_usuario)

        for nombre_url, argumentos in (
            ('academico:asignatura_lista', ()),
            ('academico:asignatura_crear', ()),
            ('academico:asignatura_editar', (self.asignatura.pk,)),
            ('academico:asignatura_eliminar', (self.asignatura.pk,)),
        ):
            with self.subTest(vista=nombre_url):
                respuesta = self.client.get(reverse(nombre_url, args=argumentos))
                self.assertEqual(respuesta.status_code, 403)

    def test_lista_busca_por_nombre_o_codigo(self):
        for consulta in ('Matemáticas', 'MAT101'):
            with self.subTest(consulta=consulta):
                respuesta = self.client.get(
                    reverse('academico:asignatura_lista'),
                    {'q': consulta},
                )

                self.assertContains(respuesta, 'MAT101')
                self.assertEqual(
                    list(respuesta.context['asignaturas']),
                    [self.asignatura],
                )

    def test_lista_pagina_de_diez_elementos_y_conserva_busqueda(self):
        for indice in range(11):
            Asignatura.objects.create(
                nombre=f'Asignatura {indice}',
                codigo=f'COD{indice:03}',
                curso='2º',
                creditos=4,
            )

        respuesta = self.client.get(
            reverse('academico:asignatura_lista'),
            {'q': 'COD'},
        )

        self.assertEqual(len(respuesta.context['asignaturas']), 10)
        self.assertTrue(respuesta.context['is_paginated'])
        self.assertContains(respuesta, 'q=COD')
        self.assertContains(respuesta, 'page=2')

    def test_alta_edicion_y_borrado_muestran_mensajes_de_exito(self):
        respuesta_alta = self.client.post(
            reverse('academico:asignatura_crear'),
            self.datos_asignatura(),
            follow=True,
        )
        asignatura = Asignatura.objects.get(codigo='HIS101')
        self.assertContains(respuesta_alta, 'Asignatura creada correctamente.')

        respuesta_edicion = self.client.post(
            reverse('academico:asignatura_editar', args=(asignatura.pk,)),
            self.datos_asignatura(nombre='Historia moderna'),
            follow=True,
        )
        self.assertContains(
            respuesta_edicion,
            'Asignatura actualizada correctamente.',
        )

        respuesta_confirmacion = self.client.get(
            reverse('academico:asignatura_eliminar', args=(asignatura.pk,))
        )
        self.assertContains(respuesta_confirmacion, 'notas asociadas')
        self.assertTrue(Asignatura.objects.filter(pk=asignatura.pk).exists())

        respuesta_borrado = self.client.post(
            reverse('academico:asignatura_eliminar', args=(asignatura.pk,)),
            follow=True,
        )
        self.assertContains(respuesta_borrado, 'Asignatura eliminada correctamente.')
        self.assertFalse(Asignatura.objects.filter(pk=asignatura.pk).exists())

    def test_borrar_asignatura_elimina_matriculas_y_notas_asociadas(self):
        matricula = Matricula.objects.create(
            alumno=Alumno.objects.create(
                nombre='Ana',
                apellidos='García',
                email='ana-asignatura@example.com',
                fecha_nacimiento=date(2005, 4, 12),
            ),
            asignatura=self.asignatura,
            anio_academico='2025-2026',
        )
        nota = Nota.objects.create(
            matricula=matricula,
            evaluacion=Nota.TipoEvaluacion.FINAL,
            valor=Decimal('8.50'),
            fecha=date(2026, 6, 1),
        )

        self.client.post(
            reverse('academico:asignatura_eliminar', args=(self.asignatura.pk,))
        )

        self.assertFalse(Matricula.objects.filter(pk=matricula.pk).exists())
        self.assertFalse(Nota.objects.filter(pk=nota.pk).exists())

    def test_navbar_de_profesor_enlaza_alumnos_y_asignaturas(self):
        respuesta = self.client.get(reverse('academico:inicio'), follow=True)

        self.assertContains(
            respuesta,
            reverse('academico:alumno_lista'),
        )
        self.assertContains(
            respuesta,
            reverse('academico:asignatura_lista'),
        )


class MatriculasYNotasTests(TestCase):
    """Comprueba el CRUD de matrículas y la validación del formulario de notas."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo_profesor = Group.objects.get(name='Profesor')
        cls.grupo_alumno = Group.objects.get(name='Alumno')

    def setUp(self):
        self.profesor = get_user_model().objects.create_user(
            username='profesor_matriculas',
            password='R0busta!Clave_2026',
        )
        self.profesor.groups.add(self.grupo_profesor)
        self.alumno_usuario = get_user_model().objects.create_user(
            username='alumno_matriculas',
            password='R0busta!Clave_2026',
        )
        self.alumno_usuario.groups.add(self.grupo_alumno)
        self.alumno = Alumno.objects.create(
            nombre='Ana',
            apellidos='García',
            email='ana-matricula@example.com',
            fecha_nacimiento=date(2005, 4, 12),
        )
        self.asignatura = Asignatura.objects.create(
            nombre='Matemáticas',
            codigo='MAT-MATR',
            curso='1º',
            creditos=6,
        )
        self.matricula = Matricula.objects.create(
            alumno=self.alumno,
            asignatura=self.asignatura,
            anio_academico='2025-2026',
        )
        self.client.force_login(self.profesor)

    def datos_matricula(self, **cambios):
        datos = {
            'alumno': self.alumno.pk,
            'asignatura': self.asignatura.pk,
            'anio_academico': '2026-2027',
        }
        datos.update(cambios)
        return datos

    def datos_nota(self, **cambios):
        datos = {
            'matricula': self.matricula.pk,
            'evaluacion': Nota.TipoEvaluacion.PRIMERA,
            'valor': '8.50',
            'fecha': '2026-10-10',
        }
        datos.update(cambios)
        return datos

    def test_usuario_anonimo_es_enviado_al_login_y_alumno_recibe_403(self):
        self.client.logout()
        respuesta_anonima = self.client.get(
            reverse('academico:matricula_lista')
        )
        self.assertRedirects(
            respuesta_anonima,
            f'{reverse("login")}?next={reverse("academico:matricula_lista")}',
        )

        self.client.force_login(self.alumno_usuario)
        for nombre_url, argumentos in (
            ('academico:matricula_lista', ()),
            ('academico:matricula_crear', ()),
            ('academico:matricula_editar', (self.matricula.pk,)),
            ('academico:matricula_eliminar', (self.matricula.pk,)),
            ('academico:nota_crear', ()),
        ):
            with self.subTest(vista=nombre_url):
                respuesta = self.client.get(reverse(nombre_url, args=argumentos))
                self.assertEqual(respuesta.status_code, 403)

    def test_crud_matricula_y_mensajes_de_exito(self):
        respuesta_alta = self.client.post(
            reverse('academico:matricula_crear'),
            self.datos_matricula(),
            follow=True,
        )
        matricula = Matricula.objects.get(anio_academico='2026-2027')
        self.assertContains(respuesta_alta, 'Matrícula creada correctamente.')

        respuesta_edicion = self.client.post(
            reverse('academico:matricula_editar', args=(matricula.pk,)),
            self.datos_matricula(anio_academico='2027-2028'),
            follow=True,
        )
        self.assertContains(
            respuesta_edicion,
            'Matrícula actualizada correctamente.',
        )
        matricula.refresh_from_db()
        self.assertEqual(matricula.anio_academico, '2027-2028')

        respuesta_confirmacion = self.client.get(
            reverse('academico:matricula_eliminar', args=(matricula.pk,))
        )
        self.assertContains(respuesta_confirmacion, 'notas asociadas')
        self.assertTrue(Matricula.objects.filter(pk=matricula.pk).exists())

        respuesta_borrado = self.client.post(
            reverse('academico:matricula_eliminar', args=(matricula.pk,)),
            follow=True,
        )
        self.assertContains(
            respuesta_borrado,
            'Matrícula eliminada correctamente.',
        )
        self.assertFalse(Matricula.objects.filter(pk=matricula.pk).exists())

    def test_formulario_matricula_rechaza_combinacion_duplicada(self):
        respuesta = self.client.post(
            reverse('academico:matricula_crear'),
            self.datos_matricula(anio_academico='2025-2026'),
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context['form'].non_field_errors())
        self.assertEqual(
            Matricula.objects.filter(
                alumno=self.alumno,
                asignatura=self.asignatura,
                anio_academico='2025-2026',
            ).count(),
            1,
        )

    def test_nota_form_valida_rango_y_evitar_evaluacion_duplicada(self):
        for valor_invalido in ('-0.01', '10.01'):
            with self.subTest(valor=valor_invalido):
                nota_form = NotaForm(
                    data=self.datos_nota(valor=valor_invalido)
                )
                self.assertFalse(nota_form.is_valid())
                self.assertIn('valor', nota_form.errors)

        primera_nota = Nota.objects.create(
            matricula=self.matricula,
            evaluacion=Nota.TipoEvaluacion.PRIMERA,
            valor=Decimal('7.00'),
            fecha=date(2026, 10, 10),
        )
        formulario_duplicado = NotaForm(data=self.datos_nota())
        self.assertFalse(formulario_duplicado.is_valid())
        self.assertIn('evaluacion', formulario_duplicado.errors)
        self.assertEqual(primera_nota.matricula, self.matricula)

        formulario_valido = NotaForm(
            data=self.datos_nota(
                evaluacion=Nota.TipoEvaluacion.SEGUNDA,
                valor='0',
            )
        )
        self.assertTrue(formulario_valido.is_valid(), formulario_valido.errors)

    def test_vista_registra_nota_y_rechaza_evaluacion_repetida(self):
        url = reverse('academico:nota_crear')
        respuesta = self.client.post(
            url,
            self.datos_nota(),
            follow=True,
        )
        self.assertContains(respuesta, 'Nota registrada correctamente.')
        self.assertEqual(self.matricula.notas.count(), 1)

        duplicada = self.client.post(url, self.datos_nota())
        self.assertEqual(duplicada.status_code, 200)
        self.assertContains(
            duplicada,
            'Ya existe una nota para esta evaluación y matrícula.',
        )
