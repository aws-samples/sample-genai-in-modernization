import React, { useState, useEffect } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  FormField,
  FileUpload,
  Button,
  Alert,
  ExpandableSection,
  Box,
  Tabs,
  Spinner,
  Badge,
  ColumnLayout,
  Toggle,
  Textarea
} from '@cloudscape-design/components';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getApiUrl } from '../../utils/apiConfig.js';
import { useMapAssessment } from '../../contexts/MapAssessmentContext.jsx';

// The comprehensive service analysis prompt
const SERVICE_ANALYSIS_PROMPT = `I need you to analyze an AWS Pricing Calculator CSV file for a cloud migration and provide a comprehensive service completeness analysis and gap identification.

**Context:**
- This is a cloud migration infrastructure assessment
- Customers typically underestimate non-compute infrastructure by 10x
- We need to identify missing services across 6 critical categories to ensure production-ready, well-architected solutions

**Analysis Required:**

1. **INFRASTRUCTURE VALIDATION**
- Extract and calculate total infrastructure costs from the CSV
- Break down costs by service category:
  * Compute (EC2, Fargate, Lambda, etc.)
  * Storage (S3, EBS, EFS, FSx, etc.)
  * Database (RDS, Aurora, DynamoDB, etc.)
  * Network (ALB, NLB, CloudFront, Route 53, Data Transfer, etc.)
  * Security (KMS, WAF, GuardDuty, Secrets Manager, etc.)
  * Monitoring (CloudWatch, CloudTrail, X-Ray, etc.)
- Calculate compute vs non-compute ratio
- Compare against production-ready benchmark (56% compute, 44% non-compute)

2. **GAP ANALYSIS - 6 CRITICAL CATEGORIES**

**Category 1: Backup & Recovery**
- Check for: AWS Backup services (including EFS Backup, VMware Backup, Timestream Backup, Storage Gateway Backup, FSx Backup, S3 Backup, Redshift Backup, RDS Backup, EBS Backup, DynamoDB Backup, Aurora Backup, Neptune Backup, DocumentDB Backup, SAP HANA Backup, Aurora DSQL Backup), EBS snapshots, S3 Glacier, cross-region backup replication
- IMPORTANT: If ANY of these backup services are present (DynamoDB Backup, Aurora Backup, RDS Backup, etc.), AWS Backup IS included - do NOT flag as missing
- Common gap: Customers plan database compute but forget backup storage
- Expected: 2-3% of total infrastructure costs
- Questions: "What's your backup retention policy? Do you need cross-region backups?"

**Category 2: Storage Infrastructure**
- Check for: S3 (all tiers), EFS, FSx (Windows/Lustre/NetApp/OpenZFS), Storage Gateway, EBS volumes
- Common gap: Customers plan S3 Standard but miss FSx, Storage Gateway, S3 Intelligent-Tiering
- Expected: 25-30% of total infrastructure costs
- Questions: "Do you have Windows file shares? Need hybrid storage connectivity?"

**Category 3: DR/HA Configuration**
- Check for: Multi-AZ deployments, cross-region replication, Elastic Disaster Recovery, Route 53 health checks
- Common gap: Customers plan single-region only, no DR orchestration
- Expected: 1-2% of total infrastructure costs
- Questions: "What's your RTO/RPO? Need disaster recovery in another region?"

**Category 4: Network Services**
- Check for: ALB/NLB, CloudFront, Route 53, Transit Gateway, Direct Connect, VPN, Data Transfer, Public IPv4, NAT Gateway, Network Firewall
- Common gap: Customers plan load balancers but miss CDN, DNS, data transfer costs, IPv4 addressing
- Expected: 10-15% of total infrastructure costs
- Questions: "Do you serve content globally? How much outbound traffic? How many public IPs? Even though CCOE/central team is managing networking, the increase in traffic wrt NAT Gateway, Transit Gateway Attachment should be included, isn't it?"

**Category 5: Observability & Monitoring**
- Check for: CloudWatch (metrics, logs, alarms), CloudTrail, X-Ray, VPC Flow Logs, Config, Systems Manager
- Common gap: Customers assume monitoring is "free" or "included"
- Expected: 2-4% of total infrastructure costs
- Questions: "What monitoring tools do you use today? Need audit logging for compliance? Even if 3rd party tools are going to be used, are they not integrated by using cloudwatch & Kinesis which means you need to hold data for short duration in AWS monitoring services?"

**Category 6: Security & Compliance**
- Check for: KMS, WAF, Shield, GuardDuty, Security Hub, Secrets Manager, Certificate Manager, Network Firewall, Macie
- Common gap: Customers include only KMS, miss application-layer security and credential management
- Expected: 2-4% of total infrastructure costs
- Questions: "What compliance frameworks apply? How do you manage secrets/credentials? How about encryption at rest and encryption in transit & certificate management?"

3. **OUTPUT FORMAT**

Provide the analysis in this structure:

**A. INFRASTRUCTURE COMPLETENESS SUMMARY**
\`\`\`
Total Annual Infrastructure Cost: $XXX,XXX
Breakdown:
- Compute: $XXX,XXX (XX%)
- Storage: $XXX,XXX (XX%)
- Database: $XXX,XXX (XX%)
- Network: $XXX,XXX (XX%)
- Security: $XXX,XXX (XX%)
- Monitoring: $XXX,XXX (XX%)

Compute vs Non-Compute Ratio: XX% / XX%
Production-Ready Benchmark: 56% / 44%
Assessment: [Complete / Incomplete / Needs Review]
\`\`\`

**B. SERVICE GAP ANALYSIS BY CATEGORY**

For each of the 6 categories, provide:
\`\`\`
Category: [Name]
Status: [Complete / Partial / Missing]
Current Cost: $XXX,XXX (XX% of total)
Expected Cost: $XXX,XXX (XX% of total)
Gap: $XXX,XXX
Services Found: [List]
Services Missing: [List with estimated cost impact]
Priority: [High / Medium / Low]
Questions to Ask Customer: [Specific questions]
\`\`\`

**C. MISSING SERVICES SUMMARY**

Create a prioritized table:
| Priority | Service | Category | Estimated Cost | Why It's Missing | Questions to Ask |
|----------|---------|----------|----------------|------------------|------------------|
| HIGH     | ...     | ...      | $XX,XXX        | ...              | ...              |

**D. RECOMMENDATIONS**

Provide specific, actionable recommendations:
1. Immediate Actions (High Priority)
2. Secondary Review (Medium Priority)
3. Future Consideration (Low Priority)

**E. ESTIMATED ADDITIONAL INFRASTRUCTURE NEEDED**
\`\`\`
Conservative Estimate: $XXX,XXX - $XXX,XXX/year
Realistic Estimate: $XXX,XXX - $XXX,XXX/year
\`\`\`

**F. COMPLETENESS RED FLAGS**

List any red flags found:
- ❌ No backup services (check for ANY service ending in "Backup" like DynamoDB Backup, Aurora Backup, RDS Backup, etc.)
- ❌ No CDN for web applications
- ❌ Security services <1% of total costs
- etc.

**G. NEXT STEPS**

Provide 5-7 specific action items for engaging with the customer.

4. **KEY COMPLETENESS CHECKS**

Flag these red flags:
- ❌ No backup services (check for: AWS Backup, DynamoDB Backup, Aurora Backup, RDS Backup, EBS Backup, or any other *Backup service - if ANY are present, backup IS included)
- ❌ No CDN (CloudFront) for web applications
- ❌ No DNS service (Route 53)
- ❌ No WAF for web applications
- ❌ No Secrets Manager for credential management
- ❌ No CloudTrail for audit logging
- ❌ Data transfer costs seem too low (<5% of total)
- ❌ Security services <1% of total costs
- ❌ No monitoring beyond basic CloudWatch
- ❌ Compute >80% of total (non-compute severely underestimated)

**Please analyze the provided CSV data and provide the complete analysis following this format.**`;

