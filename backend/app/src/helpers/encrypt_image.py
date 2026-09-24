import base64
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# AES-GCM uses a fresh 96-bit nonce for each encryption. The nonce is public
# and is prepended to the ciphertext so the frontend can decrypt the image.
# Reusing a nonce with the same key would break AES-GCM's guarantees.
AES_GCM_NONCE_BYTES = 12
AES_KEY_BITS = 256


def encrypt_image(img: bytes) -> tuple[bytes, str]:
    """Encrypt image bytes for preloading before the card is revealed.

    The returned bytes contain the nonce followed by the AES-GCM ciphertext
    and authentication tag. Send the base64 key only when revealing this card.

    Args:
        img (bytes): Complete image file bytes to encrypt.

    Returns:
        tuple[bytes, str]: Encrypted image bytes and its base64-encoded key.
    """
    key = AESGCM.generate_key(bit_length=AES_KEY_BITS)
    nonce = secrets.token_bytes(AES_GCM_NONCE_BYTES)
    encrypted_image = AESGCM(key).encrypt(nonce, img, None)
    # JSON cannot carry arbitrary key bytes directly. Base64 preserves the
    # exact AES key while letting the reveal route return it as a string.
    encoded_key = base64.b64encode(key).decode("ascii")
    return nonce + encrypted_image, encoded_key
