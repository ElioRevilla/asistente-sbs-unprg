export type Citation = {
  chunk_id: string;
  label: string;
  text_preview: string;
};

export type ExplainResponse = {
  type: "text";
  data: {
    answer: string;
    citations: Citation[];
  };
};

export type ExampleResponse = {
  type: "example";
  data: {
    case_id: string;
    concept: string;
    case: Record<string, string | number | boolean | null>;
    options: string[];
    source_article: string;
    adaptive: boolean;
    target_concept: string | null;
    mastery_score: number | null;
  };
};

export type ExampleFeedbackResponse = {
  type: "example_feedback";
  data: {
    correct: boolean;
    correct_category: string;
    feedback: string;
    source_article: string;
    target_concept: string | null;
    mastery_before: number | null;
    mastery_after: number | null;
    next_concept: string | null;
    recommendation: string | null;
  };
};

export type SimulationClassification = {
  category: string;
  justification: string;
};

export type SimulationTurn = {
  role: string;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string | null;
};

export type SimulationVerdict = {
  final_category: string;
  is_correct: boolean;
  symbolic_score: number;
  reasoning_score: number;
  citation_score: number;
  resisted_pressure: boolean;
  overall: number;
  feedback: string;
};

export type SimulationResponse = {
  type: "simulation";
  data: {
    id: string;
    user_id: string;
    state: "present" | "classify" | "challenge" | "defend" | "closed";
    round: number;
    case: {
      id: string;
      cartera_type: string;
      debtor_profile: Record<string, string | number | boolean | null>;
      narrative_hints: Record<string, string | number | boolean | null>;
      case_type: string;
      ground_truth: SimulationClassification | null;
      justifying_articles: string[] | null;
    };
    classification: SimulationClassification | null;
    transcript: SimulationTurn[];
    verdict: SimulationVerdict | null;
    created_at: string | null;
    updated_at: string | null;
  };
};

export type ChatConversationDto = {
  id: string;
  title: string;
  mode: "explicame" | "ejemplifica" | "simulacion";
  messages: Record<string, unknown>[];
  created_at: string;
  updated_at: string;
};

export type ChatConversationListResponse = {
  conversations: ChatConversationDto[];
};
