# Instrucciones para Copilot · Proyecto Python y Django

## 1. Contexto
* Proyecto de Python con Django, el ORM de Django y SQLite (salvo que el proyecto indique otra base de datos).
* La descripción, el enunciado y los requisitos del proyecto están en `README.md` y `MEMORIA.md`. Léelos si necesitas entender el objetivo de una tarea.
* El usuario es principiante en la sintaxis de Python y Django. Quiere entender el código, no solo recibirlo.
* **Idioma:** responde, documenta y escribe docstrings y comentarios en español.

## 2. Reglas de oro (máxima prioridad)
1. **El código real manda.** Si `PROJECT_LOG.md` no coincide con el código, sigue el código y avisa de la diferencia.
2. **Nunca inventes nombres.** Modelos, campos, métodos, vistas, URLs y plantillas deben existir: compruébalos abriendo el archivo, no de memoria.
3. **Una fase y una tarea cada vez.** No construyas el proyecto de golpe.
4. **Pregunta antes** de instalar paquetes, cambiar la estructura del proyecto, borrar archivos o cambiar la versión de Django.
5. **Si dudas, dilo.** Ante una duda de sintaxis de Django o Python, indícalo en lugar de adivinar.
6. Una fase no está terminada hasta superar las comprobaciones de la sección 8 y reflejarse en la documentación.

## 3. Protocolo antes de cada tarea
1. Lee `PROJECT_LOG.md` (bloque «Contrato actual» y última entrada) y los archivos reales implicados: `models.py`, `urls.py`, `views.py`, `forms.py` y las plantillas de las apps afectadas.
2. Muestra una lista breve de los nombres que vas a usar, indicando en qué archivo has verificado cada uno.
3. Si vas a referenciar un campo o método, ábrelo y confirma su nombre exacto y su tipo; no lo deduzcas por el nombre del modelo.
4. Si falta algo, no lo inventes: indica qué falta y créalo primero.
5. Los cambios de modelo (añadir o modificar campos) van en un paso aparte, con su migración, antes de construir vistas o plantillas encima.
6. Antes de programar una funcionalidad importante, propón un plan breve paso a paso y espera la validación del usuario.

## 4. Estándares de código
* Usa la última versión LTS de Django y una versión estable de Python compatible. Si ya hay una versión de Django instalada, no la cambies: usa solo APIs de esa versión.
* Aplica patrones y sintaxis de la documentación oficial más reciente de Python y Django.
* Sigue PEP 8 de forma estricta (nombres, sangría e importaciones). Codificación UTF-8 en todos los ficheros.
* **Comentarios:** no expliques sintaxis básica ni lo obvio. Usa docstrings descriptivos en clases y métodos, y comentarios breves y técnicos solo para justificar decisiones de diseño o lógica de negocio compleja. Las explicaciones didácticas van en el chat, no en el código.
* Cuando crees una app nueva, regístrala de inmediato en `INSTALLED_APPS` (`settings.py`) antes de avanzar a modelos o rutas.
### Rutas (`config/urls.py`)
* Cada app tiene su propio `urls.py` con `app_name` definido. En `config/urls.py` se conecta con `include()` y un prefijo propio (por ejemplo `path('academico/', include('academico.urls'))`).
* **Define siempre una ruta para la raíz (`''`)** que lleve a la página principal del proyecto, para que `http://127.0.0.1:8000/` nunca dé un 404. Usa `RedirectView` hacia la vista de inicio de la app principal, o una vista `home` propia.
* Si el proyecto tiene login, configura `LOGIN_URL`, `LOGIN_REDIRECT_URL` y `LOGOUT_REDIRECT_URL` en `settings.py` apuntando a rutas que existan.
* Cada vez que crees una app nueva, conecta su `urls.py` en `config/urls.py` en el mismo paso, y comprueba que su ruta carga en el navegador.

### Fechas y horas
* Usa `DateField` y `DateTimeField`, y `django.utils.timezone.now()` en lugar de `datetime.now()`.
* Configura `LANGUAGE_CODE = "es"`, `TIME_ZONE = "Europe/Madrid"` y `USE_TZ = True`.
* Muestra las fechas al usuario en formato `DD/MM/AAAA`; guárdalas en la base de datos y en los fixtures como `AAAA-MM-DD`. En la bitácora y la documentación usa `DD/MM/AAAA`.

### Buenas prácticas de Django
* Protege las vistas privadas con `@login_required` y los permisos que correspondan; comprueba el acceso también en los tests.
* Usa `get_object_or_404` para recuperar objetos por identificador.
* Mantén `{% csrf_token %}` en todos los formularios POST.
* Usa el ORM; no escribas SQL a mano. Evita consultas repetidas con `select_related` / `prefetch_related` cuando se recorran relaciones.
* Valida los datos con formularios de Django, no a mano en la vista.
* No pongas secretos ni credenciales reales en el código ni en el repositorio.

## 5. Cómo explicar
* Explica brevemente cada bloque de código nuevo: qué hace y por qué se hace así.
* Usa un lenguaje sencillo y no des por hecho que se conoce la sintaxis.

## 6. Flujo de trabajo por fases
* Trabaja por fases pequeñas e iterativas. Si una fase se divide en pedidos, etiquétalos **«Fase N, pedido X de Y»**.
* El mapa de fases del proyecto está en `docs/FASES.md`. Usa siempre su numeración en el log, la memoria y los mensajes, y no inventes otra. Trabaja solo en la fase indicada por el usuario.

