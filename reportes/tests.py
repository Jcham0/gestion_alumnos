from datetime import date
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook
import pandas as pd

from academico.models import Alumno, Asignatura, Matricula, Nota

from .services import (
    calcular_media_por_asignatura,
    calcular_porcentaje_aprobados,
    detectar_valores_atipicos_iqr,
    importar_notas_csv,
    obtener_dataframe_boletin,
    obtener_dataframe_notas,
    obtener_ranking_alumnos,
)


class ImportacionNotasTests(TestCase):
    """Comprueba la importación CSV y los rechazos con su motivo."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo_profesor = Group.objects.get(name='Profesor')
        cls.grupo_alumno = Group.objects.get(name='Alumno')
        cls.alumno = Alumno.objects.create(
            nombre='Ana',
            apellidos='García',
            email='ana-importacion@example.com',
            fecha_nacimiento=date(2005, 4, 12),
        )
        cls.asignatura = Asignatura.objects.create(
            nombre='Matemáticas',
            codigo='MAT-IMPORT',
            curso='1º',
            creditos=6,
        )
        cls.matricula = Matricula.objects.create(
            alumno=cls.alumno,
            asignatura=cls.asignatura,
            anio_academico='2025-2026',
        )

    def crear_csv(self, contenido):
        return StringIO(contenido)

    @patch('reportes.services.timezone.localdate', return_value=date(2026, 11, 12))
    def test_importa_validas_limpia_espacios_y_rechaza_filas_invalidas(self, fecha_local):
        csv = self.crear_csv(
            'email_alumno,codigo_asignatura,evaluacion,valor\n'
            ' ana-importacion@example.com , MAT-IMPORT , 1ª , 8.5 \n'
            'ana-importacion@example.com,MAT-IMPORT,1ª,8.5\n'
            ',MAT-IMPORT,2ª,7\n'
            'ana-importacion@example.com,MAT-IMPORT,2ª,10.1\n'
            'desconocido@example.com,MAT-IMPORT,final,8\n'
            'ana-importacion@example.com,MAT-IMPORT,final,no-numero\n'
            'ana-importacion@example.com,MAT-IMPORT,final,9\n'
            'ana-importacion@example.com,MAT-IMPORT,final,8\n'
        )

        resumen = importar_notas_csv(csv)

        self.assertEqual(resumen.importadas, 2)
        self.assertEqual(resumen.total_rechazadas, 6)
        motivos = [rechazo.motivo for rechazo in resumen.rechazadas]
        self.assertTrue(any('duplicada en el CSV' in motivo for motivo in motivos))
        self.assertTrue(any('nulos o vacíos' in motivo for motivo in motivos))
        self.assertTrue(any('entre 0 y 10' in motivo for motivo in motivos))
        self.assertTrue(any('No existe un alumno' in motivo for motivo in motivos))
        self.assertTrue(any('número válido' in motivo for motivo in motivos))
        self.assertTrue(
            any('Ya existe una nota para esta evaluación' in motivo for motivo in motivos)
        )
        notas = self.matricula.notas.order_by('evaluacion')
        self.assertEqual(notas.count(), 2)
        self.assertEqual(notas.get(evaluacion='1ª').valor, Decimal('8.50'))
        self.assertEqual(notas.get(evaluacion='1ª').fecha, date(2026, 11, 12))
        fecha_local.assert_called()

    def test_rechaza_matriculas_ambiguas_por_ausencia_de_anio_en_csv(self):
        Matricula.objects.create(
            alumno=self.alumno,
            asignatura=self.asignatura,
            anio_academico='2026-2027',
        )
        resumen = importar_notas_csv(
            self.crear_csv(
                'email_alumno,codigo_asignatura,evaluacion,valor\n'
                'ana-importacion@example.com,MAT-IMPORT,1ª,8\n'
            )
        )

        self.assertEqual(resumen.importadas, 0)
        self.assertEqual(resumen.total_rechazadas, 1)
        self.assertIn('varias matrículas', resumen.rechazadas[0].motivo)

    def test_rechaza_columnas_ausentes_con_error_explicito(self):
        with self.assertRaisesMessage(ValueError, 'Faltan columnas requeridas'):
            importar_notas_csv(self.crear_csv('email_alumno,valor\n'))

    def test_rechaza_evaluacion_no_contemplada(self):
        resumen = importar_notas_csv(
            self.crear_csv(
                'email_alumno,codigo_asignatura,evaluacion,valor\n'
                'ana-importacion@example.com,MAT-IMPORT,extra,8\n'
            )
        )

        self.assertEqual(resumen.importadas, 0)
        self.assertIn('evaluación debe ser', resumen.rechazadas[0].motivo)

    def test_filas_rechazadas_indican_numero_de_linea_del_csv(self):
        resumen = importar_notas_csv(
            self.crear_csv(
                'email_alumno,codigo_asignatura,evaluacion,valor\n'
                ',MAT-IMPORT,1ª,8\n'
            )
        )

        self.assertEqual(resumen.rechazadas[0].fila, 2)


class ImportarNotasViewTests(TestCase):
    """Comprueba acceso de profesor a la carga y el resumen presentado."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo_profesor = Group.objects.get(name='Profesor')
        cls.grupo_alumno = Group.objects.get(name='Alumno')

    def setUp(self):
        self.profesor = get_user_model().objects.create_user(
            username='profesor_csv',
            password='R0busta!Clave_2026',
        )
        self.profesor.groups.add(self.grupo_profesor)
        self.alumno_usuario = get_user_model().objects.create_user(
            username='alumno_csv',
            password='R0busta!Clave_2026',
        )
        self.alumno_usuario.groups.add(self.grupo_alumno)
        self.client.force_login(self.profesor)

    def subir_csv(self, contenido, nombre='notas.csv'):
        archivo = SimpleUploadedFile(
            nombre,
            contenido.encode('utf-8'),
            content_type='text/csv',
        )
        return self.client.post(
            reverse('reportes:importar_notas'),
            {'archivo': archivo},
        )

    def test_solo_profesor_puede_abrir_el_formulario(self):
        url = reverse('reportes:importar_notas')
        self.client.logout()
        anonimo = self.client.get(url)
        self.assertRedirects(anonimo, f'{reverse("login")}?next={url}')

        self.client.force_login(self.alumno_usuario)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_carga_muestra_resumen_y_detalle(self):
        Alumno.objects.create(
            nombre='Ana',
            apellidos='García',
            email='ana-carga@example.com',
            fecha_nacimiento=date(2005, 4, 12),
        )
        alumno = Alumno.objects.get(email='ana-carga@example.com')
        asignatura = Asignatura.objects.create(
            nombre='Historia',
            codigo='HIS-CARGA',
            curso='1º',
            creditos=4,
        )
        Matricula.objects.create(
            alumno=alumno,
            asignatura=asignatura,
            anio_academico='2025-2026',
        )
        respuesta = self.subir_csv(
            'email_alumno,codigo_asignatura,evaluacion,valor\n'
            'ana-carga@example.com,HIS-CARGA,final,9\n'
            'desconocido@example.com,HIS-CARGA,1ª,8\n'
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, '1 notas importadas')
        self.assertContains(respuesta, '1 filas rechazadas')
        self.assertContains(respuesta, 'No existe un alumno')

    def test_formulario_rechaza_archivo_que_no_es_csv(self):
        respuesta = self.subir_csv(
            'email_alumno,codigo_asignatura,evaluacion,valor\n',
            nombre='notas.txt',
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'extensión .csv')

    def test_archivo_de_ejemplo_tiene_las_columnas_requeridas(self):
        ruta = Path(__file__).resolve().parent.parent / 'datos' / 'ejemplo_notas.csv'
        contenido = ruta.read_text(encoding='utf-8').splitlines()[0]

        self.assertEqual(
            contenido,
            'email_alumno,codigo_asignatura,evaluacion,valor',
        )


