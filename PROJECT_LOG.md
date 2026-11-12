# Contrato actual

## Aplicaciones y modelos

- `academico`:
  - `Alumno`: `nombre`, `apellidos`, `email` (único), `fecha_nacimiento`, `activo` y `usuario` (OneToOne nullable hacia `AUTH_USER_MODEL`, con `SET_NULL`).
  - `Asignatura`: `nombre`, `codigo` (único), `curso` y `creditos`.
  - `Matricula`: FK `alumno` y `asignatura`, y `anio_academico`; unicidad conjunta por los tres campos.
  - `Nota`: FK `matricula`, `evaluacion`, `valor` decimal validado entre 0 y 10, y `fecha`.
- `reportes`: no hay modelos propios definidos en `models.py`.

## Autenticación

- Login y logout: URLs estándar de Django bajo `accounts/`.
- Registro: `academico:registro`; el formulario requiere correo único y asigna automáticamente el grupo `Alumno`.
- El formulario de registro no expone grupos; el grupo `Profesor` solo se gestiona desde el administrador.
- Una migración de datos crea los grupos `Alumno` y `Profesor`; el registro asocia el grupo `Alumno`.
- `academico.mixins.puede_gestionar_academico` centraliza el permiso `Profesor o superusuario`; `ProfesorRequiredMixin` y la navegación reutilizan esa regla.
- `academico.mixins.AlumnoRequiredMixin` protege el panel personal para cuentas del grupo Alumno.
- Al registrarse, se vincula el primer `Alumno` sin usuario cuyo correo coincida sin distinguir mayúsculas.
- Inicio de sesión redirige a `academico:inicio`; logout redirige a `login`.

## Administración

- `academico.admin`: `Alumno`, `Asignatura`, `Matricula` y `Nota` están registrados con columnas, búsqueda y filtros adecuados a sus campos.

## URLs, vistas y plantillas

- `config.urls`: raíz redirige a `academico:inicio`; `accounts/` lleva al login y conserva las rutas estándar de autenticación; `reportes/` lleva a la página de informes; también incluye `admin/`, `academico/` y las rutas de informes.
- `academico.urls`: inicio con redirección por rol, paneles de Alumno y Profesor, registro, CRUD de alumnos, asignaturas y matrículas, y alta de notas; nombres bajo `app_name = 'academico'`.
- `reportes.urls`: informes protegidos en `/reportes/informes/` (`reportes:informes`) y `/reportes/notas/estadisticas/` (`reportes:estadisticas`), importación CSV en `/reportes/notas/importar/` (`reportes:importar_notas`) y descarga de boletines CSV en `/reportes/boletin/` (`reportes:boletin_alumno`).
- `academico.views`: inicio con redirección por rol, panel personal de Alumno limitado a `request.user.perfil_alumno`, panel Profesor con accesos rápidos, registro y CRUD CBV de alumnos, asignaturas y matrículas, además del alta de notas.
- `reportes.views`: informes y estadísticas e importación CSV protegidas para profesores; los boletines CSV se ofrecen a profesores y al alumno propietario. `reportes.services` transforma y analiza notas con pandas y el ORM, además de procesar la importación.
- `academico.management.commands.seed_datos`: comando `seed_datos [N] [--limpiar]` para crear datos aleatorios de prueba, las cuentas `seed_profesor` y `seed_alumno`, y el CSV con errores intencionados.
- Plantillas globales y CRUD en `templates/`: base, login, registro, inicio y listas, formularios y confirmaciones de alumnos, asignaturas y matrículas, formulario de nota e importación CSV.
- `templates/academico/panel_alumno.html` muestra solo las matrículas de la cuenta actual, sus evaluaciones y la media por matrícula/asignatura/año; `panel_profesor.html` ofrece accesos rápidos de gestión.
- CSV de ejemplo: `datos/ejemplo_notas.csv`.
- CSV para pruebas negativas de importación: `datos/notas_prueba_errores.csv`.
- `reportes/estadisticas.html` presenta notas y análisis (medias por asignatura, porcentaje de aprobados, ranking y valores atípicos IQR), filtros GET y enlaces CSV/Excel; `reportes.services.obtener_dataframe_boletin` prepara las notas y medias individuales.
- `templates/base.html` carga `static/css/styles.css`, diferencia visitantes y usuarios autenticados, muestra un único rol y ofrece el menú de gestión a profesores y superusuarios; la administración aparece para usuarios `is_staff`.

