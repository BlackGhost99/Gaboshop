# Vérification des routes B2B

## Problème : Erreur 404 sur `/api/v1/b2b/profiles/{id}/`

### Solution 1 : Redémarrer le serveur Django

**IMPORTANT** : Après avoir ajouté de nouvelles routes, vous DEVEZ redémarrer le serveur Django.

```bash
# Arrêter le serveur (Ctrl+C)
# Puis relancer :
python manage.py runserver
```

### Solution 2 : Vérifier que les routes sont chargées

Dans la console Django, vous devriez voir au démarrage :
```
System check identified no issues (0 silenced).
Django version X.X, using settings 'Gaboshop.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

Si vous voyez des erreurs d'import, corrigez-les avant de continuer.

### Solution 3 : Tester l'endpoint directement

Dans votre navigateur ou avec curl :
```
GET http://localhost:8000/api/v1/b2b/profiles/3/
```

**Si vous obtenez une page HTML 404** : La route n'est pas chargée → Redémarrer Django

**Si vous obtenez un JSON 404** : La route fonctionne, mais le profil n'existe pas (normal pour un nouveau store)

### Solution 4 : Vérifier les permissions

L'endpoint nécessite que l'utilisateur soit admin :
- `user.is_staff = True` OU
- `user.user_type = 'admin'`

Si l'utilisateur n'est pas admin, vous obtiendrez une erreur 403, pas 404.


