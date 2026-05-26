import { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchModels, createChatCompletion, ChatModel, ChatMessage } from "../api/chat";
import ChatWindow from "../components/ChatWindow";
import ChatInput from "../components/ChatInput";
import ModelSelector from "../components/ModelSelector";
import SessionList, { Session } from "../components/SessionList";

const STORAGE_KEY = "gsml-sessions";

function loadSessions(): Record<string, { session: Session; messages: ChatMessage[] }> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveSessions(sessions: Record<string, { session: Session; messages: ChatMessage[] }>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

export default function Chat() {
  const allSessions = loadSessions();
  const [activeSessionId, setActiveSessionId] = useState(() => {
    const ids = Object.keys(allSessions);
    return ids.length > 0 ? ids[ids.length - 1] : "";
  });
  const [sessions, setSessions] = useState<Session[]>(() => Object.values(allSessions).map(s => s.session));
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const s = allSessions[activeSessionId];
    return s?.messages || [];
  });
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [selectedModel, setSelectedModel] = useState("");
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(2048);

  const { data: models } = useQuery<ChatModel[]>({
    queryKey: ["models"],
    queryFn: fetchModels,
    staleTime: 1000 * 60 * 5,
  });

  useEffect(() => {
    if (models && models.length > 0 && !selectedModel) {
      setSelectedModel(models[0].id);
    }
  }, [models]);

  useEffect(() => {
    saveSessions(Object.fromEntries(sessions.map(s => [s.id, { session: s, messages }])));
  }, [sessions, messages]);

  useEffect(() => {
    const existing = allSessions[activeSessionId];
    if (existing) {
      setMessages(existing.messages);
    }
  }, [activeSessionId]);

  const createNewSession = useCallback(() => {
    import("uuid").then(({ v4 }) => {
      const id = v4();
      const newSession: Session = { id, title: "새 세션", createdAt: Date.now() };
      setSessions(prev => [...prev, newSession]);
      setMessages([]);
      setActiveSessionId(id);
    });
  }, []);

  const deleteSession = useCallback((id: string) => {
    setSessions(prev => prev.filter(s => s.id !== id));
    setMessages([]);
    const newActive = sessions.find(s => s.id !== id);
    if (newActive) {
      setActiveSessionId(newActive.id);
      setMessages(allSessions[newActive.id]?.messages || []);
    }
  }, [sessions, allSessions]);

  const stopGeneration = useCallback(() => {
    abortController?.abort();
    setIsStreaming(false);
  }, [abortController]);

  const handleSubmit = useCallback(async (text: string) => {
    if (!selectedModel) return;

    const userMessage: ChatMessage = { role: "user", content: text };
    setMessages(prev => [...prev, userMessage]);
    setIsStreaming(true);
    setStreamingContent("");

    const controller = new AbortController();
    setAbortController(controller);

    const apiMessages = [...messages, userMessage];
    if (!messages.find(m => m.role === "system")) {
      apiMessages.unshift({ role: "system", content: "You are a helpful assistant." });
    }

    try {
      await createChatCompletion(
        { model: selectedModel, messages: apiMessages, temperature, max_tokens: maxTokens },
        (chunk) => setStreamingContent(prev => prev + chunk),
        () => {
          setMessages(prev => [...prev, { role: "assistant", content: streamingContent }]);
          setIsStreaming(false);
          setStreamingContent("");
          setAbortController(null);
        },
        (err) => {
          console.error("Chat error:", err);
          setMessages(prev => [...prev, { role: "assistant", content: `오류가 발생했습니다: ${err.message}` }]);
          setIsStreaming(false);
          setStreamingContent("");
          setAbortController(null);
        }
      );
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setMessages(prev => [...prev, { role: "assistant", content: `오류가 발생했습니다: ${err.message}` }]);
        setIsStreaming(false);
        setStreamingContent("");
      }
      setAbortController(null);
    }
  }, [selectedModel, messages, temperature, maxTokens, streamingContent]);

  useEffect(() => {
    if (isStreaming && streamingContent && messages.filter(m => m.role === "user").length === 1) {
      const firstUserMsg = messages.find(m => m.role === "user");
      if (firstUserMsg) {
        const title = firstUserMsg.content.slice(0, 40) + (firstUserMsg.content.length > 40 ? "..." : "");
        setSessions(prev => prev.map(s => s.id === activeSessionId ? { ...s, title } : s));
      }
    }
  }, [isStreaming, streamingContent, messages, activeSessionId]);

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <SessionList
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={(id) => { setActiveSessionId(id); setMessages(allSessions[id]?.messages || []); }}
        onDelete={deleteSession}
        onCreate={createNewSession}
      />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", background: "#fff" }}>
        <div style={{ padding: "12px 20px", borderBottom: "1px solid #eef0f3", display: "flex", justifyContent: "space-between", alignItems: "center", background: "#fff" }}>
          <h2 style={{ margin: 0, fontSize: "16px" }}>
            {sessions.find(s => s.id === activeSessionId)?.title || "새 세션"}
          </h2>
          <button className="secondary" onClick={() => { window.location.href = "/dashboard"; }} style={{ fontSize: "12px" }}>
            대시보드
          </button>
        </div>
        <ModelSelector
          models={models || []}
          selectedModel={selectedModel}
          onModelChange={setSelectedModel}
          temperature={temperature}
          onTemperatureChange={setTemperature}
          maxTokens={maxTokens}
          onMaxTokensChange={setMaxTokens}
        />
        <ChatWindow messages={messages} isStreaming={isStreaming} streamingContent={streamingContent} />
        <ChatInput onSubmit={handleSubmit} onStop={stopGeneration} isStreaming={isStreaming} />
      </div>
    </div>
  );
}
