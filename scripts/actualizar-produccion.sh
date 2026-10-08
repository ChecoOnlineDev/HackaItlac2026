#!/usr/bin/env bash
# Actualiza una instalación existente con FEAT-011: entrada solo por Kepler, permisos nuevos,
# trazabilidad y menú por pestañas. NO carga datos de prueba: solo migra y reparte los permisos.
#
#   ./scripts/actualizar-produccion.sh              respalda, reconstruye la aplicación y verifica
#   ./scripts/actualizar-produccion.sh --simular    solo revisa el estado, sin cambiar nada
#   ./scripts/actualizar-produccion.sh --si         no pregunta si CARGAR_DATOS_PRUEBA=true
#
# Pasos:
#   1. Avisa si CARGAR_DATOS_PRUEBA=true (al arrancar completaría datos de ejemplo) y pide confirmar.
#   2. Respaldo de la base y de los archivos (scripts/respaldo.sh). Si falla, no continúa.
#   3. docker compose up -d --build app. Al arrancar, el contenedor ejecuta `alembic upgrade head`:
#      la migración 0008 agrega los permisos nuevos a los roles ya existentes, por nombre de rol.
#   4. Espera a que la aplicación esté sana y verifica la versión de la base, los permisos nuevos
#      y la consistencia (`python -m app.mantenimiento verificar`).
#
# Los roles que alguien editó a mano conservan sus cambios: la migración solo AGREGA permisos.
#
# Códigos de salida: 0 todo bien, 1 error o verificación fallida.
set -euo pipefail
# shellcheck source=scripts/_comun.sh
. "$(dirname "${BASH_SOURCE[0]}")/_comun.sh"

CLAVES="'bitacora.ver','resguardo.ver','inventario.importar','catalogo.limites','piezas.marcar_estado','acceso.usuarios','acceso.roles','auditoria.ver'"
TOTAL=8
SIMULAR=0
SI=0
for arg in "$@"; do
  case "$arg" in
    --simular) SIMULAR=1 ;;
    --si) SI=1 ;;
    *) fallar "Opción desconocida: $arg (usa --simular o --si)." ;;
  esac
done

preparar
validar_nombre_base "$BASE"
cd "$RAIZ"

echo "== Actualización FEAT-011 =="

if [ "$(leer_env CARGAR_DATOS_PRUEBA false)" = "true" ]; then
  aviso "AVISO: CARGAR_DATOS_PRUEBA=true en .env. Al arrancar, la aplicación completará los datos de ejemplo"
  aviso "(trabajadores, vales, existencias) que falten. Es lo esperado en una demostración; en producción real"
  aviso "ponlo en false."
  if [ "$SI" != "1" ] && [ "$SIMULAR" != "1" ]; then
    read -r -p "¿Continuar? (s/N) " resp
    case "$resp" in s | S | si | SI) ;; *) fallar "Cancelado." ;; esac
  fi
fi

if [ "$SIMULAR" = "1" ]; then
  echo "Modo --simular: no se respalda ni se reconstruye nada."
  echo "Base: $BASE (contenedor $DB_CONTENEDOR)"
  APP="$(contenedor_app)"
  if [ -n "$APP" ]; then
    echo "Versión de la base hoy:"
    docker exec "$APP" alembic current 2>/dev/null || true
  else
    echo "La aplicación no está corriendo."
  fi
  exit 0
fi

echo "1/4 Respaldo..."
"$RAIZ/scripts/respaldo.sh" || fallar "El respaldo no quedó completo. No se actualiza nada."

echo "2/4 Reconstruyendo la aplicación (migra al arrancar)..."
docker compose up -d --build app || fallar "No se pudo reconstruir la aplicación."

echo "3/4 Esperando a que la aplicación esté sana..."
sana=0
for _ in $(seq 1 60); do
  APP="$(contenedor_app)"
  if [ -n "$APP" ] && [ "$(docker inspect -f '{{.State.Health.Status}}' "$APP" 2>/dev/null || true)" = "healthy" ]; then
    sana=1
    break
  fi
  sleep 3
done
[ "$sana" = "1" ] || fallar "La aplicación no quedó sana a tiempo. Revisa: docker compose logs app"

echo "4/4 Verificando..."
fallos=0
actual="$(docker exec "$APP" alembic current 2>/dev/null | grep head || true)"
if printf '%s' "$actual" | grep -q "0008_permisos_feat011"; then
  echo "  [ok] Base en la migración 0008_permisos_feat011."
else
  echo "  [!!] La base no está en la migración 0008 (actual: $actual)."; fallos=$((fallos + 1))
fi

presentes="$(docker exec "$DB_CONTENEDOR" sh -c "MYSQL_PWD=\$MYSQL_ROOT_PASSWORD mysql -uroot -N $BASE -e \"SELECT COUNT(DISTINCT permiso) FROM rol_permiso WHERE permiso IN ($CLAVES);\"" 2>/dev/null | tail -n1 || echo 0)"
if [ "${presentes:-0}" -ge 1 ]; then
  echo "  [ok] $presentes de $TOTAL permisos nuevos ya están asignados a algún rol."
else
  echo "  [!!] Ningún permiso nuevo quedó asignado a un rol."; fallos=$((fallos + 1))
fi

if docker exec "$APP" python -m app.mantenimiento verificar; then
  echo "  [ok] Verificación de consistencia sin diferencias."
else
  echo "  [!!] La verificación de consistencia encontró diferencias (arriba)."; fallos=$((fallos + 1))
fi

[ "$fallos" -eq 0 ] || fallar "La actualización terminó con $fallos problema(s). El respaldo previo está en $RESPALDOS_DIR."
echo "Listo. Revisa /roles: los roles traen los permisos nuevos. Si algún rol editado a mano debe tener otros, actívalos ahí."
