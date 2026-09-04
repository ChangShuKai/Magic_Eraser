import pyotp
import jwt
import datetime
from passlib.context import CryptContext
from typing import Optional, Dict

# 安全常數 (實際專案中應移至環境變數 .env)
SECRET_KEY = "SUPER_SECRET_ADMIN_KEY_CHANGE_ME"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證密碼"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """產生密碼雜湊"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """簽發 JWT (將作為 HttpOnly Cookie 傳遞)"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict]:
    """解析並驗證 JWT"""
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
    totp = pyotp.TOTP(secret)
    return totp.verify(code)
