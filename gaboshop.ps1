# Gaboshop - point d'entree unique pour Docker.
#
#   .\gaboshop.ps1 up              Demarre tout (API, front, Celery, Redis)
#   .\gaboshop.ps1 down            Arrete tout
#   .\gaboshop.ps1 restart         Redemarre
#   .\gaboshop.ps1 rebuild         Reconstruit les images puis redemarre
#   .\gaboshop.ps1 status          Etat des conteneurs
#   .\gaboshop.ps1 logs [service]  Journaux (web, frontend, celery_worker...)
#   .\gaboshop.ps1 test            Tests Django
#   .\gaboshop.ps1 manage <args>   Commande manage.py (ex: createsuperuser)
#   .\gaboshop.ps1 apk             APK Android de test -> builds\android\
#   .\gaboshop.ps1 apk prod https://api.mondomaine.ga
param(
    [Parameter(Position = 0)][string]$Command = "help",
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)][string[]]$Rest
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$TestApps = "payments orders users delivery stores"

function Get-LanIp {
    # Address of this PC on the Wi-Fi/Ethernet network (the one with a gateway)
    $cfg = Get-NetIPConfiguration |
        Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq "Up" } |
        Select-Object -First 1
    if ($cfg) { return @($cfg.IPv4Address)[0].IPAddress }
    return $null
}

function Invoke-Compose {
    docker compose @args
    if ($LASTEXITCODE -ne 0) { throw "docker compose $args a echoue (code $LASTEXITCODE)" }
}

$lanIp = Get-LanIp
if ($lanIp) { $env:GABOSHOP_LAN_IP = $lanIp }

switch ($Command) {
    "up" {
        Invoke-Compose up -d --build
        Write-Host ""
        Write-Host "Site web : http://localhost:5173"
        Write-Host "API      : http://localhost:8000/api/v1/"
        Write-Host "Admin    : http://localhost:8000/admin/"
        if ($lanIp) { Write-Host "Telephone (meme Wi-Fi) : http://${lanIp}:8000" }
    }
    "down"    { Invoke-Compose down }
    "restart" { Invoke-Compose restart }
    "rebuild" { Invoke-Compose up -d --build --force-recreate }
    "status"  { Invoke-Compose ps }
    "logs"    { Invoke-Compose logs -f --tail 100 @Rest }
    "test" {
        Invoke-Compose run --rm web sh -c "python manage.py test $TestApps --noinput"
    }
    "manage" {
        Invoke-Compose run --rm web python manage.py @Rest
    }
    "apk" {
        $mode = if ($Rest.Count -ge 1) { $Rest[0] } else { "dev" }
        if ($mode -eq "prod") {
            if ($Rest.Count -lt 2 -or -not $Rest[1].StartsWith("https://")) {
                throw "Usage : .\gaboshop.ps1 apk prod https://api.mondomaine.ga"
            }
            $env:APK_API_URL = $Rest[1]
        } else {
            if (-not $lanIp) { throw "Adresse reseau introuvable : connectez le PC au Wi-Fi." }
            $env:APK_API_URL = "http://${lanIp}:8000"
        }
        $env:APK_MODE = $mode
        New-Item -ItemType Directory -Force builds\android | Out-Null
        Invoke-Compose --profile android build android
        Invoke-Compose --profile android run --rm android
        if ($mode -eq "dev") {
            Write-Host ""
            Write-Host "1. Lancez l'API si besoin : .\gaboshop.ps1 up"
            Write-Host "2. Copiez builds\android\gaboshop-dev.apk sur le telephone et installez-le"
            Write-Host "   (le telephone doit etre sur le meme Wi-Fi que ce PC : $lanIp)"
        }
    }
    default {
        Get-Content $PSCommandPath | Select-Object -Skip 1 -First 12 | ForEach-Object { $_ -replace '^# ?', '' }
    }
}
