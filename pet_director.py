"""Pet behavior selection via OpenAI, with owner-data-first local fallback."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Dict, List, Literal, Optional, Tuple

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, field_validator


Emotion = Literal[
    "sad", "lonely", "anxious", "tired", "frustrated", "happy", "neutral"
]
Action = Literal["come_closer", "knead", "curl_up", "grooming"]
Sound = Literal["purr", "soft_meow", "none"]


class CompanionExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    behavior_science: str
    about_my_pet: str


class CompanionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    emotion: Emotion
    action: Action
    sound: Sound
    caption: str
    explanation: CompanionExplanation

    @field_validator("caption")
    @classmethod
    def caption_must_be_short(cls, value: str) -> str:
        value = value.strip()
        if len(value) > 22:
            raise ValueError("caption must contain at most 22 characters")
        return value


DIRECTOR_PROMPT = """
你是一名宠物行为导演，而不是聊天助手、猫语翻译器、兽医或心理咨询师。

任务：根据用户当前表达与猫咪个体资料，选择此刻最自然的行为。

决策优先级必须严格遵守：
1. 主人明确设置的 emotion_response_profile。
2. pet_behavior_memory 中与当前情绪或情境相关的真实个体记录。
3. traits 和 usual_companion_behavior。
4. 通用猫行为学合理性。

