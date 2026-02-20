import json
import os

from openai import OpenAI

from .rag_engine import query_tax_law
from .tool_registry import run_tool

SYSTEM_PROMPT = (
    "You are a financial advisor for Indian small businesses. "
    "Do not calculate tax. Only explain financial situation clearly. "
    "Use tools to fetch financial numbers before answering."
)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "pnl",
            "description": "Get profit and loss",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "balance_sheet",
            "description": "Get balance sheet",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gst_summary",
            "description": "Get GST summary for YYYY-MM",
            "parameters": {
                "type": "object",
                "properties": {"year_month": {"type": "string"}},
                "required": ["year_month"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tds_summary",
            "description": "Get TDS summary for YYYY-MM",
            "parameters": {
                "type": "object",
                "properties": {"year_month": {"type": "string"}},
                "required": ["year_month"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "financial_health",
            "description": "Get financial ratios",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "aging",
            "description": "Get AR/AP aging",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
]


def _format_assistant_tool_calls(tool_calls):
    formatted = []
    for tool_call in tool_calls:
        formatted.append(
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments or "{}",
                },
            }
        )
    return formatted


def generate_advice(session, user_id: int, question: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")

    regulations = query_tax_law(question)
    regulations_text = "\n".join(f"- {item}" for item in regulations) if regulations else "- None"
    system_prompt = f"{SYSTEM_PROMPT}\nRelevant regulatory references:\n{regulations_text}"

    client = OpenAI(api_key=api_key)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    for _ in range(5):
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        assistant_message = response.choices[0].message
        tool_calls = assistant_message.tool_calls or []

        if not tool_calls:
            return (assistant_message.content or "").strip()

        messages.append(
            {
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": _format_assistant_tool_calls(tool_calls),
            }
        )

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            raw_args = tool_call.function.arguments or "{}"
            try:
                tool_params = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError:
                tool_params = {}

            tool_result = run_tool(session, user_id, tool_name, tool_params)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result),
                }
            )

    return ""
