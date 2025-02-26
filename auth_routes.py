defrom fastapi import APIRouter, status, Depends
import datetime
from fastapi.encoders import jsonable_encoder
from sqlalchemy import or_ #yangi
from schemas import SignUpModel, LoginModel
from database import session, engine
from models import User
from fastapi.exceptions import HTTPException

from werkzeug.security import generate_password_hash, check_password_hash

from fastapi_jwt_auth import AuthJWT

auth_router = APIRouter(
    prefix='/auth'
)

session = session(bind=engine)
@auth_router.get('/')
async def welcome(Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_required()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return {'message': 'Bu auth route signup shifasi'}

@auth_router.post('/signup', status_code=status.HTTP_201_CREATED)
async def signup(user: SignUpModel):
    db_email = session.query(User).filter(User.email == user.email).first()
    if db_email is not None:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail='User with this email already exists')
    db_username = session.query(User).filter(User.username == user.username).first()
    if db_username is not None:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail='User with this username already exists')
    new_user = User(
        username=user.username,
        email=user.email,
        password=generate_password_hash(user.password),
        is_active=user.is_active,
        is_staff=user.is_staff
    )
    session.add(new_user)
    session.commit()
    data = {
        'id': new_user.id,
        'username': new_user.username,
        'email': new_user.email,
        'is_staff': new_user.is_staff,
        'is_active': new_user.is_active
    }
    response_model = {
        'success': True,
        'code': 201,
        'message': 'user is created successfull',
        'data': data,
    }
    return response_model
@auth_router.post('/login', status_code=200)
async def login(user:LoginModel, Authorize: AuthJWT=Depends()):

    #db_user = session.query(User).filter(User.username == user.username).first()
    # query with email and username
    db_user = session.query(User).filter(
        or_(
            User.username == user.username_or_email,
            User.email == user.username_or_email
        )
    ).first()
    if db_user and check_password_hash(db_user.password, user.password):
        access_lifetime = datetime.timedelta(minutes=60)  # 60 minut
        refresh_lifetime = datetime.timedelta(days=3)  # 3 kun
        access_token = Authorize.create_access_token(subject=db_user.username,
                                                     expires_time=access_lifetime)
        refresh_token = Authorize.create_refresh_token(subject=db_user.username,
                                                       expires_time=refresh_lifetime)

        token = {
            "access": access_token,
            "refresh": refresh_token
        }
        response = {
            'success': True,
            'code': 201,
            'message': 'user  successfull login',
            'data': token,
        }
        return jsonable_encoder(response)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username or password")

@auth_router.get('/login/refresh')
async def refresh_token(Authorize: AuthJWT=Depends()):
    try:
        access_lifetime = datetime.timedelta(minutes=60) # 60 minut
        #Authorize.jwt_required() # valid access token talab qiladi
        Authorize.jwt_refresh_token_required()
        current_user = Authorize.get_jwt_subject() # access tokenddan username ni ajratib oladi
        # Database dan userni filter orqali topamiz
        db_user = session.query(User).filter(User.username == current_user).first()
        if db_user is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")
        # access token yaratamiz
        new_access_token = Authorize.create_access_token(subject=db_user.username,
                                                        expires_time=access_lifetime)

        response_model = {
            'success': True,
            'code': 200,
            'message': 'New access token is created',
            'data': {
                "access_token": new_access_token
            }
        }
        return response_model
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Refresh token")