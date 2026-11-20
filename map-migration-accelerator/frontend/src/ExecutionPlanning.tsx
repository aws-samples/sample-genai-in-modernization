import { useState, useRef, useEffect, useCallback } from "react";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import Alert from "@cloudscape-design/components/alert";
import Tabs from "@cloudscape-design/components/tabs";
import FormField from "@cloudscape-design/components/form-field";
import Button from "@cloudscape-design/components/button";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Box from "@cloudscape-design/components/box";
import Input from "@cloudscape-design/components/input";
import StatusIndicator from "@cloudscape-design/components/status-indicator";
import Table from "@cloudscape-design/components/table";
import ExpandableSection from "@cloudscape-design/components/expandable-section";
import Modal from "@cloudscape-design/components/modal";
import { CodeView } from "@cloudscape-design/code-view";
import mermaid from "mermaid";
import { useSessionState } from "./App";
import DrawioDiagram from "./DrawioDiagram";

mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "strict" });

/* ------------------------------------------------------------------ */
/* Shared types                                                        */
/* ------------------------------------------------------------------ */
interface StreamEvent {
  type: string;
  data: string;
}

interface ExecutionPlanningProps {
  assessment: any;
  strategyResult: string;
}

/* ------------------------------------------------------------------ */
/* Task Breakdown types                                                */
/* ------------------------------------------------------------------ */
interface TBTask {
  subject: string;
  description: string;
}
interface TBStory {
  subject: string;
  description: string;
  tasks: TBTask[];
}
interface TBEpic {
  subject: string;
  description: string;
  stories: TBStory[];
}
interface TBWave {
  name: string;
  timeframe: string;
  description: string;
  epics: TBEpic[];
}
interface TaskBreakdownResult {
  gantt: string;
  waves: TBWave[];
  scheduling_rationale?: string;
}

