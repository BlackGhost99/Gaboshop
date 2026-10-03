#!/bin/bash
# Script de redémarrage Docker avec correction SingPay

echo "==================================="
echo "🔧 MISE À JOUR DOCKER SINGPAY"
echo "==================================="
echo ""

cd /d/Expériences/Gaboshop

echo "✓ Arrête les conteneurs..."
docker-compose down

echo ""
echo "✓ Reconstruire les images..."
docker-compose build --no-cache web

echo ""
echo "✓ Redémarre les conteneurs..."
docker-compose up -d

echo ""
echo "✓ Attendre 5 secondes pour le démarrage..."
sleep 5

echo ""
echo "✓ Vérifier l'état des conteneurs..."
docker-compose ps

echo ""
echo "✓ Vérifier les logs web..."
docker-compose logs --tail 10 web

echo ""
echo "=== ✅ MISE À JOUR TERMINÉE ==="
echo ""
echo "Accédez à l'API sur: http://localhost:8000"
echo "Accédez au Frontend sur: http://localhost:5173"
