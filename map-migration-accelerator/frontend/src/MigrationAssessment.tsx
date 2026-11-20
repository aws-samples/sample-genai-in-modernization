import { useState, useRef, useEffect, useCallback } from "react";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import Alert from "@cloudscape-design/components/alert";
import Tabs from "@cloudscape-design/components/tabs";
import FormField from "@cloudscape-design/components/form-field";
import FileInput from "@cloudscape-design/components/file-input";
import Button from "@cloudscape-design/components/button";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Box from "@cloudscape-design/components/box";
import Table from "@cloudscape-design/components/table";
import StatusIndicator from "@cloudscape-design/components/status-indicator";
import ExpandableSection from "@cloudscape-design/components/expandable-section";
import KeyValuePairs from "@cloudscape-design/components/key-value-pairs";
import ColumnLayout from "@cloudscape-design/components/column-layout";
import Input from "@cloudscape-design/components/input";
import Textarea from "@cloudscape-design/components/textarea";
import mermaid from "mermaid";
import "./styles.css";

// Initialize mermaid with pie chart support
mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "strict" });

interface StreamEvent {
  type: string;
  data: string;
}

interface CsvData {
  headers: string[];
  rows: Record<string, string>[];
  fileName: string;
}

const VISIBLE_ROWS = 5;
const ROW_HEIGHT = 40;

function parseCsvText(text: string): { headers: string[]; rows: Record<string, string>[] } {
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  if (lines.length === 0) return { headers: [], rows: [] };
  const headers = lines[0].split(",").map((h) => h.trim());
  const rows = lines.slice(1).map((line) => {
    const cells = line.split(",");
    const row: Record<string, string> = {};
    headers.forEach((h, i) => { row[h] = (cells[i] || "").trim(); });
    return row;
  });
  return { headers, rows };
}

function readFileAsCsv(file: File): Promise<CsvData> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const { headers, rows } = parseCsvText(reader.result as string);
      resolve({ headers, rows, fileName: file.name });
    };
    reader.onerror = () => reject(new Error("Failed to read file"));
    reader.readAsText(file);
  });
}

/* ------------------------------------------------------------------ */
/* Mermaid diagram renderer                                            */
/* ------------------------------------------------------------------ */
let mermaidCounter = 0;
function MermaidDiagram({ chart }: { chart: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const id = `mermaid-${++mermaidCounter}`;
    mermaid.render(id, chart.trim()).then(({ svg }) => {
      // SVG comes from mermaid.render with securityLevel "strict", which sanitises it with DOMPurify.
      // nosemgrep: javascript.browser.security.insecure-innerhtml, javascript.browser.security.insecure-document-method
      if (containerRef.current) containerRef.current.innerHTML = svg;
    }).catch(() => {
      if (containerRef.current) containerRef.current.textContent = chart;
    });
  }, [chart]);

  return <div ref={containerRef} style={{ background: "#fff", borderRadius: 4, padding: 8, margin: "4px 0" }} />;
}

/* ------------------------------------------------------------------ */
/* CSV Preview                                                         */
/* ------------------------------------------------------------------ */
function CsvPreview({ data, label }: { data: CsvData; label: string }) {
  const maxHeight = ROW_HEIGHT * VISIBLE_ROWS;
  return (
    <ExpandableSection headerText={`${label}: ${data.fileName} (${data.rows.length} rows)`} defaultExpanded>
      <div style={{ maxHeight, overflowY: "auto" }}>
        <Table
          columnDefinitions={data.headers.map((h) => ({ id: h, header: h, cell: (item: Record<string, string>) => item[h] || "" }))}
          items={data.rows}
          variant="embedded"
          empty={<Box color="text-body-secondary">No data</Box>}
        />
      </div>
    </ExpandableSection>
  );
}

/* ------------------------------------------------------------------ */
/* Circular dependency cycle diagram                                   */
/* ------------------------------------------------------------------ */
function CycleDiagram({ cycle }: { cycle: string[] }) {
  const steps = cycle.slice(0, -1);
  return (
    <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 4, padding: "8px 0" }}>
      {steps.map((app, i) => (
        <span key={i} style={{ display: "flex", alignItems: "center" }}>
          <span style={{ display: "inline-block", padding: "4px 12px", borderRadius: 6, background: "#fdd", border: "1px solid #d44", fontWeight: 600, fontSize: 13, whiteSpace: "nowrap" }}>{app}</span>
          <span style={{ margin: "0 2px", fontSize: 16, color: "#d44" }}>→</span>
        </span>
      ))}
      <span style={{ display: "inline-block", padding: "4px 12px", borderRadius: 6, background: "#fdd", border: "2px dashed #d44", fontWeight: 600, fontSize: 13, whiteSpace: "nowrap" }}>{steps[0]} ↺</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Shared Infrastructure Diagram (Dependencies tab)                    */
