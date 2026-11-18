import os

# ===== 환경변수 로드 (.env) — 비밀키는 코드가 아니라 .env 파일에 둔다 =====
def _load_env(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
_load_env()

import subprocess   
import oracledb as cx_Oracle
import sys
import google.generativeai as genai
import requests
from google.api_core import exceptions as google_exceptions
from argon2 import PasswordHasher
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify, render_template_string
from argon2.exceptions import VerifyMismatchError
from UserDAO import UserDAO
from UserDTO import *
from AnimalDAO import AnimalDAO
from AnimalDTO import *
from BoardDAO import BoardDAO
from BoardDTO import *
from db_config import db
from db_config import db as get_connection
import ssl
from werkzeug.middleware.proxy_fix import ProxyFix


def safe_json(res):
    try:
        if res.status_code != 200:
            return None
        return res.json()
    except:
        return None
    
def safe_list(val):
    if not val:
        return []
    if isinstance(val, str):
        return [val]
    if isinstance(val, tuple):
        return list(val)
    if isinstance(val, list):
        return val
    return []


def normalize_animal(animal):
    if animal in ["개", "dog"]:
        return "강아지"
    return animal

ssl._create_default_https_context = ssl._create_unverified_context
os.environ['CURL_CA_BUNDLE'] = ""
os.environ['PYTHONHTTPSVERIFY'] = '0'

# 1. requests 라이브러리의 기본 verify 옵션을 False로 고정
orig_request = requests.Session.request
def new_request(self, method, url, **kwargs):
    kwargs.setdefault('verify', False)
    return orig_request(self, method, url, **kwargs)

requests.Session.request = new_request

from flask_mail import Mail, Message  #비밀번호 찾기
from authlib.integrations.flask_client import OAuth #이메일로 로그인

app = Flask(__name__, template_folder='templates')
app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]

# Flask가 Cloudflare 같은 프록시 뒤에 있음을 알려주어 HTTPS 주소를 올바르게 생성하게 함
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)

#비밀번호 찾기 코드
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')       # 실제 구글 아이디
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')       # 구글에서 발급받은 앱 비밀번호
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER') #구글아이디 한번 더

mail = Mail(app) #비밀번호 찾기 

#이메일로 로그인
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    access_token_url='https://oauth2.googleapis.com/token',
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs',
    client_kwargs={'scope': 'openid email profile'}
)

#카카오로 로그인
oauth.register(
    name='kakao',
    client_id=os.environ.get('KAKAO_CLIENT_ID'),  # 내 REST API 키
    client_secret='',  
    access_token_url='https://kauth.kakao.com/oauth/token',
    authorize_url='https://kauth.kakao.com/oauth/authorize',
    api_base_url='https://kapi.kakao.com/',
    client_kwargs={
        'token_endpoint_auth_method': 'client_secret_post',
    }
)

#세선 키
app.secret_key = os.environ["FLASK_SECRET_KEY"]

GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')
chat = model.start_chat(history=[])

FASTAPI_URL = "http://localhost:8000/recommend"
Bigfive_URL = "http://localhost:8001/recommend"

def get_db():
    if 'db' not in g:
        g.db = db()
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db_conn = g.pop('db', None)
    if db_conn:
        try:
            db_conn.close()
        except cx_Oracle.InterfaceError:
            pass

def get_dao(dao_class):
    return dao_class(get_db())

def convert_counts_to_int(data, count_index):
    """DB에서 가져온 데이터를 순회하며 지정된 인덱스(count_index)의 COUNT 값을 
       표준 Python int 타입으로 변환합니다. (int64 오류 방지)"""
    converted_data = []
    for row in data:
        row_list = list(row)
        
        try:
            row_list[count_index] = int(row_list[count_index])
        except (ValueError, TypeError, IndexError):
            if count_index < len(row_list):
                 row_list[count_index] = 0
        converted_data.append(row_list)
    return converted_data

@app.context_processor
def inject_user():
    return dict(current_user_id=session.get('US_id'))

@app.route('/test_servies', methods = ['GET', 'POST'])
def test_servies():
    return render_template('test_servies.html')

