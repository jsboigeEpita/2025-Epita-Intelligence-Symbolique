#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour créer directement le fichier de cache du discours du Kremlin.
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent

# Définir les constantes
CACHE_DIR = parent_dir / "text_cache"
CACHE_DIR.mkdir(exist_ok=True, parents=True)

# Contenu factice du discours du Kremlin
KREMLIN_SPEECH = """
Address by the President of the Russian Federation
February 21, 2022

Citizens of Russia, friends,

I consider it necessary today to speak again about the tragic events in Donbass and the key aspects of ensuring the security of Russia.

I will begin with what I said in my address on February 21, 2022. I spoke about our biggest concerns and worries, and about the fundamental threats which irresponsible Western politicians created for Russia consistently, rudely and unceremoniously from year to year. I am referring to the eastward expansion of NATO, which is moving its military infrastructure ever closer to the Russian border.

So, I will start with the fact that modern Ukraine was entirely created by Russia, more precisely, by Bolshevik, Communist Russia. This process began almost immediately after the 1917 revolution, and Lenin and his associates did it in a way that was extremely harsh on Russia – by separating, severing what is historically Russian land. Nobody asked the millions of people living there what they thought.

Ukraine is home to NATO training missions which are, in fact, foreign military bases. They just called it a mission and that's it. They have been bringing in weapons, specialists, and instructors. Yet, they have the nerve to reproach us for conducting military exercises on our own territory. These principled proposals of ours have been ignored.

And today the "grateful progeny" has overturned monuments to Lenin in Ukraine. They call it decommunization. You want decommunization? Very well, this suits us just fine. But why stop halfway? We are ready to show what real decommunizations would mean for Ukraine.

Everything was in vain. The Minsk agreements have been buried. And it wasn't us who buried them. The current events have nothing to do with a desire to infringe on the interests of Ukraine and the Ukrainian people. They are connected with defending Russia from those who have taken Ukraine hostage and are trying to use it against our country and our people. I repeat: our actions are self-defense against the threats created for us and against a bigger calamity than what is happening today. I am asking you, however hard this may be, to understand this and to work together with us so as to turn this tragic page as soon as possible and to move forward together, without allowing anyone to interfere in our affairs and our relations but developing them independently, so as to create favorable conditions for overcoming all these problems and to strengthen us from within as a united whole, despite the existence of state borders. I believe in this – in our common future. These two documents will be prepared and signed shortly.

Thank you.
"""

def main():
    """Fonction principale."""
    print("\n=== Création du fichier de cache du discours du Kremlin ===\n")
    
    # Chemin du fichier de cache
    cache_path = CACHE_DIR / "4cf2d4853745719f6504a54610237738ad016de4f64176c3e8f5218f8fd2c01b.txt"
    
    # Écrire le contenu dans le fichier
    cache_path.write_text(KREMLIN_SPEECH, encoding='utf-8')
    
    print(f"✅ Fichier de cache créé : {cache_path}")
    print(f"   Longueur : {len(KREMLIN_SPEECH)} caractères")

if __name__ == "__main__":
    # Exécuter la fonction principale
    main()
    
    print("\n=== Création terminée ===\n")