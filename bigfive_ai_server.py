import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from pydantic import BaseModel
from unsloth import FastLanguageModel
from peft import PeftModel

import pandas as pd
import numpy as np
import torch
import uvicorn
import json
import re

app = FastAPI()
# GPU 연산 코어 부하 및 VRAM 안정성을 위해 워커 풀 최적화
executor = ThreadPoolExecutor(max_workers=2)

# =====================================================
# 1. LLM MODEL LOAD
# =====================================================
BASE_MODEL = "/home/soulpow_2121/Soulpow_AI/llama3_model"
LORA_MODEL = "/home/soulpow_2121/trained_bigfive_expert_v3"

print("🚀 LLM 로딩 시작 (SoulPaw 서빙 엔지니어링)")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=BASE_MODEL,
    max_seq_length=2048,
    load_in_4bit=True,
    device_map="auto",
)
model = PeftModel.from_pretrained(model, LORA_MODEL)
FastLanguageModel.for_inference(model)
print("✅ LLM 로딩 완료")

# =====================================================
# 2. REAL CSV DATASET LOAD & FALLBACK
# =====================================================
DATA_PATH = "/home/soulpow_2121/더블체크_품종/SoulPaw_Final_Dataset_v1plus.csv"

try:
    df = pd.read_csv(DATA_PATH, encoding="utf-8")
except UnicodeDecodeError:
    try:
        df = pd.read_csv(DATA_PATH, encoding="cp949")
    except UnicodeDecodeError:
        df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")

df.columns = [c.strip() for c in df.columns]
df["품종"] = df["품종"].str.strip()

