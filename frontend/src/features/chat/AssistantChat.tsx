import { FormEvent, useState } from "react";
import { Bot, CheckCircle2, Send, Sparkles, UserRound } from "lucide-react";
import { useMutation } from "@tanstack/react-query";

import {
  answerExample,
  explainQuestion,
  generateExample
} from "../../services/apiClient";
import type { Citation, ExampleResponse } from "../../shared/apiTypes";
import { renderAssistantMarkdown } from "../../shared/markdown";

type ChatMode = "explicame" | "ejemplifica";

type BaseMessage = {
  id: string;
  role: "user" | "assistant";
};

type UserMessage = BaseMessage & {
  role: "user";
  text: string;
};

type AssistantTextMessage = BaseMessage & {
  role: "assistant";
  kind: "text";
  citations: Citation[];
  text: string;
};

type AssistantExampleMessage = BaseMessage & {
  role: "assistant";
  kind: "example";
  example: ExampleResponse;
  feedback?: {
    correct: boolean;
    correctCategory: string;
    text: string;
  };
};

type ChatMessage = UserMessage | AssistantTextMessage | AssistantExampleMessage;

const starterPrompts = {
  explicame: "¿En qué casos un deudor se clasifica en categoría Dudoso?",
  ejemplifica: "Genera un caso de un deudor de microempresa en categoría Deficiente."
};

export function AssistantChat() {
  const [mode, setMode] = useState<ChatMode>("explicame");
  const [message, setMessage] = useState(starterPrompts.explicame);
  const [useLlmVariation, setUseLlmVariation] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: crypto.randomUUID(),
      role: "assistant",
      kind: "text",
      text: "Hola. Puedo explicarte el reglamento o generarte casos para practicar clasificación crediticia.",
      citations: []
    }
  ]);
  const [answeringIds, setAnsweringIds] = useState<Set<string>>(new Set());

  const sendMessage = useMutation({
    mutationFn: async (input: string) => {
      if (mode === "explicame") {
        return explainQuestion(input);
      }
      return generateExample(input, useLlmVariation);
    },
    onSuccess: (response) => {
      if (response.type === "text") {
        appendAssistant({
          kind: "text",
          text: response.data.answer,
          citations: response.data.citations
        });
        return;
      }
      appendAssistant({
        kind: "example",
        example: response
      });
    }
  });

  function appendAssistant(
    payload:
      | Omit<AssistantTextMessage, "id" | "role">
      | Omit<AssistantExampleMessage, "id" | "role">
  ) {
    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: "assistant",
        ...payload
      }
    ]);
  }

  async function submitExampleAnswer(messageId: string, category: string) {
    const target = messages.find(
      (item): item is AssistantExampleMessage =>
        item.id === messageId && item.role === "assistant" && item.kind === "example"
    );
    if (!target) {
      return;
    }
    setAnsweringIds((current) => new Set(current).add(messageId));
    try {
      const result = await answerExample(target.example.data.case_id, category);
      setMessages((current) =>
        current.map((item) =>
          item.id === messageId && item.role === "assistant" && item.kind === "example"
            ? {
                ...item,
                feedback: {
                  correct: result.data.correct,
                  correctCategory: result.data.correct_category,
                  text: result.data.feedback
                }
              }
            : item
        )
      );
    } finally {
      setAnsweringIds((current) => {
        const next = new Set(current);
        next.delete(messageId);
        return next;
      });
    }
  }

  function handleModeChange(nextMode: ChatMode) {
    setMode(nextMode);
    setMessage(starterPrompts[nextMode]);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || sendMessage.isPending) {
      return;
    }
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", text: trimmed }
    ]);
    setMessage("");
    sendMessage.mutate(trimmed);
  }

  return (
    <section className="chat-shell" aria-label="Chat del asistente SBS">
      <div className="chat-toolbar">
        <div className="mode-tabs" role="tablist" aria-label="Modo pedagógico">
          <button
            className={mode === "explicame" ? "active" : ""}
            type="button"
            onClick={() => handleModeChange("explicame")}
          >
            Explícame
          </button>
          <button
            className={mode === "ejemplifica" ? "active" : ""}
            type="button"
            onClick={() => handleModeChange("ejemplifica")}
          >
            Ejemplifica
          </button>
        </div>

        {mode === "ejemplifica" ? (
          <label className="inline-check">
            <input
              checked={useLlmVariation}
              type="checkbox"
              onChange={(event) => setUseLlmVariation(event.target.checked)}
            />
            Variar narrativa
          </label>
        ) : null}
      </div>

      <div className="chat-thread">
        {messages.map((item) => (
          <ChatBubble
            key={item.id}
            message={item}
            isAnswering={answeringIds.has(item.id)}
            onAnswer={submitExampleAnswer}
          />
        ))}
        {sendMessage.isPending ? (
          <div className="chat-row assistant">
            <span className="avatar">
              <Bot aria-hidden="true" size={18} />
            </span>
            <div className="bubble">Pensando...</div>
          </div>
        ) : null}
        {sendMessage.isError ? (
          <p className="form-error">No se pudo completar la solicitud.</p>
        ) : null}
      </div>

      <form className="composer" onSubmit={handleSubmit}>
        <textarea
          value={message}
          rows={2}
          onChange={(event) => setMessage(event.target.value)}
          placeholder={
            mode === "explicame"
              ? "Pregunta algo sobre el reglamento..."
              : "Pide un caso para practicar..."
          }
        />
        <button disabled={sendMessage.isPending || !message.trim()} type="submit">
          {mode === "ejemplifica" ? (
            <Sparkles aria-hidden="true" size={18} />
          ) : (
            <Send aria-hidden="true" size={18} />
          )}
          Enviar
        </button>
      </form>
    </section>
  );
}

