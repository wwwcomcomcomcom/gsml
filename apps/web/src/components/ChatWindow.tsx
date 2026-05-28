import { useRef, useEffect } from "react";
import MessageBubble from "./MessageBubble";
import { parseThink } from "./MessageBubble";
import { ChatMessage } from "../api/chat";

interface ChatWindowProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingContent: string;
}

export default function ChatWindow({ messages, isStreaming, streamingContent }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming, streamingContent]);

  const { thinking, thinkingOpen, answer } = parseThink(streamingContent);

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
      {messages.length === 0 && !isStreaming && (
        <div style={{ textAlign: "center", padding: "80px 20px", color: "#6a7178" }}>
          <h2 style={{ marginBottom: 8 }}>GSML 채팅</h2>
          <p>메시지를 입력하여 AI와 대화하세요</p>
        </div>
      )}
      {messages.map((msg, i) => (
        <MessageBubble key={i} role={msg.role as "user" | "assistant"} content={msg.content} />
      ))}
      {isStreaming && (
        <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 12 }}>
          <div className="card" style={{ maxWidth: "70%", borderRadius: "16px 16px 16px 4px", padding: "12px 16px" }}>
            {thinking !== null && (
              <details open style={{ marginBottom: answer ? 8 : 0 }}>
                <summary
                  style={{
                    cursor: "pointer",
                    color: "#9aa0a8",
                    fontSize: "12px",
                    userSelect: "none",
                    listStyle: "none",
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  <span style={{ fontSize: 10 }}>▶</span>
                  {thinkingOpen ? "추론 중…" : "추론 과정"}
                </summary>
                <div
                  style={{
                    color: "#9aa0a8",
                    fontSize: "12px",
                    marginTop: 6,
                    paddingLeft: 10,
                    borderLeft: "2px solid #e5e7eb",
                    whiteSpace: "pre-wrap",
                    lineHeight: 1.5,
                  }}
                >
                  {thinking}
                </div>
              </details>
            )}
            {answer ? (
              <p style={{ margin: 0, whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{answer}</p>
            ) : thinking === null ? (
              <p style={{ margin: 0, whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
                {streamingContent || <span style={{ color: "#6a7178" }}>⋯</span>}
              </p>
            ) : null}
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
