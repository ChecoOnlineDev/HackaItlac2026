# Notificaciones de IMHOTEP

Web Push pertenece a la PWA del supervisor. La app Capacitor no usa este transporte.
Sin VAPID siguen funcionando la aprobación, la lista y el contador de solicitudes.

Para habilitar el envío, generar una vez desde `backend/`:

```powershell
uv run python -m app.modulos.notificaciones.generar_claves
```

Copiar el par generado a `VAPID_CLAVE_PUBLICA` y `VAPID_CLAVE_PRIVADA` en el `.env`
del servidor y configurar `VAPID_CONTACTO` con un correo de administración. La clave privada
no va en Vite ni en el repositorio. Cambiar el par obliga a registrar nuevamente los dispositivos.

El router registra una suscripción por endpoint activo, ligada al usuario y a la familia de
su sesión. Cada envío verifica sesión vigente, usuario y rol activos, versión de sesión,
permiso y almacén asignado. El Administrador no recibe aprobaciones por omisión.

Las tareas de FastAPI se programan después del commit. Abren su propia sesión de base de
datos y no mantienen bloqueos durante la petición de red. El envío tiene un timeout de cinco
segundos y TTL igual al tiempo restante de la solicitud. No hay cola ni reintentos: un error
se guarda sin deshacer la operación; 404/410 revoca el endpoint. Los avisos de resolución y
uso reemplazan el aviso por almacén en silencio. La familia que resolvió no recibe el reemplazo,
pero otro dispositivo del mismo supervisor sí lo recibe.

Los endpoints aceptados son HTTPS de Google FCM, Mozilla, Apple y Microsoft. No se envían
claves a hosts arbitrarios ni se siguen redirecciones. El contenido incluye nombres, número
de artículos y almacén; excluye costos, CURP, NSS, fotos y notas del despacho.

El cifrado `aes128gcm` y la firma VAPID usan la
[biblioteca oficial pywebpush](https://github.com/web-push-libs/pywebpush).
Las pruebas ejercitan el cifrado real y reemplazan únicamente el transporte HTTP; la recepción
con la aplicación cerrada todavía requiere comprobarse en un navegador y equipo reales.