function ChatBubble({
  message,
  isAnswering,
  onAnswer
}: {
  message: ChatMessage;
  isAnswering: boolean;
  onAnswer: (messageId: string, category: string) => void;
}) {
  if (message.role === "user") {
    return (
      <div className="chat-row user">
        <div className="bubble">{message.text}</div>
        <span className="avatar">
          <UserRound aria-hidden="true" size={18} />
        </span>
      </div>
    );
  }

  return (
    <div className="chat-row assistant">
      <span className="avatar">
        <Bot aria-hidden="true" size={18} />
      </span>
      <div className="bubble">
        {message.kind === "text" ? (
          <TextAnswer message={message} />
        ) : (
          <ExampleAnswer
            message={message}
            isAnswering={isAnswering}
            onAnswer={onAnswer}
          />
        )}
      </div>
    </div>
  );
}

function TextAnswer({ message }: { message: AssistantTextMessage }) {
  return (
    <>
      <div className="assistant-markdown">{renderAssistantMarkdown(message.text)}</div>
      {message.citations.length ? (
        <div className="citation-list">
          {message.citations.map((citation) => (
            <details key={citation.chunk_id}>
              <summary>{citation.label}</summary>
              <p>{citation.text_preview}</p>
            </details>
          ))}
        </div>
      ) : null}
    </>
  );
}

function ExampleAnswer({
  message,
  isAnswering,
  onAnswer
}: {
  message: AssistantExampleMessage;
  isAnswering: boolean;
  onAnswer: (messageId: string, category: string) => void;
}) {
  const [selected, setSelected] = useState("");

  return (
    <div className="example-message">
      <p className="source-note">{message.example.data.source_article}</p>
      <div className="case-grid">
        {Object.entries(message.example.data.case).map(([key, value]) => (
          <div key={key}>
            <span>{formatLabel(key)}</span>
            <strong>{String(value)}</strong>
          </div>
        ))}
      </div>

      <div className="answer-row">
        <select
          disabled={Boolean(message.feedback)}
          value={selected}
          onChange={(event) => setSelected(event.target.value)}
        >
          <option value="">Selecciona categoría</option>
          {message.example.data.options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <button
          disabled={!selected || isAnswering || Boolean(message.feedback)}
          type="button"
          onClick={() => onAnswer(message.id, selected)}
        >
          <CheckCircle2 aria-hidden="true" size={18} />
          Validar
        </button>
      </div>

      {message.feedback ? (
        <article
          className={message.feedback.correct ? "feedback success" : "feedback warning"}
        >
          <strong>
            {message.feedback.correct ? "Respuesta correcta" : "Revisemos"}
          </strong>
          <p>{message.feedback.text}</p>
        </article>
      ) : null}
    </div>
  );
}

function formatLabel(value: string): string {
  return value.replaceAll("_", " ");
}
