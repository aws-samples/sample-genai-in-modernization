import React from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  Box,
  ColumnLayout,
  Button,
  ProgressBar,
  Alert,
  StatusIndicator,
  KeyValuePairs
} from '@cloudscape-design/components';
import { generateBusinessCase } from '../services/api';

const ReviewStep = ({
  projectInfo,
  uploadedFiles,
  selectedAgents,
  generationStatus,
  setGenerationStatus,
  setBusinessCaseResult,
  setActiveStepIndex
}) => {
  
  const agentNames = {
    itInventory: 'IT Inventory Analysis',
    rvTool: 'RVTool VMware Analysis',
    atx: 'ATX VMware Analysis',
    mra: 'MRA Organizational Readiness',
    currentState: 'Current State Synthesis',
    costAnalysis: 'AWS Cost Analysis',
    migrationStrategy: 'Migration Strategy (7Rs)',
    migrationPlan: 'Migration Plan',
    businessCase: 'Business Case Generation'
  };
  const handleGenerate = async () => {
    setGenerationStatus({
      isGenerating: true,
      progress: 0,
      currentAgent: 'Initializing...',
      completed: false,
      error: null
    });

    try {
      const agents = Object.entries(selectedAgents.agents)
        .filter(([_, enabled]) => enabled)
        .map(([id, _]) => id);

      // Estimated phases with progress percentages
      const phases = [
        { name: 'Initializing...', progress: 5 },
        { name: 'Analyzing IT inventory...', progress: 15 },
        { name: 'Processing RVTools data...', progress: 25 },
        { name: 'Analyzing MRA assessment...', progress: 35 },
        { name: 'Calculating AWS costs...', progress: 50 },
        { name: 'Developing migration strategy...', progress: 65 },
        { name: 'Creating migration plan...', progress: 80 },
        { name: 'Generating business case...', progress: 95 }
      ];

      // Simulate progress updates while API is running
      let currentPhase = 0;
      const progressInterval = setInterval(() => {
        if (currentPhase < phases.length) {
          setGenerationStatus(prev => ({
            ...prev,
            progress: phases[currentPhase].progress,
            currentAgent: phases[currentPhase].name
          }));
          currentPhase++;
        }
      }, 15000); // Update every 15 seconds

      // Show initial progress
      setGenerationStatus(prev => ({
        ...prev,
        progress: phases[0].progress,
        currentAgent: phases[0].name
      }));

      try {
        // Call the actual API (this is the real work)
        const result = await generateBusinessCase({
          projectInfo,
          uploadedFiles,
          selectedAgents: agents
        });

        // Clear the progress interval
        clearInterval(progressInterval);

        console.log('API Result:', result); // Debug log
        setBusinessCaseResult(result);
        
        // Only show 100% when actually complete
        setGenerationStatus({
          isGenerating: false,
          progress: 100,
          currentAgent: 'Business case generated successfully',
          completed: true,
          error: null
        });
      } catch (apiError) {
        clearInterval(progressInterval);
        throw apiError;
      }
      
      // Auto-navigate to results step after successful generation
      setTimeout(() => {
        setActiveStepIndex(3); // Move to results step
      }, 1000);
    } catch (error) {
      setGenerationStatus({
        isGenerating: false,
        progress: 0,
        currentAgent: '',
        completed: false,
        error: error.message || 'Failed to generate business case'
      });
    }
  };

  const getFileCount = () => {
    return Object.values(uploadedFiles).filter(Boolean).length;
  };

  const getAgentCount = () => {
    return Object.values(selectedAgents.agents).filter(Boolean).length;
  };

  return (
    <Container
      header={
        <Header
          variant="h2"
          description="Review your configuration and generate the business case"
        >
          Review & Generate
        </Header>
      }
    >
      <SpaceBetween size="l">
        {!generationStatus.completed && !generationStatus.isGenerating && (
          <Alert type="info">
            Review the information below and click "Generate Business Case" to start the analysis.
          </Alert>
        )}

        <ColumnLayout columns={2} variant="text-grid">
          <SpaceBetween size="l">
            <Box>
              <Box variant="awsui-key-label">Project Information</Box>
              <KeyValuePairs
                columns={1}
                items={[
                  { label: 'Project Name', value: projectInfo.projectName || 'Not provided' },
                  { label: 'Customer Name', value: projectInfo.customerName || 'Not provided' },
                  { label: 'AWS Region', value: projectInfo.awsRegion },
                  { label: 'Description', value: projectInfo.projectDescription || 'Not provided' }
                ]}
              />
            </Box>
          </SpaceBetween>

          <SpaceBetween size="l">
            <Box>
              <Box variant="awsui-key-label">Configuration Summary</Box>
              <KeyValuePairs
                columns={1}
                items={[
                  { label: 'Files Uploaded', value: `${getFileCount()} files` },
                  { label: 'Agents Selected', value: `${getAgentCount()} agents` }
                ]}
              />
            </Box>
          </SpaceBetween>
        </ColumnLayout>

        <Box>
          <Box variant="awsui-key-label" margin={{ bottom: 's' }}>Agents That Will Run</Box>

          <Box margin={{ top: 's' }}>
            <SpaceBetween size="xs">
              {Object.entries(selectedAgents.agents)
                .filter(([_, enabled]) => enabled)
                .map(([agentId, _]) => (
                  <Box key={agentId}>
                    <StatusIndicator type="success">
                      {agentNames[agentId] || agentId}
                    </StatusIndicator>
                  </Box>
                ))}
            </SpaceBetween>
          </Box>
        </Box>

        {generationStatus.isGenerating && (
          <SpaceBetween size="m">
            <Box>
              <StatusIndicator type="in-progress">
                {generationStatus.currentAgent}
              </StatusIndicator>
            </Box>
            <ProgressBar
              value={generationStatus.progress}
              label="Generation Progress"
              description="This may take 6-10 minutes depending on the number of agents selected"
              additionalInfo={`${Math.round(generationStatus.progress)}% complete`}
            />
          </SpaceBetween>
        )}

        {generationStatus.completed && (
          <Alert type="success">
            Business case generated successfully! Proceed to the Results step to view and export.
          </Alert>
        )}

        {generationStatus.error && (
          <Alert type="error">
            {generationStatus.error}
          </Alert>
        )}

        {!generationStatus.completed && (
          <Box float="right">
            <Button
              variant="primary"
              onClick={handleGenerate}
              loading={generationStatus.isGenerating}
              disabled={!projectInfo.projectName || getFileCount() === 0}
            >
              Generate Business Case
            </Button>
          </Box>
        )}
      </SpaceBetween>
    </Container>
  );
};

export default ReviewStep;
