export type Role = "owner" | "member";

export interface User {
  id: string;
  tenant_id: string;
  email: string;
  display_name: string;
  role: Role;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export type TaskStatus =
  | "pending"
  | "scheduled"
  | "in_progress"
  | "completed"
  | "cancelled"
  | "postponed";

export type TaskPriority = "low" | "medium" | "high" | "urgent";

export interface Task {
  id: string;
  tenant_id: string;
  created_by: string | null;
  assigned_to: string | null;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  duration_minutes: number | null;
  due_at: string | null;
  preferred_start: string | null;
  preferred_end: string | null;
  location: string | null;
  recurrence: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface TaskListResponse {
  items: Task[];
  total: number;
  limit: number;
  offset: number;
}

export interface TaskCreateInput {
  title: string;
  description?: string | null;
  assigned_to?: string | null;
  priority?: TaskPriority;
  duration_minutes?: number | null;
  due_at?: string | null;
  preferred_start?: string | null;
  preferred_end?: string | null;
  location?: string | null;
  recurrence?: string | null;
}

export type TaskUpdateInput = Partial<TaskCreateInput> & { status?: TaskStatus };

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    request_id: string | null;
  };
}
