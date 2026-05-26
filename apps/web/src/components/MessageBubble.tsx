import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
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

  return (
    <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 12 }}>
      <div className="card" style={{ maxWidth: "70%", borderRadius: "16px 16px 16px 4px", padding: "12px 16px" }}>
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
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}
