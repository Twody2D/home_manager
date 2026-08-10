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

export type CalendarEventType =
  | "working_hours"
  | "sleep"
  | "meeting"
  | "sport"
  | "trip"
  | "personal"
  | "unavailable";

export interface CalendarEvent {
  id: string;
  tenant_id: string;
  user_id: string;
  event_type: CalendarEventType;
  title: string;
  description: string | null;
  start_at: string;
  end_at: string;
  all_day: boolean;
  location: string | null;
  recurrence: string | null;
  created_at: string;
  updated_at: string;
}

export interface CalendarEventCreateInput {
  event_type: CalendarEventType;
  title: string;
  description?: string | null;
  start_at: string;
  end_at: string;
  all_day?: boolean;
  location?: string | null;
  recurrence?: string | null;
}

export type CalendarEventUpdateInput = Partial<CalendarEventCreateInput>;

export interface CalendarEventBulkCreateInput {
  events: CalendarEventCreateInput[];
}

export type EnergyPattern = "morning" | "evening" | "steady";

export interface UserPreferences {
  id: string;
  tenant_id: string;
  user_id: string;
  working_hours_start: string | null;
  working_hours_end: string | null;
  sleep_start: string | null;
  sleep_end: string | null;
  preferred_categories: string[];
  disliked_categories: string[];
  energy_pattern: EnergyPattern;
  task_speed_multiplier: number;
  notes: string | null;
}

export type UserPreferencesUpdateInput = Partial<
  Omit<UserPreferences, "id" | "tenant_id" | "user_id">
>;

export interface ScheduledTaskEntry {
  task_id: string;
  title: string;
  priority: TaskPriority;
  start_at: string;
  end_at: string;
  score: number;
}

export interface UnscheduledTaskEntry {
  task_id: string;
  title: string;
  priority: TaskPriority;
  reason: string;
}

export interface DailyPlanResponse {
  date: string;
  scheduled: ScheduledTaskEntry[];
  unscheduled: UnscheduledTaskEntry[];
}

export interface AssistantReply {
  reply: string;
  task_id: string | null;
}

export type SmartHomeCommand = "turn_on" | "turn_off" | "toggle";

export interface SmartHomeDevice {
  entity_id: string;
  name: string;
  domain: string;
  state: string;
  is_on: boolean;
}
