import { ChangeEvent, FormEvent, startTransition, useEffect, useRef, useState } from "react";

import { createTask, listTasks } from "./api";
import type {
  CsvAnalysisResult,
  ImageProcessingResult,
  ImageTransform,
  Task,
  TaskType,
} from "./types";

const TASK_OPTIONS: Array<{ value: TaskType; label: string; help: string }> = [
  {
    value: "image_processing",
    label: "Image Processing",
    help: "Upload an image, choose transforms, and review polished visual outputs.",
  },
  {
    value: "csv_analysis",
    label: "CSV Analysis",
    help: "Inspect uploaded CSV content and produce structural and numeric summaries.",
  },
];

const IMAGE_TRANSFORM_OPTIONS: Array<{
  value: ImageTransform;
  label: string;
  help: string;
}> = [
    {
      value: "thumbnail",
      label: "Thumbnail",
      help: "Generate a compact preview card.",
    },
    {
      value: "grayscale",
      label: "Grayscale",
      help: "Highlight contrast and tone.",
    },
    {
      value: "sepia",
      label: "Sepia",
      help: "Apply a warm archival treatment.",
    },
    {
      value: "blur",
      label: "Blur",
      help: "Create a softened visual pass.",
    },
    {
      value: "edge_enhance",
      label: "Edge Enhance",
      help: "Bring out edges and structure.",
    },
  ];

const MAX_UPLOAD_BYTES = 8 * 1024 * 1024;
const MAX_DIMENSION = 1600;
const OUTPUT_QUALITY = 0.82;

type ImageDraft = {
  filename: string;
  mimeType: string;
  dataUrl: string;
  previewUrl: string;
  width: number;
  height: number;
  originalSizeBytes: number;
  optimizedSizeBytes: number;
};

