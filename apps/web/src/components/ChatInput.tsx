import { useState, useRef, useEffect } from "react";

interface ChatInputProps {
  onSubmit: (message: string) => void;
  onStop: () => void;
  isStreaming: boolean;
}

export default function ChatInput({ onSubmit, onStop, isStreaming }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + "px";
    }
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !isStreaming) {
        onSubmit(value.trim());
        setValue("");
      }
    }
  };

  return (
    <div style={{ padding: "12px 20px", borderTop: "1px solid #eef0f3", background: "#fff" }}>
      <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
        <div style={{ flex: 1, position: "relative" }}>
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="메시지를 입력하세요..."
            disabled={isStreaming}
            rows={1}
            style={{
              width: "100%",
              padding: "10px 14px",
              border: "1px solid #d8dce0",
              borderRadius: "10px",
              fontSize: "14px",
              resize: "none",
              outline: "none",
              fontFamily: "inherit",
              minHeight: "44px",
              maxHeight: "200px",
              overflowY: "auto",
              boxSizing: "border-box",
            }}
          />
        </div>
        {isStreaming ? (
          <button className="danger" onClick={onStop} style={{ padding: "10px 16px" }}>
            중지
          </button>
        ) : (
          <button
            onClick={() => {
              if (value.trim()) {
                onSubmit(value.trim());
                setValue("");
              }
            }}
            disabled={!value.trim()}
            style={{ padding: "10px 16px", opacity: value.trim() ? 1 : 0.5 }}
          >
            전송
          </button>
        )}
      </div>
    </div>
  );
}
