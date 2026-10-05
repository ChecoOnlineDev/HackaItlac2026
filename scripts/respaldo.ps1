# Respaldo de la base de datos y de los archivos (firmas y fotos).
#
#   .\scripts\respaldo.ps1
#
# Genera en RESPALDOS_DIR (por defecto respaldos\), con la misma marca de fecha:
#   bd-AAAAMMDD-HHMMSS.sql.gz         volcado de la base (mysqldump dentro del contenedor)
#   archivos-AAAAMMDD-HHMMSS.tar.gz   volumen de firmas y fotos
#
# Variables (del entorno o de .env): RESPALDOS_DIR, RESPALDOS_CONSERVAR (0 = todos), MYSQL_DATABASE,
# DB_CONTENEDOR, APP_CONTENEDOR, ARCHIVOS_DIR. Mismo significado que en respaldo.sh.
#
# Códigos de salida: 0 completo, 1 error, 2 la base se respaldó pero los archivos no.
. (Join-Path $PSScriptRoot '_comun.ps1')

Preparar-Respaldos
$conservar = Leer-Env 'RESPALDOS_CONSERVAR' '0'
if ($conservar -notmatch '^[0-9]+$') { Fallar 'RESPALDOS_CONSERVAR debe ser un número entero.' }
$conservar = [int]$conservar
Validar-NombreBase $script:Base

$marca = Get-Date -Format 'yyyyMMdd-HHmmss'
$sql = Join-Path $script:RespaldosDir "bd-$marca.sql.gz"
$tar = Join-Path $script:RespaldosDir "archivos-$marca.tar.gz"
$tmpSql = "/tmp/respaldo-$marca.sql"
$estado = 0

Write-Host "== Respaldo $marca =="
Write-Host "Base: $($script:Base) (contenedor $($script:DbContenedor))"

# 1. Base de datos. La clave de root se toma del entorno del contenedor, no de esta línea.
$orden = 'MYSQL_PWD=$MYSQL_ROOT_PASSWORD mysqldump -uroot --single-transaction --routines --triggers ' +
    "--no-tablespaces --set-gtid-purged=OFF --default-character-set=utf8mb4 $($script:Base) > $tmpSql " +
    "&& gzip -f $tmpSql && gzip -t $tmpSql.gz"
& docker exec $script:DbContenedor sh -c $orden
if ($LASTEXITCODE -ne 0) {
    & docker exec $script:DbContenedor rm -f $tmpSql "$tmpSql.gz" | Out-Null
    Fallar 'No se pudo volcar la base.'
}
& docker cp "$($script:DbContenedor):$tmpSql.gz" $sql | Out-Null
Docker-Ok 'No se pudo copiar el volcado fuera del contenedor.'
& docker exec $script:DbContenedor rm -f "$tmpSql.gz" | Out-Null
if (-not (Test-Path $sql) -or (Get-Item $sql).Length -eq 0) { Fallar "El volcado quedó vacío: $sql" }
Write-Host "Base respaldada:      $sql ($((Get-Item $sql).Length) bytes)"

# 2. Archivos (firmas y fotos): del contenedor de la aplicación o de la carpeta local.
$app = Contenedor-App
$local = Carpeta-Archivos-Local
if ($app) {
    $tmpTar = "/tmp/archivos-$marca.tar.gz"
    & docker exec $app sh -c "tar -czf $tmpTar -C /data/archivos ."
    Docker-Ok 'No se pudieron empacar los archivos en el contenedor de la aplicación.'
    & docker cp "$($app):$tmpTar" $tar | Out-Null
    Docker-Ok 'No se pudieron copiar los archivos fuera del contenedor.'
    & docker exec $app rm -f $tmpTar | Out-Null
    Write-Host "Archivos respaldados: $tar (desde el contenedor de la aplicación)"
} elseif (Test-Path $local) {
    & tar -czf $tar -C $local .
    Docker-Ok 'No se pudieron empacar los archivos locales.'
    Write-Host "Archivos respaldados: $tar (desde $local)"
} else {
    Avisar 'ADVERTENCIA: no hay contenedor de la aplicación corriendo ni carpeta local de archivos.'
    Avisar '             La base se respaldó, pero NO las firmas ni las fotos. Respaldo INCOMPLETO.'
    $estado = 2
}

# 3. Retención opcional: se conservan los N respaldos más recientes (por marca).
if ($conservar -gt 0) {
    $viejos = Get-ChildItem $script:RespaldosDir -Filter 'bd-*.sql.gz' |
        Sort-Object Name -Descending | Select-Object -Skip $conservar
    foreach ($f in $viejos) {
        $m = $f.Name -replace '^bd-', '' -replace '\.sql\.gz$', ''
        Remove-Item -Force $f.FullName
        Remove-Item -Force (Join-Path $script:RespaldosDir "archivos-$m.tar.gz") -ErrorAction SilentlyContinue
        Write-Host "Retención: se borró el respaldo $m"
    }
}

Write-Host 'Listo.'
exit $estado
