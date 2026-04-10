import React, { useState, useEffect } from 'react';
import {
  AppLayout,
  TopNavigation,
  SideNavigation,
  Container,
  Header,
  SpaceBetween,
  Wizard,
  Alert,
  Toggle,
  Box,
  StatusIndicator
} from '@cloudscape-design/components';
import ProjectInfoStep from './components/ProjectInfoStep.jsx';
import FileUploadStep from './components/FileUploadStep.jsx';
import ReviewStep from './components/ReviewStep.jsx';
import ResultsStep from './components/ResultsStep.jsx';
import SavedCasesModal from './components/SavedCasesModal.jsx';
import ConfigurationModal from './components/ConfigurationModal.jsx';
import ModernizationOpportunity from './components/map-assessment/ModernizationOpportunity.jsx';
import MigrationStrategy from './components/map-assessment/MigrationStrategy.jsx';
import ResourcePlanning from './components/map-assessment/ResourcePlanning.jsx';
import LearningPathway from './components/map-assessment/LearningPathway.jsx';
import BusinessCaseReview from './components/map-assessment/BusinessCaseReview.jsx';
import ArchitectureDiagram from './components/map-assessment/ArchitectureDiagram.jsx';
import ChatAssistant from './components/map-assessment/ChatAssistant.jsx';
import ServiceAnalysis from './components/map-assessment/ServiceAnalysis.jsx';
import OLAAnalysis from './components/map-assessment/OLAAnalysis.jsx';
import { MapAssessmentProvider } from './contexts/MapAssessmentContext.jsx';
import { getApiUrl } from './utils/apiConfig.js';
import './styles/App.css';
import './styles/MapAssessment.css';