## Configuración

- `config.settings` registra las aplicaciones integradas de Django, `academico` y `reportes`.
- Las variables `DEBUG`, `SECRET_KEY` y `DATABASE_URL` se cargan desde `.env`; la base de datos configurada es SQLite.

# Bitácora

## 12/11/2026 — Configuración inicial de las aplicaciones y el entorno

- Se completó `.gitignore` para excluir `venv/`, `.env`, `db.sqlite3`, `__pycache__/` y `.DS_Store`.
- Se configuraron `.env` y `.env.example`; la clave local de desarrollo no se incluye en esta bitácora.
- Se conectó la carga de variables de entorno en `config/settings.py`, incluyendo validaciones para la URL SQLite.
- Se registraron `academico` y `reportes`, se añadieron sus módulos de URLs y se incluyeron en `config/urls.py`.

### Siguiente paso pendiente

Continuar las vistas funcionales de `academico` según el alcance acordado; el inicio actual es una página sencilla de bienvenida.

## 12/11/2026 — Modelos académicos

- Se definieron `Alumno`, `Asignatura`, `Matricula` y `Nota` con orden predeterminado, representaciones legibles, relaciones inversas y la restricción de matrícula única por alumno, asignatura y año.
- Se añadieron pruebas para unicidad, relaciones, orden, opciones de evaluación y límites de las notas.
- Se generó y aplicó `academico/migrations/0001_initial.py`.
- Las seis pruebas de `academico` pasan; `manage.py check` no detecta problemas y `makemigrations --check` no detecta cambios pendientes.
- No se modificaron vistas ni rutas.

### Siguiente paso pendiente

Definir las vistas y rutas funcionales de `academico` cuando se concrete su alcance.

## 12/11/2026 — Registro de modelos en Django Admin

- Se registraron los cuatro modelos académicos con columnas visibles, campos de búsqueda y filtros.
- Se ejecutaron `makemigrations` y `migrate`; la migración existente no requirió cambios y la base de datos quedó actualizada.
- `manage.py check` finalizó sin errores.

### Siguiente paso pendiente

Crear manualmente un superusuario con `python manage.py createsuperuser` y, más adelante, definir las vistas funcionales de `academico`.

## 12/11/2026 — Acceso y registro de alumnos

- Se habilitaron login y logout con las vistas y rutas integradas de `django.contrib.auth`.
- Se creó un formulario de alta basado en `UserCreationForm`, con correo obligatorio y comprobación de unicidad sin distinguir mayúsculas.
- El registro asigna el grupo `Alumno` en el servidor; el formulario no admite roles ni grupos enviados por el cliente.
- Se añadieron plantillas para el diseño base, login, registro e inicio; el login ofrece el enlace «Crear cuenta».
- Se configuraron las rutas de redirección y se añadieron pruebas de registro, correo duplicado, asignación de rol y ciclo login/logout.
- Las pruebas y comprobaciones de Django pasan; no hay migraciones pendientes.

### Siguiente paso pendiente

Crear o asignar grupos y usuarios desde el panel de administración según las necesidades del proyecto; ampliar el inicio cuando se definan las funciones posteriores al acceso.

## 12/11/2026 — Grupos, perfiles y permisos de profesor

- Se añadió a `Alumno` el vínculo OneToOne opcional `usuario` con `SET_NULL`.
- Se creó una migración de datos para los grupos `Alumno` y `Profesor`; su reversión conserva grupos para no eliminar asignaciones existentes.
- Se implementó `ProfesorRequiredMixin` como complemento de `LoginRequiredMixin`.
- El registro asocia transaccionalmente el nuevo usuario con el primer alumno sin usuario cuyo correo coincida sin distinguir mayúsculas.
- Se actualizaron el panel de alumnos y las pruebas de migración, permisos y asociación de cuentas.
- Se aplicaron las migraciones `0002_alumno_usuario` y `0003_crear_grupos_usuario`; los grupos requeridos ya existen en la base de datos.
- Las 15 pruebas pasan, `manage.py check` no detecta problemas y `makemigrations --check` no detecta cambios pendientes.

