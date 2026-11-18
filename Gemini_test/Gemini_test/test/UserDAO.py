from UserDTO import UserDTO
import logging

class UserDAO:
    def __init__(self, connection):
        # cursor 대신 connection만 저장합니다.
        self.conn = connection
        self.logger = logging.getLogger(__name__)
    
    # 1. 중복 확인 및 존재 여부 체크
    def duplicate(self, user_id):
        with self.conn.cursor() as cursor:
            sql = "SELECT user_id FROM User_ID_tbl WHERE user_id = :1"
            cursor.execute(sql, [user_id])
            return cursor.fetchone() is not None

    # 2. 로그인용 비밀번호 해시 가져오기
    def get_password_hash(self, user_id):
        with self.conn.cursor() as cursor:
            try:
                sql = "SELECT user_pw FROM User_ID_tbl WHERE user_id = :1"
                cursor.execute(sql, [user_id])
                row = cursor.fetchone()
                return row[0].strip() if row else None
            except Exception as e:
                self.logger.error(f"[UserDAO get_password_hash Error]: {e}")
                return None

    # 3. 회원가입
    def insert_user(self, user_dto):
        with self.conn.cursor() as cursor:
            try:
                sql = "INSERT INTO User_ID_tbl (user_id, user_pw, email, name) VALUES (:1, :2, :3, :4)" #user_email, :3 추가
                cursor.execute(sql, [user_dto.user_id, user_dto.user_pw, user_dto.user_email, user_dto.user_name])   #user_dto.user_email 추가
                self.conn.commit()
                return True
            except Exception as e:
                self.logger.error(f"회원가입 오류: {e}")
                self.conn.rollback()
                return False

    # 4. 비밀번호 보안 업데이트 (재해싱용)
    def update_password_hash(self, user_id, new_hash):
        with self.conn.cursor() as cursor:
            try:
                sql = "UPDATE User_ID_tbl SET user_pw = :1 WHERE user_id = :2"
                cursor.execute(sql, [new_hash, user_id])
                self.conn.commit()
                return True
            except Exception as e:
                self.logger.error(f"해시 업데이트 오류: {e}")
                self.conn.rollback()
                return False
    
    def check_user_for_pw(self, user_id, user_email):
        self.cursor.execute("SELECT * FROM User_ID_tbl WHERE USER_ID = :1 AND USER_EMAIL = :2", [user_id, user_email])
        return self.cursor.fetchone() is not None
    
    # 5. 회원탈퇴
    def secession(self, user_id):
        with self.conn.cursor() as cursor:
            try:
                sql = "DELETE FROM User_ID_tbl WHERE user_id = :1"
                cursor.execute(sql, [user_id])

                if cursor.rowcount == 0:
                    return False

                self.conn.commit()
                return True

            except Exception as e:
                self.logger.error(f"회원탈퇴 오류 : {e}")
                self.conn.rollback()
                return False
            
    #6. 유저 닉네임
    def username(self,user_id):
        with self.conn.cursor() as cursor:
            try:
                sql = "select name from user_id_tbl where user_id = :1"
                cursor.execute(sql, [user_id])
                return cursor.fetchone()[0]
            except Exception as e:
                self.logger.error(f"로그인 중 오류 : {e}")
                return False
            

    #7. 정보 수정
    def Update_user(self, dto):
        with self.conn.cursor() as cursor:
            try:
                if dto.user_pw and dto.name:
                    sql = "update user_id_tbl set user_pw = :1, name = :2 where user_id = :3"
                    cursor.execute(sql, [dto.user_pw, dto.name, dto.user_id])

                elif dto.user_pw:
                    sql = "update user_id_tbl set user_pw = :1 where user_id = :2"
                    cursor.execute(sql, [dto.user_pw, dto.user_id])

                elif dto.name:
                    sql = "update user_id_tbl set name = :1 where user_id = :2"
                    cursor.execute(sql, [dto.name, dto.user_id])

                else:
                    return False

                self.conn.commit()
                return True

            except Exception as e:
                self.logger.error(f"회원정보 수정 오류 : {e}")
                self.conn.rollback()
                return False
            
    #8. 이메일로 아이디 조회
    def find_id_by_email(self, user_email):
        # self.conn.cursor()를 사용하여 DB와 연결합니다.
        with self.conn.cursor() as cursor:
            try:
                # 입력받은 이메일과 일치하는 유저 아이디를 검색합니다.
                sql = "SELECT user_id FROM User_ID_tbl WHERE EMAIL = :1"
                cursor.execute(sql, [user_email])
                row = cursor.fetchone()
                
                # 결과가 있으면 아이디를 반환하고, 없으면 None을 반환합니다.
                if row:
                    return row[0].strip() # 공백 제거 후 반환
                return None
            except Exception as e:
                self.logger.error(f"아이디 찾기 DB 조회 오류: {e}")
                return None
            
    # 1. 중복 확인 및 존재 여부 체크
    def uni_name(self, user_name):
        with self.conn.cursor() as cursor:
            sql = "SELECT user_id FROM User_ID_tbl WHERE name = :1"
            cursor.execute(sql, [user_name])
            return cursor.fetchone() is not None
        
    def uni_email(self, user_email):
        with self.conn.cursor() as cursor:
            sql = "SELECT user_id FROM User_ID_tbl WHERE email = :1"
            cursor.execute(sql, [user_email])
            return cursor.fetchone() is not None
        