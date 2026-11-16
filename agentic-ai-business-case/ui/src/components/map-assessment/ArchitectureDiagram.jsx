import React, { useState, useEffect } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  FormField,
  Textarea,
  Button,
  Alert,
  ExpandableSection,
  Box,
  Tabs,
  Toggle,
  Spinner
} from '@cloudscape-design/components';
import { getApiUrl } from '../../utils/apiConfig.js';

// Default input - pre-filled so user can use immediately
const DEFAULT_INPUT = `A three-tier web application architecture with:
- Application Load Balancer for traffic distribution
- EC2 instances in Auto Scaling groups across multiple availability zones
- RDS PostgreSQL database with Multi-AZ deployment and read replicas
- ElastiCache Redis for session management and caching
- S3 buckets for static content and backups
- CloudFront CDN for global content delivery
- Route 53 for DNS management
- VPC with public and private subnets across 3 availability zones
- NAT Gateways for outbound internet access from private subnets
- Security groups and NACLs for network security`;

// Default prompt template
const DEFAULT_PROMPT = `As an AWS architecture diagram expert, generate a professional Draw.io XML diagram based on the provided architecture description.

Create a comprehensive diagram that includes:

## (1) Network Architecture
- VPC structure with CIDR blocks
- Availability zones and regions
- Public and private subnets
- Internet Gateway and NAT Gateways
- Route tables and routing

## (2) Compute Resources
- EC2 instances with appropriate icons
- Auto Scaling groups
- Load balancers (ALB/NLB/CLB)
- Lambda functions if applicable
- Container services (ECS/EKS) if applicable

## (3) Storage and Database
- RDS databases with Multi-AZ configuration
- DynamoDB tables if applicable
- S3 buckets with appropriate access patterns
- EBS volumes
- EFS file systems if applicable

## (4) Networking and Content Delivery
- CloudFront distributions
- Route 53 DNS configuration
- VPN or Direct Connect if applicable
- API Gateway if applicable

## (5) Security Components
- Security groups with inbound/outbound rules
- Network ACLs
- WAF if applicable
- Shield if applicable
- IAM roles and policies representation

## (6) Monitoring and Management
- CloudWatch monitoring
- CloudTrail logging
- Systems Manager if applicable

## (7) Diagram Layout and Styling
- Clear visual hierarchy
- Proper grouping of related components
- Color coding for different layers (public/private)
- Connection lines showing data flow
- Labels and annotations for clarity
- AWS official icons and styling

Generate valid Draw.io XML format that can be directly imported into Draw.io or diagrams.net.`;

