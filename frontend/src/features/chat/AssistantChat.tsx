import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Bot,
  CheckCircle2,
  MessageSquareText,
  Plus,
  Send,
  Sparkles,
  Trash2,
  UserRound
} from "lucide-react";
import { useMutation } from "@tanstack/react-query";

import {
  answerExample,
  deleteConversation as deletePersistedConversation,
  explainQuestion,
  generateExample,
  listConversations,
  saveConversation
} from "../../services/apiClient";
import type {
  ChatConversationDto,
  Citation,
  ExampleResponse
} from "../../shared/apiTypes";
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

type Conversation = {
  id: string;
  title: string;
  mode: ChatMode;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
};

const starterPrompts: Record<ChatMode, string> = {
  explicame: "¿En qué casos un deudor se clasifica en categoría Dudoso?",
  ejemplifica: "Genera un caso de un deudor de microempresa en categoría Deficiente."
};

function createWelcomeMessage(): AssistantTextMessage {
  return {
    id: crypto.randomUUID(),
    role: "assistant",
    kind: "text",
    text: "Hola. Puedo explicarte el reglamento o generarte casos para practicar clasificación crediticia.",
    citations: []
  };
}

function createConversation(mode: ChatMode = "explicame"): Conversation {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    title: "Nueva conversación",
    mode,
    messages: [createWelcomeMessage()],
    createdAt: now,
    updatedAt: now
  };
}

function getConversationTitle(messages: ChatMessage[]): string {
  const firstQuestion = messages.find((item) => item.role === "user");
  if (!firstQuestion || firstQuestion.role !== "user") {
    return "Nueva conversación";
  }
  return firstQuestion.text.length > 58
    ? `${firstQuestion.text.slice(0, 58)}...`
    : firstQuestion.text;
}

function formatHistoryTime(value: string): string {
  return new Intl.DateTimeFormat("es-PE", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "short"
  }).format(new Date(value));
}