#메인화면
@app.route('/', methods = ['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html')

    user_id = request.form.get('US_id', '').strip()
    user_pw = request.form.get('US_pw', '') 

    if not user_id or not user_pw:
        flash('아이디와 비밀번호를 모두 입력해주세요.')
        return render_template('index.html')

    conn = get_db()
    dao = UserDAO( conn)

    try:
        stored_hash = dao.get_password_hash(user_id)    
        
        if not stored_hash:
            flash('아이디 혹은 비밀번호가 틀렸습니다.')
            return render_template('index.html')

        if ph.verify(stored_hash, user_pw):
            if ph.check_needs_rehash(stored_hash):
                new_hash = ph.hash(user_pw)
                dao.update_password_hash(user_id, new_hash)

            session['US_id'] = user_id
            return redirect(url_for('Login'))
        
        else:
            flash('아이디 혹은 비밀번호가 틀렸습니다.')
            
    except VerifyMismatchError:
        flash('아이디 혹은 비밀번호가 틀렸습니다.')
    except Exception as e:
        print(f"로그인 검증 중 오류: {e}")
        flash('로그인 중 오류가 발생했습니다.')
    finally:
        conn.close()

    return render_template('index.html')

#로그인
@app.route('/Login', methods=['GET', 'POST'])
def Login():
    if 'US_id' not in session:
        return redirect(url_for('index'))  # 👉 비로그인 → index (OK 👍)

    US_id = session.get('US_id')

    conn = get_db()
    dao = UserDAO(conn)
    get_name = dao.username(US_id)

    session['US_name'] = get_name

    # ❌ redirect 금지
    # return redirect(url_for('Login'))

    # ✅ 그냥 페이지 렌더
    return render_template(
        'Login.html',
        Login_id=US_id,
        US_name=get_name
    )

#로그아웃
@app.route('/Logout' , methods = ['GET', 'POST'])
def Logout():
    session.pop('US_id', None)
    session.clear()
    return render_template('index.html')

#회원탈퇴시 코드 전송
@app.route('/send_withdraw_code', methods=['POST'])
def send_withdraw_code():
    import random
    # 화면의 이메일 입력창(name="user_email")에서 값 가져오기
    user_email = request.form.get('user_email', '').strip()
    
    if not user_email:
        return jsonify({"result": "fail", "message": "이메일을 입력해 주세요."})

    # 인증번호 생성 및 세션 저장
    code = str(random.randint(100000, 999999))
    session['withdraw_auth_code'] = code
    
    try:
        # 이미지에 있던 메일 발송 방식 그대로 적용
        msg = Message("회원탈퇴 인증번호", recipients=[user_email])
        msg.body = f"SoulPaw 회원탈퇴 인증번호는 [{code}] 입니다. 요청하지 않으셨다면 주의하세요."
        mail.send(msg)
        
        return jsonify({"result": "success", "message": "이메일로 인증번호를 보냈습니다."})
    except Exception as e:
        return jsonify({"result": "error", "message": "메일 발송에 실패했습니다."})

# 회원탈퇴 페이지
@app.route('/Withdraw', methods=['GET', 'POST'])
def Withdraw():
    # 1. 로그인 여부 확인
    US_name = session.get('US_name')
    if 'US_id' not in session:
        if request.method == 'GET':
            flash('로그인이 필요합니다.')
            return redirect(url_for('Login'))
        return jsonify({"result": "fail", "message": "로그인이 필요합니다."})

    # 2. 페이지 보여주기 (사용자가 탈퇴 버튼 눌러서 들어왔을 때)
    if request.method == 'GET':
        return render_template('Withdraw.html', US_name = US_name)

    # 3. 실제 탈퇴 처리 (사용자가 인증번호 입력 후 '탈퇴 확정' 눌렀을 때)
    user_id = session['US_id']
    input_code = request.form.get('auth_code') # HTML에서 입력한 번호
    server_code = session.get('withdraw_auth_code') # 세션에 저장된 진짜 번호

    # 인증번호 검증
    if not input_code or input_code != server_code:
        return jsonify({"result": "fail", "message": "인증번호가 일치하지 않습니다."})

    conn = get_db()
    dao = UserDAO(conn)
    
    try:
        # DB 삭제 처리 (기존 DAO의 secession 함수 활용)
        result = dao.secession(user_id)
        
        if result:
            # 모든 세션 제거 (로그아웃 처리)
            session.clear()
            return jsonify({"result": "success", "message": "그동안 SoulPaw를 이용해 주셔서 감사합니다."})
        else:
            return jsonify({"result": "fail", "message": "회원탈퇴 처리 중 오류가 발생했습니다."})
            
    except Exception as e:
        print(f"회원탈퇴 오류: {e}")
        return jsonify({"result": "error", "message": "서버 통신 오류가 발생했습니다."})
    finally:
        conn.close()

#MBTI 또는 Bigfive 선택
@app.route('/select_method', methods = ['GET', 'POST'])
def select_method():
    US_id = session.get('US_id')
    US_name = session.get('US_name')
    if not US_id:
        if request.method == 'POST':
            return jsonify({"error": "Unauthorized", "message": "로그인이 필요합니다."}), 401
        return redirect(url_for('index'))
    return render_template('select_method.html', Login_id=US_id, US_name = US_name)

#아이디 찾기 페이지
@app.route('/FindAuth')
def find_id_page():
    return render_template("FindAuth.html", step="email")

#아이디 찾기
@app.route('/find_id_send', methods=['POST'])
def find_id_send():
    import random
    
    user_email = request.form.get('user_email', '').strip()
    
    conn = get_db()
    dao = UserDAO(conn)
    found_id = dao.find_id_by_email(user_email)
    conn.close()

    if found_id:
        code = str(random.randint(100000, 999999))
        session['auth_code'] = code
        session['temp_user_id'] = found_id
        session['auth_email'] = user_email
        
        msg = Message("아이디 찾기 인증번호", recipients=[user_email])
        msg.body = f"인증번호: {code}"
        mail.send(msg)
        
        flash("인증번호를 보냈습니다.")
        return render_template("FindAuth.html", step="auth")
    else:
        flash("해당 이메일 없음")
        return render_template("FindAuth.html", step="email")
    
#아이디 찾기 코드 재발송
@app.route('/find_id_resend', methods=['POST'])
def find_id_resend():
    user_email = session.get('auth_email')
    
    if not user_email:
        return "Session Expired", 400
        
    import random
    code = str(random.randint(100000, 999999))
    session['auth_code'] = code  
    
    try:
        msg = Message("아이디 찾기 인증번호", recipients=[user_email])
        msg.body = f"인증번호: {code}"  
        mail.send(msg)
        return "Success", 200
    except Exception as e:
        print(f"인증번호 재발송 오류: {e}")
        return "Mail Error", 500
    
#아이디 확인  
@app.route('/find_id_confirm', methods=['POST'])
def find_id_confirm():
    user_code = request.form.get('auth_code')

    if user_code == session.get('auth_code'):
        found_id = session.get('temp_user_id')

        session.clear()

        return render_template("FindAuth.html", step="result", user_id=found_id)
    else:
        flash("인증번호 틀림")
        return render_template("FindAuth.html", step="auth")

#비밀번호 찾기
@app.route('/find_pw', methods=['POST'])
def find_pw():
    user_id = request.form.get('user_id')
    user_email = request.form.get('user_email')
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM User_ID_tbl WHERE USER_ID = :1 AND EMAIL = :2",
        [user_id, user_email]
    )
    user = cursor.fetchone()
    conn.close()
    if user:
        import random, string
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        session['reset_code'] = code
        session['reset_user'] = user_id
        session['auth_email'] = user_email
        msg = Message("비밀번호 재설정 인증 코드", recipients=[user_email])
        msg.body = f"인증코드: {code}"
        mail.send(msg)
        flash("인증코드를 이메일로 보냈습니다.")
        return render_template("FindAuth.html", step='pw_auth')
    else:
        flash("정보가 일치하지 않습니다.")
        return render_template("FindAuth.html", step="email")

