import { useState, useCallback, useRef, useEffect } from "react";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Textarea from "@cloudscape-design/components/textarea";
import Toggle from "@cloudscape-design/components/toggle";
import Alert from "@cloudscape-design/components/alert";
import StatusIndicator from "@cloudscape-design/components/status-indicator";
import ExpandableSection from "@cloudscape-design/components/expandable-section";
import mermaid from "mermaid";
import { useSessionState } from "./App";

mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "strict" });

/* ------------------------------------------------------------------ */
/* Mermaid diagram renderer                                            */
/* ------------------------------------------------------------------ */
let mermaidCounter = 5000;
function MermaidDiagram({ chart }: { chart: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const id = `mermaid-wis-${++mermaidCounter}`;
    mermaid.render(id, chart.trim()).then(({ svg }) => {
      // SVG comes from mermaid.render with securityLevel "strict", which sanitises it with DOMPurify.
      // nosemgrep: javascript.browser.security.insecure-innerhtml, javascript.browser.security.insecure-document-method
      if (containerRef.current) containerRef.current.innerHTML = svg;
    }).catch(() => {
      if (containerRef.current) containerRef.current.textContent = chart;
    });
  }, [chart]);

  return <div ref={containerRef} style={{ background: "#fff", borderRadius: 4, padding: 8, margin: "6px 0", overflowX: "auto" }} />;
}

/* ------------------------------------------------------------------ */
/* Context chip definitions                                            */
/* ------------------------------------------------------------------ */
interface ContextChip {
  label: string;
  sessionKey: string;
  truncateAt: number;
}

/* Max characters sent per output as chat context */
const CONTEXT_CHAR_LIMIT = 100000;

const CONTEXT_CHIPS: ContextChip[] = [
  { label: "Assessment", sessionKey: "ma-assessment", truncateAt: CONTEXT_CHAR_LIMIT },
  { label: "Strategy", sessionKey: "ma-strategy", truncateAt: CONTEXT_CHAR_LIMIT },
  { label: "Cost Estimation", sessionKey: "ac-cost-result", truncateAt: CONTEXT_CHAR_LIMIT },
  { label: "MAP Milestone", sessionKey: "ac-milestone-result", truncateAt: CONTEXT_CHAR_LIMIT },
  { label: "Landing Zone", sessionKey: "ep-lz-design", truncateAt: CONTEXT_CHAR_LIMIT },
  { label: "Task Breakdown", sessionKey: "ep-tb-result", truncateAt: CONTEXT_CHAR_LIMIT },
  { label: "Wave Runbook", sessionKey: "ep-wr-result", truncateAt: CONTEXT_CHAR_LIMIT },
  { label: "Resource Plan", sessionKey: "ep-rp-result", truncateAt: CONTEXT_CHAR_LIMIT },
];

function getSessionData(key: string): string | null {
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || (typeof parsed === "string" && !parsed.trim())) return null;
    return typeof parsed === "object" ? JSON.stringify(parsed) : parsed;
  } catch {
    return null;
  }
}

function truncate(text: string, maxLen: number): string {
  return text.length > maxLen ? text.slice(0, maxLen) + "\n...[truncated]" : text;
}

/* ------------------------------------------------------------------ */
/* Markdown renderer for assistant messages                            */
/* ------------------------------------------------------------------ */
function renderBold(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**") ? <strong key={i}>{p.slice(2, -2)}</strong> : p
  );
}