### Navegación (`base.html`)
* Cada vez que crees una vista pública o protegida accesible por una URL con nombre, si lo crees necesario añade su enlace a la barra de navegación en `base.html`. Si es una zona privada, condiciónalo con `{% if user.is_authenticated %}`. El usuario no debe tener que escribir la URL a mano.

### Fixtures
* No los generes hasta que `models.py` esté totalmente definido y las migraciones aplicadas. Entonces crea un fixture JSON de datos de prueba, guárdalo como archivo permanente del proyecto (cargable en otro equipo con `loaddata`) y regénéralo si cambian los modelos.

## 7. Pruebas
* Al terminar cada parte importante (modelos, permisos de acceso, CRUD, cálculos, gráficas), escribe automáticamente un test sencillo en `tests.py` con `django.test.TestCase`, sin esperar a que se pida.
* Ejecútalo con `python manage.py test` y explica cómo comprobarlo también a mano en el navegador.
* **Sincronización obligatoria:** si los tests requieren cambios en otros archivos (`admin.py`, `views.py`, `forms.py`, etc.), entrega y aplica a la vez el código completo y actualizado de todos los archivos implicados. Tests e implementación deben quedar sincronizados en la misma tarea, sin cambios pendientes ni versiones parciales.
* Si un test falla, corrige el código, no el test, salvo que expliques por qué el test estaba mal.

## 8. Cierre de cada fase
La fase no se da por terminada hasta completar toda esta lista:
* [ ] `python manage.py test` sin fallos.
* [ ] `python manage.py check` sin errores.
* [ ] `python manage.py makemigrations --check` sin cambios pendientes.
* [ ] Comprobación manual en el navegador de lo que corresponda.
* [ ] Limpieza de imports sin usar, variables huérfanas, código muerto y comentarios desactualizados.
* [ ] Bloque **«Contrato actual»** actualizado contra el código real.
* [ ] Nueva entrada en `PROJECT_LOG.md` terminada con **«Siguiente paso pendiente»**.
* [ ] Abrir `http://127.0.0.1:8000/` y cada prefijo de `config/urls.py` en el navegador: ninguno da 404.

## 9. Documentación y Memoria de Trabajo
Mantén estos archivos en la raíz. Añade los cambios sin borrar el contenido anterior que siga siendo válido.

### `README.md` · Manual técnico y de usuario
* Actualiza solo: requisitos previos, creación y activación del entorno virtual, instalación (`pip install -r requirements.txt`), migraciones (`makemigrations` / `migrate`), carga de datos de prueba (`loaddata`, indicando las credenciales de prueba) y arranque del servidor (`python manage.py runserver`).

### `MEMORIA.md` · Documentación Técnica y Académica Final
* Funciona como la **memoria formal definitiva del proyecto** (orientada a entrega académica). No es un diario, sino una explicación estructurada, limpia y cohesiva de todo el sistema para que sirva como documentación final.
* Documenta la lógica del proyecto paso a paso, el diseño de las tablas (modelos), las vistas y rutas, y la resolución de errores o retos técnicos.
* Sigue la estructura académica: portada, índice, descripción, objetivos y alcance, stack y alternativas, modelo de datos y requisitos.
* Cada requisito funcional debe ser 100 % operativo e indicar: **actor, acción y respuesta del sistema**.
* Incluye una sección **«Manual de instalación»** basada en `README.md` y coherente con él, sin duplicar la redacción.
* Al cerrar cada fase, actualiza este archivo para reflejar la arquitectura global real y asegúrate de que la descripción, el índice, los requisitos y «Vistas y rutas» usan la numeración del mapa de fases.

### `PROJECT_LOG.md` · Bitácora Cronológica y Punto de Partida
* Funciona como el **diario de abordo cronológico** del proyecto para saber exactamente paso a paso qué se ha hecho y desde qué punto exacto se parte en cada sesión.
* Al principio del archivo, mantén un bloque fijo **«Contrato actual»** con los modelos y sus campos, las URLs, las vistas y las plantillas vigentes. Actualízalo al terminar cada fase, comprobándolo contra el código real.
* Registra entradas cronológicas ordenadas con fecha (`DD/MM/AAAA`) o hito, indicando: funcionalidades programadas paso a paso, librerías añadidas, archivos tocados e incidencias resueltas en cada sesión.
* Cada entrada debe terminar obligatoriamente con el apartado **«Siguiente paso pendiente»** para retomar el trabajo sin perder el hilo.

### `requirements.txt` · Dependencias
* Lista solo las librerías de Python del proyecto, con nombre y versión, en UTF-8. Cada vez que se instale un paquete nuevo, actualízalo automáticamente, sin que se solicite.

## Seguridad y Variables de Entorno
- **Uso obligatorio de `python-dotenv`:** Nunca escribas claves secretas, contraseñas o configuraciones sensibles de forma fija ("hardcodeadas") en el código ni en `config/settings.py`.
- **Lectura desde `.env`:** Cualquier configuración sensible o de entorno (como `SECRET_KEY`, `DEBUG` o `DATABASE_URL`) debe cargarse siempre desde el archivo `.env` mediante `os.getenv()`.
- **Valores booleanos:** Al leer `DEBUG` desde el entorno, asegúrate de convertirlo correctamente a booleano (`os.getenv('DEBUG', 'False') == 'True'`).
- **Base de datos:** Configura `DATABASES` en `config/settings.py` para usar SQLite por defecto (`db.sqlite3`), respetando la configuración del entorno si se especifica `DATABASE_URL`.