#비밀번호 찾기 코드 재발송  
@app.route('/find_pw_resend', methods=['POST'])
def find_pw_resend():
    user_email = session.get('auth_email')
    
    if not user_email:
        return "Session Expired", 400
        
    # 새로운 비밀번호 재설정 인증코드 생성 및 세션 갱신
    import random, string
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    session['reset_code'] = code  # 기존 reset_code 덮어쓰기
    
    try:
        # 이메일 발송 (제목과 본문은 기존 비밀번호 찾기 양식에 맞게 조절하세요)
        msg = Message("비밀번호 재설정 인증코드 (재발송)", recipients=[user_email])
        msg.body = f"변경 인증코드: {code}"
        mail.send(msg)
        return "Success", 200
    except Exception as e:
        print(f"비밀번호 재발송 오류: {e}")
        return "Mail Error", 500

#새 비밀번호
@app.route('/reset_pw', methods=['POST'])
def reset_pw():
    input_code = request.form.get('reset_code')
    new_pw = request.form.get('new_pw')
    if input_code != session.get('reset_code'):
        flash("인증코드가 틀렸습니다.")
        return render_template("FindAuth.html", step="pw_auth")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        hashed_pw = ph.hash(new_pw)
        cursor.execute(
            "UPDATE User_ID_tbl SET USER_PW = :1 WHERE USER_ID = :2",
            [hashed_pw, session.get('reset_user')]
        )
        conn.commit()
        conn.close()
        session.clear()
        flash("비밀번호 변경 완료")
        return render_template("FindAuth.html", step="pw_result")
    except Exception as e:
        print(e)
        flash("오류 발생")
        return render_template("FindAuth.html", step="pw_auth")

#구글로 로그인 버튼 클릭시 이동
@app.route('/login/google')
def login_google():
    redirect_url = url_for('google_auth', _external=True)
    return google.authorize_redirect(redirect_url, prompt='select_account')

#구글 인증 후 돌아오는 경로
@app.route('/login/google/authorize')
def google_auth():
    error = request.args.get('error')
    if error:
        print(f"구글 로그인 취소/에러 발생: {error}")
        return render_template_string('''
            <script>
                alert("구글 로그인이 취소되었습니다.");
                location.href = "/Login"; /* 기존 로그인 페이지 주소 */
            </script>
        ''')
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    email = user_info['email']

#구글 이름에서 공백을 제거하거나 앞부분만 따서 ID로 사용(최대 12자 제한 대응)
    google_id = email.split('@')[0][:12]

    conn = get_connection()
    cursor = conn.cursor()

# 1. DB에 해당 이메일이 있는지 확인
    cursor.execute("SELECT USER_ID FROM USER_ID_tbl WHERE EMAIL = :1", [email])
    user = cursor.fetchone()

    if not user:
        # [신규 유저] 세션에 정보만 담고 닉네임 설정 페이지로 이동
        session['temp_google_email'] = email
        session['temp_google_id'] = google_id
        
        cursor.close()
        conn.close()
        return redirect(url_for('set_name'))
    else:
        # [기존 유저] 바로 로그인 처리
        session['US_id'] = user[0]

    cursor.close()
    conn.close()

    return redirect(url_for('Login'))

#카카오로 로그인 버튼 클릭시 이동
@app.route('/login/kakao')
def kakao_login():
    client_id = os.environ.get('KAKAO_CLIENT_ID')
    redirect_uri = url_for('kakao_auth', _external=True)
    kakao_url = f"https://kauth.kakao.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&prompt=select_account"
    return redirect(kakao_url)

#카카오 인증 후 돌아오는 경로
@app.route('/login/kakao/authorize')
def kakao_auth():
    code = request.args.get('code')
    if not code:
        return "<script>alert('로그인에 실패했습니다.'); location.href='/';</script>"
    
    token_url = "https://kauth.kakao.com/oauth/token"
    headers = {"Content-type": "application/x-www-form-urlencoded;charset=utf-8"}
    
    redirect_uri = url_for('kakao_auth', _external=True)
    
    data = {
        "grant_type": "authorization_code",
        "client_id": os.environ.get("KAKAO_CLIENT_ID"),
        "redirect_uri": redirect_uri,
        "code": code
    }
    
    # 1. 카카오 토큰 및 유저 정보 수신
    token_response = requests.post(token_url, headers=headers, data=data)
    token_json = token_response.json()
    
    if 'access_token' not in token_json:
        return "<script>alert('인증 토큰 발급에 실패했습니다.'); location.href='/';</script>"
        
    access_token = token_json['access_token']
    
    user_info_url = "https://kapi.kakao.com/v2/user/me"
    user_info_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-type": "application/x-www-form-urlencoded;charset=utf-8"
    }
    user_response = requests.post(user_info_url, headers=user_info_headers)
    user_info = user_response.json()
    
    kakao_account = user_info.get('kakao_account', {})
    email = kakao_account.get('email')
    
    if not email:
        return "<script>alert('이메일 제공 동의가 필요합니다.'); location.href='/';</script>"

    # 구글 회원과 겹치지 않게 뒤에 _k를 명시적으로 붙여 중복 가입 에러를 방지합니다.
    kakao_id = email.split('@')[0][:9] + "_k"

    conn = get_connection()
    cursor = conn.cursor()

    # 2. DB에 해당 카카오 이메일이 있는지 확인
    cursor.execute("SELECT USER_ID FROM USER_ID_tbl WHERE EMAIL = :1", [email])
    user = cursor.fetchone()

    if not user:
        # [신규 유저] 구글과 완벽히 동일한 세션 변수명에 담고 닉네임 설정 페이지로 이동
        session['temp_google_email'] = email
        session['temp_google_id'] = kakao_id
        
        cursor.close()
        conn.close()
        return redirect(url_for('set_name'))
    else:
        # [기존 유저] 바로 로그인 처리
        session['US_id'] = user[0]
        
    cursor.close()
    conn.close()

    # 구글 코드 스타일대로 로그인 성공 후 'Login' 라우트로 리다이렉트
    return redirect(url_for('Login'))

