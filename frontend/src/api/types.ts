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
  // Defaults to the creator on the backend. Set to another household
  // member's id to put the same event on their calendar too.
  user_id?: string | null;
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
  workplace: string | null;
  working_hours_start: string | null;
  working_hours_end: string | null;
  sleep_start: string | null;
  sleep_end: string | null;
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
  proposed_events: CalendarEventCreateInput[] | null;
}

export interface InviteLink {
  token: string;
  expires_at: string;
}

export interface Household {
  name: string;
  display_name: string | null;
}

export interface InvitePreview {
  household_name: string;
  expires_at: string;
}

export interface Income {
  id: string;
  tenant_id: string;
  user_id: string;
  label: string;
  amount: string;
  payment_day: number;
  created_at: string;
  updated_at: string;
}

export interface IncomeCreateInput {
  user_id?: string | null;
  label: string;
  amount: string;
  payment_day: number;
}

export type IncomeUpdateInput = Partial<IncomeCreateInput>;

export interface IncomeListResponse {
  items: Income[];
  total: number;
  limit: number;
  offset: number;
}

export type SubscriptionCadence = "monthly" | "yearly";
export type SubscriptionKind = "subscription" | "recurring_expense";

export interface Subscription {
  id: string;
  tenant_id: string;
  name: string;
  amount: string;
  kind: SubscriptionKind;
  cadence: SubscriptionCadence;
  payment_day: number;
  payment_month: number | null;
  owner_user_id: string | null;
  active: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionCreateInput {
  name: string;
  amount: string;
  kind?: SubscriptionKind;
  cadence?: SubscriptionCadence;
  payment_day: number;
  payment_month?: number | null;
  owner_user_id?: string | null;
}

export type SubscriptionUpdateInput = Partial<SubscriptionCreateInput> & { active?: boolean };

export interface SubscriptionListResponse {
  items: Subscription[];
  total: number;
  limit: number;
  offset: number;
}

export type SmartHomeCommand = "turn_on" | "turn_off" | "toggle";

export interface SmartHomeDevice {
  entity_id: string;
  name: string;
  domain: string;
  state: string;
  is_on: boolean;
}