export function App() {
  const [taskType, setTaskType] = useState<TaskType>("image_processing");
  const [csvFilename, setCsvFilename] = useState("sales-report.csv");
  const [csvText, setCsvText] = useState(
    "name,amount,region\nAsha,120,North\nRavi,95,South\nMina,210,West\nKabir,,East",
  );
  const [selectedTransforms, setSelectedTransforms] = useState<ImageTransform[]>([
    "thumbnail",
    "grayscale",
    "sepia",
  ]);
  const [imageDraft, setImageDraft] = useState<ImageDraft | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  async function refreshTasks(silently = false) {
    try {
      const nextTasks = await listTasks();
      startTransition(() => {
        setTasks(nextTasks);
      });
      if (silently) {
        setRefreshError(null);
      }
    } catch (refreshTaskError) {
      const message = refreshTaskError instanceof Error ? refreshTaskError.message : "Unable to load tasks";
      if (silently) {
        setRefreshError(message);
      } else {
        setError(message);
      }
    }
  }

  useEffect(() => {
    void refreshTasks();
    const timer = window.setInterval(() => {
      void refreshTasks(true);
    }, 3000);

    return () => window.clearInterval(timer);
  }, []);

  async function onSelectImage(file: File | null) {
    setError(null);

    if (!file) {
      setImageDraft(null);
      return;
    }

    if (!file.type.startsWith("image/")) {
      setError("Please choose a PNG, JPEG, or WebP image.");
      return;
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      setError(`Image is too large. Please choose a file under ${formatBytes(MAX_UPLOAD_BYTES)}.`);
      return;
    }

    setIsUploadingImage(true);
    try {
      const optimized = await optimizeImage(file);
      setImageDraft(optimized);
    } catch (imageError) {
      setImageDraft(null);
      setError(imageError instanceof Error ? imageError.message : "Unable to prepare image");
    } finally {
      setIsUploadingImage(false);
    }
  }

  async function onFileInputChange(event: ChangeEvent<HTMLInputElement>) {
    await onSelectImage(event.target.files?.[0] ?? null);
  }

  function toggleTransform(transform: ImageTransform) {
    setSelectedTransforms((current) => {
      if (current.includes(transform)) {
        if (current.length === 1) {
          return current;
        }
        return current.filter((item) => item !== transform);
      }
      return [...current, transform];
    });
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const payload =
        taskType === "image_processing"
          ? {
            filename: imageDraft?.filename ?? "",
            image_data_url: imageDraft?.dataUrl ?? "",
            transforms: selectedTransforms,
          }
          : {
            filename: csvFilename,
            csv_text: csvText,
          };

      if (taskType === "image_processing" && !imageDraft) {
        throw new Error("Choose an image before starting the task.");
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
        <h1>Smarter file processing with clearer feedback.</h1>
        <p>
          Prepare an image or CSV, submit it into the task pipeline, and review rich results as the
          workers complete each job.
        </p>
      </header>

      <main className="panel form-panel">
        <div className="panel-header">
          <div>
            <h2>New Task</h2>
            <span>
              {TASK_OPTIONS.find((option) => option.value === taskType)?.help}
            </span>
          </div>
          <div className="poll-indicator">
            <span className="pulse-dot" />
            Polling every 3s
          </div>
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
              <input
                ref={fileInputRef}
                className="visually-hidden"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={onFileInputChange}
              />

              <div
                className={`dropzone ${isDragging ? "dropzone-active" : ""} ${imageDraft ? "dropzone-ready" : ""}`}
                onClick={() => fileInputRef.current?.click()}
                onDragEnter={(event) => {
                  event.preventDefault();
                  setIsDragging(true);
                }}
                onDragOver={(event) => {
                  event.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={(event) => {
                  event.preventDefault();
                  setIsDragging(false);
                }}
                onDrop={(event) => {
                  event.preventDefault();
                  setIsDragging(false);
                  void onSelectImage(event.dataTransfer.files?.[0] ?? null);
                }}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    fileInputRef.current?.click();
                  }
                }}
              >
                <div className="dropzone-copy">
                  <span className="dropzone-title">Drop an image here or click to browse</span>
                  <span className="dropzone-subtitle">
                    PNG, JPEG, or WebP up to {formatBytes(MAX_UPLOAD_BYTES)}. Large images are compressed
                    in the browser before upload.
                  </span>
                </div>
                <button type="button" className="secondary-button">
                  Choose File
                </button>
              </div>

              {isUploadingImage ? <p className="info-text">Optimizing image for upload...</p> : null}

              {imageDraft ? (
                <section className="image-draft-card">
                  <div className="image-draft-preview">
                    <img className="preview-image" src={imageDraft.previewUrl} alt="Selected preview" />
                  </div>
                  <div className="image-draft-meta">
                    <div className="section-title">Preview Details</div>
                    <div className="stats-grid">
                      <div className="stats-item">
                        <span className="stats-label">File</span>
                        <span className="stats-value">{imageDraft.filename}</span>
                      </div>
                      <div className="stats-item">
                        <span className="stats-label">Type</span>
                        <span className="stats-value">{imageDraft.mimeType}</span>
                      </div>
                      <div className="stats-item">
                        <span className="stats-label">Dimensions</span>
                        <span className="stats-value">
                          {imageDraft.width} × {imageDraft.height}
                        </span>
                      </div>
                      <div className="stats-item">
                        <span className="stats-label">Compression</span>
                        <span className="stats-value">
                          {formatBytes(imageDraft.originalSizeBytes)} to {formatBytes(imageDraft.optimizedSizeBytes)}
                        </span>
                      </div>
                    </div>
                  </div>
                </section>
              ) : null}

              <fieldset className="transform-picker">
                <legend>Processing Modes</legend>
                <div className="transform-grid">
                  {IMAGE_TRANSFORM_OPTIONS.map((option) => {
                    const selected = selectedTransforms.includes(option.value);
                    return (
                      <label key={option.value} className={`transform-card ${selected ? "transform-selected" : ""}`}>
                        <input
                          type="checkbox"
                          checked={selected}
                          onChange={() => toggleTransform(option.value)}
                        />
                        <span className="transform-label">{option.label}</span>
                        <span className="transform-help">{option.help}</span>
                      </label>
                    );
                  })}
                </div>
              </fieldset>
            </>
          ) : (
            <>
              <label>
                CSV Filename
                <input value={csvFilename} onChange={(event) => setCsvFilename(event.target.value)} />
              </label>
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

          <button type="submit" disabled={isSubmitting || isUploadingImage}>
            {isSubmitting ? "Submitting Task..." : "Run Task"}
          </button>

          {error ? <p className="error-text">{error}</p> : null}
          {refreshError ? <p className="info-text">{refreshError}</p> : null}
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

              <p className="task-id">{task.id}</p>

              {task.result ? (
                <div className="task-block">
                  {isImageProcessingResult(task.result) ? (
                    <ImageResultCard task={task} />
                  ) : isCsvAnalysisResult(task.result) ? (
                    <CsvResultCard result={task.result} />
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

function ImageResultCard({ task }: { task: Task }) {
  const result = task.result as unknown as ImageProcessingResult;

  return (
    <div className="image-result-detail">
      <div className="result-header">
        <div>
          <div className="section-title">Original Asset</div>
          <div className="result-caption">{result.filename}</div>
        </div>
        <div className="badge-row">
          {result.transforms.map((transform) => (
            <span key={transform} className="badge">
              {IMAGE_TRANSFORM_OPTIONS.find((option) => option.value === transform)?.label ?? transform}
            </span>
          ))}
        </div>
      </div>

      <div className="image-comparison">
        <div className="result-item result-item-featured">
          <span className="badge badge-muted">Original</span>
          <img className="result-image" src={result.original.image_data_url} alt="Original upload" />
        </div>
        <div className="stats-grid">
          <div className="stats-item">
            <span className="stats-label">Format</span>
            <span className="stats-value">{result.original.format}</span>
          </div>
          <div className="stats-item">
            <span className="stats-label">Resolution</span>
            <span className="stats-value">
              {result.original.width} × {result.original.height}
            </span>
          </div>
          <div className="stats-item">
            <span className="stats-label">Size</span>
            <span className="stats-value">{formatBytes(result.original.size_bytes)}</span>
          </div>
          <div className="stats-item">
            <span className="stats-label">Aspect</span>
            <span className="stats-value">{result.original.aspect_ratio ?? "-"}</span>
          </div>
        </div>
      </div>

      <div className="section-title">Processed Outputs</div>
      <div className="result-media">
        {result.outputs.map((output) => (
          <div key={output.key} className="result-item">
            <div className="result-item-header">
              <span className="badge">{output.label}</span>
              <a className="download-link" href={output.image_data_url} download={`${task.id}-${output.key}.png`}>
                Download
              </a>
            </div>
            <img className="result-image" src={output.image_data_url} alt={output.label} />
            <p className="result-description">{output.description}</p>
            <p className="result-caption">
              {output.width} × {output.height}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function CsvResultCard({ result }: { result: CsvAnalysisResult }) {
  const numericEntries = Object.entries(result.numeric_summary);
  const chartEntries =
    result.bar_chart?.columns?.slice(0, 3) ??
    numericEntries.map(([column, stats]) => ({ column, value: stats.average })).slice(0, 3);
  const maxValue = chartEntries.reduce((max, entry) => Math.max(max, entry.value), 0);

  return (
    <div className="csv-result-detail">
      <div className="section-title">Dataset Overview</div>
      <div className="stats-grid">
        <div className="stats-item">
          <span className="stats-label">Rows</span>
          <span className="stats-value">{result.row_count}</span>
        </div>
        <div className="stats-item">
          <span className="stats-label">Columns</span>
          <span className="stats-value">{result.column_count}</span>
        </div>
      </div>

      {numericEntries.length > 0 ? (
        <>
          {chartEntries.length > 0 ? (
            <>
              <div className="section-title">Top 3 Column Averages</div>
              <div className="csv-bar-chart">
                {chartEntries.map((entry) => {
                  const heightPercent = maxValue > 0 ? (entry.value / maxValue) * 100 : 0;
                  return (
                    <div key={entry.column} className="csv-bar-column">
                      <div className="csv-bar-head">
                        <span className="csv-bar-value">{entry.value.toFixed(2)}</span>
                      </div>
                      <div className="csv-bar-track">
                        <div className="csv-bar-fill" style={{ height: `${heightPercent}%` }}>
                          <span className="csv-bar-flower" aria-hidden="true">
                            <span className="csv-flower-center" />
                          </span>
                        </div>
                      </div>
                      <span className="csv-bar-label">{entry.column}</span>
                    </div>
                  );
                })}
              </div>
            </>
          ) : null}

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
                {numericEntries.map(([column, stats]) => (
                  <tr key={column}>
                    <td>{column}</td>
                    <td>{stats.min}</td>
                    <td>{stats.max}</td>
                    <td>{stats.average}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      <div className="section-title">Sample Data</div>
      <div className="data-table-container">
        <table className="data-table">
          <thead>
            <tr>
              {result.columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.sample_rows.map((row, index) => (
              <tr key={index}>
                {result.columns.map((column) => (
                  <td key={column}>{String(row[column] ?? "-")}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

async function optimizeImage(file: File): Promise<ImageDraft> {
  const sourceDataUrl = await readFileAsDataUrl(file);
  const image = await loadImage(sourceDataUrl);

  const scale = Math.min(1, MAX_DIMENSION / Math.max(image.width, image.height));
  const width = Math.max(1, Math.round(image.width * scale));
  const height = Math.max(1, Math.round(image.height * scale));
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;

  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("Your browser could not prepare the image for upload.");
  }

  context.drawImage(image, 0, 0, width, height);

  const outputType = file.type === "image/png" ? "image/png" : "image/jpeg";
  const optimizedDataUrl = canvas.toDataURL(outputType, OUTPUT_QUALITY);
  const optimizedSizeBytes = estimateDataUrlBytes(optimizedDataUrl);

  return {
    filename: file.name,
    mimeType: file.type || outputType,
    dataUrl: optimizedDataUrl,
    previewUrl: optimizedDataUrl,
    width,
    height,
    originalSizeBytes: file.size,
    optimizedSizeBytes,
  };
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

function loadImage(dataUrl: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Unable to load image"));
    image.src = dataUrl;
  });
}

function estimateDataUrlBytes(dataUrl: string) {
  const [, encoded = ""] = dataUrl.split(",", 2);
  const padding = encoded.endsWith("==") ? 2 : encoded.endsWith("=") ? 1 : 0;
  return Math.round((encoded.length * 3) / 4) - padding;
}

function formatBytes(value: number) {
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(2)} MB`;
}

function isImageProcessingResult(result: unknown): result is ImageProcessingResult {
  return (
    typeof result === "object" &&
    result !== null &&
    "original" in result &&
    "outputs" in result &&
    Array.isArray(result.outputs)
  );
}

function isCsvAnalysisResult(result: unknown): result is CsvAnalysisResult {
  return (
    typeof result === "object" &&
    result !== null &&
    "row_count" in result &&
    typeof result.row_count === "number" &&
    "column_count" in result &&
    typeof result.column_count === "number" &&
    "columns" in result &&
    Array.isArray(result.columns) &&
    "numeric_summary" in result &&
    typeof result.numeric_summary === "object" &&
    result.numeric_summary !== null &&
    "sample_rows" in result &&
    Array.isArray(result.sample_rows)
  );
}