### Siguiente paso pendiente

Usar `LoginRequiredMixin` junto con `ProfesorRequiredMixin` en las vistas de profesor cuando se implementen.

## 12/11/2026 — CRUD de alumnos para profesores

- Se creó `AlumnoForm` para los campos académicos, excluyendo el vínculo de usuario.
- Se añadieron vistas CBV de listado, creación, edición y eliminación, protegidas por `LoginRequiredMixin` y `ProfesorRequiredMixin`.
- El listado permite buscar por nombre, apellidos o email y pagina diez registros por página; los enlaces preservan la búsqueda.
- Se añadieron plantillas extendidas desde `base.html`, enlace de navegación para profesores y confirmación POST con CSRF antes de eliminar.
- El borrado advierte y ejecuta la cascada existente de eliminación de matrículas y notas relacionadas.
- Se añadieron pruebas para autorización, búsqueda, paginación, CRUD, vínculo de usuario y cascada.

### Siguiente paso pendiente

Probar visualmente las pantallas con una cuenta del grupo Profesor y continuar con las funciones académicas que se definan.

- Las 24 pruebas pasan; `manage.py check` no detecta problemas y `makemigrations --check` no detecta cambios pendientes.

## 12/11/2026 — Navegación por rol y estilos base

- Se mejoró `templates/base.html` con navegación de sesión, distintivos de rol, cierre CSRF, mensajes accesibles y bloques `title` y `content`.
- Se creó `static/css/styles.css` con estilos responsivos sencillos y se configuró `STATICFILES_DIRS`.
- Se añadieron pruebas para navegación pública, rol alumno/profesor, visibilidad de administración y referencia del CSS.

### Siguiente paso pendiente

Continuar la navegación con enlaces a funciones reales cuando se implementen las vistas de cada rol.

- Las 18 pruebas pasan; `manage.py check` no detecta problemas y `makemigrations --check` no detecta cambios pendientes.
- `manage.py findstatic css/styles.css` localiza correctamente la hoja de estilos en `static/css/styles.css`.

## 12/11/2026 — CRUD de asignaturas y mensajes de operación

- Se creó `AsignaturaForm` y las vistas CBV de listado, alta, edición y borrado para profesores.
- La lista busca por nombre o código, pagina diez registros y conserva la búsqueda entre páginas.
- Se añadieron plantillas con confirmación CSRF para borrar; se informa de la cascada sobre matrículas y notas.
- Se ordenaron y nombraron las rutas CRUD de ambas entidades bajo `app_name = 'academico'`.
- Se añadieron mensajes de éxito a las altas, ediciones y borrados de alumnos y asignaturas, y enlaces de ambas secciones en la navbar del profesor.
- Se incorporaron pruebas para permisos, búsqueda, paginación, rutas, mensajes, navegación y borrado en cascada.

### Siguiente paso pendiente

Probar visualmente el CRUD con una cuenta del grupo Profesor.

- Las 32 pruebas pasan; `manage.py check` no detecta problemas y `makemigrations --check` no detecta cambios pendientes.

## Fase 5, pedidos 1–3 de 3 — Matrículas, notas e importación CSV

- Se creó el CRUD de matrículas para profesores, con paginación, mensajes de éxito y confirmación de borrado; el borrado elimina las notas asociadas según la cascada del modelo.
- Se creó `NotaForm` con validación en `clean()` del rango 0–10 y de la unicidad de la evaluación por matrícula, y una vista protegida para registrar notas.
- Se implementó `reportes.services.importar_notas_csv`, que limpia espacios, rechaza filas duplicadas adicionales, valores vacíos o inválidos y evalúa cada fila localizando alumno, asignatura y matrícula con el ORM.
- El CSV no tiene columna de fecha: las notas importadas usan `timezone.localdate()`. Si hay varias matrículas del alumno y asignatura en distintos años, la fila se rechaza por ambigüedad, ya que el CSV no especifica el curso académico.
- Se añadieron una vista y plantilla protegidas para subir CSV, un resumen de filas importadas/rechazadas con motivo y `datos/ejemplo_notas.csv`.
- Se configuró la interfaz y la fecha local con idioma español y zona horaria `Europe/Madrid`.
- Se actualizaron la navegación y las pruebas. No se requieren cambios de modelo ni migraciones.
- Las 46 pruebas pasan, `manage.py check` no detecta problemas y `makemigrations --check` no detecta cambios pendientes.

