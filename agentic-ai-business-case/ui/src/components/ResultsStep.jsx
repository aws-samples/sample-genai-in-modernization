import React, { useState, useMemo } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  Box,
  Button,
  ButtonDropdown,
  Tabs,
  Alert,
  ColumnLayout,
  KeyValuePairs,
  ExpandableSection,
  StatusIndicator
} from '@cloudscape-design/components';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import html2pdf from 'html2pdf.js';
import { getApiUrl } from '../utils/apiConfig.js';

const ResultsStep = ({ businessCaseResult, setBusinessCaseResult, projectInfo, dynamoDBEnabled, onSave, lastUpdated, currentCaseId }) => {
  const [activeTabId, setActiveTabId] = useState('preview');
  const [isExporting, setIsExporting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState(null);
  const [editedContent, setEditedContent] = useState('');
  const [isEdited, setIsEdited] = useState(false);
  const [downloadingFile, setDownloadingFile] = useState(null);

  // Initialize edited content when business case result changes
  React.useEffect(() => {
    if (businessCaseResult?.content) {
      setEditedContent(businessCaseResult.content);
      setIsEdited(false);
    }
  }, [businessCaseResult]);

  // Extract key metrics from business case content
  const keyMetrics = useMemo(() => {
    if (!businessCaseResult?.content) return null;
    
    const content = businessCaseResult.content;
    const metrics = {};
    
    // Extract monthly cost - more flexible patterns
    const monthlyMatch = content.match(/(?:Total\s+)?Monthly(?:\s+AWS)?\s+Cost[:\s]*\$?([\d,]+\.?\d*)/i);
    if (monthlyMatch) metrics.monthlyCost = monthlyMatch[1];
    
    // Extract annual cost - handle "ARR" and "including backup"
    const annualMatch = content.match(/(?:Total\s+)?Annual(?:\s+AWS)?\s+Cost(?:\s+\(ARR(?:,\s+including\s+backup)?\))?[:\s]*\$?([\d,]+\.?\d*)/i);
    if (annualMatch) metrics.annualCost = annualMatch[1];
    
    // Extract 3-year cost
    const threeYearMatch = content.match(/3-Year\s+(?:Total\s+)?Cost[:\s]*\$?([\d,]+\.?\d*)/i);
    if (threeYearMatch) metrics.threeYearCost = threeYearMatch[1];
    
    // Extract VM count
    const vmMatch = content.match(/Total\s+VMs?[:\s]*(\d+)/i);
    if (vmMatch) metrics.totalVMs = vmMatch[1];
    
    // Extract vCPU count
    const vcpuMatch = content.match(/Total\s+vCPUs?[:\s]*([\d,]+)/i);
    if (vcpuMatch) metrics.totalVCPUs = vcpuMatch[1].replace(/,/g, '');
    
    // Extract RAM
    const ramMatch = content.match(/Total\s+RAM[:\s]*([\d,]+(?:\.\d+)?)\s*GB/i);
    if (ramMatch) metrics.totalRAM = ramMatch[1].replace(/,/g, '');
    
    // Extract storage
    const storageMatch = content.match(/Total\s+Storage[:\s]*([\d,]+(?:\.\d+)?)\s*TB/i);
    if (storageMatch) metrics.totalStorage = storageMatch[1].replace(/,/g, '');
    
    // Extract timeline - prioritize overall project timeline over wave durations
    // First try to match "within X months" or "X-month timeline/implementation/phased"
    const timelineMatch = content.match(/within\s+(\d+)\s*months?/i) ||
                          content.match(/(\d+)-month\s+(?:phased\s+)?(?:implementation|timeline|approach|migration)/i) ||
                          content.match(/(?:Migration\s+)?Timeline[:\s]*(\d+)\s*months?/i) ||
                          content.match(/(\d+)\s*months?\s+(?:phased\s+)?(?:implementation|timeline|approach)/i);
    if (timelineMatch) metrics.timeline = timelineMatch[1];
    
    return Object.keys(metrics).length > 0 ? metrics : null;
  }, [businessCaseResult]);

  const handleContentChange = (e) => {
    setEditedContent(e.target.value);
    setIsEdited(true);
  };

  const handleSaveChanges = () => {
    // Update the business case result with edited content
    setBusinessCaseResult({
      ...businessCaseResult,
      content: editedContent
    });
    setIsEdited(false);
    setSaveMessage({ type: 'success', text: 'Changes saved locally. Click "Save to Database" to persist.' });
  };

  const handleDiscardChanges = () => {
    setEditedContent(businessCaseResult?.content || '');
    setIsEdited(false);
    setSaveMessage({ type: 'info', text: 'Changes discarded.' });
  };

  const handleExportPDF = async () => {
    setIsExporting(true);
    try {
      const element = document.getElementById('business-case-content');
      const opt = {
        margin: 1,
        filename: `${projectInfo.projectName.replace(/\s+/g, '_')}_Business_Case.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2 },
        jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
      };
      await html2pdf().set(opt).from(element).save();
    } catch (error) {
      console.error('PDF export failed:', error);
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportMarkdown = () => {
    // Export the currently displayed (possibly edited) content
    const blob = new Blob([editedContent || ''], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${projectInfo.projectName.replace(/\s+/g, '_')}_Business_Case.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleCopyToClipboard = () => {
    navigator.clipboard.writeText(editedContent || '');
    setSaveMessage({ type: 'success', text: 'Copied to clipboard!' });
    setTimeout(() => setSaveMessage(null), 2000);
  };

  const handleSaveToDatabase = async () => {
    setIsSaving(true);
    setSaveMessage(null);
    
    try {
      const result = await onSave();
      if (result.success) {
        setSaveMessage({ type: 'success', text: 'Business case saved successfully!' });
      } else {
        setSaveMessage({ type: 'error', text: result.message });
      }
    } catch (error) {
      setSaveMessage({ type: 'error', text: 'Failed to save: ' + error.message });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDownloadFile = async (fileType, fileName) => {
    setDownloadingFile(fileType);
    try {
      console.log('Download attempt:', { fileType, fileName });
      console.log('businessCaseResult:', businessCaseResult);
      console.log('outputS3Keys:', businessCaseResult?.outputS3Keys);
      
      const caseId = currentCaseId || businessCaseResult.caseId;
      
      // Get the S3 key for this file type from outputS3Keys
      const s3Key = businessCaseResult.outputS3Keys?.[fileType];
      
      console.log('Resolved:', { caseId, s3Key });
      
      if (!s3Key) {
        setSaveMessage({ type: 'error', text: `File not available for download. ${fileName} was not generated or uploaded to S3.` });
        setDownloadingFile(null);
        return;
      }

      // Build URL with either caseId (for saved cases) or s3Key (for unsaved cases)
      let url = getApiUrl(`/download/${fileType}`);
      if (caseId) {
        url += `?caseId=${encodeURIComponent(caseId)}`;
      } else {
        url += `?s3Key=${encodeURIComponent(s3Key)}`;
      }

      console.log('Fetching:', url);
      
      const response = await fetch(url);
      const data = await response.json();
      
      console.log('Download response:', data);
      
      if (data.success) {
        // Open presigned URL in new tab to trigger download
        window.open(data.url, '_blank', 'noopener,noreferrer');
        setSaveMessage({ type: 'success', text: `Downloading ${fileName}...` });
        setTimeout(() => setSaveMessage(null), 3000);
      } else {
        setSaveMessage({ type: 'error', text: `Download failed: ${data.message}` });
      }
    } catch (error) {
      console.error('Download error:', error);
      setSaveMessage({ type: 'error', text: `Download error: ${error.message}` });
    } finally {
      setDownloadingFile(null);
    }
  };

  if (!businessCaseResult) {
    return (
      <Container>
        <Alert type="warning">
          No business case has been generated yet. Please complete the previous steps.
        </Alert>
      </Container>
    );
  }

  return (
    <Container
      header={
        <Header
          variant="h2"
          description="View and export your generated business case"
          actions={
            <SpaceBetween direction="horizontal" size="xs">
              {isEdited && (
                <>
                  <Button
                    onClick={handleDiscardChanges}
                  >
                    Discard Changes
                  </Button>
                  <Button
                    iconName="check"
                    onClick={handleSaveChanges}
                    variant="primary"
                  >
                    Save Changes
                  </Button>
                </>
              )}
              {dynamoDBEnabled && !isEdited && !businessCaseResult.autoSaved && (
                <Button
                  iconName="upload"
                  onClick={handleSaveToDatabase}
                  loading={isSaving}
                  variant="primary"
                >
                  {lastUpdated ? 'Update in Database' : 'Save to Database'}
                </Button>
              )}
              {businessCaseResult.autoSaved && (
                <Box variant="span" color="text-status-success">
                  <StatusIndicator type="success">Auto-saved to database</StatusIndicator>
                </Box>
              )}
              <Button
                iconName="copy"
                onClick={handleCopyToClipboard}
              >
                Copy to Clipboard
              </Button>
              <ButtonDropdown
                items={[
                  { text: 'Export as PDF', id: 'pdf', iconName: 'file' },
                  { text: 'Export as Markdown', id: 'markdown', iconName: 'file' }
                ]}
                onItemClick={({ detail }) => {
                  if (detail.id === 'pdf') {
                    handleExportPDF();
                  } else if (detail.id === 'markdown') {
                    handleExportMarkdown();
                  }
                }}
                loading={isExporting}
              >
                Export
              </ButtonDropdown>
            </SpaceBetween>
          }
        >
          Business Case Results
        </Header>
      }
    >
      <SpaceBetween size="l">
        <Alert type="success">
          Your business case has been generated successfully!
          <Box variant="small" color="text-status-inactive" margin={{ top: 'xs' }}>
            Generated at: {new Date().toLocaleString()} • Case ID: {currentCaseId || businessCaseResult.caseId || 'N/A'}
          </Box>
          {businessCaseResult.s3FileKeys && businessCaseResult.s3BucketName && (
            <Box variant="small" color="text-status-inactive" margin={{ top: 'xs' }}>
              <strong>S3 Storage:</strong> s3://{businessCaseResult.s3BucketName}/{currentCaseId || businessCaseResult.caseId}/
            </Box>
          )}
        </Alert>

        {isEdited && (
          <Alert type="warning">
            You have unsaved changes. Click "Save Changes" to apply them, or "Discard Changes" to revert.
          </Alert>
        )}

        {saveMessage && (
          <Alert
            type={saveMessage.type}
            dismissible
            onDismiss={() => setSaveMessage(null)}
          >
            {saveMessage.text}
          </Alert>
        )}

        <Tabs
          activeTabId={activeTabId}
          onChange={({ detail }) => setActiveTabId(detail.activeTabId)}
          tabs={[
            {
              label: 'Preview',
              id: 'preview',
              content: (
                <Box padding={{ vertical: 'l' }}>
                  {/* Key Metrics Dashboard */}
                  {keyMetrics && (
                    <Box margin={{ bottom: 'xl' }}>
                      <Container
                        header={
                          <Header variant="h3">
                            Key Metrics at a Glance
                          </Header>
                        }
                      >
                        <ColumnLayout columns={4} variant="text-grid">
                          {keyMetrics.monthlyCost && (
                            <div className="metric-card">
                              <Box variant="awsui-key-label">Monthly Cost</Box>
                              <div className="metric-value">${keyMetrics.monthlyCost}</div>
                            </div>
                          )}
                          {keyMetrics.annualCost && (
                            <div className="metric-card">
                              <Box variant="awsui-key-label">Annual Cost (ARR)</Box>
                              <div className="metric-value">${keyMetrics.annualCost}</div>
                            </div>
                          )}
                          {keyMetrics.totalVMs && (
                            <div className="metric-card">
                              <Box variant="awsui-key-label">Total VMs</Box>
                              <div className="metric-value">{keyMetrics.totalVMs}</div>
                            </div>
                          )}
                          {keyMetrics.timeline && (
                            <div className="metric-card">
                              <Box variant="awsui-key-label">Migration Timeline</Box>
                              <div className="metric-value">{keyMetrics.timeline} months</div>
                            </div>
                          )}
                        </ColumnLayout>
                        
                        {(keyMetrics.totalVCPUs || keyMetrics.totalRAM || keyMetrics.totalStorage) && (
                          <Box margin={{ top: 'l' }}>
                            <ColumnLayout columns={3} variant="text-grid">
                              {keyMetrics.totalVCPUs && (
                                <div className="metric-card-small">
                                  <Box variant="awsui-key-label">Total vCPUs</Box>
                                  <div className="metric-value-small">{keyMetrics.totalVCPUs}</div>
                                </div>
                              )}
                              {keyMetrics.totalRAM && (
                                <div className="metric-card-small">
                                  <Box variant="awsui-key-label">Total RAM</Box>
                                  <div className="metric-value-small">{keyMetrics.totalRAM} GB</div>
                                </div>
                              )}
                              {keyMetrics.totalStorage && (
                                <div className="metric-card-small">
                                  <Box variant="awsui-key-label">Total Storage</Box>
                                  <div className="metric-value-small">{keyMetrics.totalStorage} TB</div>
                                </div>
                              )}
                            </ColumnLayout>
                          </Box>
                        )}
                      </Container>
                    </Box>
                  )}
                  
                  {/* Business Case Content */}
                  <div id="business-case-content" className="business-case-professional">
                    <style>{`
                      /* Metric Cards Styling */
                      .metric-card {
                        padding: 16px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        border-radius: 8px;
                        text-align: center;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                      }
                      
                      .metric-card .awsui-key-label {
                        color: rgba(255, 255, 255, 0.9) !important;
                        font-size: 12px;
                        font-weight: 600;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                      }
                      
                      .metric-value {
                        color: white;
                        font-size: 32px;
                        font-weight: 700;
                        margin-top: 8px;
                        line-height: 1;
                      }
                      
                      .metric-card-small {
                        padding: 12px;
                        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                        border-radius: 6px;
                        text-align: center;
                        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                      }
                      
                      .metric-card-small .awsui-key-label {
                        color: rgba(255, 255, 255, 0.9) !important;
                        font-size: 11px;
                        font-weight: 600;
                        text-transform: uppercase;
                      }
                      
                      .metric-value-small {
                        color: white;
                        font-size: 24px;
                        font-weight: 700;
                        margin-top: 4px;
                      }
                      
                      /* Professional Business Case Styling */
                      .business-case-professional {
                        background: white;
                        padding: 48px;
                        border-radius: 12px;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
                      }
                      
                      #business-case-content h1 {
                        font-size: 2.5em;
                        font-weight: 700;
                        margin-top: 1.5em;
                        margin-bottom: 0.6em;
                        color: #232f3e;
                        border-bottom: 3px solid #ff9900;
                        padding-bottom: 0.4em;
                        letter-spacing: -0.5px;
                      }
                      
                      #business-case-content h1:first-child {
                        margin-top: 0;
                      }
                      
                      #business-case-content h2 {
                        font-size: 1.8em;
                        font-weight: 600;
                        margin-top: 2em;
                        margin-bottom: 0.8em;
                        color: #232f3e;
                        padding-left: 12px;
                        border-left: 4px solid #ff9900;
                      }
                      
                      #business-case-content h3 {
                        font-size: 1.4em;
                        font-weight: 600;
                        margin-top: 1.5em;
                        margin-bottom: 0.6em;
                        color: #16191f;
                      }
                      
                      #business-case-content h4 {
                        font-size: 1.1em;
                        font-weight: 600;
                        margin-top: 1.2em;
                        margin-bottom: 0.5em;
                        color: #414d5c;
                      }
                      
                      #business-case-content p {
                        line-height: 1.8;
                        margin-bottom: 1.2em;
                        color: #414d5c;
                        font-size: 16px;
                      }
                      
                      #business-case-content table {
                        width: 100%;
                        border-collapse: separate;
                        border-spacing: 0;
                        margin: 2em 0;
                        font-size: 0.95em;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                        border-radius: 8px;
                        overflow: hidden;
                      }
                      
                      #business-case-content table thead {
                        background: linear-gradient(135deg, #232f3e 0%, #414d5c 100%);
                        color: white;
                      }
                      
                      #business-case-content table th {
                        padding: 16px 20px;
                        text-align: left;
                        font-weight: 600;
                        border: none;
                        text-transform: uppercase;
                        font-size: 0.85em;
                        letter-spacing: 0.5px;
                      }
                      
                      #business-case-content table td {
                        padding: 14px 20px;
                        border: none;
                        border-bottom: 1px solid #e9ebed;
                        vertical-align: top;
                        color: #414d5c;
                      }
                      
                      #business-case-content table tbody tr {
                        transition: all 0.2s ease;
                      }
                      
                      #business-case-content table tbody tr:nth-child(even) {
                        background-color: #f9fafb;
                      }
                      
                      #business-case-content table tbody tr:hover {
                        background-color: #fff8e6;
                        transform: scale(1.01);
                        box-shadow: 0 2px 8px rgba(255, 153, 0, 0.1);
                      }
                      
                      #business-case-content table tbody tr:last-child td {
                        border-bottom: none;
                      }
                      
                      #business-case-content ul, #business-case-content ol {
                        margin-left: 1.8em;
                        margin-bottom: 1.2em;
                        line-height: 1.8;
                      }
                      
                      #business-case-content li {
                        margin-bottom: 0.6em;
                        color: #414d5c;
                        padding-left: 0.3em;
                      }
                      
                      #business-case-content li::marker {
                        color: #ff9900;
                        font-weight: bold;
                      }
                      
                      #business-case-content code {
                        background: linear-gradient(135deg, #f4f4f4 0%, #e9ebed 100%);
                        padding: 3px 8px;
                        border-radius: 4px;
                        font-family: 'Monaco', 'Courier New', monospace;
                        font-size: 0.9em;
                        color: #d63384;
                        border: 1px solid #e9ebed;
                      }
                      
                      #business-case-content pre {
                        background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
                        padding: 20px;
                        border-radius: 8px;
                        overflow-x: auto;
                        margin: 1.5em 0;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                      }
                      
                      #business-case-content pre code {
                        background: transparent;
                        color: #68d391;
                        border: none;
                        padding: 0;
                      }
                      
                      #business-case-content blockquote {
                        border-left: 5px solid #ff9900;
                        padding: 16px 24px;
                        margin: 1.5em 0;
                        background: linear-gradient(90deg, #fff8e6 0%, #ffffff 100%);
                        border-radius: 0 8px 8px 0;
                        color: #414d5c;
                        font-style: italic;
                        box-shadow: 0 2px 8px rgba(255, 153, 0, 0.1);
                      }
                      
                      #business-case-content strong {
                        font-weight: 600;
                        color: #232f3e;
                      }
                      
                      #business-case-content hr {
                        border: none;
                        border-top: 2px solid #e9ebed;
                        margin: 3em 0;
                      }
                      
                      #business-case-content a {
                        color: #0073bb;
                        text-decoration: none;
                        border-bottom: 1px solid transparent;
                        transition: all 0.2s ease;
                      }
                      
                      #business-case-content a:hover {
                        color: #ff9900;
                        border-bottom-color: #ff9900;
                      }
                      
                      /* Print Optimization */
                      @media print {
                        .business-case-professional {
                          padding: 20px;
                          box-shadow: none;
                        }
                        
                        #business-case-content table {
                          page-break-inside: avoid;
                        }
                        
                        #business-case-content h1, 
                        #business-case-content h2, 
                        #business-case-content h3 {
                          page-break-after: avoid;
                        }
                      }
                    `}</style>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {editedContent}
                    </ReactMarkdown>
                  </div>
                </Box>
              )
            },
            {
              label: 'Edit Markdown',
              id: 'markdown',
              content: (
                <Box padding={{ vertical: 'l' }}>
                  <SpaceBetween size="m">
                    <Alert type="info">
                      Edit the markdown content below. Changes will be reflected in the Preview tab. Click "Save Changes" to apply your edits.
                    </Alert>
                    <textarea
                      value={editedContent}
                      onChange={handleContentChange}
                      style={{
                        width: '100%',
                        height: '600px',
                        fontFamily: 'monospace',
                        fontSize: '14px',
                        padding: '16px',
                        border: '1px solid #e9ebed',
                        borderRadius: '8px',
                        backgroundColor: '#ffffff',
                        resize: 'vertical'
                      }}
                    />
                  </SpaceBetween>
                </Box>
              )
            },
            {
              label: 'Execution Summary',
              id: 'summary',
              content: (
                <Box padding={{ vertical: 'l' }}>
                  <SpaceBetween size="l">
                    <Box>
                      <Box variant="awsui-key-label">Generation Details</Box>
                      <Box variant="p">
                        <strong>Project:</strong> {projectInfo.projectName}<br />
                        <strong>Customer:</strong> {projectInfo.customerName}<br />
                        <strong>Region:</strong> {projectInfo.awsRegion}<br />
                        <strong>Generated:</strong> {new Date().toLocaleString()}<br />
                        <strong>Agents Executed:</strong> {businessCaseResult.agentsExecuted || 'N/A'}<br />
                        <strong>Execution Time:</strong> {businessCaseResult.executionTime || 'N/A'}<br />
                        <strong>Token Usage:</strong> {businessCaseResult.tokenUsage || 'N/A'}
                      </Box>
                    </Box>
                    
                    <Box>
                      <Box variant="awsui-key-label">Input Files Used</Box>
                      <Box variant="p">
                        {businessCaseResult.uploadedFiles && businessCaseResult.uploadedFiles.length > 0 ? (
                          businessCaseResult.uploadedFiles.map((fileKey) => {
                            const fileNames = {
                              'itInventory': 'IT Infrastructure Inventory (Excel)',
                              'rvTool': 'RVTool VMware Assessment (CSV)',
                              'atxExcel': 'ATX Analysis Data (Excel)',
                              'atxPdf': 'ATX Technical Report (PDF)',
                              'atxPptx': 'ATX Business Case (PowerPoint)',
                              'mra': 'Migration Readiness Assessment (Markdown)',
                              'portfolio': 'Application Portfolio (CSV)'
                            };
                            
                            // Get S3 location if available
                            const s3Key = businessCaseResult.s3FileKeys && businessCaseResult.s3FileKeys[fileKey];
                            
                            return (
                              <div key={fileKey} style={{ marginBottom: '8px' }}>
                                <div>✓ {fileNames[fileKey] || fileKey}</div>
                                {s3Key && (
                                  <div style={{ marginLeft: '20px', fontSize: '12px', color: '#5f6b7a', fontFamily: 'monospace' }}>
                                    S3: s3://{businessCaseResult.s3BucketName || 'bucket'}/{s3Key}
                                  </div>
                                )}
                              </div>
                            );
                          })
                        ) : (
                          <div>No input files information available</div>
                        )}
                      </Box>
                    </Box>
                  </SpaceBetween>
                </Box>
              )
            },
            {
              label: 'Download Files',
              id: 'downloads',
              content: (
                <Box padding={{ vertical: 'l' }}>
                  <SpaceBetween size="l">
                    <Alert type="info">
                      Download the generated business case files. Files are stored in S3 and available for download.
                    </Alert>
                    
                    <Container
                      header={
                        <Header variant="h3">
                          Generated Files
                        </Header>
                      }
                    >
                      <ColumnLayout columns={2} variant="text-grid">
                        <SpaceBetween size="m">
                          <Box>
                            <Box variant="awsui-key-label">Business Case Document</Box>
                            <Box variant="p" margin={{ top: 'xs', bottom: 's' }}>
                              Complete business case in Markdown format with all analysis and recommendations.
                            </Box>
                            <Button
                              onClick={() => handleDownloadFile('business_case', 'Business Case (MD)')}
                              iconName="download"
                              loading={downloadingFile === 'business_case'}
                              disabled={!businessCaseResult.outputS3Keys?.business_case}
                            >
                              Download Business Case (MD)
                            </Button>
                          </Box>
                          
                          {/* Show VM to EC2 Mapping for RVTools input */}
                          {businessCaseResult.outputS3Keys?.excel_mapping && (
                            <Box>
                              <Box variant="awsui-key-label">VM to EC2 Mapping</Box>
                              <Box variant="p" margin={{ top: 'xs', bottom: 's' }}>
                                Detailed Excel spreadsheet mapping VMware VMs to recommended EC2 instances with pricing.
                              </Box>
                              <Button
                                onClick={() => handleDownloadFile('excel_mapping', 'VM to EC2 Mapping (Excel)')}
                                iconName="download"
                                loading={downloadingFile === 'excel_mapping'}
                              >
                                Download VM Mapping (Excel)
                              </Button>
                            </Box>
                          )}
                          
                          {/* Show IT Inventory for IT Inventory input */}
                          {businessCaseResult.outputS3Keys?.it_inventory && (
                            <Box>
                              <Box variant="awsui-key-label">IT Inventory Pricing</Box>
                              <Box variant="p" margin={{ top: 'xs', bottom: 's' }}>
                                Complete IT inventory with AWS pricing calculations and cost breakdown.
                              </Box>
                              <Button
                                onClick={() => handleDownloadFile('it_inventory', 'IT Inventory (Excel)')}
                                iconName="download"
                                loading={downloadingFile === 'it_inventory'}
                              >
                                Download IT Inventory (Excel)
                              </Button>
                            </Box>
                          )}
                        </SpaceBetween>
                        
                        <SpaceBetween size="m">
                          {/* Show EKS Analysis only if generated */}
                          {businessCaseResult.outputS3Keys?.eks_analysis && (
                            <Box>
                              <Box variant="awsui-key-label">EKS Migration Analysis</Box>
                              <Box variant="p" margin={{ top: 'xs', bottom: 's' }}>
                                Kubernetes workload analysis and EKS migration recommendations with cost estimates.
                              </Box>
                              <Button
                                onClick={() => handleDownloadFile('eks_analysis', 'EKS Analysis (Excel)')}
                                iconName="download"
                                loading={downloadingFile === 'eks_analysis'}
                              >
                                Download EKS Analysis (Excel)
                              </Button>
                            </Box>
                          )}
                        </SpaceBetween>
                      </ColumnLayout>
                      
                      {(!businessCaseResult.outputS3Keys || Object.keys(businessCaseResult.outputS3Keys).length === 0) && (
                        <Box margin={{ top: 'l' }}>
                          <Alert type="warning">
                            No files available for download. Files are only available when S3 storage is enabled. 
                            {!businessCaseResult.s3InputBucket && ' Please ensure S3 is configured in your deployment.'}
                          </Alert>
                        </Box>
                      )}
                      
                      {businessCaseResult.outputS3Keys && Object.keys(businessCaseResult.outputS3Keys).length > 0 && !businessCaseResult.outputS3Keys.eks_analysis && (
                        <Box margin={{ top: 'l' }}>
                          <Alert type="info">
                            <strong>Note:</strong> EKS Migration Analysis is only generated when eligible containerizable workloads are detected in your infrastructure.
                          </Alert>
                        </Box>
                      )}
                    </Container>
                  </SpaceBetween>
                </Box>
              )
            }
          ]}
        />
      </SpaceBetween>
    </Container>
  );
};

export default ResultsStep;
