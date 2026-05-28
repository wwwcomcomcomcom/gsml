import { api } from "./client";

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface ChatCompletionParams {
  model: string;
  messages: ChatMessage[];
  stream?: boolean;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
}

export interface ChatModel {
  id: string;
  name: string;
}

export async function fetchModels(): Promise<ChatModel[]> {
  try {
    const res = await api.get("/v1/models");
    return res.data.data?.map((m: any) => ({ id: m.id, name: m.id })) || [];
  } catch {
    return [];
  }
}

export async function createChatCompletion(
  params: ChatCompletionParams,
  onChunk: (text: string) => void,
  onDone: () => void,
  _onError: (err: Error) => void
): Promise<void> {
  const response = await api.post("/api/chat/completions", {
    ...params,
    stream: true,
  }, {
    responseType: "stream",
    headers: { "Content-Type": "application/json" },
  });

  const reader = response.data.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith("data: ")) continue;
        const data = trimmed.slice(6);
        if (data === "[DONE]") {
          onDone();
          return;
        }
        try {
          const parsed = JSON.parse(data);
          const content = parsed.choices?.[0]?.delta?.content;
          if (content) onChunk(content);
        } catch {
          // Skip malformed JSON
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
