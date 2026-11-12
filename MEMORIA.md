# Memoria técnica del proyecto

## Portada

**Proyecto:** Sistema de gestión de alumnos

**Tecnología principal:** Python y Django

**Base de datos de desarrollo:** SQLite

**Fecha de cierre documental:** 12/11/2026

## Índice

1. Descripción, objetivos y alcance
2. Tecnologías y alternativas
3. Modelo de datos
4. Arquitectura y rutas
5. Requisitos funcionales
6. Instalación y ejecución
7. Pruebas y calidad
8. Retos técnicos y trabajo pendiente

## 1. Descripción, objetivos y alcance

El sistema permite mantener la información académica de alumnos, asignaturas,
matrículas y notas desde una aplicación web. Distingue las funciones según el
rol del usuario, limita la información personal al alumno propietario y ofrece
herramientas de importación, análisis y exportación de resultados.

El alcance incluye registro y autenticación, gestión académica, consulta de
historial individual, informes tabulares y generación de datos para pruebas.
La configuración de producción (dominio, HTTPS, proxy y correo) depende del
entorno de publicación y no forma parte de la configuración local incluida.

## 2. Tecnologías y alternativas

- **Python y Django:** estructura web, autenticación, formularios, vistas,
  permisos y migraciones.
- **ORM de Django:** consultas y persistencia de los datos académicos.
- **SQLite:** base local sencilla para desarrollo y pruebas. En un despliegue
  compartido podría sustituirse por una base de datos de servidor, configurando
  apropiadamente el proyecto.
- **pandas:** procesamiento de CSV y cálculo de tablas estadísticas.
- **openpyxl:** escritura de informes Excel.
- **HTML y CSS:** plantillas Django y estilos locales.

Las versiones exactas de dependencias del entorno de desarrollo están en
[`requirements.txt`](./requirements.txt).

## 3. Modelo de datos

Los modelos están definidos en `academico/models.py`; `reportes` no define
tablas propias.

| Modelo | Datos principales | Relación y reglas |
| --- | --- | --- |
| `Alumno` | Nombre, apellidos, email, fecha de nacimiento y estado activo | Email único; vínculo opcional uno a uno con el usuario Django. |
| `Asignatura` | Nombre, código, curso y créditos | Código único. |
| `Matricula` | Año académico | Pertenece a un alumno y una asignatura. Solo se permite una matrícula por alumno, asignatura y año. |
| `Nota` | Evaluación, valor decimal y fecha | Pertenece a una matrícula; el valor se valida entre 0 y 10. |

Las relaciones tienen nombres inversos para recorrer matrículas y notas desde
los objetos relacionados. El orden predeterminado de cada modelo y las
restricciones de unicidad se declaran en sus opciones de modelo. Las
migraciones crean las tablas, el vínculo opcional con el usuario y los grupos
`Alumno` y `Profesor`.

## 4. Arquitectura y rutas

`config/` contiene ajustes globales y conecta las dos aplicaciones mediante
sus archivos `urls.py`. La ruta raíz lleva al inicio académico; la
autenticación estándar está bajo `accounts/`.

### Aplicación `academico`

Contiene modelos, administración, formularios, reglas de acceso, vistas,
rutas, migraciones y el comando de datos de prueba. Sus rutas bajo
`/academico/` proporcionan registro, inicio, paneles por rol, CRUD de alumnos,
asignaturas y matrículas, y alta de notas. Las plantillas académicas están en
`templates/academico/`.

### Aplicación `reportes`

Contiene filtros, vistas y lógica de servicio para importar CSV, obtener y
analizar DataFrames, presentar informes y descargar resultados. Sus rutas
están bajo `/reportes/`; sus plantillas están en `templates/reportes/`.
Estadísticas e importación requieren permiso de gestión; el boletín es
descargable por un profesor o por el alumno propietario.

Las plantillas generales y de acceso están en `templates/`, y los estilos
compartidos en `static/css/`.

## 5. Requisitos funcionales