### Siguiente paso pendiente

Probar visualmente la gestión de matrículas y la carga CSV con una cuenta del grupo Profesor; acordar si futuras importaciones deben incluir año académico y fecha como columnas.

## 12/11/2026 — Redirección de la raíz y accesos a prefijos

- Se añadió en `config/urls.py` la redirección de `/` a `academico:inicio`, nombre comprobado en `academico/urls.py`.
- Se protegió la vista de inicio con `login_required`; las visitas sin sesión terminan en la pantalla de login.
- Se añadieron accesos a `/accounts/` y `/reportes/`, manteniendo las rutas específicas de autenticación e informes.
- Se añadieron pruebas para la raíz, los prefijos principales y las rutas configuradas en `LOGIN_URL` y `LOGIN_REDIRECT_URL`.
- Las 49 pruebas pasan; `manage.py check` no detecta problemas y `makemigrations --check --dry-run` no encuentra cambios pendientes. Las comprobaciones HTTP de `/`, `/academico/`, `/reportes/` y `/accounts/` terminan con respuesta 200; las rutas protegidas redirigen al login cuando no hay sesión.

### Siguiente paso pendiente

Probar visualmente la navegación con sesiones de alumno y profesor.

## 12/11/2026 — Acceso de gestión para superusuarios

- Se centralizó en `academico.mixins.puede_gestionar_academico` la regla común para profesores y superusuarios.
- Se actualizó `ProfesorRequiredMixin`, compartido por las vistas de `academico` y `reportes`, para delegar en esa función.
- Se añadió la etiqueta `acceso_gestion_academica` para que `templates/base.html` aplique exactamente la misma regla al menú.
- Se añadió la etiqueta `es_alumno` para identificar el grupo Alumno sin confundirlo con otros grupos no académicos.
- El menú presenta una sola etiqueta de rol y muestra una sola vez cada enlace, incluso si un profesor también pertenece al grupo Alumno.
- Se añadieron pruebas para profesor, alumno, superusuario sin grupo y usuario sin grupo, tanto para navegación como para permisos de las vistas.
- Las 52 pruebas pasan y `manage.py check` no detecta problemas.

### Siguiente paso pendiente

Probar visualmente el menú con cuentas de profesor, alumno y superusuario.

## Fase 7, pedidos 1–3 de 3 — Análisis de datos con pandas

- Se añadió `obtener_dataframe_notas` en `reportes/services.py`; consulta con `values()` y devuelve las columnas `alumno`, `asignatura`, `evaluacion`, `valor` y `anio`, con filtros opcionales por asignatura y año académico.
- Se añadieron funciones que devuelven DataFrames para media por asignatura, porcentaje de aprobados (nota >= 5), ranking de los N alumnos con mayor media e identificación de valores atípicos por el criterio IQR de 1,5 veces el rango intercuartílico.
- Se creó un formulario GET que ofrece las asignaturas y años existentes, y la vista protegida `EstadisticasNotasView` en `/reportes/notas/estadisticas/`.
- Se añadió la plantilla `templates/reportes/estadisticas.html` con tablas para cada análisis y enlaces desde el menú y el panel del profesorado.
- Se añadieron pruebas para el DataFrame, filtros, agregaciones, ranking, IQR, resultados vacíos, validación de filtros y permisos.
- Las 63 pruebas pasan; `manage.py check` no detecta problemas y `makemigrations --check --dry-run` no encuentra cambios pendientes.
- La URL de estadísticas está disponible y redirige al login sin sesión; las pruebas verifican la vista y su contenido al entrar con un usuario Profesor.

### Siguiente paso pendiente

Revisar visualmente las tablas de estadísticas con una cuenta del grupo Profesor.

## Fase 8, pedidos 1–3 de 3 — Informes y exportación

