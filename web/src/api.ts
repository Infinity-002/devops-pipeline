import type { CreateTaskResponse, Task, TaskType } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function createTask(taskType: TaskType, payload: Record<string, unknown>) {
  const response = await fetch(`${API_BASE_URL}/api/v1/tasks`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      task_type: taskType,
      payload,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to create task");
  }

  return (await response.json()) as CreateTaskResponse;
}

export async function listTasks() {
  const response = await fetch(`${API_BASE_URL}/api/v1/tasks`);
  if (!response.ok) {
    throw new Error("Failed to load tasks");
  }
  return (await response.json()) as Task[];
}

