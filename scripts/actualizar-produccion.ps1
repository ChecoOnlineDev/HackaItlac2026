# Actualiza una instalación existente con FEAT-011: entrada solo por Kepler, permisos nuevos,
# trazabilidad y menú por pestañas. NO carga datos de prueba: solo migra y reparte los permisos.
#
#   .\scripts\actualizar-produccion.ps1            respalda, reconstruye la aplicación y verifica
#   .\scripts\actualizar-produccion.ps1 -Simular   solo revisa el estado, sin cambiar nada
#   .\scripts\actualizar-produccion.ps1 -Si         no pregunta si CARGAR_DATOS_PRUEBA=true
#
# Pasos:
#   1. Avisa si CARGAR_DATOS_PRUEBA=true (al arrancar completaría datos de ejemplo) y pide confirmar.
#   2. Respaldo de la base y de los archivos (scripts\respaldo.ps1). Si falla, no continúa.
#   3. docker compose up -d --build app. Al arrancar, el contenedor ejecuta `alembic upgrade head`:
#      la migración 0008 agrega los permisos nuevos a los roles ya existentes, por nombre de rol.
#   4. Espera a que la aplicación esté sana y verifica la versión de la base, los permisos nuevos
#      y la consistencia (`python -m app.mantenimiento verificar`).
#
# Los roles que alguien editó a mano conservan sus cambios: la migración solo AGREGA permisos.
# Para volver los cinco roles a su configuración de fábrica (borra los cambios hechos en /roles):
#   docker compose exec app python -m app.datos_prueba --restablecer-roles   (carga también datos de prueba; no recomendado en producción)
#
# Códigos de salida: 0 todo bien, 1 error o verificación fallida.
param([switch]$Simular, [switch]$Si)
. (Join-Path $PSScriptRoot '_comun.ps1')
# Los errores de docker se revisan con $LASTEXITCODE; así su salida de error no se muestra como excepción.
$ErrorActionPreference = 'Continue'

$claves = @('bitacora.ver', 'resguardo.ver', 'inventario.importar', 'catalogo.limites',
    'piezas.marcar_estado', 'acceso.usuarios', 'acceso.roles', 'auditoria.ver')

Preparar-Respaldos
Validar-NombreBase $script:Base
Push-Location $script:Raiz
try {
    Write-Host '== Actualización FEAT-011 =='

    if ((Leer-Env 'CARGAR_DATOS_PRUEBA' 'false') -eq 'true') {
        Avisar 'AVISO: CARGAR_DATOS_PRUEBA=true en .env. Al arrancar, la aplicación completará los datos de ejemplo'
        Avisar '(trabajadores, vales, existencias) que falten. Es lo esperado en una demostración; en producción real'
        Avisar 'ponlo en false.'
        if (-not $Si -and -not $Simular) {
            $resp = Read-Host '¿Continuar? (s/N)'
            if ($resp -notmatch '^(s|si|sí)$') { Fallar 'Cancelado.' }
        }
    }

    if ($Simular) {
        Write-Host 'Modo -Simular: no se respalda ni se reconstruye nada.'
        Write-Host "Base: $($script:Base) (contenedor $($script:DbContenedor))"
        $app = Contenedor-App
        if ($app) {
            Write-Host 'Versión de la base hoy:'
            & docker exec $app alembic current 2>$null
        } else {
            Write-Host 'La aplicación no está corriendo.'
        }
        exit 0
    }

    Write-Host '1/4 Respaldo...'
    & (Join-Path $PSScriptRoot 'respaldo.ps1')
    if ($LASTEXITCODE -ne 0) { Fallar 'El respaldo no quedó completo. No se actualiza nada.' }

    Write-Host '2/4 Reconstruyendo la aplicación (migra al arrancar)...'
    & docker compose up -d --build app
    Docker-Ok 'No se pudo reconstruir la aplicación.'

    Write-Host '3/4 Esperando a que la aplicación esté sana...'
    $sana = $false
    for ($i = 0; $i -lt 60; $i++) {
        $app = Contenedor-App
        if ($app) {
            $estado = & docker inspect -f '{{.State.Health.Status}}' $app 2>$null
            if ($estado -eq 'healthy') { $sana = $true; break }
        }
        Start-Sleep -Seconds 3
    }
    if (-not $sana) { Fallar 'La aplicación no quedó sana a tiempo. Revisa: docker compose logs app' }

    Write-Host '4/4 Verificando...'
    $fallos = 0
    $actual = (& docker exec $app alembic current 2>$null | Select-String 'head') -join ''
    if ($actual -match '0008_permisos_feat011') { Write-Host '  [ok] Base en la migración 0008_permisos_feat011.' }
    else { Write-Host "  [!!] La base no está en la migración 0008 (actual: $actual)."; $fallos++ }

    $lista = ($claves | ForEach-Object { "'$_'" }) -join ','
    $consulta = "SELECT COUNT(DISTINCT permiso) FROM rol_permiso WHERE permiso IN ($lista);"
    $orden = 'MYSQL_PWD=$MYSQL_ROOT_PASSWORD mysql -uroot -N ' + $script:Base + ' -e "' + $consulta + '"'
    $presentes = (& docker exec $script:DbContenedor sh -c $orden 2>$null | Select-Object -Last 1)
    if ($presentes -ge 1) { Write-Host "  [ok] $presentes de $($claves.Count) permisos nuevos ya están asignados a algún rol." }
    else { Write-Host '  [!!] Ningún permiso nuevo quedó asignado a un rol.'; $fallos++ }

    & docker exec $app python -m app.mantenimiento verificar
    if ($LASTEXITCODE -eq 0) { Write-Host '  [ok] Verificación de consistencia sin diferencias.' }
    else { Write-Host '  [!!] La verificación de consistencia encontró diferencias (arriba).'; $fallos++ }

    if ($fallos -gt 0) { Fallar "La actualización terminó con $fallos problema(s). El respaldo previo está en $($script:RespaldosDir)." }
    Write-Host 'Listo. Revisa /roles: los roles traen los permisos nuevos. Si algún rol editado a mano debe tener otros, actívalos ahí.'
}
finally {
    Pop-Location
}
