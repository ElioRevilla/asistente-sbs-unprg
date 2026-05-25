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
  };
};

export type ExampleFeedbackResponse = {
  type: "example_feedback";
  data: {
    correct: boolean;
    correct_category: string;
    feedback: string;
    source_article: string;
  };
};
