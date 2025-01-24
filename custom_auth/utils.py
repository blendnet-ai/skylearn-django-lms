from cryptography.fernet import Fernet
import base64
import os

# Use the key you generated above
KEY = b'acDXvWXrXUBtiW0N0EnJ5QWl52_xShq5O-9XFnCEGYA=' 
cipher = Fernet(KEY)

class CryptographyHandler:
    @staticmethod
    def encrypt_user_id(user_id):
        user_id_bytes = str(user_id).encode()
        encrypted_user_id = cipher.encrypt(user_id_bytes)
        return base64.urlsafe_b64encode(encrypted_user_id).decode()

    @staticmethod
    def decrypt_user_id(encrypted_user_id):
        encrypted_user_id_bytes = base64.urlsafe_b64decode(encrypted_user_id)
        decrypted_user_id = cipher.decrypt(encrypted_user_id_bytes).decode()
        return int(decrypted_user_id)