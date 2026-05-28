import { api } from "./client";
import { authStore } from "../lib/auth";

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

/**
 * @param onChunk  스트리밍 중 새 토큰이 올 때마다 호출
 * @param onDone   완료 시 호출 — 최종 누적 텍스트 전달
 * @param onError  오류 시 호출
 */
export async function createChatCompletion(
  params: ChatCompletionParams,
  onChunk: (text: string) => void,
  onDone: (fullContent: string) => void,
  onError: (err: Error) => void
): Promise<void> {
  const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const token = authStore.get();

  let response: Response;
  try {
    response = await fetch(`${baseURL}/api/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ ...params, stream: true }),
    });
  } catch (e) {
    onError(e instanceof Error ? e : new Error(String(e)));
    return;
  }

  if (!response.ok) {
    onError(new Error(`HTTP ${response.status}`));
    return;
  }

  if (!response.body) {
    onError(new Error("No response body"));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let accumulated = "";
  let finished = false;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith("data: ")) continue;
        const data = trimmed.slice(6);
        if (data === "[DONE]") {
          finished = true;
          onDone(accumulated);
          return;
        }
        try {
          const parsed = JSON.parse(data);
          const content = parsed.choices?.[0]?.delta?.content;
          if (content) {
            accumulated += content;
            onChunk(content);
          }
        } catch {
          // malformed JSON chunk — skip
        }
      }
    }
  } catch (e) {
    onError(e instanceof Error ? e : new Error(String(e)));
  } finally {
    reader.releaseLock();
    if (!finished) onDone(accumulated);
  }
}
