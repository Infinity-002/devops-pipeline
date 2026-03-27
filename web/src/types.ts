export type TaskType = "image_processing" | "csv_analysis";

export type TaskStatus = "queued" | "running" | "completed" | "failed";

export type ImageTransform = "thumbnail" | "grayscale" | "sepia" | "blur" | "edge_enhance";

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

export interface ImageOutput {
  key: ImageTransform;
  label: string;
  description: string;
  width: number;
  height: number;
  image_data_url: string;
}

export interface ImageProcessingResult {
  filename: string;
  original: {
    format: string;
    width: number;
    height: number;
    size_bytes: number;
    aspect_ratio: number | null;
    image_data_url: string;
  };
  transforms: ImageTransform[];
  outputs: ImageOutput[];
}

export interface CsvAnalysisResult {
  row_count: number;
  column_count: number;
  columns: string[];
  numeric_summary: Record<string, { count: number; min: number; max: number; average: number }>;
  bar_chart?: {
    kind?: "grouped" | "columns";
    metric: "average";
    columns?: Array<{ column: string; value: number }>;
    x_axis?: string;
    series?: string[];
    groups?: Array<{ flower: string; averages: Record<string, number> }>;
  };
  sample_rows: Array<Record<string, unknown>>;
}
