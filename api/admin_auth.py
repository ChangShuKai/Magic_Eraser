import pyotp
import jwt
import datetime
import os
from passlib.context import CryptContext
from typing import Optional, Dict

# 安全常數 — 從環境變數讀取，絕不硬編碼
SECRET_KEY = os.environ.get("ADMIN_JWT_SECRET", "")
if not SECRET_KEY:
    import warnings
    warnings.warn("環境變數 ADMIN_JWT_SECRET 未設定！請設定後再使用 JWT 認證功能。")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證密碼"""
    if not plain_password or not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """產生密碼雜湊"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """簽發 JWT (將作為 HttpOnly Cookie 傳遞)"""
    if not SECRET_KEY:
        raise RuntimeError("ADMIN_JWT_SECRET 未設定，無法簽發 Token！")
    to_encode = data.copy()
    now = datetime.datetime.now(datetime.timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict]:
    """解析並驗證 JWT"""
    if not SECRET_KEY or not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def generate_totp_secret() -> str:
    """產生新的 TOTP 密鑰供使用者綁定 MFA"""
    return pyotp.random_base32()

def verify_totp(secret: str, code: str) -> bool:
    """驗證 TOTP 碼"""
    if not secret or not code:
        return False
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(code)
    except Exception:
        return False
