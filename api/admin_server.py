from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.security import APIKeyCookie
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import sys
import os

# 將當前目錄加入 sys.path 以確保在 Vercel 也能正確 import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from admin_auth import (
    verify_password, get_password_hash, create_access_token, 
    decode_access_token, verify_totp
)

# 初始化日誌 (針對 Vercel Serverless，改為輸出至標準輸出 stdout，避免寫入 read-only 檔案系統)
logger = logging.getLogger("admin_audit")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(clientip)s - %(user)s - %(message)s'))
logger.addHandler(handler)

# 建立 FastAPI 應用程式
app = FastAPI(title="Secure Admin Backend")

# Vercel 環境下的 Host 會是動態的，因此先暫時允許所有，或是透過 Vercel 提供的特定網域
# 若有自訂網域可將其加入 allowed_hosts
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["*"] 
)

# CSP 中介軟體：為所有回應加上 Content-Security-Policy 標頭
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    csp = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net https://use.fontawesome.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com https://use.fontawesome.com; "
        "img-src 'self' data:;"
    )
    response.headers["Content-Security-Policy"] = csp
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

cookie_scheme = APIKeyCookie(name="admin_token", auto_error=False)

MOCK_ADMIN_DB = {
    "admin": {
        "username": "admin",
        "password_hash": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "totp_secret": "JBSWY3DPEHPK3PXP",
        "role": "superadmin"
    }
}

async def get_current_admin(request: Request, token: str = Depends(cookie_scheme)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authentication Cookie")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or Expired Token")
    username = payload.get("sub")
    if username not in MOCK_ADMIN_DB:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return MOCK_ADMIN_DB[username]

from pydantic import BaseModel
class LoginData(BaseModel):
    username: str
    password: str
    totp: str

# Vercel Serverless Function 預設會根據檔案與路徑映射
# 若此檔案名為 admin_server.py，在未特殊設定 vercel.json 的情況下，Vercel 預設可能不一定能完美支援帶路徑的 FastAPI
# 最安全的做法是讓 FastAPI 的 route 和 Vercel 的預期相符，或者直接透過 vercel.json 做 rewrite
# 這裡維持原有 API 設計，後續會教導您如何設定 vercel.json
@app.post("/api/admin_server/login")
async def login(data: LoginData, request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"
    user = MOCK_ADMIN_DB.get(data.username)
    
    if not user or not verify_password(data.password, user["password_hash"]):
        logger.warning(f"Login failed", extra={"clientip": client_ip, "user": data.username})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
    if not verify_totp(user["totp_secret"], data.totp):
        logger.warning(f"MFA failed", extra={"clientip": client_ip, "user": data.username})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code")
        
    access_token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    
    response = JSONResponse(content={"message": "Login successful", "role": user["role"]})
    
    # 在 Vercel (https) 上，secure=True 是必須且安全的
    response.set_cookie(
        key="admin_token",
        value=access_token,
        httponly=True,
        secure=True, 
        samesite="lax",
        max_age=3600
    )
    
    logger.info(f"Login successful", extra={"clientip": client_ip, "user": data.username})
    return response

@app.post("/api/admin_server/logout")
async def logout(response: Response):
    response.delete_cookie(key="admin_token", httponly=True, secure=True, samesite="lax")
    return {"message": "Logged out successfully"}

@app.get("/api/admin_server/system-status")
async def get_system_status(admin_user: dict = Depends(get_current_admin)):
    return {
        "status": "healthy",
        "active_users": 42,
        "current_user": admin_user["username"],
        "role": admin_user["role"]
    }

class DeleteRequest(BaseModel):
    item_id: str
    totp: str

@app.delete("/api/admin_server/items/{item_id}")
async def delete_item(
    item_id: str, 
    request: Request,
    data: DeleteRequest, 
    admin_user: dict = Depends(get_current_admin)
):
    client_ip = request.client.host if request.client else "unknown"
    
    if not verify_totp(admin_user["totp_secret"], data.totp):
        logger.warning(f"Step-up Auth failed", extra={"clientip": client_ip, "user": admin_user["username"]})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP for critical action")
    
    logger.info(f"Deleted item {item_id}", extra={"clientip": client_ip, "user": admin_user["username"]})
    
    return {"message": f"Item {item_id} successfully deleted"}
