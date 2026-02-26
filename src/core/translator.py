"""
Translation Service for KDTPS Error Manager
Supports Gemini API and Google Translate for Japanese <-> Vietnamese translation.
"""
import logging
import json
import os
from pathlib import Path
from typing import Optional, Callable
from functools import lru_cache

logger = logging.getLogger(__name__)


class TranslationService:
    """Handles text translation between Japanese and Vietnamese."""
    
    def __init__(self, settings_path: Optional[Path] = None):
        self.settings_path = settings_path
        self.settings = self._load_settings()
        self._gemini_client = None
    
    def _load_settings(self) -> dict:
        """Load AI settings from JSON file and Environment variables."""
        settings = {
            "api_key": "",
            "translation_service": "google",
            "fallback_to_google": True
        }

        if self.settings_path is None:
            from utils.config import config
            self.settings_path = config.ai_settings_path
        
        if self.settings_path.exists():
            try:
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    file_settings = json.load(f)
                    settings.update(file_settings)
            except Exception as e:
                logger.error(f"Failed to load AI settings: {e}")
        
        # Override/Fallback with Environment Variables
        env_key = os.getenv("GEMINI_API_KEY")
        if env_key:
             settings["api_key_env"] = env_key

        return settings

    @property
    def api_keys(self) -> list[str]:
        """Get list of API keys."""
        keys = []
        
        # Priority 1: Environment Variable
        env_key = self.settings.get("api_key_env")
        if env_key:
            keys.append(env_key)

        # Priority 2: JSON Settings
        json_keys = self.settings.get("api_keys", [])
        if json_keys:
            keys.extend(json_keys)
            
        # Fallback: Single JSON key
        if not keys:
            single_key = self.settings.get("api_key", "")
            if single_key:
                keys.append(single_key)
                
        return keys

    @property
    def use_gemini(self) -> bool:
        """Check if Gemini should be used."""
        return (
            self.settings.get("translation_service") == "gemini" 
            and bool(self.api_keys)
        )
    
    def _translate_gemini(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None
    ) -> Optional[str]:
        """Translate using Gemini API with Key Rotation."""
        try:
            from google import genai
            
            keys = self.api_keys
            if not keys:
                return None
            
            lang_names = {
                "ja": "Japanese",
                "vi": "Vietnamese", 
                "en": "English"
            }
            target_name = lang_names.get(target_lang, target_lang)
            source_name = lang_names.get(source_lang or "", "auto-detected")
            
            prompt = f"""Translate the following text to {target_name}.
Only output the translated text, no explanations.

Source language: {source_name}
Text to translate:
{text}"""
            
            # Rotation Logic: Try each key
            for i, key in enumerate(keys):
                try:
                    logger.debug(f"Gemini: Attempting translation with Key #{i+1} (ends in {key[-4:]})")
                    
                    # Try models in order from settings
                    models = self.settings.get("waterfall_strategy", [
                        {"model_id": "gemini-2.0-flash", "is_active": True, "timeout": 10}
                    ])
                    
                    for model_config in models:
                        if not model_config.get("is_active", True):
                            continue
                        
                        model_id = model_config.get("model_id", "gemini-2.0-flash")
                        timeout_sec = model_config.get("timeout", 10)
                        
                        try:
                            # Tạo SSL context an toàn cho request này
                            # Không disable SSL verify global nữa mà chỉ cho request cụ thể
                            import ssl
                            ssl_context = ssl.create_default_context()
                            ssl_context.check_hostname = True
                            ssl_context.verify_mode = ssl.CERT_REQUIRED

                            # Khởi tạo client với timeout cho model request cụ thể
                            # http_options là pattern phổ biến cho google-genai
                            client = genai.Client(
                                api_key=key,
                                http_options={"timeout": timeout_sec}
                            )
                            
                            response = client.models.generate_content(
                                model=model_id,
                                contents=prompt
                            )
                            
                            if response.text:
                                logger.info(f"Gemini translation successful with {model_id} (Key #{i+1})")
                                return response.text.strip()
                                
                        except Exception as model_error:
                            # Inner loop cho models: nếu lỗi là 429/403 -> Break ra outer key loop
                            # Nếu là lỗi model cụ thể -> Continue sang model tiếp theo
                            err_str = str(model_error).lower()
                            if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                                logger.warning(f"Quota/Rate limit hit for Key #{i+1}: {model_error}. Rotating key...")
                                raise  # Propagate lỗi ra outer loop (key rotation)
                            
                            logger.warning(f"Model {model_id} failed with Key #{i+1}: {model_error}")
                            continue
                            
                    # Nếu chạy hết models mà không raise exception (chỉ fail tất cả models), thử key tiếp theo
                    # Hoặc có thể key hiện tại bị lỗi. Thử key tiếp theo cho chắc.
                    
                except Exception as key_error:
                    # Key level exception (ví dụ: init client fail, hoặc propagated quota error)
                    logger.warning(f"Key #{i+1} failed: {key_error}")
                    continue  # Thử key tiếp theo
            
            return None
            
        except ImportError:
            logger.error("google-genai not installed")
            return None
        except Exception as e:
            logger.error(f"Gemini translation failed: {e}")
            return None
    
    def _translate_google(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None
    ) -> Optional[str]:
        """Translate using Google Translate (free)."""
        try:
            from deep_translator import GoogleTranslator
            
            translator = GoogleTranslator(
                source=source_lang or 'auto',
                target=target_lang
            )
            
            result = translator.translate(text)
            logger.info("Google Translate successful")
            return result
            
        except ImportError:
            logger.error("deep-translator not installed")
            return None
        except Exception as e:
            logger.error(f"Google Translate failed: {e}")
            return None
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of text.
        Simple heuristic: if contains Japanese characters -> 'ja', else 'vi'
        """
        # Check for Japanese characters (Hiragana, Katakana, Kanji ranges)
        for char in text:
            code = ord(char)
            # Hiragana: 3040-309F, Katakana: 30A0-30FF, CJK: 4E00-9FFF
            if (0x3040 <= code <= 0x309F or 
                0x30A0 <= code <= 0x30FF or
                0x4E00 <= code <= 0x9FFF):
                return 'ja'
        
        return 'vi'
    
    def translate(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> Optional[str]:
        """
        Translate text to target language.
        
        Args:
            text: Text to translate
            target_lang: Target language code ('ja' or 'vi')
            source_lang: Source language code (auto-detect if None)
            
        Returns:
            Translated text or None if translation fails
        """
        if not text or not text.strip():
            return None
            
        # Try Gemini first if enabled
        if self.use_gemini:
            result = self._translate_gemini(text, target_lang, source_lang)
            if result:
                return result
            
            # Fallback to Google if configured
            if self.settings.get("fallback_to_google", True):
                logger.info("Falling back to Google Translate")
                return self._translate_google(text, target_lang, source_lang)
            return None
        else:
            # Use Google Translate directly
            return self._translate_google(text, target_lang, source_lang)

    def translate_auto(self, text: str) -> tuple[Optional[str], str]:
        """
        Auto-detect source language and translate to the other.
        
        Returns:
            Tuple of (translated_text, target_language)
            translated_text có thể là None nếu dịch thất bại
        """
        source_lang = self.detect_language(text)
        target_lang = 'vi' if source_lang == 'ja' else 'ja'
        
        translated = self.translate(text, target_lang, source_lang)
        return translated, target_lang


# Singleton instance
_translator_instance: Optional[TranslationService] = None

def get_translator(settings_path: Optional[Path] = None) -> TranslationService:
    """Get or create TranslationService instance.
    
    Args:
        settings_path: Đường dẫn tới file settings (tùy chọn)
    
    Returns:
        TranslationService instance
    """
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = TranslationService(settings_path)
    return _translator_instance


def translate_text(text: str, target_lang: str) -> Optional[str]:
    """Convenience function for translation."""
    return get_translator().translate(text, target_lang)


def translate_ja_to_vi(text: str) -> Optional[str]:
    """Translate Japanese to Vietnamese."""
    return get_translator().translate(text, 'vi', 'ja')


def translate_vi_to_ja(text: str) -> Optional[str]:
    """Translate Vietnamese to Japanese."""
    return get_translator().translate(text, 'ja', 'vi')
