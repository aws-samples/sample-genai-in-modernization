import { useState } from "react";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import Alert from "@cloudscape-design/components/alert";
import Tabs from "@cloudscape-design/components/tabs";
import FormField from "@cloudscape-design/components/form-field";
import Textarea from "@cloudscape-design/components/textarea";
import Button from "@cloudscape-design/components/button";
import SpaceBetween from "@cloudscape-design/components/space-between";
import ExpandableSection from "@cloudscape-design/components/expandable-section";
import Box from "@cloudscape-design/components/box";
import AgentStream from "./AgentStream";

export default function ArchitectureDiagram() {
  const [activeTab, setActiveTab] = useState("input");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [xmlResult, setXmlResult] = useState("");

  const handleGenerate = () => {
    if (!description.trim()) {
      setError("Please provide a description of your AWS architecture.");
      return;
    }
    setError("");
    setXmlResult("");
    setStreaming(true);
  };

  const handleDownload = () => {
    const blob = new Blob([xmlResult], { type: "application/xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `aws_architecture_${Date.now()}.drawio`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleOpenDrawio = () => {
    const encoded = encodeURIComponent(xmlResult);
    window.open(`https://app.diagrams.net/#R${encoded}`, "_blank", "noopener,noreferrer");
  };

  return (
    <Container
      header={
        <Header
          variant="h1"
          description="Generate Draw.io XML diagrams from architecture descriptions using AI"
        >
          Architecture Generator
        </Header>
      }
    >
      <SpaceBetween size="m">
        <Alert type="info">
          Describe your AWS architecture and generate a professional Draw.io XML
          diagram with proper AWS service icons, styling, and connections.
        </Alert>

        <Tabs
          activeTabId={activeTab}
          onChange={({ detail }) => setActiveTab(detail.activeTabId)}
          tabs={[
            {
              id: "input",
              label: "Architecture Input",
              content: (
                <SpaceBetween size="m">
                  <FormField
                    label="Describe your AWS architecture"
                    description="Include services, connections, and patterns"
                  >
                    <Textarea
                      value={description}
                      onChange={({ detail }) => setDescription(detail.value)}
                      placeholder="Example: A serverless architecture with API Gateway, Lambda, and DynamoDB..."
                      rows={6}
                    />
                  </FormField>

                  {error && (
                    <Alert
                      type="error"
                      dismissible
                      header="Generation error"
                      onDismiss={() => setError("")}
                    >
                      {error}
                    </Alert>
                  )}

                  <Button
                    variant="primary"
                    onClick={handleGenerate}
                    loading={streaming}
                    disabled={streaming}
                  >
                    Generate diagram
                  </Button>

                  <AgentStream
                    url="/api/generate"
                    body={{ description: description.trim() }}
                    active={streaming}
                    onDone={(xml) => {
                      setXmlResult(xml);
                      setStreaming(false);
                      setActiveTab("result");
                    }}
                    onError={(msg) => {
                      setError(msg);
                      setStreaming(false);
                    }}
                  />
                </SpaceBetween>
              ),
            },
            {
              id: "result",
              label: "Generated Diagram",
              content: xmlResult ? (
                <SpaceBetween size="m">
                  <Alert type="success">
                    Diagram generated successfully. Download the .drawio file and
                    open it in draw.io to view and edit.
                  </Alert>

                  <SpaceBetween direction="horizontal" size="s">
                    <Button
                      variant="primary"
                      iconName="download"
                      onClick={handleDownload}
                    >
                      Download .drawio
                    </Button>
                    <Button iconName="external" onClick={handleOpenDrawio}>
                      Open in draw.io
                    </Button>
                  </SpaceBetween>

                  <ExpandableSection headerText="View XML source">
                    <Box variant="code">{xmlResult}</Box>
                  </ExpandableSection>
                </SpaceBetween>
              ) : (
                <Alert type="info">
                  No diagram generated yet. Go to the Architecture Input tab to
                  get started.
                </Alert>
              ),
            },
          ]}
        />
      </SpaceBetween>
    </Container>
  );
}
