import os
import sys
import gzip
import json

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from argumentation_analysis.utils.core_utils.crypto_utils import derive_encryption_key


def create_encrypted_config():
    """
    Creates an empty, gzipped, and encrypted config file.
    """
    config_dir = os.path.join(project_root, "argumentation_analysis", "data")
    output_file = os.path.join(config_dir, "extract_sources.json.gz.enc")

    # 1. Create empty JSON data
    empty_json_data = json.dumps([]).encode("utf-8")

    # 2. Compress the data
    compressed_data = gzip.compress(empty_json_data)

    # 3. Encrypt the data
    passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        print("ERROR: TEXT_CONFIG_PASSPHRASE environment variable not set.")
        return

    encryption_key = derive_encryption_key(passphrase)
    if not encryption_key:
        print("ERROR: Failed to derive encryption key.")
        return

    from cryptography.fernet import Fernet

    fernet = Fernet(encryption_key)
    encrypted_data = fernet.encrypt(compressed_data)

    # 4. Write to file
    os.makedirs(config_dir, exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(encrypted_data)

    print(f"Successfully created empty encrypted config file at: {output_file}")


if __name__ == "__main__":
    create_encrypted_config()
