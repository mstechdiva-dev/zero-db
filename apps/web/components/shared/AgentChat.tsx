"use client";

import { useState, useRef, useEffect } from "react";

type AgentName = "obi" | "sully" | "sal";

const AGENT_LABELS: Record<AgentName, { name: string; role: string }> = {
  obi: { name: "Obi", role: "Database setup assistant" },
  sully: { name: "Sully", role: "Support" },
  sal: { name: "Sal", role: "Sales" },
};

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface AgentChatProps {
  agent: AgentName;
  initialMessage?: string;
  onHandoff?: (signal: string) => void;
}

export default function AgentChat({
  agent,
  initialMessage,
  onHandoff,
}: AgentChatProps) {
  const info = AGENT_LABELS[agent];
  const [messages, setMessages] = useState<Message[]>(
    initialMessage ? [{ role: "assistant", content: initialMessage }] : []
  );
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const res = await fetch("/api/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent, message: text, history: messages }),
      });
      if (!res.ok) {
        throw new Error(`Request failed: ${res.status}`);
      }
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response },
      ]);
      if (data.handoff) onHandoff?.(data.handoff);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-[#111] border border-gray-800 rounded-xl flex flex-col h-[480px]">
      <div className="px-5 py-4 border-b border-gray-800">
        <p className="text-sm font-medium text-white">{info.name}</p>
        <p className="text-xs text-gray-500">{info.role}</p>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] px-4 py-2.5 rounded-xl text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-[#00e87a]/10 text-[#00e87a] rounded-br-sm"
                  : "bg-gray-900 text-gray-200 rounded-bl-sm"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-900 text-gray-500 px-4 py-2.5 rounded-xl rounded-bl-sm text-sm">
              Thinking...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="px-4 py-4 border-t border-gray-800 flex gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Type a message..."
          className="flex-1 px-4 py-2.5 bg-[#0a0a0a] border border-gray-800 rounded-lg text-white placeholder-gray-600 text-sm focus:outline-none focus:border-[#00e87a] transition-colors"
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="px-4 py-2.5 bg-[#00e87a] text-black font-semibold text-sm rounded-lg hover:bg-[#00c96a] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </div>
    </div>
  );
}