/* ------------------------------------------------------------------ */
function SharedInfraDiagram({ sharedInfra, status }: { sharedInfra?: Record<string, string[]>; status?: string }) {
  const entries = Object.entries(sharedInfra || {}).filter(([, apps]) => Array.isArray(apps) && apps.length > 0);
  const hasMultiApp = entries.some(([, apps]) => apps.length > 1);

  // No infra uploaded
  if (status === "no_infra_data" || !sharedInfra) {
    return (
      <Container header={<Header variant="h2">Shared Infrastructure Map</Header>}>
        <Alert type="info">Upload an infrastructure CSV to see which apps share physical servers.</Alert>
      </Container>
    );
  }

  // Infra uploaded but no shared servers
  if (!hasMultiApp) {
    return (
      <Container header={<Header variant="h2">Shared Infrastructure Map</Header>}>
        <Alert type="success">No shared infrastructure detected — each app runs on dedicated infrastructure.</Alert>
      </Container>
    );
  }

  // Shared servers found — render diagram
  let chart = "flowchart LR\n";
  entries.forEach(([server, apps]) => {
    const isRisk = apps.length > 1;
    const sid = server.replace(/[^a-zA-Z0-9]/g, "_");
    chart += `  ${sid}["🖥 ${server}"]${isRisk ? ":::risk" : ""}\n`;
    apps.forEach((app) => {
      const aid = app.replace(/[^a-zA-Z0-9]/g, "_");
      chart += `  ${sid} --> ${aid}["${app}"]\n`;
    });
  });
  chart += "  classDef risk fill:#fdd,stroke:#d44,stroke-width:2px\n";

  return (
    <Container header={<Header variant="h2" description="Which apps share a physical server — migrating one may impact the others">Shared Infrastructure Map</Header>}>
      <ExpandableSection headerText={`${entries.length} server(s) with hosted applications (AI-inferred)`} defaultExpanded={false}>
        <SpaceBetween size="xs">
          <Box variant="small" color="text-body-secondary">
            Servers in red host multiple applications — concentration risk during migration.
            App-to-server mappings are AI-inferred and may need validation.
          </Box>
          <MermaidDiagram chart={chart} />
        </SpaceBetween>
      </ExpandableSection>
    </Container>
  );
}

/* ------------------------------------------------------------------ */
/* Tech Stack Pie Chart (Discovery tab)                                */
/* ------------------------------------------------------------------ */
function TechStackPieChart({ applications }: { applications: any[] }) {
  if (!applications || applications.length === 0) return null;

  const counts: Record<string, number> = {};
  applications.forEach((app) => {
    const stacks = app.tech_stack || [];
    stacks.forEach((t: string) => { counts[t] = (counts[t] || 0) + 1; });
  });

  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  if (sorted.length === 0) return null;

  // Show top 8, group rest as "Other"
  const top = sorted.slice(0, 8);
  const otherCount = sorted.slice(8).reduce((sum, [, c]) => sum + c, 0);

  let chart = "pie title Tech Stack Distribution\n";
  top.forEach(([name, count]) => { chart += `  "${name}" : ${count}\n`; });
  if (otherCount > 0) chart += `  "Other" : ${otherCount}\n`;

  return (
    <Container header={<Header variant="h2">Tech Stack Distribution</Header>}>
      <MermaidDiagram chart={chart} />
    </Container>
  );
}

/* ------------------------------------------------------------------ */
/* Top-N High-Risk Connected Apps (Dependencies tab)                   */
/* ------------------------------------------------------------------ */
const MAX_TOP_APPS = 15;

function TopConnectedApps({ graph }: { graph: { nodes: string[]; edges: { from: string; to: string }[] } }) {
  if (!graph?.nodes?.length || !graph?.edges?.length) return null;

  const nodes = graph.nodes;
  const edges = graph.edges;

  // Compute total degree (in + out) per node
  const degree: Record<string, number> = {};
  nodes.forEach((n) => { degree[n] = 0; });
  edges.forEach((e) => {
    degree[e.from] = (degree[e.from] || 0) + 1;
    degree[e.to] = (degree[e.to] || 0) + 1;
  });

  // Sort by degree descending, take top N
  const sorted = Object.entries(degree).sort((a, b) => b[1] - a[1]);
  const topApps = sorted.slice(0, MAX_TOP_APPS).map(([name]) => name);
  const topSet = new Set(topApps);
  const hiddenCount = nodes.length - topApps.length;

  // Only show edges where BOTH endpoints are in the top set
  const visibleEdges = edges.filter((e) => topSet.has(e.from) && topSet.has(e.to));

  if (topApps.length === 0) return null;

  // Build Mermaid flowchart
  let chart = "flowchart LR\n";

  // Add nodes with density class
  topApps.forEach((app) => {
    const d = degree[app] || 0;
    const cls = d >= 5 ? ":::high" : d >= 2 ? ":::med" : ":::low";
    const aid = app.replace(/[^a-zA-Z0-9]/g, "_");
    chart += `  ${aid}["${app} (${d})"]${cls}\n`;
  });

  // Add edges
  visibleEdges.forEach((e) => {
    const fid = e.from.replace(/[^a-zA-Z0-9]/g, "_");
    const tid = e.to.replace(/[^a-zA-Z0-9]/g, "_");
    chart += `  ${fid} --> ${tid}\n`;
  });

  chart += "  classDef high fill:#fdd,stroke:#d44,stroke-width:2px,color:#000\n";
  chart += "  classDef med fill:#ffd,stroke:#ec7211,stroke-width:2px,color:#000\n";
  chart += "  classDef low fill:#dfd,stroke:#037f0c,stroke-width:2px,color:#000\n";

  return (
    <Container header={<Header variant="h2" description="Top connected apps by dependency count — the migration hotspots">Dependency Hotspots</Header>}>
      <SpaceBetween size="s">
        <Box variant="small" color="text-body-secondary">
          🔴 High (5+ connections) &nbsp; 🟠 Medium (2–4) &nbsp; 🟢 Low (1) &nbsp; — Numbers in parentheses show total connections per app.
        </Box>
        <MermaidDiagram chart={chart} />
        {hiddenCount > 0 && (
          <Box variant="small" color="text-body-secondary" textAlign="center">
            ... and {hiddenCount} standalone/low-density app{hiddenCount !== 1 ? "s" : ""} not shown
          </Box>
        )}
      </SpaceBetween>
    </Container>
  );
}

