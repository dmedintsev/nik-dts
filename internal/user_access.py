import datetime
import json
import os

import jwt
import requests
from fastapi import HTTPException
from starlette.responses import RedirectResponse, JSONResponse

from dependencies import DTS_USER_GROUP, URL_AUTH, BASE_URL, DTS_ADMIN_GROUP


class UserAuth:
    @staticmethod
    def parse_token(token):
        public_key = open(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'internal', 'jwtRS256.key.pub')).read()
        return jwt.decode(token, public_key, algorithms=['RS256'])

    @staticmethod
    def validate_token(cookies):
        try:
            if 'access_token' in cookies:
                token = cookies['access_token']
                dt_now = datetime.datetime.now()
                dt_token = datetime.datetime.fromtimestamp(UserAuth.parse_token(token)['exp'])
                print((dt_token - dt_now).total_seconds())
                if (dt_token - dt_now).total_seconds() > 0:
                    print(f'validate_token: VALID')
                    return True
        except Exception as exc:
            print(f'validate_token: INVALID')
            print(exc)
        response = RedirectResponse(url=BASE_URL)
        return response

    @staticmethod
    def check_access_rights(login, password):
        raw_data = {
            "username": login,
            "password": password
        }
        dd = requests.post(URL_AUTH, json=raw_data)
        if dd.status_code == 200:
            j = json.loads(dd.text)
            if DTS_ADMIN_GROUP in j['groups']:
                return j['access'], 'DTS_ADMIN'
            elif DTS_USER_GROUP in j['groups']:
                return j['access'], 'DTS_USER'
            else:
                raise HTTPException(status_code=403, detail="Access forbidden")
        else:
            raise HTTPException(status_code=401, detail="Bad username or password")

    @staticmethod
    def set_jwt_cookies(cls):
        pass

    @staticmethod
    def unset_jwt_cookies(cookies):
        content = {"msg": "Successfully logout"}
        response = JSONResponse(content)
        for c in cookies:
            if c in ['access_token', 'user_role']:
                response.delete_cookie(key=c)
            else:
                response.set_cookie(key=c, value=cookies[c])
        return response