export function AssistantChat({ userKey }: { userKey: string }) {
  const [mode, setMode] = useState<ChatMode>("explicame");
  const [message, setMessage] = useState(starterPrompts.explicame);
  const [useLlmVariation, setUseLlmVariation] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState("");
  const [answeringIds, setAnsweringIds] = useState<Set<string>>(new Set());
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [dirtyConversationIds, setDirtyConversationIds] = useState<Set<string>>(
    new Set()
  );

  const activeConversation = useMemo(
    () => conversations.find((item) => item.id === activeConversationId),
    [activeConversationId, conversations]
  );
  const messages = activeConversation?.messages ?? [];

  useEffect(() => {
    let cancelled = false;
    setHistoryLoaded(false);
    setHistoryError(null);
    setDirtyConversationIds(new Set());

    async function loadHistory() {
      try {
        const persisted = await listConversations();
        if (cancelled) {
          return;
        }
        if (persisted.length > 0) {
          const ordered = persisted
            .map(fromDto)
            .sort(
            (left, right) =>
              new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime()
          );
          setConversations(ordered);
          setActiveConversationId(ordered[0].id);
          setMode(ordered[0].mode);
          setMessage(starterPrompts[ordered[0].mode]);
          setHistoryLoaded(true);
          return;
        }
      } catch {
        if (!cancelled) {
          setHistoryError("No se pudo cargar el historial.");
        }
      }

      if (cancelled) {
        return;
      }
      const initial = createConversation();
      setConversations([initial]);
      setActiveConversationId(initial.id);
      setMode(initial.mode);
      setMessage(starterPrompts[initial.mode]);
      setHistoryLoaded(true);
    }

    void loadHistory();
    return () => {
      cancelled = true;
    };
  }, [userKey]);

  useEffect(() => {
    if (
      !historyLoaded ||
      conversations.length === 0 ||
      dirtyConversationIds.size === 0
    ) {
      return;
    }
    for (const conversationId of dirtyConversationIds) {
      const conversation = conversations.find((item) => item.id === conversationId);
      if (!conversation) {
        continue;
      }
      void saveConversation(toDto(conversation))
        .then(() => {
          setHistoryError(null);
          setDirtyConversationIds((current) => {
            const next = new Set(current);
            next.delete(conversationId);
            return next;
          });
        })
        .catch(() => {
          setHistoryError("No se pudo guardar el historial.");
        });
    }
  }, [conversations, dirtyConversationIds, historyLoaded]);

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

  function updateActiveMessages(updater: (current: ChatMessage[]) => ChatMessage[]) {
    setConversations((current) =>
      current.map((conversation) => {
        if (conversation.id !== activeConversationId) {
          return conversation;
        }
        const nextMessages = updater(conversation.messages);
        markConversationDirty(conversation.id);
        return {
          ...conversation,
          messages: nextMessages,
          title: getConversationTitle(nextMessages),
          updatedAt: new Date().toISOString()
        };
      })
    );
  }

  function appendAssistant(
    payload:
      | Omit<AssistantTextMessage, "id" | "role">
      | Omit<AssistantExampleMessage, "id" | "role">
  ) {
    updateActiveMessages((current) => [
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
      updateActiveMessages((current) =>
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
    markConversationDirty(activeConversationId);
    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === activeConversationId
          ? { ...conversation, mode: nextMode, updatedAt: new Date().toISOString() }
          : conversation
      )
    );
  }

  function startNewConversation() {
    const next = createConversation(mode);
    setConversations((current) => [next, ...current]);
    setActiveConversationId(next.id);
    setMessage(starterPrompts[next.mode]);
    markConversationDirty(next.id);
  }

  function selectConversation(conversation: Conversation) {
    setActiveConversationId(conversation.id);
    setMode(conversation.mode);
    setMessage(starterPrompts[conversation.mode]);
  }

  function deleteConversation(conversationId: string) {
    void deletePersistedConversation(conversationId).catch(() => {
      setHistoryError("No se pudo eliminar la conversación.");
    });
    setDirtyConversationIds((current) => {
      const next = new Set(current);
      next.delete(conversationId);
      return next;
    });
    setConversations((current) => {
      const remaining = current.filter((item) => item.id !== conversationId);
      if (remaining.length > 0) {
        if (conversationId === activeConversationId) {
          setActiveConversationId(remaining[0].id);
          setMode(remaining[0].mode);
          setMessage(starterPrompts[remaining[0].mode]);
        }
        return remaining;
      }

      const fresh = createConversation();
      setActiveConversationId(fresh.id);
      setMode(fresh.mode);
      setMessage(starterPrompts[fresh.mode]);
      return [fresh];
    });
  }

  function markConversationDirty(conversationId: string) {
    if (!conversationId) {
      return;
    }
    setDirtyConversationIds((current) => {
      const next = new Set(current);
      next.add(conversationId);
      return next;
    });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || sendMessage.isPending) {
      return;
    }
    updateActiveMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", text: trimmed }
    ]);
    setMessage("");
    sendMessage.mutate(trimmed);
  }

  return (
    <section className="assistant-workspace" aria-label="Chat del asistente SBS">
      <div className="chat-shell">
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
          {historyError ? <p className="form-error">{historyError}</p> : null}
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
      </div>

      <aside className="history-panel" aria-label="Historial de conversaciones">
        <div className="history-header">
          <div>
            <p className="eyebrow">Tu actividad</p>
            <h2>Historial</h2>
          </div>
          <button
            aria-label="Nueva conversación"
            className="icon-button"
            type="button"
            onClick={startNewConversation}
          >
            <Plus aria-hidden="true" size={18} />
          </button>
        </div>

        <div className="history-list">
          {!historyLoaded ? (
            <p className="history-empty">Cargando historial...</p>
          ) : null}
          {conversations.map((conversation) => (
            <article
              className={
                conversation.id === activeConversationId
                  ? "history-item active"
                  : "history-item"
              }
              key={conversation.id}
            >
              <button type="button" onClick={() => selectConversation(conversation)}>
                <span className="history-icon">
                  <MessageSquareText aria-hidden="true" size={16} />
                </span>
                <span>
                  <strong>{conversation.title}</strong>
                  <small>
                    {conversation.mode === "explicame" ? "Explícame" : "Ejemplifica"} ·{" "}
                    {formatHistoryTime(conversation.updatedAt)}
                  </small>
                </span>
              </button>
              <button
                aria-label={`Eliminar ${conversation.title}`}
                className="history-delete"
                type="button"
                onClick={() => deleteConversation(conversation.id)}
              >
                <Trash2 aria-hidden="true" size={15} />
              </button>
            </article>
          ))}
        </div>
      </aside>
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

function toDto(
  conversation: Conversation
): Pick<ChatConversationDto, "id" | "title" | "mode" | "messages"> {
  return {
    id: conversation.id,
    title: conversation.title,
    mode: conversation.mode,
    messages: conversation.messages as unknown as Record<string, unknown>[]
  };
}

function fromDto(conversation: ChatConversationDto): Conversation {
  return {
    id: conversation.id,
    title: conversation.title,
    mode: conversation.mode,
    messages: conversation.messages as ChatMessage[],
    createdAt: conversation.created_at,
    updatedAt: conversation.updated_at
  };
}