/* ------------------------------------------------------------------ */
/* Key Findings panel                                                  */
/* ------------------------------------------------------------------ */
function KeyFindings({ findings }: { findings: any }) {
  if (!findings) return null;
  const isStructured = findings.length > 0 && typeof findings[0] === "object";
  if (!isStructured) {
    return (
      <Alert type="info" header="Key Findings">
        <ul>{findings.map((f: string, i: number) => <li key={i}>{f}</li>)}</ul>
      </Alert>
    );
  }
  return (
    <SpaceBetween size="xs">
      {findings.map((f: any, i: number) => (
        <Alert key={i} type={f.severity === "High" ? "error" : f.severity === "Medium" ? "warning" : "info"} header={f.title}>
          <Box variant="p">{f.detail}</Box>
          {f.affected_apps?.length > 0 && (
            <Box variant="small" color="text-body-secondary" margin={{ top: "xxs" }}>Affected: {f.affected_apps.join(", ")}</Box>
          )}
        </Alert>
      ))}
    </SpaceBetween>
  );
}

/* ------------------------------------------------------------------ */
/* Migration Readiness panel                                           */
/* ------------------------------------------------------------------ */
function ReadinessPanel({ readiness }: { readiness: any }) {
  if (!readiness) return null;
  if (typeof readiness === "string") {
    return <Alert type="info" header="Migration Readiness">{readiness}</Alert>;
  }
  return (
    <Container header={<Header variant="h3">Migration Readiness</Header>}>
      <SpaceBetween size="s">
        <KeyValuePairs columns={4} items={[
          { label: "Ready", value: <StatusIndicator type="success">{readiness.ready_count ?? "—"}</StatusIndicator> },
          { label: "Needs Work", value: <StatusIndicator type="warning">{readiness.needs_work_count ?? "—"}</StatusIndicator> },
          { label: "High Risk", value: <StatusIndicator type="error">{readiness.high_risk_count ?? "—"}</StatusIndicator> },
          { label: "Readiness", value: `${readiness.readiness_pct ?? "—"}%` },
        ]} />
        {readiness.summary && <Box variant="p">{readiness.summary}</Box>}
      </SpaceBetween>
    </Container>
  );
}

/* ------------------------------------------------------------------ */
/* Custom markdown code block renderer — renders mermaid diagrams      */
/* ------------------------------------------------------------------ */
/* Strategy output parser — splits markdown into structured sections   */
/* ------------------------------------------------------------------ */
interface StrategySection {
  title: string;
  blocks: Array<{ type: "text" | "table" | "code"; content: string; headers?: string[]; rows?: string[][]; lang?: string }>;
}

