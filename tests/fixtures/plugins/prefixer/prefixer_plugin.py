# -*- coding: utf-8 -*-


class PrefixerPlugin:
    """
    Un plugin de test simple qui ajoute un préfixe à une chaîne de caractères.
    """

    def add_prefix(self, text: str, prefix: str = "pre_") -> dict:
        """
        Ajoute un préfixe à la chaîne de caractères fournie.
        """
        processed_text = f"{prefix}{text}"
        return {"processed_text": processed_text}
