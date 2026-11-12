# Decisiones finales del proyecto

- Proyecto Django con SQLite, configurado localmente mediante `.env`; el
  archivo real de entorno, la base de datos local y `venv/` están excluidos de
  Git.
- Las dependencias se congelaron desde el entorno virtual en
  `requirements.txt` con `pip freeze`.
- Los roles principales son grupos Django `Alumno` y `Profesor`. La capacidad
  de gestión se centraliza en `puede_gestionar_academico`: Profesor o
  superusuario. Un alumno solo consulta datos vinculados a su propia cuenta.
- El comando `python manage.py seed_datos [N] [--limpiar]` genera datos de
  prueba y credenciales aleatorias; las contraseñas se consultan en la salida
  de cada ejecución y no se guardan en la documentación.
- La suite verificada en Fase 10 contiene 77 pruebas. `manage.py check` y
  `makemigrations --check` finalizaron sin errores ni cambios pendientes.
- El despliegue aún requiere definir dominio, terminación HTTPS y backend de
  correo. `check --deploy` detecta esas opciones de producción pendientes; no
  se configuraron valores supuestos.
- La comprobación visual autenticada de los paneles y las descargas sigue como
  tarea pendiente. El push a GitHub corresponde al usuario.