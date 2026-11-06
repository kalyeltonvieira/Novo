"""
Módulo de Autenticação e Segurança (JWT & Hashing)
===================================================
Gerencia hashing de senhas, validação de credenciais e emissão/verificação de JWTs.
"""

import os
import time
import hmac
import hashlib
import base64
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Secret key e algoritmo para assinar JWTs
SECRET_KEY = os.getenv("SECRET_KEY", "transparencia_secret_key_super_segura_2026_change_in_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas

try:
    from jose import jwt, JWTError
    JOSE_AVAILABLE = True
except ImportError:
    JOSE_AVAILABLE = False


def hash_password(password: str) -> str:
    """
    Gera hash seguro usando PBKDF2-HMAC-SHA256 com salt aleatório.
    Formato retornado: pbkdf2_sha256$iterations$salt$hash
    """
    salt = secrets.token_hex(16)
    iterations = 100000
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${pwd_hash.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto plano corresponde ao hash gerado."""
    try:
        if not hashed_password.startswith("pbkdf2_sha256$"):
            # Fallback para comparação direta se senha for formato legado/plano
            return plain_password == hashed_password

        parts = hashed_password.split("$")
        if len(parts) != 4:
            return False

        _, iterations_str, salt, expected_hash = parts
        iterations = int(iterations_str)

        pwd_hash = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations)
        return hmac.compare_digest(pwd_hash.hex(), expected_hash)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria um token JWT de acesso assinado."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": int(expire.timestamp())})

    if JOSE_AVAILABLE:
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    # Fallback JWT nativo usando HMAC-SHA256
    header = {"alg": ALGORITHM, "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(to_encode).encode()).decode().rstrip("=")
    signature_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(SECRET_KEY.encode(), signature_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodifica e valida o token JWT."""
    if JOSE_AVAILABLE:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None

    # Fallback verificação manual
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        
        signature_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(SECRET_KEY.encode(), signature_input, hashlib.sha256).digest()
        
        padded_sig = sig_b64 + "=" * (-len(sig_b64) % 4)
        if not hmac.compare_digest(base64.urlsafe_b64decode(padded_sig), expected_sig):
            return None

        padded_payload = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_payload).decode())

        if payload.get("exp") and time.time() > payload["exp"]:
            return None

        return payload
    except Exception:
        return None
