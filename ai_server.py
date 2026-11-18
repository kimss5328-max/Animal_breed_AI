from fastapi import FastAPI
from pydantic import BaseModel
from unsloth import FastLanguageModel
from peft import PeftModel
from typing import List, Optional

import torch
import uvicorn
import json
import re
import os
import random

# =====================================================
# FastAPI
# =====================================================
app = FastAPI()

# =====================================================
# 모델 경로
# =====================================================
MODEL_DIR = "/home/soulpow_2121/Soulpow_AI/llama3_model"
LORA_DIR = "/home/soulpow_2121/trained_mbti_expert_v3"

# =====================================================
# 모델 로딩
# =====================================================
print("🚀 SoulPaw 모델 로딩 시작...")

if not os.path.exists(MODEL_DIR):
    raise Exception(f"❌ MODEL_DIR 없음: {MODEL_DIR}")

if not os.path.exists(LORA_DIR):
    raise Exception(f"❌ LORA_DIR 없음: {LORA_DIR}")

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_DIR,
    max_seq_length=2048,
    load_in_4bit=True,
    dtype=None,
    device_map="auto",
)

model = PeftModel.from_pretrained(
    model,
    LORA_DIR
)

FastLanguageModel.for_inference(model)

print("✅ 모델 로딩 완료")

# =====================================================
# 반려동물 종류
# =====================================================
ANIMAL_TYPES = [
    "가재",
    "강아지",
    "고양이",
    "관상어",
    "금화조",
    "기니피그",
    "도마뱀",
    "메추리",
    "문조",
    "뱀",
    "비둘기",
    "비쉬림프",
    "사슴벌레",
    "생이새우",
    "소라게",
    "슈가글라이더",
    "앵무새",
    "지네",
    "타란튤라",
    "토끼"
]

# =====================================================
# fallback 품종
# =====================================================
FALLBACK_BREEDS = {
    "강아지": [
        "푸들",
        "말티즈",
        "비글",
        "웰시코기",
        "포메라니안",
        "시바견"
    ],

    "고양이": [
        "코리안 숏헤어",
        "러시안 블루",
        "샴",
        "페르시안"
    ],

    "관상어": [
        "구피",
        "베타",
        "네온테트라"
    ],

    "햄스터": [
        "골든 햄스터",
        "드워프 햄스터"
    ]
}

# =====================================================
# 입력 스키마
# =====================================================
class UserInput(BaseModel):
    mbti: str
    environment: str
    yard: str
    prefer: Optional[str] = "없음"
    dislike: Optional[str] = "없음"
    exclude_breeds: List[str] = []

# =====================================================
# 동물명 정규화
# =====================================================
def normalize_animal(animal):

    if animal is None:
            return "없음"

    animal = (
        str(animal)
        .strip()
        .replace(" ", "")
        .lower()
    )

    mapping = {
        "": "없음",
        "없음": "없음",
        "none": "없음",
        "null": "없음",

        # 강아지
        "개": "강아지",
        "강아지": "강아지",
        "견": "강아지",
        "멍멍이": "강아지",
        "dog": "강아지",

        # 고양이
        "고양이": "고양이",
        "냥이": "고양이",
        "묘": "고양이",
        "cat": "고양이",

        "기니피그": "기니피그",
        "토끼": "토끼",
        "뱀":"뱀",
        "비둘기":"비둘기",
        "사슴벌레":"사슴벌레",
        "메추리":"메추리",
        "슈가글라이더":"슈가글라이더",
        "비쉬림프":"비쉬림프",
        "생이새우":"생이새우",
        "지네":"지네",
        "타란튤라":"타란튤라",
        "소라게":"소라게",

        "앵무새": "앵무새",
        "문조":"문조",
        "금화조":"금화조",

        "물고기": "관상어",
        "관상어": "관상어",

        "도마뱀": "도마뱀",
    }

    return mapping.get(animal, animal)

# =====================================================
# 텍스트 정리
# =====================================================
def clean_text(text):

    text = str(text)

    text = text.replace("```json", "")
    text = text.replace("```", "")

    return text.strip()

