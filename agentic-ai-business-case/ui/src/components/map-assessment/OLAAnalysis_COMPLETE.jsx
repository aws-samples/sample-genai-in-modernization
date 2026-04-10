import React, { useState, useEffect } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  FormField,
  FileUpload,
  Button,
  Alert,
  Select,
  Box,
  Spinner,
  ColumnLayout,
  Badge,
  ProgressBar,
  Tabs,
  ExpandableSection
} from '@cloudscape-design/components';
import { getApiUrl } from '../../utils/apiConfig.js';
import { useMapAssessment } from '../../contexts/MapAssessmentContext.jsx';

function OLAAnalysis() {
  const { olaData, setOLAData, resetOLA } = useMapAssessment();
  
  const [rvtoolsFile, setRvtoolsFile] = useState([]);
  const [databaseFile, setDatabaseFile] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(olaData?.results || null);
  const [activeTabId, setActiveTabId] = useState('decision-guidance');
  
  const [saStatus, setSaStatus] = useState({ 
    label: 'Need to verify with Microsoft', 
    value: 'need_verify' 
  });
  
  const [region, setRegion] = useState({ 
    label: 'US East (N. Virginia)', 
    value: 'us-east-1' 
  });

  const saStatusOptions = [
    { label: 'Have active SA on all licenses', value: 'all_active' },
    { label: 'Have SA on some licenses', value: 'mixed' },
    { label: 'No active SA / Unknown', value: 'none_unknown' },
    { label: 'Need to verify with Microsoft', value: 'need_verify' }
  ];

  const regionOptions = [
    { label: 'US East (N. Virginia)', value: 'us-east-1' },
    { label: 'US West (Oregon)', value: 'us-west-2' },
    { label: 'EU (Ireland)', value: 'eu-west-1' },
    { label: 'Asia Pacific (Singapore)', value: 'ap-southeast-1' }
  ];

  useEffect(() => {
    if (olaData?.results) {
      setResults(olaData.results);
    }
  }, [olaData]);

  const handleAnalyze = async () => {
    if (rvtoolsFile.length === 0 || databaseFile.length === 0) {
      setError('Please upload both RVTools and Database Inventory files');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('rvtools', rvtoolsFile[0]);
      formData.append('database_inventory', databaseFile[0]);
      formData.append('sa_status', saStatus.value);
      formData.append('region', region.value);

      const response = await fetch(getApiUrl('/map/ola/analyze'), {
        method: 'POST',
        body: formData
      });

      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.message);
      }

      setResults(result.summary);
      setOLAData({ results: result.summary });
      setActiveTabId('results');
    } catch (err) {
      setError(err.message || 'Failed to analyze OLA');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setResults(null);
    setRvtoolsFile([]);
    setDatabaseFile([]);
    setSaStatus({ label: 'Need to verify with Microsoft', value: 'need_verify' });
    setActiveTabId('decision-guidance');
    resetOLA();
  };

  const getOLABadgeType = (level) => {
    if (level === 'OLA Required') return 'red';
    if (level === 'OLA Strongly Recommended') return 'red';
    if (level === 'OLA Recommended') return 'blue';
    if (level === 'OLA Optional') return 'grey';
    return 'green';
  };

  // Render Results Tab Content
  const renderResults = () => {
    if (!results) return null;

    return (
      <SpaceBetween size="l">
        {/* OLA Recommendation */}
        <Container
          header={<Header variant="h2">OLA Engagement Recommendation</Header>}
        >
          <SpaceBetween size="m">
            <Box textAlign="center" padding="l">
              <SpaceBetween size="s" alignItems="center">
                <Badge color={getOLABadgeType(results.ola_recommendation.level)} size="large">
                  {results.ola_recommendation.level}
                </Badge>
                <Box variant="h3">
                  Estimated Annual ARR: ${results.estimated_annual_arr.toLocaleString()}
                </Box>
                <Box variant="p">
                  Complexity Score: {results.complexity_score}/10
                </Box>
              </SpaceBetween>
            </Box>

            <Box variant="h4">Rationale:</Box>
            <ul>
              {results.ola_recommendation.rationale.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>

            <Box variant="h4">Next Steps:</Box>
            <ul>
              {results.ola_recommendation.next_steps.map((step, idx) => (
                <li key={idx}>
                  {step.required && <Box variant="strong">[Required] </Box>}
                  {step.step}
                </li>
              ))}
            </ul>
          </SpaceBetween>
        </Container>

        {/* Summary Statistics */}
        <Container header={<Header variant="h2">Analysis Summary</Header>}>
          <SpaceBetween size="m">
            <ColumnLayout columns={3} variant="text-grid">
              <div>
                <Box variant="awsui-key-label">Total Servers</Box>
                <Box variant="h3">{results.total_servers}</Box>
                <Box variant="small">
                  {results.windows_servers} Windows, {results.linux_servers} Linux
                </Box>
              </div>
              <div>
                <Box variant="awsui-key-label">Total Databases</Box>
                <Box variant="h3">{results.total_databases}</Box>
                <Box variant="small">
                  {results.sql_server} SQL Server, {results.oracle} Oracle
                </Box>
              </div>
              <div>
                <Box variant="awsui-key-label">Estimated Monthly Cost</Box>
                <Box variant="h3">${results.estimated_monthly_cost.toLocaleString()}</Box>
                <Box variant="small">
                  ${results.estimated_annual_arr.toLocaleString()}/year ARR
                </Box>
              </div>
            </ColumnLayout>
            
            {results.cost_breakdown && (
              <Alert type="info">
                <SpaceBetween size="xs">
                  <Box variant="strong">Cost Estimate Breakdown:</Box>
                  <Box>
                    • Windows Servers: {results.cost_breakdown.windows_servers.count} × $200/mo = ${results.cost_breakdown.windows_servers.monthly.toLocaleString()}/mo<br/>
                    • Linux Servers: {results.cost_breakdown.linux_servers.count} × $100/mo = ${results.cost_breakdown.linux_servers.monthly.toLocaleString()}/mo<br/>
                    • SQL Databases: {results.cost_breakdown.sql_databases.count} × $500/mo = ${results.cost_breakdown.sql_databases.monthly.toLocaleString()}/mo<br/>
                    • Oracle Databases: {results.cost_breakdown.oracle_databases.count} × $800/mo = ${results.cost_breakdown.oracle_databases.monthly.toLocaleString()}/mo
                  </Box>
                  <Box variant="small" color="text-body-secondary">
                    {results.pricing_note}
                  </Box>
                </SpaceBetween>
              </Alert>
            )}
          </SpaceBetween>
        </Container>

        {/* Complexity Analysis */}
        <Container header={<Header variant="h2">Complexity Analysis (Score: {results.complexity_score}/10)</Header>}>
          <SpaceBetween size="m">
            <Box>
              <Box variant="strong">License Diversity: {results.complexity_breakdown.license_diversity.score}/2</Box>
              <Box variant="p">Products: {results.complexity_breakdown.license_diversity.products.join(', ')}</Box>
              <Box variant="small" color="text-body-secondary">
                Multiple Microsoft products increase licensing complexity
              </Box>
            </Box>
            <Box>
              <Box variant="strong">Software Assurance: {results.complexity_breakdown.sa_status.score}/2</Box>
              <Box variant="p">Status: {results.complexity_breakdown.sa_status.status.replace('_', ' ')}</Box>
              <Box variant="small" color="text-body-secondary">
                Active SA enables License Mobility and BYOL
              </Box>
            </Box>
            <Box>
              <Box variant="strong">Feature Dependencies: {results.complexity_breakdown.feature_dependencies.score}/2</Box>
              <Box variant="p">Enterprise features: {results.complexity_breakdown.feature_dependencies.count}</Box>
            </Box>
            <Box>
              <Box variant="strong">Environment Mix: {results.complexity_breakdown.environment_mix.score}/2</Box>
              <Box variant="p">Production: {results.complexity_breakdown.environment_mix.production} of {results.complexity_breakdown.environment_mix.total}</Box>
            </Box>
            <Box>
              <Box variant="strong">Scale: {results.complexity_breakdown.scale.score}/2</Box>
              <Box variant="p">Total resources: {results.complexity_breakdown.scale.total_resources}</Box>
            </Box>
          </SpaceBetween>
        </Container>
      </SpaceBetween>
    );
  };

  // Render Decision Guidance Tab Content
  const renderDecisionGuidance = () => {
    return (
      <SpaceBetween size="l">
        {/* Header */}
        <Alert type="info">
          <SpaceBetween size="xs">
            <Box variant="strong">⚠️ Assumption-Based Migration Strategy</Box>
            <Box>
              When full OLA assessment cannot proceed and licensing details are unavailable, 
              use these strategic defaults for business case development. These recommendations 
              balance cost, risk, and modernization benefits.
            </Box>
          </SpaceBetween>
        </Alert>

        {/* Database Recommendation */}
        <ExpandableSection
          headerText="🗄️ Databases: Migrate to RDS (License Included)"
          variant="container"
          defaultExpanded={true}
        >
          <SpaceBetween size="m">
            <Box variant="h4">Recommendation:</Box>
            <Box>Move all SQL Server and Oracle databases to Amazon RDS with License Included</Box>
            
            <Box variant="h4">Rationale:</Box>
            <ul>
              <li>Eliminates license compliance risk - AWS manages all licensing</li>
              <li>Modernization benefits: Automated backups, patching, and high availability</li>
              <li>Reduced operational overhead - No database administration required</li>
              <li>Predictable costs - No surprise license audits or true-ups</li>
              <li>Faster migration - No license verification delays</li>
            </ul>
            
            <Box variant="h4">Tradeoff:</Box>
            <Box>Higher monthly cost vs BYOL, but justified by operational savings and reduced risk</Box>
            
            <Box variant="h4">Action:</Box>
            <Box variant="strong">Include RDS License Included pricing in business case</Box>
          </SpaceBetween>
        </ExpandableSection>

        {/* Windows Server Recommendation */}
        <ExpandableSection
          headerText="🖥️ Windows Servers: EC2 with License Included"
          variant="container"
          defaultExpanded={true}
        >
          <SpaceBetween size="m">
            <Box variant="h4">Recommendation:</Box>
            <Box>Deploy Windows servers on EC2 with License Included</Box>
            
            <Box variant="h4">Rationale:</Box>
            <ul>
              <li>License flexibility - Scale up/down without license constraints</li>
              <li>No Microsoft audit risk - AWS handles compliance</li>
              <li>Faster migration - No license verification required</li>
              <li>Pay-as-you-go - Only pay for what you use</li>
              <li>No upfront license investment required</li>
            </ul>
            
            <Box variant="h4">Tradeoff:</Box>
            <Box>Higher cost than BYOL, but provides maximum flexibility and zero license risk</Box>
            
            <Box variant="h4">Action:</Box>
            <Box variant="strong">Include EC2 Windows License Included pricing in business case</Box>
          </SpaceBetween>
        </ExpandableSection>

        {/* Exception for SQL with SA */}
        <ExpandableSection
          headerText="💡 Exception: SQL Server with Active Software Assurance"
          variant="container"
        >
          <SpaceBetween size="m">
            <Box variant="h4">Recommendation:</Box>
            <Box>If SQL Server licenses have confirmed active SA, consider Dedicated Hosts for BYOL</Box>
            
            <Box variant="h4">Rationale:</Box>
            <ul>
              <li>Maximize existing license investment</li>
              <li>Significant cost savings vs License Included</li>
              <li>License Mobility rights enable BYOL on AWS</li>
              <li>Suitable for stable, long-term workloads</li>
            </ul>
            
            <Box variant="h4">Requirements:</Box>
            <ul>
              <li>Must verify active Software Assurance</li>
              <li>Must have License Mobility rights</li>
              <li>Must be comfortable managing licenses on AWS</li>
              <li>Workload must be stable (not highly elastic)</li>
            </ul>
            
            <Box variant="h4">Action:</Box>
            <Box variant="strong">If SA confirmed, calculate Dedicated Host BYOL option as alternative</Box>
          </SpaceBetween>
        </ExpandableSection>

        {/* ARR Impact */}
        <Container header={<Header variant="h3">📊 ARR Impact Assessment</Header>}>
          <SpaceBetween size="m">
            <Box>
              <Box variant="strong">Low ARR (&lt;$100K/year):</Box>
              <Box>Proceed with assumptions - licensing cost difference has minimal impact on overall business case</Box>
            </Box>
            <Box>
              <Box variant="strong">Medium ARR ($100K-$500K/year):</Box>
              <Box>Consider pursuing OLA if timeline allows - potential savings justify effort</Box>
            </Box>
            <Box>
              <Box variant="strong">High ARR (&gt;$500K/year):</Box>
              <Box>OLA strongly recommended - significant potential savings warrant detailed analysis</Box>
            </Box>
          </SpaceBetween>
        </Container>

        {/* Summary Strategy */}
        <Alert type="success">
          <SpaceBetween size="xs">
            <Box variant="strong">✅ Recommended Approach for Business Case</Box>
            <Box variant="h4">Strategy:</Box>
            <ol>
              <li>Use RDS License Included for all databases (modernization + risk reduction)</li>
              <li>Use EC2 License Included for Windows servers (flexibility + compliance)</li>
              <li>Exception: Use Dedicated Host BYOL only for SQL Server with confirmed active SA</li>
              <li>Document all assumptions clearly in business case</li>
              <li>Plan for license optimization review post-migration if ARR is significant</li>
            </ol>
            
            <Box variant="h4">Benefits:</Box>
            <ul>
              <li>Fastest path to migration</li>
              <li>Lowest risk approach</li>
              <li>Predictable costs</li>
              <li>Modernization benefits</li>
              <li>No license compliance concerns</li>
            </ul>
          </SpaceBetween>
        </Alert>
      </SpaceBetween>
    );
  };

  return (
    <SpaceBetween size="l">
      <Container
        header={
          <Header
            variant="h1"
            description="Preliminary licensing optimization assessment for AWS migration"
            actions={
              results && (
                <Button onClick={handleReset}>
                  Reset
                </Button>
              )
            }
          >
            Preliminary OLA Analysis
          </Header>
        }
      >
        <Tabs
          activeTabId={activeTabId}
          onChange={({ detail }) => setActiveTabId(detail.activeTabId)}
          tabs={[
            {
              id: 'input',
              label: 'Input',
              content: (
                <SpaceBetween size="m">
                  <Alert type="warning">
                    <SpaceBetween size="xs">
                      <Box variant="strong">⚠️ IMPORTANT DISCLAIMERS</Box>
                      <Box>
                        • This is NOT a replacement for official AWS OLA<br/>
                        • Preliminary assessment only - requires license verification<br/>
                        • Please share existing license agreements for detailed review<br/>
                        • Microsoft Oct 2019 licensing changes may impact costs
                      </Box>
                    </SpaceBetween>
                  </Alert>

                  <Alert type="info">
                    <SpaceBetween size="xs">
                      <Box variant="strong">📅 Microsoft October 1, 2019 Licensing Changes</Box>
                      <Box>
                        Microsoft implemented significant licensing changes affecting BYOL deployments 
                        on "Listed Providers" like AWS:
                      </Box>
                      <ul>
                        <li>Products without License Mobility require Dedicated Hosts</li>
                        <li>BYOL on shared EC2 requires active Software Assurance (SA)</li>
                        <li>Windows Server & SQL Server without SA must use Dedicated Hosts</li>
                        <li>License Included options are not affected</li>
                      </ul>
                      <Box variant="strong">⚠️ Action Required: Verify your SA status before proceeding</Box>
                    </SpaceBetween>
                  </Alert>

                  <SpaceBetween size="l">
                    <FormField
                      label="RVTools Export"
                      description="Upload your RVTools CSV or Excel export containing server inventory"
                    >
                      <FileUpload
                        value={rvtoolsFile}
                        onChange={({ detail }) => setRvtoolsFile(detail.value)}
                        accept=".csv,.xlsx,.xls"
                        constraintText="CSV or Excel files only"
                      />
                    </FormField>

                    <FormField
                      label="Database Inventory"
                      description="Upload database inventory CSV with SQL Server, Oracle, and other databases"
                    >
                      <FileUpload
                        value={databaseFile}
                        onChange={({ detail }) => setDatabaseFile(detail.value)}
                        accept=".csv,.xlsx,.xls"
                        constraintText="CSV or Excel files only"
                      />
                    </FormField>

                    <FormField
                      label="Software Assurance Status"
                      description="Select your current SA status (critical for cost estimates)"
                    >
                      <Select
                        selectedOption={saStatus}
                        onChange={({ detail }) => setSaStatus(detail.selectedOption)}
                        options={saStatusOptions}
                      />
                    </FormField>

                    <FormField
                      label="AWS Region"
                      description="Target AWS region for migration"
                    >
                      <Select
                        selectedOption={region}
                        onChange={({ detail }) => setRegion(detail.selectedOption)}
                        options={regionOptions}
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
                      <Box textAlign="center" padding="l">
                        <SpaceBetween size="m" alignItems="center">
                          <Spinner size="large" />
                          <Box variant="p" color="text-body-secondary">
                            Analyzing licensing and calculating costs with AWS Pricing API... This may take 2-3 minutes.
                          </Box>
                          <ProgressBar value={50} />
                        </SpaceBetween>
                      </Box>
                    )}

                    <Box textAlign="center">
                      <Button
                        variant="primary"
                        onClick={handleAnalyze}
                        disabled={loading || rvtoolsFile.length === 0 || databaseFile.length === 0}
                        iconName="search"
                      >
                        Run Preliminary Analysis
                      </Button>
                    </Box>
                  </SpaceBetween>
                </SpaceBetween>
              )
            },
            {
              id: 'results',
              label: 'Results',
              disabled: !results,
              content: results ? renderResults() : (
                <Box textAlign="center" padding="l">
                  <Box variant="p" color="text-body-secondary">
                    Run analysis to see results
                  </Box>
                </Box>
              )
            },
            {
              id: 'decision-guidance',
              label: 'Decision Guidance',
              content: renderDecisionGuidance()
            }
          ]}
        />
      </Container>
    </SpaceBetween>
  );
}

export default OLAAnalysis;
