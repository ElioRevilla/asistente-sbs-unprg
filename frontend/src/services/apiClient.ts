import axios from "axios";

import type {
  ChatConversationDto,
  ChatConversationListResponse,
  ExampleFeedbackResponse,
  ExampleResponse,
  ExplainResponse,
  SimulationResponse,
  TeacherConceptAnalytics,
  TeacherOverview,
  TeacherStudentAnalytics,
  TeacherStudentSummary
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
  useLlmVariation: boolean,
  studentId: string | null,
  adaptive: boolean
): Promise<ExampleResponse> {
  const response = await apiClient.post<ExampleResponse>("/modes/example/generate", {
    concept,
    student_id: studentId,
    use_llm_variation: useLlmVariation,
    adaptive
  });
  return response.data;
}

export async function answerExample(
  caseId: string,
  selectedCategory: string,
  studentId: string | null
): Promise<ExampleFeedbackResponse> {
  const response = await apiClient.post<ExampleFeedbackResponse>(
    "/modes/example/answer",
    {
      case_id: caseId,
      selected_category: selectedCategory,
      student_id: studentId
    }
  );
  return response.data;
}

export async function startSimulation(
  focus: string,
  studentId: string | null
): Promise<SimulationResponse> {
  const response = await apiClient.post<SimulationResponse>(
    "/modes/simulation/start",
    {
      focus,
      student_id: studentId
    }
  );
  return response.data;
}

export async function classifySimulation(
  sessionId: string,
  category: string,
  justification: string
): Promise<SimulationResponse> {
  const response = await apiClient.post<SimulationResponse>(
    `/modes/simulation/${sessionId}/classify`,
    {
      category,
      justification
    }
  );
  return response.data;
}

export async function advanceSimulationTurn(
  sessionId: string,
  defense: string
): Promise<SimulationResponse> {
  const response = await apiClient.post<SimulationResponse>(
    `/modes/simulation/${sessionId}/turn`,
    {
      defense
    }
  );
  return response.data;
}

export async function listConversations(): Promise<ChatConversationDto[]> {
  const response = await apiClient.get<ChatConversationListResponse>(
    "/chat/conversations"
  );
  return response.data.conversations;
}

export async function saveConversation(
  conversation: Pick<ChatConversationDto, "id" | "title" | "mode" | "messages">
): Promise<ChatConversationDto> {
  const response = await apiClient.put<ChatConversationDto>(
    `/chat/conversations/${conversation.id}`,
    {
      title: conversation.title,
      mode: conversation.mode,
      messages: conversation.messages
    }
  );
  return response.data;
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await apiClient.delete(`/chat/conversations/${conversationId}`);
}

export async function fetchTeacherOverview(): Promise<TeacherOverview> {
  const response = await apiClient.get<TeacherOverview>("/teacher/overview");
  return response.data;
}

export async function fetchTeacherStudents(): Promise<TeacherStudentSummary[]> {
  const response = await apiClient.get<{ students: TeacherStudentSummary[] }>(
    "/teacher/students"
  );
  return response.data.students;
}

export async function fetchTeacherStudentAnalytics(
  studentId: string
): Promise<TeacherStudentAnalytics> {
  const response = await apiClient.get<TeacherStudentAnalytics>(
    `/teacher/students/${studentId}/analytics`
  );
  return response.data;
}

export async function fetchTeacherConcepts(): Promise<TeacherConceptAnalytics> {
  const response = await apiClient.get<TeacherConceptAnalytics>(
    "/teacher/concepts"
  );
  return response.data;
}

export async function downloadTeacherAnalyticsCsv(): Promise<Blob> {
  const response = await apiClient.get<Blob>("/teacher/export.csv", {
    responseType: "blob"
  });
  return response.data;
}
