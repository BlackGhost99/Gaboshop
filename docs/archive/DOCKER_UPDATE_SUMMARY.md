# 🐳 Docker Configuration Updates - Summary

## ✅ Problème Résolu

**Erreur 500 sur `/admin/login/`**: "Missing staticfiles manifest entry for 'admin/css/base.css'"

### Cause
L'étape `collectstatic` n'était pas exécutée au démarrage des conteneurs Docker, ce qui causait une erreur 500 lors du chargement de la page de login admin.

---

## 📋 Mises à Jour Effectuées

### 1. **Dockerfile** (Développement)
```diff
- FROM python:3.11-slim
+ FROM python:3.12-slim

- CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
+ CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py runserver 0.0.0.0:8000"]

- RUN mkdir -p /app/static /app/media
+ RUN mkdir -p /app/staticfiles /app/media
```

**Changements clés:**
- ✅ Upgrade Python 3.11 → 3.12
- ✅ Ajouter `collectstatic --noinput` avant le runserver
- ✅ Créer le répertoire `staticfiles` au lieu de `static`

---

### 2. **Dockerfile.prod** (Production)
```diff
- FROM python:3.11-slim
+ FROM python:3.12-slim

+ RUN mkdir -p /app/staticfiles /app/media
```

**Changements clés:**
- ✅ Synchroniser avec Dockerfile (Python 3.12)
- ✅ Créer `staticfiles` et `media` directories

---

### 3. **docker-compose.yml** (Développement)
```diff
- command: sh -c "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"
+ command: sh -c "python manage.py migrate --noinput && python manage.py collectstatic --noinput && python manage.py runserver 0.0.0.0:8000"
```

**Changements clés:**
- ✅ Ajouter `collectstatic` dans la commande

---

### 4. **docker-compose.prod.yml** (Production)
```diff
  web:
    ...
    volumes:
      - ./db.sqlite3:/app/db.sqlite3
      - ./media:/app/media
+     - ./staticfiles:/app/staticfiles
    ...

volumes:
  redis_data:
+  staticfiles:
+  frontend_node_modules:
```

**Changements clés:**
- ✅ Ajouter volume `staticfiles` pour persister les fichiers statiques
- ✅ Déclarer les volumes à la fin du fichier

---

### 5. **scripts/entrypoint.prod.sh**
Aucun changement (déjà correct):
```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput  # ✅ Déjà présent
exec gunicorn ...
```

---

## 🚀 Comment Utiliser

### Sur Windows (PowerShell)
```powershell
.\restart_docker.ps1
```

### Sur Linux/Mac (Bash/Shell)
```bash
chmod +x restart_docker_updated.sh
./restart_docker_updated.sh
```

### Manuellement
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 🔍 Vérification

Après le redémarrage, vérifiez:

```bash
# ✅ Les conteneurs tournent
docker-compose ps

# ✅ Les logs du web service
docker-compose logs web

# ✅ Accédez à l'admin
curl http://localhost:8000/admin/ -v

# ✅ Vérifier les staticfiles
docker exec <web_container_id> ls -la /app/staticfiles/
```

---

## 📦 Configuration Python

La version Python a été mise à jour:
- **Avant**: 3.11
- **Après**: 3.12

Assurez-vous que vos dépendances sont compatibles avec Python 3.12!

---

## ⚠️ Notes Importantes

1. **Volume staticfiles**: Les fichiers statiques sont maintenant persistés via volume Docker
2. **Collectstatic**: Exécuté automatiquement au démarrage
3. **Manifest**: Le `staticfiles.json` manifest est généré automatiquement
4. **Production**: Le script `entrypoint.prod.sh` gère `collectstatic` avec gunicorn

---

## 🐛 Troubleshooting

### Problème: "Missing manifest entry for admin/css/base.css"
**Solution**: 
```bash
docker-compose down
docker-compose up -d
# ou
docker-compose restart web
```

### Problème: Permissions sur /app/staticfiles
**Solution**:
```bash
docker-compose exec web chmod -R 755 /app/staticfiles
```

### Voir tous les logs
```bash
docker-compose logs -f --all
```

---

**Dernière mise à jour**: 2026-04-05