function ArchitectureDiagram() {
  const [description, setDescription] = useState(DEFAULT_INPUT);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [diagramXml, setDiagramXml] = useState(null);
  const [activeTabId, setActiveTabId] = useState('input');
  
  // Prompt customization
  const [customPrompt, setCustomPrompt] = useState(DEFAULT_PROMPT);
  const [useCustomPrompt, setUseCustomPrompt] = useState(false);
  
  // Load saved custom prompt from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('map_custom_prompt_diagram');
    if (saved) {
      setCustomPrompt(saved);
      setUseCustomPrompt(true);
    }
  }, []);
  
  // Save custom prompt
  const saveCustomPrompt = () => {
    localStorage.setItem('map_custom_prompt_diagram', customPrompt);
    alert('✓ Custom prompt saved successfully!');
  };
  
  // Reset to default
  const resetPrompt = () => {
    if (confirm('Reset prompt to default? This cannot be undone.')) {
      setCustomPrompt(DEFAULT_PROMPT);
      setUseCustomPrompt(false);
      localStorage.removeItem('map_custom_prompt_diagram');
      alert('✓ Prompt reset to default!');
    }
  };

  const handleGenerate = async () => {
    if (!description.trim()) {
      setError('Please provide an architecture description');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const requestBody = { description };
      
      // Add custom prompt if enabled
      if (useCustomPrompt && customPrompt.trim()) {
        requestBody.custom_prompt = customPrompt;
      }
      
      const response = await fetch(getApiUrl('/map/architecture-diagram/generate'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });

      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.message);
      }

      setDiagramXml(result.diagramXml);
      // Switch to results tab to show the generated diagram
      setActiveTabId('results');
    } catch (err) {
      setError(err.message || 'Failed to generate architecture diagram');
    } finally {
      setLoading(false);
    }
  };

  const downloadXml = () => {
    const blob = new Blob([diagramXml], { type: 'application/xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'aws_architecture_diagram.drawio';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const openInDrawio = () => {
    const encodedXml = encodeURIComponent(diagramXml);
    window.open(`https://app.diagrams.net/?lightbox=1#R${encodedXml}`, '_blank', 'noopener,noreferrer');
  };

  return (
    <SpaceBetween size="l">
      <Container
        header={
          <Header
            variant="h1"
            description="Generate AWS Diagrams in Draw.io XML Format"
          >
            Architecture Diagram Generator
          </Header>
        }
      >
        <SpaceBetween size="m">
          <Alert type="info">
            Describe your desired AWS architecture and generate a professional diagram 
            in Draw.io XML format. The diagram can be opened directly in Draw.io for 
            further customization. A sample description is pre-filled.
          </Alert>

          <Tabs
            activeTabId={activeTabId}
            onChange={({ detail }) => setActiveTabId(detail.activeTabId)}
            tabs={[
              {
                id: 'input',
                label: 'Architecture Input',
                content: (
                  <SpaceBetween size="l">
                    <FormField
                      label="Architecture Description"
                      description="Pre-filled with sample architecture - edit as needed or use as-is"
                    >
                      <Textarea
                        value={description}
                        onChange={({ detail }) => setDescription(detail.value)}
                        rows={12}
                      />
                    </FormField>

                    {error && (
                      <Alert
                        type="error"
                        dismissible
                        onDismiss={() => setError(null)}
                      >
                        {error}
                      </Alert>
                    )}

                    {loading && (
                      <Box textAlign="center">
                        <SpaceBetween size="m" alignItems="center">
                          <Spinner size="large" />
                          <Box variant="p" color="text-body-secondary">
                            Generating architecture diagram... This may take a few minutes.
                          </Box>
                        </SpaceBetween>
                      </Box>
                    )}

                    <Box textAlign="center">
                      <Button
                        variant="primary"
                        onClick={handleGenerate}
                        disabled={loading || !description.trim()}
                      >
                        Generate Diagram
                      </Button>
                    </Box>
                  </SpaceBetween>
                )
              },
              {
                id: 'prompt',
                label: 'Customize Prompt',
                content: (
                  <SpaceBetween size="l">
                    <Alert type="info">
                      The default diagram generation prompt is shown below. Toggle "Use Custom Prompt" to modify it for your specific needs.
                      Your custom prompt will be saved and used for future diagram generations.
                    </Alert>

                    <FormField>
                      <Toggle
                        checked={useCustomPrompt}
                        onChange={({ detail }) => setUseCustomPrompt(detail.checked)}
                      >
                        <Box variant="strong">Use Custom Prompt</Box>
                      </Toggle>
                    </FormField>

                    <FormField
                      label="Generation Prompt"
                      description={useCustomPrompt ? "Edit the prompt below to customize the diagram generation" : "Default prompt (toggle above to edit)"}
                    >
                      <Textarea
                        value={customPrompt}
                        onChange={({ detail }) => setCustomPrompt(detail.value)}
                        rows={25}
                        disabled={!useCustomPrompt}
                      />
                    </FormField>

                    <SpaceBetween direction="horizontal" size="xs">
                      <Button
                        variant="primary"
                        onClick={saveCustomPrompt}
                        disabled={!useCustomPrompt}
                      >
                        Save Custom Prompt
                      </Button>
                      <Button
                        onClick={resetPrompt}
                      >
                        Reset to Default
                      </Button>
                    </SpaceBetween>

                    <ExpandableSection
                      headerText="Prompt Customization Tips"
                      variant="default"
                    >
                      <SpaceBetween size="s">
                        <Box variant="p">
                          <strong>Tips for customizing the prompt:</strong>
                        </Box>
                        <ul>
                          <li>Add specific AWS services you want to emphasize</li>
                          <li>Include custom styling or color schemes</li>
                          <li>Specify particular diagram layout preferences</li>
                          <li>Add industry-specific architectural patterns</li>
                          <li>Include specific security or compliance visualizations</li>
                          <li>Adjust the level of detail for diagram components</li>
                        </ul>
                      </SpaceBetween>
                    </ExpandableSection>
                  </SpaceBetween>
                )
              },
              {
                id: 'results',
                label: 'Generated Diagram',
                disabled: !diagramXml,
                content: diagramXml && (
                  <ExpandableSection
                    headerText="Generated Diagram"
                    variant="container"
                    defaultExpanded
                  >
                    <SpaceBetween size="m">
                      <Alert type="success">
                        Diagram generated successfully! You can download the XML file or open it directly in Draw.io.
                      </Alert>

                      <SpaceBetween direction="horizontal" size="xs">
                        <Button
                          onClick={downloadXml}
                          iconName="download"
                        >
                          Download XML
                        </Button>
                        <Button
                          onClick={openInDrawio}
                          iconName="external"
                        >
                          Open in Draw.io
                        </Button>
                      </SpaceBetween>

                      <ExpandableSection
                        headerText="View XML Source"
                        variant="default"
                      >
                        <Box padding="s">
                          <pre style={{
                            backgroundColor: '#f4f4f4',
                            padding: '12px',
                            borderRadius: '4px',
                            overflow: 'auto',
                            maxHeight: '400px',
                            fontSize: '12px',
                            fontFamily: 'monospace'
                          }}>
                            {diagramXml}
                          </pre>
                        </Box>
                      </ExpandableSection>
                    </SpaceBetween>
                  </ExpandableSection>
                )
              }
            ]}
          />
        </SpaceBetween>
      </Container>
    </SpaceBetween>
  );
}

export default ArchitectureDiagram;
