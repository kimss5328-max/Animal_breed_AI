/*  ALTER SESSION set "_ORALCE_SCRIPT"=TRUE;
    create user Gemini_DB identified by Gemini;
    
*/
CREATE table User_ID_tbl(                                       /* 유저 아이디 및 패스워드를 저장하는 테이블*/ 
User_ID VARCHAR(12) PRIMARY KEY,                                /* 유저 아이디*/
User_PW VARCHAR(20) not null                                  /* 유저 패스워드*/
)
    
CREATE table User_personality_tbl(                              /* 유저의 성격을 저장하는 테이블*/
User_ID VARCHAR(12) not null,                                /* User_ID_tbl에서 User_ID를 Foreing key 해서 가져옴*/
User_personality VARCHAR(50) NOT NULL,                                   /* 유저의 성격을 저장*/
User_MBTI VARCHAR(4) NOT NULL,                                           /* 유저의 MBTI 저장*/
Animal VARCHAR(20) not null,                                             /* Gemini 동물 추천 저장*/
Animal_breed VARCHAR(30) not null,                                       /* Gemini 동물 품종 추천 저장*/
FOREIGN KEY(User_ID) REFERENCES User_ID_tbl(User_ID)            
)

CREATE SEQUENCE board_seq
    INCREMENT BY 1
    START WITH 1
    MINVALUE 1
    MAXVALUE 99999
    NOCYCLE
    NOCACHE
    NOORDER;

SELECT b.bono, b.user_id, b.board_title, b.board_detail, b.board_time
FROM Board_Author_tbl b
JOIN User_personality_tbl u
    ON b.user_id = u.user_id;

CREATE table Board_Author_tbl(
    bono number not null PRIMARY KEY,
    USER_ID VARCHAR2(12) NOT NULL,
    board_title VARCHAR2(100) NOT NULL,
    bOard_detail VARCHAR2(3000) NOT NULL,
    board_time DATE,
    FOREIGN KEY(USER_ID) REFERENCES User_ID_tbl(USER_ID)
);

insert into Board_Author_tbl VALUES(board_seq.nextval, 'test','title_test', 'detailtest',SYSDATE);


/* 아직 안됨*/
CREATE table Board_comment_tbl(
    USER_ID VARCHAR2(12) NOT NULL,
    US_comment VALUE(300) NOT NULL,
    comment_time DATE,
    FOREIGN KEY(USER_ID) REFERENCES User_ID_tbl(USER_ID)
)

select NB
from Gemini_tbl
WHERE User_ID = "입력 값"


/* 추천 받은 동물 보기   최근 5개 보는 방법으로 DATE 최근 순서대로 5개가 넘으면 한 뒤 가장 오래된 데이터는 삭제 */
CREATE table received_animal(
    User_ID VARCHAR2(12) NOT NULL,
    Animal VARCHAR2(20) NOT NULL,
    Animal_breed VARCHAR2(30) NOT NULL,
    Create_DATE DATE,
    FOREIGN KEY(USER_ID) REFERENCES USER_ID_tbl(USER_ID)
)

delete from animal_in_de
where (Create_DATE, USER_ID) in count() = 1  (
    select Create_DATE, USER_ID from( 
        select Create_DATE, USER_ID
        from received_animal
        ORDER BY Create_DATE asc
        FETCH FIRST 1 rows ONLY
    )
);
DECLARE
    u_count number;
BEGIN
/* 사용자별 데이터 개수 확인 */
select count(*) into u_count from received_animal where USER_ID = :1;
IF u_count >= 5 THEN
    delete from received_animal
    where (Create_DATE, USER_ID) in(
        select Create_DATE, USER_ID
        from(
            select Create_DATE, USER_ID
            from received_animal
            where USER_ID = :1
            ORDER BY Create_DATE ASC
            FETCH FIRST 1 row ONLY
        )
    );
    END IF;

insert into received_animal(USER_ID, animal, Animal_breed, Create_DATE) VALUES(:1, :2, :3, SYSDATE)

    with animal_in_de as (
        select Create_DATE, USER_ID
        from received_animal
        where USER_ID = :1
        ORDER BY Create_DATE ASC
        FETCH FIRST 1 ROWS ONLY
    )
    END;

    insert into received_animal(User_ID, Animal, Animal_breed, Create_DATE)
    select *
    from animal_in_de;

    delete from animal_in_de
    where (Create_DATE, USER_ID) in (
        select Create_DATE, USER_ID from received_animal
    );
    END IF;
    COMMIT;
END;