#닉네임 작성
@app.route('/set_name', methods=['GET', 'POST'])
def set_name():
    if request.method == 'GET':
        if 'temp_google_email' not in session:
            return redirect('/')
        return render_template('set_name.html')

    # POST: 닉네임 제출 시
    new_nickname = request.form.get('user_name')
    email = session.get('temp_google_email')
    google_id = session.get('temp_google_id')

    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 최종적으로 DB에 유저 정보 저장
        cursor.execute("""
            INSERT INTO USER_ID_tbl (USER_ID, USER_PW, EMAIL, NAME)
            VALUES (:1, :2, :3, :4)
        """, [google_id, 'SOCIAL_GOOGLE_LOGIN', email, new_nickname])
        conn.commit()
        
        # 가입 완료 후 로그인 상태로 변경
        session['US_id'] = google_id
        # 임시 세션은 반드시 삭제
        session.pop('temp_google_email', None)
        session.pop('temp_google_id', None)
        
    except Exception as e:
        print(f"회원가입 오류: {e}")
        conn.rollback()
        return "<script>alert('이미 사용 중인 정보이거나 오류가 발생했습니다.'); history.back();</script>"
    finally:
        cursor.close()
        conn.close()

    return "<script>alert('반갑습니다! 가입이 완료되었습니다.'); location.href='/';</script>"

#회원가입
@app.route('/NewUser', methods=['GET', 'POST'])
def NewUser():
    if request.method == 'GET':
        # 페이지 진입 시 중복체크 상태 초기화
        session.pop('id_checked', None)
        return render_template('NewUser.html')

    # POST 요청 (회원가입 버튼 클릭 시)
    user_id = request.form.get('NW_id', '').strip()
    user_pw = request.form.get('NW_pw', '')
    user_pw_1 = request.form.get('NW_pw_1', '')
    user_email = request.form.get('US_email', '').strip()
    user_name = request.form.get('US_name','').strip()

    # 1. 중복 확인 여부 체크 (세션 확인)
    if not session.get('id_checked') or session.get('checked_user_id') != user_id:
        flash('아이디 중복 확인을 먼저 해주세요.')
        return render_template('NewUser.html')

    # 2. 비밀번호 일치 확인
    if user_pw != user_pw_1:
        flash('비밀번호가 서로 다릅니다.')
        return render_template('NewUser.html')
    if not user_email: # 이메일이 비어있는지 체크
        flash('이메일을 입력해주세요.')
        return render_template('NewUser.html')
    if not user_name:
        flash('닉네임을 작성해주세요')
        return render_template('NewUser.html')

    conn = get_db()
    dao = UserDAO(conn)

    try:
        # 3. 실제 DB에 아이디가 있는지 최종 확인 (보안)
        if dao.duplicate(user_id):
            flash('이미 사용 중인 아이디입니다.')
            return render_template('NewUser.html')
        if dao.uni_name(user_name):
            flash('이미 사용 중인 닉네임입니다.')
            return render_template('NeuUser.html')
        if dao.uni_email(user_email):
            flash('이미 있는 이메일입니다.')
            return render_template('NewUser.html')
        # 4. 해싱 및 저장
        hashed_pw = ph.hash(user_pw)
        new_user_dto = UserDTO(user_id, hashed_pw,user_email,user_name) 
        dao.insert_user(new_user_dto)
        
        # 성공 시 세션 정리
        session.pop('id_checked', None)
        session.pop('checked_user_id', None)
        
        flash('회원가입이 완료되었습니다. 로그인 해주세요.')
        return redirect(url_for('index'))

    except Exception as e:
        print(f"회원가입 오류: {e}")
        flash('회원가입 중 오류가 발생했습니다.')
        return render_template('NewUser.html')
    finally:
        conn.close()

#사용자 정보수정
@app.route('/Useredit', methods=['GET', 'POST'])
def Useredit():
    if 'US_id' not in session:
        return redirect(url_for('index'))
    US_id = session.get('US_id')
    US_name = session.get('US_name')
    if request.method == 'POST':
        US_pw = request.form.get('US_pw', '').strip()
        user_name = request.form.get('user_name', '').strip()
        conn = get_db()
        dao = UserDAO(conn)
        if US_pw:
            hashed_pw = ph.hash(US_pw)
            new_user_dto = Update_user(US_id, hashed_pw, user_name)
        else:
            new_user_dto = Update_user(US_id, None, user_name)

        dao.Update_user(new_user_dto)
        conn.close()

        return redirect(url_for('Login'))
    return render_template('Useredit.html', US_name = US_name, US_id = US_id)

#중복체크
@app.route('/reset_id_check', methods=['POST'])
def reset_id_check():
    session.pop('id_checked', None)
    session.pop('checked_user_id', None)
    return '', 204

#중복 아이디
@app.route('/dup', methods=['POST'])
def dup():
    user_id = request.form['NW_id']
    if not user_id:
        return "이이디를 입력해주세요."
    conn = get_db()
    dao = UserDAO(conn)
    
    duplication = dao.duplicate(user_id)

    if duplication:
        session['id_checked'] = False
        return "이미 있는 아이디 입니다."
    else:
        session['id_checked'] = True
        session['checked_user_id'] = user_id
        return "사용 가능한 아이디 입니다."

@app.route('/Bigfive', methods=['GET'])
def bigfive_page():
    US_id = session.get('US_id')
    US_name = session.get('US_name')

    if not US_id:
        return redirect(url_for('index'))

    return render_template('Bigfive.html', Login_id=US_id, US_name=US_name)

def clean_text(text):
    if not text:
        return "리포트를 생성할 수 없습니다."
    text = text.lstrip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

