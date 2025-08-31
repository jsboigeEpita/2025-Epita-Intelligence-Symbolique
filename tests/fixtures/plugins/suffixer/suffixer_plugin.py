# -*- coding: utf-8 -*-

class SuffixerPlugin:
    """
    Un plugin de test simple qui ajoute un suffixe à une chaîne de caractères.
    """
    def add_suffix(self, text: str, suffix: str = "_suf") -> dict:
        """
        Ajoute un suffixe à la chaîne de caractères fournie.
        """
        processed_text = f"{text}{suffix}"
        return {"processed_text": processed_text}