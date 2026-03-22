import { FormEvent, useEffect, useMemo, useState } from "react";

import { createTask, listTasks } from "./api";
import type { Task, TaskType } from "./types";

const TASK_OPTIONS: Array<{ value: TaskType; label: string; help: string }> = [
  {
    value: "image_processing",
    label: "Image Processing",
    help: "Generate a thumbnail, grayscale preview, and basic image metadata.",
  },
  {
    value: "csv_analysis",
    label: "CSV Analysis",
    help: "Inspect uploaded CSV content and produce structural and numeric summaries.",
  },
];

export function App() {
  const [taskType, setTaskType] = useState<TaskType>("image_processing");
  const [imageName, setImageName] = useState("sample-image.png");
  const [imageDataUrl, setImageDataUrl] = useState<string | null>(null);
  const [csvFilename] = useState("sales-report.csv");
  const [csvText, setCsvText] = useState(
    "name,amount,region\nAsha,120,North\nRavi,95,South\nMina,210,West\nKabir,,East",
  );
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshTasks() {
    try {
      const nextTasks = await listTasks();
      setTasks(nextTasks);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Unable to load tasks");
    }
  }

  useEffect(() => {
    void refreshTasks();
    const timer = window.setInterval(() => {
      void refreshTasks();
    }, 3000);

    return () => window.clearInterval(timer);
  }, []);

  const selectedTask = useMemo(
    () => TASK_OPTIONS.find((option) => option.value === taskType) ?? TASK_OPTIONS[0],
    [taskType],
  );

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const payload =
        taskType === "image_processing"
          ? {
            filename: imageName,
            image_data_url: imageDataUrl,
          }
          : {
            filename: csvFilename,
            csv_text: csvText,
          };

      if (taskType === "image_processing" && !imageDataUrl) {
        throw new Error("Please choose an image file before submitting");
      }

      await createTask(taskType, payload);
      await refreshTasks();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Task submission failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="page-shell">
      <header className="hero-card">
        <div className="eyebrow">Cloud Processor</div>
        <h1>Effortless file processing.</h1>
        <p>
          Upload an image or CSV and get instant results.
        </p>
      </header>

      <main className="panel form-panel">
        <div className="panel-header">
          <h2>New Task</h2>
          <span>{selectedTask.help}</span>
        </div>

        <form onSubmit={onSubmit}>
          <label>
            Task Type
            <select value={taskType} onChange={(event) => setTaskType(event.target.value as TaskType)}>
              {TASK_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          {taskType === "image_processing" ? (
            <>
              <label>
                Image File
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={async (event) => {
                    const file = event.target.files?.[0];
                    if (!file) {
                      setImageDataUrl(null);
                      return;
                    }

                    setImageName(file.name);
                    const dataUrl = await readFileAsDataUrl(file);
                    setImageDataUrl(dataUrl);
                  }}
                />
              </label>

              {imageDataUrl ? <img className="preview-image" src={imageDataUrl} alt="Selected preview" /> : null}
            </>
          ) : (
            <>
              <label>
                CSV Data
                <textarea
                  rows={8}
                  value={csvText}
                  onChange={(event) => setCsvText(event.target.value)}
                  placeholder="name,amount,region&#10;Asha,120,North"
                />
              </label>
            </>
          )}

          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Processing..." : "Run Task"}
          </button>

          {error ? <p className="error-text">{error}</p> : null}
        </form>
      </main>

      <section className="task-list">
        {tasks.length === 0 ? (
          <div className="empty-state">No tasks yet. Your results will appear here.</div>
        ) : (
          tasks.map((task) => (
            <article key={task.id} className="task-card">
              <div className="task-topline">
                <span className={`status-badge status-${task.status}`}>{task.status}</span>
                <code>{task.task_type.replace("_", " ")}</code>
              </div>

              {task.result ? (
                <div className="task-block">
                  {isImageProcessingResult(task.result) ? (
                    <div className="image-result-detail">
                      <div className="section-title">Original Metadata</div>
                      <div className="stats-grid">
                        <div className="stats-item">
                          <span className="stats-label">Format</span>
                          <span className="stats-value">{task.result.original.format}</span>
                        </div>
                        <div className="stats-item">
                          <span className="stats-label">Resolution</span>
                          <span className="stats-value">
                            {task.result.original.width} × {task.result.original.height}
                          </span>
                        </div>
                      </div>

                      <div className="section-title">Processed Previews</div>
                      <div className="result-media">
                        <div className="result-item">
                          <span className="badge">Thumbnail</span>
                          <img
                            className="result-image"
                            src={task.result.thumbnail.image_data_url}
                            alt="Thumbnail"
                          />
                        </div>
                        <div className="result-item">
                          <span className="badge">Grayscale</span>
                          <img
                            className="result-image"
                            src={task.result.grayscale_preview.image_data_url}
                            alt="Grayscale"
                          />
                        </div>
                      </div>
                    </div>
                  ) : isCsvAnalysisResult(task.result) ? (
                    <div className="csv-result-detail">
                      <div className="section-title">Dataset Overview</div>
                      <div className="stats-grid">
                        <div className="stats-item">
                          <span className="stats-label">Rows</span>
                          <span className="stats-value">{task.result.row_count}</span>
                        </div>
                        <div className="stats-item">
                          <span className="stats-label">Columns</span>
                          <span className="stats-value">{task.result.column_count}</span>
                        </div>
                      </div>

                      {Object.keys(task.result.numeric_summary).length > 0 && (
                        <>
                          <div className="section-title">Numeric Summary</div>
                          <div className="data-table-container">
                            <table className="data-table">
                              <thead>
                                <tr>
                                  <th>Column</th>
                                  <th>Min</th>
                                  <th>Max</th>
                                  <th>Avg</th>
                                </tr>
                              </thead>
                              <tbody>
                                {Object.entries(task.result.numeric_summary).map(([col, stats]) => (
                                  <tr key={col}>
                                    <td>{col}</td>
                                    <td>{stats.min}</td>
                                    <td>{stats.max}</td>
                                    <td>{stats.average}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </>
                      )}

                      <div className="section-title">Sample Data</div>
                      <div className="data-table-container">
                        <table className="data-table">
                          <thead>
                            <tr>
                              {task.result.columns.map((col: string) => (
                                <th key={col}>{col}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {task.result.sample_rows.map((row, i) => {
                              const res = task.result;
                              return (
                                <tr key={i}>
                                  {isCsvAnalysisResult(res) && res.columns.map((col: string) => (
                                    <td key={col}>{String(row[col] ?? "-")}</td>
                                  ))}
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : (
                    <div className="generic-result">
                      <strong>Analysis Result</strong>
                      <pre>{JSON.stringify(task.result, null, 2)}</pre>
                    </div>
                  )}
                </div>
              ) : task.error ? (
                <p className="error-text">{task.error}</p>
              ) : (
                <div className="task-block">
                  <p className="task-id">Processing your request...</p>
                </div>
              )}
            </article>
          ))
        )}
      </section>
    </div>
  );
}

function readFileAsDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
        return;
      }
      reject(new Error("Unable to read file"));
    };
    reader.onerror = () => reject(new Error("Unable to read file"));
    reader.readAsDataURL(file);
  });
}

function isImageProcessingResult(
  result: Record<string, unknown> | null,
): result is {
  original: { format: string; width: number; height: number };
  thumbnail: { image_data_url: string };
  grayscale_preview: { image_data_url: string };
} {
  return (
    result !== null &&
    typeof result.original === "object" &&
    result.original !== null &&
    typeof result.thumbnail === "object" &&
    result.thumbnail !== null &&
    typeof result.grayscale_preview === "object" &&
    result.grayscale_preview !== null
  );
}

function isCsvAnalysisResult(
  result: Record<string, unknown> | null,
): result is {
  row_count: number;
  column_count: number;
  columns: string[];
  numeric_summary: Record<string, { min: number; max: number; average: number }>;
  sample_rows: Array<Record<string, unknown>>;
} {
  return (
    result !== null &&
    typeof result.row_count === "number" &&
    typeof result.column_count === "number" &&
    Array.isArray(result.columns) &&
    typeof result.numeric_summary === "object" &&
    result.numeric_summary !== null &&
    Array.isArray(result.sample_rows)
  );
}
