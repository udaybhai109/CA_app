import { useCallback, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";

import { uploadFile } from "../lib/api";

const STEPS = ["Uploaded", "Extracting", "Mapping", "Completed"] as const;

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

type DataUploaderProps = {
  onUploadSuccess?: () => void;
};

export default function DataUploader({ onUploadSuccess }: DataUploaderProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const runProcessingFlow = useCallback(async () => {
    setActiveStep(2);
    setProgress(45);
    await delay(500);

    setActiveStep(3);
    setProgress(75);
    await delay(500);

    setActiveStep(4);
    setProgress(100);
  }, []);

  const onDrop = useCallback(
    async (acceptedFiles: File[], fileRejections: FileRejection[]) => {
      if (fileRejections.length > 0) {
        const message = fileRejections[0]?.errors?.[0]?.message || "Unsupported file format.";
        setError(message);
        return;
      }

      const file = acceptedFiles[0];
      if (!file) return;

      setError(null);
      setToast(null);
      setFileName(file.name);
      setIsUploading(true);
      setActiveStep(1);
      setProgress(20);

      try {
        await uploadFile(file);
        await runProcessingFlow();
        setToast("Data processed successfully");
        window.setTimeout(() => setToast(null), 3000);
        if (onUploadSuccess) {
          onUploadSuccess();
        }
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("dashboard:refresh"));
        }
      } catch {
        setError("Upload failed. Please try again.");
      } finally {
        setIsUploading(false);
      }
    },
    [onUploadSuccess, runProcessingFlow]
  );

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    disabled: isUploading,
    multiple: false,
    noClick: true,
    accept: {
      "application/pdf": [".pdf"],
      "text/csv": [".csv"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
    },
  });

  return (
    <div className="relative rounded-2xl border border-borderLight bg-card p-6 shadow-sm transition-all duration-200 ease-in-out hover:-translate-y-0.5 hover:shadow-md">
      {toast ? (
        <div className="absolute right-6 top-6 z-10 rounded-lg border border-success/40 bg-success/10 px-3 py-2 text-sm text-success transition-all duration-200 ease-in-out">
          {toast}
        </div>
      ) : null}

      <div
        {...getRootProps()}
        className={`rounded-2xl border-2 border-dashed p-6 text-center transition-all duration-200 ease-in-out ${
          isDragActive
            ? "border-primary bg-primary/5"
            : isUploading
              ? "border-borderLight bg-white"
              : "border-borderLight bg-white hover:border-primary/40"
        }`}
      >
        <input {...getInputProps()} />
        <h3 className="text-base font-semibold text-navy">Upload Financial Data</h3>
        <p className="mt-2 text-sm text-muted">
          Drag and drop or browse files in PDF, CSV, or XLSX format.
        </p>
        <button
          type="button"
          onClick={open}
          disabled={isUploading}
          className="mt-4 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-all duration-200 ease-in-out hover:brightness-110 active:scale-95 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isUploading ? "Uploading..." : "Select File"}
        </button>
      </div>

      <div className="mt-6 space-y-6">
        <div>
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="font-medium text-navy">
              {fileName ? `File: ${fileName}` : "No file selected"}
            </span>
            <span className="text-muted">{progress}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-bg">
            <div
              className="h-2 rounded-full bg-primary transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {isUploading ? (
          <div className="flex items-center gap-2 text-sm text-navy">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-primary" />
            Processing upload...
          </div>
        ) : null}

        <ul className="space-y-3">
          {STEPS.map((step, index) => {
            const stepNumber = index + 1;
            const isCompleted = activeStep >= stepNumber;
            const isCurrent = isUploading && activeStep === stepNumber;

            return (
              <li key={step} className="flex items-center gap-3 text-sm">
                <span
                  className={`inline-flex h-6 w-6 items-center justify-center rounded-full border ${
                    isCompleted
                      ? "border-success bg-success text-white"
                      : isCurrent
                        ? "border-primary bg-primary text-white"
                        : "border-borderLight bg-white text-muted"
                  }`}
                >
                  {stepNumber}
                </span>
                <span className={isCompleted || isCurrent ? "text-navy" : "text-muted"}>{step}</span>
              </li>
            );
          })}
        </ul>

        {error ? <p className="text-sm text-danger">{error}</p> : null}
      </div>
    </div>
  );
}