CREATE TABLE Comment_tbl (
    cno NUMBER NOT NULL PRIMARY KEY,
    bono NUMBER NOT NULL,
    user_id VARCHAR2(12) NOT NULL,
    comment_detail VARCHAR2(1000) NOT NULL,
    parent_cno NUMBER NULL,
    comment_time DATE DEFAULT SYSDATE,
    FOREIGN KEY(bono) REFERENCES Board_Author_tbl(bono),
    FOREIGN KEY(user_id) REFERENCES User_ID_tbl(user_id),
    FOREIGN KEY(parent_cno) REFERENCES Comment_tbl(cno)
);

CREATE SEQUENCE COMMENT_SEQ
START WITH 1
INCREMENT BY 1
NOCACHE;

INSERT INTO Comment_tbl (
    cno, 
    bono, 
    user_id, 
    comment_detail, 
    parent_cno, 
    comment_time
) VALUES (
    COMMENT_SEQ.NEXTVAL,
    1,
    'commenter01',
    '첫 번째 댓글입니다.',
    NULL,
    SYSDATE
);

INSERT INTO Comment_tbl (
    cno, 
    bono, 
    user_id, 
    comment_detail, 
    parent_cno, 
    comment_time
) VALUES (
    COMMENT_SEQ.NEXTVAL,
    1,
    'replyuser02',
    '이것은 첫 번째 댓글에 대한 대댓글입니다.',
    1, -- 부모 댓글의 cno
    SYSDATE
);

SELECT
    cno,
    bono,
    user_id,
    comment_detail,
    parent_cno,
    comment_time,
    -- LEVEL: 계층의 깊이 (1: 원댓글, 2: 1차 대댓글 등)
    LEVEL AS depth
FROM
    Comment_tbl
WHERE
    bono = 1
START WITH
    parent_cno IS NULL -- 원댓글(부모가 없는 댓글)부터 시작
CONNECT BY
    PRIOR cno = parent_cno -- 부모의 cno와 현재 댓글의 parent_cno를 연결
ORDER SIBLINGS BY
    comment_time ASC; -- 같은 레벨(형제)끼리는 작성 시간 순으로 정렬

COMMENT ON TABLE Comment_tbl IS '댓글 및 대댓글 테이블';
COMMENT ON COLUMN Comment_tbl.cno IS '댓글 번호 (PK)';
COMMENT ON COLUMN Comment_tbl.bono IS '원 게시글 번호 (FK)';
COMMENT ON COLUMN Comment_tbl.parent_cno IS '부모 댓글 번호 (대댓글인 경우)';

/* 날짜 비교 최근 받은 순서대로 하고 가장 오래된거 삭제 = acs로 정렬하고 마지막 삭제 */
/*Animal_stcs 
P.Animal VARCHAR(20),                                             /* User_personality_tbl에서 가져오는 동물 데이터*/
P.Animal_breed VARCHAR(30),                                       /* User_personality_tbl에서 가져오는 동물 품종 데이터*/
P.User_personality VARCHAR(20),                                   /* User_personality_tbl에서 가져오는 유저의 성격을 저장*/
P.User_MBTI VARCHAR(4),                                           /* User_personaliy_tbl에서 가져오는 유저의 MBTI*/


*/
SELECT  User_personality_tbl                                       /* 유저들의 품종 및 동물 통계를 위한 테이블*/
FROM Animal,
Animal_breed,
User_personality,
User_MBTI;

TRUNCATE _table


select Animal_breed, User_personality, User_MBTI from User_personality_tbl where animal = '강아지';

/*
User_ID_tbl             유저 아이디,패스워드 테이블
사용자 아이디 PK
사용자 패스워드
---------------------------------------------
Gemini_beer_tbl              Gemini 질문 횟수 카운팅 테이블
사용자가 추천받은 최근 5개 종류 품종
사용자 아이디 PK, FK
Gemini추천하는 반려동물
Gemini추천하는 품종
----------------------------------------------
G
----------------------------------------------
User_personality_tbl    사용자 성격 및 추천 반려동물, 품종 테이블
사용자 아이디 PK, FK
사용자 성격 
사용자 MBTI 
Gemini추천하는 반려동물
Gemini추천하는 품종
---------------------------------------------
Gemini_tbl              
사용자의 질문 및 Gemini 답변 내용 저장 테이블 이것도 고민 할지 말지
숫자 카운팅 fk
사용자 아이디 fk
----------------------------------------------
board_tbl
사용자 아이디 PK,FK
게시판 내용 NL
현재 시간 NL
----------------------------------------------
comment_tbl
사용자 아이디 PK, FK
게시판 댓글 NL
현재 시간 NL
----------------------------------------------
Animal_stcs 통계를 위한 테이블
Gemini추천하는 반려동물 fk
Gemini추천하는 품종 fk
사용자 성격 fk
사용자 MBTI fk

새로운 동물이 나올때마다 추가?? 이건 나중에 한번 찾아보기