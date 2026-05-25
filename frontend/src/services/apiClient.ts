import axios from "axios";

import type {
  ExampleFeedbackResponse,
  ExampleResponse,
  ExplainResponse
} from "../shared/apiTypes";
import { firebaseAuth } from "./firebase";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    "Content-Type": "application/json"
  }
});

apiClient.interceptors.request.use(async (config) => {
  const token = await firebaseAuth?.currentUser?.getIdToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function explainQuestion(question: string): Promise<ExplainResponse> {
  const response = await apiClient.post<ExplainResponse>("/modes/explain", {
    question,
    student_id: null
  });
  return response.data;
}

export async function generateExample(
  concept: string,
  useLlmVariation: boolean
): Promise<ExampleResponse> {
  const response = await apiClient.post<ExampleResponse>("/modes/example/generate", {
    concept,
    student_id: null,
    use_llm_variation: useLlmVariation
  });
  return response.data;
}

export async function answerExample(
  caseId: string,
  selectedCategory: string
): Promise<ExampleFeedbackResponse> {
  const response = await apiClient.post<ExampleFeedbackResponse>(
    "/modes/example/answer",
    {
      case_id: caseId,
      selected_category: selectedCategory,
      student_id: null
    }
  );
  return response.data;
}
