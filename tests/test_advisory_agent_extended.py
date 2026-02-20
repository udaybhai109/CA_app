import json

import pytest

import app.advisory_agent as advisory_agent_module


class DummyFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class DummyToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.function = DummyFunction(name, arguments)


class DummyMessage:
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class DummyChoice:
    def __init__(self, message):
        self.message = message


class DummyResponse:
    def __init__(self, message):
        self.choices = [DummyChoice(message)]


class SinglePassCompletions:
    def __init__(self):
        self.captured_messages = None

    def create(self, **kwargs):
        self.captured_messages = kwargs["messages"]
        return DummyResponse(DummyMessage(content="Deterministic advisory response."))


class FakeOpenAI:
    def __init__(self, api_key):
        self.chat = type(
            "FakeChat",
            (),
            {"completions": SinglePassCompletions()},
        )()


def test_format_assistant_tool_calls():
    tool_calls = [
        DummyToolCall("call_1", "pnl", "{}"),
        DummyToolCall("call_2", "gst_summary", '{"year_month":"2025-06"}'),
    ]

    formatted = advisory_agent_module._format_assistant_tool_calls(tool_calls)
    assert formatted == [
        {"id": "call_1", "type": "function", "function": {"name": "pnl", "arguments": "{}"}},
        {
            "id": "call_2",
            "type": "function",
            "function": {"name": "gst_summary", "arguments": '{"year_month":"2025-06"}'},
        },
    ]


def test_generate_advice_requires_openai_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY is not set."):
        advisory_agent_module.generate_advice(object(), 1, "What is my cash runway?")


def test_generate_advice_injects_rag_regulation_context(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(advisory_agent_module, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(
        advisory_agent_module,
        "query_tax_law",
        lambda question: [
            "Section 194J: TDS at 10% on professional services exceeding 30000 INR."
        ],
    )

    captured = {}

    class CapturingCompletions:
        def create(self, **kwargs):
            captured["messages"] = kwargs["messages"]
            return DummyResponse(DummyMessage(content="Advisory output"))

    class CapturingOpenAI:
        def __init__(self, api_key):
            self.chat = type(
                "FakeChat",
                (),
                {"completions": CapturingCompletions()},
            )()

    monkeypatch.setattr(advisory_agent_module, "OpenAI", CapturingOpenAI)

    response = advisory_agent_module.generate_advice(object(), 1, "What is TDS?")
    assert response == "Advisory output"
    assert captured["messages"][0]["role"] == "system"
    assert "Relevant regulatory references" in captured["messages"][0]["content"]
    assert "Section 194J" in captured["messages"][0]["content"]


def test_generate_advice_executes_requested_tool(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(advisory_agent_module, "query_tax_law", lambda _: [])

    class TwoStepCompletions:
        def __init__(self):
            self.call_count = 0

        def create(self, **kwargs):
            self.call_count += 1
            if self.call_count == 1:
                return DummyResponse(
                    DummyMessage(
                        tool_calls=[DummyToolCall("tc1", "pnl", json.dumps({}))],
                    )
                )
            tool_messages = [m for m in kwargs["messages"] if m["role"] == "tool"]
            assert json.loads(tool_messages[-1]["content"]) == {"net_profit": 30000.0}
            return DummyResponse(DummyMessage(content="Net profit is 30000.0"))

    class TwoStepOpenAI:
        def __init__(self, api_key):
            self.chat = type("FakeChat", (), {"completions": TwoStepCompletions()})()

    monkeypatch.setattr(advisory_agent_module, "OpenAI", TwoStepOpenAI)
    monkeypatch.setattr(
        advisory_agent_module,
        "run_tool",
        lambda session, user_id, tool_name, params: {"net_profit": 30000.0},
    )

    result = advisory_agent_module.generate_advice(object(), 99, "What is my net profit?")
    assert "30000" in result
