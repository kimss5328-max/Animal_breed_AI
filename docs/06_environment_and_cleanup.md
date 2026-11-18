# 06. 실행 환경 · 폴더 정리

## 실행 환경 (현재 운영)
| 항목 | 내용 |
|---|---|
| GPU | NVIDIA RTX 4070 12GB |
| 서버 OS | Linux (`/home/soulpow_2121/`) |
| Python | 3.12 (venv 기준) |
| 웹 | Flask 3.1, oracledb (thick), argon2-cffi, flask-mail, authlib, google-generativeai |
| AI 서버 | FastAPI, uvicorn, unsloth, peft, transformers 4.44, torch, bitsandbytes, pandas, numpy |
| DB 클라이언트 | Oracle Instant Client (코드 경로: `instantclient_23_26`) |
| 외부 공개 | cloudflared 터널 (app.py에 주석으로 남아 있음) 또는 ngrok |

> ⚠️ 폴더 안의 `venv/` 2개에는 `oracledb`·`argon2`·`flask_mail`·`authlib`가 없다. 실제 실행 환경과 다르므로, 서버에서 `pip freeze > requirements.txt`로 패키지 목록을 뽑아 두는 것을 권장한다 (**확인이 필요함**).

## 실행 순서
1. Oracle XE (`192.168.210.167:1521/xe`)
2. `python ai_server.py` → :8000
3. `python bigfive_ai_server.py` → :8001
4. `python app.py` → :2121
5. (외부 공개 시) 터널

## 폴더 정리 권장
| 분류 | 대상 | 조치 |
|---|---|---|
| 자동 생성 | `venv/`, `__pycache__/`, `unsloth_compiled_cache/` | 삭제 가능. 특히 `__pycache__`에는 **DB 비밀번호가 평문으로** 들어 있음 |
| 바이너리 | `instantclient_23_8/` + zip 2개(470MB), `ngrok-*.tgz`, `libaio.so.1.0.1`(0바이트), `META-INF/` | 저장소에서 빼고 설치 방법만 문서로 |
| 쓰레기 | `*_Zone.Identifier` 15개, `.app.py.swp`, `=0.8.6` | 삭제 |
| 구버전 | [99a_archive.md](99a_archive.md)의 목록 | `archive/`로 이동 |

## 환경변수 (`.env`)
비밀키는 코드에 넣지 않고 `Gemini_test/Gemini_test/test/.env`에서 읽는다. `app.py`와 `db_config.py`가 시작할 때 이 파일을 자동으로 불러온다 (추가 패키지 필요 없음).

| 키 | 용도 |
|---|---|
| `FLASK_SECRET_KEY` | 세션 서명 (무작위 64자로 새로 생성 → 기존 로그인 세션은 한 번 끊김) |
| `GEMINI_API_KEY` | `/info` Q&A |
| `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER` | 인증번호 메일 |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | 구글 로그인 |
| `KAKAO_CLIENT_ID` | 카카오 로그인 |
| `DB_HOST`, `DB_PORT`, `DB_SERVICE`, `DB_USER`, `DB_PASSWORD` | Oracle |
| `ORACLE_CLIENT_DIR` | Instant Client 경로 (기본값: 서버 경로) |

새 환경에서 설치할 때:
```bash
cd Gemini_test/Gemini_test/test
cp .env.example .env    # 값 채우기
python app.py
```
> ⚠️ 리눅스 서버에서 실행하려면 **수정한 `app.py`·`db_config.py`와 `.env`를 함께 서버로 복사**해야 한다. `.env` 없이 실행하면 `KeyError: 'FLASK_SECRET_KEY'`가 난다.
> 수정 전 원본: `app.py.bak_before_env`, `db_config.py.bak_before_env` (깃 제외 대상)

## 깃 저장소
- 루트: `Soulpow_AI/` (`git init` 완료, 커밋은 아직 하지 않음)
- 제외 규칙: `Soulpow_AI/.gitignore` — 비밀 정보, 모델 가중치, 자동 생성 파일, 바이너리, 쓰레기 파일, 구버전 파일
- 업로드 대상: 102개 파일, 약 1.9MB (코드, 템플릿, CSS, 이미지, 문서)
- 저장소에 없는 것: `llama3_model/`(5.7GB), LoRA 어댑터 v3 2개 → 별도 보관 (외장 드라이브, Google Drive, Hugging Face 비공개 저장소 등)
- 학습 폴더 `데이터셋_AI학습/더블체크_품종/`은 이 저장소에 포함되지 않는다. 함께 올리려면 필요한 스크립트(`MBTI_AI.py`, `mbti_tain.py`, `train_unsloth.py`)와 데이터만 `training/` 폴더로 복사하는 것을 권장