# 하드코딩 매핑 데이터 (한글 표준화 버전)
size_map = {
    "골든 리트리버": {"크기": "대형견", "weight_min": 25.0, "weight_max": 34.0, "height_min": 51, "height_max": 61},
    "래브라도 리트리버": {"크기": "대형견", "weight_min": 25.0, "weight_max": 36.0, "height_min": 54, "height_max": 62},
    "그레이트 데인": {"크기": "대형견", "weight_min": 45.0, "weight_max": 90.0, "height_min": 71, "height_max": 86},
    "복서": {"크기": "대형견", "weight_min": 25.0, "weight_max": 36.0, "height_min": 53, "height_max": 63},
    "불마스티프": {"크기": "대형견", "weight_min": 45.0, "weight_max": 59.0, "height_min": 61, "height_max": 69},
    "그레이하운드": {"크기": "대형견", "weight_min": 27.0, "weight_max": 40.0, "height_min": 68, "height_max": 76},
    "그레이트 피레니즈": {"크기": "대형견", "weight_min": 39.0, "weight_max": 54.0, "height_min": 65, "height_max": 82},
    "버니즈 마운틴 독": {"크기": "대형견", "weight_min": 32.0, "weight_max": 52.0, "height_min": 58, "height_max": 70},
    "뉴펀들랜드": {"크기": "대형견", "weight_min": 45.0, "weight_max": 68.0, "height_min": 66, "height_max": 71},
    "로트와일러": {"크기": "대형견", "weight_min": 35.0, "weight_max": 60.0, "height_min": 56, "height_max": 69},
    "아키타": {"크기": "대형견", "weight_min": 32.0, "weight_max": 59.0, "height_min": 61, "height_max": 71},
    "블러드하운드": {"크기": "대형견", "weight_min": 36.0, "weight_max": 50.0, "height_min": 58, "height_max": 69},
    "코몬도르": {"크기": "대형견", "weight_min": 36.0, "weight_max": 61.0, "height_min": 65, "height_max": 80},
    "도베르만 핀셔": {"크기": "대형견", "weight_min": 30.0, "weight_max": 45.0, "height_min": 63, "height_max": 72},
    "사모예드": {"크기": "대형견", "weight_min": 20.0, "weight_max": 30.0, "height_min": 48, "height_max": 60},
    "로디지안 리지백": {"크기": "대형견", "weight_min": 32.0, "weight_max": 39.0, "height_min": 61, "height_max": 69},
    "알래스칸 말라뮤트": {"크기": "대형견", "weight_min": 34.0, "weight_max": 43.0, "height_min": 58, "height_max": 66},
    "아이리시 세터": {"크기": "대형견", "weight_min": 27.0, "weight_max": 32.0, "height_min": 58, "height_max": 67},
    "달마시안": { "크기": "중형견", "weight_min": 16.0, "weight_max": 32.0, "height_min": 48, "height_max": 61},

    "바센지": { "크기": "중형견", "weight_min": 9.0, "weight_max": 11.0, "height_min": 40, "height_max": 43},
    "시베리안 허스키": {"크기": "중형견", "weight_min": 16.0, "weight_max": 27.0, "height_min": 50, "height_max": 60},
    "차우차우": {"크기": "중형견", "weight_min": 20.0, "weight_max": 32.0, "height_min": 43, "height_max": 56},
    "차이니즈 샤페이": {"크기": "중형견", "weight_min": 18.0, "weight_max": 29.0, "height_min": 46, "height_max": 51},
    "불 테리어": {"크기": "중형견", "weight_min": 22.0, "weight_max": 38.0, "height_min": 45, "height_max": 55},
    "휘핏": {"크기": "중형견", "weight_min": 11.0, "weight_max": 18.0, "height_min": 44, "height_max": 56},
    "바셋 하운드": {"크기": "중형견", "weight_min": 20.0, "weight_max": 29.0, "height_min": 28, "height_max": 38},
    "진돗개": {"크기": "중형견", "weight_min": 15.0, "weight_max": 23.0, "height_min": 45, "height_max": 55},
    "벨지안 말리노이즈": {"크기": "중형견", "weight_min": 20.0, "weight_max": 30.0, "height_min": 56, "height_max": 66},
    "오스트레일리안 셰퍼드": {"크기": "중형견", "weight_min": 18.0, "weight_max": 30.0, "height_min": 46, "height_max": 58},
    "비글": {"크기": "중형견", "weight_min": 9.0, "weight_max": 14.0, "height_min": 33, "height_max": 41},
    "보더 콜리": {"크기": "중형견", "weight_min": 14.0, "weight_max": 20.0, "height_min": 46, "height_max": 56},
    "카디건 웰시 코기": {"크기": "중형견", "weight_min": 11.0, "weight_max": 17.0, "height_min": 26, "height_max": 33},
    "코커 스패니얼": {"크기": "중형견", "weight_min": 12.0, "weight_max": 16.0, "height_min": 34, "height_max": 39},
    "비즐라": {"크기": "중형견", "weight_min": 20.0, "weight_max": 30.0, "height_min": 53, "height_max": 64},
    "셰틀랜드 쉽독": {"크기": "중형견", "weight_min": 6.0, "weight_max": 12.0, "height_min": 33, "height_max": 41},
    "시바 이누": {"크기": "중형견", "weight_min": 8.0, "weight_max": 11.0, "height_min": 35, "height_max": 43},
    "아이리시 테리어": {"크기": "중형견", "weight_min": 11.0, "weight_max": 13.0, "height_min": 45, "height_max": 48},
    "프렌치 불독": {"크기": "중형견", "weight_min": 8.0, "weight_max": 14.0, "height_min": 28, "height_max": 33},
    "펨브록 웰시 코기": {"크기": "중형견", "weight_min": 10.0, "weight_max": 14.0, "height_min": 25, "height_max": 30},

    "시추": {"크기": "소형견", "weight_min": 4.0, "weight_max": 7.0, "height_min": 20, "height_max": 28},
    "포메라니안": {"크기": "소형견", "weight_min": 1.8, "weight_max": 3.5, "height_min": 18, "height_max": 24},
    "웨스트 하이랜드 화이트 테리어": {"크기": "소형견", "weight_min": 6.0, "weight_max": 10.0, "height_min": 25, "height_max": 30},
    "퍼그": {"크기": "소형견", "weight_min": 6.0, "weight_max": 8.0, "height_min": 25, "height_max": 33},
    "보스턴 테리어": {"크기": "소형견", "weight_min": 5.0, "weight_max": 11.0, "height_min": 38, "height_max": 43},
    "말티즈": {"크기": "소형견", "weight_min": 2.0, "weight_max": 4.0, "height_min": 20, "height_max": 25},
    "비숑 프리제": {"크기": "소형견", "weight_min": 5.0, "weight_max": 10.0, "height_min": 23, "height_max": 30},
    "치와와": {"크기": "소형견", "weight_min": 1.5, "weight_max": 3.0, "height_min": 15, "height_max": 23},
    "페키니즈": {"크기": "소형견", "weight_min": 3.0, "weight_max": 6.0, "height_min": 15, "height_max": 23},
    "하바니즈": {"크기": "소형견", "weight_min": 3.0, "weight_max": 6.0, "height_min": 21, "height_max": 29},
    "파피용": {"크기": "소형견", "weight_min": 3.0, "weight_max": 5.0, "height_min": 20, "height_max": 28},
    "요크셔 테리어": {"크기": "소형견", "weight_min": 2.0, "weight_max": 3.0, "height_min": 18, "height_max": 23},
    "이탈리안 그레이하운드": {"크기": "소형견", "weight_min": 3.0, "weight_max": 6.0, "height_min": 32, "height_max": 38},
    "카발리에 킹 찰스 스패니얼": {"크기": "소형견", "weight_min": 5.0, "weight_max": 8.0, "height_min": 30, "height_max": 33}
}

