import { useState } from "react";
import { ChatModel } from "../api/chat";

interface ModelSelectorProps {
  models: ChatModel[];
  selectedModel: string;
  onModelChange: (model: string) => void;
  temperature: number;
  onTemperatureChange: (temp: number) => void;
  maxTokens: number;
  onMaxTokensChange: (tokens: number) => void;
}

export default function ModelSelector({
  models,
  selectedModel,
  onModelChange,
  temperature,
  onTemperatureChange,
  maxTokens,
  onMaxTokensChange,
}: ModelSelectorProps) {
  const [showSettings, setShowSettings] = useState(false);

  return (
    <div style={{ padding: "8px 20px", borderBottom: "1px solid #eef0f3", background: "#fafbfc" }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <select
          value={selectedModel}
          onChange={(e) => onModelChange(e.target.value)}
          style={{
            padding: "6px 12px",
            border: "1px solid #d8dce0",
            borderRadius: "6px",
            fontSize: "13px",
            background: "#fff",
            outline: "none",
          }}
        >
          {models.length === 0 && <option value="">모델 로딩 중...</option>}
          {models.map((m) => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>
        <button
          className="secondary"
          onClick={() => setShowSettings(!showSettings)}
          style={{ fontSize: "12px", padding: "4px 10px" }}
        >
          설정
        </button>
      </div>
      {showSettings && (
        <div style={{ display: "flex", gap: 16, marginTop: 8, alignItems: "center" }}>
          <label style={{ fontSize: "12px", display: "flex", alignItems: "center", gap: 4 }}>
            Temp:
            <input
              type="number"
              min="0"
              max="2"
              step="0.1"
              value={temperature}
              onChange={(e) => onTemperatureChange(parseFloat(e.target.value) || 0.7)}
              style={{ width: 50, padding: "4px 6px", border: "1px solid #d8dce0", borderRadius: "4px", fontSize: "12px" }}
            />
          </label>
          <label style={{ fontSize: "12px", display: "flex", alignItems: "center", gap: 4 }}>
            Max:
            <input
              type="number"
              min="1"
              step="100"
              value={maxTokens}
              onChange={(e) => onMaxTokensChange(parseInt(e.target.value) || 2048)}
              style={{ width: 70, padding: "4px 6px", border: "1px solid #d8dce0", borderRadius: "4px", fontSize: "12px" }}
            />
          </label>
        </div>
      )}
    </div>
  );
}