function App() {
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [currentView, setCurrentView] = useState('business-case'); // 'business-case' or MAP view names
  const [projectInfo, setProjectInfo] = useState({
    projectName: '',
    projectDescription: '',
    customerName: '',
    awsRegion: 'us-east-1'
  });
  const [uploadedFiles, setUploadedFiles] = useState({});
  const [selectedAgents, setSelectedAgents] = useState({
    runAll: false,
    agents: {}
  });
  const [currentUser, setCurrentUser] = useState(null);

  // Auto-select agents based on uploaded files
  useEffect(() => {
    const agents = {
      // Phase 1: Data Analysis - based on uploaded files
      itInventory: !!uploadedFiles.itInventory,
      rvTool: !!(uploadedFiles.rvTool && (Array.isArray(uploadedFiles.rvTool) ? uploadedFiles.rvTool.length > 0 : true)),
      atx: !!uploadedFiles.atxPptx,
      mra: !!uploadedFiles.mra,
      // Phase 2, 3, 4: Always run
      currentState: true,
      costAnalysis: true,
      migrationStrategy: true,
      migrationPlan: true,
      businessCase: true
    };
    
    const runAll = Object.values(agents).every(v => v === true);
    setSelectedAgents({ runAll, agents });
  }, [uploadedFiles]);
  const [generationStatus, setGenerationStatus] = useState({
    isGenerating: false,
    progress: 0,
    currentAgent: '',
    completed: false,
    error: null
  });
  const [businessCaseResult, setBusinessCaseResult] = useState(null);
  const [dynamoDBEnabled, setDynamoDBEnabled] = useState(false);
  const [dynamoDBAvailable, setDynamoDBAvailable] = useState(false);
  const [s3Available, setS3Available] = useState(false);
  const [currentCaseId, setCurrentCaseId] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [showSavedCasesModal, setShowSavedCasesModal] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);

  useEffect(() => {
    checkStorageStatus();
    fetchCurrentUser();
    
    // Handle initial hash navigation on page load
    const hash = window.location.hash;
    if (hash) {
      const view = hash.replace('#/', '');
      if (view) {
        setCurrentView(view);
      }
    }
  }, []);

  // Handle auto-saved cases - set currentCaseId and lastUpdated
  useEffect(() => {
    if (businessCaseResult?.autoSaved && businessCaseResult?.caseId) {
      setCurrentCaseId(businessCaseResult.caseId);
      setLastUpdated(new Date().toISOString());
    }
  }, [businessCaseResult?.autoSaved, businessCaseResult?.caseId]);

  const fetchCurrentUser = async () => {
    try {
      const response = await fetch(getApiUrl('/user'));
      const data = await response.json();
      if (data.success) {
        setCurrentUser(data.user);
      }
    } catch (error) {
      console.error('Failed to fetch user:', error);
    }
  };

  const checkStorageStatus = async () => {
    try {
      const response = await fetch(getApiUrl('/storage/status'));
      const data = await response.json();
      setDynamoDBAvailable(data.dynamodb.enabled);
      setDynamoDBEnabled(data.dynamodb.enabled);
      setS3Available(data.s3.enabled);
    } catch (error) {
      console.error('Failed to check storage status:', error);
      setDynamoDBAvailable(false);
      setS3Available(false);
    }
  };

  const saveToDatabase = async () => {
    if (!dynamoDBEnabled || !businessCaseResult) return;

    try {
      const response = await fetch(getApiUrl('/dynamodb/save'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          caseId: currentCaseId || businessCaseResult.caseId,
          projectInfo,
          uploadedFiles: Object.keys(uploadedFiles),
          selectedAgents,
          businessCaseContent: businessCaseResult.content,
          executionStats: {
            agentsExecuted: businessCaseResult.agentsExecuted,
            executionTime: businessCaseResult.executionTime,
            tokenUsage: businessCaseResult.tokenUsage
          },
          s3FileKeys: businessCaseResult.s3FileKeys,
          outputS3Keys: businessCaseResult.outputS3Keys,  // Add this for downloads!
          s3BucketName: businessCaseResult.s3BucketName
        })
      });

      const data = await response.json();
      
      if (data.success) {
        setCurrentCaseId(data.caseId);
        setLastUpdated(data.lastUpdated);
        return { success: true, message: 'Saved successfully' };
      } else {
        return { success: false, message: data.message };
      }
    } catch (error) {
      return { success: false, message: error.message };
    }
  };

  const loadCase = (caseData) => {
    setProjectInfo(caseData.projectInfo || {});
    setSelectedAgents(caseData.selectedAgents || {});
    setBusinessCaseResult({
      content: caseData.businessCaseContent,
      uploadedFiles: caseData.uploadedFiles || [],
      caseId: caseData.caseId,
      s3FileKeys: caseData.s3FileKeys,
      outputS3Keys: caseData.outputS3Keys || {},  // Add outputS3Keys for downloads
      s3BucketName: caseData.s3BucketName,
      ...caseData.executionStats
    });
    setCurrentCaseId(caseData.caseId);
    setLastUpdated(caseData.lastUpdated);
    setActiveStepIndex(3); // Go to results step (now step 3 instead of 4)
  };

  const isProjectInfoValid = () => {
    return projectInfo.projectName && 
           projectInfo.customerName && 
           projectInfo.projectDescription && 
           projectInfo.awsRegion;
  };

  const isFileUploadValid = () => {
    // Check if RVTools has files (it's an array)
    const hasRVTools = uploadedFiles['rvTool'] && 
                       (Array.isArray(uploadedFiles['rvTool']) ? uploadedFiles['rvTool'].length > 0 : true);
    
    // Check if at least one infrastructure file is uploaded
    const hasInfrastructureFile = uploadedFiles['itInventory'] || 
                                   hasRVTools || 
                                   uploadedFiles['atxExcel'] || 
                                   uploadedFiles['atxPdf'] || 
                                   uploadedFiles['atxPptx'];
    
    // MRA is now optional
    return hasInfrastructureFile;
  };

  const steps = [
    {
      title: 'Project Information',
      isOptional: false,
      content: (
        <ProjectInfoStep
          projectInfo={projectInfo}
          setProjectInfo={setProjectInfo}
        />
      )
    },
    {
      title: 'Upload Assessment Files',
      isOptional: false,
      content: (
        <FileUploadStep
          uploadedFiles={uploadedFiles}
          setUploadedFiles={setUploadedFiles}
        />
      )
    },
    {
      title: 'Review & Generate',
      content: (
        <ReviewStep
          projectInfo={projectInfo}
          uploadedFiles={uploadedFiles}
          selectedAgents={selectedAgents}
          generationStatus={generationStatus}
          setGenerationStatus={setGenerationStatus}
          setBusinessCaseResult={setBusinessCaseResult}
          setActiveStepIndex={setActiveStepIndex}
        />
      )
    },
    {
      title: 'Results',
      content: (
        <ResultsStep
          businessCaseResult={businessCaseResult}
          setBusinessCaseResult={setBusinessCaseResult}
          projectInfo={projectInfo}
          dynamoDBEnabled={dynamoDBEnabled}
          onSave={saveToDatabase}
          lastUpdated={lastUpdated}
          currentCaseId={currentCaseId}
        />
      ),
      isOptional: false
    }
  ];

  const renderContent = () => {
    switch (currentView) {
      case 'business-case':
        return (
          <Container>
            <SpaceBetween size="l">
              <Header
                variant="h1"
                description="Generate comprehensive AWS migration business cases using AI-powered analysis"
                actions={
                  <SpaceBetween direction="horizontal" size="xs">
                    {dynamoDBAvailable && (
                      <Toggle
                        checked={dynamoDBEnabled}
                        onChange={({ detail }) => setDynamoDBEnabled(detail.checked)}
                      >
                        <Box variant="span">
                          <StatusIndicator type={dynamoDBEnabled ? "success" : "stopped"}>
                            DynamoDB Persistence
                          </StatusIndicator>
                        </Box>
                      </Toggle>
                    )}
                  </SpaceBetween>
                }
              >
                AWS Migration and Modernisation
              </Header>

              {dynamoDBEnabled && lastUpdated && (
                <Alert type="info">
                  Last saved: {new Date(lastUpdated).toLocaleString()}
                  {currentCaseId && ` (Case ID: ${currentCaseId})`}
                  {s3Available && ' • Files backed up to S3'}
                </Alert>
              )}

              {dynamoDBEnabled && s3Available && (
                <Alert type="success">
                  <Box variant="span">
                    <strong>Enhanced Storage:</strong> DynamoDB + S3 enabled. Your business cases and uploaded files are fully persisted.
                  </Box>
                </Alert>
              )}

              {generationStatus.error && (
                <Alert type="error" dismissible onDismiss={() => setGenerationStatus({...generationStatus, error: null})}>
                  {generationStatus.error}
                </Alert>
              )}

              <Wizard
                steps={steps}
                activeStepIndex={activeStepIndex}
                className={activeStepIndex === 3 ? 'hide-wizard-actions' : ''}
                onNavigate={({ detail }) => {
                  const requestedStep = detail.requestedStepIndex;
                  
                  // Validate step 0 (Project Info) before moving forward
                  if (activeStepIndex === 0 && requestedStep > 0 && !isProjectInfoValid()) {
                    setGenerationStatus({
                      ...generationStatus,
                      error: 'Please fill in all required project information fields (Project Name, Customer Name, Project Description, and AWS Region).'
                    });
                    return;
                  }
                  
                  // Validate step 1 (File Upload) before moving forward
                  if (activeStepIndex === 1 && requestedStep > 1 && !isFileUploadValid()) {
                    setGenerationStatus({
                      ...generationStatus,
                      error: 'Please upload at least one infrastructure file (IT Inventory, RVTools, or ATX) and the MRA document.'
                    });
                    return;
                  }
                  
                  // Prevent navigation away from Review & Generate step during generation
                  if (activeStepIndex === 2 && generationStatus.isGenerating) {
                    setGenerationStatus({
                      ...generationStatus,
                      error: 'Please wait for business case generation to complete before navigating.'
                    });
                    return;
                  }
                  
                  setActiveStepIndex(requestedStep);
                }}
                i18nStrings={{
                  stepNumberLabel: stepNumber => `Step ${stepNumber}`,
                  collapsedStepsLabel: (stepNumber, stepsCount) =>
                    `Step ${stepNumber} of ${stepsCount}`,
                  skipToButtonLabel: (step, stepNumber) =>
                    `Skip to ${step.title}`,
                  navigationAriaLabel: 'Steps',
                  cancelButton: 'Cancel',
                  previousButton: 'Previous',
                  nextButton: 'Next',
                  submitButton: 'Generate Business Case',
                  optional: 'optional'
                }}
                onCancel={() => {
                  setActiveStepIndex(0);
                  setProjectInfo({ projectName: '', projectDescription: '', customerName: '', awsRegion: 'us-east-1' });
                  setUploadedFiles({});
                  setSelectedAgents({ runAll: true, agents: {} });
                  setGenerationStatus({ isGenerating: false, progress: 0, currentAgent: '', completed: false, error: null });
                  setBusinessCaseResult(null);
                }}
              />
            </SpaceBetween>
          </Container>
        );
      case 'modernization':
        return <ModernizationOpportunity />;
      case 'migration':
        return <MigrationStrategy />;
      case 'resources':
        return <ResourcePlanning />;
      case 'learning':
        return <LearningPathway />;
      case 'review':
        return <BusinessCaseReview />;
      case 'architecture':
        return <ArchitectureDiagram />;
      case 'chat':
        return <ChatAssistant />;
      case 'service-analysis':
        return <ServiceAnalysis />;
      case 'ola-analysis':
        return <OLAAnalysis />;
      default:
        return null;
    }
  };

  return (
    <MapAssessmentProvider>
      <div className="app">
        <TopNavigation
          identity={{
            href: '#',
            title: 'AWS Migration and Modernisation',
            logo: {
              src: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA1MCA0MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjUwIiBoZWlnaHQ9IjQwIiBmaWxsPSIjMjMyRjNFIi8+Cjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjRkY5OTAwIiBmb250LXNpemU9IjE4IiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtd2VpZ2h0PSJib2xkIj5BV1M8L3RleHQ+Cjwvc3ZnPg==',
              alt: 'AWS'
            },
            onFollow: (e) => {
              e.preventDefault();
              setCurrentView('business-case');
              setActiveStepIndex(0);
            }
          }}
          utilities={[
            {
              type: 'menu-dropdown',
              text: currentUser 
                ? `Welcome, ${currentUser.given_name || currentUser.name?.split(' ')[0] || currentUser.email?.split('@')[0] || 'User'}` 
                : 'User',
              iconName: 'user-profile',
              items: [
                {
                  id: 'user-info',
                  text: currentUser?.email || 'Not authenticated',
                  disabled: true
                }
              ]
            },
            {
              type: 'button',
              text: 'Configuration',
              onClick: () => setShowConfigModal(true)
            },
            {
              type: 'button',
              text: 'Load Saved Cases',
              onClick: () => setShowSavedCasesModal(true),
              disabled: !dynamoDBEnabled
            },
            {
              type: 'button',
              text: 'Documentation',
              href: 'https://github.com/aws-samples/sample-genai-in-modernization/tree/main/agentic-ai-business-case',
              external: true,
              externalIconAriaLabel: ' (opens in a new tab)'
            }
          ]}
        />

        <SavedCasesModal
          visible={showSavedCasesModal}
          onDismiss={() => setShowSavedCasesModal(false)}
          onLoadCase={loadCase}
        />

        <ConfigurationModal
          visible={showConfigModal}
          onDismiss={() => setShowConfigModal(false)}
        />
        
        <AppLayout
          navigation={
            <SideNavigation
              activeHref={`#/${currentView}`}
              header={{ text: 'Navigation', href: '#/' }}
              onFollow={event => {
                if (!event.detail.external) {
                  event.preventDefault();
                  const view = event.detail.href.replace('#/', '');
                  setCurrentView(view || 'business-case');
                }
              }}
              items={[
                {
                  type: 'section',
                  text: 'Business Case Generator',
                  items: [
                    { type: 'link', text: 'Generate Case', href: '#/business-case' }
                  ]
                },
                { type: 'divider' },
                {
                  type: 'section',
                  text: 'GenAI Usecases',
                  items: [
                    { type: 'link', text: 'Modernization Opportunity', href: '#/modernization' },
                    { type: 'link', text: 'Migration Strategy', href: '#/migration' },
                    { type: 'link', text: 'Resource Planning', href: '#/resources' },
                    { type: 'link', text: 'Learning Pathway', href: '#/learning' },
                    { type: 'link', text: 'Business Case Review', href: '#/review' },
                    { type: 'link', text: 'Architecture Diagram', href: '#/architecture' },
                    { type: 'link', text: 'Service Analysis', href: '#/service-analysis' },
                    { type: 'link', text: 'OLA Analysis', href: '#/ola-analysis' },
                    { type: 'link', text: 'Chat Assistant', href: '#/chat' }
                  ]
                }
              ]}
            />
          }
          toolsHide={true}
          content={renderContent()}
        />
      </div>
    </MapAssessmentProvider>
  );
}

export default App;
