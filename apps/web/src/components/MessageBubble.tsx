import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
}

export interface ParsedContent {
  thinking: string | null;
  thinkingOpen: boolean;
  answer: string;
}

export function parseThink(content: string): ParsedContent {
  const closed = content.match(/^<think>([\s\S]*?)<\/think>\s*/);
  if (closed) {
    const thinkingText = closed[1].trim();
    if (!thinkingText) {
      return { thinking: null, thinkingOpen: false, answer: content.slice(closed[0].length) };
    }
    return { thinking: thinkingText, thinkingOpen: false, answer: content.slice(closed[0].length) };
  }
  if (content.startsWith("<think>")) {
    const partial = content.slice(7).trim();
    return { thinking: partial || null, thinkingOpen: true, answer: "" };
  }
  return { thinking: null, thinkingOpen: false, answer: content };
}

function ThinkingBlock({ text, streaming = false }: { text: string; streaming?: boolean }) {
  const [open, setOpen] = useState(streaming);

  return (
    <div style={{ marginBottom: 8 }}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          background: "none",
          border: "none",
          padding: 0,
          cursor: "pointer",
          color: "#9aa0a8",
          fontSize: "12px",
          display: "flex",
          alignItems: "center",
          gap: 5,
        }}
      >
        <span
          style={{
            fontSize: 9,
            display: "inline-block",
            transform: open ? "rotate(90deg)" : "none",
            transition: "transform 0.15s",
          }}
        >
          ▶
        </span>
        {streaming ? "추론 중…" : "추론 과정"}
      </button>
      {open && (
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
          {text}
        </div>
      )}
    </div>
  );
}

export default function MessageBubble({ role, content }: MessageBubbleProps) {
  if (role === "user") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <div className="card" style={{ maxWidth: "70%", borderRadius: "16px 16px 4px 16px", padding: "12px 16px" }}>
          <p style={{ margin: 0, whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{content}</p>
        </div>
      </div>
    );
  }

  const { thinking, answer } = parseThink(content);

  return (
    <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 12 }}>
      <div className="card" style={{ maxWidth: "70%", borderRadius: "16px 16px 16px 4px", padding: "12px 16px" }}>
        {thinking !== null && <ThinkingBlock text={thinking} streaming={false} />}
        {answer && (
          <ReactMarkdown
            components={{
              code({ className, children, ...props }) {
                const isInline = !className;
                if (isInline) {
                  return <code className="mono" {...props}>{children}</code>;
                }
                const match = /language-(\w+)/.exec(className || "");
                const language = match ? match[1] : "";
                return (
                  <SyntaxHighlighter
                    style={oneDark}
                    language={language}
                    PreTag="div"
                    customStyle={{ margin: "8px 0", borderRadius: "8px" }}
                  >
                    {String(children).replace(/\n$/, "")}
                  </SyntaxHighlighter>
                );
              },
              p({ children }) {
                return <p style={{ margin: "4px 0", whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{children}</p>;
              },
            }}
          >
            {answer}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}
