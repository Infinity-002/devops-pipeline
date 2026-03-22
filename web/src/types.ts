export type TaskType = "image_processing" | "csv_analysis";

export type TaskStatus = "queued" | "running" | "completed" | "failed";

export interface Task {
  id: string;
  task_type: TaskType;
  status: TaskStatus;
  payload: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateTaskResponse {
  task_id: string;
  status: "queued";
}
