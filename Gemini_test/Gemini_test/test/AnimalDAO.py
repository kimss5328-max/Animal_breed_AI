from AnimalDTO import AnimalDTO
import logging

class AnimalDAO:
    def __init__(self, connection):
        self.conn = connection
        self.logger = logging.getLogger(__name__)

    def get_Animal(self, User_id):
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM User_personality_tbl WHERE User_ID = :1", [User_id])
            row = cursor.fetchone()
            return AnimalDTO(*row) if row else None

    def get_beerd(self, US_id):
        with self.conn.cursor() as cursor:
            sql = """
                SELECT Animal_breed
                FROM User_personality_tbl
                WHERE User_ID = :1 
            """
            cursor.execute(sql, [US_id])
            rows = cursor.fetchall()
            return [row[0] for row in rows] if rows else []

    def InAnimal(self, AN_DAO):
        with self.conn.cursor() as cursor:
            try:
                sql = """
                    INSERT INTO User_personality_tbl 
                    (User_ID, User_personality, User_MBTI, Animal, Animal_breed)
                    VALUES (:1, :2, :3, :4, :5)
                """
                cursor.execute(sql, [
                    AN_DAO.user_id,
                    AN_DAO.personality,
                    AN_DAO.mbti,
                    AN_DAO.animal,
                    AN_DAO.breed
                ])
            except Exception as e:
                self.logger.error(f"InAnimal Error: {e}")
                raise

    def re_animal(self, UAN_DAO):
        with self.conn.cursor() as cursor:
            sql = """
                DECLARE
                    u_count number;
                BEGIN
                    SELECT count(*) INTO u_count 
                    FROM RECEIVED_ANIMAL
                    WHERE USER_ID = :uid AND TYPE = :type;

                    IF u_count >= 5 THEN
                        DELETE FROM RECEIVED_ANIMAL
                        WHERE (Create_DATE, USER_ID, TYPE) IN (
                            SELECT Create_DATE, USER_ID, TYPE FROM (
                                SELECT Create_DATE, USER_ID, TYPE
                                FROM RECEIVED_ANIMAL
                                WHERE USER_ID = :uid AND TYPE = :type
                                ORDER BY Create_DATE ASC
                            ) WHERE ROWNUM = 1
                        );
                    END IF;

                    INSERT INTO RECEIVED_ANIMAL
                    (USER_ID, animal, Animal_breed, Create_DATE, TYPE) 
                    VALUES(:uid, :ani, :brd, SYSDATE, :type);
                END;
            """

            try:
                cursor.execute(sql, {
                    'uid': UAN_DAO.user_id,
                    'ani': UAN_DAO.animal,
                    'brd': UAN_DAO.breed,
                    'type': UAN_DAO.type
                })
                # ❌ commit 삭제
            except Exception as e:
                self.logger.error(f"re_animal Error: {e}")
                raise

    def delet(self, User_id):
        with self.conn.cursor() as cursor:
            try:
                cursor.execute(
                    "DELETE FROM User_personality_tbl WHERE User_ID = :1",
                    [User_id]
                )
            except Exception as e:
                self.logger.error(f"delet Error: {e}")
                raise

    def Group_tbl(self):
        with self.conn.cursor() as cursor:
            # self.cursor를 cursor로 수정했습니다.
            cursor.execute("SELECT Animal, count(*) FROM User_personality_tbl GROUP BY Animal")
            return cursor.fetchall() 
    
    def wher(self, GR_DTO):
        with self.conn.cursor() as cursor:
            sql = "SELECT Animal_breed, User_personality, User_MBTI FROM User_personality_tbl WHERE animal = :1"
            cursor.execute(sql, [GR_DTO.animal])
            return cursor.fetchall()

    def get_user_animals(self, US_id):
        with self.conn.cursor() as cursor:
            delete_sql = """
            DELETE FROM received_animal
            WHERE ROWID IN (
                SELECT rid FROM (
                    SELECT ROWID AS rid,
                        ROW_NUMBER() OVER (
                            PARTITION BY User_ID
                            ORDER BY Create_date DESC
                        ) AS rn
                    FROM received_animal
                    WHERE User_ID = :1
                )
                WHERE rn > 5
            )
            """
            cursor.execute(delete_sql, [US_id])
            self.conn.commit()
            select_sql = """
            SELECT animal, Animal_breed, TO_CHAR(Create_date, 'YYYY/MM/DD')
            FROM received_animal
            WHERE User_ID = :1
            ORDER BY Create_date DESC
            """
            cursor.execute(select_sql, [US_id])
            return cursor.fetchall()

    def filtered(self, MBTI):
        with self.conn.cursor() as cursor:
            sql = """
            SELECT User_MBTI, animal, COUNT(User_MBTI)
            FROM User_personality_tbl
            WHERE User_MBTI = :1
            GROUP BY User_MBTI, animal
            """
            cursor.execute(sql, [MBTI])
            return cursor.fetchall()
    
    def animal_drop(self):
        with self.conn.cursor() as cursor:
            sql = "SELECT DISTINCT User_MBTI FROM User_personality_tbl"
            cursor.execute(sql)
            return cursor.fetchall()
    
    def breed_animal(self, MBTI, animal):
        with self.conn.cursor() as cursor:
            sql = """
            SELECT ANIMAL_BREED, COUNT(ANIMAL_BREED)
            FROM User_personality_tbl
            WHERE UPPER(TRIM(USER_MBTI)) = :1
            AND UPPER(TRIM(ANIMAL)) = :2
            GROUP BY ANIMAL_BREED
            """
            cursor.execute(sql, [MBTI, animal])
            return cursor.fetchall()
    
    def group_total(self):
        with self.conn.cursor() as cursor:
            sql = "SELECT animal, COUNT(User_MBTI) FROM User_personality_tbl GROUP BY animal"
            cursor.execute(sql)
            return cursor.fetchall()
    
    def group_all(self):
        with self.conn.cursor() as cursor:
            sql = "SELECT User_MBTI, animal, COUNT(User_MBTI) FROM User_personality_tbl GROUP BY User_MBTI, animal"
            cursor.execute(sql)
            return cursor.fetchall()