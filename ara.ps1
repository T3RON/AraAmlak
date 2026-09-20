# ara.ps1 - Windows PowerShell equivalent of Makefile for Ara Amlak
# Usage: .\ara.ps1 <target>
# Targets: up, down, test, lint, migrate, shell, seed, build, logs, ps, help

param(
    [Parameter(Position=0)]
    [string]$Target = "help"
)

$ErrorActionPreference = "Stop"

# Ensure UTF-8 output for Farsi text in terminals that support it
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Run($cmd) {
    Write-Host "> $cmd" -ForegroundColor Cyan
    Invoke-Expression $cmd
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

switch ($Target) {
    "up"      { Run "docker compose up --build" }
    "down"    { Run "docker compose down" }
    "build"   { Run "docker compose build" }
    "logs"    { Run "docker compose logs -f web" }
    "ps"      { Run "docker compose ps" }
    "test"    { Run "docker compose run --rm web pytest -v --tb=short" }
    "lint"    { Run "docker compose run --rm web ruff check ." }
    "migrate" { Run "docker compose run --rm web python manage.py migrate --noinput" }
    "shell"   { Run "docker compose run --rm web python manage.py shell" }
    "seed"    { Run "docker compose run --rm web python manage.py seed" }
    "help" {
        Write-Host ""
        Write-Host "  Ara Amlak -- available targets:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  .\ara.ps1 up        start all services (build + docker compose up)"
        Write-Host "  .\ara.ps1 down      stop and remove containers"
        Write-Host "  .\ara.ps1 test      run pytest test suite"
        Write-Host "  .\ara.ps1 lint      run ruff linter"
        Write-Host "  .\ara.ps1 migrate   run Django migrations"
        Write-Host "  .\ara.ps1 shell     open Django shell"
        Write-Host "  .\ara.ps1 seed      load initial seed data"
        Write-Host "  .\ara.ps1 build     rebuild Docker images"
        Write-Host "  .\ara.ps1 logs      tail web service logs"
        Write-Host "  .\ara.ps1 ps        show service status"
        Write-Host ""
        Write-Host "  Tip: on Linux/macOS/WSL/Git Bash you can also use: make <target>" -ForegroundColor DarkGray
        Write-Host ""
    }
    default {
        Write-Host "Unknown target: '$Target'" -ForegroundColor Red
        Write-Host "Run '.\ara.ps1 help' to see available targets."
        exit 1
    }
}
