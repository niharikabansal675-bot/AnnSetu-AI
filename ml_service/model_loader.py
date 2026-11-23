import json
import os
from functools import lru_cache


@lru_cache(maxsize=1)
def load_model():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    base_id = os.getenv("ANNSETU_BASE_MODEL", "Qwen/Qwen3-0.6B")
    adapter = os.getenv("ANNSETU_ADAPTER_PATH", "")
    if not adapter or not os.path.isfile(os.path.join(adapter, "adapter_config.json")):
        raise RuntimeError("ANNSETU_ADAPTER_PATH must point to the extracted LoRA adapter")
    if not torch.cuda.is_available():
        raise RuntimeError("GPU inference requested, but CUDA is unavailable")

    tokenizer = AutoTokenizer.from_pretrained(base_id)
    base = AutoModelForCausalLM.from_pretrained(
        base_id, dtype=torch.float16, device_map="auto"
    )
    model = PeftModel.from_pretrained(base, adapter)
    model.eval()
    return tokenizer, model


def generate_json(facts: dict) -> dict:
    import torch
    tokenizer, model = load_model()
    messages = [
        {"role": "system", "content": (
            "You explain VERIFIED backend decisions for AnnSetu-AI. Do not decide again. "
            "Return ONLY JSON with keys action, selected_ngo, explanation. "
            "Copy action and selected_ngo exactly. No invented names, numbers, "
            "offer-execution claims, or new safety assertions. Keep explanation short."
        )},
        {"role": "user", "content": json.dumps(facts, ensure_ascii=False)},
    ]
    inputs = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True,
        enable_thinking=False, return_dict=True, return_tensors="pt"
    ).to(model.device)
    with torch.inference_mode():
        tokens = model.generate(
            **inputs, do_sample=False, max_new_tokens=130,
            pad_token_id=tokenizer.eos_token_id
        )
    response_text = tokenizer.decode(
        tokens[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True
    ).strip()
    parsed = json.loads(response_text)
    if not isinstance(parsed, dict):
        raise ValueError("Model output was not a JSON object")
    return parsed
