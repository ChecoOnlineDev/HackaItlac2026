# Funciones compartidas por respaldo.ps1 y restaurar.ps1. No se ejecuta directamente.
#
# Las contraseñas NUNCA viajan en la línea de comandos: mysqldump y mysql se ejecutan dentro del
# contenedor de la base y leen la clave de root de su propio entorno (MYSQL_ROOT_PASSWORD).

$ErrorActionPreference = 'Stop'
$script:Raiz = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Fallar([string]$mensaje) {
    [Console]::Error.WriteLine("ERROR: $mensaje")
    exit 1
}

function Avisar([string]$mensaje) {
    [Console]::Error.WriteLine($mensaje)
}

# Leer-Env NOMBRE [DEFECTO]: la variable del entorno manda; si no, el archivo .env.
function Leer-Env([string]$nombre, [string]$defecto = '') {
    $valor = [Environment]::GetEnvironmentVariable($nombre)
    if ([string]::IsNullOrEmpty($valor)) {
        $archivo = Join-Path $script:Raiz '.env'
        if (Test-Path $archivo) {
            $linea = Get-Content $archivo | Where-Object { $_ -match "^$nombre=" } | Select-Object -Last 1
            if ($linea) { $valor = ($linea -replace "^$nombre=", '').Trim().Trim('"') }
        }
    }
    if ([string]::IsNullOrEmpty($valor)) { return $defecto }
    return $valor
}

# Docker devuelve su código de salida en $LASTEXITCODE; se revisa tras cada llamada importante.
function Docker-Ok([string]$mensaje) {
    if ($LASTEXITCODE -ne 0) { Fallar $mensaje }
}

function Preparar-Respaldos {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fallar 'No se encontró docker.' }
    $script:DbContenedor = Leer-Env 'DB_CONTENEDOR' 'imhotep_db'
    $script:Base = Leer-Env 'MYSQL_DATABASE' 'imhotep'
    $script:UsuarioApp = Leer-Env 'MYSQL_USER' 'imhotep'
    $dir = Leer-Env 'RESPALDOS_DIR' 'respaldos'
    if (-not [System.IO.Path]::IsPathRooted($dir)) { $dir = Join-Path $script:Raiz $dir }
    $script:RespaldosDir = $dir
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $corre = & docker inspect -f '{{.State.Running}}' $script:DbContenedor 2>$null
    if ($corre -ne 'true') { Fallar "El contenedor de la base («$($script:DbContenedor)») no está corriendo." }
}

# El nombre de una base se usa dentro de comandos SQL: solo letras, números y guion bajo.
function Validar-NombreBase([string]$nombre) {
    if ($nombre -notmatch '^[A-Za-z0-9_]+$') {
        Fallar "Nombre de base no válido: «$nombre» (solo letras, números y _)."
    }
}

# Contenedor de la aplicación (donde vive el volumen de archivos); vacío si no corre.
function Contenedor-App {
    $c = Leer-Env 'APP_CONTENEDOR'
    if ([string]::IsNullOrEmpty($c)) {
        Push-Location $script:Raiz
        try { $c = (& docker compose ps -q app 2>$null | Select-Object -First 1) } catch { $c = '' } finally { Pop-Location }
    }
    if ($c) {
        $corre = & docker inspect -f '{{.State.Running}}' $c 2>$null
        if ($corre -eq 'true') { return $c }
    }
    return ''
}

# Carpeta local de archivos (desarrollo): ARCHIVOS_DIR relativa a backend\, o backend\almacenamiento.
function Carpeta-Archivos-Local {
    $d = Leer-Env 'ARCHIVOS_DIR' './almacenamiento'
    if (-not [System.IO.Path]::IsPathRooted($d)) { $d = Join-Path (Join-Path $script:Raiz 'backend') $d }
    return $d
}