class AnalisisNotasTests(TestCase):
    """Comprueba la consulta de notas y los análisis estadísticos."""

    @classmethod
    def setUpTestData(cls):
        cls.alumna = Alumno.objects.create(
            nombre='Ana',
            apellidos='Alvarez',
            email='ana-estadisticas@example.com',
            fecha_nacimiento=date(2005, 4, 12),
        )
        cls.alumno = Alumno.objects.create(
            nombre='Berta',
            apellidos='Benítez',
            email='berta-estadisticas@example.com',
            fecha_nacimiento=date(2005, 5, 12),
        )
        cls.matematicas = Asignatura.objects.create(
            nombre='Matemáticas',
            codigo='MAT-EST',
            curso='1º',
            creditos=6,
        )
        cls.historia = Asignatura.objects.create(
            nombre='Historia',
            codigo='HIS-EST',
            curso='1º',
            creditos=4,
        )
        matricula_ana = Matricula.objects.create(
            alumno=cls.alumna,
            asignatura=cls.matematicas,
            anio_academico='2025-2026',
        )
        matricula_berta = Matricula.objects.create(
            alumno=cls.alumno,
            asignatura=cls.matematicas,
            anio_academico='2025-2026',
        )
        matricula_historia = Matricula.objects.create(
            alumno=cls.alumna,
            asignatura=cls.historia,
            anio_academico='2026-2027',
        )
        for matricula, evaluacion, valor, fecha in (
            (matricula_ana, Nota.TipoEvaluacion.PRIMERA, '5', date(2025, 10, 1)),
            (matricula_ana, Nota.TipoEvaluacion.SEGUNDA, '5', date(2026, 2, 1)),
            (matricula_berta, Nota.TipoEvaluacion.PRIMERA, '5', date(2025, 10, 1)),
            (matricula_berta, Nota.TipoEvaluacion.SEGUNDA, '10', date(2026, 2, 1)),
            (
                matricula_historia,
                Nota.TipoEvaluacion.FINAL,
                '0',
                date(2027, 6, 1),
            ),
        ):
            Nota.objects.create(
                matricula=matricula,
                evaluacion=evaluacion,
                valor=Decimal(valor),
                fecha=fecha,
            )

    def test_dataframe_contiene_columnas_requeridas_y_admite_filtros(self):
        dataframe = obtener_dataframe_notas(
            asignatura_id=self.matematicas.pk,
            anio='2025-2026',
        )

        self.assertEqual(
            list(dataframe.columns),
            ['alumno', 'asignatura', 'evaluacion', 'valor', 'anio'],
        )
        self.assertEqual(len(dataframe), 4)
        self.assertTrue(dataframe['asignatura'].str.startswith('MAT-EST').all())
        self.assertEqual(set(dataframe['anio']), {'2025-2026'})
        self.assertEqual(obtener_dataframe_notas().shape[0], 5)

    def test_estadisticas_de_asignaturas_y_ranking(self):
        dataframe = obtener_dataframe_notas(
            asignatura_id=self.matematicas.pk,
            anio='2025-2026',
        )

        medias = calcular_media_por_asignatura(dataframe)
        aprobados = calcular_porcentaje_aprobados(dataframe)
        ranking = obtener_ranking_alumnos(dataframe, cantidad=1)

        self.assertEqual(medias.iloc[0]['media'], 6.25)
        self.assertEqual(aprobados.iloc[0]['total'], 4)
        self.assertEqual(aprobados.iloc[0]['aprobados'], 4)
        self.assertEqual(aprobados.iloc[0]['porcentaje_aprobados'], 100)
        self.assertEqual(ranking.iloc[0]['alumno'], 'Benítez, Berta')
        self.assertEqual(ranking.iloc[0]['media'], 7.5)

    def test_iqr_detecta_valores_extremos_y_ranking_valida_cantidad(self):
        dataframe = obtener_dataframe_notas(
            asignatura_id=self.matematicas.pk,
            anio='2025-2026',
        )

        atipicos = detectar_valores_atipicos_iqr(dataframe)

        self.assertEqual(atipicos['valor'].tolist(), [10.0])
        self.assertEqual(
            list(atipicos.columns),
            ['alumno', 'asignatura', 'evaluacion', 'valor', 'anio'],
        )
        with self.assertRaisesMessage(ValueError, 'mayor que cero'):
            obtener_ranking_alumnos(dataframe, cantidad=0)

    def test_analisis_aceptan_dataframe_vacio(self):
        dataframe = obtener_dataframe_notas(
            asignatura_id=-1,
        )

        self.assertTrue(calcular_media_por_asignatura(dataframe).empty)
        self.assertTrue(calcular_porcentaje_aprobados(dataframe).empty)
        self.assertTrue(obtener_ranking_alumnos(dataframe).empty)
        self.assertTrue(detectar_valores_atipicos_iqr(dataframe).empty)

    def test_dataframe_boletin_contiene_notas_y_media_por_asignatura_y_anio(self):
        dataframe = obtener_dataframe_boletin(self.alumna.pk)

        self.assertEqual(
            list(dataframe.columns),
            [
                'alumno',
                'asignatura',
                'anio',
                'evaluacion',
                'valor',
                'fecha',
                'media_asignatura',
            ],
        )
        self.assertEqual(len(dataframe), 3)
        historia = dataframe[dataframe['asignatura'].str.startswith('HIS-EST')]
        self.assertEqual(historia.iloc[0]['media_asignatura'], 0)
        matematicas = dataframe[
            dataframe['asignatura'].str.startswith('MAT-EST')
        ]
        self.assertTrue((matematicas['media_asignatura'] == 5).all())


