# 08. 데이터셋 (현재 운영 버전)

운영 중인 서버와 v3 어댑터가 실제로 쓰는 데이터만 정리한다. 실험·구버전 데이터 16종은 [99a_archive.md](99a_archive.md)

| 파일 | 쓰는 곳 | 형식 | 건수 |
|---|---|---|---|
| `*_품종.xlsx` (20개) | `MBTI_AI.py` → MBTI 학습 | 엑셀 7열 | 345행 |
| `mbti_dataset_final.jsonl` | `mbti_tain.py` → `trained_mbti_expert_v3` | instruction / input / JSON | 서버에만 있음 (**확인이 필요함**) |
| `SoulPaw_SFT_Train_Data_KO_TEST.json` | `train_unsloth.py` → `trained_bigfive_expert_v3` | instruction / input(빈 값) / 번호 텍스트 | 3,000 |
| `SoulPaw_Final_Dataset_v1plus.csv` | `bigfive_ai_server.py` 런타임 | CSV 34열 (cp949) | 53품종 |
| `SoulPaw_Final_Dataset_v1_utf8.csv` | 엑셀 확인용 사본 (utf-8-sig) | 위와 같음 | 53품종 |

## 1. 동물별 품종 엑셀 (20개)
`가재 · 강아지 · 고양이 · 관상어 · 금화조 · 기니피그 · 도마뱀 · 메추리 · 문조 · 뱀 · 비둘기 · 비쉬림프 · 사슴벌레 · 생이새우 · 소라게 · 슈가글라이더 · 앵무새 · 지네 · 타란튤라 · 토끼` + `_품종.xlsx`

| 항목 | 내용 |
|---|---|
| 컬럼 | 동물 · 품종 · 성격 · 특징 · 주의점 · 털길이 · 크기 |
| 행 수 | 강아지 54, 고양이 47, 토끼 28, 도마뱀 26, 관상어 21, 타란튤라 20 … 메추리 6 |
| 형식 문제 | 첫 행이 헤더인 파일 9개, **분류 제목 행(`소형견(10kg이하)` 등)이 데이터 사이에 섞인 파일 11개**. 생성 스크립트가 휴리스틱으로 걸러내므로, 엑셀 형식을 하나로 통일하면 오염 위험이 줄어든다 |

## 2. `SoulPaw_SFT_Train_Data_KO_TEST.json` (Big Five 학습)
| 항목 | 내용 |
|---|---|
| instruction | `사용자의 성격 수치({'개방성': 6, '성실성': 1, …})와 거주 환경({'거주공간': '단독주택', '활동수준': 3, '가족구성원수': 5})에 맞는 반려동물을 추천하세요.` |
| 점수 범위 | 성격 **1~10점** (서빙은 0~1 실수) |
| input | 3,000건 모두 빈 값 |
| output | `1. 추천 동물 종류 … 2. 추천 품종 … 3. 추천 이유 …` 번호 텍스트 (학습 스크립트가 JSON으로 변환) |
| 품종 | 53종 (v1plus CSV와 같은 목록) |
| ⚠️ 품질 | 3,000건 모두 "추천 동물 종류" 칸에 품종 이름이 들어 있음 (예: `동물 종류: 바센지`) |

## 3. `SoulPaw_Final_Dataset_v1plus.csv` (Big Five 서버 런타임)
| 컬럼 그룹 | 컬럼 |
|---|---|
| 기질 점수 (1~5) | 아이들친화력, 다른개들과 친화력, 털빠짐, 미용/관리난이도, 낯선사람과 친화력, 놀이욕구, 경계성, 훈련용이성, 에너지, 짖음 |
| 영문 견종 DB | Breed_EN, description, temperament, popularity, min/max_height, min/max_weight, min/max_expectancy, group, grooming·shedding·energy·trainability·demeanor (value / category) |
| 서비스용 | **유전병**, **초보자가이드** (결과 화면 5·9번 항목에 사용) |
| 결측 | 기질·유전병·초보자가이드 0건. popularity(진돗개)·shedding(아이리시 테리어) 일부 결측, 서버에서는 쓰지 않는 컬럼 |
| 인코딩 | cp949 (서버가 utf-8 → cp949 → utf-8-sig 순서로 시도) |
| 품종 목록 | 서버 코드의 `size_map`·`coat_map` 53종과 정확히 일치. 품종을 추가할 때는 두 맵도 함께 갱신해야 함 |
