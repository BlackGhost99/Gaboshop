"""
Système multi-providers pour l'IA
Supporte plusieurs services d'IA (Claude, DeepSeek, OpenAI, etc.)
"""
import os
from typing import Optional, Dict, Any
from django.conf import settings


class AIProvider:
    """
    Classe abstraite pour les providers d'IA
    """
    
    @staticmethod
    def get_provider_config() -> Dict[str, Any]:
        """
        Retourne la configuration du provider actif
        """
        provider = getattr(settings, 'AI_PROVIDER', 'local').lower()
        api_key = None
        
        if provider == 'anthropic' or provider == 'claude':
            api_key = getattr(settings, 'ANTHROPIC_API_KEY', None) or os.environ.get('ANTHROPIC_API_KEY')
            return {
                'name': 'anthropic',
                'api_key': api_key,
                'model': getattr(settings, 'ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'),
                'available': bool(api_key and api_key != 'votre_cle_api_ici' and api_key.strip())
            }
        
        elif provider == 'deepseek':
            api_key = getattr(settings, 'DEEPSEEK_API_KEY', None) or os.environ.get('DEEPSEEK_API_KEY')
            return {
                'name': 'deepseek',
                'api_key': api_key,
                'model': getattr(settings, 'DEEPSEEK_MODEL', 'deepseek-chat'),
                'base_url': getattr(settings, 'DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1'),
                'available': bool(api_key and api_key.strip())
            }
        
        elif provider == 'openai':
            api_key = getattr(settings, 'OPENAI_API_KEY', None) or os.environ.get('OPENAI_API_KEY')
            return {
                'name': 'openai',
                'api_key': api_key,
                'model': getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo'),
                'available': bool(api_key and api_key.strip())
            }
        
        elif provider == 'groq':
            api_key = getattr(settings, 'GROQ_API_KEY', None) or os.environ.get('GROQ_API_KEY')
            return {
                'name': 'groq',
                'api_key': api_key,
                'model': getattr(settings, 'GROQ_MODEL', 'llama-3.1-8b-instant'),
                'base_url': 'https://api.groq.com/openai/v1',
                'available': bool(api_key and api_key.strip())
            }
        
        elif provider == 'gemini':
            api_key = getattr(settings, 'GEMINI_API_KEY', None) or os.environ.get('GEMINI_API_KEY')
            return {
                'name': 'gemini',
                'api_key': api_key,
                'model': getattr(settings, 'GEMINI_MODEL', 'gemini-pro'),
                'available': bool(api_key and api_key.strip())
            }
        
        # Mode local par défaut
        return {
            'name': 'local',
            'api_key': None,
            'available': True
        }
    
    @staticmethod
    def call_ai(system_prompt: str, user_message: str, config: Dict[str, Any]) -> Optional[str]:
        """
        Appelle le provider d'IA configuré
        """
        provider_name = config.get('name', 'local')
        
        if provider_name == 'local':
            return None  # Utiliser LocalAI
        
        if provider_name == 'anthropic':
            return AIProvider._call_anthropic(system_prompt, user_message, config)
        
        elif provider_name == 'deepseek':
            return AIProvider._call_deepseek(system_prompt, user_message, config)
        
        elif provider_name == 'openai':
            return AIProvider._call_openai(system_prompt, user_message, config)
        
        elif provider_name == 'groq':
            return AIProvider._call_groq(system_prompt, user_message, config)
        
        elif provider_name == 'gemini':
            return AIProvider._call_gemini(system_prompt, user_message, config)
        
        return None
    
    @staticmethod
    def _call_anthropic(system_prompt: str, user_message: str, config: Dict[str, Any]) -> Optional[str]:
        """Appelle Anthropic Claude API"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=config['api_key'])
            response = client.messages.create(
                model=config['model'],
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            )
            
            ai_response = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, 'text'):
                        ai_response += block.text
            return ai_response
        except Exception:
            return None
    
    @staticmethod
    def _call_deepseek(system_prompt: str, user_message: str, config: Dict[str, Any]) -> Optional[str]:
        """Appelle DeepSeek API (compatible OpenAI)"""
        try:
            import openai
            base_url = config.get('base_url', 'https://api.deepseek.com/v1')
            # S'assurer que l'URL se termine par /v1
            if not base_url.endswith('/v1'):
                if base_url.endswith('/'):
                    base_url = base_url + 'v1'
                else:
                    base_url = base_url + '/v1'
            
            client = openai.OpenAI(
                api_key=config['api_key'],
                base_url=base_url
            )
            response = client.chat.completions.create(
                model=config['model'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=1024,
                temperature=0.7
            )
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content:
                    return content
            return None
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            error_str = str(e)
            error_details = f"Erreur DeepSeek API: {error_str}\n{traceback.format_exc()}"
            logger.error(error_details)
            
            # Gérer les erreurs spécifiques
            if "402" in error_str or "Insufficient Balance" in error_str:
                raise ValueError("Le compte DeepSeek n'a pas assez de crédits. Veuillez recharger votre compte sur https://platform.deepseek.com/")
            elif "401" in error_str or "unauthorized" in error_str.lower():
                raise ValueError("Clé API DeepSeek invalide. Vérifiez DEEPSEEK_API_KEY dans settings.py")
            elif "404" in error_str:
                raise ValueError("URL DeepSeek incorrecte. Vérifiez la configuration.")
            
            # Re-raise pour les autres erreurs
            raise
    
    @staticmethod
    def _call_openai(system_prompt: str, user_message: str, config: Dict[str, Any]) -> Optional[str]:
        """Appelle OpenAI API"""
        try:
            import openai
            client = openai.OpenAI(api_key=config['api_key'])
            response = client.chat.completions.create(
                model=config['model'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=1024
            )
            return response.choices[0].message.content
        except Exception:
            return None
    
    @staticmethod
    def _call_groq(system_prompt: str, user_message: str, config: Dict[str, Any]) -> Optional[str]:
        """Appelle Groq API (gratuit, ultra-rapide)"""
        try:
            import openai
            client = openai.OpenAI(
                api_key=config['api_key'],
                base_url=config.get('base_url', 'https://api.groq.com/openai/v1')
            )
            response = client.chat.completions.create(
                model=config['model'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=1024,
                temperature=0.7
            )
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content:
                    return content
            return None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur Groq API: {str(e)}")
            return None
    
    @staticmethod
    def _call_gemini(system_prompt: str, user_message: str, config: Dict[str, Any]) -> Optional[str]:
        """Appelle Google Gemini API (gratuit)"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=config['api_key'])
            
            # Utiliser le modèle configuré (doit commencer par 'models/')
            model_name = config.get('model', 'models/gemini-2.0-flash')
            if not model_name.startswith('models/'):
                model_name = f'models/{model_name}'
            
            # Combiner system prompt et user message dans le prompt
            full_prompt = f"{system_prompt}\n\n{user_message}"
            
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                full_prompt,
                generation_config={
                    'max_output_tokens': 1024,
                    'temperature': 0.7,
                }
            )
            
            if response and response.text:
                return response.text
            return None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            error_str = str(e)
            logger.error(f"Erreur Gemini API: {error_str}")
            
            # Gérer les erreurs spécifiques - essayer un modèle de fallback
            if "404" in error_str or "not found" in error_str.lower():
                try:
                    # Essayer avec gemini-2.0-flash comme fallback
                    fallback_model = 'models/gemini-2.0-flash'
                    if model_name != fallback_model:
                        model = genai.GenerativeModel(fallback_model)
                        response = model.generate_content(
                            full_prompt,
                            generation_config={
                                'max_output_tokens': 1024,
                                'temperature': 0.7,
                            }
                        )
                        if response and response.text:
                            return response.text
                except:
                    pass
            
            return None