class AnalisisDataFrameUnitTests(TestCase):
    """Comprueba los análisis pandas con datos pequeños conocidos."""

    def setUp(self):
        self.dataframe = pd.DataFrame(
            [
                ('Ana, A', 'MAT - Matemáticas', '1ª', 1.0, '2025-2026'),
                ('Ana, A', 'MAT - Matemáticas', '2ª', 2.0, '2025-2026'),
                ('Berta, B', 'MAT - Matemáticas', '1ª', 2.0, '2025-2026'),
                ('Berta, B', 'MAT - Matemáticas', '2ª', 3.0, '2025-2026'),
                ('Carla, C', 'MAT - Matemáticas', '1ª', 4.0, '2025-2026'),
                ('Carla, C', 'MAT - Matemáticas', '2ª', 10.0, '2025-2026'),
                ('Ana, A', 'HIS - Historia', 'final', 8.0, '2025-2026'),
                ('Berta, B', 'HIS - Historia', 'final', 10.0, '2025-2026'),
            ],
            columns=['alumno', 'asignatura', 'evaluacion', 'valor', 'anio'],
        )

    def test_media_y_porcentaje_aprobados_por_asignatura(self):
        medias = calcular_media_por_asignatura(self.dataframe)
        aprobados = calcular_porcentaje_aprobados(self.dataframe)
        medias_por_asignatura = medias.set_index('asignatura')
        aprobados_por_asignatura = aprobados.set_index('asignatura')

        self.assertAlmostEqual(
            medias_por_asignatura.loc['MAT - Matemáticas', 'media'],
            22 / 6,
        )
        self.assertEqual(
            medias_por_asignatura.loc['HIS - Historia', 'media'],
            9,
        )
        self.assertEqual(
            aprobados_por_asignatura.loc['MAT - Matemáticas', 'total'],
            6,
        )
        self.assertEqual(
            aprobados_por_asignatura.loc['MAT - Matemáticas', 'aprobados'],
            1,
        )
        self.assertAlmostEqual(
            aprobados_por_asignatura.loc[
                'MAT - Matemáticas',
                'porcentaje_aprobados',
            ],
            100 / 6,
        )
        self.assertEqual(
            aprobados_por_asignatura.loc[
                'HIS - Historia',
                'porcentaje_aprobados',
            ],
            100,
        )

    def test_ranking_y_atipicos_iqr_con_resultado_conocido(self):
        ranking = obtener_ranking_alumnos(self.dataframe, cantidad=2)
        matematicas = self.dataframe[
            self.dataframe['asignatura'] == 'MAT - Matemáticas'
        ]
        atipicos = detectar_valores_atipicos_iqr(matematicas)

        self.assertEqual(ranking['alumno'].tolist(), ['Carla, C', 'Berta, B'])
        self.assertEqual(ranking['media'].tolist(), [7, 5])
        self.assertEqual(atipicos['valor'].tolist(), [10.0])


