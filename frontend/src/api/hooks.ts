import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "./client";
import type {
  Blueprint,
  Feedback,
  MockAnswerAck,
  MockQuestion,
  MockReport,
  MockState,
  PracticeSet,
  Progress,
  Question,
  QuestionDetail,
  QuestionPage,
  Report,
  TaskResponse,
  TaskType,
  TypeSummary,
  User,
} from "./types";

export function useMe() {
  return useQuery<User | null>({
    queryKey: ["me"],
    queryFn: async () => {
      try {
        return await api<User>("/me");
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    staleTime: 60_000,
  });
}

export function useSignIn() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; password: string }) => api<User>("/auth/signin", { method: "POST", body }),
    onSuccess: (user) => {
      client.clear();
      client.setQueryData(["me"], user);
    },
  });
}

export function useSignUp() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; password: string; display_name: string }) =>
      api<User>("/auth/signup", { method: "POST", body }),
    onSuccess: (user) => {
      client.clear();
      client.setQueryData(["me"], user);
    },
  });
}

export function useSignOut() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<void>("/auth/signout", { method: "POST" }),
    onSuccess: () => {
      client.clear();
      client.setQueryData(["me"], null);
    },
  });
}

export function useTaskTypes() {
  return useQuery<TaskType[]>({ queryKey: ["task-types"], queryFn: () => api("/task-types"), staleTime: Infinity });
}

export function useProgress(enabled = true) {
  return useQuery<Progress>({ queryKey: ["progress"], queryFn: () => api("/me/progress"), enabled });
}

export function useStartSet() {
  return useMutation({
    mutationFn: (taskType: string) => api<PracticeSet>("/sets", { method: "POST", body: { task_type: taskType } }),
  });
}

export function useSet(setId: number) {
  return useQuery<PracticeSet>({ queryKey: ["set", setId], queryFn: () => api(`/sets/${setId}`) });
}

export function useQuestion(setId: number, position: number) {
  return useQuery<Question>({
    queryKey: ["set", setId, "question", position],
    queryFn: () => api(`/sets/${setId}/questions/${position}`),
    staleTime: Infinity,
    enabled: position > 0,
  });
}

export function useAnswer(setId: number, position: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (response: TaskResponse) =>
      api<Question>(`/sets/${setId}/questions/${position}/answer`, { method: "POST", body: { response } }),
    onSuccess: (question) => {
      client.setQueryData(["set", setId, "question", position], question);
      client.invalidateQueries({ queryKey: ["set", setId], exact: true });
    },
  });
}

export function useFinishSet(setId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<PracticeSet>(`/sets/${setId}/finish`, { method: "POST" }),
    onSuccess: (set) => {
      client.setQueryData(["set", setId], set);
      client.invalidateQueries({ queryKey: ["progress"] });
    },
  });
}

export function useReview(setId: number) {
  return useQuery<Question[]>({ queryKey: ["set", setId, "review"], queryFn: () => api(`/sets/${setId}/review`) });
}

export function useFeedback(setQuestionId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<Feedback>(`/set-questions/${setQuestionId}/feedback`, { method: "POST" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["set"] }),
  });
}

export function useReport(questionId: number) {
  return useMutation({
    mutationFn: (reason: string) =>
      api<{ message: string }>(`/questions/${questionId}/report`, { method: "POST", body: { reason } }),
  });
}

// Admin

export function useAdminSummary() {
  return useQuery<TypeSummary[]>({ queryKey: ["admin", "summary"], queryFn: () => api("/admin/summary") });
}

export interface QuestionFilters {
  task_type?: string;
  status?: string;
  reported?: boolean;
  search?: string;
  page: number;
}

export function useAdminQuestions(filters: QuestionFilters) {
  const params = new URLSearchParams();
  if (filters.task_type) params.set("task_type", filters.task_type);
  if (filters.status) params.set("status", filters.status);
  if (filters.reported) params.set("reported", "true");
  if (filters.search) params.set("search", filters.search);
  params.set("page", String(filters.page));
  return useQuery<QuestionPage>({
    queryKey: ["admin", "questions", filters],
    queryFn: () => api(`/admin/questions?${params.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useAdminQuestion(id: number) {
  return useQuery<QuestionDetail>({ queryKey: ["admin", "question", id], queryFn: () => api(`/admin/questions/${id}`) });
}

export function useUpdateQuestion(id: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { payload?: Record<string, unknown>; status?: string; difficulty?: number }) =>
      api<QuestionDetail>(`/admin/questions/${id}`, { method: "PATCH", body }),
    onSuccess: (question) => {
      client.setQueryData(["admin", "question", id], question);
      client.invalidateQueries({ queryKey: ["admin", "summary"] });
      client.invalidateQueries({ queryKey: ["admin", "questions"] });
    },
  });
}

export function usePromoteBackup() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (code: string) => api<QuestionDetail>(`/admin/task-types/${code}/promote`, { method: "POST", body: {} }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["admin"] }),
  });
}

export function useResolveReport() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (reportId: number) => api<Report>(`/admin/reports/${reportId}/resolve`, { method: "POST" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["admin"] }),
  });
}

// --- Full mock test ---

export function useBlueprint() {
  return useQuery<Blueprint>({ queryKey: ["mock", "blueprint"], queryFn: () => api("/mock-tests/blueprint"), staleTime: Infinity });
}

export function useStartMock() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<MockState>("/mock-tests", { method: "POST" }),
    onSuccess: (state) => client.setQueryData(["mock", state.id], state),
  });
}

export function useMockState(setId: number, enabled = true) {
  return useQuery<MockState>({ queryKey: ["mock", setId], queryFn: () => api(`/mock-tests/${setId}`), enabled });
}

export function useMockQuestion(setId: number, position: number) {
  return useQuery<MockQuestion>({
    queryKey: ["mock", setId, "question", position],
    queryFn: () => api(`/mock-tests/${setId}/questions/${position}`),
    enabled: position > 0,
    staleTime: Infinity,
    retry: false,
  });
}

export function useMockAnswer(setId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ position, response }: { position: number; response: TaskResponse }) =>
      api<MockAnswerAck>(`/mock-tests/${setId}/questions/${position}/answer`, { method: "POST", body: { response } }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["mock", setId], exact: true }),
  });
}

export function useSubmitMock(setId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<MockReport>(`/mock-tests/${setId}/submit`, { method: "POST" }),
    onSuccess: (report) => {
      client.setQueryData(["mock", setId, "report"], report);
      client.invalidateQueries({ queryKey: ["mock", setId], exact: true });
      client.invalidateQueries({ queryKey: ["progress"] });
    },
  });
}

export function useMockReport(setId: number, enabled = true) {
  return useQuery<MockReport>({
    queryKey: ["mock", setId, "report"],
    queryFn: () => api(`/mock-tests/${setId}/report`),
    enabled,
  });
}
