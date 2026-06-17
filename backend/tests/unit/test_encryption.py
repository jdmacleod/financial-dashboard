import pytest

from app.core.encryption import decrypt, encrypt


def test_encrypt_decrypt_roundtrip_ascii() -> None:
    plaintext = "Chase Bank Account 1234"
    assert decrypt(encrypt(plaintext)) == plaintext


def test_encrypt_decrypt_roundtrip_unicode() -> None:
    plaintext = "Banco Español — 日本語テスト"
    assert decrypt(encrypt(plaintext)) == plaintext


def test_encrypt_decrypt_roundtrip_empty_string() -> None:
    assert decrypt(encrypt("")) == ""


def test_nonce_differs_across_calls_for_identical_plaintext() -> None:
    plaintext = "identical plaintext"
    ct1 = encrypt(plaintext)
    ct2 = encrypt(plaintext)
    assert ct1 != ct2
    assert ct1[:12] != ct2[:12]  # nonce prefix


def test_decrypt_raises_on_tampered_ciphertext() -> None:
    ciphertext = encrypt("sensitive data")
    tampered = bytearray(ciphertext)
    tampered[-1] ^= 0xFF
    with pytest.raises(Exception):  # noqa: B017 — AEAD tag check raises cryptography's InvalidTag
        decrypt(bytes(tampered))


def test_decrypt_raises_on_tampered_nonce() -> None:
    ciphertext = encrypt("sensitive data")
    tampered = bytearray(ciphertext)
    tampered[0] ^= 0xFF
    with pytest.raises(Exception):  # noqa: B017
        decrypt(bytes(tampered))