class EstadisticasNotasViewTests(TestCase):
    """Comprueba filtros, resultados y permisos de la página estadística."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo_profesor = Group.objects.get(name='Profesor')
        cls.grupo_alumno = Group.objects.get(name='Alumno')
        cls.profesor = get_user_model().objects.create_user(
            username='profesor_estadisticas',
            password='R0busta!Clave_2026',
        )
        cls.profesor.groups.add(cls.grupo_profesor)
        cls.alumno = get_user_model().objects.create_user(
            username='alumno_estadisticas',
            password='R0busta!Clave_2026',
        )
        cls.alumno.groups.add(cls.grupo_alumno)
        cls.asignatura = Asignatura.objects.create(
            nombre='Estadística',
            codigo='EST-VISTA',
            curso='2º',
            creditos=5,
        )
        cls.perfil = Alumno.objects.create(
            nombre='Ana',
            apellidos='Estudiante',
            email='vista-estadisticas@example.com',
            fecha_nacimiento=date(2005, 4, 12),
        )
        matricula = Matricula.objects.create(
            alumno=cls.perfil,
            asignatura=cls.asignatura,
            anio_academico='2025-2026',
        )
        Nota.objects.create(
            matricula=matricula,
            evaluacion=Nota.TipoEvaluacion.FINAL,
            valor=Decimal('8.00'),
            fecha=date(2026, 6, 1),
        )

    def test_solo_profesor_puede_ver_estadisticas(self):
        url = reverse('reportes:estadisticas')
        self.client.logout()
        respuesta_anonimo = self.client.get(url)
        self.assertRedirects(
            respuesta_anonimo,
            f'{reverse("login")}?next={url}',
        )

        self.client.force_login(self.alumno)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.profesor)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_vista_muestra_tablas_y_aplica_filtros_get(self):
        self.client.force_login(self.profesor)
        respuesta = self.client.get(
            reverse('reportes:estadisticas'),
            {'asignatura': self.asignatura.pk, 'anio': '2025-2026'},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, 'reportes/estadisticas.html')
        self.assertContains(respuesta, 'Media por asignatura')
        self.assertContains(respuesta, 'Porcentaje de aprobados')
        self.assertContains(respuesta, 'Ranking de alumnos')
        self.assertContains(respuesta, 'Valores atípicos')
        self.assertContains(respuesta, 'EST-VISTA - Estadística')
        self.assertEqual(
            respuesta.context['medias'][0]['media'],
            8,
        )

    def test_filtros_invalidos_muestran_errores_sin_resultados(self):
        self.client.force_login(self.profesor)
        respuesta = self.client.get(
            reverse('reportes:estadisticas'),
            {'asignatura': 'invalida'},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context['form'].errors)
        self.assertEqual(respuesta.context['medias'], [])

    def test_exportaciones_csv_y_excel_respetan_filtros_y_cabeceras(self):
        self.client.force_login(self.profesor)
        url = reverse('reportes:estadisticas')
        parametros = {
            'asignatura': self.asignatura.pk,
            'anio': '2025-2026',
        }

        respuesta_csv = self.client.get(
            url,
            {**parametros, 'export': 'csv'},
        )
        self.assertEqual(respuesta_csv.status_code, 200)
        self.assertEqual(
            respuesta_csv['Content-Disposition'],
            'attachment; filename="informe_notas.csv"',
        )
        self.assertIn('EST-VISTA - Estadística', respuesta_csv.content.decode('utf-8-sig'))
        self.assertNotIn('HIS-EST', respuesta_csv.content.decode('utf-8-sig'))

        respuesta_excel = self.client.get(
            url,
            {**parametros, 'export': 'xlsx'},
        )
        self.assertEqual(respuesta_excel.status_code, 200)
        self.assertEqual(
            respuesta_excel['Content-Disposition'],
            'attachment; filename="informe_notas.xlsx"',
        )
        libro = load_workbook(BytesIO(respuesta_excel.content), read_only=True)
        self.assertEqual(
            libro.sheetnames,
            ['Notas', 'Medias', 'Aprobados', 'Ranking', 'Atipicos'],
        )
        self.assertIn('EST-VISTA - Estadística', str(list(libro['Notas'].values)))

    def test_exportacion_rechaza_formato_desconocido(self):
        self.client.force_login(self.profesor)

        respuesta = self.client.get(
            reverse('reportes:estadisticas'),
            {'export': 'pdf'},
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_informe_resalta_notas_suspensas_y_ofrece_navegacion(self):
        alumno = Alumno.objects.create(
            nombre='Luis',
            apellidos='López',
            email='luis-suspenso@example.com',
            fecha_nacimiento=date(2005, 1, 1),
        )
        matricula = Matricula.objects.create(
            alumno=alumno,
            asignatura=self.asignatura,
            anio_academico='2025-2026',
        )
        Nota.objects.create(
            matricula=matricula,
            evaluacion=Nota.TipoEvaluacion.PRIMERA,
            valor=Decimal('4.00'),
            fecha=date(2025, 12, 1),
        )
        self.client.force_login(self.profesor)

        respuesta = self.client.get(reverse('reportes:informes'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'href="#notas"')
        self.assertContains(respuesta, 'href="#medias"')
        self.assertContains(respuesta, 'class="nota-suspensa"')
        self.assertContains(respuesta, 'López, Luis')
        self.assertContains(respuesta, 'export=xlsx')
        self.assertContains(respuesta, 'Descargar boletín CSV')


class BoletinAlumnoCSVViewTests(TestCase):
    """Comprueba permisos y datos incluidos en el boletín CSV."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo_profesor = Group.objects.get(name='Profesor')
        cls.grupo_alumno = Group.objects.get(name='Alumno')
        cls.profesor = get_user_model().objects.create_user(
            username='profesor_boletin',
            password='R0busta!Clave_2026',
        )
        cls.profesor.groups.add(cls.grupo_profesor)
        cls.usuario_alumno = get_user_model().objects.create_user(
            username='alumno_boletin',
            password='R0busta!Clave_2026',
        )
        cls.usuario_alumno.groups.add(cls.grupo_alumno)
        cls.perfil = Alumno.objects.create(
            nombre='Carla',
            apellidos='Cano',
            email='carla-boletin@example.com',
            fecha_nacimiento=date(2005, 3, 10),
            usuario=cls.usuario_alumno,
        )
        asignatura = Asignatura.objects.create(
            nombre='Lengua',
            codigo='LEN-CSV',
            curso='1º',
            creditos=4,
        )
        matricula = Matricula.objects.create(
            alumno=cls.perfil,
            asignatura=asignatura,
            anio_academico='2025-2026',
        )
        Nota.objects.create(
            matricula=matricula,
            evaluacion=Nota.TipoEvaluacion.PRIMERA,
            valor=Decimal('4.50'),
            fecha=date(2025, 12, 1),
        )
        Nota.objects.create(
            matricula=matricula,
            evaluacion=Nota.TipoEvaluacion.FINAL,
            valor=Decimal('7.50'),
            fecha=date(2026, 6, 1),
        )

    def test_alumno_descarga_solo_su_boletin(self):
        self.client.force_login(self.usuario_alumno)
        respuesta = self.client.get(reverse('reportes:boletin_alumno'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'text/csv; charset=utf-8')
        self.assertEqual(
            respuesta['Content-Disposition'],
            f'attachment; filename="boletin_alumno_{self.perfil.pk}.csv"',
        )
        contenido = respuesta.content.decode('utf-8-sig')
        self.assertIn('LEN-CSV - Lengua', contenido)
        self.assertIn('4.5', contenido)
        self.assertIn('7.5', contenido)
        self.assertIn('6.0', contenido)

    def test_alumno_no_puede_descargar_boletin_ajeno_cambiando_query(self):
        otro_alumno = Alumno.objects.create(
            nombre='Diana',
            apellidos='Díaz',
            email='diana-boletin@example.com',
            fecha_nacimiento=date(2006, 3, 10),
        )
        self.client.force_login(self.usuario_alumno)

        respuesta = self.client.get(
            reverse('reportes:boletin_alumno'),
            {'alumno': otro_alumno.pk},
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_profesor_descarga_boletin_de_alumno_seleccionado(self):
        self.client.force_login(self.profesor)

        respuesta = self.client.get(
            reverse('reportes:boletin_alumno'),
            {'alumno': self.perfil.pk},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('Cano, Carla', respuesta.content.decode('utf-8-sig'))

    def test_usuario_sin_rol_no_puede_descargar_boletines(self):
        usuario = get_user_model().objects.create_user(
            username='sin_rol_boletin',
            password='R0busta!Clave_2026',
        )
        self.client.force_login(usuario)

        respuesta = self.client.get(
            reverse('reportes:boletin_alumno'),
            {'alumno': self.perfil.pk},
        )

        self.assertEqual(respuesta.status_code, 403)