# =====================================================
# JSON 추출
# =====================================================
def extract_json(text):

    try:
        text = clean_text(text)

        start = text.find("{")

        if start == -1:
            print("❌ JSON 시작 없음")
            return None

        brace_count = 0
        end = -1

        for i in range(start, len(text)):

            if text[i] == "{":
                brace_count += 1

            elif text[i] == "}":
                brace_count -= 1

                if brace_count == 0:
                    end = i + 1
                    break

        if end == -1:
            print("❌ JSON 종료 없음")
            return None

        json_text = text[start:end]

        print("\n🔥 추출 JSON:")
        print(json_text)

        parsed = json.loads(json_text)

        return parsed

    except Exception as e:

        print("❌ JSON 파싱 실패:", e)

        return None

# =====================================================
# 제외 품종 검사
# =====================================================
def is_excluded(breed, excluded):

    breed = (
        str(breed)
        .replace(" ", "")
        .lower()
        .strip()
    )

    for ex in excluded:

        ex = (
            str(ex)
            .replace(" ", "")
            .lower()
            .strip()
        )

        if breed == ex:
            return True

        if ex in breed:
            return True

        if breed in ex:
            return True

    return False

# =====================================================
# 비선호 동물 검사
# =====================================================
def is_disliked(animal, breed, dislike):

    dislike_norm = normalize_animal(dislike)

    if dislike_norm == "없음":
        return False

    animal_norm = normalize_animal(animal)

    breed_clean = re.sub(
        r"[^가-힣a-zA-Z0-9]",
        "",
        str(breed)
    ).lower().strip()

    dislike_clean = re.sub(
        r"[^가-힣a-zA-Z0-9]",
        "",
        dislike_norm
    ).lower().strip()

    if animal_norm == dislike_norm:
        return True

    if dislike_clean in breed_clean:
        return True

    return False

# =====================================================
# 결과 검증
# =====================================================
def validate_result(
    result,
    prefer_list,
    dislike_list,
    excluded
):
    required_keys = [
        "animal_type",
        "breed",
        "reason",
        "warning",
        "environment_fit",
        "size_text",
        "guide"
    ]
    for key in required_keys:
        if key not in result:
            print(f"❌ 키 누락: {key}")
            return False
    animal = normalize_animal(
        result.get("animal_type", "")
    )
    result["animal_type"] = animal
    breed = str(
        result.get("breed", "")
    ).strip()
    if len(breed) < 2:
        print("❌ 품종 길이 오류")
        return False
    if animal not in ANIMAL_TYPES:
        print("❌ 잘못된 동물 타입")
        return False
    if "없음" not in prefer_list:

        if animal not in prefer_list:
            print("❌ 선호 동물 불일치")
            return False
    for dislike in dislike_list:
        if dislike == "없음":
            continue
        if is_disliked(
            animal,
            breed,
            dislike
        ):
            print("❌ 비선호 동물 감지")
            return False
    if is_excluded(
        breed,
        excluded
    ):
        print("❌ 제외 품종 감지")
        return False

    return True
