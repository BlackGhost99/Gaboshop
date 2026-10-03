#!/usr/bin/env pwsh
# Test pour reproduire l'erreur 400 de création commande

Write-Host "=== TEST CREATION COMMANDE SINGPAY ===" -ForegroundColor Green
Write-Host ""

# 1. Récupérer un utilisateur de test
$apiUrl = "http://localhost:8000"

# Token d'un user existant (à récupérer de la DB)
# Pour tester, on doit d'abord avoir un utilisateur valide

# Créer un payload minimal pour tester
$payload = @{
    store = 1
    delivery_address = "123 Rue Test"
    delivery_phone = "+24177777777"
    delivery_zone = "Zone Test"
    items = @(
        @{
            product_id = 1
            quantity = 1
        }
    )
} | ConvertTo-Json

Write-Host "📤 Payload envoyé:" -ForegroundColor Yellow
Write-Host $payload
Write-Host ""

# Test sans authentification d'abord
Write-Host "🔐 Test sans authentification..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest `
        -Uri "$apiUrl/api/v1/orders/create/" `
        -Method Post `
        -Headers @{"Content-Type"="application/json"} `
        -Body $payload `
        -UseBasicParsing -ErrorAction Stop
    
    Write-Host "✓ Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host $response.Content
} catch {
    Write-Host "❌ Status: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    Write-Host "Response:" -ForegroundColor Yellow
    Write-Host $_.Exception.Response.ToString()
}

Write-Host ""
Write-Host "💡 Pour tester avec authentification:" -ForegroundColor Cyan
Write-Host "  1. Aller à http://localhost:8000/admin"
Write-Host "  2. Copier un token utilisateur"
Write-Host "  3. Remplacer \$token ci-dessous et relancer"

# Exemple avec authentification
# $token = "YOUR_TOKEN_HERE"
# $response = Invoke-WebRequest `
#     -Uri "$apiUrl/api/v1/orders/create/" `
#     -Method Post `
#     -Headers @{ 
#         "Content-Type"="application/json"
#         "Authorization"="Token $token"
#     } `
#     -Body $payload `
#     -UseBasicParsing
