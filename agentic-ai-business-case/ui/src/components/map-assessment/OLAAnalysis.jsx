import React, { useState, useEffect } from 'react';
import * as XLSX from 'xlsx';
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
  const [activeTabId, setActiveTabId] = useState('input');
  
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
    setActiveTabId('input');
    resetOLA();
  };

  const handleDownloadExcel = () => {
    if (!results) return;
    
    // Create workbook
    const wb = XLSX.utils.book_new();
    
    // Sheet 1: Summary
    const summaryData = [
      ['OLA Analysis Summary'],
      [''],
      ['Total Servers', results.total_servers],
      ['Windows Servers', results.windows_servers],
      ['Linux Servers', results.linux_servers],
      ['Total Databases', results.total_databases],
      ['SQL Server Databases', results.sql_server],
      ['Oracle Databases', results.oracle],
      [''],
      ['Estimated Monthly Cost (LI)', `$${results.estimated_monthly_cost.toLocaleString()}`],
      ['Estimated Annual ARR', `$${results.estimated_annual_arr.toLocaleString()}`],
    ];
    const ws1 = XLSX.utils.aoa_to_sheet(summaryData);
    XLSX.utils.book_append_sheet(wb, ws1, 'Summary');
    
    // Sheet 2: Option 1 - EC2 Shared (LI)
    if (results.cost_breakdown?.option_1_ec2_shared_li) {
      const opt1 = results.cost_breakdown.option_1_ec2_shared_li;
      const opt1Data = [
        ['Option 1: EC2 Shared Instances (License Included)'],
        [''],
        ['Description', opt1.description],
        [''],
        ['Windows Servers', opt1.windows_count],
        ['Linux Servers', opt1.linux_count],
        [''],
        ['Monthly Cost', `$${opt1.total_monthly.toLocaleString()}`],
        ['Annual Cost', `$${opt1.total_annual.toLocaleString()}`],
        [''],
        ['Pricing Model', '3-Year Reserved Instance, No Upfront'],
      ];
      const ws2 = XLSX.utils.aoa_to_sheet(opt1Data);
      XLSX.utils.book_append_sheet(wb, ws2, 'Option 1 - EC2 Shared');
    }
    
    // Sheet 3: Option 2 - Dedicated Hosts (BYOL)
    if (results.cost_breakdown?.option_2_dedicated_host_byol) {
      const opt2 = results.cost_breakdown.option_2_dedicated_host_byol;
      const opt2Data = [
        ['Option 2: Dedicated Hosts (BYOL)'],
        [''],
        ['Description', opt2.description],
        [''],
        ['Dedicated Hosts for Windows', opt2.host_count],
        ['Average Utilization', `${opt2.vms_per_host.toFixed(1)}%`],
        ['Dedicated Hosts for SQL Server', opt2.sql_host_count || 0],
        [''],
        ['Monthly Cost', `$${opt2.total_monthly.toLocaleString()}`],
        ['Annual Cost', `$${opt2.total_annual.toLocaleString()}`],
        [''],
        ['Potential Savings vs LI', `$${opt2.savings_vs_li.toLocaleString()}/year`],
        ['Savings Percentage', `${opt2.savings_percentage.toFixed(1)}%`],
        [''],
        ['Pricing Model', '3-Year Reserved Instance, No Upfront'],
        ['Requirements', 'Active Software Assurance for post-Oct 2019 licenses'],
      ];
      const ws3 = XLSX.utils.aoa_to_sheet(opt2Data);
      XLSX.utils.book_append_sheet(wb, ws3, 'Option 2 - Dedicated Hosts');
    }
    
    // Sheet 4: Option 3 - RDS (LI)
    if (results.cost_breakdown?.option_3_rds_li) {
      const opt3 = results.cost_breakdown.option_3_rds_li;
      const opt3Data = [
        ['Option 3: RDS (License Included)'],
        [''],
        ['Description', opt3.description],
        [''],
        ['SQL Server Databases', opt3.sql_count],
        ['Oracle Databases', opt3.oracle_count],
        [''],
        ['Monthly Cost', `$${opt3.total_monthly.toLocaleString()}`],
        ['Annual Cost', `$${opt3.total_annual.toLocaleString()}`],
        [''],
        ['Pricing Model', '3-Year Reserved Instance, No Upfront'],
      ];
      const ws4 = XLSX.utils.aoa_to_sheet(opt3Data);
      XLSX.utils.book_append_sheet(wb, ws4, 'Option 3 - RDS');
    }
    
    // Sheet 5: Version Breakdown
    if (results.cost_breakdown?.version_breakdown) {
      const vb = results.cost_breakdown.version_breakdown;
      const vbData = [
        ['Version Breakdown (Microsoft Oct 2019 Licensing)'],
        [''],
        ['Windows Server'],
        ['Pre-Oct 2019', vb.windows_pre_2019, 'BYOL eligible without SA'],
        ['Post-Oct 2019', vb.windows_post_2019, 'Requires SA for BYOL'],
        ['Unknown Version', vb.windows_unknown],
        [''],
        ['SQL Server'],
        ['Pre-Oct 2019', vb.sql_pre_2019, 'BYOL eligible without SA'],
        ['Post-Oct 2019', vb.sql_post_2019, 'Requires SA for BYOL'],
        ['Unknown Version', vb.sql_unknown],
      ];
      const ws5 = XLSX.utils.aoa_to_sheet(vbData);
      XLSX.utils.book_append_sheet(wb, ws5, 'Version Breakdown');
    }
    
    // Sheet 6: Server Instance Mapping (detailed per-server breakdown)
    if (results.server_details && results.server_details.length > 0) {
      const serverRows = [
        ['Server Instance Mapping — Detailed Breakdown'],
        [''],
        ['Server Name', 'OS', 'vCPU', 'Memory (GB)', 'Mapped EC2 Instance', 'EC2 Shared LI ($/mo)', 'Dedicated Host BYOL ($/mo)', 'License Date', 'BYOL Eligible']
      ];
      results.server_details.forEach(s => {
        serverRows.push([
          s.server_name || '',
          s.os || '',
          s.vcpu || '',
          s.memory || '',
          s.instance_type || '',
          s.shared_ec2_li != null ? Number(s.shared_ec2_li).toFixed(2) : 'N/A',
          s.dedicated_host_byol != null ? Number(s.dedicated_host_byol).toFixed(2) : 'N/A',
          s.license_date || '',
          s.can_use_byol ? 'Yes' : 'No'
        ]);
      });
      const ws6 = XLSX.utils.aoa_to_sheet(serverRows);
      // Set column widths
      ws6['!cols'] = [
        { wch: 25 }, { wch: 30 }, { wch: 8 }, { wch: 12 },
        { wch: 18 }, { wch: 20 }, { wch: 24 }, { wch: 14 }, { wch: 14 }
      ];
      XLSX.utils.book_append_sheet(wb, ws6, 'Server Details');
    }
    
    // Sheet 7: Database Instance Mapping (detailed per-database breakdown)
    if (results.database_details && results.database_details.length > 0) {
      const dbRows = [
        ['Database Instance Mapping — Detailed Breakdown'],
        [''],
        ['Database Name', 'Type', 'Edition', 'Version', 'vCPU', 'Memory (GB)', 'Mapped RDS Instance', 'RDS LI ($/mo)', 'Dedicated Host BYOL ($/mo)', 'License Date', 'BYOL Eligible']
      ];
      results.database_details.forEach(d => {
        dbRows.push([
          d.db_name || '',
          d.db_type || '',
          d.edition || '',
          d.version || '',
          d.vcpu || '',
          d.memory || '',
          d.instance_type || '',
          d.rds_li != null ? Number(d.rds_li).toFixed(2) : 'N/A',
          d.dedicated_host_byol != null ? Number(d.dedicated_host_byol).toFixed(2) : 'N/A',
          d.license_date || '',
          d.can_use_byol ? 'Yes' : 'No'
        ]);
      });
      const ws7 = XLSX.utils.aoa_to_sheet(dbRows);
      ws7['!cols'] = [
        { wch: 25 }, { wch: 15 }, { wch: 14 }, { wch: 18 }, { wch: 8 },
        { wch: 12 }, { wch: 18 }, { wch: 16 }, { wch: 24 }, { wch: 14 }, { wch: 14 }
      ];
      XLSX.utils.book_append_sheet(wb, ws7, 'Database Details');
    }
    
    // Download
    XLSX.writeFile(wb, 'OLA_Analysis_Results.xlsx');
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
                <Box variant="awsui-key-label">Estimated Monthly Cost (LI)</Box>
                <Box variant="h3">${results.estimated_monthly_cost.toLocaleString()}</Box>
                <Box variant="small">
                  ${results.estimated_annual_arr.toLocaleString()}/year ARR
                </Box>
              </div>
            </ColumnLayout>
            
            {results.cost_breakdown && results.cost_breakdown.version_breakdown && (
              <Alert type="info">
                <SpaceBetween size="xs">
                  <Box variant="strong">📊 Version Breakdown (Microsoft Oct 2019 Licensing):</Box>
                  <Box>
                    • Windows Server Pre-2019: {results.cost_breakdown.version_breakdown.windows_pre_2019} (BYOL eligible without SA)<br/>
                    • Windows Server Post-2019: {results.cost_breakdown.version_breakdown.windows_post_2019} (requires SA for BYOL)<br/>
                    • Windows Server Unknown: {results.cost_breakdown.version_breakdown.windows_unknown}<br/>
                    • SQL Server Pre-2019: {results.cost_breakdown.version_breakdown.sql_pre_2019} (BYOL eligible without SA)<br/>
                    • SQL Server Post-2019: {results.cost_breakdown.version_breakdown.sql_post_2019} (requires SA for BYOL)<br/>
                    • SQL Server Unknown: {results.cost_breakdown.version_breakdown.sql_unknown}
                  </Box>
                </SpaceBetween>
              </Alert>
            )}
          </SpaceBetween>
        </Container>

        {/* Migration Options Comparison */}
        {results.cost_breakdown && (
          <Container header={<Header variant="h2">💰 Migration Cost Options (AWS Pricing API)</Header>}>
            <SpaceBetween size="l">
              {/* Option 1: EC2 Shared (License Included) */}
              <ExpandableSection
                headerText={`Option 1: ${results.cost_breakdown.option_1_ec2_shared_li?.name || 'EC2 Shared (License Included)'}`}
                variant="container"
                defaultExpanded={true}
              >
                <SpaceBetween size="m">
                  <Box>{results.cost_breakdown.option_1_ec2_shared_li?.description}</Box>
                  <ColumnLayout columns={2} variant="text-grid">
                    <div>
                      <Box variant="awsui-key-label">Monthly Cost</Box>
                      <Box variant="h3">${results.cost_breakdown.option_1_ec2_shared_li?.total_monthly.toLocaleString()}</Box>
                    </div>
                    <div>
                      <Box variant="awsui-key-label">Annual Cost</Box>
                      <Box variant="h3">${results.cost_breakdown.option_1_ec2_shared_li?.total_annual.toLocaleString()}</Box>
                    </div>
                  </ColumnLayout>
                  <Box variant="small" color="text-body-secondary">
                    {results.cost_breakdown.option_1_ec2_shared_li?.windows_count} Windows + {results.cost_breakdown.option_1_ec2_shared_li?.linux_count} Linux servers
                  </Box>
                </SpaceBetween>
              </ExpandableSection>

              {/* Option 2: Dedicated Hosts (BYOL) */}
              <ExpandableSection
                headerText={`Option 2: ${results.cost_breakdown.option_2_dedicated_host_byol?.name || 'Dedicated Hosts (BYOL)'}`}
                variant="container"
                defaultExpanded={true}
              >
                <SpaceBetween size="m">
                  <Box>{results.cost_breakdown.option_2_dedicated_host_byol?.description}</Box>
                  <ColumnLayout columns={2} variant="text-grid">
                    <div>
                      <Box variant="awsui-key-label">Monthly Cost</Box>
                      <Box variant="h3">${results.cost_breakdown.option_2_dedicated_host_byol?.total_monthly.toLocaleString()}</Box>
                    </div>
                    <div>
                      <Box variant="awsui-key-label">Annual Cost</Box>
                      <Box variant="h3">${results.cost_breakdown.option_2_dedicated_host_byol?.total_annual.toLocaleString()}</Box>
                    </div>
                  </ColumnLayout>
                  {results.cost_breakdown.option_2_dedicated_host_byol?.savings_vs_li > 0 && (
                    <Alert type="success">
                      <Box variant="strong">
                        💰 Potential Savings: ${results.cost_breakdown.option_2_dedicated_host_byol?.savings_vs_li.toLocaleString()}/year 
                        ({results.cost_breakdown.option_2_dedicated_host_byol?.savings_percentage.toFixed(1)}% lower than License Included)
                      </Box>
                    </Alert>
                  )}
                  <Box variant="small" color="text-body-secondary">
                    {results.cost_breakdown.option_2_dedicated_host_byol?.host_count} Dedicated Hosts for Windows 
                    ({results.cost_breakdown.option_2_dedicated_host_byol?.vms_per_host.toFixed(1)}% avg utilization)
                    {results.cost_breakdown.option_2_dedicated_host_byol?.sql_host_count > 0 && 
                      ` + ${results.cost_breakdown.option_2_dedicated_host_byol?.sql_host_count} hosts for SQL Server`}
                  </Box>
                </SpaceBetween>
              </ExpandableSection>

              {/* Option 3: RDS (License Included) */}
              <ExpandableSection
                headerText={`Option 3: ${results.cost_breakdown.option_3_rds_li?.name || 'RDS (License Included)'}`}
                variant="container"
                defaultExpanded={true}
              >
                <SpaceBetween size="m">
                  <Box>{results.cost_breakdown.option_3_rds_li?.description}</Box>
                  <ColumnLayout columns={2} variant="text-grid">
                    <div>
                      <Box variant="awsui-key-label">Monthly Cost</Box>
                      <Box variant="h3">${results.cost_breakdown.option_3_rds_li?.total_monthly.toLocaleString()}</Box>
                    </div>
                    <div>
                      <Box variant="awsui-key-label">Annual Cost</Box>
                      <Box variant="h3">${results.cost_breakdown.option_3_rds_li?.total_annual.toLocaleString()}</Box>
                    </div>
                  </ColumnLayout>
                  <Box variant="small" color="text-body-secondary">
                    {results.cost_breakdown.option_3_rds_li?.sql_count} SQL Server + {results.cost_breakdown.option_3_rds_li?.oracle_count} Oracle databases
                  </Box>
                </SpaceBetween>
              </ExpandableSection>

              <Alert type="info">
                <Box variant="small">{results.pricing_note}</Box>
              </Alert>
            </SpaceBetween>
          </Container>
        )}

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

        {/* SQL Server with Active SA */}
        <ExpandableSection
          headerText="🗄️ SQL Server with Active Software Assurance — BYOL Options"
          variant="container"
          defaultExpanded={true}
        >
          <SpaceBetween size="m">
            <Box variant="strong">Option A: Shared EC2 (BYOL via License Mobility) — Primary Recommendation</Box>
            <Box>
              This is the primary/default recommendation for active SA customers. Bring your own
              licenses to standard shared EC2 instances. No dedicated hardware required. Offers full
              elasticity and scaling flexibility. Purchase date and SQL Server version do NOT matter —
              only active SA is required.
            </Box>

            <Box variant="strong">Option B: Dedicated Hosts (BYOL)</Box>
            <Box>
              Also valid with active SA. Recommended when the customer needs dedicated hardware for
              compliance/regulatory reasons, or when they also have Windows Server licenses without SA
              (pre-10/1/2019) that require Dedicated Hosts. Can yield ~44.5% cost savings vs License
              Included on comparable instance types.
            </Box>

            <Box variant="strong">Option C: Shared EC2 (License Included)</Box>
            <Box>
              Pay AWS for SQL Server licenses. No BYOL required. Most flexible for elastic/variable workloads.
            </Box>
          </SpaceBetween>
        </ExpandableSection>

        {/* Windows Server BYOL Options */}
        <ExpandableSection
          headerText="🖥️ Windows Server with Active Software Assurance — BYOL Options"
          variant="container"
          defaultExpanded={true}
        >
          <SpaceBetween size="m">
            <Box variant="strong">Option A: Dedicated Hosts (BYOL) — Only BYOL Path for Windows Server</Box>
            <Box>
              This is the ONLY BYOL path for Windows Server on AWS. Unlike SQL Server, Windows Server
              does not qualify for License Mobility, meaning it cannot be brought to shared EC2 instances.
              Dedicated Hosts are always required for Windows Server BYOL. Eligible only for Windows Server
              versions released before October 1, 2019 (Windows Server 2016 and earlier). Active SA is required.
            </Box>

            <Box variant="strong">Option B: Shared EC2 (License Included)</Box>
            <Box>
              Pay AWS for Windows Server licenses bundled into the EC2 instance price. No SA or BYOL required.
              Supports all Windows Server versions including 2019, 2022, and 2025. Most flexible for
              elastic/variable workloads and the only viable path for Windows Server 2019 and later on AWS.
            </Box>

            <Box variant="strong">Option C: Dedicated Hosts (License Included)</Box>
            <Box>
              Dedicated hardware with AWS-provided Windows Server licensing. No BYOL or SA required.
              Suitable for compliance/regulatory requirements where dedicated hardware is needed but
              license management overhead should be avoided.
            </Box>
          </SpaceBetween>
        </ExpandableSection>

        {/* Oracle Database Options */}
        <ExpandableSection
          headerText="🛢️ Oracle Database with Active Software Update License & Support (SULS) — Options"
          variant="container"
          defaultExpanded={true}
        >
          <SpaceBetween size="m">
            <Box variant="strong">Option A: EC2 BYOL (Self-Managed)</Box>
            <Box>
              Bring your existing Oracle licenses to Amazon EC2. Full control over OS and database
              configuration. Supports Enterprise Edition (EE) and Standard Edition 2 (SE2). No dedicated
              hardware required — any EC2 tenancy is permitted. Active SULS is required.
              Note: Oracle's Core Factor Table does not apply on AWS — 1 processor license covers 2 vCPUs
              (vs. 4 vCPUs on-premises for Intel/AMD). Best for complex workloads, EE features, or
              customers with large existing Oracle estates.
            </Box>

            <Box variant="strong">Option B: Amazon RDS for Oracle (BYOL)</Box>
            <Box>
              Managed database service using your own Oracle licenses. AWS handles patching, backups,
              and high availability. Supports SE2 and EE editions. Active SULS required. Same Oracle
              cloud vCPU counting rules apply as EC2 BYOL. Best for customers wanting managed
              infrastructure while leveraging existing Oracle licenses.
            </Box>

            <Box variant="strong">Option C: Amazon RDS for Oracle (License Included)</Box>
            <Box>
              Pay AWS for Oracle SE2 licenses bundled into RDS pricing. No separate Oracle license
              purchase or SULS required. Only SE2 is available under License Included — Enterprise
              Edition is not offered. Higher per-hour cost but zero license management overhead.
              Best for smaller workloads, SE2-compatible applications, or customers without existing
              Oracle licenses.
            </Box>

            <Box variant="strong">Option D: Amazon RDS Custom for Oracle (BYOL)</Box>
            <Box>
              Managed service with OS and database-level customization. Supports BYOL only. Allows
              custom patches, agents, and configurations not possible in standard RDS. Active SULS
              required. Best for Oracle applications requiring OS-level access such as Oracle E-Business Suite.
            </Box>
          </SpaceBetween>
        </ExpandableSection>

        {/* ARR Impact */}
        <Alert type="info">
          <SpaceBetween size="xs">
            <Box variant="strong">📊 ARR Impact Assessment</Box>
            <Box variant="h4">When to Proceed with Assumptions vs Full OLA:</Box>
            <SpaceBetween size="s">
              <Box>
                <Box variant="strong">Low ARR (&lt;$100K/year):</Box>
                <Box>Proceed with assumptions — licensing cost difference has minimal impact on overall business case</Box>
              </Box>
              <Box>
                <Box variant="strong">Medium ARR ($100K–$500K/year):</Box>
                <Box>Consider pursuing OLA if timeline allows — potential savings justify effort</Box>
              </Box>
              <Box>
                <Box variant="strong">High ARR (&gt;$500K/year):</Box>
                <Box>OLA strongly recommended — significant potential savings warrant detailed analysis</Box>
              </Box>
            </SpaceBetween>
          </SpaceBetween>
        </Alert>

        {/* Summary Strategy */}
        <Container header={<Header variant="h3">✅ Summary: Assumption-Based Strategy</Header>}>
          <SpaceBetween size="m">
            <Box variant="h4">Recommended Approach:</Box>
            <ol>
              <li>SQL Server with active SA: Use Shared EC2 BYOL via License Mobility (primary) or Dedicated Hosts BYOL for compliance needs</li>
              <li>Windows Server with active SA (pre-2019 only): Use Dedicated Hosts BYOL; for 2019+ use EC2 License Included</li>
              <li>Oracle with active SULS: Use EC2 BYOL or RDS BYOL; without SULS use RDS License Included (SE2 only)</li>
              <li>When licensing status is unknown: Default to License Included for all Windows Server on EC2 and modernize DB to RDS (zero license risk and modernization benefits)</li>
              <li>Document all assumptions clearly in business case</li>
            </ol>
          </SpaceBetween>
        </Container>
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
                <SpaceBetween direction="horizontal" size="xs">
                  <Button onClick={handleDownloadExcel} iconName="download">
                    Download Excel
                  </Button>
                  <Button onClick={handleReset}>
                    Reset
                  </Button>
                </SpaceBetween>
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
