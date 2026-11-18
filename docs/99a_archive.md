# 99a. 부록 — 구버전·실험 기록 (아카이브)

> 본문 01~09는 **현재 운영 버전**만 다룬다. 이 부록은 개발 이력과, 지금은 쓰지 않는 코드·데이터·모델을 **목록으로만** 남긴다.
> 정리 권장: 아래 항목은 `archive/` 폴더로 옮기거나 삭제해도 현재 서비스에 영향이 없다 (삭제는 서버에 백업이 있는지 확인한 뒤).

## 1. 개발 이력
| 단계 | 구조 | 흔적 |
|---|---|---|
| 1 | 콘솔 프로토타입: Gemini 2.0 Flash가 직접 추천하고, 응답을 `--동물--`, `!!품종!!` 구분자로 파싱 | `Gemini_test/test.py` |
| 2 | Django 시도 (중단) | `test/manage.py`, `views.cpython-39.pyc` |
| 3 | Flask 웹앱 + Gemini 추천 | `app.py` 초기 버전 (`app.cpython-39.pyc`) |
| 4 | 자체 LLM 도입: 중계 서버(:8000) → 모델 서버(:9000) | `Fastserver.py` |
| 5 | 중계 서버 제거, `ai_server.py` 하나로 통합 (:8000) | **현재** |
| 6 | Big Five 추가: 규칙 기반 매칭 + LLM 설명 (:8001) | **현재** |

## 2. 구버전 코드
| 파일 | 내용 | 비고 |
|---|---|---|
| `Soulpow_AI/Fastserver.py` | :8000 `/recommend` → `:9000/ai_recommend`로 넘기는 중계 서버 | `ai_server.py`의 이전 버전 |
| `Soulpow_AI/AI_test.py` | `trained_pet_expert` 어댑터 단독 추론 테스트 (Big Five 텍스트형) | SSL 검증 해제 코드 포함 |
| `Gemini_test/test.py` | 콘솔 프로토타입 | ⚠️ Gemini 키와 DB 비밀번호 평문, SQL 문자열 이어붙이기 |
| `test/manage.py`, `__pycache__/views.cpython-39.pyc`, `User_DTO.cpython-39.pyc` | Django 흔적, 초기 DTO | 원본 없음 |
| `test/templates/find_pw.html`, `reset_pw.html` | `FindAuth.html`로 통합되기 전의 화면 | app.py에서 렌더링하지 않음 |
| `test/templates/test_servies.html` | 테스트 페이지 | 배포 전 제거 대상 |
| `test/gemma3_test.ipynb` | Colab Gemma 테스트 | GPU 없이 실행해 실패 |
| `Bigfiveresults.html` 구버전 (업로드로 확인) | `score_o` 등 app.py가 넘기지 않는 변수 사용 | 현재 버전은 `data.big5.*` 사용 |

## 3. 구버전 학습 스크립트 (`더블체크_품종`)
| 파일 | 내용 |
|---|---|
| `animal_MBTI.py` | MBTI 데이터 생성 구버전 (`{"text": …}` 한 필드, 아파트/마당X 고정) |
| `big_test.py` | Big Five SFT/DPO/Rank 데이터 생성 (6,000명). ⚠️ 주거 점수를 `int()==1`로 비교하는 버그 |
| `make_bigfive_dataset.py` | 최근접 품종 1개 데이터 (3,000건) |
| `date_set.py` | 섞인 원본을 SFT/DPO/Rank로 분리 |
| `BigFivedatetest.py` | 기질 → OCEAN 변환 (현재는 같은 공식이 `bigfive_ai_server.py` 안에 들어가 있음) |
| `dog_vector_search.py`, `test_recommend.py`, `llm_reason.py`, `recommend_cat.py` | 벡터 검색, 이유 생성, 다른 동물 추천 프로토타입 |
| `__pycache__/recommend_pet.cpython-310.pyc` | 원본 없음 |

