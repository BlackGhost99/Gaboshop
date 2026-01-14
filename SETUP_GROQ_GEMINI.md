# Configuration des Providers IA Gratuits

## 🚀 Configuration Rapide

### Option 1: Groq (RECOMMANDÉ - Gratuit, Rapide)

1. **Obtenir une clé API** :
   - Aller sur https://console.groq.com/
   - Créer un compte (gratuit, pas de carte bancaire)
   - Générer une clé API

2. **Configurer dans `settings.py`** :
   ```python
   AI_PROVIDER = 'groq'
   GROQ_API_KEY = 'votre_cle_groq_ici'
   ```

3. **C'est tout !** Groq est déjà intégré, utilise le module `openai` existant.

**Limites** : 14,400 requêtes/jour (gratuit à vie)

---

### Option 2: Google Gemini (Gratuit, Puissant)

1. **Obtenir une clé API** :
   - Aller sur https://makersuite.google.com/app/apikey
   - Créer un compte Google
   - Générer une clé API

2. **Installer la dépendance** :
   ```bash
   pip install google-generativeai
   ```

3. **Configurer dans `settings.py`** :
   ```python
   AI_PROVIDER = 'gemini'
   GEMINI_API_KEY = 'votre_cle_gemini_ici'
   ```

**Limites** : 1,500 requêtes/jour (gratuit)

---

## 📝 Modèles Disponibles

### Groq
- `llama-3.1-8b-instant` (rapide, recommandé)
- `mixtral-8x7b-32768` (plus puissant)
- `gemma-7b-it` (léger)

### Gemini
- `gemini-pro` (recommandé)
- `gemini-pro-vision` (avec vision)

---

## ✅ Test Rapide

Après configuration, redémarrez le serveur Django et testez l'IA dans l'interface.

Si vous voyez des erreurs, vérifiez :
1. La clé API est correcte
2. Les dépendances sont installées (`openai` pour Groq, `google-generativeai` pour Gemini)
3. Le provider est bien configuré dans `settings.py`



