import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// --- Types ---

export interface Student {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  created_at: string;
}

export interface Test {
  id: string;
  name: string;
  max_marks: number;
  negative_marking: Record<string, number>;
}

export interface AttemptScore {
  attempt_id: string;
  correct: number;
  wrong: number;
  skipped: number;
  accuracy: number;
  net_correct: number;
  score: number;
  computed_at: string;
  explanation: Record<string, unknown> | null;
}

export interface Flag {
  id: string;
  attempt_id: string;
  reason: string;
  created_at: string;
}

export interface Attempt {
  id: string;
  student_id: string;
  test_id: string;
  source_event_id: string;
  started_at: string;
  submitted_at: string | null;
  answers: Record<string, string>;
  status: string;
  duplicate_of_attempt_id: string | null;
  student?: Student;
  test?: Test;
  score?: AttemptScore | null;
  flags?: Flag[];
}

export interface AttemptListResponse {
  items: Attempt[];
  total: number;
  page: number;
  page_size: number;
}

export interface LeaderboardEntry {
  rank: number;
  student_id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  attempt_id: string;
  score: number;
  accuracy: number;
  net_correct: number;
  correct: number;
  wrong: number;
  skipped: number;
  submitted_at: string | null;
}

export interface LeaderboardResponse {
  test_id: string;
  test_name: string;
  entries: LeaderboardEntry[];
}

export interface IngestResponse {
  ingested: number;
  duplicates: number;
  errors: number;
  results: Array<{
    source_event_id: string;
    attempt_id: string | null;
    status: string;
    message: string;
  }>;
}

// --- API calls ---

export async function fetchAttempts(params: {
  page?: number;
  page_size?: number;
  test_id?: string;
  student_id?: string;
  status?: string;
  has_duplicates?: boolean;
  search?: string;
  date_from?: string;
  date_to?: string;
}): Promise<AttemptListResponse> {
  const { data } = await api.get('/api/attempts', { params });
  return data;
}

export async function fetchAttempt(id: string): Promise<Attempt> {
  const { data } = await api.get(`/api/attempts/${id}`);
  return data;
}

export async function fetchDuplicateThread(id: string): Promise<{
  canonical: Attempt;
  duplicates: Attempt[];
}> {
  const { data } = await api.get(`/api/attempts/${id}/duplicates`);
  return data;
}

export async function recomputeScore(id: string): Promise<AttemptScore> {
  const { data } = await api.post(`/api/attempts/${id}/recompute`);
  return data;
}

export async function flagAttempt(id: string, reason: string): Promise<Flag> {
  const { data } = await api.post(`/api/attempts/${id}/flag`, { reason });
  return data;
}

export async function fetchTests(): Promise<Test[]> {
  const { data } = await api.get('/api/tests');
  return data;
}

export async function fetchLeaderboard(testId: string): Promise<LeaderboardResponse> {
  const { data } = await api.get('/api/leaderboard', { params: { test_id: testId } });
  return data;
}

export async function ingestAttempts(events: unknown[]): Promise<IngestResponse> {
  const { data } = await api.post('/api/ingest/attempts', { events });
  return data;
}

export default api;