#빅파이브 추천화면
@app.route('/Animalbeer/bigfive', methods=['POST'])
def bigfive():
    US_id = session.get('US_id')
    US_name = session.get('US_name')

    if not US_id:
        return jsonify({"error": "로그인 필요"}), 401

    conn = None

    try:
        q = [int(request.form.get(f"q{i}", 3)) for i in range(1, 11)]

        ext = round((q[0] + q[1]) / 2 / 5, 2)
        agr = round((q[2] + q[3]) / 2 / 5, 2)
        con = round((q[4] + q[5]) / 2 / 5, 2)
        neu = round((q[6] + q[7]) / 2 / 5, 2)
        ope = round((q[8] + q[9]) / 2 / 5, 2)

        house = request.form.get('house', '').strip()
        yard = request.form.get('yard', '').strip()

        if not house or not yard:
            return jsonify({"error": "거주환경 선택 필요"}), 400
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT ANIMAL_BREED
            FROM RECEIVED_ANIMAL
            WHERE USER_ID = :1
        """, [US_id])

        exclude_list = [r[0] for r in cursor.fetchall()] if cursor else []

        payload = {
            "O": ope,
            "C": con,
            "E": ext,
            "A": agr,
            "N": neu,
            "environment": house,
            "yard": yard,
            "exclude": exclude_list
        }

        res = requests.post(
            "http://127.0.0.1:8001/recommend_bigfive",
            json=payload,
            timeout=60
        )

        if res.status_code != 200:
            raise Exception(res.text)

        data = res.json()

        if data.get("status") == "error":
            raise Exception(data.get("message"))

        animal_type = data.get("animal", "").strip()
        breed = data.get("breed", "").strip()
        score = data.get("score", 0)

        full_text = clean_text(data.get("full_text", ""))

        if not animal_type or not breed:
            raise ValueError("추천 결과 파싱 실패")

        ANDAO = AnimalDAO(conn)

        if ANDAO.get_Animal(User_id=US_id):
            ANDAO.delet(User_id=US_id)

        ANDAO.re_animal(UserAnimalList(US_id, animal_type, breed, "BIG5"))
        ANDAO.InAnimal(AnimalDTO(US_id, "BIG5", "BIG5", animal_type, breed))

        conn.commit()

        # =========================
        # 5. 세션 저장
        # =========================
        session['animal_result_data'] = {
            'Text': full_text,
            'mal': animal_type,
            'anibreed': breed,
            'score': score,
            'Login_id': US_id,
            'US_name': US_name,
            'house': house,
            'yard': yard,
            'big5': {
                'E': ext, 'A': agr, 'C': con, 'N': neu, 'O': ope
            }
        }

        return jsonify({"redirectUrl": url_for('bigfive_result')})

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[Big5 ERROR]: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            conn.close()

#Bigfiv 추천로직
@app.route('/result_big5')
def bigfive_result():
    data = session.get('animal_result_data') 
    US_name = session.get('US_name')
    Login_id = session.get('US_id')
    if not data:
        return redirect(url_for('Bigfive'))
    data = session.get('animal_result_data')
    
    return render_template("Bigfiveresults.html", 
                           data=data, 
                           mal=data.get('mal'),
                           anibreed=data.get('anibreed'),
                           US_name=US_name, 
                           Login_id=Login_id)

#Bigfive
@app.route('/Animalbeer/re_recommend', methods=['POST'])
def re_recommend():
    US_id = session.get('US_id')
    old_data = session.get('animal_result_data')

    if not US_id or not old_data:
        return jsonify({"error": "세션 만료"}), 401

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT ANIMAL_BREED 
            FROM RECEIVED_ANIMAL 
            WHERE USER_ID = :1
        """, [US_id])

        exclude_list = [r[0] for r in cursor.fetchall()]

        big5 = old_data.get('big5', {})

        payload = {
            "O": float(big5.get('O', 0.5)),
            "C": float(big5.get('C', 0.5)),
            "E": float(big5.get('E', 0.5)),
            "A": float(big5.get('A', 0.5)),
            "N": float(big5.get('N', 0.5)),
            "environment": old_data.get('house', '아파트'),
            "yard": old_data.get('yard', '없음'),
            "exclude": exclude_list
        }

        res = requests.post(
            "http://127.0.0.1:8001/recommend_bigfive",
            json=payload,
            timeout=60
        )

        data = res.json()

        if data.get("status") == "error":
            raise Exception(data.get("message"))

        animal = data.get("animal")
        breed = data.get("breed")
        score = data.get("score", 0)

        text = clean_text(data.get("full_text"))

        # DB 업데이트
        ANDAO = AnimalDAO(conn)

        if ANDAO.get_Animal(User_id=US_id):
            ANDAO.delet(User_id=US_id)

        ANDAO.re_animal(UserAnimalList(US_id, animal, breed, "BIG5"))
        ANDAO.InAnimal(AnimalDTO(US_id, "BIG5", "BIG5", animal, breed))

        conn.commit()

        # 세션 갱신
        old_data.update({
            'Text': text,
            'mal': animal,
            'anibreed': breed,
            'score': score
        })

        session['animal_result_data'] = old_data
        session.modified = True

        return jsonify({
            "success": True,
            "redirectUrl": url_for('bigfive_result')
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[Re ERROR]: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            conn.close()

# 동물 추천화면
@app.route('/Animalbeer', methods=['GET', 'POST'])
def Animalbeer():
    US_id = session.get('US_id')
    US_name = session.get('US_name')

    if not US_id:
        return jsonify({
            "error": "Unauthorized",
            "message": "로그인이 필요합니다.",
            "redirectUrl": url_for('index')
        }), 401

    if request.method == 'POST':
        US_pe = request.form.get('US_pe', '없음')
        Good_animal = request.form.get('Good_animal', '').strip()
        Be_animal = request.form.get('Be_animal', '').strip()
        house = request.form.get('house') or "아파트"
        US_MBTI = (request.form.get('US_MBTI') or "INTJ").upper()
        yard = request.form.get('yard_value') or "X"
        print(f"🔥 입력값: {US_MBTI} {house} {yard} {Good_animal} {Be_animal}")
        try:
            res = requests.post(FASTAPI_URL, json={
                "mbti": US_MBTI,
                "environment": house,
                "yard": yard,
                "prefer": Good_animal or "없음",
                "dislike": Be_animal or "없음",
            }, timeout=40)

            if res.status_code == 200:
                data = res.json()
            else:
                print(f"🔥 AI 서버 응답 이상: {res.status_code}")
                raise Exception("AI 서버 응답 오류")

        except Exception as e:
            print(f"🔥 AI 호출 중 에러 발생: {e}")
            data = {
                "animal": "고양이",
                "breed": "코리안숏헤어",
                "full_text": "AI 서버와 연결이 원활하지 않아 기본 추천 결과를 제공합니다. 잠시 후 다시 시도해 주세요!"
            }
        
        animal_type = normalize_animal(
            data.get("animal", "강아지")
        )

        animal_breed = data.get("breed", "말티즈")

        animal_text = data.get(
            "full_text",
            "추천 결과를 생성할 수 없습니다."
        )
    
        conn = get_db()
        try:
            ANDAO = AnimalDAO(conn)   
            ANDAO.delet(User_id=US_id)
            ANDAO.re_animal(UserAnimalList(US_id, animal_type, animal_breed, US_MBTI))
            ANDAO.InAnimal(AnimalDTO(US_id, US_pe, US_MBTI, animal_type, animal_breed))
            
            conn.commit() 
        except Exception as e:
            conn.rollback()
            print(f"🔥 DB 저장 에러: {e}")
        finally:
            conn.close()

        session['animal_result_data'] = {
            'Text': animal_text,
            'mal': animal_type,
            'anibreed': animal_breed,
            'Login_id': US_id,
            'Good_animal': Good_animal,
            'Be_animal': Be_animal,
            'US_pe': US_pe,
            'US_MBTI': US_MBTI,
            'house': house,
            'yard': yard
        }
        session.modified = True
        return jsonify({
            "redirectUrl": url_for('show_animal_result')
        })

    return render_template('Animalbeer.html', Login_id=US_id, US_name=US_name)

@app.route('/show_animal_result')
def show_animal_result():
    US_name = session.get('US_name')
    result_data = session.get('animal_result_data')
    print("🔥 결과 페이지 세션:", result_data)
    # 세션 없으면 로그인 이동
    if result_data is None:
        return redirect(url_for('Login'))
    print("🔥 MBTI:", result_data.get('US_MBTI'))
    result_data['US_name'] = US_name
    return render_template(
        'beer.html',
        **result_data
    )

# 동물 재추첨
@app.route('/beer', methods=['GET', 'POST'])
def beer():
    US_id = session.get('US_id')
    if not US_id:
        return jsonify({"error": "login required"}), 401

    if request.method == 'POST':
        try:
            US_pe = request.form.get('US_pe', '없음')
            Good_animal = (
                request.form.get('Good_animal', '')
                .strip()
            )

            Be_animal = (
                request.form.get('Be_animal', '')
                .strip()
            )

            if Good_animal == "":
                Good_animal = "없음"

            if Be_animal == "":
                Be_animal = "없음"
            house = request.form.get('house') or "아파트"
            yard = request.form.get('yard_value') or "X"
            US_MBTI = (request.form.get('US_MBTI') or "INTJ").upper()

            conn = get_db()
            animal_dao = AnimalDAO(conn)

            previous_breeds = animal_dao.get_beerd(US_id) or []

            if isinstance(previous_breeds, str):
                previous_breeds = [previous_breeds]
            elif isinstance(previous_breeds, tuple):
                previous_breeds = list(previous_breeds)
            elif not isinstance(previous_breeds, list):
                previous_breeds = []

            cursor = conn.cursor()

            cursor.execute("""
                SELECT ANIMAL_BREED
                FROM (
                    SELECT ANIMAL_BREED
                    FROM RECEIVED_ANIMAL
                    WHERE USER_ID = :1
                    ORDER BY CREATE_DATE DESC
                )
                WHERE ROWNUM <= 5
            """, [US_id])

            previous_breeds = [
                str(row[0]).strip()
                for row in cursor.fetchall()
                if row[0]
            ][:5]
            previous_breeds = previous_breeds[-5:]
            payload = {
                "mbti": US_MBTI,
                "environment": house,
                "yard": yard,
                "prefer": Good_animal,
                "dislike": Be_animal,
                "exclude_breeds": previous_breeds, # 이 부분이 FastAPI의 UserInput과 매칭됨
            }
            # 최근 5개 제외
            print("🔥 request.form =", request.form)

            print("🔥 제외 품종:", previous_breeds)
            print(f"🔥 [Flask] FastAPI로 보내는 데이터: {payload}")
            try:
                res = requests.post(
                    FASTAPI_URL,
                    json=payload,
                    timeout=40
                )

                print("🔥 상태코드:", res.status_code)

                if res.status_code != 200:
                    raise Exception(res.text)

                data = res.json()

            except Exception as e:
                print("🔥 AI 실패:", e)
                data = {}
            animal_type = normalize_animal(
                data.get("animal", "강아지")
            )

            animal_breed = data.get("breed", "말티즈")

            animal_text = data.get(
                "full_text",
                "추천 결과를 생성할 수 없습니다."
            )

            try:
                if animal_type and animal_breed:
                    animal_dao.re_animal(UserAnimalList(US_id, animal_type, animal_breed, US_MBTI))
                    animal_dao.InAnimal(AnimalDTO(US_id, US_pe, US_MBTI, animal_type, animal_breed))

                conn.commit()

            except Exception as e:
                conn.rollback()
                print("🔥 DB 실패:", e)

            session['animal_result_data'] = {
                'Text': animal_text,
                'mal': animal_type,
                'anibreed': animal_breed,
                'Login_id': US_id,
                'Good_animal': Good_animal,
                'Be_animal': Be_animal,
                'US_pe': US_pe,
                'US_MBTI': US_MBTI,
                'house': house,
                'yard': yard
            }
            session.modified = True

            print("🔥 저장된 세션:", session['animal_result_data'])
            print("🔥 저장된 MBTI:", session['animal_result_data'].get('US_MBTI'))
            return jsonify({"redirectUrl": url_for('show_animal_result')})
        
        except Exception as e:
            print("🔥 전체 에러:", e)
            return jsonify({
                "error": "server error",
                "message": "추천 중 오류 발생",
                "redirectUrl": url_for('show_animal_result')
            }), 200

    return redirect(url_for('show_animal_result'))

#동물 관련 질문 화면
@app.route('/info', methods = ['GET', 'POST'])
def info():
    US_name = session.get('US_name')
    US_id = session.get('US_id')
    if not US_id:
        if request.method == 'POST':
            return jsonify({"error": "Unauthorized", "message": "로그인이 필요합니다."}), 401
        return redirect(url_for('index'))
    if request.method == 'POST':
        try:
            US_qe = request.form['US_qe']
        except KeyError:
            return jsonify({'Gemitext': '오류: 질문 내용을 입력하지 않았습니다.'}), 400
        animal_info_system_prompt = (
            "너는은 반려동물 전문가입니다. 동물 관련 질문에만 답하고, "
            "답변은 항상 300글자 이내로 제공해줘. "
            "동물 관련 질문이 아닌 경우 '동물 관련 질문만 해주세요.'라고 답해줘. "
            "답변에서 동물 종류나 품종을 언급할 때 --나 ^^ 같은 구분자는 사용하지 마세요. 가독성 좋게 줄내릴때마다 \n해줘 답변해줘."
        )
        full_query = f"{animal_info_system_prompt}\n\n사용자 질문: {US_qe}"
        try:
            response = chat.send_message(full_query)
            Gemini_text = response.text
            print(Gemini_text)
        
        except google_exceptions.ResourceExhausted as e:
            print(f'[Quota Exceeded Error]: {e}')
            return jsonify({
                "error": "Quota Exceeded", 
                "message": "API 사용량 제한(쿼터)을 초과하여 답변을 생성할 수 없습니다. 잠시 후 다시 시도해 주세요. (자세한 오류: 429 ResourceExhausted)"
            }), 429
        
        except Exception as e:
            print(f'[AI Error]: {e}')
            return jsonify({'Gemitext': f'AI 답변 생성 중 오류가 발생했습니다. (상세: {e})'}), 500

        
        if Gemini_text.strip() != "":
            return jsonify({'Gemitext': Gemini_text})
        else:
            return jsonify({'Gemitext': 'AI가 답변을 생성하지 못했습니다.'}), 500
            
    return render_template('info.html', Login_id=US_id, US_name = US_name)

#추천 동물 통계
@app.route('/Group', methods = ['GET','POST'])
def Group():
    US_id = session.get('US_id')
    US_name = session.get('US_name')
    conn = get_db()
    try:
        Group_dao = AnimalDAO(conn)
        total = Group_dao.group_total()
        all = Group_dao.group_all()
    finally:
        conn.close()
    
    return render_template('Group.html', 
                           animal_one = all, 
                           animal_select = all,
                           animal_total_stats = total,
                           is_filtered = False,
                           Login_id = US_id,
                           US_name = US_name)



#추천 동물 통계 세부정보
@app.route('/Ani_in', methods=['GET', 'POST'])
def Ani_in():
    US_id = session.get('US_id')
    US_name = session.get('US_name')
    MBTI = request.form['MBTI'].strip().upper()
    animal = request.form['animal'].strip().replace('"', '').replace("'", "")  
    conn = get_db()
    try:
        breed_dao = AnimalDAO(conn)
        breed = breed_dao.breed_animal(MBTI,animal)
    finally:
        conn.close()
    
    # JS용 데이터: [품종, 인원]
    animal_one = [[row[0], row[1]] for row in breed]
    return render_template(
        'Ani_in.html',
        animal_all=breed,
        mbti_type=MBTI,
        animal_type=animal,
        animal_one=animal_one,
        Login_id = US_id,
        US_name = US_name
    )


#MBTI로 검색
@app.route('/sub_select', methods=['POST'])
def sub_select():
    # 1. 폼 데이터 가져오기 (값이 없을 때 처리)
    selected_mbti = request.form.get('Users', '').strip()
    US_name = session.get(('US_name'))
    if not selected_mbti:
        return redirect("/Group")

    conn = get_db()
    try:
        mbti_dao = AnimalDAO(conn)
        
        # 2. 필터링된 데이터 조회
        mbti_data = mbti_dao.filtered(selected_mbti)

        # 3. 드롭다운 목록 유지용 데이터 조회
        drop = mbti_dao.animal_drop()
    except Exception as e:
        print(f"Error during sub_select: {e}")
        return redirect("/Group")
    finally:
        conn.close()

    return render_template(
        'Group.html',
        animal_one=mbti_data,           
        animal_total_stats=mbti_data,  
        animal_select=drop,       
        is_filtered=True,
        selected_mbti=selected_mbti,
        US_name = US_name
    )


# 추천 받았던 동물
@app.route('/User_Animal', methods = ['GET', 'POST'])
def User_Animal():
    US_id = session.get('US_id')
    US_name = session.get('US_name')
    conn = get_db()
    try:
        ANDAO = AnimalDAO(conn)
        result = ANDAO.get_user_animals(US_id)
    finally:
        conn.close()
    return render_template('User_Animal.html', list = result, User_id = US_id, US_name = US_name)

# 게시판 메인화면
@app.route('/board', methods=['GET'])
def board():
    US_id = session.get('US_id')
    US_name = session.get('US_name')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    conn = get_db()
    board_dao = BoardDAO(conn)
    total_count = board_dao.get_total_count()
    total_pages = (total_count + per_page - 1) // per_page  
    offset = (page - 1) * per_page
    board_main = board_dao.boardmain(offset, per_page)
    return render_template("board.html",
                           board_main=board_main,
                           User_id=US_id,
                           page=page,
                           total_pages=total_pages,
                           US_name = US_name)

# 게시판 작성
@app.route('/write', methods=['GET', 'POST'])
def write():
    US_id = session.get('US_id')
    US_name = session.get('US_name')
    if request.method == 'POST':
        US_id = session.get('US_id')
        title_original = request.form.get('title')
        content_original = request.form.get('content')
        title = title_original.strip() if title_original else None
        content = content_original.strip() if content_original else None

        if not title or not content:
            flash("제목과 내용을 모두 입력해야 합니다 (공백만 입력 불가).")
            return render_template('Write.html', user_id=US_id)

        conn = get_db()
        board_dao = BoardDAO(conn)
        
        try:
            user_personality = board_dao.check_write_power(US_id)
            if not user_personality:
                flash("게시글 작성 전에 성격/MBTI/선호 동물 정보를 등록해야 합니다.")
                return render_template('Write.html', User_id=US_id)

            # 데이터가 있으면 게시글 작성
            board_dao = BoardDAO(conn)
            board_dao.in_board(US_id, title, content)
            conn.commit()
            return redirect(url_for('board'))

        except Exception as e:
            conn.rollback()
            print(f"DB Error: {e}")
            flash("게시글 저장 중 오류가 발생했습니다.")
            return render_template('Write.html', User_id=US_id,US_name = US_name)
        
    return render_template('Write.html', User_id = US_id, US_name = US_name)

#검색 기능
@app.route('/board/search', methods=['GET'])
def search():
    keyword = request.args.get('keyword', '').strip()
    page = request.args.get('page', 1, type=int)  # 현재 페이지
    per_page = 10  # 한 페이지당 글 수

    conn = get_db()
    board_dao = BoardDAO(conn)

    # 검색 결과 전체 수
    total_count = board_dao.get_search_count(keyword)
    total_pages = (total_count + per_page - 1) // per_page
    offset = (page - 1) * per_page

    # 실제 글 가져오기 (페이징 적용)
    search_result = board_dao.get_search_list(keyword, offset, per_page)
    
    return render_template(
        "board.html",
        board_main=search_result,
        keyword=keyword,
        page=page,
        total_pages=total_pages
    )

#게시글
@app.route('/detail/<int:bono>')
def detail(bono):
    US_name = session.get('US_name')
    conn = get_db()
    board_dao = BoardDAO(conn)

    # 게시글 가져오기
    post = board_dao.get_post_detail(bono)

    comments = board_dao.get_comments(bono)

    # 댓글을 계층 구조 순서대로 가져오기 (중요)
    
    if not post:
        return "<script>alert('존재하지 않는 게시글입니다.');history.back();</script>"

    return render_template(
        "detail.html",
        post=post,
        comments=comments,
        bono=bono,
        User_id=session.get('US_id'),
        US_name = US_name, 
    )

#댓글
@app.route('/comment/add', methods=['POST'])
def comment_add():
    comment = request.form.get("comment_detail")
    bono = request.form.get("bono")
    US_id = session.get("US_id")

    # parent_cno는 빈 값("") 또는 None이면 None 처리, 숫자면 int 변환
    parent_raw = request.form.get("parent_cno")
    parent_cno = int(parent_raw) if parent_raw and parent_raw.isdigit() else None

    conn = get_db()
    cursor = conn.cursor()

    board_dao = BoardDAO(conn)
    board_dao.in_comment(bono, US_id, comment, parent_cno)
    conn.commit()

    cursor.close()

    return redirect(f"/detail/{bono}")

#댓글 수정
@app.route('/comment/edit/<int:cno>', methods=['POST'])
def comment_edit(cno):
    new_comment = request.form.get("comment_detail")
    bono = request.form.get('bono')
    conn = get_db()
    board_dao = BoardDAO(conn)
    #권한 체크
    author_id = board_dao.update_power(cno)

    if not author_id:
        return "<script>alert('댓글이 존재하지 않습니다');history.back();</script>"

    #현재 로그인 유저와 비교
    if author_id != session.get("US_id"):
        return "<script>alert('권한이 없습니다 (작성자만 수정 가능)');history.back();</script>"

    #수정 실행
    
    success = board_dao.update_comment(new_comment, cno)
    if success:
        return redirect(f"/detail/{bono}")
    else:
        return "<script>alert('수정 중 오류가 발생했습니다');history.back();</script>"
    
#댓글 삭제
@app.route('/comment/delete/<int:cno>', methods=['POST'])
def comment_delete(cno):
    login_id = session.get("US_id")
    bono = request.form.get('bono')

    conn = get_db()
    board_dao = BoardDAO(conn)

    # 1. 정보 확인 및 존재 여부 체크
    row = board_dao.get_comment_info(cno)
    if not row:
        return "<script>alert('댓글이 존재하지 않습니다.');history.back();</script>"

    user_id, parent_cno = row

    # 2. 권한 확인
    if login_id != "admin" and user_id != login_id:
        return "<script>alert('권한이 없습니다.');history.back();</script>"

    # 3. 삭제 로직 수행
    if board_dao.get_child_count(cno) > 0:
        board_dao.mark_deleted_comment(cno) # 'NULL'로 변경
    else:
        board_dao.delete_comment(cno) # 진짜 삭제

    # 4. 연쇄 삭제 체크 (부모가 빈 껍데기인지 확인)
    if parent_cno is not None:
        board_dao.delete_empty_parent(parent_cno)

    conn.commit()
    return redirect(f"/detail/{bono}")

#게시글수정하기
@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
def edit(post_id):
    user_id = session.get('US_id')
    US_name = session.get('US_name')
    conn = get_db()
    board_dao = BoardDAO(conn)

    post = board_dao.power_board(post_id)

    if not post or (post[2] != user_id and user_id != 'admin'):
        return "<script>alert('수정 권한이 없습니다.'); history.back();</script>"

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        board_dao.update_board(title, content, post_id)
        return redirect(f"/detail/{post_id}")

    return render_template("edit.html", post=(post_id, post[0], post[1], post[2]), Login_id = user_id, US_name = US_name)

#게시글 삭제하기
@app.route('/delete/<int:post_id>', methods=['POST','GET'])
def delete(post_id):
    user_id = session.get('US_id')
    if not user_id:
        return "<script>alert('로그인이 필요합니다.'); location.href='/login';</script>"

    conn = get_db()
    board_dao = BoardDAO(conn)

    author_id = board_dao.select_board(post_id)

    # 3. 권한 체크
    if not author_id or (author_id != user_id and user_id != 'admin'):
        return "<script>alert('삭제 권한이 없습니다.'); history.back();</script>"
    
    try:
        # 4. 삭제 로직 (순서 중요: 자식 레코드인 댓글부터 삭제)
        board_dao.delete_board_comments(post_id)
        board_dao.delete_board(post_id)
        
        # 5. 모든 작업이 성공했을 때만 DB에 영구 반영
        conn.commit()
    except Exception as e:
        conn.rollback() # 하나라도 실패하면 원복
        print(f"Error: {e}")
        return "<script>alert('오류가 발생했습니다.'); history.back();</script>"
    finally:
        conn.close()

    return redirect('/board')

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

if __name__ == '__main__':
   # subprocess.Popen(["cloudflared", "tunnel", "--url", "http://localhost:2121"])
    app.config['JSON_AS_ASCII'] = False
    app.run(host='0.0.0.0', port=2121 , debug=True)