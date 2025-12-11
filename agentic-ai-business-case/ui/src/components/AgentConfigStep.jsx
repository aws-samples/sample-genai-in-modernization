import React from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  Toggle,
  Box,
  ColumnLayout,
  Checkbox,
  Alert,
  ExpandableSection
} from '@cloudscape-design/components';

const AgentConfigStep = ({ selectedAgents, setSelectedAgents, uploadedFiles }) => {
  const agentConfigs = [
    {
      id: 'itInventory',
      name: 'IT Inventory Analysis',
      description: 'Analyzes general IT infrastructure inventory',
      phase: 'Phase 1: Data Analysis',
      duration: '~2-3 min',
      requiredFile: 'itInventory',
      details: 'Performs asset categorization, technical environment analysis, dependency mapping, and infrastructure assessment.'
    },
    {
      id: 'rvTool',
      name: 'RVTool VMware Analysis',
      description: 'Analyzes RVTool VMware assessment data',
      phase: 'Phase 1: Data Analysis',
      duration: '~2-3 min',
      requiredFile: 'rvTool',
      details: 'Analyzes VMware inventory, capacity and performance metrics, disaster recovery capabilities, and cost optimization opportunities.'
    },
    {
      id: 'atx',
      name: 'ATX VMware Analysis',
      description: 'Analyzes AWS Transform for VMware assessment',
      phase: 'Phase 1: Data Analysis',
      duration: '~2-3 min',
      requiredFiles: ['atxExcel', 'atxPdf', 'atxPptx'],
      details: 'Evaluates VMware environment, workload categorization, AWS target architecture mapping, and TCO comparison.'
    },
    {
      id: 'mra',
      name: 'MRA Organizational Readiness',
      description: 'Analyzes Migration Readiness Assessment',
      phase: 'Phase 1: Data Analysis',
      duration: '~2-3 min',
      requiredFile: 'mra',
      details: 'Assesses organizational readiness across business, people, process, technology, security, operations, and financial dimensions.'
    },
    {
      id: 'currentState',
      name: 'Current State Synthesis',
      description: 'Synthesizes all analyses into unified view',
      phase: 'Phase 2: Synthesis',
      duration: '~1-2 min',
      dependsOn: ['itInventory', 'rvTool', 'atx', 'mra'],
      details: 'Combines technical and organizational assessments into comprehensive current state analysis.',
      required: true,
      alwaysRun: true
    },
    {
      id: 'costAnalysis',
      name: 'AWS Cost Analysis',
      description: 'Calculates AWS costs and TCO',
      phase: 'Phase 2: Synthesis',
      duration: '~1-2 min',
      dependsOn: ['itInventory', 'rvTool', 'atx', 'mra'],
      details: 'Projects AWS costs using multiple pricing models (On-Demand, Reserved Instances, Savings Plans) and performs 3-year TCO comparison.',
      required: true,
      alwaysRun: true
    },
    {
      id: 'migrationStrategy',
      name: 'Migration Strategy (6Rs)',
      description: 'Recommends migration approach using 6Rs',
      phase: 'Phase 2: Synthesis',
      duration: '~1-2 min',
      dependsOn: ['itInventory', 'rvTool', 'atx', 'mra'],
      details: 'Categorizes applications by 6Rs (Rehost, Replatform, Repurchase, Refactor, Retire, Retain) and creates wave planning.',
      required: true,
      alwaysRun: true
    },
    {
      id: 'migrationPlan',
      name: 'Migration Plan (MAP)',
      description: 'Creates comprehensive migration plan',
      phase: 'Phase 3: Planning',
      duration: '~1-2 min',
      dependsOn: ['currentState', 'costAnalysis', 'migrationStrategy'],
      details: 'Develops detailed plan covering Assess, Mobilize, Migrate, and Modernize phases with timelines and resources.',
      required: true,
      alwaysRun: true
    },
    {
      id: 'businessCase',
      name: 'Business Case Generation',
      description: 'Generates final business case document',
      phase: 'Phase 4: Final',
      duration: '~1 min',
      dependsOn: ['currentState', 'costAnalysis', 'migrationStrategy', 'migrationPlan'],
      details: 'Compiles all analyses into executive-ready comprehensive business case document.',
      required: true,
      alwaysRun: true
    }
  ];

  const handleRunAllToggle = (checked) => {
    if (checked) {
      const allAgents = {};
      agentConfigs.forEach(agent => {
        allAgents[agent.id] = true;
      });
      setSelectedAgents({ runAll: true, agents: allAgents });
    } else {
      // When turning off "Run All", keep Phase 2, 3, 4 agents enabled
      const requiredAgents = {};
      agentConfigs.forEach(agent => {
        if (agent.alwaysRun) {
          requiredAgents[agent.id] = true;
        }
      });
      setSelectedAgents({ runAll: false, agents: requiredAgents });
    }
  };

  const handleAgentToggle = (agentId, checked) => {
    const newAgents = { ...selectedAgents.agents, [agentId]: checked };
    
    // If turning off an agent, turn off dependent agents
    if (!checked) {
      agentConfigs.forEach(agent => {
        if (agent.dependsOn && agent.dependsOn.includes(agentId)) {
          newAgents[agent.id] = false;
        }
      });
    }
    
    // If turning on an agent, turn on required dependencies
    if (checked) {
      const agent = agentConfigs.find(a => a.id === agentId);
      if (agent.dependsOn) {
        agent.dependsOn.forEach(dep => {
          newAgents[dep] = true;
        });
      }
    }
    
    setSelectedAgents({ runAll: false, agents: newAgents });
  };

  const isAgentAvailable = (agent) => {
    if (agent.requiredFile) {
      return !!uploadedFiles[agent.requiredFile];
    }
    if (agent.requiredFiles) {
      return agent.requiredFiles.every(file => uploadedFiles[file]);
    }
    return true;
  };

  const getSelectedCount = () => {
    return Object.values(selectedAgents.agents).filter(Boolean).length;
  };

  const getTotalDuration = () => {
    let total = 0;
    agentConfigs.forEach(agent => {
      if (selectedAgents.agents[agent.id]) {
        const duration = agent.duration.match(/\d+/g);
        if (duration) {
          total += parseInt(duration[0]);
        }
      }
    });
    return `~${total} minutes`;
  };

  const groupedAgents = agentConfigs.reduce((acc, agent) => {
    if (!acc[agent.phase]) {
      acc[agent.phase] = [];
    }
    acc[agent.phase].push(agent);
    return acc;
  }, {});

  return (
    <Container
      header={
        <Header
          variant="h2"
          description="Select which agents to run for your business case generation"
          info={
            <Box>
              {getSelectedCount()} agents selected • Estimated time: {getTotalDuration()}
            </Box>
          }
        >
          Configure Agents
        </Header>
      }
    >
      <SpaceBetween size="l">


        <Toggle
          onChange={({ detail }) => handleRunAllToggle(detail.checked)}
          checked={selectedAgents.runAll}
        >
          <Box variant="strong">Run All Agents (Recommended)</Box>
          <Box variant="small">Execute complete analysis with all 9 agents</Box>
        </Toggle>

        {!selectedAgents.runAll && (
          <SpaceBetween size="m">
            {Object.entries(groupedAgents).map(([phase, agents]) => (
              <ExpandableSection
                key={phase}
                headerText={phase}
                variant="container"
                defaultExpanded={true}
              >
                <ColumnLayout columns={1} variant="text-grid">
                  {agents.map(agent => (
                    <Box key={agent.id}>
                      <Checkbox
                        checked={selectedAgents.agents[agent.id] || false}
                        onChange={({ detail }) => handleAgentToggle(agent.id, detail.checked)}
                        disabled={agent.alwaysRun || !isAgentAvailable(agent)}
                      >
                        <SpaceBetween size="xxs">
                          <Box variant="strong">{agent.name}</Box>
                          <Box variant="small">{agent.description}</Box>
                          <Box variant="small" color="text-status-inactive">
                            Duration: {agent.duration}
                            {agent.dependsOn && ` • Depends on: ${agent.dependsOn.length} agent(s)`}
                            {agent.alwaysRun && ' • Always runs (required for business case)'}
                          </Box>
                          <Box variant="small">{agent.details}</Box>
                          {!isAgentAvailable(agent) && (
                            <Box variant="small" color="text-status-error">
                              Required file(s) not uploaded
                            </Box>
                          )}
                        </SpaceBetween>
                      </Checkbox>
                    </Box>
                  ))}
                </ColumnLayout>
              </ExpandableSection>
            ))}
          </SpaceBetween>
        )}
      </SpaceBetween>
    </Container>
  );
};

export default AgentConfigStep;
