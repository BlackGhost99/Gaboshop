#!/usr/bin/env pwsh
# Docker Restart avec Static Files Fix
# Résout l'erreur 500 du login admin

Write-Host "===================================" -ForegroundColor Green
Write-Host "🔧 REDÉMARRAGE DOCKER - STATICFILES FIX" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host ""

Set-Location "D:\Expériences\Gaboshop"

Write-Host "1️⃣  Arrêter les conteneurs..." -ForegroundColor Yellow
docker-compose down
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "2️⃣  Reconstruire les images..." -ForegroundColor Yellow
docker-compose build --no-cache web frontend

Write-Host ""
Write-Host "3️⃣  Démarrer les services..." -ForegroundColor Yellow
docker-compose up -d

Write-Host ""
Write-Host "4️⃣  Attendre le démarrage des services..." -ForegroundColor Yellow
Start-Sleep -Seconds 8

Write-Host ""
Write-Host "5️⃣  État des conteneurs:" -ForegroundColor Yellow
docker-compose ps

Write-Host ""
Write-Host "6️⃣  Logs du service web (dernières 20 lignes):" -ForegroundColor Yellow
docker-compose logs --tail 20 web

Write-Host ""
Write-Host "=== ✅ REDÉMARRAGE TERMINÉ ===" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Services disponibles:" -ForegroundColor Cyan
Write-Host "   • API Backend:    http://localhost:8000" -ForegroundColor Cyan
Write-Host "   • Admin Panel:    http://localhost:8000/admin" -ForegroundColor Cyan
Write-Host "   • Frontend:       http://localhost:5173" -ForegroundColor Cyan
Write-Host "   • Redis:          localhost:6379" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 Voir les logs: docker-compose logs -f web" -ForegroundColor Magenta

