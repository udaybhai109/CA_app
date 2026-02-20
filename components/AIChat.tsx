import { FormEvent, useEffect, useRef, useState } from "react";

import { apiClient } from "../lib/api";

type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  toolLabel?: string;
};

type AIChatProps = {
  userId?: number;
};

const TOOL_NAME_MAP: Record<string, string> = {
  pnl: "P&L",
  balance_sheet: "Balance Sheet",
  gst_summary: "GST Summary",
  tds_summary: "TDS Summary",
  financial_health: "Financial Health",
  aging: "Aging",
};

const getToolLabel = (toolUsed: unknown): string | undefined => {
  if (!toolUsed) return undefined;

  const tools = Array.isArray(toolUsed) ? toolUsed : [toolUsed];
  const labels = tools
    .map((tool) => TOOL_NAME_MAP[String(tool)] || String(tool))
    .filter((tool) => tool && tool !== "undefined");

  if (labels.length === 0) {
    return "Analysis based on: P&L / GST Summary";
  }

  return `Analysis based on: ${labels.join(" / ")}`;
};

const parseAdviceResponse = (
  data: unknown
): { message: string; toolLabel?: string } => {
  if (typeof data === "string") {
    return { message: data };
  }

  if (data && typeof data === "object") {
    const payload = data as Record<string, unknown>;
    const message =
      (payload.explanation as string) ||
      (payload.advice as string) ||
      (payload.response as string) ||
      (payload.message as string) ||
      "Unable to generate advice at this time.";

    const toolLabel = getToolLabel(
      payload.tool_used ??
        payload.toolUsed ??
        (payload.metadata as Record<string, unknown> | undefined)?.tool_used
    );

    return { message, toolLabel };
  }

  return { message: "Unable to generate advice at this time." };
};

export default function AIChat({ userId = 1 }: AIChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      text: "Ask a financial question to get a concise, professional analysis.",
    },
  ]);
  const [question, setQuestion] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messageListRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!messageListRef.current) return;
    messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
  }, [messages, isSending]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isSending) return;

    setError(null);
    setIsSending(true);

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      text: trimmedQuestion,
    };
    setMessages((prev) => [...prev, userMessage]);
    setQuestion("");

    try {
      const response = await apiClient.get(`/advice/${userId}`, {
        params: { question: trimmedQuestion },
      });
      const parsed = parseAdviceResponse(response.data);

      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          text: parsed.message,
          toolLabel: parsed.toolLabel,
        },
      ]);
    } catch {
      setError("Unable to fetch advice right now.");
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="flex h-[28rem] flex-col rounded-2xl border border-borderLight bg-card shadow-sm transition-all duration-200 ease-in-out hover:-translate-y-0.5 hover:shadow-md">
      <div ref={messageListRef} className="flex-1 space-y-4 overflow-y-auto p-6">
        {messages.map((message) => (
          <div key={message.id} className="space-y-1">
            <div
              className={`max-w-[90%] rounded-xl border px-3 py-2 text-sm ${
                message.role === "user"
                  ? "ml-auto border-primary/25 bg-primary/10 text-navy"
                  : "border-borderLight bg-white text-navy"
              }`}
            >
              {message.text}
            </div>
            {message.toolLabel ? (
              <p className="text-xs text-muted">{message.toolLabel}</p>
            ) : null}
          </div>
        ))}
        {isSending ? <p className="text-sm text-muted">Generating analysis...</p> : null}
      </div>

      <form onSubmit={handleSubmit} className="border-t border-borderLight p-6">
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask about profit, GST, cash runway, or risks"
            className="h-10 w-full rounded-lg border border-borderLight bg-white px-3 text-sm text-navy outline-none ring-primary/30 placeholder:text-muted transition-all duration-200 ease-in-out focus:ring-2"
          />
          <button
            type="submit"
            disabled={isSending || !question.trim()}
            className="h-10 rounded-lg bg-primary px-4 text-sm font-medium text-white transition-all duration-200 ease-in-out hover:brightness-110 active:scale-95 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Send
          </button>
        </div>
        {error ? <p className="mt-2 text-xs text-danger">{error}</p> : null}
      </form>
    </div>
  );
}
