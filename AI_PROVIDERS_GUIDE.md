# Guide des Providers IA pour Gaboshop

## Options disponibles

### 1. Mode Local (GRATUIT - Par défaut)
- **Coût** : 0 FCFA
- **Configuration** : Aucune clé API nécessaire
- **Fonctionnalités** : 
  - Chat avec règles prédéfinies
  - Explications d'erreurs
  - Recherche simple de produits
  - Guidance basique
- **Limitations** : Pas de compréhension avancée du langage naturel

### 2. DeepSeek (GRATUIT avec limites généreuses) ⭐ RECOMMANDÉ
- **Coût** : 1 million de tokens/mois GRATUIT
- **Obtenir une clé** : https://platform.deepseek.com/
- **Configuration** :
  ```python
  # Dans settings.py
  AI_PROVIDER = 'deepseek'
  DEEPSEEK_API_KEY = 'votre_cle_deepseek_ici'
  ```
- **Avantages** :
  - Gratuit avec 1M tokens/mois
  - Compatible OpenAI (même API)
  - Performances excellentes
  - Supporte le français

### 3. Anthropic Claude (PAYANT)
- **Coût** : ~$0.003-0.015 par requête
- **Obtenir une clé** : https://console.anthropic.com/
- **Configuration** :
  ```python
  # Dans settings.py
  AI_PROVIDER = 'anthropic'
  ANTHROPIC_API_KEY = 'votre_cle_anthropic_ici'
  ```

### 4. OpenAI (PAYANT, crédits gratuits au départ)
- **Coût** : Payant après crédits gratuits
- **Obtenir une clé** : https://platform.openai.com/
- **Configuration** :
  ```python
  # Dans settings.py
  AI_PROVIDER = 'openai'
  OPENAI_API_KEY = 'votre_cle_openai_ici'
  ```

## Configuration rapide avec DeepSeek (GRATUIT)

1. **Obtenir une clé API DeepSeek** :
   - Allez sur https://platform.deepseek.com/
   - Créez un compte
   - Générez une clé API (gratuite avec 1M tokens/mois)

2. **Configurer dans settings.py** :
   ```python
   AI_PROVIDER = 'deepseek'
   DEEPSEEK_API_KEY = 'sk-votre_cle_ici'
   ```

3. **Redémarrer le serveur Django**

4. **C'est tout !** L'IA utilisera maintenant DeepSeek gratuitement.

## Comparaison des providers

| Provider | Coût | Tokens gratuits/mois | Qualité | Recommandé pour |
|----------|------|---------------------|---------|-----------------|
| **Local** | Gratuit | Illimité | Basique | Développement/Test |
| **DeepSeek** | Gratuit | 1M tokens | Excellente | Production (gratuit) |
| **Claude** | Payant | 0 | Excellente | Production (budget) |
| **OpenAI** | Payant | Crédits initiaux | Excellente | Production (budget) |

## Recommandation

**Pour la production avec budget limité** : Utilisez **DeepSeek** (gratuit avec 1M tokens/mois, largement suffisant pour la plupart des cas d'usage).

**Pour le développement** : Le mode **local** fonctionne très bien.

