#!/usr/bin/env bash
# Funciones compartidas por respaldo.sh y restaurar.sh. No se ejecuta directamente.
#
# Las contraseñas NUNCA viajan en la línea de comandos: mysqldump y mysql se ejecutan dentro del
# contenedor de la base y leen la clave de root de su propio entorno (MYSQL_ROOT_PASSWORD).

# Git Bash en Windows convierte rutas como /tmp a C:/Program Files/Git/tmp: se desactiva.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Ruta de la máquina para pasársela a docker.exe: en Git Bash /c/Users/x se vuelve C:/Users/x.
ruta_docker() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s' "$1"; fi
}

aviso() { printf '%s\n' "$*" >&2; }
fallar() { aviso "ERROR: $*"; exit 1; }

# leer_env NOMBRE [VALOR_POR_DEFECTO]: la variable del entorno manda; si no, el archivo .env.
leer_env() {
  local nombre="$1" defecto="${2-}" valor="${!1-}"
  if [ -z "$valor" ] && [ -f "$RAIZ/.env" ]; then
    valor="$(grep -E "^${nombre}=" "$RAIZ/.env" | tail -n1 | cut -d= -f2- | tr -d '\r' | sed -e 's/^"//' -e 's/"$//' || true)"
  fi
  printf '%s' "${valor:-$defecto}"
}

preparar() {
  command -v docker >/dev/null 2>&1 || fallar "No se encontró docker."
  DB_CONTENEDOR="$(leer_env DB_CONTENEDOR imhotep_db)"
  BASE="$(leer_env MYSQL_DATABASE imhotep)"
  USUARIO_APP="$(leer_env MYSQL_USER imhotep)"
  RESPALDOS_DIR="$(leer_env RESPALDOS_DIR respaldos)"
  case "$RESPALDOS_DIR" in
    /* | [A-Za-z]:*) ;;
    *) RESPALDOS_DIR="$RAIZ/$RESPALDOS_DIR" ;;
  esac
  mkdir -p "$RESPALDOS_DIR"
  [ "$(docker inspect -f '{{.State.Running}}' "$DB_CONTENEDOR" 2>/dev/null || true)" = "true" ] \
    || fallar "El contenedor de la base («$DB_CONTENEDOR») no está corriendo."
}

# El nombre de una base se usa dentro de comandos SQL: solo letras, números y guion bajo.
validar_nombre_base() {
  case "$1" in
    "" | *[!A-Za-z0-9_]*) fallar "Nombre de base no válido: «$1» (solo letras, números y _)." ;;
  esac
}

# Contenedor de la aplicación (donde vive el volumen de archivos); vacío si no corre.
contenedor_app() {
  local c
  c="$(leer_env APP_CONTENEDOR)"
  if [ -z "$c" ]; then
    c="$(cd "$RAIZ" && docker compose ps -q app 2>/dev/null | head -n1 || true)"
  fi
  if [ -n "$c" ] && [ "$(docker inspect -f '{{.State.Running}}' "$c" 2>/dev/null || true)" = "true" ]; then
    printf '%s' "$c"
  fi
}

# Carpeta local de archivos (desarrollo): ARCHIVOS_DIR relativa a backend/, o backend/almacenamiento.
carpeta_archivos_local() {
  local d
  d="$(leer_env ARCHIVOS_DIR ./almacenamiento)"
  case "$d" in
    /* | [A-Za-z]:*) ;;
    *) d="$RAIZ/backend/$d" ;;
  esac
  printf '%s' "$d"
}