规则：
- 只能选择 come_closer、knead、curl_up、grooming。
- 行为是回应主体；caption 只是辅助，可以为空，最多 22 个汉字。
- 不建议、不说教、不诊断、不输出步骤，不假装猫理解工作等复杂概念。
- explanation.behavior_science 只说明一般猫行为学上的可能意义，必须使用“可能、通常、结合情境”等克制表达。
- explanation.about_my_pet 必须说明本次具体参考了哪些主人 Profile 或 Behavioral Memory；没有参考时也要如实说明。
- explanation 的两个字段都是用户会直接看到的中文，不得出现任何英文 enum、变量名或“系统参考、优先级、权重、模型选择”等工程表达。
- about_my_pet 最多两个短段落，总长度约 60 至 120 个中文字。自然表达“你之前告诉我……”与“你曾经记录过……”，不罗列标签。
- 尽量避免 previous_action，但主人明确设置的 Profile 优先级更高。
- 只能返回给定 Schema。
""".strip()


USUAL_ACTION = {
    "靠着我": "come_closer",
    "趴在我附近": "curl_up",
    "给我踩奶": "knead",
    "主动蹭我": "come_closer",
    "看我一眼然后走开": "curl_up",
}

ACTION_LABEL = {
    "come_closer": "靠近你",
    "knead": "轻轻踩奶",
    "curl_up": "在附近窝下来",
    "grooming": "开始整理自己",
}

BEHAVIOR_SCIENCE = {
    "come_closer": "猫咪主动靠近，有时是在寻找熟悉的接触或陪伴距离。具体代表什么，要结合当时的情境一起看。",
    "knead": "踩奶是猫咪常见的节律性动作，有时和舒适、放松或熟悉的体验有关。具体代表什么，要结合当时的情境一起看。",
    "curl_up": "猫咪在附近窝下来，有时只是想休息，也可能是在保持一个让自己舒服的距离。具体代表什么，要结合当时的情境一起看。",
    "grooming": "猫咪在紧张、环境变化，或者只是想让自己慢下来时，都可能会通过理毛来整理自己。具体代表什么，要结合当时的情境一起看。",
}

EMOTION_PROFILE_KEY = {
    "happy": "happy",
    "sad": "sad",
    "lonely": "sad",
    "anxious": "anxious",
    "frustrated": "anxious",
    "tired": "tired",
}

EMOTION_COPY = {
    "happy": "开心",
    "sad": "难过",
    "lonely": "孤独",
    "anxious": "焦虑或烦躁",
    "frustrated": "烦躁",
    "tired": "疲惫或低落",
    "neutral": "平静",
}


def _contains_any(text: str, words: List[str]) -> bool:
    normalized = text.lower().replace(" ", "")
    return any(word.lower() in normalized for word in words)


def detect_emotion(user_text: str) -> Emotion:
    if _contains_any(user_text, ["累", "困", "撑不住", "疲惫", "没力气", "低落"]):
        return "tired"
    if _contains_any(user_text, ["孤独", "孤单", "一个人", "没人陪"]):
        return "lonely"
    if _contains_any(user_text, ["难过", "伤心", "想哭", "哭了"]):
        return "sad"
    if _contains_any(user_text, ["紧张", "焦虑", "害怕", "担心", "不安"]):
        return "anxious"
    if _contains_any(user_text, ["生气", "烦", "崩溃", "火大", "受够了"]):
        return "frustrated"
    if _contains_any(user_text, ["开心", "成功", "做完了", "完成了", "太好了"]):
        return "happy"
    return "neutral"


def relevant_behavior_memories(
    user_text: str,
    emotion: Emotion,
    memories: Optional[List[dict]],
) -> List[dict]:
    if not memories:
        return []
    normalized = user_text.replace(" ", "")
    results: List[Tuple[int, dict]] = []
    for memory in memories:
        score = 0
        joined = " ".join(
            str(memory.get(key, ""))
            for key in ("context", "observed_behavior", "pet_specific_pattern")
        )
        for token in ["摸", "撸", "安静", "累", "焦虑", "开心", "难过", "舔毛", "踩奶", "靠近"]:
            if token in normalized and token in joined:
                score += 2
        action = memory.get("observed_behavior")
        if emotion == "tired" and action in {"grooming", "curl_up"}:
            score += 1
        if emotion in {"sad", "lonely", "anxious"} and action in {"come_closer", "knead"}:
            score += 1
        if score:
            results.append((score, memory))
    results.sort(key=lambda item: item[0], reverse=True)
    return [memory for _, memory in results[:3]]


def _caption(emotion: Emotion, action: Action) -> str:
    captions = {
        "come_closer": "它决定离你近一点。",
        "knead": "它轻轻踩了几下。",
        "curl_up": "它在你身边慢慢窝下。",
        "grooming": "它听完，开始整理自己。",
    }
    if emotion == "happy" and action == "come_closer":
        return "它好像也被你感染了。"
    return captions[action]


def _response(
    emotion: Emotion,
    action: Action,
    pet_name: str,
    source: str,
    relevant_memories: Optional[List[dict]] = None,
) -> CompanionResponse:
    sound: Sound = "purr" if action in {"come_closer", "knead", "curl_up"} else "none"
    if emotion == "happy" and action == "come_closer":
        sound = "soft_meow"

    details: List[str] = []
    profile_key = EMOTION_PROFILE_KEY.get(emotion)
    if source == "profile" and profile_key:
        details.append(
            f"你之前告诉我，当你{EMOTION_COPY[emotion]}的时候，{pet_name}常常会{ACTION_LABEL[action]}。"
        )
    elif source == "traits":
        details.append(f"{pet_name}平时更习惯用这样的方式待在你身边。")
    elif source == "memory":
        details.append(f"你曾经记录过，{pet_name}在相似的时刻也会有这样的表现。")
    else:
        details.append(f"关于{pet_name}，现在还没有足够多相似的观察。随着记录变多，它自己的小习惯会慢慢清晰起来。")

    for memory in relevant_memories or []:
        if memory.get("observed_behavior") == action and memory.get("pet_specific_pattern"):
            details.append(str(memory["pet_specific_pattern"]))
            break

    return CompanionResponse(
        emotion=emotion,
        action=action,
        sound=sound,
        caption=_caption(emotion, action),
        explanation=CompanionExplanation(
            behavior_science=BEHAVIOR_SCIENCE[action],
            about_my_pet=" ".join(details),
        ),
    )


def local_fallback(
    user_text: str,
    traits: List[str],
    usual_companion_behavior: str,
    previous_action: Optional[str] = None,
    emotion_response_profile: Optional[Dict[str, str]] = None,
    pet_behavior_memory: Optional[List[dict]] = None,
    pet_name: str = "这只猫",
) -> CompanionResponse:
    """Choose a stable response with owner-provided data before generic rules."""
    emotion = detect_emotion(user_text)
    profile_key = EMOTION_PROFILE_KEY.get(emotion)
    profile_action = (emotion_response_profile or {}).get(profile_key or "")
    valid_actions = {"come_closer", "knead", "curl_up", "grooming"}
    relevant = relevant_behavior_memories(user_text, emotion, pet_behavior_memory)

    if profile_action in valid_actions:
        return _response(emotion, profile_action, pet_name, "profile", relevant)  # type: ignore[arg-type]

    for memory in relevant:
        memory_action = memory.get("observed_behavior")
        if memory_action in valid_actions:
            return _response(emotion, memory_action, pet_name, "memory", relevant)  # type: ignore[arg-type]

    trait_set = set(traits)
    if emotion == "tired":
        action: Action = "knead" if "爱踩奶" in trait_set else "curl_up"
    elif emotion in {"sad", "lonely"}:
        action = "come_closer"
    elif emotion == "anxious":
        action = "come_closer" if {"黏人", "爱撒娇"} & trait_set else "curl_up"
    elif emotion == "frustrated":
        action = "grooming" if "高冷" in trait_set else "curl_up"
    elif emotion == "happy":
        action = "come_closer"
    else:
        action = USUAL_ACTION.get(usual_companion_behavior, "curl_up")  # type: ignore[assignment]
        if action == previous_action:
            alternatives: Dict[str, Action] = {
                "come_closer": "knead" if "爱踩奶" in trait_set else "curl_up",
                "knead": "come_closer",
                "curl_up": "grooming" if "高冷" in trait_set else "come_closer",
                "grooming": "curl_up",
            }
            action = alternatives[action]
    return _response(emotion, action, pet_name, "traits", relevant)


def _request_openai(
    user_text: str,
    detected_emotion: Emotion,
    pet_name: str,
    traits: List[str],
    usual_companion_behavior: str,
    previous_action: Optional[str],
    emotion_response_profile: Optional[Dict[str, str]],
    relevant_memories: List[dict],
) -> CompanionResponse:
    client = OpenAI(timeout=4.4, max_retries=0)
    payload = {
        "user_text": user_text,
        "detected_emotion": detected_emotion,
        "pet_name": pet_name,
        "traits": traits,
        "usual_companion_behavior": usual_companion_behavior,
        "emotion_response_profile": emotion_response_profile or {},
        "relevant_pet_behavior_memory": relevant_memories,
        "previous_action": previous_action,
    }
    response = client.responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
        instructions=DIRECTOR_PROMPT,
        input=json.dumps(payload, ensure_ascii=False),
        text_format=CompanionResponse,
        max_output_tokens=500,
        store=False,
        timeout=4.4,
    )
    if response.output_parsed is None:
        raise ValueError("OpenAI returned no parsed response")
    return response.output_parsed


def get_companion_response(
    user_text: str,
    pet_name: str,
    traits: List[str],
    usual_companion_behavior: str,
    previous_action: Optional[str] = None,
    timeout_seconds: float = 5.0,
    emotion_response_profile: Optional[Dict[str, str]] = None,
    pet_behavior_memory: Optional[List[dict]] = None,
) -> Tuple[CompanionResponse, str]:
    """Return an AI response or a deterministic owner-data-first fallback."""
    fallback = local_fallback(
        user_text,
        traits,
        usual_companion_behavior,
        previous_action,
        emotion_response_profile,
        pet_behavior_memory,
        pet_name,
    )
    if not os.getenv("OPENAI_API_KEY"):
        return fallback, "fallback:no_api_key"

    emotion = detect_emotion(user_text)
    relevant = relevant_behavior_memories(user_text, emotion, pet_behavior_memory)
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pet-director")
    future = executor.submit(
        _request_openai,
        user_text,
        emotion,
        pet_name,
        traits,
        usual_companion_behavior,
        previous_action,
        emotion_response_profile,
        relevant,
    )
    try:
        result = future.result(timeout=timeout_seconds)
        profile_key = EMOTION_PROFILE_KEY.get(emotion)
        profile_action = (emotion_response_profile or {}).get(profile_key or "")
        if profile_action and result.action != profile_action:
            return fallback, "openai:profile_enforced"
        return result, "openai"
    except FutureTimeoutError:
        future.cancel()
        return fallback, "fallback:timeout"
    except Exception as exc:
        return fallback, f"fallback:{type(exc).__name__}"
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
