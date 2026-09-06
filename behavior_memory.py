"""Analyze one observed pet behavior and prepare an owner-confirmed memory."""

from __future__ import annotations

import base64
import io
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Literal, Optional, Tuple

from openai import OpenAI
from PIL import Image
from pydantic import BaseModel, ConfigDict, field_validator


Confidence = Literal["low", "medium", "high"]


class BehaviorAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed_behavior: str
    general_meaning: str
    context_interpretation: str
    pet_specific_pattern: str
    confidence: Confidence

    @field_validator(
        "observed_behavior",
        "general_meaning",
        "context_interpretation",
        "pet_specific_pattern",
    )
    @classmethod
    def text_must_not_be_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("behavior analysis fields cannot be empty")
        return value


OBSERVER_PROMPT = """
你是一名宠物行为观察助手，不是猫语翻译器、兽医或心理诊断工具。

请严格区分：
A. 图片中可观察到的行为。
B. 通用猫行为学上的可能解释。
C. 结合主人文字后，对这只具体宠物形成的个体观察。

表达必须克制，使用“可能”“通常”“结合情境”“从当前观察来看”。
禁止断言猫在想什么，禁止健康诊断，禁止把 grooming 固定解释成生气或焦虑。
observed_behavior 优先使用正式动作 enum：come_closer、knead、curl_up、grooming；无法归类时使用 other。
除 observed_behavior 外，其余字段都是用户会直接看到的中文：
- 不出现英文 enum、变量名、中英文夹杂或“模型、系统、优先级、权重”等工程表达。
- general_meaning 用自然中文说明这个动作在一般情况下可能意味着什么，并提醒要结合当时的情境。
- context_interpretation 用第二人称自然复述当时发生的事，不断言猫的具体心理。
- pet_specific_pattern 使用宠物名字，说明一次观察不一定代表稳定习惯；如果类似情况经常出现，记录才会慢慢变得有意义。
- 每个字段保持一至两句，温暖、自然、克制，不像分析报告。
只能返回给定 Schema。
""".strip()


def prepare_vision_image(image_bytes: bytes) -> str:
    """Resize a session image for a fast, bounded Vision request."""
    with Image.open(io.BytesIO(image_bytes)) as image:
        image = image.convert("RGB")
        image.thumbnail((1024, 1024))
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=82, optimize=True)
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def local_behavior_analysis(context: str, pet_name: str) -> BehaviorAnalysis:
    """Text-only fallback that keeps the behavior-memory demo usable offline."""
    normalized = context.replace(" ", "")
    display_context = context.strip().rstrip("。！？!?")
    if any(word in normalized for word in ("舔毛", "理毛", "梳理", "舔自己")):
        behavior = "grooming"
        general = "猫咪有时会通过理毛来清洁和整理自己，也可能只是想让状态慢下来。具体代表什么，要结合当时的情境一起看。"
        pattern = f"一次观察不一定说明什么。如果类似情况经常出现，它就可能慢慢成为{pet_name}自己的一个小习惯。"
    elif "踩奶" in normalized:
        behavior = "knead"
        general = "踩奶是猫咪常见的节律性动作，有时和舒适、放松或熟悉的体验有关。具体代表什么，要结合当时的情境一起看。"
        pattern = f"如果类似情况经常出现，它就可能慢慢成为{pet_name}自己的一个小习惯。"
    elif any(word in normalized for word in ("靠近", "蹭", "挨着")):
        behavior = "come_closer"
        general = "猫咪主动靠近，有时是在寻找熟悉的接触，也可能只是在选择一个舒服的距离。具体代表什么，要结合当时的情境一起看。"
        pattern = f"这只是关于{pet_name}的一次观察。如果类似情况经常出现，它才可能慢慢成为一个属于它的小习惯。"
    elif any(word in normalized for word in ("趴", "窝", "睡")):
        behavior = "curl_up"
        general = "猫咪在附近窝下来，有时只是想休息，也可能是在保持一个让自己舒服的距离。具体代表什么，要结合当时的情境一起看。"
        pattern = f"如果类似情况经常出现，我们就能慢慢看见{pet_name}更习惯怎样待在你身边。"
    else:
        behavior = "other"
        general = "猫咪持续留意一个方向，有时是在关注周围的变化，也可能只是在安静观察。单独一个动作很难说明它具体在想什么。"
        pattern = f"一次观察不一定说明什么。如果这样的情况经常发生，它就可能慢慢成为{pet_name}自己的一个小习惯。"

    return BehaviorAnalysis(
        observed_behavior=behavior,
        general_meaning=general,
        context_interpretation=(
            f"结合你写下的情境——{display_context}——它可能只是在留意当时发生的变化。"
            "单独这一次，还不能说明它具体在想什么。"
        ),
        pet_specific_pattern=pattern,
        confidence="medium" if behavior != "other" else "low",
    )


def demo_grooming_analysis(pet_name: str) -> BehaviorAnalysis:
    return BehaviorAnalysis(
        observed_behavior="grooming",
        general_meaning="猫咪有时会通过理毛来清洁和整理自己，也可能只是想让状态慢下来。具体代表什么，要结合当时的情境一起看。",
        context_interpretation=f"你和{pet_name}互动之后，它开始认真整理自己的毛。单独这一次，还不能说明它具体在想什么。",
        pet_specific_pattern=f"你曾经留意到，{pet_name}在被撸之后经常开始认真舔毛。如果类似情况持续出现，它就可能是{pet_name}自己的一个小习惯。",
        confidence="medium",
    )


def build_memory_entry(context: str, analysis: BehaviorAnalysis) -> dict:
    return {
        "context": context.strip(),
        "observed_behavior": analysis.observed_behavior,
        "general_meaning": analysis.general_meaning,
        "pet_specific_pattern": analysis.pet_specific_pattern,
        "confidence": analysis.confidence,
    }


def _request_vision(
    image_bytes: bytes,
    context: str,
    pet_name: str,
) -> BehaviorAnalysis:
    client = OpenAI(timeout=6.5, max_retries=0)
    response = client.responses.parse(
        model=os.getenv("OPENAI_VISION_MODEL", os.getenv("OPENAI_MODEL", "gpt-5.4-mini")),
        instructions=OBSERVER_PROMPT,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"宠物名字：{pet_name}\n主人提供的情境：{context}",
                    },
                    {
                        "type": "input_image",
                        "image_url": prepare_vision_image(image_bytes),
                        "detail": "low",
                    },
                ],
            }
        ],
        text_format=BehaviorAnalysis,
        max_output_tokens=600,
        store=False,
        timeout=6.5,
    )
    if response.output_parsed is None:
        raise ValueError("OpenAI returned no parsed behavior analysis")
    return response.output_parsed


def analyze_behavior(
    image_bytes: bytes,
    context: str,
    pet_name: str,
    timeout_seconds: float = 7.0,
) -> Tuple[Optional[BehaviorAnalysis], str]:
    """Use Vision first and degrade to a conservative text interpretation."""
    fallback = local_behavior_analysis(context, pet_name)
    if not os.getenv("OPENAI_API_KEY"):
        return fallback, "fallback:text:no_api_key"

    try:
        prepare_vision_image(image_bytes)
    except Exception:
        return None, "failed:invalid_image"

    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pet-observer")
    future = executor.submit(_request_vision, image_bytes, context, pet_name)
    try:
        return future.result(timeout=timeout_seconds), "openai:vision"
    except FutureTimeoutError:
        future.cancel()
        return fallback, "fallback:text:timeout"
    except Exception as exc:
        return fallback, f"fallback:text:{type(exc).__name__}"
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
