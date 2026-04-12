const RAILWAY_API_URL = process.env.RAILWAY_API_URL;

if (!RAILWAY_API_URL) {
  throw new Error("RAILWAY_API_URL environment variable is not set");
}

export type AgentName = "shawn" | "taylor" | "jordan";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  response: string;
  handoff: string | null;
  agent: string;
}

export async function callAgent(
  agentName: AgentName,
  message: string,
  history: ChatMessage[] = [],
  accessToken: string
): Promise<ChatResponse> {
  const res = await fetch(`${RAILWAY_API_URL}/agent/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ agent: agentName, message, history }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Agent request failed (${res.status}): ${text}`);
  }

  return res.json();
}
