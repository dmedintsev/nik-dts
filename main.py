import uvicorn as uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

from internal.user_access import UserAuth
from routers import filter_router, component_router, search_router, article_router

app = FastAPI()

app.include_router(filter_router.router)
app.include_router(component_router.router)
app.include_router(search_router.router)
app.include_router(article_router.router)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class User(BaseModel):
    username: str
    password: str


@app.post('/login')
def login(request: Request, user: User):
    access_token, user_role = UserAuth.check_access_rights(user.username, user.password)
    response = JSONResponse({
        "msg": "Successfully login",
        "access_token": access_token,
        "user_role": user_role
    })
    for c in request.cookies:
        response.set_cookie(key=c, value=request.cookies[c])
    response.set_cookie(key="access_token", value=access_token)
    response.set_cookie(key="user_role", value=user_role)
    return response


@app.delete('/logout')
def logout(request: Request):
    """
    Because the JWT are stored in an httponly cookie now, we cannot
    log the user out by simply deleting the cookies in the frontend.
    We need the backend to send us a response to delete the cookies.
    """
    return UserAuth.unset_jwt_cookies(request.cookies)


@app.get('/protected')
def protected(request: Request):
    """
    We do not need to make any changes to our protected endpoints. They
    will all still function the exact same as they do when sending the
    JWT in via a headers instead of a cookies
    """
    f = UserAuth.validate_token(request.cookies)
    if not isinstance(f, bool):
        return f

    return {"user": 'current_user'}


if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8000)