- Se convirtió la página de estadísticas de la Fase 7 en un informe académico legible, disponible en `/reportes/informes/`, con navegación entre secciones, columnas numéricas alineadas y notas inferiores a 5 resaltadas.
- Se añadieron exportaciones CSV y Excel desde la vista protegida; las dos respetan los filtros GET. El Excel incluye hojas de notas, medias, aprobados, ranking y valores atípicos; los archivos se devuelven con `HttpResponse` y `Content-Disposition`.
- Se instaló `openpyxl==3.1.5` en `venv` y se fijó junto a su dependencia `et-xmlfile==2.0.0` en `requirements.txt`.
- Se añadió la descarga CSV del boletín con todas las evaluaciones y la media por asignatura y año. El Profesor puede seleccionar cualquier alumno; una cuenta Alumno se resuelve desde `request.user.perfil_alumno` y no puede seleccionar otro identificador.
- Se añadió el acceso a informes en el menú, el panel Profesor y la raíz `/reportes/`; el panel del Alumno incluye el enlace a su boletín propio.
- Se añadieron pruebas de tablas, resaltado de suspensos, filtros, cabeceras/formatos de exportación, contenido del boletín y permisos de Profesor, Alumno y cuenta sin rol.
- Las 71 pruebas pasan; `manage.py check` no detecta problemas, `makemigrations --check --dry-run` no encuentra cambios pendientes y `pip check` no detecta dependencias rotas.
- `/reportes/`, `/reportes/informes/`, `/reportes/notas/estadisticas/` y `/reportes/boletin/` responden sin 404 y redirigen al login si no hay sesión. Los accesos y descargas autenticados se comprueban con tests.

### Siguiente paso pendiente

Revisar visualmente el informe y las descargas con cuentas autenticadas de Profesor y Alumno si se dispone de ellas.

## Fase 9, pedidos 1–2 de 2 — Datos de prueba

- Se creó el comando `python manage.py seed_datos [N]`, con diez alumnos por defecto, cinco asignaturas, matrículas y notas aleatorias válidas. Las evaluaciones no se repiten dentro de una matrícula.
- `--limpiar` elimina solo alumnos con correo `seed.alumno.*@example.com`, asignaturas con código `SEED*` y las cuentas reservadas `seed_profesor`/`seed_alumno`; las matrículas y notas asociadas se eliminan por cascada. Una cantidad menor que uno se rechaza antes de limpiar.
- El comando asigna un usuario al grupo Profesor y otro al grupo Alumno, vincula el segundo a un perfil generado y muestra contraseñas aleatorias. Las contraseñas de estas cuentas reservadas se restablecen en cada ejecución y se muestran en consola.
- Se generó `datos/notas_prueba_errores.csv` con pandas, con una fila duplicada, valores vacíos, una nota superior a 10 y un email inexistente. Las pruebas ejecutan el archivo mediante `importar_notas_csv` y verifican los rechazos.
- Se ejecutó el comando con el valor por defecto, creando 10 alumnos, 5 asignaturas y 43 matrículas en la base de desarrollo local.
- Las 74 pruebas pasan; `manage.py check` no detecta problemas, `makemigrations --check --dry-run` no encuentra cambios pendientes y `pip check` no detecta dependencias rotas.

### Siguiente paso pendiente

Usar las credenciales impresas al ejecutar el comando para probar la interfaz con las cuentas de prueba; si se necesita limpiar los datos generados, ejecutar `python manage.py seed_datos 10 --limpiar`.

## Fase 6, pedidos 1–3 de 3 — Zona del usuario final

- Se creó un panel de solo lectura para el grupo Alumno. La consulta filtra las matrículas por `alumno__usuario=request.user`, sin aceptar identificadores de alumno desde la URL o el formulario; una cuenta sin perfil vinculado recibe una lista vacía.
- El historial muestra cada evaluación y fecha, agrupadas por matrícula (asignatura y año académico), y calcula la media de las notas de esa matrícula.
- Se creó un panel de Profesor con accesos rápidos a alumnos, asignaturas, matrículas, registro de notas e importación CSV.
- `academico:inicio`, destino de `LOGIN_REDIRECT_URL`, redirige a Profesor/superusuario primero y a Alumno después. El usuario autenticado sin esos roles conserva la página genérica.
- Se incorporaron `AlumnoRequiredMixin` y una comprobación compartida de pertenencia al grupo Alumno; los paneles respetan los permisos correspondientes.
- Se añadieron pruebas de aislamiento entre alumnos, cuenta Alumno sin perfil, permisos de ambos paneles, media de notas y redirección por rol, incluida la prioridad cuando se combinan grupos.
- Las 56 pruebas pasan; `manage.py check` no detecta problemas y `makemigrations --check --dry-run` no encuentra cambios pendientes.
- En el navegador, `/` redirige al formulario de login cuando no hay sesión. La navegación autenticada de los dos roles queda cubierta por pruebas; no se han usado credenciales reales para una sesión visual.