function parseStrategyMarkdown(md: string): StrategySection[] {
  const sections: StrategySection[] = [];
  // Split by ## headings
  const parts = md.split(/^##\s+/m).filter((p) => p.trim());
  for (const part of parts) {
    const lines = part.split("\n");
    const title = lines[0].trim();
    const body = lines.slice(1).join("\n").trim();
    const blocks: StrategySection["blocks"] = [];
    // Split body into table and non-table segments
    const bodyLines = body.split("\n");
    let i = 0;
    let textBuf: string[] = [];
    const flushText = () => {
      const t = textBuf.join("\n").trim();
      if (t) blocks.push({ type: "text", content: t });
      textBuf = [];
    };
    while (i < bodyLines.length) {
      const line = bodyLines[i];
      // Detect code blocks (```lang ... ```)
      const codeMatch = line.trim().match(/^```(\w*)/);
      if (codeMatch) {
        flushText();
        const lang = codeMatch[1] || "";
        const codeLines: string[] = [];
        i++;
        while (i < bodyLines.length && !bodyLines[i].trim().startsWith("```")) {
          codeLines.push(bodyLines[i]);
          i++;
        }
        i++; // skip closing ```
        blocks.push({ type: "code", content: codeLines.join("\n"), lang });
        continue;
      }
      // Detect table: line starts with | and next line is separator
      if (line.trim().startsWith("|") && i + 1 < bodyLines.length && /^\|[\s\-:|]+\|/.test(bodyLines[i + 1].trim())) {
        flushText();
        const tableLines: string[] = [];
        while (i < bodyLines.length && bodyLines[i].trim().startsWith("|")) {
          tableLines.push(bodyLines[i]);
          i++;
        }
        // Parse table
        if (tableLines.length >= 2) {
          const parseRow = (r: string) => r.split("|").map((c) => c.trim()).filter((c) => c !== "");
          const headers = parseRow(tableLines[0]);
          const rows = tableLines.slice(2).map(parseRow).filter((r) => r.length > 0);
          blocks.push({ type: "table", content: tableLines.join("\n"), headers, rows });
        }
      } else {
        textBuf.push(line);
        i++;
      }
    }
    flushText();
    if (title && (blocks.length > 0 || title.toLowerCase().includes("input"))) {
      sections.push({ title, blocks });
    }
  }
  return sections;
}

/* ------------------------------------------------------------------ */
/* StrategyOutput — renders parsed strategy with Cloudscape components */
/* ------------------------------------------------------------------ */
function StrategyOutput({ markdown }: { markdown: string }) {
  const sections = parseStrategyMarkdown(markdown);
  if (sections.length === 0) return <Box>{markdown}</Box>;
  return (
    <SpaceBetween size="l">
      {sections.map((section, si) => {
        const isExecSummary = section.title.toLowerCase().includes("executive summary") || section.title.toLowerCase().includes("migration strategy");
        return (
        <div key={si} style={isExecSummary ? { borderLeft: "4px solid #0972d3", borderRadius: 4, background: "#f2f8fd" } : undefined}>
        <Container header={<Header variant="h2">{section.title}</Header>}>
          <SpaceBetween size="s">
            {section.blocks.map((block, bi) => {
              if (block.type === "table" && block.headers && block.rows) {
                const ROW_HEIGHT = 45;
                const needsScroll = block.rows.length > 10;
                const tableEl = (
                  <Table
                    key={bi}
                    variant="embedded"
                    columnDefinitions={block.headers.map((h, ci) => ({
                      id: `col-${ci}`,
                      header: h,
                      cell: (item: string[]) => item[ci] || "—",
                    }))}
                    items={block.rows}
                    wrapLines
                    stickyHeader
                  />
                );
                return needsScroll
                  ? <div key={bi} style={{ maxHeight: ROW_HEIGHT * 10, overflowY: "auto" }}>{tableEl}</div>
                  : tableEl;
              }
              if (block.type === "code") {
                if (block.lang === "mermaid") {
                  return <MermaidDiagram key={bi} chart={block.content} />;
                }
                return (
                  <pre key={bi} style={{ background: "rgba(0,0,0,0.06)", padding: 12, borderRadius: 4, overflowX: "auto", fontSize: 13 }}>
                    <code>{block.content}</code>
                  </pre>
                );
              }
              // Render text block — handle bullets, bold, emoji, blockquotes
              return (
                <Box key={bi} variant="p">
                  {block.content.split("\n").map((line, li) => {
                    const trimmed = line.trim();
                    if (!trimmed) return null;
                    if (trimmed.startsWith("> ")) {
                      return <Alert key={li} type="warning" statusIconAriaLabel="Warning">{trimmed.slice(2)}</Alert>;
                    }
                    // Sub-headings (### or ####)
                    if (trimmed.startsWith("### ") || trimmed.startsWith("#### ")) {
                      const text = trimmed.replace(/^#{3,4}\s+/, "");
                      return <div key={li} style={{ fontWeight: 700, fontSize: 15, marginTop: 16, marginBottom: 4, paddingBottom: 4, borderBottom: "1px solid #e9ebed" }}>{renderBold(text)}</div>;
                    }
                    // Numbered list (1. item)
                    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
                    if (numMatch) {
                      return <div key={li} style={{ paddingLeft: 16 }}>{numMatch[1]}. {renderBold(numMatch[2])}</div>;
                    }
                    if (trimmed.startsWith("- ") || trimmed.startsWith("• ")) {
                      const bullet = trimmed.slice(2);
                      return <div key={li} style={{ paddingLeft: 16 }}>• {renderBold(bullet)}</div>;
                    }
                    return <div key={li}>{renderBold(trimmed)}</div>;
                  })}
                </Box>
              );
            })}
          </SpaceBetween>
        </Container>
        </div>
        );
      })}
    </SpaceBetween>
  );
}

/** Render **bold** segments within a string */
function renderBold(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**")
      ? <strong key={i}>{p.slice(2, -2)}</strong>
      : p
  );
}

