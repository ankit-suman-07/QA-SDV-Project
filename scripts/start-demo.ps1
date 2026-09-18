#!/usr/bin/env pwsh
# Windows-native equivalent of start-demo.sh.
# Run from anywhere: .\scripts\start-demo.ps1

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $RootDir ".demo-runtime"
$LogDir = Join-Path $RuntimeDir "logs"
$Python = Join-Path $RootDir ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: Required command not found: $Name"
        exit 1
    }
}

function Wait-ForUrl {
    param(
        [string]$Name,
        [string]$Url,
        [int]$Attempts = 30,
        [string]$User,
        [string]$Password
    )

    for ($i = 1; $i -le $Attempts; $i++) {
        try {
            if ($User) {
                $cred = New-Object PSCredential($User, (ConvertTo-SecureString $Password -AsPlainText -Force))
                $resp = Invoke-WebRequest -Uri $Url -Credential $cred -UseBasicParsing -TimeoutSec 5
            } else {
                $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            }
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) {
                Write-Host "[ready] $Name"
                return $true
            }
        } catch {
            # not ready yet, keep polling
        }
        Start-Sleep -Seconds 1
    }

    Write-Host "ERROR: $Name did not become ready: $Url"
    return $false
}

function Start-BackgroundProcess {
    param(
        [string]$Name,
        [string]$PidFile,
        [string]$LogFile,
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory = $RootDir,
        [hashtable]$Environment = @{}
    )

    if (Test-Path $PidFile) {
        $existingPid = Get-Content $PidFile
        if (Get-Process -Id $existingPid -ErrorAction SilentlyContinue) {
            Write-Host "[running] $Name (PID $existingPid)"
            return
        }
    }

    foreach ($key in $Environment.Keys) {
        Set-Item -Path "env:$key" -Value $Environment[$key]
    }

    $proc = Start-Process -FilePath $FilePath -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError "$LogFile.err" `
        -WindowStyle Hidden -PassThru

    $proc.Id | Out-File -FilePath $PidFile -Encoding ascii
    Write-Host "[started] $Name (PID $($proc.Id))"
}

Require-Command curl.exe
Require-Command docker

if (-not (Test-Path $Python)) {
    Write-Host "ERROR: Python virtual environment not found."
    Write-Host "Create it at $RootDir\.venv and install dependencies:"
    Write-Host "  python -m venv .venv"
    Write-Host "  .venv\Scripts\Activate.ps1"
    Write-Host "  pip install -r vehicle-simulator\requirements.txt"
    exit 1
}

Write-Host "Checking external Eclipse Ditto..."

if (-not (Wait-ForUrl -Name "Eclipse Ditto" -Url "http://localhost:8080/api/2/things" -Attempts 1 -User "ditto" -Password "ditto")) {
    Write-Host "ERROR: Eclipse Ditto is not available on port 8080."
    Write-Host "Start the external Ditto Docker deployment first."
    exit 1
}

Write-Host "Starting Kuksa and vehicle simulator..."

docker compose -f "$RootDir\vehicle-simulator\docker-compose.yml" up -d --build

Wait-ForUrl -Name "Vehicle simulator" -Url "http://localhost:8090/health" -Attempts 45 | Out-Null

Write-Host "Starting Kuksa-to-Ditto bridge..."

Start-BackgroundProcess -Name "Kuksa-to-Ditto bridge" `
    -PidFile "$RuntimeDir\bridge.pid" `
    -LogFile "$LogDir\bridge.log" `
    -FilePath $Python `
    -ArgumentList @("$RootDir\ditto\scripts\interim-kuksa-to-ditto-bridge.py") `
    -Environment @{
        PYTHONUNBUFFERED = "1"
        EXPERIMENT_ID = "demo-runtime"
        EXPERIMENT_EVENT_LIMIT = "100000"
        PUBLISH_INTERVAL_SECONDS = "1"
        SIMULATOR_CONTROL_URL = "http://localhost:8090"
    }

Write-Host "Starting Spring Boot backend..."

$backendUp = $false
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:8082/actuator/health" -UseBasicParsing -TimeoutSec 5
    $backendUp = $resp.StatusCode -eq 200
} catch {}

if ($backendUp) {
    Write-Host "[running] Spring Boot backend"
} else {
    $env:SERVER_PORT = "8082"
    $env:SDV_SIMULATOR_MODE = "http"
    $env:SIMULATOR_BASE_URL = "http://localhost:8090"

    $proc = Start-Process -FilePath "$RootDir\backend\mvnw.cmd" -ArgumentList @("spring-boot:run") `
        -WorkingDirectory "$RootDir\backend" `
        -RedirectStandardOutput "$LogDir\backend.log" `
        -RedirectStandardError "$LogDir\backend.log.err" `
        -WindowStyle Hidden -PassThru

    $proc.Id | Out-File -FilePath "$RuntimeDir\backend.pid" -Encoding ascii

    Wait-ForUrl -Name "Spring Boot backend" -Url "http://localhost:8082/actuator/health" -Attempts 60 | Out-Null
}

Write-Host "Starting frontend..."

$frontendUp = $false
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:3000/index.html" -UseBasicParsing -TimeoutSec 5
    $frontendUp = $resp.StatusCode -eq 200
} catch {}

if ($frontendUp) {
    Write-Host "[running] Frontend"
} else {
    Start-BackgroundProcess -Name "Frontend" `
        -PidFile "$RuntimeDir\frontend.pid" `
        -LogFile "$LogDir\frontend.log" `
        -FilePath $Python `
        -ArgumentList @("-m", "http.server", "3000", "--directory", "$RootDir\frontend")

    Wait-ForUrl -Name "Frontend" -Url "http://localhost:3000/index.html" -Attempts 15 | Out-Null
}

Write-Host ""
Write-Host "SDV demo services are ready:"
Write-Host "  Frontend:  http://localhost:3000/index.html"
Write-Host "  Backend:   http://localhost:8082/actuator/health"
Write-Host "  Simulator: http://localhost:8090/health"
Write-Host "  Ditto:     http://localhost:8080/api/2/things/sdv:vehicle-001"
Write-Host ""
Write-Host "Logs:"
Write-Host "  $LogDir\bridge.log"
Write-Host "  $LogDir\backend.log"
Write-Host "  $LogDir\frontend.log"
