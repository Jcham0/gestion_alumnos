# Gestión de alumnos

Aplicación web desarrollada con Django para administrar alumnos, asignaturas,
matrículas y notas. Incluye acceso diferenciado por rol, análisis de resultados
y exportación de informes.

## Funcionalidades por rol

| Rol | Funcionalidades |
| --- | --- |
| Visitante | Crear una cuenta de alumno e iniciar sesión. |
| Alumno | Consultar su panel, asignaturas, notas e historial; descargar su propio boletín CSV. No puede consultar datos de otro alumno cambiando la URL. |
| Profesor | Gestionar alumnos, asignaturas y matrículas; registrar notas; importar notas desde CSV; consultar estadísticas e informes y descargar boletines. |
| Superusuario | Acceder a la gestión académica y a las funciones de Profesor. El panel de administración de Django requiere además los permisos de administración correspondientes. |

El acceso de Profesor también se concede a los superusuarios, aunque no pertenezcan
al grupo `Profesor`. Los usuarios que se registran desde el formulario reciben
el grupo `Alumno`. El rol `Profesor` lo asigna el personal autorizado desde el
administrador.

## Requisitos

- Python 3.14 o una versión compatible con las dependencias de
  [`requirements.txt`](./requirements.txt).
- SQLite, incluido con Python.

Las versiones instaladas en el entorno de desarrollo se encuentran fijadas en
`requirements.txt`.

## Instalación y configuración

Desde la carpeta del proyecto, crea y activa un entorno virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

En Windows PowerShell, la activación es:

```powershell
venv\Scripts\Activate.ps1
```

Instala las dependencias y crea la configuración local:

```bash
python -m pip install -r requirements.txt
cp -n .env.example .env
```

Edita `.env` y sustituye el valor de ejemplo de `SECRET_KEY` por una clave
privada nueva. Para generar una clave de desarrollo con Django:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

El archivo `.env` contiene configuración local y está excluido de Git; no lo
compartas ni lo subas al repositorio. La configuración de ejemplo usa SQLite y
`DEBUG=True`, por lo que no es una configuración de producción.

## Base de datos y datos de prueba

Las migraciones necesarias ya están incluidas. Si más adelante se modifican los
modelos, genera primero las nuevas migraciones y después aplícalas:

```bash
python manage.py makemigrations
python manage.py migrate
```

Para generar datos de prueba, ejecuta:

```bash
python manage.py seed_datos
```

Por defecto se crean diez alumnos, asignaturas, matrículas, notas, dos cuentas
de prueba y un CSV con filas intencionalmente inválidas. Se pueden indicar
otra cantidad y, opcionalmente, limpiar antes los datos creados por este
comando:

```bash
python manage.py seed_datos 20
python manage.py seed_datos 10 --limpiar
```

El comando imprime las contraseñas aleatorias de las cuentas `seed_profesor` y
`seed_alumno` en la consola. Son nuevas en cada ejecución: consulta esa salida
para iniciar sesión y no reutilices credenciales anteriores. El CSV generado
para probar rechazos está en `datos/notas_prueba_errores.csv`; hay además un
ejemplo de importación válido en `datos/ejemplo_notas.csv`.

Para crear una cuenta administrativa propia:

```bash
python manage.py createsuperuser
```

## Ejecutar y probar

Inicia el servidor de desarrollo:

```bash
python manage.py runserver
```

Abre <http://127.0.0.1:8000/>. La aplicación redirige a la pantalla de acceso
cuando no hay una sesión iniciada. El panel de administración está en
<http://127.0.0.1:8000/admin/>.

Ejecuta la suite de pruebas automatizadas con:

```bash
python manage.py test
```

Comprobaciones adicionales del proyecto:

```bash
python manage.py check
python manage.py makemigrations --check
```

`python manage.py check --deploy` aún requiere configuración específica del
entorno donde se publique: dominio permitido, HTTPS/proxy y backend de correo.
No se deben activar opciones de producción sin adaptar esos valores.

## Estructura de las aplicaciones

```text
academico/
├── admin.py                  # Administración de los modelos académicos
├── forms.py                  # Formularios de registro y notas
├── management/commands/      # Comando seed_datos
├── migrations/               # Esquema y grupos iniciales
├── mixins.py                 # Reglas compartidas de acceso por rol
├── models.py                 # Alumno, Asignatura, Matricula y Nota
├── templatetags/             # Etiquetas para la navegación según el rol
├── tests.py                  # Pruebas de modelos, acceso y vistas académicas
├── tests_seed.py             # Pruebas del comando de datos de prueba
├── urls.py                   # Rutas de la aplicación
└── views.py                  # Registro, paneles y CRUD académico

reportes/
├── forms.py                  # Filtros e importación
├── migrations/               # Migraciones de la aplicación
├── services.py               # Importación, consultas y análisis con pandas
├── tests.py                  # Pruebas de importación, análisis y exportación
├── urls.py                   # Rutas de informes, estadísticas y boletines
└── views.py                  # Vistas de importación, informes y descargas
```

La configuración global de Django está en `config/`; las plantillas comunes y
por aplicación están en `templates/`, los estilos en `static/` y los CSV de
ejemplo en `datos/`.