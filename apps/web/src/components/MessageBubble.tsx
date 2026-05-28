import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
}

export interface ParsedContent {
  thinking: string | null;
  /** thinking 블록이 아직 닫히지 않은 상태 (스트리밍 중) */
  thinkingOpen: boolean;
  answer: string;
}

export function parseThink(content: string): ParsedContent {
  // 완전한 <think>...</think> 블록
  const closed = content.match(/^<think>([\s\S]*?)<\/think>\s*/);
  if (closed) {
    return { thinking: closed[1].trim(), thinkingOpen: false, answer: content.slice(closed[0].length) };
  }
  // 아직 닫히지 않은 <think>... (스트리밍 중)
  if (content.startsWith("<think>")) {
    return { thinking: content.slice(7), thinkingOpen: true, answer: "" };
  }
  return { thinking: null, thinkingOpen: false, answer: content };
}

function ThinkingBlock({ text, open }: { text: string; open?: boolean }) {
  return (
    <details open={open} style={{ marginBottom: 8 }}>
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
        {open ? "추론 중…" : "추론 과정"}
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
        {text}
      </div>
    </details>
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

  const { thinking, thinkingOpen, answer } = parseThink(content);

  return (
    <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 12 }}>
      <div className="card" style={{ maxWidth: "70%", borderRadius: "16px 16px 16px 4px", padding: "12px 16px" }}>
        {thinking !== null && <ThinkingBlock text={thinking} open={thinkingOpen} />}
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
