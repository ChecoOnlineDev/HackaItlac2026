# Restaura un respaldo hecho con respaldo.ps1 (o respaldo.sh: mismo formato).
#
#   .\scripts\restaurar.ps1                          el respaldo más reciente, sobre la base de producción
#   .\scripts\restaurar.ps1 20261005-021500          el de esa marca
#   .\scripts\restaurar.ps1 --base imhotep_prueba    en OTRA base (no toca la de producción)
#
# Opciones (acepta --base o -Base, --si o -Si):
#   --base NOMBRE   restaura en esa base (se crea si no existe). Con --base los archivos NO se meten
#                   al volumen de la aplicación: se extraen en respaldos\restaurado-MARCA\ para revisarlos.
#   --si            no pregunta (para automatizar; úselo con cuidado).
#   MARCA           marca del respaldo (AAAAMMDD-HHMMSS). Sin ella se usa el más reciente.
#
# Sobrescribe: antes de tocar la base de producción se pide escribir su nombre. Después de restaurar:
#   cd backend; uv run python -m app.mantenimiento verificar
. (Join-Path $PSScriptRoot '_comun.ps1')

$destino = ''
$marca = ''
$sinPregunta = $false
$i = 0
while ($i -lt $args.Count) {
    $a = [string]$args[$i]
    switch -Regex ($a.ToLower()) {
        '^--?base$' {
            if ($i + 1 -ge $args.Count) { Fallar '--base necesita un nombre.' }
            $destino = [string]$args[$i + 1]; $i += 2; continue
        }
        '^--?si$' { $sinPregunta = $true; $i += 1; continue }
        '^-' { Fallar "Opción desconocida: $a" }
        default { $marca = $a; $i += 1; continue }
    }
}

Preparar-Respaldos
$enProduccion = $true
if ($destino -ne '' -and $destino -ne $script:Base) { $enProduccion = $false }
if ($destino -eq '') { $destino = $script:Base }
Validar-NombreBase $destino

if ($marca -eq '') {
    $ultimo = Get-ChildItem $script:RespaldosDir -Filter 'bd-*.sql.gz' -ErrorAction SilentlyContinue |
        Sort-Object Name | Select-Object -Last 1
    if (-not $ultimo) { Fallar "No hay respaldos en $($script:RespaldosDir)." }
    $marca = $ultimo.Name -replace '^bd-', '' -replace '\.sql\.gz$', ''
}
$sql = Join-Path $script:RespaldosDir "bd-$marca.sql.gz"
$tar = Join-Path $script:RespaldosDir "archivos-$marca.tar.gz"
if (-not (Test-Path $sql)) { Fallar "No existe $sql" }

Write-Host "== Restauración del respaldo $marca =="
Write-Host "Base de datos destino: $destino"
if ($enProduccion) {
    Write-Host 'ATENCIÓN: es la base de producción. Se SOBRESCRIBEN sus tablas y los archivos del volumen.'
}
if (-not $sinPregunta) {
    if ($enProduccion) {
        $r = Read-Host "Para continuar escriba el nombre de la base («$destino»)"
        if ($r -ne $destino) { Fallar 'Cancelado: no coincide. No se cambió nada.' }
    } else {
        $r = Read-Host "¿Restaurar en «$destino»? (escriba si)"
        if ($r -ne 'si') { Fallar 'Cancelado. No se cambió nada.' }
    }
}

# 1. Base de datos. La clave de root se toma del entorno del contenedor.
$tmp = "/tmp/restaurar-$marca.sql.gz"
& docker cp $sql "$($script:DbContenedor):$tmp" | Out-Null
Docker-Ok 'No se pudo copiar el respaldo al contenedor.'
$crear = "CREATE DATABASE IF NOT EXISTS ``$destino`` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;`n" +
    "GRANT ALL ON ``$destino``.* TO ``$($script:UsuarioApp)``@``%``;`n"
$crear | & docker exec -i $script:DbContenedor sh -c 'MYSQL_PWD=$MYSQL_ROOT_PASSWORD mysql -uroot'
Docker-Ok 'No se pudo crear la base de destino.'
$cargar = "gunzip -c $tmp | MYSQL_PWD=`$MYSQL_ROOT_PASSWORD mysql -uroot --default-character-set=utf8mb4 $destino"
& docker exec $script:DbContenedor sh -c $cargar
if ($LASTEXITCODE -ne 0) {
    & docker exec $script:DbContenedor rm -f $tmp | Out-Null
    Fallar 'No se pudo restaurar la base.'
}
& docker exec $script:DbContenedor rm -f $tmp | Out-Null
Write-Host "Base restaurada en «$destino»."

# 2. Archivos.
if (-not (Test-Path $tar)) {
    Avisar "ADVERTENCIA: no hay $tar; solo se restauró la base."
} elseif ($enProduccion) {
    $app = Contenedor-App
    $local = Carpeta-Archivos-Local
    if ($app) {
        & docker cp $tar "$($app):/tmp/restaurar-archivos.tar.gz" | Out-Null
        Docker-Ok 'No se pudieron copiar los archivos al contenedor.'
        & docker exec $app sh -c 'tar -xzf /tmp/restaurar-archivos.tar.gz -C /data/archivos && rm -f /tmp/restaurar-archivos.tar.gz'
        Docker-Ok 'No se pudieron extraer los archivos en el contenedor.'
        Write-Host 'Archivos restaurados en el volumen de la aplicación.'
    } else {
        New-Item -ItemType Directory -Force -Path $local | Out-Null
        & tar -xzf $tar -C $local
        Docker-Ok 'No se pudieron extraer los archivos.'
        Write-Host "Archivos restaurados en $local."
    }
} else {
    $afuera = Join-Path (Join-Path $script:RespaldosDir "restaurado-$marca") 'archivos'
    New-Item -ItemType Directory -Force -Path $afuera | Out-Null
    & tar -xzf $tar -C $afuera
    Docker-Ok 'No se pudieron extraer los archivos.'
    Write-Host "Archivos extraídos en $afuera (el volumen de la aplicación no se tocó)."
}

Write-Host "Listo. Verifique con: cd backend; `$env:MYSQL_DATABASE='$destino'; uv run python -m app.mantenimiento verificar"