### Siguiente paso pendiente

Si se desea completar la comprobación visual autenticada, probar los paneles con cuentas de Alumno y Profesor del proyecto.

## Fase 10, pedidos 1–3 de 3 — Pruebas y calidad

- Se ampliaron las pruebas de modelos para comprobar que la base de datos rechaza correos duplicados, códigos de asignatura repetidos y matrículas duplicadas, además de las validaciones de `full_clean()` ya existentes.
- Se añadieron pruebas unitarias con un DataFrame pequeño y resultados conocidos para medias, porcentaje de aprobados, ranking y detección de valores atípicos por IQR.
- Se conservaron y verificaron las pruebas de permisos: las cuentas anónimas se redirigen al login, los alumnos no acceden al CRUD ni a la importación y no pueden consultar las matrículas de otro alumno, mientras que Profesor y superusuario pueden gestionar.
- Se limpiaron imports sin uso y plantillas vacías de administración/modelos. Se conservaron las firmas que exige Django y se marcaron los parámetros no utilizados como tales.
- `python manage.py test`: 77 pruebas correctas. `python manage.py check`: sin problemas. `python manage.py makemigrations --check`: sin cambios pendientes.
- `python manage.py check --deploy` no queda limpio: reporta `mail.E001` (backend de correo de consola) y `security.W004`, `W008`, `W012`, `W016`, `W018` y `W020` (HSTS, redirección/cookies HTTPS, `DEBUG=True` y `ALLOWED_HOSTS` vacío). No se fijaron valores de producción porque dependen del dominio, HTTPS/proxy y proveedor de correo del despliegue.
- No se modificaron modelos ni comportamiento de producción; el contrato actual sigue correspondiendo al código.

### Siguiente paso pendiente

Completar una comprobación visual autenticada de los paneles y, antes de desplegar, definir dominio, terminación HTTPS y backend de correo para corregir las advertencias de `check --deploy`.

## Fase 11, pedidos 1–3 de 3 — Documentación final y cierre

- Se completó `README.md` con descripción, funcionalidades por rol, instalación, migraciones, creación de datos de prueba, ejecución de tests y estructura de `academico` y `reportes`. Las contraseñas de prueba se generan al ejecutar `seed_datos` y se consultan en su salida; no se documentaron credenciales fijas.
- Se creó `MEMORIA.md` como memoria técnica final con alcance, stack, modelo de datos, rutas, requisitos funcionales por actor, instalación, pruebas y retos pendientes. También se completó `MEMORY.md` con las decisiones operativas finales solicitadas.
- Se ejecutó `pip freeze` desde `venv` y se actualizó `requirements.txt` con las diez dependencias fijadas del entorno.
- El repositorio está en la rama `main`. `.env`, `venv/` y `db.sqlite3` aparecen ignorados y no rastreados por Git. No se realizará `git push`; el propietario lo hará manualmente.
- Las verificaciones de código de la Fase 10 siguen siendo la referencia: 77 pruebas correctas, `check` sin problemas y `makemigrations --check` sin cambios pendientes. `check --deploy` conserva los avisos de configuración de producción documentados en esta bitácora.
- Resumen de trabajo: configuración inicial y estructura Django; modelos y administración; autenticación, grupos y permisos; navegación y CRUD; Fase 5, matrículas, notas e importación; Fase 6, paneles e historial; Fase 7, análisis pandas; Fase 8, informes y exportaciones; Fase 9, datos de prueba; Fase 10, pruebas y calidad; Fase 11, documentación y preparación del repositorio.

### Siguiente paso pendiente

Ejecutar la comprobación visual autenticada que falta; para publicar en producción, definir dominio, HTTPS/proxy y correo, y resolver los avisos de `check --deploy`. Revisar el commit inicial preparado y hacer el push a GitHub manualmente.