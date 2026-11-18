import os
import oracledb
# ===== 환경변수 로드 (db_config 단독 실행 대비) (.env) — 비밀키는 코드가 아니라 .env 파일에 둔다 =====
def _load_env(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
_load_env()


# 🔥 반드시 추가 (thick mode)
oracledb.init_oracle_client(
    lib_dir=os.environ.get("ORACLE_CLIENT_DIR", "/home/soulpow_2121/oracle/instantclient_23_26")
)

def db():
    db_server_ip = os.environ["DB_HOST"]
    print(f"DB 연결 시도 IP: {db_server_ip}")

    try:
        dsn = oracledb.makedsn(db_server_ip, int(os.environ.get("DB_PORT", 1521)), service_name=os.environ.get("DB_SERVICE", "xe"))

        conn = oracledb.connect(
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            dsn=dsn
        )

        print("DB 연결 성공!")
        return conn

    except oracledb.DatabaseError as e:
        error, = e.args
        print(f"DB 연결 실패: {error.code}. 메시지: {error.message}")
        raise

# 테스트 실행
if __name__ == "__main__":
    try:
        connection = db()
        connection.close()
    except Exception as e:
        print(e)