function renderMarkdown(content: string, allowMermaid: boolean = true): React.ReactNode {
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // Code block
    if (trimmed.startsWith("```")) {
      const lang = trimmed.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      const code = codeLines.join("\n");
      if (lang === "mermaid" && allowMermaid) {
        elements.push(<MermaidDiagram key={elements.length} chart={code} />);
      } else {
        elements.push(
          <pre key={elements.length} style={{ background: "rgba(0,0,0,0.06)", padding: 10, borderRadius: 4, overflowX: "auto", fontSize: 12, margin: "6px 0" }}>
            <code>{code}</code>
          </pre>
        );
      }
      continue;
    }

    // Table row (detect header + separator)
    if (trimmed.startsWith("|") && i + 1 < lines.length && /^\|[\s\-:|]+\|/.test(lines[i + 1].trim())) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        tableLines.push(lines[i]);
        i++;
      }
      if (tableLines.length >= 2) {
        const parseRow = (r: string) => r.split("|").map((c) => c.trim()).filter((c) => c !== "");
        const headers = parseRow(tableLines[0]);
        const rows = tableLines.slice(2).map(parseRow);
        elements.push(
          <table key={elements.length} style={{ borderCollapse: "collapse", margin: "6px 0", fontSize: 13, width: "100%" }}>
            <thead>
              <tr>{headers.map((h, hi) => <th key={hi} style={{ border: "1px solid #d5dbdb", padding: "4px 8px", background: "#f2f3f3", textAlign: "left" }}>{renderBold(h)}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => (
                <tr key={ri}>{row.map((cell, ci) => <td key={ci} style={{ border: "1px solid #d5dbdb", padding: "4px 8px" }}>{renderBold(cell)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        );
      }
      continue;
    }

    // Headings
    if (trimmed.startsWith("## ")) {
      elements.push(<div key={elements.length} style={{ fontWeight: 700, fontSize: 16, marginTop: 12, marginBottom: 4 }}>{renderBold(trimmed.slice(3))}</div>);
      i++; continue;
    }
    if (trimmed.startsWith("### ")) {
      elements.push(<div key={elements.length} style={{ fontWeight: 700, fontSize: 14, marginTop: 10, marginBottom: 2 }}>{renderBold(trimmed.slice(4))}</div>);
      i++; continue;
    }
    if (trimmed.startsWith("#### ")) {
      elements.push(<div key={elements.length} style={{ fontWeight: 600, fontSize: 13, marginTop: 8 }}>{renderBold(trimmed.slice(5))}</div>);
      i++; continue;
    }

    // Numbered list
    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      elements.push(<div key={elements.length} style={{ paddingLeft: 16, margin: "2px 0" }}>{numMatch[1]}. {renderBold(numMatch[2])}</div>);
      i++; continue;
    }

    // Bullet list
    if (trimmed.startsWith("- ") || trimmed.startsWith("• ") || trimmed.startsWith("* ")) {
      const indent = line.startsWith("  ") ? 32 : 16;
      const bullet = indent > 16 ? "◦" : "•";
      elements.push(<div key={elements.length} style={{ paddingLeft: indent, margin: "2px 0" }}>{bullet} {renderBold(trimmed.replace(/^[-•*]\s+/, ""))}</div>);
      i++; continue;
    }

    // Empty line
    if (!trimmed) {
      elements.push(<div key={elements.length} style={{ height: 6 }} />);
      i++; continue;
    }

    // Regular text
    elements.push(<div key={elements.length} style={{ margin: "2px 0" }}>{renderBold(trimmed)}</div>);
    i++;
  }

  return <>{elements}</>;
}

/* ------------------------------------------------------------------ */
/* Chat message type                                                   */
/* ------------------------------------------------------------------ */
interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

/* ------------------------------------------------------------------ */
/* WhatIfScenario component                                            */
/* ------------------------------------------------------------------ */
export default function WhatIfScenario() {
  const [chatMessages, setChatMessages] = useSessionState<ChatMessage[]>("wis-chat-history", []);
  const [chatInput, setChatInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const [enabledChips, setEnabledChips] = useState<Record<string, boolean>>({});

  const availableChips = CONTEXT_CHIPS.filter((c) => !!getSessionData(c.sessionKey));
  const enabledCount = availableChips.filter((c) => enabledChips[c.sessionKey]).length;
  const cutLabels = availableChips
    .filter((c) => enabledChips[c.sessionKey] && (getSessionData(c.sessionKey) || "").length > c.truncateAt)
    .map((c) => c.label);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const buildContext = useCallback(() => {
    const context: Record<string, string> = {};
    for (const chip of CONTEXT_CHIPS) {
      if (!enabledChips[chip.sessionKey]) continue;
      const data = getSessionData(chip.sessionKey);
      if (data) context[chip.label] = truncate(data, chip.truncateAt);
    }
    return context;
  }, [enabledChips]);

  const handleSend = useCallback(async () => {
    if (!chatInput.trim() || streaming) return;
    if (enabledCount === 0) {
      setError("Toggle at least one context chip before chatting.");
      return;
    }
    setError("");

    const userMsg: ChatMessage = { role: "user", content: chatInput.trim() };
    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    setStreaming(true);

    const history = [...chatMessages, userMsg].map((m) => ({ role: m.role, content: m.content }));
    setChatMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      const context = buildContext();
      const res = await fetch("/api/migration/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg.content,
          assessment: context,
          history: history.slice(0, -1),
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        setChatMessages((prev) => {
          const u = [...prev];
          u[u.length - 1] = { role: "assistant", content: `Error: ${err.error || "Chat failed"}` };
          return u;
        });
        setStreaming(false);
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
            if (currentEventType === "text") {
              setChatMessages((prev) => {
                const u = [...prev];
                const last = u[u.length - 1];
                u[u.length - 1] = { ...last, content: last.content + data };
                return u;
              });
            } else if (currentEventType === "error") {
              setChatMessages((prev) => {
                const u = [...prev];
                u[u.length - 1] = { role: "assistant", content: `Error: ${data}` };
                return u;
              });
            }
            currentEventType = "";
          }
        }
      }
    } catch (err: any) {
      setChatMessages((prev) => {
        const u = [...prev];
        u[u.length - 1] = { role: "assistant", content: `Error: ${err.message}` };
        return u;
      });
    }
    setStreaming(false);
  }, [chatInput, streaming, chatMessages, enabledCount, buildContext]);

  const handleClear = () => {
    setChatMessages([]);
    setError("");
  };

  return (
    <SpaceBetween size="l">
      <Header
        variant="h1"
        description="Ask what-if questions across your generated outputs"
      >
        What-If Scenario
      </Header>

      {/* Context chips — collapsed by default */}
      <ExpandableSection
        headerText={`Context Selection (${enabledCount} of ${availableChips.length} selected)`}
        variant="container"
      >
        <SpaceBetween size="s">
          {availableChips.length === 0 ? (
            <Box variant="p" color="text-body-secondary">
              No outputs generated yet. Complete an assessment or generate outputs from other pages first.
            </Box>
          ) : (
            <>
              <Box variant="p" fontSize="body-s" color="text-body-secondary">
                Toggle the outputs you want to include as context for your what-if questions.
              </Box>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
                {availableChips.map((chip) => (
                  <Toggle
                    key={chip.sessionKey}
                    checked={!!enabledChips[chip.sessionKey]}
                    onChange={({ detail }) =>
                      setEnabledChips((prev) => ({ ...prev, [chip.sessionKey]: detail.checked }))
                    }
                  >
                    {chip.label}
                  </Toggle>
                ))}
              </div>

              {cutLabels.length > 0 && (
                <Alert type="warning">
                  {`Only the first ${CONTEXT_CHAR_LIMIT.toLocaleString()} characters of these outputs are shared with the chat: ${cutLabels.join(", ")}.`}
                </Alert>
              )}

              {/* Preview of enabled context */}
              {enabledCount > 0 && (
                <ExpandableSection headerText="Preview selected context">
                  <SpaceBetween size="m">
                    {availableChips.filter((c) => enabledChips[c.sessionKey]).map((chip) => {
                      const data = getSessionData(chip.sessionKey) || "";
                      const isJson = data.trim().startsWith("{") || data.trim().startsWith("[");

                      // Summarize assessment JSON instead of showing raw
                      let summaryView = null;
                      if (isJson && chip.label === "Assessment") {
                        try {
                          const parsed = JSON.parse(data);
                          const disc = parsed.discovery || {};
                          const dep = parsed.dependency || {};
                          const apps = disc.app_analysis?.applications || [];
                          const infra = disc.infra_analysis?.components || [];
                          const exec = disc.executive_summary || {};
                          const depSum = dep.dependency_summary || {};
                          const scores = dep.complexity_scores || {};
                          summaryView = (
                            <SpaceBetween size="m">
                              <ExpandableSection headerText={`IT Discovery (${apps.length} apps, ${infra.length} infra)`} defaultExpanded>
                                <SpaceBetween size="xs">
                                  <Box variant="small"><strong>Risk:</strong> {exec.overall_risk_level || "—"} | <strong>Readiness:</strong> {exec.migration_readiness?.readiness_pct ?? "—"}%</Box>
                                  {exec.migration_readiness?.summary && <Box variant="small">{exec.migration_readiness.summary}</Box>}
                                  {apps.length > 0 && (
                                    <Box variant="small"><strong>Apps:</strong> {apps.map((a: any) => `${a.name} (${a.type}, ${a.criticality})`).join(" · ")}</Box>
                                  )}
                                  {exec.key_findings?.length > 0 && (
                                    <Box variant="small"><strong>Findings:</strong> {exec.key_findings.map((f: any) => f.title).join(" · ")}</Box>
                                  )}
                                </SpaceBetween>
                              </ExpandableSection>
                              {dep && (
                                <ExpandableSection headerText={`Application Dependencies (${depSum.total_edges || 0} edges, ${dep.clusters?.length || 0} clusters)`} defaultExpanded>
                                  <SpaceBetween size="xs">
                                    <Box variant="small"><strong>Standalone:</strong> {depSum.standalone_count || 0} | <strong>Avg deps:</strong> {depSum.avg_dependencies || 0} | <strong>Most connected:</strong> {depSum.most_connected_app || "—"}</Box>
                                    {dep.circular_dependencies?.length > 0 && <Box variant="small"><strong>Circular deps:</strong> {dep.circular_dependencies.length} cycle(s)</Box>}
                                    {dep.key_findings?.length > 0 && (
                                      <Box variant="small"><strong>Findings:</strong> {dep.key_findings.map((f: any) => f.title).join(" · ")}</Box>
                                    )}
                                    {Object.keys(scores).length > 0 && (
                                      <Box variant="small"><strong>Complexity:</strong> {Object.entries(scores).map(([name, s]: [string, any]) => `${name}: ${s.score}`).join(" · ")}</Box>
                                    )}
                                  </SpaceBetween>
                                </ExpandableSection>
                              )}
                            </SpaceBetween>
                          );
                        } catch { /* fall through to raw */ }
                      }

                      return (
                        <ExpandableSection key={chip.sessionKey} headerText={chip.label} defaultExpanded>
                          <div style={{ maxHeight: 500, overflowY: "auto" }}>
                            {summaryView ? summaryView : isJson ? (
                              <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0, fontSize: 11, background: "rgba(0,0,0,0.04)", padding: 10, borderRadius: 4 }}>{data}</pre>
                            ) : (
                              <div style={{ fontSize: 13, lineHeight: 1.5 }}>
                                {renderMarkdown(data, false)}
                              </div>
                            )}
                          </div>
                        </ExpandableSection>
                      );
                    })}
                  </SpaceBetween>
                </ExpandableSection>
              )}
            </>
          )}
        </SpaceBetween>
      </ExpandableSection>

      {error && <Alert type="error" dismissible onDismiss={() => setError("")}>{error}</Alert>}

      {/* Chat conversation */}
      <Container
        header={
          <Header
            variant="h2"
            actions={
              chatMessages.length > 0 ? (
                <Button variant="normal" onClick={handleClear}>Clear Chat</Button>
              ) : undefined
            }
          >
            Conversation
          </Header>
        }
      >
        <div style={{ maxHeight: 600, overflowY: "auto", padding: "4px 0" }}>
          <SpaceBetween size="s">
            {chatMessages.length === 0 && (
              <Box variant="p" color="text-body-secondary" padding="l" textAlign="center">
                Select context above, then ask a what-if question to get started.
              </Box>
            )}

            {chatMessages.map((msg, i) => (
              <div
                key={i}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  background: msg.role === "user" ? "#f0f4ff" : "#f9f9f9",
                  borderLeft: msg.role === "user" ? "3px solid #0972d3" : "3px solid #FF9900",
                }}
              >
                <Box variant="small" color="text-body-secondary" margin={{ bottom: "xxs" }}>
                  {msg.role === "user" ? "You" : "Assistant"}
                </Box>
                <div style={{ fontSize: 14, lineHeight: 1.5 }}>
                  {msg.role === "assistant" ? (
                    renderMarkdown(msg.content, !(streaming && i === chatMessages.length - 1))
                  ) : (
                    <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>
                  )}
                  {streaming && i === chatMessages.length - 1 && msg.role === "assistant" && !msg.content && (
                    <StatusIndicator type="loading">Thinking...</StatusIndicator>
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </SpaceBetween>
        </div>
      </Container>

      {/* Input — multi-line textarea */}
      <Container>
        <SpaceBetween size="s">
          <Textarea
            value={chatInput}
            onChange={({ detail }) => setChatInput(detail.value)}
            placeholder="Ask a what-if question... (e.g., What if we move Wave 3 apps to containers instead of rehost?)"
            disabled={streaming || availableChips.length === 0}
            rows={3}
          />
          <Button
            variant="primary"
            onClick={handleSend}
            loading={streaming}
            disabled={!chatInput.trim() || availableChips.length === 0}
          >
            Send
          </Button>
        </SpaceBetween>
      </Container>
    </SpaceBetween>
  );
}