## 4. 구버전 어댑터·체크포인트
| 폴더 | r / α / dropout | 크기 | 추정 용도 |
|---|---|---|---|
| `trained_pet_expert` | 32 / 32 / 0 | 320MB | Big Five 텍스트형 초기 모델 (`AI_test.py`) |
| `trained_dog_expert` | 32 / 32 / 0 | 320MB | 강아지 추천 이유 생성 (`llm_reason.py`) |
| `trained_dog_expert_step7` | 32 / 32 / 0 | 320MB | 위 모델의 후속 실험 (확인 필요) |
| `trained_bigfive_expert` | 32 / 32 / 0 | 320MB | Big Five v1 |
| `trained_mbti_model` | 16 / 16 / 0.05 | 160MB | MBTI 초기 버전 |
| `outputs/checkpoint-300·375·400·750·1125` | 16 / 16 / 0 | 각 260MB | Big Five 학습 실험. loss 2.1 → 0.10, **1 epoch 이후 거의 감소하지 않음**(0.109 → 0.106). 현재 `train_unsloth.py`(α=32)와 설정이 달라 v3 이전 실험으로 판단 |

합계 약 2.8GB 중 2.7GB가 여기에 해당한다. 체크포인트의 `optimizer.pt`(5개, 430MB)는 학습을 이어서 할 계획이 없으면 지워도 된다.

## 5. 구버전·실험 데이터셋
| 파일 | 건수 | 내용 | 품질 문제 |
|---|---|---|---|
| `mbti_dog_training_data.jsonl` (업로드) | 1,136 | 가장 초기 MBTI 데이터, 강아지만, Gemini 구분자 형식 | 품종 칸에 헤더 혼입 112건 (`관절`, `구분`, `행동`) |
| `Soulpow_AI/mbti_pet_training_data_test.jsonl` | 1,000 | 강아지 8품종, 번호 텍스트 | – |
| `all_pets_mbti_1000.jsonl` | 1,956 | 다른 동물 포함 MBTI | 헤더 혼입 270건(14%), 중복 37 |
| `all_pets_mbti_final.jsonl` | 1,686 | 위 파일을 정리한 판 | 중복 2 |
| `all_pets_mbti_finetuning_1000.jsonl`, `_v2.jsonl` | 1,128 / 188 | MBTI 실험 | 문장 오류 |
| `pets_mbti_dataset_final.jsonl` | 3,000 | 선호·비선호 반영 텍스트형 | 기니피그 31% |
| `test.jsonl` | 3,000 | MBTI | 사슴벌레 92.5%, 중복 112 |
| `ultimate_pets_dataset.jsonl` | 2,500 | 줄글 서술형 | – |
| `SoulPaw_SFT_Train_Data_KO.json` | 3,000 | KO_TEST의 이전 판 | output 앞에 `### 출력 형식 (고정)` |
| `sft.jsonl`, `sft_dataset.jsonl`, `sft_final.jsonl` | 5,000 / 6,000 / 6,000 | Big Five SFT 실험 (`big_test.py`) | 고정 문구 |
| `dpo.jsonl`, `rank_dataset.jsonl`, `dog_recommend_dataset.jsonl` | 5,000 / 6,000 / 15,000 | DPO·랭킹 실험 | DPO로 학습한 흔적 없음 |
| `pets_bigfive_dataset.jsonl` | 3,000 | `추천 품종: X` 한 줄 | – |
| `SoulPaw_Final_Dataset_v1.csv` (업로드) | 53 | v1plus의 이전 판 (유전병·초보자가이드 없음) | – |
| `강아지_빅파이브.csv`, `_완성.csv`, `_최종.csv`, `dog_bigfive_final.csv`, `total_pet_bigfive_result.csv`, `고양이_빅파이브.csv` | 9~124 | 기질 데이터 가공 중간본 | 97종 → 53종으로 줄어든 이력 |

## 6. 구버전 화면
- `docs/images/02_bigfive_result.png`의 리포트는 **8개 항목**으로, 이전 Big Five 서버의 출력이다. 현재 서버는 9개 항목을 출력한다. 최신 화면으로 다시 캡처하는 것을 권장한다.
