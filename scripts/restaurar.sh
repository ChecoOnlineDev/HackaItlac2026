#!/usr/bin/env bash
# Restaura un respaldo hecho con respaldo.sh.
#
#   ./scripts/restaurar.sh                         el respaldo más reciente, sobre la base de producción
#   ./scripts/restaurar.sh 20261005-021500         el de esa marca
#   ./scripts/restaurar.sh --base imhotep_prueba   en OTRA base (no toca la de producción)
#
# Opciones:
#   --base NOMBRE   restaura en esa base (se crea si no existe) en lugar de la base de producción.
#                   Con --base los archivos NO se meten al volumen de la aplicación: se extraen en
#                   respaldos/restaurado-MARCA/ para revisarlos.
#   --si            no pregunta (para automatizar; úselo con cuidado).
#   MARCA           marca del respaldo (AAAAMMDD-HHMMSS). Sin ella se usa el más reciente.
#
# Sobrescribe: antes de tocar la base de producción se pide escribir su nombre. Haga un respaldo
# nuevo antes si no está seguro. Después de restaurar corra:
#   cd backend && uv run python -m app.mantenimiento verificar
set -euo pipefail
# shellcheck source=scripts/_comun.sh
. "$(dirname "${BASH_SOURCE[0]}")/_comun.sh"

DESTINO=""
MARCA=""
SIN_PREGUNTA=0
while [ $# -gt 0 ]; do
  case "$1" in
    --base) [ $# -ge 2 ] || fallar "--base necesita un nombre."; DESTINO="$2"; shift 2 ;;
    --si) SIN_PREGUNTA=1; shift ;;
    -h | --help) sed -n '2,19p' "$0"; exit 0 ;;
    -*) fallar "Opción desconocida: $1" ;;
    *) MARCA="$1"; shift ;;
  esac
done

preparar
EN_PRODUCCION=1
if [ -n "$DESTINO" ] && [ "$DESTINO" != "$BASE" ]; then
  EN_PRODUCCION=0
fi
[ -n "$DESTINO" ] || DESTINO="$BASE"
validar_nombre_base "$DESTINO"

if [ -z "$MARCA" ]; then
  ultimo="$(ls -1 "$RESPALDOS_DIR"/bd-*.sql.gz 2>/dev/null | sort | tail -n1 || true)"
  [ -n "$ultimo" ] || fallar "No hay respaldos en $RESPALDOS_DIR."
  MARCA="${ultimo##*/bd-}"; MARCA="${MARCA%.sql.gz}"
fi
SQL="$RESPALDOS_DIR/bd-$MARCA.sql.gz"
TAR="$RESPALDOS_DIR/archivos-$MARCA.tar.gz"
[ -f "$SQL" ] || fallar "No existe $SQL"
gzip -t "$SQL" || fallar "El respaldo $SQL está dañado."

echo "== Restauración del respaldo $MARCA =="
echo "Base de datos destino: $DESTINO"
if [ "$EN_PRODUCCION" = 1 ]; then
  echo "ATENCIÓN: es la base de producción. Se SOBRESCRIBEN sus tablas y los archivos del volumen."
fi
if [ "$SIN_PREGUNTA" != 1 ]; then
  if [ "$EN_PRODUCCION" = 1 ]; then
    printf 'Para continuar escriba el nombre de la base («%s»): ' "$DESTINO"
    read -r respuesta || respuesta=""
    [ "$respuesta" = "$DESTINO" ] || fallar "Cancelado: no coincide. No se cambió nada."
  else
    printf '¿Restaurar en «%s»? (escriba si): ' "$DESTINO"
    read -r respuesta || respuesta=""
    [ "$respuesta" = "si" ] || fallar "Cancelado. No se cambió nada."
  fi
fi

# 1. Base de datos. La clave de root se toma del entorno del contenedor.
TMP_SQL="/tmp/restaurar-$MARCA.sql.gz"
docker cp "$(ruta_docker "$SQL")" "$DB_CONTENEDOR:$TMP_SQL" >/dev/null
docker exec "$DB_CONTENEDOR" sh -c '
  set -e
  export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"
  mysql -uroot -e "CREATE DATABASE IF NOT EXISTS \`$1\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
  mysql -uroot -e "GRANT ALL ON \`$1\`.* TO \`$3\`@\`%\`"
  gunzip -c "$2" | mysql -uroot --default-character-set=utf8mb4 "$1"
' _ "$DESTINO" "$TMP_SQL" "$USUARIO_APP" || { docker exec "$DB_CONTENEDOR" rm -f "$TMP_SQL" 2>/dev/null || true; fallar "No se pudo restaurar la base."; }
docker exec "$DB_CONTENEDOR" rm -f "$TMP_SQL"
echo "Base restaurada en «$DESTINO»."

# 2. Archivos.
if [ ! -f "$TAR" ]; then
  aviso "ADVERTENCIA: no hay $TAR; solo se restauró la base."
elif [ "$EN_PRODUCCION" = 1 ]; then
  APP="$(contenedor_app)"
  LOCAL="$(carpeta_archivos_local)"
  if [ -n "$APP" ]; then
    docker cp "$(ruta_docker "$TAR")" "$APP:/tmp/restaurar-archivos.tar.gz" >/dev/null
    docker exec "$APP" sh -c 'tar -xzf /tmp/restaurar-archivos.tar.gz -C /data/archivos && rm -f /tmp/restaurar-archivos.tar.gz'
    echo "Archivos restaurados en el volumen de la aplicación."
  else
    mkdir -p "$LOCAL"
    tar -xzf "$TAR" -C "$LOCAL"
    echo "Archivos restaurados en $LOCAL."
  fi
else
  AFUERA="$RESPALDOS_DIR/restaurado-$MARCA/archivos"
  mkdir -p "$AFUERA"
  tar -xzf "$TAR" -C "$AFUERA"
  echo "Archivos extraídos en $AFUERA (el volumen de la aplicación no se tocó)."
fi

echo "Listo. Verifique con: (cd backend && MYSQL_DATABASE=$DESTINO uv run python -m app.mantenimiento verificar)"
