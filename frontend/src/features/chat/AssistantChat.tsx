import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Bot,
  CheckCircle2,
  Gavel,
  MessageSquareText,
  Plus,
  Send,
  Sparkles,
  Trash2,
  UserRound
} from "lucide-react";
import { useMutation } from "@tanstack/react-query";

import {
  advanceSimulationTurn,
  answerExample,
  classifySimulation,
  deleteConversation as deletePersistedConversation,
  explainQuestion,
  generateExample,
  listConversations,
  saveConversation,
  startSimulation
} from "../../services/apiClient";
import type {
  ChatConversationDto,
  Citation,
  ExampleResponse,
  SimulationResponse
} from "../../shared/apiTypes";
import { renderAssistantMarkdown } from "../../shared/markdown";

type ChatMode = "explicame" | "ejemplifica" | "simulacion";

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
    targetConcept: string | null;
    masteryBefore: number | null;
    masteryAfter: number | null;
    nextConcept: string | null;
    recommendation: string | null;
  };
};

type AssistantSimulationMessage = BaseMessage & {
  role: "assistant";
  kind: "simulation";
  simulation: SimulationResponse;
};

type ChatMessage =
  | UserMessage
  | AssistantTextMessage
  | AssistantExampleMessage
  | AssistantSimulationMessage;

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
  ,
  simulacion: "Inicia una simulacion adversarial de microempresa Deficiente."
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
  const [useAdaptivePractice, setUseAdaptivePractice] = useState(true);
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
  const hasPendingExample = useMemo(
    () =>
      mode === "ejemplifica" &&
      messages.some(
        (item) =>
          item.role === "assistant" &&
          item.kind === "example" &&
          !item.feedback
      ),
    [messages, mode]
  );
  const hasOpenSimulation = useMemo(
    () =>
      mode === "simulacion" &&
      messages.some(
        (item) =>
          item.role === "assistant" &&
          item.kind === "simulation" &&
          item.simulation.data.state !== "closed"
      ),
    [messages, mode]
  );

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
      if (mode === "ejemplifica") {
        return generateExample(input, useLlmVariation, userKey, useAdaptivePractice);
      }
      return startSimulation(input, userKey);
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
      if (response.type === "example") {
        appendAssistant({
          kind: "example",
          example: response
        });
        return;
      }
      appendAssistant({
        kind: "simulation",
        simulation: response
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
      | Omit<AssistantSimulationMessage, "id" | "role">
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
      const result = await answerExample(
        target.example.data.case_id,
        category,
        userKey
      );
      updateActiveMessages((current) =>
        current.map((item) =>
          item.id === messageId && item.role === "assistant" && item.kind === "example"
            ? {
                ...item,
                feedback: {
                  correct: result.data.correct,
                  correctCategory: result.data.correct_category,
                  text: result.data.feedback,
                  targetConcept: result.data.target_concept,
                  masteryBefore: result.data.mastery_before,
                  masteryAfter: result.data.mastery_after,
                  nextConcept: result.data.next_concept,
                  recommendation: result.data.recommendation
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

  async function submitSimulationClassification(
    messageId: string,
    category: string,
    justification: string
  ) {
    const target = messages.find(
      (item): item is AssistantSimulationMessage =>
        item.id === messageId &&
        item.role === "assistant" &&
        item.kind === "simulation"
    );
    if (!target) {
      return;
    }

    setAnsweringIds((current) => new Set(current).add(messageId));
    try {
      const result = await classifySimulation(
        target.simulation.data.id,
        category,
        justification
      );
      updateSimulationMessage(messageId, result);
    } finally {
      setAnsweringIds((current) => {
        const next = new Set(current);
        next.delete(messageId);
        return next;
      });
    }
  }

  async function submitSimulationDefense(messageId: string, defense: string) {
    const target = messages.find(
      (item): item is AssistantSimulationMessage =>
        item.id === messageId &&
        item.role === "assistant" &&
        item.kind === "simulation"
    );
    if (!target) {
      return;
    }

    setAnsweringIds((current) => new Set(current).add(messageId));
    try {
      const result = await advanceSimulationTurn(target.simulation.data.id, defense);
      updateSimulationMessage(messageId, result);
    } finally {
      setAnsweringIds((current) => {
        const next = new Set(current);
        next.delete(messageId);
        return next;
      });
    }
  }

  function updateSimulationMessage(messageId: string, simulation: SimulationResponse) {
    updateActiveMessages((current) =>
      current.map((item) =>
        item.id === messageId &&
        item.role === "assistant" &&
        item.kind === "simulation"
          ? { ...item, simulation }
          : item
      )
    );
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
    if (mode === "ejemplifica" && hasPendingExample) {
      appendAssistant({
        kind: "text",
        text: "Primero selecciona una categor\u00eda y valida el caso pendiente. Despu\u00e9s te puedo generar otro ejemplo adaptativo.",
        citations: []
      });
      return;
    }
    if (mode === "simulacion" && hasOpenSimulation) {
      appendAssistant({
        kind: "text",
        text: "Primero cierra la simulacion adversarial actual: clasifica, defiende tu criterio y espera el veredicto del juez.",
        citations: []
      });
      return;
    }
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
            <button
              className={mode === "simulacion" ? "active" : ""}
              type="button"
              onClick={() => handleModeChange("simulacion")}
            >
              Simulacion
            </button>
          </div>

          {mode === "ejemplifica" ? (
            <div className="toolbar-checks">
              <label className="inline-check">
                <input
                  checked={useAdaptivePractice}
                  type="checkbox"
                  onChange={(event) =>
                    setUseAdaptivePractice(event.target.checked)
                  }
                />
                Practica adaptativa
              </label>
              <label className="inline-check">
                <input
                  checked={useLlmVariation}
                  type="checkbox"
                  onChange={(event) => setUseLlmVariation(event.target.checked)}
                />
                Variar narrativa
              </label>
            </div>
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
              onSimulationClassify={submitSimulationClassification}
              onSimulationDefend={submitSimulationDefense}
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
                : mode === "ejemplifica"
                  ? "Pide un caso para practicar..."
                  : "Pide una simulacion adversarial..."
            }
          />
          <button disabled={sendMessage.isPending || !message.trim()} type="submit">
            {mode === "ejemplifica" ? (
              <Sparkles aria-hidden="true" size={18} />
            ) : mode === "simulacion" ? (
              <Gavel aria-hidden="true" size={18} />
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
  onAnswer,
  onSimulationClassify,
  onSimulationDefend
}: {
  message: ChatMessage;
  isAnswering: boolean;
  onAnswer: (messageId: string, category: string) => void;
  onSimulationClassify: (
    messageId: string,
    category: string,
    justification: string
  ) => void;
  onSimulationDefend: (messageId: string, defense: string) => void;
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
        ) : message.kind === "example" ? (
          <ExampleAnswer
            message={message}
            isAnswering={isAnswering}
            onAnswer={onAnswer}
          />
        ) : (
          <SimulationAnswer
            message={message}
            isAnswering={isAnswering}
            onClassify={onSimulationClassify}
            onDefend={onSimulationDefend}
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
      {message.example.data.adaptive ? (
        <p className="adaptive-note">
          Objetivo adaptativo: {formatConcept(message.example.data.target_concept)}
          {message.example.data.mastery_score !== null
            ? ` · dominio ${formatPercent(message.example.data.mastery_score)}`
            : ""}
        </p>
      ) : null}
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
          {message.feedback.recommendation ? (
            <div className="adaptive-feedback">
              <span>
                Dominio:{" "}
                {formatPercent(message.feedback.masteryBefore)}
                {" -> "}
                {formatPercent(message.feedback.masteryAfter)}
              </span>
              <span>{message.feedback.recommendation}</span>
              {message.feedback.nextConcept ? (
                <small>
                  Siguiente foco: {formatConcept(message.feedback.nextConcept)}
                </small>
              ) : null}
            </div>
          ) : null}
        </article>
      ) : null}
    </div>
  );
}

function SimulationAnswer({
  message,
  isAnswering,
  onClassify,
  onDefend
}: {
  message: AssistantSimulationMessage;
  isAnswering: boolean;
  onClassify: (messageId: string, category: string, justification: string) => void;
  onDefend: (messageId: string, defense: string) => void;
}) {
  const [category, setCategory] = useState("");
  const [justification, setJustification] = useState("");
  const [defense, setDefense] = useState("");
  const simulation = message.simulation.data;
  const canClassify = simulation.state === "classify";
  const canDefend = simulation.state === "defend";

  return (
    <div className="simulation-message">
      <div className="simulation-header">
        <span>Simulacion adversarial</span>
        <strong>{simulation.state}</strong>
      </div>

      <div className="simulation-case">
        <p className="source-note">
          Cartera {formatConcept(simulation.case.cartera_type)} · caso{" "}
          {formatConcept(simulation.case.case_type)}
        </p>
        <div className="case-grid">
          {Object.entries(simulation.case.debtor_profile).map(([key, value]) => (
            <div key={key}>
              <span>{formatLabel(key)}</span>
              <strong>{String(value)}</strong>
            </div>
          ))}
        </div>
      </div>

      <div className="simulation-transcript">
        {simulation.transcript.map((turn, index) => (
          <article className={`simulation-turn ${turn.role}`} key={`${turn.role}-${index}`}>
            <span>{roleLabel(turn.role)}</span>
            <p>{turn.content}</p>
            {turn.metadata.cited_articles ? (
              <small>
                Citas: {String((turn.metadata.cited_articles as string[]).join(", "))}
              </small>
            ) : null}
          </article>
        ))}
      </div>

      {canClassify ? (
        <div className="simulation-form">
          <label>
            Categoria que defenderas
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              <option value="">Selecciona categoria</option>
              {riskCategoryOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label>
            Justificacion inicial
            <textarea
              rows={3}
              value={justification}
              onChange={(event) => setJustification(event.target.value)}
              placeholder="Sustenta tu criterio con dias de atraso, tipo de cartera o articulo aplicable..."
            />
          </label>
          <button
            disabled={!category || !justification.trim() || isAnswering}
            type="button"
            onClick={() => onClassify(message.id, category, justification.trim())}
          >
            <Gavel aria-hidden="true" size={18} />
            Defender criterio
          </button>
        </div>
      ) : null}

      {canDefend ? (
        <div className="simulation-form">
          <label>
            Defensa ante Supervisor y Banco
            <textarea
              rows={3}
              value={defense}
              onChange={(event) => setDefense(event.target.value)}
              placeholder="Responde la objecion, corrige si hace falta y cita el criterio normativo..."
            />
          </label>
          <button
            disabled={!defense.trim() || isAnswering}
            type="button"
            onClick={() => onDefend(message.id, defense.trim())}
          >
            <Send aria-hidden="true" size={18} />
            Enviar defensa
          </button>
        </div>
      ) : null}

      {simulation.verdict ? (
        <article className="simulation-verdict">
          <strong>Veredicto del juez</strong>
          <p>{simulation.verdict.feedback}</p>
          <div>
            <span>Categoria final: {simulation.verdict.final_category}</span>
            <span>Resultado: {formatPercent(simulation.verdict.overall)}</span>
          </div>
          {simulation.case.ground_truth ? (
            <small>
              Verdad de fondo: {simulation.case.ground_truth.category} ·{" "}
              {simulation.case.justifying_articles?.join(", ")}
            </small>
          ) : null}
        </article>
      ) : null}
    </div>
  );
}

const riskCategoryOptions = [
  "Normal",
  "CPP",
  "Deficiente",
  "Dudoso",
  "Perdida"
];

function roleLabel(role: string): string {
  return (
    {
      alumno: "Alumno",
      banco: "Banco",
      cliente: "Cliente",
      juez: "Juez",
      supervisor: "Supervisor SBS"
    }[role] ?? role
  );
}

function modeLabel(mode: ChatMode): string {
  if (mode === "explicame") {
    return "Explicame";
  }
  if (mode === "ejemplifica") {
    return "Ejemplifica";
  }
  return "Simulacion";
}

function formatLabel(value: string): string {
  return value.replaceAll("_", " ");
}

function formatConcept(value: string | null): string {
  if (!value) {
    return "concepto inicial";
  }
  return value.replaceAll("_", " ");
}

function formatPercent(value: number | null): string {
  if (value === null) {
    return "--";
  }
  return `${Math.round(value * 100)}%`;
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