/* ------------------------------------------------------------------ */
/* Main component                                                      */
/* ------------------------------------------------------------------ */
interface MigrationAssessmentProps {
  assessment: any;
  setAssessment: (val: any) => void;
  strategyResult: string;
  setStrategyResult: (val: string) => void;
}

export default function MigrationAssessment({ assessment, setAssessment, strategyResult, setStrategyResult }: MigrationAssessmentProps) {
  const [appFiles, setAppFiles] = useState<File[]>([]);
  const [infraFiles, setInfraFiles] = useState<File[]>([]);
  const [error, setError] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [activeTab, setActiveTab] = useState("upload");
  const [appCsvPreview, setAppCsvPreview] = useState<CsvData | null>(null);
  const [infraCsvPreview, setInfraCsvPreview] = useState<CsvData | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Strategy state
  const [strategyDrivers, setStrategyDrivers] = useState("");
  const [strategyTimeline, setStrategyTimeline] = useState("");
  const [strategyStartDate, setStrategyStartDate] = useState("");
  const [strategyStreaming, setStrategyStreaming] = useState(false);
  const [strategyEvents, setStrategyEvents] = useState<StreamEvent[]>([]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [events]);
  useEffect(() => { if (!assessment) { setStrategyResult(""); setStrategyDrivers(""); setStrategyTimeline(""); setStrategyStartDate(""); setStrategyEvents([]); } }, [assessment, setStrategyResult]);
  useEffect(() => {
    if (appFiles.length > 0) readFileAsCsv(appFiles[0]).then(setAppCsvPreview).catch(() => setAppCsvPreview(null));
    else setAppCsvPreview(null);
  }, [appFiles]);
  useEffect(() => {
    if (infraFiles.length > 0) readFileAsCsv(infraFiles[0]).then(setInfraCsvPreview).catch(() => setInfraCsvPreview(null));
    else setInfraCsvPreview(null);
  }, [infraFiles]);

  // Strategy handler
  const handleRunStrategy = useCallback(async () => {
    if (!assessment || strategyStreaming) return;
    const timelineText = strategyStartDate
      ? `${strategyTimeline} (Expected start: ${strategyStartDate})`
      : strategyTimeline;
    setStrategyResult("");
    setStrategyEvents([]);
    setStrategyStreaming(true);
    try {
      const res = await fetch("/api/migration/strategy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ drivers_and_scope: strategyDrivers, timeline: timelineText, assessment }),
      });
      if (!res.ok) {
        const err = await res.json();
        setStrategyResult(`Error: ${err.error || "Strategy generation failed"}`);
        setStrategyStreaming(false);
        return;
      }
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        let currentEventType = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) currentEventType = line.slice(7).trim();
          else if (line.startsWith("data: ") && currentEventType) {
            const data = JSON.parse(line.slice(6));
            if (currentEventType === "lifecycle") {
              setStrategyEvents((prev) => [...prev, { type: "lifecycle", data }]);
            } else if (currentEventType === "done") {
              setStrategyResult(data);
            } else if (currentEventType === "error") {
              setStrategyResult(`Error: ${data}`);
            }
            currentEventType = "";
          }
        }
      }
    } catch (err: any) {
      setStrategyResult(`Error: ${err.message}`);
    }
    setStrategyStreaming(false);
  }, [assessment, strategyStreaming, strategyDrivers, strategyTimeline, strategyStartDate]);

  const handleUpload = async () => {
    if (appFiles.length === 0) { setError("Please select an application inventory CSV file."); return; }
    if (!appFiles[0].name.toLowerCase().endsWith(".csv")) { setError("Application file must be a CSV."); return; }
    if (infraFiles.length > 0 && !infraFiles[0].name.toLowerCase().endsWith(".csv")) { setError("Infrastructure file must be a CSV."); return; }

    setError(""); setEvents([]); setAssessment(null); setStrategyResult(""); setStrategyEvents([]); setStreaming(true);
    const formData = new FormData();
    formData.append("app_file", appFiles[0]);
    if (infraFiles.length > 0) formData.append("infra_file", infraFiles[0]);

    try {
      const res = await fetch("/api/migration/upload", { method: "POST", body: formData });
      if (!res.ok) { const err = await res.json(); setError(err.error || "Upload failed"); setStreaming(false); return; }
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        let currentEventType = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) currentEventType = line.slice(7).trim();
          else if (line.startsWith("data: ") && currentEventType) {
            const data = JSON.parse(line.slice(6));
            if (currentEventType === "done") { const result = typeof data === "string" ? JSON.parse(data) : data; setAssessment(result); setStreaming(false); setActiveTab("discovery"); }
            else if (currentEventType === "partial") { const result = typeof data === "string" ? JSON.parse(data) : data; setAssessment(result); setActiveTab("discovery"); }
            else if (currentEventType === "error") { setError(data); setStreaming(false); }
            else setEvents((prev) => [...prev, { type: currentEventType, data }]);
            currentEventType = "";
          }
        }
      }
    } catch (err: any) { setError(err.message); setStreaming(false); }
  };

  const discovery = assessment?.discovery;
  const dependency = assessment?.dependency;
  const apps = discovery?.app_analysis?.applications || [];
  const infra = discovery?.infra_analysis?.components || [];
  const execSummary = discovery?.executive_summary;
  const graph = dependency?.graph;
  const clusters = dependency?.clusters || [];
  const circularDeps = dependency?.circular_dependencies || [];
  const circularDepsDetail = dependency?.circular_dependencies_detail || [];
  const complexityScores = dependency?.complexity_scores || {};
  const lifecycleEvents = events.filter((e) => e.type === "lifecycle" || e.type === "tool");


  /* ------------------------------------------------------------------ */
  /* JSX                                                                 */
  /* ------------------------------------------------------------------ */
  return (
    <SpaceBetween size="l">
      <Header variant="h1" description="AI-powered cloud migration assessment using multi-agent analysis">
        Dependency Assessment
      </Header>

      {error && <Alert type="error" dismissible onDismiss={() => setError("")}>{error}</Alert>}

      <Tabs
        activeTabId={activeTab}
        onChange={({ detail }) => setActiveTab(detail.activeTabId)}
        tabs={[
              {
                id: "upload",
                label: "Upload Inventory Data",
                content: (
                  <Container header={<Header variant="h2">Upload Inventory Data</Header>}>
                    <SpaceBetween size="l">
                      <ColumnLayout columns={2}>
                        <FormField label="Application Inventory CSV" description="Required — application portfolio data">
                          <FileInput value={appFiles} onChange={({ detail }) => setAppFiles(detail.value)} accept=".csv">Choose file</FileInput>
                        </FormField>
                        <FormField label="Infrastructure Inventory CSV" description="Optional — infrastructure component data">
                          <FileInput value={infraFiles} onChange={({ detail }) => setInfraFiles(detail.value)} accept=".csv">Choose file</FileInput>
                        </FormField>
                      </ColumnLayout>

                      {appCsvPreview && <CsvPreview data={appCsvPreview} label="Application Data" />}
                      {infraCsvPreview && <CsvPreview data={infraCsvPreview} label="Infrastructure Data" />}

                      <Button variant="primary" onClick={handleUpload} loading={streaming} disabled={appFiles.length === 0}>
                        {streaming ? "Analyzing..." : "Run Assessment"}
                      </Button>

                      {/* Streaming events */}
                      {lifecycleEvents.length > 0 && (
                        <Container header={<Header variant="h3">Analysis Progress</Header>}>
                          <SpaceBetween size="xs">
                            {lifecycleEvents.map((e, i) => (
                              <StatusIndicator key={i} type={e.type === "tool" ? "in-progress" : "success"}>
                                {e.data}
                              </StatusIndicator>
                            ))}
                            {streaming && <StatusIndicator type="loading">Processing...</StatusIndicator>}
                          </SpaceBetween>
                          <div ref={bottomRef} />
                        </Container>
                      )}
                    </SpaceBetween>
                  </Container>
                ),
              },
              {
                id: "discovery",
                label: "IT Discovery",
                disabled: !assessment,
                content: assessment ? (
                  <SpaceBetween size="l">
                    {/* Discovery Summary */}
                    {execSummary && (
                      <Container header={<Header variant="h2">Discovery Summary</Header>}>
                        <SpaceBetween size="m">
                          <KeyValuePairs columns={4} items={[
                            { label: "Total Applications", value: execSummary.total_applications },
                            { label: "Total Infrastructure", value: execSummary.total_infrastructure },
                            { label: "Overall Risk", value: <StatusIndicator type={execSummary.overall_risk_level === "High" ? "error" : execSummary.overall_risk_level === "Medium" ? "warning" : "success"}>{execSummary.overall_risk_level}</StatusIndicator> },
                            { label: "Estimated Timeline", value: execSummary.estimated_timeline || "—" },
                          ]} />
                          {execSummary.key_findings && <KeyFindings findings={execSummary.key_findings} />}
                        </SpaceBetween>
                      </Container>
                    )}

                    {/* Readiness */}
                    {discovery?.migration_readiness && <ReadinessPanel readiness={discovery.migration_readiness} />}

                    {/* Application Analysis */}
                    {apps.length > 0 && (
                      <Container header={<Header variant="h2">Application Analysis ({apps.length} apps)</Header>}>
                        <div style={{ maxHeight: ROW_HEIGHT * 10, overflowY: "auto" }}>
                          <Table
                            columnDefinitions={[
                              { id: "name", header: "Application", cell: (item: any) => item.name },
                              { id: "type", header: "Type", cell: (item: any) => item.type || "—" },
                              { id: "criticality", header: "Criticality", cell: (item: any) => <StatusIndicator type={item.criticality === "High" ? "error" : item.criticality === "Medium" ? "warning" : "success"}>{item.criticality}</StatusIndicator> },
                              { id: "risk", header: "Risk Signals", cell: (item: any) => {
                                const signals = item.risk_signals || [];
                                return signals.length > 0 ? signals.join(", ") : <Box color="text-status-success">None detected</Box>;
                              }},
                              { id: "tech", header: "Tech Stack", cell: (item: any) => item.tech_stack?.join(", ") || "—" },
                            ]}
                            items={apps}
                            variant="embedded"
                            wrapLines
                          />
                        </div>
                      </Container>
                    )}

                    {/* Infrastructure */}
                    {infra.length > 0 && (
                      <Container header={<Header variant="h2">Infrastructure Components ({infra.length} servers)</Header>}>
                        <div style={{ maxHeight: ROW_HEIGHT * 10, overflowY: "auto" }}>
                          <Table
                            columnDefinitions={[
                              { id: "server", header: "Server", cell: (item: any) => item.server_name || item.name || "—" },
                              { id: "os", header: "OS", cell: (item: any) => item.os || "—" },
                              { id: "risk", header: "Risk Signals", cell: (item: any) => item.risk_signals?.join(", ") || "None" },
                              { id: "apps", header: "Hosted Apps", cell: (item: any) => item.hosted_apps?.join(", ") || "—" },
                            ]}
                            items={infra}
                            variant="embedded"
                            wrapLines
                          />
                        </div>
                      </Container>
                    )}

                    {/* Tech Stack Pie Chart */}
                    {apps.length > 0 && <TechStackPieChart applications={apps} />}
                  </SpaceBetween>
                ) : <Box>No data</Box>,
              },
              {
                id: "dependencies",
                label: "Application Dependencies",
                disabled: !assessment?.dependency,
                content: assessment ? (
                  <SpaceBetween size="l">
                    {/* Dependency Summary */}
                    {dependency?.dependency_summary && (
                      <Container header={<Header variant="h2" description="High-level stats on application connections and integration density">Dependency Summary</Header>}>
                        <KeyValuePairs columns={5} items={[
                          { label: "Total Apps", value: dependency.dependency_summary.total_apps },
                          { label: "Total Edges", value: dependency.dependency_summary.total_edges },
                          { label: "Standalone", value: dependency.dependency_summary.standalone_count },
                          { label: "Avg Dependencies", value: dependency.dependency_summary.avg_dependencies },
                          { label: "Most Connected", value: dependency.dependency_summary.most_connected_app },
                        ]} />
                      </Container>
                    )}

                    {/* Dependency Key Findings */}
                    {dependency?.key_findings?.length > 0 && <KeyFindings findings={dependency.key_findings} />}

                    {/* Shared Infrastructure Map */}
                    {dependency && <SharedInfraDiagram sharedInfra={dependency.shared_infrastructure} status={dependency.shared_infrastructure_status} />}

                    {/* Top Connected Apps — Dependency Hotspots */}
                    {graph && <TopConnectedApps graph={graph} />}

                    {/* Complexity Scores */}
                    {Object.keys(complexityScores).length > 0 && (
                      <Container header={<Header variant="h2" description="How difficult is each app to migrate based on its dependencies and coupling">Migration Complexity</Header>}>
                        <div style={{ maxHeight: ROW_HEIGHT * 10, overflowY: "auto" }}>
                          <Table
                            columnDefinitions={[
                              { id: "app", header: "Application", cell: (item: any) => item.app },
                              { id: "score", header: "Score", cell: (item: any) => item.numScore },
                              { id: "complexity", header: "Complexity", cell: (item: any) => (
                                <StatusIndicator type={item.numScore >= 70 ? "error" : item.numScore >= 40 ? "warning" : "success"}>
                                  {item.numScore >= 70 ? "High" : item.numScore >= 40 ? "Medium" : "Low"}
                                </StatusIndicator>
                              )},
                              { id: "bar", header: "Distribution", cell: (item: any) => (
                                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                  <div style={{ width: 120, height: 12, background: "#e9ebed", borderRadius: 6, overflow: "hidden" }}>
                                    <div style={{ width: `${item.numScore}%`, height: "100%", background: item.numScore >= 70 ? "#d91515" : item.numScore >= 40 ? "#ec7211" : "#037f0c", borderRadius: 6 }} />
                                  </div>
                                </div>
                              )},
                              { id: "rationale", header: "Migration Rationale", cell: (item: any) => item.rationale || "—" },
                            ]}
                            items={Object.entries(complexityScores).map(([app, data]: [string, any]) => {
                              const numScore = typeof data === "object" ? (data.score ?? 0) : (typeof data === "number" ? data : 0);
                              const rationale = typeof data === "object" ? (data.migration_rationale || "") : "";
                              return { app, numScore, rationale };
                            }).sort((a, b) => b.numScore - a.numScore)}
                            variant="embedded"
                            wrapLines
                          />
                        </div>
                      </Container>
                    )}

                    {/* Circular Dependencies */}
                    {circularDeps.length > 0 && (
                      <Container header={<Header variant="h2" description="Which apps are in deadlock loops — you can't migrate one without the other">Circular Dependencies</Header>}>
                        <SpaceBetween size="s">
                          {circularDeps.map((cycle: string[], i: number) => {
                            const detail = circularDepsDetail[i];
                            const impact = detail?.impact || "";
                            return (
                              <ExpandableSection key={i} headerText={`Cycle ${i + 1}: ${cycle.length - 1} applications`} defaultExpanded={i === 0}>
                                <CycleDiagram cycle={cycle} />
                                {impact && <Box variant="p" color="text-body-secondary" margin={{ top: "xs" }}>{impact}</Box>}
                              </ExpandableSection>
                            );
                          })}
                        </SpaceBetween>
                      </Container>
                    )}

                    {/* Recommendation: Breaking Circular Dependencies */}
                    {circularDeps.length > 0 && (
                      <Container header={<Header variant="h2">Recommendation: Breaking Circular Dependencies</Header>}>
                        <SpaceBetween size="s">
                          <Box variant="p">Circular dependencies are migration blockers — you cannot migrate one app independently. Consider these strategies:</Box>
                          <Box variant="p"><b>1. Parallel cutover</b> — Migrate all apps in a cycle simultaneously during a single maintenance window.</Box>
                          <Box variant="p"><b>2. Introduce an abstraction layer</b> — Place an API gateway or message queue between tightly coupled apps to decouple them before migration.</Box>
                          <Box variant="p"><b>3. Temporary dual-write</b> — Run both old and new environments in parallel with data sync until all apps in the cycle are migrated.</Box>
                          <Box variant="p"><b>4. Strangler fig pattern</b> — Gradually route traffic from the legacy app to the migrated version, breaking one dependency at a time.</Box>
                        </SpaceBetween>
                      </Container>
                    )}

                    {/* Migration Clusters */}
                    {clusters.length > 0 && (
                      <Container header={<Header variant="h2" description="Groups of tightly connected apps that should be migrated together">Migration Clusters</Header>}>
                        <Table
                          columnDefinitions={[
                            { id: "name", header: "Cluster", cell: (item: any) => item.name },
                            { id: "wave", header: "Wave", cell: (item: any) => item.suggested_wave },
                            { id: "risk", header: "Risk", cell: (item: any) => <StatusIndicator type={item.risk_level === "High" ? "error" : item.risk_level === "Medium" ? "warning" : "success"}>{item.risk_level}</StatusIndicator> },
                            { id: "apps", header: "Applications", cell: (item: any) => item.apps?.join(", ") },
                          ]}
                          items={clusters}
                          variant="embedded"
                        />
                      </Container>
                    )}

                  </SpaceBetween>
                ) : <Box>No data</Box>,
              },
              {
                id: "strategy",
                label: "Migration and Modernisation Strategy",
                disabled: !assessment,
                content: assessment ? (
                  <SpaceBetween size="l">
                    <Container header={<Header variant="h2" description="Provide migration context to generate a tailored strategy and wave plan">Migration Strategy Inputs</Header>}>
                      <SpaceBetween size="m">
                        <FormField label="Migration Drivers & Scope" description="What is driving this migration? (e.g., data centre exit, cost reduction, modernisation, compliance)">
                          <Textarea value={strategyDrivers} onChange={({ detail }) => setStrategyDrivers(detail.value)} placeholder="e.g., Data centre lease expiry in 18 months, reduce operational costs by 30%, modernise legacy .NET apps" rows={3} />
                        </FormField>
                        <FormField label="Migration Timeline" description="Target duration and any hard deadlines">
                          <Input value={strategyTimeline} onChange={({ detail }) => setStrategyTimeline(detail.value)} placeholder="e.g., 12 months, must complete by Q4 2026" />
                        </FormField>
                        <FormField label="Expected Migration Start Date" description="When do you plan to begin?">
                          <Input value={strategyStartDate} onChange={({ detail }) => setStrategyStartDate(detail.value)} placeholder="e.g., July 2026" />
                        </FormField>
                        <Button variant="primary" onClick={handleRunStrategy} loading={strategyStreaming} disabled={!strategyDrivers.trim() || !strategyTimeline.trim()}>
                          {strategyStreaming ? "Generating Strategy..." : "Generate Migration Strategy"}
                        </Button>
                      </SpaceBetween>
                    </Container>

                    {/* Strategy streaming progress */}
                    {strategyEvents.length > 0 && (
                      <Container header={<Header variant="h3">Strategy Generation Progress</Header>}>
                        <SpaceBetween size="xs">
                          {strategyEvents.map((e, i) => (
                            <StatusIndicator key={i} type="success">{e.data}</StatusIndicator>
                          ))}
                          {strategyStreaming && <StatusIndicator type="loading">Generating strategy...</StatusIndicator>}
                        </SpaceBetween>
                      </Container>
                    )}

                    {strategyResult && !strategyStreaming && (
                      <StrategyOutput markdown={strategyResult} />
                    )}
                  </SpaceBetween>
                ) : <Box>No data</Box>,
              },
            ]}
          />
        </SpaceBetween>
  );
}
