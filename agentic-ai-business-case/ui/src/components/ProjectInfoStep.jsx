import React, { useState } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  FormField,
  Input,
  Textarea,
  Select,
  Button,
  Alert
} from '@cloudscape-design/components';

const ProjectInfoStep = ({ projectInfo, setProjectInfo }) => {
  const [isGeneratingDescription, setIsGeneratingDescription] = useState(false);

  const getWordCount = (text) => {
    if (!text) return 0;
    return text.trim().split(/\s+/).filter(word => word.length > 0).length;
  };

  const wordCount = getWordCount(projectInfo.projectDescription);

  const awsRegions = [
    { label: 'US East (N. Virginia) - us-east-1', value: 'us-east-1' },
    { label: 'US East (Ohio) - us-east-2', value: 'us-east-2' },
    { label: 'US West (N. California) - us-west-1', value: 'us-west-1' },
    { label: 'US West (Oregon) - us-west-2', value: 'us-west-2' },
    { label: 'Africa (Cape Town) - af-south-1', value: 'af-south-1' },
    { label: 'Asia Pacific (Hong Kong) - ap-east-1', value: 'ap-east-1' },
    { label: 'Asia Pacific (Hyderabad) - ap-south-2', value: 'ap-south-2' },
    { label: 'Asia Pacific (Jakarta) - ap-southeast-3', value: 'ap-southeast-3' },
    { label: 'Asia Pacific (Melbourne) - ap-southeast-4', value: 'ap-southeast-4' },
    { label: 'Asia Pacific (Mumbai) - ap-south-1', value: 'ap-south-1' },
    { label: 'Asia Pacific (Osaka) - ap-northeast-3', value: 'ap-northeast-3' },
    { label: 'Asia Pacific (Seoul) - ap-northeast-2', value: 'ap-northeast-2' },
    { label: 'Asia Pacific (Singapore) - ap-southeast-1', value: 'ap-southeast-1' },
    { label: 'Asia Pacific (Sydney) - ap-southeast-2', value: 'ap-southeast-2' },
    { label: 'Asia Pacific (Tokyo) - ap-northeast-1', value: 'ap-northeast-1' },
    { label: 'Canada (Central) - ca-central-1', value: 'ca-central-1' },
    { label: 'Canada West (Calgary) - ca-west-1', value: 'ca-west-1' },
    { label: 'Europe (Frankfurt) - eu-central-1', value: 'eu-central-1' },
    { label: 'Europe (Ireland) - eu-west-1', value: 'eu-west-1' },
    { label: 'Europe (London) - eu-west-2', value: 'eu-west-2' },
    { label: 'Europe (Milan) - eu-south-1', value: 'eu-south-1' },
    { label: 'Europe (Paris) - eu-west-3', value: 'eu-west-3' },
    { label: 'Europe (Spain) - eu-south-2', value: 'eu-south-2' },
    { label: 'Europe (Stockholm) - eu-north-1', value: 'eu-north-1' },
    { label: 'Europe (Zurich) - eu-central-2', value: 'eu-central-2' },
    { label: 'Israel (Tel Aviv) - il-central-1', value: 'il-central-1' },
    { label: 'Middle East (Bahrain) - me-south-1', value: 'me-south-1' },
    { label: 'Middle East (UAE) - me-central-1', value: 'me-central-1' },
    { label: 'South America (São Paulo) - sa-east-1', value: 'sa-east-1' }
  ];

  const handleGenerateDescription = async () => {
    if (!projectInfo.projectName || !projectInfo.customerName) {
      return;
    }

    setIsGeneratingDescription(true);
    
    try {
      // Call AI service to enhance description
      const response = await fetch('http://localhost:5000/api/enhance-description', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          projectName: projectInfo.projectName,
          customerName: projectInfo.customerName,
          currentDescription: projectInfo.projectDescription,
          awsRegion: projectInfo.awsRegion
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setProjectInfo({
          ...projectInfo,
          projectDescription: data.enhancedDescription
        });
      } else {
        // Fallback to template if API fails
        const fallbackDescription = projectInfo.projectDescription || 
          `This project aims to assess and plan the migration of ${projectInfo.customerName}'s on-premises infrastructure to AWS. The assessment will include a comprehensive analysis of the current IT environment, VMware workloads, organizational readiness, and provide detailed migration strategies aligned with AWS best practices. The business case will outline the total cost of ownership (TCO) comparison, migration roadmap using the 6Rs framework, and a phased execution plan following the AWS Migration Acceleration Program (MAP) methodology.`;
        
        setProjectInfo({
          ...projectInfo,
          projectDescription: fallbackDescription
        });
      }
    } catch (error) {
      console.error('AI enhancement failed:', error);
      // Fallback to template
      const fallbackDescription = projectInfo.projectDescription || 
        `This project aims to assess and plan the migration of ${projectInfo.customerName}'s on-premises infrastructure to AWS. The assessment will include a comprehensive analysis of the current IT environment, VMware workloads, organizational readiness, and provide detailed migration strategies aligned with AWS best practices. The business case will outline the total cost of ownership (TCO) comparison, migration roadmap using the 6Rs framework, and a phased execution plan following the AWS Migration Acceleration Program (MAP) methodology.`;
      
      setProjectInfo({
        ...projectInfo,
        projectDescription: fallbackDescription
      });
    } finally {
      setIsGeneratingDescription(false);
    }
  };

  return (
    <Container
      header={
        <Header
          variant="h2"
          description="Provide basic information about your migration project"
        >
          Project Information
        </Header>
      }
    >
      <SpaceBetween size="l">
        <Alert type="info">
          All fields are required. This information will be used to personalize your business case document.
        </Alert>

        <FormField
          label={<span>Project Name <span style={{ color: '#d91515' }}>*</span></span>}
          description="A descriptive name for this migration project"
        >
          <Input
            value={projectInfo.projectName}
            onChange={({ detail }) =>
              setProjectInfo({ ...projectInfo, projectName: detail.value })
            }
            placeholder="e.g., Enterprise Cloud Migration 2024"
          />
        </FormField>

        <FormField
          label={<span>Customer Name <span style={{ color: '#d91515' }}>*</span></span>}
          description="Name of the organization being assessed"
        >
          <Input
            value={projectInfo.customerName}
            onChange={({ detail }) =>
              setProjectInfo({ ...projectInfo, customerName: detail.value })
            }
            placeholder="e.g., Acme Corporation"
          />
        </FormField>

        <FormField
          label={<span>Target AWS Region <span style={{ color: '#d91515' }}>*</span></span>}
          description="Primary AWS region for the migration"
        >
          <Select
            selectedOption={awsRegions.find(r => r.value === projectInfo.awsRegion)}
            onChange={({ detail }) =>
              setProjectInfo({ ...projectInfo, awsRegion: detail.selectedOption.value })
            }
            options={awsRegions}
            placeholder="Select AWS region"
          />
        </FormField>

        <FormField
          label={<span>Project Description <span style={{ color: '#d91515' }}>*</span></span>}
          description="Description of the migration project, objectives, and expected outcomes"
          constraintText={`${wordCount} words`}
          secondaryControl={
            <Button
              onClick={handleGenerateDescription}
              loading={isGeneratingDescription}
              disabled={!projectInfo.projectName || !projectInfo.customerName}
              iconName="gen-ai"
            >
              Generate with AI
            </Button>
          }
        >
          <Textarea
            value={projectInfo.projectDescription}
            onChange={({ detail }) =>
              setProjectInfo({ ...projectInfo, projectDescription: detail.value })
            }
            placeholder="Describe the migration project, objectives, and expected outcomes..."
            rows={6}
          />
        </FormField>
      </SpaceBetween>
    </Container>
  );
};

export default ProjectInfoStep;