/* ------------------------------------------------------------------ */
/* Mermaid diagram renderer (same pattern as MigrationAssessment)      */
/* ------------------------------------------------------------------ */
let mermaidCounter = 1000;
function MermaidDiagram({ chart }: { chart: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const id = `mermaid-exec-${++mermaidCounter}`;
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
/* Markdown parser — reuses same pattern as MigrationAssessment        */
/* ------------------------------------------------------------------ */
interface StructuredSection {
  title: string;
  blocks: Array<{ type: "text" | "table" | "code"; content: string; headers?: string[]; rows?: string[][]; lang?: string }>;
}

function parseStructuredMarkdown(md: string): StructuredSection[] {
  const sections: StructuredSection[] = [];
  const parts = md.split(/^##\s+/m).filter((p) => p.trim());
  for (const part of parts) {
    const lines = part.split("\n");
    const title = lines[0].trim();
    const body = lines.slice(1).join("\n").trim();
    const blocks: StructuredSection["blocks"] = [];
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
        i++;
        blocks.push({ type: "code", content: codeLines.join("\n"), lang });
        continue;
      }
      if (line.trim().startsWith("|") && i + 1 < bodyLines.length && /^\|[\s\-:|]+\|/.test(bodyLines[i + 1].trim())) {
        flushText();
        const tableLines: string[] = [];
        while (i < bodyLines.length && bodyLines[i].trim().startsWith("|")) {
          tableLines.push(bodyLines[i]);
          i++;
        }
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
    if (title && blocks.length > 0) {
      sections.push({ title, blocks });
    }
  }
  return sections;
}

function renderBold(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**")
      ? <strong key={i}>{p.slice(2, -2)}</strong>
      : p
  );
}

/* ------------------------------------------------------------------ */
/* StructuredOutput — renders parsed markdown with Cloudscape          */
/* ------------------------------------------------------------------ */
function StructuredOutput({ markdown, collapsible }: { markdown: string; collapsible?: boolean }) {
  const sections = parseStructuredMarkdown(markdown);
  if (sections.length === 0) return <Box>{markdown}</Box>;
  return (
    <SpaceBetween size="l">
      {sections.map((section, si) => {
        const content = (
          <SpaceBetween size="s">
            {section.blocks.map((block, bi) => {
              if (block.type === "table" && block.headers && block.rows) {
                return (
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
              return (
                <Box key={bi} variant="p">
                  {block.content.split("\n").map((line, li) => {
                    const trimmed = line.trim();
                    if (!trimmed) return null;
                    if (trimmed.startsWith("> ")) {
                      return <Alert key={li} type="warning">{renderBold(trimmed.slice(2))}</Alert>;
                    }
                    if (trimmed.startsWith("### ") || trimmed.startsWith("#### ")) {
                      const text = trimmed.replace(/^#{3,4}\s+/, "");
                      return <div key={li} style={{ fontWeight: 700, fontSize: 14, marginTop: 8 }}>{renderBold(text)}</div>;
                    }
                    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
                    if (numMatch) {
                      return <div key={li} style={{ paddingLeft: 16 }}>{numMatch[1]}. {renderBold(numMatch[2])}</div>;
                    }
                    if (trimmed.startsWith("- ") || trimmed.startsWith("• ") || trimmed.startsWith("* ")) {
                      return <div key={li} style={{ paddingLeft: 16 }}>• {renderBold(trimmed.replace(/^[-•*]\s+/, ""))}</div>;
                    }
                    if (line.startsWith("  - ") || line.startsWith("  • ") || line.startsWith("  * ")) {
                      return <div key={li} style={{ paddingLeft: 32 }}>◦ {renderBold(trimmed.replace(/^[-•*]\s+/, ""))}</div>;
                    }
                    return <div key={li}>{renderBold(trimmed)}</div>;
                  })}
                </Box>
              );
            })}
          </SpaceBetween>
        );
        return collapsible ? (
          <ExpandableSection key={si} headerText={section.title} variant="container">{content}</ExpandableSection>
        ) : (
          <Container key={si} header={<Header variant="h2">{section.title}</Header>}>{content}</Container>
        );
      })}
    </SpaceBetween>
  );
}

/* ------------------------------------------------------------------ */
/* IaC code block parser — extracts YAML blocks with headers           */
/* ------------------------------------------------------------------ */
interface IaCBlock {
  title: string;
  yaml: string;
}

function parseIaCBlocks(markdown: string): IaCBlock[] {
  const blocks: IaCBlock[] = [];
  const lines = markdown.split("\n");
  let i = 0;
  let lastHeading = "CloudFormation Template";

  while (i < lines.length) {
    const line = lines[i];
    // Track headings
    if (line.trim().startsWith("## ") || line.trim().startsWith("### ")) {
      lastHeading = line.trim().replace(/^#{2,3}\s+/, "");
      i++;
      continue;
    }
    // Detect yaml code block
    if (line.trim().startsWith("```yaml") || line.trim().startsWith("```yml")) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      if (codeLines.length > 0) {
        blocks.push({ title: lastHeading, yaml: codeLines.join("\n") });
      }
      continue;
    }
    i++;
  }
  return blocks;
}

/* ------------------------------------------------------------------ */
/* Main component                                                      */
/* ------------------------------------------------------------------ */
export default function ExecutionPlanning({ assessment, strategyResult }: ExecutionPlanningProps) {
  const [activeTab, setActiveTab] = useState("landing-zone");

  // Landing Zone — Design sub-tab state
  const [lzRegion, setLzRegion] = useState("us-east-1");
  const [lzAccountStrategy, setLzAccountStrategy] = useState("Multi-Account");
  const [lzConnectivity, setLzConnectivity] = useState("Hybrid with Direct Connect");
  const [lzDesignResult, setLzDesignResult] = useSessionState<string>("ep-lz-design", "");
  const [lzStreaming, setLzStreaming] = useState(false);
  const [lzEvents, setLzEvents] = useState<StreamEvent[]>([]);
  const [lzError, setLzError] = useState("");

  // Landing Zone — IaC sub-tab state
  const [iacResult, setIacResult] = useSessionState<string>("ep-lz-iac", "");
  const [iacError, setIacError] = useState("");

  // Landing Zone — Architecture Diagram sub-tab state
  const [diagResult, setDiagResult] = useSessionState<string>("ep-lz-diag", "");
  const [diagError, setDiagError] = useState("");
  const [diagEditorOpen, setDiagEditorOpen] = useState(false);

  // Landing Zone sub-tab
  const [lzSubTab, setLzSubTab] = useState("lz-design");

  // Task Breakdown state
  const [tbResult, setTbResult] = useSessionState<TaskBreakdownResult | null>("ep-tb-result", null);
  const [tbStreaming, setTbStreaming] = useState(false);
  const [tbEvents, setTbEvents] = useState<StreamEvent[]>([]);
  const [tbError, setTbError] = useState("");
  const [tbActiveWave, setTbActiveWave] = useState("wave-0");

  // Push to Taiga state
  const [taigaStreaming, setTaigaStreaming] = useState(false);
  const [taigaEvents, setTaigaEvents] = useState<StreamEvent[]>([]);
  const [taigaError, setTaigaError] = useState("");
  const [taigaResult, setTaigaResult] = useSessionState<{
    success: boolean;
    epics_created: number;
    stories_created: number;
    tasks_created: number;
    project_url: string;
  } | null>("ep-taiga-result", null);

  // Wave Runbook state
  const [wrResult, setWrResult] = useSessionState<string>("ep-wr-result", "");
  const [wrStreaming, setWrStreaming] = useState(false);
  const [wrEvents, setWrEvents] = useState<StreamEvent[]>([]);
  const [wrError, setWrError] = useState("");

  // Expose lzDesignResult as lzResult for downstream consumers (task breakdown, wave runbook)
  const lzResult = lzDesignResult;

  const handleRunLandingZone = useCallback(async () => {
    if (lzStreaming) return;
    setLzDesignResult("");
    setIacResult("");
    setDiagResult("");
    setLzEvents([]);
    setLzError("");
    setIacError("");
    setDiagError("");
    setLzStreaming(true);

    try {
      const res = await fetch("/api/execution/landing-zone", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          region: lzRegion,
          account_strategy: lzAccountStrategy,
          connectivity: lzConnectivity,
          assessment,
          strategy: strategyResult,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        setLzError(err.error || "Landing zone generation failed");
        setLzStreaming(false);
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
              setLzEvents((prev) => [...prev, { type: "lifecycle", data }]);
            } else if (currentEventType === "design_done") {
              setLzDesignResult(data);
            } else if (currentEventType === "diagram_done") {
              setDiagResult(data);
            } else if (currentEventType === "iac_done") {
              setIacResult(data);
            } else if (currentEventType === "error") {
              // Route errors to appropriate sub-tab
              if (typeof data === "string" && data.includes("Design Agent")) setLzError(data);
              else if (typeof data === "string" && data.includes("Diagram Agent")) setDiagError(data);
              else if (typeof data === "string" && data.includes("IaC Agent")) setIacError(data);
              else setLzError(data);
            }
            currentEventType = "";
          }
        }
      }
    } catch (err: any) {
      setLzError(err.message);
    }
    setLzStreaming(false);
  }, [lzStreaming, lzRegion, lzAccountStrategy, lzConnectivity, assessment, strategyResult]);

  const handleRunTaskBreakdown = useCallback(async () => {
    if (tbStreaming) return;
    setTbResult(null);
    setTbEvents([]);
    setTbError("");
    setTbStreaming(true);
    try {
      const res = await fetch("/api/execution/task-breakdown", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          assessment,
          strategy: strategyResult,
          landing_zone: lzResult,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        setTbError(err.error || "Task breakdown generation failed");
        setTbStreaming(false);
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
              setTbEvents((prev) => [...prev, { type: "lifecycle", data }]);
            } else if (currentEventType === "done") {
              const parsed = typeof data === "string" ? JSON.parse(data) : data;
              setTbResult(parsed);
              setTbActiveWave("wave-0");
            } else if (currentEventType === "error") {
              setTbError(data);
            }
            currentEventType = "";
          }
        }
      }
    } catch (err: any) {
      setTbError(err.message);
    }
    setTbStreaming(false);
  }, [tbStreaming, assessment, strategyResult, lzResult]);

  const handlePushToTaiga = useCallback(async () => {
    if (taigaStreaming || !tbResult) return;
    setTaigaResult(null);
    setTaigaEvents([]);
    setTaigaError("");
    setTaigaStreaming(true);
    try {
      const res = await fetch("/api/execution/push-to-taiga", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_breakdown: tbResult }),
      });
      if (!res.ok) {
        const err = await res.json();
        setTaigaError(err.error || "Push to Taiga failed");
        setTaigaStreaming(false);
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
              setTaigaEvents((prev) => [...prev, { type: "lifecycle", data }]);
            } else if (currentEventType === "done") {
              const parsed = typeof data === "string" ? JSON.parse(data) : data;
              setTaigaResult(parsed);
            } else if (currentEventType === "error") {
              setTaigaError(data);
            }
            currentEventType = "";
          }
        }
      }
    } catch (err: any) {
      setTaigaError(err.message);
    }
    setTaigaStreaming(false);
  }, [taigaStreaming, tbResult]);

  const handleRunWaveRunbook = useCallback(async () => {
    if (wrStreaming) return;
    setWrResult("");
    setWrEvents([]);
    setWrError("");
    setWrStreaming(true);
    try {
      const res = await fetch("/api/execution/wave-runbook", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          assessment,
          strategy: strategyResult,
          landing_zone: lzResult,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        setWrError(err.error || "Wave runbook generation failed");
        setWrStreaming(false);
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
              setWrEvents((prev) => [...prev, { type: "lifecycle", data }]);
            } else if (currentEventType === "done") {
              setWrResult(data);
            } else if (currentEventType === "error") {
              setWrError(data);
            }
            currentEventType = "";
          }
        }
      }
    } catch (err: any) {
      setWrError(err.message);
    }
    setWrStreaming(false);
  }, [wrStreaming, assessment, strategyResult, lzResult]);

  /* ---------------------------------------------------------------- */
  /* Landing Zone tab content with sub-tabs                            */
  /* ---------------------------------------------------------------- */
  const iacBlocks = iacResult ? parseIaCBlocks(iacResult) : [];

  const landingZoneContent = (
    <SpaceBetween size="l">
      <Container header={<Header variant="h2">Landing Zone Configuration</Header>}>
        <SpaceBetween size="m">
          <FormField label="Target AWS Region">
            <Input value={lzRegion} onChange={({ detail }) => setLzRegion(detail.value)} disabled={lzStreaming} />
          </FormField>
          <FormField label="Account Strategy">
            <Input value={lzAccountStrategy} onChange={({ detail }) => setLzAccountStrategy(detail.value)} disabled={lzStreaming} />
          </FormField>
          <FormField label="Connectivity Model">
            <Input value={lzConnectivity} onChange={({ detail }) => setLzConnectivity(detail.value)} disabled={lzStreaming} />
          </FormField>
          <Button variant="primary" onClick={handleRunLandingZone} loading={lzStreaming}>
            {lzStreaming ? "Generating..." : "Generate Landing Zone Design"}
          </Button>
        </SpaceBetween>
      </Container>

      {/* Progress events */}
      {lzEvents.length > 0 && lzStreaming && (
        <Container header={<Header variant="h3">Progress</Header>}>
          <SpaceBetween size="xs">
            {lzEvents.map((e, i) => (
              <StatusIndicator key={i} type="success">{e.data}</StatusIndicator>
            ))}
            <StatusIndicator type="loading">Processing...</StatusIndicator>
          </SpaceBetween>
        </Container>
      )}

      {/* Sub-tabs — enabled independently as data arrives */}
      {(lzDesignResult || iacResult || diagResult || lzError || iacError || diagError) && (
        <Tabs
          activeTabId={lzSubTab}
          onChange={({ detail }) => setLzSubTab(detail.activeTabId)}
          tabs={[
            {
              id: "lz-design",
              label: "Landing Zone Design",
              disabled: !lzDesignResult && !lzError,
              content: (
                <SpaceBetween size="l">
                  {lzError && <Alert type="error" dismissible onDismiss={() => setLzError("")}>{lzError}</Alert>}
                  {lzDesignResult && <StructuredOutput markdown={lzDesignResult} collapsible />}
                </SpaceBetween>
              ),
            },
            {
              id: "lz-iac",
              label: "IaC Templates",
              disabled: !iacResult && !iacError,
              content: (
                <SpaceBetween size="l">
                  {iacError && <Alert type="error" dismissible onDismiss={() => setIacError("")}>{iacError}</Alert>}
                  {iacBlocks.length > 0 && iacBlocks.map((block, bi) => (
                    <ExpandableSection key={bi} headerText={block.title} variant="container">
                      <SpaceBetween size="xs">
                        <div style={{ textAlign: "right" }}>
                          <Button variant="icon" iconName="copy" onClick={() => navigator.clipboard.writeText(block.yaml)} ariaLabel="Copy to clipboard" />
                        </div>
                        <CodeView content={block.yaml} lineNumbers wrapLines />
                      </SpaceBetween>
                    </ExpandableSection>
                  ))}
                  {iacResult && iacBlocks.length === 0 && (
                    <ExpandableSection headerText="IaC Output" variant="container">
                      <CodeView content={iacResult} lineNumbers wrapLines />
                    </ExpandableSection>
                  )}
                </SpaceBetween>
              ),
            },
            {
              id: "lz-diagram",
              label: "Architecture Diagram",
              disabled: !diagResult && !diagError,
              content: (
                <SpaceBetween size="l">
                  {diagError && <Alert type="error" dismissible onDismiss={() => setDiagError("")}>{diagError}</Alert>}
                  {diagResult && (
                    <SpaceBetween size="m">
                      <Container header={
                        <Header variant="h2" actions={
                          <SpaceBetween direction="horizontal" size="xs">
                            <Button variant="normal" iconName="download" onClick={() => {
                              const blob = new Blob([diagResult], { type: "application/xml" });
                              const url = URL.createObjectURL(blob);
                              const a = document.createElement("a");
                              a.href = url;
                              a.download = "landing-zone-architecture.drawio";
                              a.click();
                              URL.revokeObjectURL(url);
                            }}>Download .drawio</Button>
                            <Button variant="normal" iconName="expand" onClick={() => setDiagEditorOpen(true)}>Open in draw.io</Button>
                          </SpaceBetween>
                        }>Architecture Diagram</Header>
                      }>
                        <DrawioDiagram xml={diagResult} />
                      </Container>
                      <Modal
                        visible={diagEditorOpen}
                        onDismiss={() => setDiagEditorOpen(false)}
                        size="max"
                        header="Architecture Diagram Editor"
                      >
                        {diagEditorOpen && <DrawioDiagram xml={diagResult} editor />}
                      </Modal>
                      <ExpandableSection headerText="Raw XML Output (Debug)" variant="container">
                        <Box>
                          <SpaceBetween size="xs">
                            <Button variant="normal" iconName="copy" onClick={() => navigator.clipboard.writeText(diagResult)}>Copy XML to Clipboard</Button>
                            <pre style={{ background: "rgba(0,0,0,0.06)", padding: 12, borderRadius: 4, overflowX: "auto", fontSize: 12, maxHeight: 400, overflowY: "auto", whiteSpace: "pre-wrap", wordBreak: "break-all" }}>{diagResult}</pre>
                          </SpaceBetween>
                        </Box>
                      </ExpandableSection>
                    </SpaceBetween>
                  )}
                </SpaceBetween>
              ),
            },
          ]}
        />
      )}
    </SpaceBetween>
  );

  /* ---------------------------------------------------------------- */
  /* Task Breakdown tab content                                        */
  /* ---------------------------------------------------------------- */
  const taskBreakdownContent = (
    <SpaceBetween size="l">
      <Container header={<Header variant="h2">Task Breakdown</Header>}>
        <SpaceBetween size="m">
          <Box variant="p" color="text-body-secondary">
            Generate a structured task breakdown for all migration waves. Each wave produces an Epic with User Stories and Tasks that can be pushed to Taiga for project tracking.
          </Box>
          <Button
            variant="primary"
            onClick={handleRunTaskBreakdown}
            loading={tbStreaming}
            disabled={!lzResult}
          >
            {tbStreaming ? "Generating..." : "Generate Task Breakdown"}
          </Button>
          {!lzResult && (
            <Alert type="info">Generate a Landing Zone design first before creating the task breakdown.</Alert>
          )}
        </SpaceBetween>
      </Container>

      {tbError && <Alert type="error" dismissible onDismiss={() => setTbError("")}>{tbError}</Alert>}

      {tbEvents.length > 0 && !tbResult && (
        <Container header={<Header variant="h3">Progress</Header>}>
          <SpaceBetween size="xs">
            {tbEvents.map((e, i) => (
              <StatusIndicator key={i} type="success">{e.data}</StatusIndicator>
            ))}
            {tbStreaming && <StatusIndicator type="loading">Processing...</StatusIndicator>}
          </SpaceBetween>
        </Container>
      )}

      {tbResult && (
        <SpaceBetween size="l">
          {tbResult.scheduling_rationale && (
            <Alert type="info" header="Wave Scheduling Rationale">
              {tbResult.scheduling_rationale}
            </Alert>
          )}

          {tbResult.gantt && (
            <Container header={<Header variant="h2">Wave Timeline</Header>}>
              <MermaidDiagram chart={tbResult.gantt} />
            </Container>
          )}

          {tbResult.waves && tbResult.waves.length > 0 && (
            <Tabs
              activeTabId={tbActiveWave}
              onChange={({ detail }) => setTbActiveWave(detail.activeTabId)}
              tabs={tbResult.waves.map((wave, wi) => ({
                id: `wave-${wi}`,
                label: wave.name,
                content: (
                  <SpaceBetween size="m">
                    <Container header={
                      <Header variant="h2" description={wave.description}>
                        {wave.name} — {wave.timeframe}
                      </Header>
                    }>
                      <SpaceBetween size="m">
                        {wave.epics.map((epic, ei) => (
                          <ExpandableSection
                            key={ei}
                            headerText={`Epic: ${epic.subject}`}
                            defaultExpanded
                            variant="container"
                          >
                            <SpaceBetween size="s">
                              <Box variant="p" color="text-body-secondary">{epic.description}</Box>
                              {epic.stories.map((story, si) => (
                                <ExpandableSection
                                  key={si}
                                  headerText={story.subject}
                                  defaultExpanded
                                >
                                  <SpaceBetween size="s">
                                    <Box variant="p">
                                      {story.description.split("\n").map((line, li) => (
                                        <div key={li}>{line}</div>
                                      ))}
                                    </Box>
                                    <Table
                                      variant="embedded"
                                      columnDefinitions={[
                                        { id: "task", header: "Task", cell: (item: TBTask) => item.subject, width: 250 },
                                        { id: "desc", header: "Description", cell: (item: TBTask) => item.description },
                                      ]}
                                      items={story.tasks}
                                      wrapLines
                                    />
                                  </SpaceBetween>
                                </ExpandableSection>
                              ))}
                            </SpaceBetween>
                          </ExpandableSection>
                        ))}
                      </SpaceBetween>
                    </Container>
                  </SpaceBetween>
                ),
              }))}
            />
          )}
        </SpaceBetween>
      )}

      {/* Push to Taiga */}
      {tbResult && (
        <Container header={<Header variant="h2">Sync Migration Plan to Kanban Board (Taiga)</Header>}>
          <SpaceBetween size="m">
            <Box variant="p" color="text-body-secondary">
              Push the generated task breakdown to your Taiga project. This will create epics, user stories, and tasks for all migration waves.
            </Box>
            <Button
              variant="primary"
              onClick={handlePushToTaiga}
              loading={taigaStreaming}
              disabled={taigaResult?.success === true}
            >
              {taigaStreaming ? "Pushing..." : taigaResult?.success ? "Pushed to Taiga ✓" : "Push to Taiga"}
            </Button>

            {taigaError && <Alert type="error" dismissible onDismiss={() => setTaigaError("")}>{taigaError}</Alert>}

            {taigaEvents.length > 0 && (
              <ExpandableSection headerText="Progress" defaultExpanded>
                <SpaceBetween size="xs">
                  {taigaEvents.map((e, i) => (
                    <StatusIndicator key={i} type="success">{e.data}</StatusIndicator>
                  ))}
                  {taigaStreaming && <StatusIndicator type="loading">Processing...</StatusIndicator>}
                </SpaceBetween>
              </ExpandableSection>
            )}

            {taigaResult?.success && (
              <Alert type="success" header="Successfully pushed to Taiga">
                Created {taigaResult.epics_created} epics, {taigaResult.stories_created} user stories, and {taigaResult.tasks_created} tasks.
                {taigaResult.project_url && (
                  <span> View your project at <a href={taigaResult.project_url} target="_blank" rel="noopener noreferrer">{taigaResult.project_url}</a></span>
                )}
              </Alert>
            )}
          </SpaceBetween>
        </Container>
      )}
    </SpaceBetween>
  );

  return (
    <SpaceBetween size="l">
      <Header variant="h1" description="Plan and execute your cloud migration">
        Migration Execution and Planning
      </Header>

      <Tabs
        activeTabId={activeTab}
        onChange={({ detail }) => setActiveTab(detail.activeTabId)}
        tabs={[
          { id: "landing-zone", label: "Landing Zone Design", content: landingZoneContent },
          { id: "task-breakdown", label: "Task Management", content: taskBreakdownContent },
          { id: "wave-runbooks", label: "Wave Runbooks", disabled: !tbResult, content: (
            <SpaceBetween size="l">
              <Container header={<Header variant="h2">Wave Runbooks</Header>}>
                <SpaceBetween size="m">
                  <Box variant="p" color="text-body-secondary">
                    Generate detailed operational runbooks for Wave 1 migration, including pre-migration checklists, cutover steps, rollback plans, and post-migration validation.
                  </Box>
                  <Button
                    variant="primary"
                    onClick={handleRunWaveRunbook}
                    loading={wrStreaming}
                    disabled={!tbResult}
                  >
                    {wrStreaming ? "Generating..." : "Generate Wave Runbooks"}
                  </Button>
                  {!tbResult && (
                    <Alert type="info">Generate a Task Breakdown first before creating wave runbooks.</Alert>
                  )}
                </SpaceBetween>
              </Container>

              {wrError && <Alert type="error" dismissible onDismiss={() => setWrError("")}>{wrError}</Alert>}

              {wrEvents.length > 0 && !wrResult && (
                <Container header={<Header variant="h3">Progress</Header>}>
                  <SpaceBetween size="xs">
                    {wrEvents.map((e, i) => (
                      <StatusIndicator key={i} type="success">{e.data}</StatusIndicator>
                    ))}
                    {wrStreaming && <StatusIndicator type="loading">Processing...</StatusIndicator>}
                  </SpaceBetween>
                </Container>
              )}

              {wrResult && <StructuredOutput markdown={wrResult} />}
            </SpaceBetween>
          ) },
        ]}
      />
    </SpaceBetween>
  );
}
