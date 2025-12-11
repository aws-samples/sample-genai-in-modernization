import React, { useState } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  Box,
  Button,
  ButtonDropdown,
  Tabs,
  Alert
} from '@cloudscape-design/components';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import html2pdf from 'html2pdf.js';

const ResultsStep = ({ businessCaseResult, setBusinessCaseResult, projectInfo, dynamoDBEnabled, onSave, lastUpdated, currentCaseId }) => {
  const [activeTabId, setActiveTabId] = useState('preview');
  const [isExporting, setIsExporting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState(null);
  const [editedContent, setEditedContent] = useState('');
  const [isEdited, setIsEdited] = useState(false);

  // Initialize edited content when business case result changes
  React.useEffect(() => {
    if (businessCaseResult?.content) {
      setEditedContent(businessCaseResult.content);
      setIsEdited(false);
    }
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
              {dynamoDBEnabled && !isEdited && (
                <Button
                  iconName="upload"
                  onClick={handleSaveToDatabase}
                  loading={isSaving}
                  variant="primary"
                >
                  {lastUpdated ? 'Update in Database' : 'Save to Database'}
                </Button>
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
                  <div id="business-case-content" style={{ 
                    padding: '20px',
                    maxWidth: '1200px',
                    margin: '0 auto'
                  }}>
                    <style>{`
                      #business-case-content h1 {
                        font-size: 2em;
                        font-weight: 700;
                        margin-top: 1.5em;
                        margin-bottom: 0.5em;
                        color: #16191f;
                        border-bottom: 2px solid #e9ebed;
                        padding-bottom: 0.3em;
                      }
                      #business-case-content h2 {
                        font-size: 1.5em;
                        font-weight: 600;
                        margin-top: 1.2em;
                        margin-bottom: 0.5em;
                        color: #16191f;
                      }
                      #business-case-content h3 {
                        font-size: 1.2em;
                        font-weight: 600;
                        margin-top: 1em;
                        margin-bottom: 0.5em;
                        color: #16191f;
                      }
                      #business-case-content p {
                        line-height: 1.6;
                        margin-bottom: 1em;
                        color: #16191f;
                      }
                      #business-case-content table {
                        width: 100%;
                        border-collapse: collapse;
                        margin: 1.5em 0;
                        font-size: 0.9em;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        overflow: hidden;
                      }
                      #business-case-content table thead {
                        background-color: #232f3e;
                        color: white;
                      }
                      #business-case-content table th {
                        padding: 12px 15px;
                        text-align: left;
                        font-weight: 600;
                        border: 1px solid #d5dbdb;
                      }
                      #business-case-content table td {
                        padding: 10px 15px;
                        border: 1px solid #d5dbdb;
                        vertical-align: top;
                      }
                      #business-case-content table tbody tr:nth-child(even) {
                        background-color: #f9fafb;
                      }
                      #business-case-content table tbody tr:hover {
                        background-color: #eaeded;
                      }
                      #business-case-content ul, #business-case-content ol {
                        margin-left: 1.5em;
                        margin-bottom: 1em;
                        line-height: 1.6;
                      }
                      #business-case-content li {
                        margin-bottom: 0.5em;
                      }
                      #business-case-content code {
                        background-color: #f4f4f4;
                        padding: 2px 6px;
                        border-radius: 3px;
                        font-family: 'Monaco', 'Courier New', monospace;
                        font-size: 0.9em;
                      }
                      #business-case-content pre {
                        background-color: #f4f4f4;
                        padding: 15px;
                        border-radius: 5px;
                        overflow-x: auto;
                        margin: 1em 0;
                      }
                      #business-case-content blockquote {
                        border-left: 4px solid #ff9900;
                        padding-left: 1em;
                        margin: 1em 0;
                        color: #5f6b7a;
                        font-style: italic;
                      }
                      #business-case-content strong {
                        font-weight: 600;
                        color: #16191f;
                      }
                      #business-case-content hr {
                        border: none;
                        border-top: 1px solid #e9ebed;
                        margin: 2em 0;
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
            }
          ]}
        />
      </SpaceBetween>
    </Container>
  );
};

export default ResultsStep;
