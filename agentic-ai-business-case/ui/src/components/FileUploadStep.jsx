import React from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  FormField,
  FileUpload,
  Alert,
  Box,
  ExpandableSection,
  StatusIndicator
} from '@cloudscape-design/components';

const FileUploadStep = ({ uploadedFiles, setUploadedFiles }) => {
  // Define input type groups - only ONE can be selected
  const inputTypeGroups = {
    itInventory: ['itInventory'],
    rvTool: ['rvTool'],
    atx: ['atxExcel', 'atxPdf', 'atxPptx']
  };

  // Determine which input type is currently selected
  const getSelectedInputType = () => {
    if (uploadedFiles['itInventory']) return 'itInventory';
    if (uploadedFiles['rvTool'] && (Array.isArray(uploadedFiles['rvTool']) ? uploadedFiles['rvTool'].length > 0 : true)) return 'rvTool';
    if (uploadedFiles['atxPptx']) return 'atx';
    return null;
  };

  const selectedInputType = getSelectedInputType();

  const fileConfigs = [
    {
      key: 'itInventory',
      label: 'IT Infrastructure Inventory',
      description: 'Excel file containing general IT asset inventory',
      acceptedFormats: '.xlsx, .xls',
      required: false,
      inputType: 'itInventory',
      details: 'Should include servers, storage, databases, applications, and network components with details like CPU, memory, storage capacity, OS versions, and utilization metrics.',
      example: 'it-infrastructure-inventory.xlsx'
    },
    {
      key: 'rvTool',
      label: 'RVTool VMware Assessment',
      description: 'CSV or Excel files from RVTool containing VMware environment data',
      acceptedFormats: '.csv, .xlsx, .xls',
      required: false,
      multiple: true,
      inputType: 'rvTool',
      details: 'VMware environment data exported from RVTool. For best performance with large datasets, upload the vInfo tab/file which contains comprehensive VM information (names, CPUs, memory, storage, OS, power state). You can upload multiple files, but vInfo will be prioritized for analysis to prevent timeouts.',
      example: 'rvtool-vInfo.csv or rvtools-tabvInfo.xlsx'
    },
    {
      key: 'atxPptx',
      label: 'ATX Business Case (PowerPoint)',
      description: 'AWS Transform for VMware - Executive presentation for x86 servers (VMware only)',
      acceptedFormats: '.pptx, .ppt',
      required: false,
      inputType: 'atx',
      details: 'Use ATX output for x86 servers (VMware environments). For databases + VMs, use IT Infrastructure Inventory instead. If ATX is not available, use RVTools.',
      example: 'atx_business_case.pptx'
    },
    {
      key: 'mra',
      label: 'Migration Readiness Assessment (MRA)',
      description: 'Organizational readiness evaluation document',
      acceptedFormats: '.md, .docx, .doc, .pdf',
      required: true,
      inputType: null, // Not part of input type restriction
      details: 'Migration Readiness Assessment evaluating organizational readiness across business, people, process, technology, security, operations, and financial dimensions. Supports Markdown, Word, and PDF formats.',
      example: 'aws-customer-migration-readiness-assessment.md or mra-report.pdf'
    },
    {
      key: 'portfolio',
      label: 'Application Portfolio (Optional)',
      description: 'Detailed application portfolio assessment',
      acceptedFormats: '.csv, .xlsx, .xls',
      required: false,
      inputType: null, // Not part of input type restriction
      details: 'Optional: Detailed application portfolio with characteristics, dependencies, and business criticality. If not provided, industry-standard assumptions will be used.',
      example: 'application-portfolio.csv'
    }
  ];

  const handleFileChange = (key, files, isMultiple, inputType) => {
    // If this is an infrastructure input type and a different type is already selected, clear the old type
    if (inputType && selectedInputType && selectedInputType !== inputType) {
      // Clear all files from the previously selected input type
      const filesToClear = inputTypeGroups[selectedInputType];
      const clearedFiles = { ...uploadedFiles };
      filesToClear.forEach(fileKey => {
        clearedFiles[fileKey] = null;
      });
      
      // Set the new file
      if (isMultiple) {
        clearedFiles[key] = files.length > 0 ? files : null;
      } else {
        clearedFiles[key] = files[0] || null;
      }
      setUploadedFiles(clearedFiles);
    } else {
      // Normal file change handling
      if (isMultiple) {
        setUploadedFiles({
          ...uploadedFiles,
          [key]: files.length > 0 ? files : null
        });
      } else {
        setUploadedFiles({
          ...uploadedFiles,
          [key]: files[0] || null
        });
      }
    }
  };

  const getUploadStatus = () => {
    const requiredFiles = fileConfigs.filter(f => f.required);
    const uploadedRequired = requiredFiles.filter(f => uploadedFiles[f.key]);
    
    // Check if at least one infrastructure file is uploaded (IT Inventory, RVTools, or any ATX file)
    // For RVTools (multiple files), check if array has items
    const hasRVTools = uploadedFiles['rvTool'] && 
                       (Array.isArray(uploadedFiles['rvTool']) ? uploadedFiles['rvTool'].length > 0 : true);
    
    const hasInfrastructureFile = uploadedFiles['itInventory'] || 
                                   hasRVTools || 
                                   uploadedFiles['atxExcel'] || 
                                   uploadedFiles['atxPdf'] || 
                                   uploadedFiles['atxPptx'];
    
    const allRequiredUploaded = uploadedRequired.length === requiredFiles.length;
    
    return {
      total: requiredFiles.length,
      uploaded: uploadedRequired.length,
      complete: allRequiredUploaded && hasInfrastructureFile,
      hasInfrastructureFile
    };
  };

  const status = getUploadStatus();

  return (
    <Container
      header={
        <Header
          variant="h2"
        >
          Upload Assessment Files
        </Header>
      }
    >
      <SpaceBetween size="l">
        <Alert type="info">
          <strong>Important:</strong> You must select ONE infrastructure input type:
          <ul style={{ marginTop: '8px', marginBottom: '0' }}>
            <li><strong>IT Infrastructure Inventory</strong> - General IT asset inventory (servers + databases)</li>
            <li><strong>RVTools</strong> - VMware environment assessment data</li>
            <li><strong>ATX</strong> - AWS Transform for VMware assessment (Excel/PDF/PowerPoint)</li>
          </ul>
          {selectedInputType && (
            <Box variant="p" margin={{ top: 's' }}>
              Currently selected: <strong>
                {selectedInputType === 'itInventory' && 'IT Infrastructure Inventory'}
                {selectedInputType === 'rvTool' && 'RVTools'}
                {selectedInputType === 'atx' && 'ATX (AWS Transform for VMware)'}
              </strong>
            </Box>
          )}
        </Alert>

        {!status.hasInfrastructureFile ? (
          <Alert type="warning">
            Please upload at least one infrastructure file (IT Infrastructure Inventory, RVTools, or ATX files) and the MRA document to proceed.
          </Alert>
        ) : !status.complete ? (
          <Alert type="info">
            MRA document is required. {status.uploaded} of {status.total} required files uploaded.
          </Alert>
        ) : (
          <Alert type="success">
            All required files uploaded. You can proceed to the next step.
          </Alert>
        )}

        {fileConfigs.map((config) => (
          <ExpandableSection
            key={config.key}
            headerText={
              <Box>
                {config.label}
                {config.required && <Box variant="span" color="text-status-error"> *</Box>}
                {uploadedFiles[config.key] && (
                  <StatusIndicator type="success">
                    {config.multiple && Array.isArray(uploadedFiles[config.key])
                      ? ` ${uploadedFiles[config.key].length} file(s) uploaded`
                      : ' Uploaded'}
                  </StatusIndicator>
                )}
              </Box>
            }
            variant="container"
          >
            <SpaceBetween size="m">
              <Box variant="small">
                <strong>Details:</strong> {config.details}
              </Box>
              
              <Box variant="small" color="text-status-inactive">
                <strong>Example:</strong> {config.example}
              </Box>

              <FormField
                constraintText={`Formats: ${config.acceptedFormats}${config.multiple ? ' • Multiple files allowed' : ''}`}
              >
                <FileUpload
                  onChange={({ detail }) => handleFileChange(config.key, detail.value, config.multiple)}
                  value={config.multiple 
                    ? (uploadedFiles[config.key] || [])
                    : (uploadedFiles[config.key] ? [uploadedFiles[config.key]] : [])
                  }
                  multiple={config.multiple || false}
                  i18nStrings={{
                    uploadButtonText: e => (e ? 'Choose files' : 'Choose file'),
                    dropzoneText: e => (e ? 'Drop files to upload' : 'Drop file to upload'),
                    removeFileAriaLabel: e => `Remove file ${e + 1}`,
                    limitShowFewer: 'Show fewer files',
                    limitShowMore: 'Show more files',
                    errorIconAriaLabel: 'Error'
                  }}
                  showFileLastModified
                  showFileSize
                  showFileThumbnail
                  tokenLimit={config.multiple ? 10 : 1}
                  constraintText={config.required ? 'Required' : 'Optional'}
                />
              </FormField>
            </SpaceBetween>
          </ExpandableSection>
        ))}
      </SpaceBetween>
    </Container>
  );
};

export default FileUploadStep;
