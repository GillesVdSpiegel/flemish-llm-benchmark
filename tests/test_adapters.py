"""Adapters against recorded response shapes. No network."""

import json
from types import SimpleNamespace as NS

import httpx

from flembench.adapters.anthropic_adapter import AnthropicAdapter
from flembench.adapters.gemini_adapter import GeminiAdapter
from flembench.adapters.ollama_adapter import OllamaAdapter
from flembench.adapters.openai_adapter import OpenAIAdapter


class Recorder:
    def __init__(self, response):
        self.response, self.calls = response, []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def test_anthropic_adapter():
    resp = NS(
        id="msg_1",
        model="claude-sonnet-5",
        stop_reason="end_turn",
        content=[NS(type="text", text="B")],
        usage=NS(input_tokens=120, output_tokens=2),
    )
    rec = Recorder(resp)
    c = AnthropicAdapter(client=NS(messages=NS(create=rec))).complete(
        "claude-sonnet-5", "sys", "user", 1024, {"thinking": {"type": "disabled"}}
    )
    assert (c.text, c.input_tokens, c.output_tokens, c.model_reported) == (
        "B",
        120,
        2,
        "claude-sonnet-5",
    )
    call = rec.calls[0]
    assert call["thinking"] == {"type": "disabled"} and "temperature" not in call
    assert call["messages"] == [{"role": "user", "content": "user"}]


def test_openai_adapter_reports_reasoning_tokens():
    resp = NS(
        id="resp_1",
        model="gpt-5.6-terra",
        status="completed",
        output_text="C",
        usage=NS(input_tokens=100, output_tokens=40, output_tokens_details=NS(reasoning_tokens=35)),
    )
    rec = Recorder(resp)
    c = OpenAIAdapter(client=NS(responses=NS(create=rec))).complete(
        "gpt-5.6-terra", "sys", "user", 1024, {"reasoning": {"effort": "none"}}
    )
    assert c.reasoning_tokens == 35 and c.output_tokens == 40
    assert rec.calls[0]["store"] is False and rec.calls[0]["instructions"] == "sys"


def test_gemini_adapter_counts_thoughts_as_output():
    resp = NS(
        text="A",
        model_version="gemini-3.8-flash-001",
        response_id="r1",
        candidates=[NS(finish_reason="STOP")],
        usage_metadata=NS(prompt_token_count=90, candidates_token_count=1, thoughts_token_count=12),
    )
    rec = Recorder(resp)
    c = GeminiAdapter(client=NS(models=NS(generate_content=rec))).complete(
        "gemini-3.8-flash", "sys", "user", 1024, {"temperature": 0, "thinking_level": "LOW"}
    )
    assert (c.output_tokens, c.reasoning_tokens) == (13, 12)
    cfg = rec.calls[0]["config"]
    assert cfg.temperature == 0 and cfg.thinking_config.thinking_level.value == "LOW"


def test_ollama_adapter_records_digest():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "m:q8", "digest": "abc123"}]})
        body = json.loads(request.content)
        assert body["options"] == {"temperature": 0, "seed": 0, "num_predict": 512}
        return httpx.Response(
            200,
            json={
                "message": {"content": "D"},
                "prompt_eval_count": 80,
                "eval_count": 1,
                "done_reason": "stop",
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    c = OllamaAdapter(client=client, host="http://x").complete(
        "m:q8", "sys", "user", 512, {"temperature": 0, "seed": 0}
    )
    assert c.text == "D" and c.model_reported == "m:q8@abc123"
