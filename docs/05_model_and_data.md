# 05. 모델 (현재 운영 버전)

## 베이스 모델 `Soulpow_AI/llama3_model/` (5.4GB)
| 항목 | 값 (`config.json`) |
|---|---|
| 원본 | `unsloth/llama-3-8b` (Base 모델, Instruct 아님) |
| 구조 | LlamaForCausalLM, 32 layers, hidden 4096, heads 32 / KV 8 (GQA), vocab 128,256 |
| 컨텍스트 | 8,192 (서버에서는 `max_seq_length=2048`) |
| 양자화 | bitsandbytes 4bit **NF4**, double quant, compute dtype bfloat16 |
| 버전 | transformers 4.44.2, unsloth 2024.9 |
| 파일 | `model.safetensors` 5.70GB, `tokenizer.json` 9MB, `tokenizer_config.json`, `special_tokens_map.json`, `generation_config.json` |
| 생성 기본값 | `do_sample=True, temperature=0.6, top_p=0.9` |
| 토큰 | bos 128000, eos 128001, pad 128255 |
| 실행 GPU | NVIDIA RTX 4070 12GB |

## 운영 중인 LoRA 어댑터
| 어댑터 | 서버 | r / α / dropout | 학습 스크립트 | 학습 데이터 |
|---|---|---|---|---|
| `trained_mbti_expert_v3` | `ai_server.py` :8000 | 16 / 16 / 0.05 | `mbti_tain.py` (5 epoch) | `mbti_dataset_final.jsonl` (`MBTI_AI.py`로 생성) |
| `trained_bigfive_expert_v3` | `bigfive_ai_server.py` :8001 | 16 / 32 / 0 | `train_unsloth.py` (3 epoch) | `SoulPaw_SFT_Train_Data_KO_TEST.json` (3,000건) |

- 두 어댑터 모두 대상 모듈은 7개(q, k, v, o, gate, up, down)
- ⚠️ 두 어댑터와 MBTI 학습 데이터는 **리눅스 서버(`/home/soulpow_2121/`)에만 있다.** r·α 값은 스크립트 기준이며, 실제 `adapter_config.json`과의 대조는 **확인이 필요함**
- 학습 과정 상세: [07_training_pipeline.md](07_training_pipeline.md) / 데이터: [08_datasets.md](08_datasets.md)

## VRAM
- 모델 1개(4bit)에 약 5.5~6GB가 들고, 여기에 CUDA 컨텍스트와 KV 캐시가 더해진다 (추정)
- 서버 2개가 같은 베이스 모델을 각자 로딩하므로, 12GB가 거의 꽉 찬다 → [99](99_known_issues.md) F14
- 개선안: 베이스 모델은 1번만 로딩하고, 어댑터 2개를 `load_adapter`로 붙인 뒤 요청마다 `set_adapter`로 전환

## ⚠️ 핵심 문제

### 1) MBTI 라벨이 무작위다
`MBTI_AI.py`는 정답(동물·품종)을 엑셀 행에서 정하고, MBTI는 `random.choice`로 따로 뽑는다. 그런데 정답 동물은 항상 입력의 "추천 가능한 동물 후보" 목록에 들어 있다.
→ 모델은 MBTI가 아니라 **후보 목록과 선호 동물을 보고 고르는 법**을 배운다. 서빙할 때 후보는 무작위 5개(`random.sample`)이므로 **결과가 MBTI와 무관하게 사실상 무작위**일 가능성이 높다.

### 2) 학습 템플릿 ↔ 서빙 프롬프트 불일치
| | 학습 | 서빙 |
|---|---|---|
| MBTI 틀 | `### 지시:` / `### 입력:` / `### 응답:` | 틀 없음, `JSON:`으로 끝남 |
| MBTI 필드 이름 | `추천 가능한 동물 후보`, `선호동물`, `비선호동물`, `제외 품종` | `후보`, `선호`, `비선호`, `제외` |
| MBTI 주거 값 | 아파트 / 주택 / 원룸 | 화면: 아파트 / 빌라 / 단독주택 |
| Big Five 과제 | 성격 점수(1~10)를 보고 **품종 선택 + 설명** | 이미 고른 품종의 **설명만** 작성 |
| Big Five 출력 키 | 5개 | 4개 요청 |

### 개선 방향
| 방안 | 내용 | 장단점 |
|---|---|---|
| A. 서빙 프롬프트를 학습 템플릿에 맞추기 | `### 지시/입력/응답` 틀과 학습 때 쓴 필드 이름·값으로 변경 | 재학습 없이 바로 적용 가능, JSON 성공률 향상 기대. MBTI 무작위 라벨 문제는 그대로 |
| B. 라벨 규칙 정의 후 재학습 | MBTI 축별 동물 기질 매핑 규칙을 정하고, 그 규칙으로 정답 생성 | 근본적인 해결. 규칙 설계에 근거가 필요함 |
| C. Big Five 방식으로 통일 | 동물·품종 선택은 규칙/검색, LLM은 설명만 | 가장 안정적이고 설명하기 쉬움. 이미 Big Five 서버에서 검증된 구조 |

구버전 모델과 데이터: [99a_archive.md](99a_archive.md)
