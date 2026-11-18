# 98. 보안 점검 🔴

> 이 문서에는 위치만 적고 **값은 쓰지 않는다**. 실제 값은 원본 파일에만 있다.
>
> **졸업작품 기준 우선순위**: 런칭하지 않으므로, 이 문서에서 실제로 필요한 것은 §1(코드를 공개할 때)과 §3의 Gemini 공유 문제 정도다. 나머지는 "운영 시 고려사항"이다 → [99](99_known_issues.md)의 C·D·E 등급

## 1. 하드코딩된 비밀 정보

> ✅ **2026-11-17 조치**: `app.py`와 `db_config.py`의 값은 모두 `test/.env`로 옮기고, 코드는 `os.environ`으로 읽도록 바꿨다. `.env`, 원본 백업(`*.bak_before_env`), `test.py`, `__pycache__`는 `.gitignore`로 제외했다. 아래 표의 줄 번호는 **수정 전** 기준이다.
| 위치 | 항목 | 조치 |
|---|---|---|
| `test/app.py` L64, L107 | Flask `SECRET_KEY`(두 번 설정해서 뒤의 값이 덮어씀) | 무작위 32바이트 이상 값을 `.env`로 |
| `test/app.py` L75–77 | Gmail 계정 + **앱 비밀번호** | 🔴 재발급 |
| `test/app.py` L85–86 | Google OAuth `client_id` / **`client_secret`** | 🔴 재발급 |
| `test/app.py` L96, L510, L529 | Kakao REST API 키 (3곳에 중복) | 재발급 권장, 한 곳으로 모으기 |
| `test/app.py` L109 | **Gemini API 키** | 🔴 재발급 |
| `test/db_config.py` | Oracle 계정·비밀번호, 내부 IP | `.env`로, 비밀번호 변경 |
| `Gemini_test/test.py` (아카이브 대상 파일) | 또 다른 **Gemini API 키**, DB 계정·비밀번호 | 🔴 재발급. 쓰지 않는 파일이라도 키가 살아 있을 수 있음 |
| `__pycache__/*.pyc` | db_config·test의 비밀번호가 바이트코드 안에 평문으로 남아 있음 | 공유 전 반드시 삭제 |

**권장 구조**
```python
# .env (git에 올리지 않음)
FLASK_SECRET_KEY=...
GEMINI_API_KEY=...
# app.py
from dotenv import load_dotenv; load_dotenv()
app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]
```
코드가 GitHub, 공유 드라이브, 메신저 등으로 한 번이라도 나간 적이 있다면 **문서 정리보다 키 재발급을 먼저** 해야 한다.

## 2. 실행 설정
| 항목 | 위험 | 조치 |
|---|---|---|
| `app.run(debug=True, host='0.0.0.0')` | Cloudflare나 ngrok으로 공개하면 Werkzeug 디버거를 통해 **원격 코드 실행** 가능 | 배포 시 `debug=False` + gunicorn |
| SSL 검증 전역 해제 (`ssl._create_unverified_context`, `requests` verify=False 패치) | OAuth·카카오·Gemini 통신을 중간자 공격으로 가로챌 수 있음 | 제거. 사내 프록시 때문이라면 CA 번들을 지정 |

## 3. 인증·권한
| 항목 | 위험 | 조치 |
|---|---|---|
| 관리자 판정이 `user_id == 'admin'` | 소셜 가입 시 ID = 이메일 앞부분 → `admin@...` 이메일로 가입하면 **관리자 권한 획득**(DB에 admin 계정이 아직 없는 경우) | `IS_ADMIN` 컬럼이나 역할 테이블로 분리 |
| 소셜 가입자 `USER_PW='SOCIAL_GOOGLE_LOGIN'` (카카오도 같음) | 일반 로그인을 시도하면 argon2 `InvalidHash` 예외 → "오류 발생" 메시지 | `LOGIN_TYPE` 컬럼 추가 |
| 인증번호(탈퇴·ID·PW 찾기) | 만료 시간·시도 횟수 제한이 없음 → 6자리를 무차별 대입 가능 | 발급 시각 저장 후 5분 만료, 5회 실패 시 폐기 |
| `/Withdraw` 인증번호 | 입력한 아무 이메일로나 발송 가능 (계정 이메일과 대조하지 않음) | 세션 사용자의 DB 이메일로만 발송 |
| CSRF 방어 없음, `/delete/<id>`가 GET 허용 | 외부 링크 클릭만으로 글 삭제·수정 | Flask-WTF CSRF, 삭제는 POST만 |
| `/comment/add`, `/Ani_in`, `/Group` | 로그인 체크 없음 → `user_id=None`으로 INSERT 시도 | 데코레이터로 로그인 강제 |
| Gemini `chat` 객체를 전역에서 공유 | **모든 사용자의 질문이 한 대화 기록에 섞임** (다른 사람의 질문이 맥락에 들어가고 토큰도 계속 늘어남) | 요청마다 `generate_content` 호출, 또는 사용자별 세션 |

## 4. 정보 노출
| 항목 | 내용 |
|---|---|
| 예외 메시지를 그대로 응답 | `/Animalbeer/bigfive`, `/info` 등이 `str(e)`를 클라이언트에 반환 |
| 로그에 개인정보 출력 | `print(request.form)`, 세션 전체 출력 |
| 경로 노출 | `.pyc`에 `C:\Users\kimss\...`, 코드에 `/home/soulpow_2121/...` |
