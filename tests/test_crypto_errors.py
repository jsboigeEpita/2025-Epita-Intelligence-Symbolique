#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test pour évaluer les messages d'erreur du service de cryptographie.
"""

import sys
import os
import base64
from cryptography.fernet import Fernet, InvalidToken

# Ajouter le répertoire du projet au PYTHONPATH
sys.path.insert(0, os.path.abspath('.'))

# Définir une classe CryptoService simplifiée pour les tests
class CryptoService:
    def __init__(self, encryption_key=None):
        self.encryption_key = encryption_key
        print(f"Service initialisé avec clé: {'présente' if encryption_key else 'absente'}")
    
    def encrypt_data(self, data):
        if not self.encryption_key:
            print("ERREUR: Clé de chiffrement manquante.")
            return None
        
        try:
            f = Fernet(self.encryption_key)
            encrypted_data = f.encrypt(data)
            print("Chiffrement réussi.")
            return encrypted_data
        except Exception as e:
            print(f"ERREUR de chiffrement: {e}")
            return None
    
    def decrypt_data(self, encrypted_data):
        if not self.encryption_key:
            print("ERREUR: Clé de chiffrement manquante.")
            return None
        
        try:
            f = Fernet(self.encryption_key)
            decrypted_data = f.decrypt(encrypted_data)
            print("Déchiffrement réussi.")
            return decrypted_data
        except InvalidToken:
            print("ERREUR: Jeton invalide. La clé est incorrecte ou les données sont corrompues.")
            return None
        except Exception as e:
            print(f"ERREUR de déchiffrement: {e}")
            return None

def test_invalid_key():
    print("\n=== Test avec clé invalide ===")
    service = CryptoService(encryption_key=b'invalid_key')
    result = service.encrypt_data(b'test')
    print(f"Résultat: {result}")

def test_missing_key():
    print("\n=== Test sans clé ===")
    service = CryptoService()
    result = service.encrypt_data(b'test')
    print(f"Résultat: {result}")

def test_valid_key():
    print("\n=== Test avec clé valide ===")
    key = Fernet.generate_key()
    service = CryptoService(encryption_key=key)
    encrypted = service.encrypt_data(b'test')
    print(f"Données chiffrées: {encrypted}")
    
    if encrypted:
        decrypted = service.decrypt_data(encrypted)
        print(f"Données déchiffrées: {decrypted}")

def test_wrong_key_decrypt():
    print("\n=== Test de déchiffrement avec mauvaise clé ===")
    # Chiffrer avec une clé
    key1 = Fernet.generate_key()
    service1 = CryptoService(encryption_key=key1)
    encrypted = service1.encrypt_data(b'test')
    
    # Déchiffrer avec une autre clé
    key2 = Fernet.generate_key()
    service2 = CryptoService(encryption_key=key2)
    decrypted = service2.decrypt_data(encrypted)
    print(f"Résultat: {decrypted}")

def test_corrupted_data():
    print("\n=== Test avec données corrompues ===")
    key = Fernet.generate_key()
    service = CryptoService(encryption_key=key)
    encrypted = service.encrypt_data(b'test')
    
    # Corrompre les données
    if encrypted:
        corrupted = encrypted[:-5] + b'12345'
        decrypted = service.decrypt_data(corrupted)
        print(f"Résultat: {decrypted}")

if __name__ == "__main__":
    print("=== Tests des messages d'erreur du service de cryptographie ===")
    test_invalid_key()
    test_missing_key()
    test_valid_key()
    test_wrong_key_decrypt()
    test_corrupted_data()