coat_map = {
    "골든 리트리버": "장모종", "그레이트 피레니즈": "장모종", "버니즈 마운틴 독": "장모종",
    "뉴펀들랜드": "장모종", "사모예드": "장모종", "오스트레일리안 셰퍼드": "장모종",
    "셰틀랜드 쉽독": "장모종", "아이리시 세터": "장모종", "코커 스패니얼": "장모종",
    "시추": "장모종", "포메라니안": "장모종", "말티즈": "장모종", "요크셔 테리어": "장모종",
    "페키니즈": "장모종", "하바니즈": "장모종", "파피용": "장모종", "카발리에 킹 찰스 스패니얼": "장모종",
    "코몬도르": "특수모(장모류)", "비숑 프리제": "중장모종(곱슬모)", "웨스트 하이랜드 화이트 테리어": "중단모(이중모)",
    "시베리안 허스키": "중모종", "차우차우": "중모종", "아키타": "중모종", 
    "진돗개": "중모종", "알래스칸 말라뮤트": "중모종", "보더 콜리": "중모종", 
    "시바 이누": "중모종", "벨지안 말리노이즈": "중모종", "웰시 코기": "중모종",
    "펨브록 웰시 코기": "중모종", "카디건 웰시 코기": "중모종",
    "래브라도 리트리버": "단모종", "그레이트 데인": "단모종", "복서": "단모종", 
    "불마스티프": "단모종", "그레이하운드": "단모종", "로트와일러": "단모종", 
    "도베르만 핀셔": "단모종", "로디지안 리지백": "단모종", "비글": "단모종", 
    "비즐라": "단모종", "아이리시 테리어": "단모종", "프렌치 불독": "단모종", 
    "불 테리어": "단모종", "휘핏": "단모종", "바셋 하운드": "단모종", 
    "퍼그": "단모종", "보스턴 테리어": "단모종", "치와와": "단모종", 
    "이탈리안 그레이하운드": "단모종", "차이니즈 샤페이": "단모종",
    "달마시안": "단모종", "바센지": "단모종",
}

# =====================================================
# 3. BIG FIVE & 환경 점수 산출
# =====================================================
def safe_num(series, default=3):
    return pd.to_numeric(series, errors="coerce").fillna(default)

energy = safe_num(df.get("에너지"))
play = safe_num(df.get("놀이욕구"))
train = safe_num(df.get("훈련용이성"))
friendly_child = safe_num(df.get("아이들친화력"))
friendly_dog = safe_num(df.get("다른개들과 친화력"))
friendly_people = safe_num(df.get("낯선사람과 친화력"))
guard = safe_num(df.get("경계성"))
bark = safe_num(df.get("짖음"))

df["E"] = ((energy + play) / 2 / 5).round(2)
df["A"] = ((friendly_child + friendly_dog + friendly_people) / 3 / 5).round(2)
df["C"] = ((train + (6 - bark)) / 2 / 5).round(2) 
df["N"] = ((guard + bark) / 2 / 5).round(2)
df["O"] = ((friendly_people + train) / 2 / 5).round(2)

df["환경_아파트"] = 1.0; df["환경_빌라"] = 1.0; df["환경_단독주택"] = 1.0; df["마당필요도"] = 0.0