function ServiceAnalysis() {
  const { 
    serviceAnalysisData, 
    setServiceAnalysisData, 
    resetServiceAnalysis
  } = useMapAssessment();
  
  const [calculatorFile, setCalculatorFile] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analysis, setAnalysis] = useState(serviceAnalysisData?.analysis || null);
  const [recordsProcessed, setRecordsProcessed] = useState(0);
  const [activeTabId, setActiveTabId] = useState('upload');
  
  // Prompt customization
  const [customPrompt, setCustomPrompt] = useState(SERVICE_ANALYSIS_PROMPT);
  const [useCustomPrompt, setUseCustomPrompt] = useState(false);
  
  // Load existing data from context on mount
  useEffect(() => {
    if (serviceAnalysisData?.analysis) {
      setAnalysis(serviceAnalysisData.analysis);
      setActiveTabId('results');
    }
  }, []);

  // Load saved custom prompt from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('map_custom_prompt_service_analysis');
    if (saved) {
      setCustomPrompt(saved);
      setUseCustomPrompt(true);
    }
  }, []);
  
  // Save custom prompt
  const saveCustomPrompt = () => {
    localStorage.setItem('map_custom_prompt_service_analysis', customPrompt);
    alert('✓ Custom prompt saved successfully!');
  };
  
  // Reset to default
  const resetPrompt = () => {
    if (confirm('Reset prompt to default? This cannot be undone.')) {
      setCustomPrompt(SERVICE_ANALYSIS_PROMPT);
      setUseCustomPrompt(false);
      localStorage.removeItem('map_custom_prompt_service_analysis');
      alert('✓ Prompt reset to default!');
    }
  };

  const handleAnalyze = async () => {
    if (calculatorFile.length === 0) {
      setError('Please upload an AWS Calculator CSV file');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', calculatorFile[0]);
      formData.append('custom_prompt', useCustomPrompt ? customPrompt : SERVICE_ANALYSIS_PROMPT);

      const response = await fetch(getApiUrl('/map/service-analysis/analyze'), {
        method: 'POST',
        body: formData
      });

      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.message);
      }

      setAnalysis(result.analysis);
      setRecordsProcessed(result.recordsProcessed || 0);
      // Save to context
      setServiceAnalysisData({ analysis: result.analysis });
      // Switch to results tab
      setActiveTabId('results');
    } catch (err) {
      setError(err.message || 'Failed to analyze services');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setAnalysis(null);
    setRecordsProcessed(0);
    setCalculatorFile([]);
    setActiveTabId('upload');
    resetServiceAnalysis();
  };

  const downloadMarkdown = (content, filename) => {
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleGenerateCalculator = () => {
    // Calculator Generator has been removed
    // Users can manually create estimates in AWS Pricing Calculator
  };

  return (
    <SpaceBetween size="l">
      <Container
        header={
          <Header
            variant="h1"
            description="Identify Missing Services for Complete, Production-Ready Infrastructure"
            actions={
              <Button onClick={handleReset} disabled={!analysis}>
                Reset
              </Button>
            }
          >
            Service Analysis
          </Header>
        }
      >
        <SpaceBetween size="m">
          <Alert type="info">
            <SpaceBetween size="xs">
              <Box variant="strong">Ensure Complete Infrastructure Coverage</Box>
              <Box>
                Upload your AWS Pricing Calculator CSV to identify missing services across 6 critical 
                categories: Backup & Recovery, Storage, DR/HA, Network, Observability, and Security. 
                Customers typically underestimate non-compute infrastructure by 10x.
              </Box>
              <ColumnLayout columns={3} variant="text-grid">
                <div>
                  <Box variant="awsui-key-label">Production-Ready Benchmark</Box>
                  <Box>56% Compute / 44% Non-Compute</Box>
                </div>
                <div>
                  <Box variant="awsui-key-label">Typical Gap</Box>
                  <Box>10-40% of infrastructure missing</Box>
                </div>
                <div>
                  <Box variant="awsui-key-label">Analysis Time</Box>
                  <Box>2-3 minutes</Box>
                </div>
              </ColumnLayout>
            </SpaceBetween>
          </Alert>

          <Tabs
            activeTabId={activeTabId}
            onChange={({ detail }) => setActiveTabId(detail.activeTabId)}
            tabs={[
              {
                id: 'upload',
                label: 'Upload & Analyze',
                content: (
                  <SpaceBetween size="l">
                    <FormField
                      label="AWS Pricing Calculator CSV"
                      description="Upload your AWS Calculator export file for comprehensive service completeness analysis"
                    >
                      <FileUpload
                        value={calculatorFile}
                        onChange={({ detail }) => setCalculatorFile(detail.value)}
                        accept=".csv"
                        constraintText="CSV files only"
                      />
                    </FormField>

                    <ExpandableSection
                      headerText="What This Analysis Covers"
                      variant="container"
                    >
                      <SpaceBetween size="m">
                        <Box variant="h4">6 Critical Categories for Production-Ready Infrastructure:</Box>
                        <ColumnLayout columns={2} variant="text-grid">
                          <div>
                            <Box variant="strong">🔒 Backup & Recovery</Box>
                            <Box variant="small">AWS Backup, snapshots, Glacier, cross-region replication</Box>
                          </div>
                          <div>
                            <Box variant="strong">💾 Storage Infrastructure</Box>
                            <Box variant="small">S3 tiers, EFS, FSx, Storage Gateway, EBS</Box>
                          </div>
                          <div>
                            <Box variant="strong">🔄 DR/HA Configuration</Box>
                            <Box variant="small">Multi-AZ, cross-region, Elastic DR, health checks</Box>
                          </div>
                          <div>
                            <Box variant="strong">🌐 Network Services</Box>
                            <Box variant="small">ALB/NLB, CloudFront, Route 53, Transit Gateway, IPv4</Box>
                          </div>
                          <div>
                            <Box variant="strong">📊 Observability & Monitoring</Box>
                            <Box variant="small">CloudWatch, CloudTrail, X-Ray, VPC Flow Logs</Box>
                          </div>
                          <div>
                            <Box variant="strong">🛡️ Security & Compliance</Box>
                            <Box variant="small">KMS, WAF, GuardDuty, Secrets Manager, Network Firewall</Box>
                          </div>
                        </ColumnLayout>
                      </SpaceBetween>
                    </ExpandableSection>

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
                      <Box textAlign="center" padding="l">
                        <SpaceBetween size="m" alignItems="center">
                          <Spinner size="large" />
                          <Box variant="p" color="text-body-secondary">
                            Analyzing infrastructure and identifying service gaps... This may take 2-3 minutes.
                          </Box>
                        </SpaceBetween>
                      </Box>
                    )}

                    <Box textAlign="center">
                      <Button
                        variant="primary"
                        onClick={handleAnalyze}
                        disabled={loading || calculatorFile.length === 0}
                        iconName="search"
                      >
                        Analyze Services
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
                      The default service analysis prompt is shown below. Toggle "Use Custom Prompt" to modify it for your specific needs.
                      Your custom prompt will be saved and used for future analyses.
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
                      label="Service Analysis Prompt"
                      description={useCustomPrompt ? "Edit the prompt below to customize the analysis" : "Default prompt (toggle above to edit)"}
                    >
                      <Textarea
                        value={customPrompt}
                        onChange={({ detail }) => setCustomPrompt(detail.value)}
                        rows={30}
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
                          <strong>Tips for customizing the service analysis prompt:</strong>
                        </Box>
                        <ul>
                          <li>Adjust expected percentages for specific industries or workload types</li>
                          <li>Add or remove service categories based on your focus areas</li>
                          <li>Modify the questions to ask customers based on your discovery process</li>
                          <li>Change the priority thresholds for completeness checks</li>
                          <li>Add industry-specific compliance requirements</li>
                          <li>Customize the output format to match your reporting needs</li>
                          <li>Include specific AWS Well-Architected Framework pillars</li>
                        </ul>
                      </SpaceBetween>
                    </ExpandableSection>
                  </SpaceBetween>
                )
              },
              {
                id: 'results',
                label: 'Analysis Results',
                disabled: !analysis,
                content: analysis && (
                  <SpaceBetween size="m">
                    <Alert type="success">
                      <SpaceBetween size="xs">
                        <Box variant="strong">Service Analysis Complete</Box>
                        <Box>
                          Review the comprehensive analysis below to identify missing services and 
                          infrastructure gaps. Use the recommendations to build a complete, production-ready solution.
                        </Box>
                      </SpaceBetween>
                    </Alert>

                    <ExpandableSection
                      headerText="Service Analysis Results"
                      variant="container"
                      defaultExpanded
                    >
                      <SpaceBetween size="m">
                        {recordsProcessed > 0 && (
                          <Box variant="small" color="text-status-info">
                            {recordsProcessed} services analyzed from AWS Calculator
                          </Box>
                        )}
                        <div className="markdown-content">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {analysis}
                          </ReactMarkdown>
                        </div>
                        <Button
                          onClick={() => downloadMarkdown(analysis, 'service_analysis_report.md')}
                          iconName="download"
                        >
                          Download Analysis Report
                        </Button>
                      </SpaceBetween>
                    </ExpandableSection>

                    <Alert type="info">
                      <SpaceBetween size="xs">
                        <Box variant="strong">Next Steps</Box>
                        <Box>
                          1. Review the service gap analysis and missing infrastructure components<br/>
                          2. Schedule a technical review with your customer<br/>
                          3. Ask the specific questions provided for each category<br/>
                          4. Update the AWS Calculator with recommended services<br/>
                          5. Re-run this analysis to validate infrastructure completeness
                        </Box>
                      </SpaceBetween>
                    </Alert>
                  </SpaceBetween>
                )
              }
            ]}
          />
        </SpaceBetween>
      </Container>
    </SpaceBetween>
  );
}

export default ServiceAnalysis;
