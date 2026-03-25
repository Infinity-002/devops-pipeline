import type { CreateTaskResponse, Task, TaskType } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

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
    throw new Error(await getErrorMessage(response, "Failed to create task"));
  }

  return (await response.json()) as CreateTaskResponse;
}

export async function listTasks() {
  const response = await fetch(`${API_BASE_URL}/api/v1/tasks`);
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Failed to load tasks"));
  }
  return (await response.json()) as Task[];
}

async function getErrorMessage(response: Response, fallback: string) {
  try {
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const json = (await response.json()) as { detail?: string; message?: string };
      if (json.detail) {
        return `${fallback}: ${json.detail}`;
      }
      if (json.message) {
        return `${fallback}: ${json.message}`;
      }
    } else {
      const text = (await response.text()).trim();
      if (text) {
        return `${fallback}: ${text}`;
      }
    }
  } catch {
    return `${fallback} (${response.status})`;
  }

  return `${fallback} (${response.status})`;
}
