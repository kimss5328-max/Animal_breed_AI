from BoardDTO import BoardDTO
import logging

class BoardDAO:
    def __init__(self, connection):
        # 변수명을 connection으로 명확히 하고, app.py에서 넘겨준 연결 객체를 받습니다.
        self.conn = connection
        # 배포 시 에러 추적을 위한 로거 설정
        self.logger = logging.getLogger(__name__)

    # 공통: 쿼리 결과(튜플)를 딕셔너리로 변환하는 헬퍼 메서드
    def _to_dict(self, cursor):
        if cursor.description is None: return None
        columns = [col[0].lower() for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    # 게시글 전체 개수
    def get_total_count(self):
        with self.conn.cursor() as cursor:
            try:
                sql = "SELECT COUNT(*) FROM Board_Author_tbl"
                cursor.execute(sql)
                return cursor.fetchone()[0]
            except Exception as e:
                self.logger.error(f"Total count error: {e}")
                return 0

    # 게시글 리스트 조회 (페이징)
    def boardmain(self, offset=0, per_page=10):
        with self.conn.cursor() as cursor:
            sql =sql = """
            SELECT * FROM (
                SELECT a.*, ROWNUM AS rnum FROM (
                    SELECT 
                        b.bono, 
                        b.board_title, 
                        b.user_id,
                        u.name AS name,
                        TO_CHAR(b.board_time, 'YYYY/MM/DD') AS board_date
                    FROM Board_Author_tbl b
                    JOIN user_id_tbl u
                    ON b.user_id = u.user_id
                    ORDER BY b.bono DESC
                ) a
                WHERE ROWNUM <= :max_row
            )
            WHERE rnum > :offset
        """
            try:
                # max_row는 offset + per_page 입니다.
                max_row = offset + per_page
                cursor.execute(sql, {"max_row": max_row, "offset": offset})
                return self._to_dict(cursor)
            except Exception as e:
                self.logger.error(f"Board list error (ORA-00933): {e}")
                return []

    # 게시글 상세 정보
    def get_post_detail(self, bono):
        with self.conn.cursor() as cursor:
            sql = """
                SELECT 
                    b.bono, 
                    b.board_title, 
                    b.board_detail, 
                    b.user_id, 
                    u.name, -- user_id_tbl에서 이름을 가져옴
                    TO_CHAR(b.board_time, 'YYYY/MM/DD') as board_date
                FROM 
                    Board_Author_tbl b
                JOIN 
                    user_id_tbl u ON b.user_id = u.user_id -- 두 테이블을 아이디로 연결
                WHERE 
                    b.bono = :1
            """
            cursor.execute(sql, (bono,))
            # 상세 정보는 단일 행이므로 fetchone 후 딕셔너리 변환
            row = cursor.fetchone()
            if row:
                columns = [col[0].lower() for col in cursor.description]
                return dict(zip(columns, row))
            return None

    # 댓글 목록 가져오기 (계층형)
    def get_comments(self, bono):
        with self.conn.cursor() as cursor:
            sql = """
                SELECT * FROM (
                    SELECT 
                        LEVEL AS depth, 
                        c.cno, 
                        c.parent_cno, 
                        c.user_id, 
                        c.comment_detail, 
                        u.name, -- 조인된 유저 이름
                        TO_CHAR(c.comment_time, 'YYYY/MM/DD HH24:MI') as comment_time,
                        CONNECT_BY_ISLEAF AS is_leaf
                    FROM Comment_tbl c
                    JOIN user_id_tbl u ON c.user_id = u.user_id
                    WHERE c.bono = :bono
                    START WITH c.parent_cno IS NULL
                    CONNECT BY PRIOR c.cno = c.parent_cno
                    ORDER SIBLINGS BY c.comment_time ASC
                )
                WHERE NOT (comment_detail = 'NULL' AND is_leaf = 1)
            """
            cursor.execute(sql, {"bono": bono})
            return self._to_dict(cursor)

    # 게시글 작성 권한 체크
    def check_write_power(self, user_id):
        with self.conn.cursor() as cursor:
            sql = """
                SELECT Animal_breed, User_personality, User_MBTI
                FROM User_personality_tbl
                WHERE UPPER(TRIM(USER_ID)) = UPPER(TRIM(:1))
            """
            cursor.execute(sql, [user_id])
            return cursor.fetchone()

    # 게시글 작성
    def in_board(self, user_id, board_title, board_detail):
        with self.conn.cursor() as cursor:
            sql = """
            INSERT INTO Board_Author_tbl (bono, user_id, board_title, board_detail, board_time)
            VALUES(board_seq.nextval, :1, :2, :3, SYSDATE)
            """
            try:
                cursor.execute(sql, [user_id, board_title, board_detail])
                self.conn.commit()
                return True
            except Exception as e:
                self.conn.rollback()
                self.logger.error(f"Insert Board Error: {e}")
                return False

    # 댓글 작성
    def in_comment(self, bono, user_id, comment, parent_cno=None):
        with self.conn.cursor() as cursor:
            try:
                sql = """
                INSERT INTO Comment_tbl (cno, bono, user_id, comment_detail, parent_cno, comment_time)
                VALUES (comment_seq.nextval, :1, :2, :3, :4, SYSDATE)
                """
                cursor.execute(sql, [bono, user_id, comment, parent_cno])
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                self.logger.error(f"Insert Comment Error: {e}")

    # 게시글 수정 권한
    def power_board(self, post_id):
        with self.conn.cursor() as cursor:
            try:
                # bono를 숫자로 처리하기 위해 TRIM 제거 (성능 최적화)
                sql = "SELECT board_title, board_detail, user_id FROM Board_Author_tbl WHERE bono = :1"
                cursor.execute(sql, [post_id])
                row = cursor.fetchone()
                # app.py가 post[0], post[1], post[2]로 접근하므로 튜플 그대로 반환
                return row if row else None
            except Exception as e:
                self.logger.error(f"power_board error: {e}")
                return None

    # 게시글 수정
    def update_board(self, title, content, post_id):
        with self.conn.cursor() as cursor:
            try:
                sql = "UPDATE Board_Author_tbl SET board_title = :1, board_detail = :2 WHERE bono = :3"
                cursor.execute(sql, [title, content, post_id])
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                self.logger.error(f"Update Board Error: {e}")

    # 댓글 수정 권한
    def update_power(self, cno):
        with self.conn.cursor() as cursor:
            try:
                # 댓글 번호(cno)로 작성자 ID 조회
                sql = "SELECT user_id FROM Comment_tbl WHERE cno = :1"
                cursor.execute(sql, (cno,))
                row = cursor.fetchone()
                # 배포용 딕셔너리 구조가 아닌 튜플/단일값 반환 방식 유지
                return row[0] if row else None
            except Exception as e:
                self.logger.error(f"update_power error: {e}")
                return None
            
    # 댓글 수정
    def update_comment(self, new_comment, cno):
        with self.conn.cursor() as cursor:
            try:
                sql = "UPDATE Comment_tbl SET comment_detail = :1 WHERE cno = :2"
                cursor.execute(sql, (new_comment, cno))
                self.conn.commit()
                return True
            except Exception as e:
                self.conn.rollback()
                self.logger.error(f"update_comment error: {e}")
                return False
    
    # 게시글 삭제
    def delete_board(self, post_id):
        with self.conn.cursor() as cursor:
            try:
                # 관련 댓글 먼저 삭제 (참조 무결성)
                cursor.execute("DELETE FROM Comment_tbl WHERE bono = :1", [post_id])
                # 게시글 삭제
                cursor.execute("DELETE FROM Board_Author_tbl WHERE bono = :1", [post_id])
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                self.logger.error(f"Delete Board Error: {e}")

    # 1. 댓글 작성자 정보 조회 
    def get_comment_info(self, cno):
        with self.conn.cursor() as cursor:
            sql = "SELECT user_id, parent_cno FROM Comment_tbl WHERE cno = :1"
            cursor.execute(sql, (cno,))
            return cursor.fetchone()

    # 2. 자식(대댓글) 개수 확인
    def get_child_count(self, cno):
        with self.conn.cursor() as cursor:
            sql = "SELECT COUNT(*) FROM Comment_tbl WHERE parent_cno = :1"
            cursor.execute(sql, (cno,))
            return cursor.fetchone()[0]

    # 3. 부모 댓글 연쇄 삭제 로직
    def delete_empty_parent(self, parent_cno):
        with self.conn.cursor() as cursor:
            try:
                # 부모에게 남은 자식이 있는지 확인
                cursor.execute("SELECT COUNT(*) FROM Comment_tbl WHERE parent_cno = :1", (parent_cno,))
                remain_children = cursor.fetchone()[0]

                if remain_children == 0:
                    # 자식이 없다면 부모의 내용이 'NULL'인지 확인
                    cursor.execute("SELECT comment_detail FROM Comment_tbl WHERE cno = :1", (parent_cno,))
                    p_row = cursor.fetchone()
                    
                    if p_row and p_row[0] == 'NULL':
                        # 내용도 'NULL'(삭제됨)이고 자식도 없으므로 실제 삭제
                        cursor.execute("DELETE FROM Comment_tbl WHERE cno = :1", (parent_cno,))
                        self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                self.logger.error(f"delete_empty_parent error: {e}")

    # 2. 댓글 삭제 (내용만 NULL 처리)
    def mark_deleted_comment(self, cno):
        with self.conn.cursor() as cursor:
            try:
                sql = "UPDATE Comment_tbl SET comment_detail = 'NULL' WHERE cno = :1"
                cursor.execute(sql, [cno])
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()

    # 3. 실제 삭제 로직 (자식이 없을 때)
    def delete_comment(self, cno):
        with self.conn.cursor() as cursor:
            try:
                cursor.execute("DELETE FROM Comment_tbl WHERE cno = :1", [cno])
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()

    # 1. 게시글 작성자 조회 (권한 체크용)
    def select_board(self, post_id):
        with self.conn.cursor() as cursor:
            # app.py에서 author_id를 바로 비교하므로 단일 값 반환
            sql = "SELECT user_id FROM Board_Author_tbl WHERE bono = :1"
            cursor.execute(sql, [post_id])
            row = cursor.fetchone()
            return row[0] if row else None

    # 2. 게시글에 달린 모든 댓글 삭제
    def delete_board_comments(self, post_id):
        with self.conn.cursor() as cursor:
            sql = "DELETE FROM Comment_tbl WHERE bono = :1"
            cursor.execute(sql, [post_id])
            # app.py에서 직접 commit하므로 여기선 제외 (혹은 중복해도 무방)



    # 1. 검색 결과의 총 개수 (페이징 계산용)
    def get_search_count(self, keyword):
        with self.conn.cursor() as cursor:
            sql = """
                SELECT COUNT(*)
                FROM Board_Author_tbl b
                JOIN user_id_tbl u
                ON b.user_id = u.user_id
                WHERE UPPER(TRIM(b.board_title)) LIKE UPPER(:1)
            """
            try:
                cursor.execute(sql, [f"%{keyword}%"])
                return cursor.fetchone()[0]
            except Exception as e:
                self.logger.error(f"Search count error: {e}")
                return 0

    # 2. 검색 결과 리스트 조회 (페이징 적용)
    def get_search_list(self, keyword, offset, per_page):
        with self.conn.cursor() as cursor:
            sql = """
                SELECT * FROM (
                    SELECT a.*, ROWNUM AS rnum FROM (
                        SELECT 
                            b.bono,
                            b.board_title,
                            b.user_id,
                            u.name AS name,  -- 🔥 핵심
                            TO_CHAR(b.board_time, 'YYYY/MM/DD') AS board_date
                        FROM Board_Author_tbl b
                        JOIN user_id_tbl u
                        ON b.user_id = u.user_id
                        WHERE UPPER(TRIM(b.board_title)) LIKE UPPER(:keyword)
                        ORDER BY b.bono DESC
                    ) a
                    WHERE ROWNUM <= :max_row
                )
                WHERE rnum > :offset
            """
            try:
                max_row = offset + per_page

                cursor.execute(sql, {
                    "keyword": f"%{keyword}%",
                    "max_row": max_row,
                    "offset": offset
                })

                return self._to_dict(cursor)

            except Exception as e:
                self.logger.error(f"Search list error: {e}")
                return []