import { useState } from "react";
import { Copy, Check, Download } from "lucide-react";

export function CodeBlock({ filename, code }: { filename: string; code: string }) {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  const onDownload = () => {
    const blob = new Blob([code], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <div className="overflow-hidden rounded-card border border-border bg-[#0F172A]">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-2.5">
        <span className="font-mono text-xs text-slate-300">{filename}</span>
        <div className="flex gap-2">
          <button onClick={onCopy} className="flex min-h-[32px] items-center gap-1.5 rounded-md px-2.5 py-1 text-xs text-slate-300 hover:bg-white/10" aria-label={`Copy ${filename}`}>
            {copied ? <Check size={14} /> : <Copy size={14} />}
            {copied ? "Copied" : "Copy"}
          </button>
          <button onClick={onDownload} className="flex min-h-[32px] items-center gap-1.5 rounded-md px-2.5 py-1 text-xs text-slate-300 hover:bg-white/10" aria-label={`Download ${filename}`}>
            <Download size={14} /> Download
          </button>
        </div>
      </div>
      <pre className="max-h-72 overflow-auto px-4 py-3 text-xs leading-relaxed text-slate-200">
        <code>{code}</code>
      </pre>
    </div>
  );
}