| Actor | Acción | Respuesta del sistema |
| --- | --- | --- |
| Visitante | Crear una cuenta | El formulario valida usuario y email, asigna el grupo `Alumno`, vincula un perfil existente con el mismo email si corresponde y redirige al login con confirmación. |
| Usuario | Iniciar o cerrar sesión | Django autentica la cuenta; el inicio deriva al panel que corresponda al rol. |
| Profesor o superusuario | Mantener alumnos, asignaturas y matrículas | El sistema permite listar, buscar, paginar, crear, editar y borrar con confirmación y mensajes de resultado. |
| Profesor o superusuario | Registrar notas | El formulario valida evaluación y valor, y evita duplicar una evaluación para la misma matrícula. |
| Alumno | Consultar su panel e historial | El sistema presenta únicamente las asignaturas y notas vinculadas a la cuenta autenticada, junto con medias. |
| Alumno | Descargar un boletín | Se genera un CSV con sus notas y medias; un parámetro de URL no permite seleccionar los datos de otra persona. |
| Profesor o superusuario | Importar un CSV de notas | El servicio normaliza y valida filas, busca las relaciones con el ORM e informa las importadas y los rechazos con su motivo. |
| Profesor o superusuario | Consultar estadísticas e informes | El sistema muestra tablas filtrables con medias, aprobados, ranking y detección de valores atípicos; permite exportar CSV y Excel. |
| Profesor o superusuario | Descargar un boletín | Puede seleccionar el alumno cuyos datos quiere exportar. |
| Administrador | Administrar cuentas y asignar el grupo Profesor | Django Admin proporciona la administración de usuarios y modelos según los permisos concedidos. |

La regla de gestión se comparte entre las vistas y la navegación: el grupo
`Profesor` o `is_superuser`. El grupo `Alumno` no concede acceso a las vistas
de gestión.

## 6. Instalación y ejecución

Los pasos completos y los comandos para generar datos de prueba y ejecutar los
tests se mantienen en el [README](./README.md). En resumen:

1. Crear y activar un entorno virtual.
2. Instalar `requirements.txt`.
3. Copiar `.env.example` a `.env` y reemplazar la clave de ejemplo por una
   clave privada local.
4. Aplicar las migraciones con `python manage.py migrate`.
5. Opcionalmente ejecutar `python manage.py seed_datos` y consultar en consola
   las contraseñas aleatorias impresas.
6. Iniciar el servidor con `python manage.py runserver`.

El archivo `.env`, la base de datos SQLite local y el entorno virtual no deben
subirse al repositorio.

## 7. Pruebas y calidad

La suite se ejecuta con `python manage.py test`. Incluye pruebas de modelos y
restricciones, autenticación y permisos, CRUD, aislamiento de datos de
alumnos, importación CSV, análisis pandas, exportaciones y comando de datos
de prueba.

Al cierre de la Fase 10 se verificaron 77 pruebas correctas,
`python manage.py check` sin problemas y `python manage.py makemigrations
--check` sin cambios pendientes.

## 8. Retos técnicos y trabajo pendiente

- La unicidad se prueba tanto mediante validación de modelos como mediante
  restricciones reales de base de datos.
- El aislamiento del alumno se resuelve limitando la consulta al perfil
  asociado con el usuario autenticado, no confiando en un identificador
  enviado en la URL.
- La selección del rol no se ofrece en el registro: el servidor asigna
  `Alumno`; la concesión del rol `Profesor` corresponde a administración.
- El CSV de notas no incluye el año académico, por lo que el importador rechaza
  los casos donde la matrícula no se puede determinar de forma única.
- `python manage.py check --deploy` informa que falta definir backend de correo
  de producción, dominio permitido, HSTS, redirección/cookies seguras y
  `DEBUG=False`. Se deben configurar según el hosting, el proxy y el dominio
  reales; fijar valores sin esa información no sería seguro.
- Queda pendiente comprobar visualmente, con cuentas autenticadas, los paneles
  y descargas en un navegador. El push a GitHub lo realizará el propietario
  del repositorio.