for i, row in df.iterrows():
    apt_score, villa_score, yard_need = 1.0, 1.0, 0.0
    noise_factor = (row["짖음"] + row["경계성"]) / 2
    if noise_factor >= 4.0: apt_score -= 0.4; villa_score -= 0.3
    elif noise_factor >= 3.0: apt_score -= 0.2; villa_score -= 0.1
    if row["E"] > 0.75: apt_score -= 0.4; yard_need += 0.8
    elif row["E"] > 0.60: apt_score -= 0.2; yard_need += 0.4
    if row["털빠짐"] >= 4.0: villa_score -= 0.3
    elif row["털빠짐"] >= 3.0: villa_score -= 0.1

    df.at[i, "환경_아파트"] = round(max(0.1, apt_score), 2)
    df.at[i, "환경_빌라"] = round(max(0.1, villa_score), 2)
    df.at[i, "환경_단독주택"] = 1.0
    df.at[i, "마당필요도"] = round(min(1.0, yard_need), 2)

# =====================================================
# 4. INPUT MODEL & UTILS
# =====================================================
class BigFiveInput(BaseModel):
    O: float
    C: float
    E: float
    A: float
    N: float
    environment: str
    yard: str
    exclude: list[str] = []

def safe(v, default=""):
    return str(v).strip() if pd.notna(v) else default

def normalize_breed_name(name):
    if not name: return ""
    return re.sub(r"\s+", "", str(name)).replace("/", "").replace("(", "").replace(")", "").lower()

# =====================================================
# 5. 추천 엔진 및 성향 데이터 매칭 분석기
# =====================================================
def recommend(user, exclude):
    normalized_exclude = [normalize_breed_name(x) for x in exclude]
    data = df[~df["품종"].apply(lambda x: normalize_breed_name(x) in normalized_exclude)].copy()
    if len(data) == 0: data = df.copy()

    def score(row):
        dist = np.sqrt(
            (user["O"] - row["O"])**2 + (user["C"] - row["C"])**2 +
            (user["E"] - row["E"])**2 + (user["A"] - row["A"])**2 + (user["N"] - row["N"])**2
        )
        s = 1 / (dist + 0.05)
        if user["environment"] == "아파트": s *= row["환경_아파트"]
        elif user["environment"] == "빌라": s *= row["환경_빌라"]
        if user["yard"] != "있음" and row["마당필요도"] >= 0.6: s *= (1.0 - (row["마당필요도"] * 0.4))
        return s

    data["score"] = data.apply(score, axis=1)
    top_candidates = data.sort_values(by="score", ascending=False).head(10).copy()
    
    score_sum = top_candidates["score"].sum()
    top_candidates["prob"] = top_candidates["score"] / score_sum if score_sum > 0 else 1.0 / len(top_candidates)
    return top_candidates.sample(1, weights="prob").iloc[0]


def compile_detailed_reason(user, row):
    match_details = []
    
    # 1. 외향성 (E)
    e_diff = abs(user["E"] - row["E"])
    if e_diff <= 0.2:
        match_details.append(f"보호자의 라이프 템포(E: {user['E']})와 이 품종 고유의 활동 지표(에너지: {row['에너지']}/5, 놀이욕구: {row['놀이욕구']}/5)가 완벽하게 동기화되어 주기적인 산책과 활동 주기를 조화롭게 공유할 수 있습니다.")
    elif user["E"] > row["E"]:
        match_details.append(f"보호자는 에너제틱한 성향(E: {user['E']})인 반면, 본 품종은 실내에서 매우 차분하게 휴식을 취하는 성향(에너지: {row['에너지']}/5)을 지니고 있어 보호자의 일상적 스트레스와 피로도를 덜어주는 정서적 안식처가 되어 줍니다.")
    else:
        match_details.append(f"본 품종은 장난기가 넘치고 에너지 레벨이 활발하여(놀이욕구: {row['놀이욕구']}/5), 다소 정적일 수 있는 보호자의 환경(E: {user['E']})에 긍정적인 활력과 생기를 불어넣어 줄 완벽한 페이스메이커 역할을 수행합니다.")

    # 2. 친화성 (A)
    if row["A"] >= 0.7:
        match_details.append(f"품종 고유의 높은 사회성 수치(A: {row['A']})는 어린아이({row['아이들친화력']}/5) 및 타견종({row['다른개들과 친화력']}/5)은 물론이고 낯선 사람에게도 배타성이 낮아 원만한 대인/대견 관계를 안정적으로 유지합니다.")
    else:
        match_details.append(f"과도하게 치닫지 않는 독립적이고 진중한 성품이 보호자의 차분한 관계 성향(A: {user['A']})과 호응하여, 잦은 요구성 행동이나 분리불안 없이 성숙하고 깊은 교감을 축적해 나갑니다.")

    # 3. 성실성 (C)
    if row["훈련용이성"] >= 4:
        match_details.append(f"지능이 높고 사람과의 소통 협조도(훈련용이성: {row['훈련용이성']}/5)가 매우 탁월하여, 계획적이고 일관성 있는 상호작용 규칙을 지향하는 보호자(C: {user['C']})의 통제 성향하에 가장 이상적인 반려견으로 교육 및 관리가 가능합니다.")
    else:
        match_details.append(f"자기 주관이 조심스럽게 드러나는 품종이나 일상적인 기본 양육 규칙 안에서 칭찬 중심의 피드백을 유지한다면 가정 내 규칙을 무리 없이 습득할 수 있는 구조입니다.")

    # 4. 소음 및 환경 리스크
    env = user["environment"]
    if env in ["아파트", "빌라"]:
        noise_avg = (row["짖음"] + row["경계성"]) / 2
        if noise_avg <= 2.5:
            match_details.append(f"공동주택({env}) 생활 환경의 아킬레스건인 소음 발생률(짖음 빈도: {row['짖음']}/5, 경계성: {row['경계성']}/5)이 극히 미미하게 설계되어 이웃 간 소음 분쟁 우려로부터 한층 자유롭습니다.")
        else:
            match_details.append(f"공동주택({env}) 여건상 영역 경계심 완화를 위한 초반 소음 방지 교육이 권장되며 보호자의 꼼꼼한 케어와 환경 조성으로 안전하게 커버 가능한 적합도입니다.")

    return "\n- ".join(match_details)

