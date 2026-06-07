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

export type ChatConversationDto = {
  id: string;
  title: string;
  mode: "explicame" | "ejemplifica";
  messages: Record<string, unknown>[];
  created_at: string;
  updated_at: string;
};

export type ChatConversationListResponse = {
  conversations: ChatConversationDto[];
};