# =====================================================
# 추천 API
# =====================================================
@app.post("/recommend")
def recommend(data: UserInput):

    try:

        print("\n==============================")
        print("🔥 추천 요청")
        print("==============================")

        print("🔥 입력 데이터:", data)

        raw_prefer = str(data.prefer or "").strip()
        raw_dislike = str(data.dislike or "").strip()

        # 쉼표 여러개 대응
        prefer_list = [
            normalize_animal(x)
            for x in raw_prefer.split(",")
            if x.strip()
        ]

        dislike_list = [
            normalize_animal(x)
            for x in raw_dislike.split(",")
            if x.strip()
        ]

        if not prefer_list:
            prefer_list = ["없음"]

        if not dislike_list:
            dislike_list = ["없음"]

        print("🔥 선호 리스트:", prefer_list)
        print("🔥 비선호 리스트:", dislike_list)

        excluded = [
            b.strip()
            for b in data.exclude_breeds
            if b.strip()
        ]

        print("🔥 제외 품종:", excluded)

        # =====================================================
        # 후보군 생성
        # =====================================================
        available_candidates = [
            animal for animal in ANIMAL_TYPES
            if normalize_animal(animal) not in dislike_list
        ]

        # 선호 동물 적용
        if "없음" not in prefer_list:

            available_candidates = [
                animal
                for animal in available_candidates
                if normalize_animal(animal) in prefer_list
            ]

        if not available_candidates:
            available_candidates = [
                animal for animal in ANIMAL_TYPES
                if normalize_animal(animal) not in dislike_list
            ]

        print("🔥 후보군:", available_candidates)

        # =====================================================
        # 추론 루프
        # =====================================================
        result = None

        MAX_RETRY = 5

        for attempt in range(MAX_RETRY):

            print(f"\n🔥 {attempt+1}번째 시도")

            exclude_text = (
                ", ".join(excluded)
                if excluded
                else "없음"
            )

            animal_hint = ", ".join(
                random.sample(
                    available_candidates,
                    min(
                        len(available_candidates),
                        5
                    )
                )
            )

            instruction = """
JSON만 출력하라.

{
 "animal_type":"강아지",
 "breed":"푸들",
 "reason":"추천 이유",
 "warning":"주의사항",
 "environment_fit":"환경 적합성",
 "size_text":"크기 설명",
 "guide":"초보자 가이드"
}

JSON 외 문장 출력 금지.
exclude_breeds 품종 추천 금지.
"""

            prompt = f"""
{instruction}

MBTI:{data.mbti}
환경:{data.environment}
마당:{data.yard}
선호:{", ".join(prefer_list)}
비선호:{", ".join(dislike_list)}
제외:{exclude_text}
후보:{animal_hint}

JSON:
"""

            inputs = tokenizer(
                prompt,
                return_tensors="pt"
            ).to(model.device)

            with torch.no_grad():

                output = model.generate(
                    **inputs,
                    max_new_tokens=220,
                    temperature=0.45,
                    top_p=0.85,
                    do_sample=True,
                    repetition_penalty=1.05,
                    eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.eos_token_id,
                )

                generated = tokenizer.decode(
                    output[0][inputs["input_ids"].shape[-1]:],
                    skip_special_tokens=True
                )


            print("\n🔥 생성 결과:")
            print(generated)

            parsed = extract_json(generated)

            if parsed is None:
                print("❌ JSON 추출 실패")
                continue

            if validate_result(
                parsed,
                prefer_list,
                dislike_list,
                excluded
            ):

                print("✅ 검증 통과")

                result = parsed

                break

            print("⚠️ 검증 실패 → 재시도")

        # =====================================================
        # fallback
        # =====================================================
        if result is None:

            print("⚠️ fallback 작동")

            if (
                "없음" not in prefer_list
                and len(prefer_list) > 0
            ):
                fallback_type = random.choice(prefer_list)

            else:
                fallback_type = random.choice(
                    available_candidates
                )

                

            breed_pool = FALLBACK_BREEDS.get(
                fallback_type,
                ["일반 품종"]
            )

            available_breeds = [
                breed for breed in breed_pool
                if not is_excluded(
                    breed,
                    excluded
                )
            ]

            if not available_breeds:
                available_breeds = ["일반 품종"]

            fallback_breed = random.choice(
                available_breeds
            )

            result = {
                "animal_type": fallback_type,
                "breed": fallback_breed,
                "reason": "사용자의 성향과 생활 패턴을 분석하여 추천했습니다.",
                "warning": "정기적인 건강 관리가 필요합니다.",
                "environment_fit": "현재 주거 환경에서 안정적으로 생활 가능합니다.",
                "size_text": "실내 생활 적응력이 우수합니다.",
                "guide": "초보자도 비교적 쉽게 양육 가능합니다."
            }

        # =====================================================
        # 출력 구성
        # =====================================================
        animal = result.get(
            "animal_type",
            "관상어"
        )

        breed = result.get(
            "breed",
            "구피"
        )

        yard_text = (
            "마당 없이도 생활 가능합니다."
            if data.yard == "X"
            else "마당 활용 시 활동량 충족에 도움이 됩니다."
        )

        full_text = f"""
1. 추천 동물 종류: {animal}
2. 추천 품종: {breed}
3. 추천 이유: {result.get("reason", "")}
4. 주의사항 및 유전병: {result.get("warning", "")}
5. 거주 환경 적합성: {result.get("environment_fit", "")}
6. 크기 및 특징: {result.get("size_text", "")}
7. 마당 관련 조언: {yard_text}
8. 초보자 가이드: {result.get("guide", "")}
"""

        return {
            "status": "success",
            "animal": animal,
            "breed": breed,
            "result": result,
            "full_text": full_text
        }

    except Exception as e:

        print("❌ 시스템 에러:", str(e))

        return {
            "status": "error",
            "message": str(e)
        }

# =====================================================
# 실행
# =====================================================
if __name__ == "__main__":

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )