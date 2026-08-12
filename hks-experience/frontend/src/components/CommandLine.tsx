import { useState } from "react";
import { Copy, Check, ExternalLink } from "lucide-react";

/** A single copyable shell command -- used for "Apply this YAML"
 * (`kubectl apply -f <raw-url>`), manual/verify commands, and anywhere else
 * that needs ONE command rather than a multi-line script block (see
 * ../components/CodeBlock.tsx for the YAML-content case). Deliberately
 * separate from CodeBlock: "Copy YAML" and "Copy kubectl Command" must
 * never be the same button/action. */
export function CommandLine({ command, label, href, hrefLabel }: { command: string; label?: string; href?: string; hrefLabel?: string }) {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    await navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div>
      {label && <p className="mb-1.5 font-subheading text-sm">{label}</p>}
      <div className="flex items-center gap-2 rounded-lg bg-[#0F172A] px-3 py-2.5">
        <code className="flex-1 overflow-x-auto whitespace-pre text-xs text-slate-200">{command}</code>
        <button onClick={onCopy} className="flex shrink-0 items-center gap-1.5 rounded-md px-2 py-1 text-xs text-slate-300 hover:bg-white/10" aria-label="Copy command">
          {copied ? <Check size={14} /> : <Copy size={14} />}
          {copied ? "Copied" : "Copy Command"}
        </button>
        {href && (
          <a href={href} target="_blank" rel="noreferrer" className="flex shrink-0 items-center gap-1.5 rounded-md px-2 py-1 text-xs text-slate-300 hover:bg-white/10">
            <ExternalLink size={14} />
            {hrefLabel ?? "Open"}
          </a>
        )}
      </div>
    </div>
  );
}
