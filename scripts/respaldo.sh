#!/usr/bin/env bash
# Respaldo de la base de datos y de los archivos (firmas y fotos).
#
#   ./scripts/respaldo.sh
#
# Genera en RESPALDOS_DIR (por defecto respaldos/), con la misma marca de fecha:
#   bd-AAAAMMDD-HHMMSS.sql.gz         volcado de la base (mysqldump dentro del contenedor)
#   archivos-AAAAMMDD-HHMMSS.tar.gz   volumen de firmas y fotos
#
# Variables (del entorno o de .env):
#   RESPALDOS_DIR        carpeta de destino                     (por defecto respaldos/)
#   RESPALDOS_CONSERVAR  cuántos respaldos guardar; 0 = todos   (por defecto 0)
#   MYSQL_DATABASE       base a respaldar                       (por defecto imhotep)
#   DB_CONTENEDOR        contenedor de MySQL                    (por defecto imhotep_db)
#   APP_CONTENEDOR       contenedor de la aplicación; si no se indica se busca con docker compose
#   ARCHIVOS_DIR         carpeta local de archivos si no hay contenedor (backend/almacenamiento)
#
# Códigos de salida: 0 completo, 1 error, 2 la base se respaldó pero los archivos no.
set -euo pipefail
# shellcheck source=scripts/_comun.sh
. "$(dirname "${BASH_SOURCE[0]}")/_comun.sh"

preparar
CONSERVAR="$(leer_env RESPALDOS_CONSERVAR 0)"
case "$CONSERVAR" in "" | *[!0-9]*) fallar "RESPALDOS_CONSERVAR debe ser un número entero." ;; esac
validar_nombre_base "$BASE"

MARCA="$(date +%Y%m%d-%H%M%S)"
SQL="$RESPALDOS_DIR/bd-$MARCA.sql.gz"
TAR="$RESPALDOS_DIR/archivos-$MARCA.tar.gz"
TMP_SQL="/tmp/respaldo-$MARCA.sql"
estado=0

echo "== Respaldo $MARCA =="
echo "Base: $BASE (contenedor $DB_CONTENEDOR)"

# 1. Base de datos. La clave de root se toma del entorno del contenedor, no de esta línea.
docker exec "$DB_CONTENEDOR" sh -c '
  set -e
  MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot \
    --single-transaction --routines --triggers --no-tablespaces --set-gtid-purged=OFF \
    --default-character-set=utf8mb4 "$1" > "$2"
  gzip -f "$2"
  gzip -t "$2.gz"
' _ "$BASE" "$TMP_SQL" || { docker exec "$DB_CONTENEDOR" rm -f "$TMP_SQL" "$TMP_SQL.gz" 2>/dev/null || true; fallar "No se pudo volcar la base."; }
docker cp "$DB_CONTENEDOR:$TMP_SQL.gz" "$(ruta_docker "$SQL")" >/dev/null
docker exec "$DB_CONTENEDOR" rm -f "$TMP_SQL.gz"
[ -s "$SQL" ] || fallar "El volcado quedó vacío: $SQL"
echo "Base respaldada:     $SQL ($(wc -c < "$SQL" | tr -d ' ') bytes)"

# 2. Archivos (firmas y fotos): del contenedor de la aplicación o de la carpeta local.
APP="$(contenedor_app)"
LOCAL="$(carpeta_archivos_local)"
if [ -n "$APP" ]; then
  TMP_TAR="/tmp/archivos-$MARCA.tar.gz"
  docker exec "$APP" sh -c 'tar -czf "$1" -C /data/archivos .' _ "$TMP_TAR"
  docker cp "$APP:$TMP_TAR" "$(ruta_docker "$TAR")" >/dev/null
  docker exec "$APP" rm -f "$TMP_TAR"
  echo "Archivos respaldados: $TAR (desde el contenedor de la aplicación)"
elif [ -d "$LOCAL" ]; then
  tar -czf "$TAR" -C "$LOCAL" .
  echo "Archivos respaldados: $TAR (desde $LOCAL)"
else
  aviso "ADVERTENCIA: no hay contenedor de la aplicación corriendo ni carpeta local de archivos."
  aviso "             La base se respaldó, pero NO las firmas ni las fotos. Respaldo INCOMPLETO."
  estado=2
fi

# 3. Retención opcional: se conservan los N respaldos más recientes (por marca).
if [ "$CONSERVAR" -gt 0 ]; then
  mapfile -t viejas < <(ls -1 "$RESPALDOS_DIR"/bd-*.sql.gz 2>/dev/null | sort -r | tail -n +"$((CONSERVAR + 1))")
  for f in "${viejas[@]}"; do
    m="${f##*/bd-}"; m="${m%.sql.gz}"
    rm -f "$f" "$RESPALDOS_DIR/archivos-$m.tar.gz"
    echo "Retención: se borró el respaldo $m"
  done
fi

echo "Listo."
exit "$estado"
