"""The original chat templates, rendered exactly as transformers would, plus the raw-prompt
path of the Ollama adapter. No network."""

import json

import httpx
import pytest

from flembench.adapters.ollama_adapter import ContextOverflow, OllamaAdapter, render_chat
from flembench.registry import load_registry

T = "config/chat_templates/"


def test_eurollm_template():
    assert render_chat(T + "eurollm-9b.jinja", "SYS", "USER") == (
        "<|im_start|>system\nSYS<|im_end|>\n<|im_start|>user\nUSER<|im_end|>\n<|im_start|>assistant\n"
    )


def test_geitje_template():
    assert render_chat(T + "geitje-7b-ultra.jinja", "SYS", "USER", eos_token="</s>") == (
        "<|system|>\nSYS</s>\n<|user|>\nUSER</s>\n<|assistant|>\n"
    )


def test_chocollama_template_bos_only_when_given():
    out = render_chat(T + "chocollama-8b.jinja", "SYS", "USER", bos_token="")
    assert out == (
        "<|start_header_id|>system<|end_header_id|>\n\nSYS<|eot_id|>"
        "<|start_header_id|>user<|end_header_id|>\n\nUSER<|eot_id|>"
        "<|start_header_id|>assistant<|end_header_id|>\n\n"
    )
    assert render_chat(T + "chocollama-8b.jinja", "S", "U", bos_token="<B>").startswith("<B>")


def test_registry_hashes_templates_into_params():
    reg = load_registry()
    for key in ("eurollm-9b", "geitje-7b-ultra", "chocollama-8b"):
        assert len(reg[key].params["chat_template_sha256"]) == 64
    assert "chat_template" not in reg["gemma4-12b"].params


def _adapter(handler):
    return OllamaAdapter(
        client=httpx.Client(transport=httpx.MockTransport(handler)), host="http://x"
    )


def _tags(request):
    return httpx.Response(200, json={"models": [{"name": "m", "digest": "d1"}]})


def test_raw_generate_with_original_template():
    seen = {}

    def handler(request):
        if request.url.path == "/api/tags":
            return _tags(request)
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"response": "B", "prompt_eval_count": 50, "eval_count": 1})

    params = {
        "temperature": 0,
        "num_ctx": 4096,
        "chat_template": T + "geitje-7b-ultra.jinja",
        "chat_template_sha256": "x",
        "bos_token": "",
        "eos_token": "</s>",
    }
    c = _adapter(handler).complete("m", "SYS", "USER", 64, params)
    body = seen["body"]
    assert seen["path"] == "/api/generate" and body["raw"] is True
    assert body["prompt"].startswith("<|system|>\nSYS</s>")
    assert body["options"] == {
        "temperature": 0,
        "num_ctx": 4096,
        "num_predict": 64,
        "stop": ["</s>"],
    }
    assert c.text == "B" and c.model_reported == "m@d1"


def test_think_is_top_level_and_chat_endpoint_used():
    seen = {}

    def handler(request):
        if request.url.path == "/api/tags":
            return _tags(request)
        seen["path"], seen["body"] = request.url.path, json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": "A"}, "prompt_eval_count": 10})

    _adapter(handler).complete("m", "S", "U", 64, {"temperature": 0, "think": False})
    assert seen["path"] == "/api/chat"
    assert seen["body"]["think"] is False and "think" not in seen["body"]["options"]


def test_context_overflow_raises():
    def handler(request):
        if request.url.path == "/api/tags":
            return _tags(request)
        return httpx.Response(200, json={"message": {"content": "A"}, "prompt_eval_count": 4090})

    with pytest.raises(ContextOverflow):
        _adapter(handler).complete("m", "S", "U", 64, {"num_ctx": 4096})