# =====================================================
# 6. LLM 전문가 소견 생성기 (순수 한국어 템플릿 강제)
# =====================================================
def generate_description(breed, animal, size, coat_type, environment, yard, detailed_analysis):
    prompt = f"""### 지시:
제공된 품종 정보와 수치 기반의 데이터 매칭 리포트를 근거로, 실제 동물병원 수의사 혹은 반려동물 행동전문가 관점의 임상학적 추천 소견을 상세하게 확장하여 지정된 JSON 포맷으로 응답하세요.
JSON 블록 외의 어떠한 설명, 인사말, 결론 문장도 절대로 포함해서는 안 됩니다. 모든 답변 문장은 자연스럽고 품격 있는 한국어로 작성하세요.

### 입력 데이터:
추천 품종: {breed} ({animal})
외형 정보: {coat_type} / {size}
거주 환경: {environment} (마당 여부: {yard})
[수치 데이터 기반 정밀 매칭 분석]:
- {detailed_analysis}

### 응답 포맷 (반드시 아래의 키 구조를 100% 엄수할 것):
{{
  "reason": "위의 데이터 매칭 분석 지표를 바탕으로, 이 품종의 기질과 보호자의 심리 매트릭스가 행동학적으로 왜 최고의 시너지를 내는지 의학적/상담학적으로 자연스럽게 풀어낸 심층 분석 줄글",
  "warning": "해당 품종이 태생적으로 조심해야 할 주요 유전질환 및 행동학적 케어 위험 요소",
  "environment_fit": "주거지 내부 구조 및 이웃 관계를 고려한 환경 적합성 맞춤 소견",
  "guide": "보호자의 성향 발달과 조화로운 동행을 위한 전문가 행동 처방 가이드"
}}
"""
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=550,
            temperature=0.1,
            top_p=0.8,
            do_sample=False,
            repetition_penalty=1.1,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated = tokenizer.decode(output[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True).strip()
    torch.cuda.empty_cache()

    match = re.search(r"\{.*\}", generated, re.DOTALL)
    
    # 🌟 예외 처리(Fallback) 문구도 완전히 한글화 완료
    default_fallback = {
        "reason": f"사용자의 성향 데이터 세트와 {breed}의 고유 기질 지표가 일치하여 추천되었습니다.",
        "warning": "정기적인 예방접종 및 건강 관리가 필요합니다.",
        "environment_fit": "환경에 무리 없이 적응할 수 있습니다.",
        "guide": "초기 사회화 훈련을 권장합니다."
    }

    if not match: return default_fallback
    try: return json.loads(match.group())
    except: return default_fallback

# =====================================================
# 7. HIGH CONCURRENCY ASYNC API ENDPOINT
# =====================================================
@app.post("/recommend_bigfive")
async def api(data: BigFiveInput):
    try:
        user = {"O": data.O, "C": data.C, "E": data.E, "A": data.A, "N": data.N, "environment": data.environment, "yard": data.yard}

        loop = asyncio.get_running_loop()
        row = await loop.run_in_executor(executor, recommend, user, data.exclude)

        breed = safe(row.get("품종"), "말티즈")
        animal = "강아지"
        
        # 크기 및 털길이 맵핑 데이터 로드 (미보유 시 기본값 세팅)
        breed_size_info = size_map.get(breed, {"크기": "중형견"})
        size = breed_size_info.get("크기", "중형견")
        coat_type = coat_map.get(breed, "단모종")
        score = round(float(row.get("score", 0)) * 10, 2)

        # 100% 팩트 기반 데이터 분석 리포트 자동 조립
        detailed_analysis = compile_detailed_reason(user, row)

        # 데이터 팩트를 LLM에 이식하여 고품질 소견 JSON 추출
        llm = await loop.run_in_executor(
            executor, generate_description, 
            breed, animal, size, coat_type, data.environment, data.yard, detailed_analysis
        )

        # 변수값 매핑 및 포맷 결합
        reason = safe(llm.get("reason"), "사용자와 성향 매칭도가 매우 준수한 품종입니다.")
        
        csv_warning = safe(row.get("유전병"))
        llm_warning = safe(llm.get("warning"))
        warning = f"{llm_warning} (요주의 질환군: {csv_warning})" if csv_warning else llm_warning
        
        environment_fit = safe(llm.get("environment_fit"), f"{data.environment} 환경에서 생활 가능합니다.")
        
        # 외형 정보 스트링 빌드 완료
        weight_min = breed_size_info.get("weight_min")
        weight_max = breed_size_info.get("weight_max")
        height_min = breed_size_info.get("height_min")
        height_max = breed_size_info.get("height_max")

        weight_text = (
            f"{weight_min:.1f}~{weight_max:.1f}kg"
            if weight_min is not None and weight_max is not None
            else "정보 없음"
        )

        height_text = (
            f"{height_min}~{height_max}cm"
            if height_min is not None and height_max is not None
            else "정보 없음"
        )

        size_text = (
            f"{coat_type} / {size} "
            f"(체중: {weight_text}, 체고: {height_text})"
        )
        
        csv_guide = safe(row.get("초보자가이드"))
        llm_guide = safe(llm.get("guide"))
        guide = f"{llm_guide} [양육 수칙: {csv_guide}]" if csv_guide else llm_guide

        needs_yard = (size == "대형견" and row.get("마당필요도", 0) >= 0.6)
        if data.yard == "있음":
            yard_text = "야외 마당 공간을 유기적으로 활용 시 본 품종의 스트레스 해소와 활동량 충족에 매우 이상적인 인프라가 됩니다." if needs_yard else "마당 인프라를 통해 일상적인 에너지 발산 관리에 큰 도움을 줍니다."
        else:
            yard_text = "대형견 고유의 스펙상 정기적이고 강도 높은 야외 산책 세션을 통해 실외 활동량을 상쇄시켜 주는 것이 필수적입니다." if needs_yard else "실내 생활 중심의 패턴이므로 일일 규칙적인 산책 스케줄을 유지해 주시는 편이 좋습니다."

        # 🌟 9개 항목 전용 고정 출력 레이아웃 (순수 한국어 100% 일치)
        full_text = f"""
1. 추천 동물 종류: {animal}

2. 추천 품종: {breed}

3. 빅파이브 점수 대조 정밀 매칭 분석 보고서:
- {detailed_analysis}

4. 수의 행동학 전문가 종합 소견: {reason}

5. 주의해야 할 유전적 질환 일람: {warning}

6. 주거 환경 매칭 피드백: {environment_fit}

7. 외형 특성 (털 길이 및 크기): {size_text}

8. 마당 활용 및 산책 조언: {yard_text}

9. 초보 보호자 핵심 양육 가이드: {guide}
""".strip()

        return {
            "status": "success", "animal": animal, "breed": breed, "score": score,
            "full_text": full_text, "reason": reason, "detailed_analysis": detailed_analysis,
            "warning": warning, "environment_fit": environment_fit, "size_text": size_text, "guide": guide
        }

    except Exception as e:
        print("❌ API 오류 로그:", str(e))
        return {"status": "error", "message": str(e)}

# =====================================================
# 8. RUN SERVER
# =====================================================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)