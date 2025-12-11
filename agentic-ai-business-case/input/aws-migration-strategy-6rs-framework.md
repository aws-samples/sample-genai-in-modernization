# AWS Migration Strategy - 6Rs Framework

## Overview
The AWS Migration Strategy framework, commonly known as the "6Rs," provides a structured approach to categorizing applications for cloud migration. Each strategy represents a different migration pattern with varying levels of effort, cost, and business value.

## The 6Rs Migration Strategies

### 1. Rehost (Lift and Shift)
**Description**: Move applications to AWS without making changes to the application architecture.

**Characteristics**:
- Minimal code changes
- Fastest migration path
- Lower initial cost
- Limited cloud optimization

**Best For**:
- Legacy applications with no business case for re-architecture
- Applications requiring quick migration (e.g., data center exit)
- Large-scale migrations with tight timelines
- Applications with unclear business value

**Typical Effort**: Low to Medium
**Typical Timeline**: 1-3 months per application
**Cost Optimization**: 20-30% savings vs. on-premises

**AWS Services**:
- AWS Application Migration Service (MGN)
- AWS Server Migration Service (SMS)
- CloudEndure Migration
- EC2 instances

---

### 2. Replatform (Lift, Tinker, and Shift)
**Description**: Make minimal cloud optimizations without changing core architecture.

**Characteristics**:
- Some optimization for cloud
- Moderate effort
- Better performance and cost efficiency than rehost
- Maintains application core

**Best For**:
- Applications that can benefit from managed services
- Database migrations to RDS, Aurora
- Applications needing better scalability
- Modernization without full re-architecture

**Typical Effort**: Medium
**Typical Timeline**: 2-4 months per application
**Cost Optimization**: 30-40% savings vs. on-premises

**Common Changes**:
- Migrate databases to Amazon RDS or Aurora
- Use Elastic Load Balancing
- Implement Auto Scaling
- Move to managed services where possible

**AWS Services**:
- Amazon RDS, Aurora
- Elastic Load Balancing
- Auto Scaling
- Amazon ElastiCache

---

### 3. Repurchase (Drop and Shop)
**Description**: Move to a different product, typically a SaaS solution.

**Characteristics**:
- Replace existing application with SaaS
- No infrastructure management
- Subscription-based pricing
- May require business process changes

**Best For**:
- Legacy commercial software with SaaS alternatives
- Applications with high maintenance costs
- Standard business functions (CRM, HR, Finance)
- Organizations wanting to reduce technical debt

**Typical Effort**: Medium to High (due to data migration and integration)
**Typical Timeline**: 3-6 months per application
**Cost Model**: Subscription-based (OpEx vs. CapEx)

**Examples**:
- Migrate from on-premises CRM to Salesforce
- Move from Exchange to Microsoft 365
- Replace custom HR system with Workday
- Move from on-premises ERP to SAP S/4HANA Cloud

---

### 4. Refactor / Re-architect
**Description**: Re-imagine application architecture using cloud-native features.

**Characteristics**:
- Highest effort and cost
- Maximum cloud benefits
- Improved agility and scalability
- Modern architecture patterns

**Best For**:
- Business-critical applications
- Applications requiring significant scalability
- Monoliths needing to become microservices
- Applications with strong business case for modernization

**Typical Effort**: High
**Typical Timeline**: 6-18 months per application
**Cost Optimization**: 40-60% savings vs. on-premises (long-term)

**Common Patterns**:
- Monolith to microservices
- Serverless architecture
- Containerization (ECS, EKS)
- Event-driven architecture

**AWS Services**:
- AWS Lambda
- Amazon ECS, EKS
- Amazon API Gateway
- Amazon EventBridge
- AWS Step Functions
- Amazon DynamoDB

---

### 5. Retire
**Description**: Decommission applications that are no longer needed.

**Characteristics**:
- Zero migration cost
- Immediate cost savings
- Reduced complexity
- Risk mitigation

**Best For**:
- Redundant applications
- Applications with <5% usage
- Shadow IT applications
- End-of-life systems

**Typical Effort**: Low (decommissioning process)
**Cost Savings**: 100% of application costs

**Process**:
1. Identify low-usage applications
2. Validate with business stakeholders
3. Archive data if needed
4. Decommission infrastructure

---

### 6. Retain (Revisit)
**Description**: Keep applications in source environment (on-premises or other cloud).

**Characteristics**:
- No immediate migration
- Defer decision to future
- May migrate later
- Keep running as-is

**Best For**:
- Applications recently upgraded
- Applications with compliance restrictions
- Applications requiring major refactoring (not ready yet)
- Applications with unclear business value
- Mainframe applications

**Typical Timeline**: Revisit in 6-12 months

**Reasons to Retain**:
- Recent significant investment
- Regulatory or compliance constraints
- High complexity with unclear ROI
- Dependencies on other systems not yet migrated
- Lack of business sponsorship

---

## Migration Strategy Selection Criteria

### Decision Matrix

| Criteria | Rehost | Replatform | Repurchase | Refactor | Retire | Retain |
|----------|--------|------------|------------|----------|--------|--------|
| **Speed to Cloud** | Fast | Medium | Medium | Slow | Immediate | N/A |
| **Cost (Initial)** | Low | Medium | Medium | High | None | None |
| **Cloud Optimization** | Low | Medium | High | Very High | N/A | N/A |
| **Business Risk** | Low | Low-Med | Medium | High | Low | Low |
| **Technical Complexity** | Low | Medium | Medium | High | Low | N/A |
| **Ongoing Costs** | Medium | Low-Med | Medium | Low | None | Current |

### Key Considerations

1. **Business Criticality**
   - High: Consider Refactor or Replatform
   - Medium: Rehost or Replatform
   - Low: Retire or Retain

2. **Technical Debt**
   - High: Refactor or Repurchase
   - Medium: Replatform
   - Low: Rehost

3. **Compliance Requirements**
   - Strict: May require Retain or specific Refactor
   - Standard: Any strategy applicable

4. **Timeline Pressure**
   - Urgent: Rehost
   - Moderate: Replatform
   - Flexible: Refactor

5. **Budget Constraints**
   - Limited: Rehost or Retire
   - Moderate: Replatform or Repurchase
   - Flexible: Refactor

---

## Default Application Portfolio Distribution (Industry Standard)

**IMPORTANT**: These percentages should be used as default assumptions ONLY when detailed application portfolio assessment is NOT available. Always recommend conducting a comprehensive portfolio assessment for accurate, customer-specific distribution.

### Recommended Distribution by 6Rs

Based on industry standards and AWS best practices:

| Strategy | % of Portfolio (Range) | Typical % | Typical Use Case |
|----------|----------------------|-----------|------------------|
| **Rehost** | **40-60%** | **50%** | Majority of applications - quick migration with minimal changes |
| **Replatform** | **15-25%** | **20%** | Applications that can benefit from managed services |
| **Repurchase** | **5-15%** | **10%** | Standard business functions with SaaS alternatives |
| **Refactor** | **3-10%** | **5%** | Business-critical applications requiring cloud-native transformation |
| **Retire** | **5-15%** | **10%** | Redundant, unused, or low-value applications |
| **Retain** | **3-10%** | **5%** | Applications to keep on-premises (compliance, recent upgrades) |
| **TOTAL** | **~100%** | **100%** | Ranges allow flexibility based on customer context |

### Distribution Rationale

**Rehost (40-60%, typically 50%)** - Largest percentage because:
- Fastest path to cloud
- Lowest initial risk and cost
- Suitable for most legacy applications
- Can optimize later (Rehost → Replatform → Refactor)
- **Higher end (60%)**: Data center exit, tight timelines, risk-averse organizations
- **Lower end (40%)**: Strong modernization focus, cloud-ready applications

**Replatform (15-25%, typically 20%)** - Significant portion because:
- Good balance of effort vs. benefit
- Leverages AWS managed services (RDS, ELB, etc.)
- Moderate optimization without full re-architecture
- **Higher end (25%)**: Database-heavy portfolio, managed services adoption
- **Lower end (15%)**: Limited modernization budget, legacy applications

**Repurchase (5-15%, typically 10%)** - Moderate percentage because:
- Limited to applications with SaaS alternatives
- Common for CRM, HR, email, collaboration tools
- Reduces technical debt
- **Higher end (15%)**: Many standard business functions, SaaS-first strategy
- **Lower end (5%)**: Custom applications, limited SaaS alternatives

**Refactor (3-10%, typically 5%)** - Smallest percentage because:
- Highest effort and cost
- Reserved for business-critical applications
- Requires significant development resources
- Long-term investment
- **Higher end (10%)**: Digital transformation, microservices strategy, strong dev capability
- **Lower end (3%)**: Limited budget, focus on quick migration

**Retire (5-15%, typically 10%)** - Important percentage because:
- Typical finding in portfolio assessments
- Immediate cost savings
- Reduces complexity
- Common in shadow IT discovery
- **Higher end (15%)**: Shadow IT discovery, M&A consolidation, rationalization project
- **Lower end (5%)**: Well-maintained portfolio, recent cleanup

**Retain (3-10%, typically 5%)** - Small percentage because:
- Temporary decision (revisit in 6-12 months)
- Compliance or regulatory constraints
- Recent significant investments
- Dependencies not yet resolved
- **Higher end (10%)**: Strict compliance, mainframe dependencies, recent upgrades
- **Lower end (3%)**: Cloud-first strategy, minimal constraints

---

## Typical Migration Wave Strategy

### Wave 1: Quick Wins (Months 1-3)
- **Strategy**: Primarily Rehost + Retire
- **Target**: 10-15% of portfolio
- **Focus**: Low-risk, non-critical applications
- **Goal**: Build confidence and experience
- **Expected Distribution**: 60% Rehost, 40% Retire

### Wave 2: Optimization (Months 4-6)
- **Strategy**: Replatform + Repurchase + Rehost
- **Target**: 30-40% of portfolio
- **Focus**: Applications benefiting from managed services
- **Goal**: Demonstrate cost savings and performance improvements
- **Expected Distribution**: 50% Rehost, 30% Replatform, 20% Repurchase

### Wave 3: Transformation (Months 7-12)
- **Strategy**: Refactor + Replatform + Rehost
- **Target**: 20-30% of portfolio
- **Focus**: Business-critical applications
- **Goal**: Maximize cloud-native benefits
- **Expected Distribution**: 60% Rehost, 30% Replatform, 10% Refactor

### Wave 4: Completion (Months 13-18)
- **Strategy**: Mixed (remaining applications) + Retain decisions
- **Target**: Remaining portfolio
- **Focus**: Complex applications and dependencies
- **Goal**: Complete migration, finalize Retain decisions
- **Expected Distribution**: 40% Rehost, 30% Replatform, 20% Refactor, 10% Retain

---

## Special Considerations

### Windows Server Optimization
**If >20 Windows Servers are identified:**

**Mandatory Step**: Optimization and License Assessment (OLA)

**OLA Process**:
1. **License Inventory**
   - Document all Windows Server licenses
   - Identify SQL Server licenses
   - Review Microsoft Enterprise Agreement

2. **Optimization Opportunities**
   - AWS License Included instances
   - Bring Your Own License (BYOL)
   - License Mobility through Software Assurance
   - SQL Server on RDS (license included)

3. **Cost Analysis**
   - Compare license-included vs. BYOL pricing
   - Evaluate Reserved Instances and Savings Plans
   - Consider Windows Server 2008/2012 end-of-support

4. **Recommendations**
   - Rightsizing opportunities
   - Consolidation strategies
   - Modernization to Linux where applicable
   - Use of AWS Systems Manager for patch management

**Typical Savings**: 30-50% through license optimization

---

## Application Portfolio Assessment Integration

**When Application Portfolio Assessment is Available**:
- Use actual application characteristics and dependencies
- Align migration strategy with business priorities
- Consider application interdependencies
- Factor in technical constraints and requirements
- Adjust percentages based on actual portfolio composition

**When Application Portfolio Assessment is NOT Available**:
- **USE THE DEFAULT DISTRIBUTION PERCENTAGES ABOVE** (50% Rehost, 20% Replatform, 10% Repurchase, 5% Refactor, 10% Retire, 5% Retain)
- Apply these percentages to the total application count
- Use this framework as default guidance
- **CLEARLY STATE** these are industry-standard assumptions
- **STRONGLY RECOMMEND** conducting comprehensive portfolio assessment
- Start with low-risk Rehost approach
- Plan for iterative optimization

**Example Calculation** (if portfolio assessment not available):
- Total Applications: 100
- Rehost: 50 applications (50%)
- Replatform: 20 applications (20%)
- Repurchase: 10 applications (10%)
- Refactor: 5 applications (5%)
- Retire: 10 applications (10%)
- Retain: 5 applications (5%)

**Note**: Customer-specific migration strategy should always be preferred when available. This framework and default percentages serve as industry-standard guidance in the absence of detailed portfolio assessment. Actual distribution may vary significantly based on:
- Application portfolio maturity
- Technical debt levels
- Business priorities
- Budget constraints
- Timeline requirements
- Organizational readiness

---

## Success Metrics

### Technical Metrics
- Migration velocity (applications per month)
- Downtime during migration
- Performance improvements
- Availability improvements

### Business Metrics
- Cost savings (% reduction)
- Time to market improvements
- Operational efficiency gains
- Innovation velocity

### Financial Metrics
- TCO reduction
- ROI timeline
- OpEx vs. CapEx shift
- Cost avoidance

---

## References
- AWS Migration Hub
- AWS Application Discovery Service
- AWS Migration Evaluator (formerly TSO Logic)
- AWS Well-Architected Framework


---

## AGENT USAGE GUIDE: How to Apply These Ranges

### Quick Reference for Agents

When application portfolio assessment is **NOT available**, use these ranges:

| Strategy | Range | Typical (Midpoint) | Adjust Higher When | Adjust Lower When |
|----------|-------|-------------------|-------------------|-------------------|
| Rehost | 30-40% | 35% | Data center exit, tight timeline, risk-averse | Strong modernization, cloud-ready apps |
| Replatform | 10-20% | 15% | Database-heavy, managed services focus | Limited budget, legacy apps |
| Repurchase | 10-20% | 15% | SaaS-first strategy, standard functions | Custom apps, limited alternatives |
| Refactor | 5-10% | 7% | Digital transformation, strong dev team | Limited budget, quick migration |
| Retire | 5-10% | 7% | Shadow IT discovery, rationalization | Well-maintained portfolio |
| Retain | 5-10% | 7% | Compliance constraints, mainframe | Cloud-first strategy |

### Step-by-Step Application Process

**Step 1: Start with Typical Values**
```
Rehost:     35%
Replatform: 15%
Repurchase: 15%
Refactor:   7%
Retire:     7%
Retain:     7%
Subtotal:   86%
```

**Step 2: Analyze Infrastructure Data**
Look for context indicators:
- Server count and types (Windows, Linux, databases)
- Application types (web, database, custom, COTS)
- Utilization patterns (high, medium, low)
- Age of infrastructure
- Compliance requirements mentioned
- Timeline constraints

**Step 3: Adjust Within Ranges**
Based on context, adjust percentages within defined ranges.

**Step 4: Scale to 100%**
Proportionally adjust all percentages to sum to 100%.

Example:
```
Initial (86%):  35/15/15/7/7/7
Scaled (100%):  41/17/17/8/8/9 = 100%
```

**Step 5: Validate**
- All percentages within ranges? ✓
- Total equals 100%? ✓
- Adjustments justified? ✓

### Context Indicators from Infrastructure Data

**Indicators for Higher Rehost (→ 40%)**:
- Large number of legacy servers (>100)
- Tight migration timeline mentioned
- Data center exit scenario
- Limited modernization budget
- Many Windows servers
- Risk-averse indicators

**Indicators for Higher Replatform (→ 20%)**:
- Many database servers (SQL, Oracle, MySQL, PostgreSQL)
- Web application servers with load balancers
- Caching infrastructure (Redis, Memcached)
- Message queues (RabbitMQ, ActiveMQ)
- Managed services readiness

**Indicators for Higher Repurchase (→ 20%)**:
- Standard business applications (CRM, HR, Email, ERP)
- Commercial off-the-shelf (COTS) software
- High maintenance costs mentioned
- SaaS alternatives available
- Licensing complexity

**Indicators for Higher Refactor (→ 10%)**:
- Business-critical applications identified
- Microservices architecture mentioned
- Digital transformation initiative
- Strong development team
- Innovation focus
- Scalability requirements

**Indicators for Higher Retire (→ 10%)**:
- Low utilization servers (<20% CPU/Memory)
- Redundant applications
- Shadow IT discovery
- M&A consolidation scenario
- Application rationalization project
- End-of-life systems

**Indicators for Higher Retain (→ 10%)**:
- Compliance requirements (HIPAA, PCI-DSS, etc.)
- Mainframe systems
- Recent infrastructure upgrades (<2 years)
- Regulatory constraints
- Complex dependencies
- Unclear business case

### Example Calculations

**Example 1: Balanced Approach (100 applications)**
```
Context: Standard enterprise portfolio, moderate timeline
Rehost:     35 apps (35%)
Replatform: 20 apps (20%)
Repurchase: 15 apps (15%)
Refactor:   10 apps (10%)
Retire:     10 apps (10%)
Retain:     10 apps (10%)
TOTAL:      100 apps (100%)
```

**Example 2: Quick Migration (Data Center Exit)**
```
Context: 6-month data center exit, 150 applications
Rehost:     60 apps (40%)
Replatform: 23 apps (15%)
Repurchase: 23 apps (15%)
Refactor:    8 apps (5%)
Retire:     23 apps (15%)
Retain:     13 apps (9%)
TOTAL:      150 apps (100%)
Rationale: Higher Rehost (40%) due to tight timeline
```

**Example 3: Modernization Focus**
```
Context: Digital transformation, 80 applications, 18-month timeline
Rehost:     24 apps (30%)
Replatform: 16 apps (20%)
Repurchase: 16 apps (20%)
Refactor:    8 apps (10%)
Retire:      8 apps (10%)
Retain:      8 apps (10%)
TOTAL:      80 apps (100%)
Rationale: Lower Rehost (30%), Higher Refactor (10%) for modernization
```

### Mandatory Disclaimers

When using these ranges, **ALWAYS include**:

1. **Data Availability Statement**:
   ```
   ⚠️ IMPORTANT: Application portfolio assessment is NOT available.
   The following recommendations are based on industry-standard ranges
   and available infrastructure data.
   ```

2. **Assumption Statement**:
   ```
   The distribution percentages (Rehost: X%, Replatform: Y%, etc.) are
   derived from industry standards and adjusted based on infrastructure
   analysis. Actual distribution may vary significantly.
   ```

3. **Recommendation Statement**:
   ```
   🔍 STRONG RECOMMENDATION: Conduct a comprehensive application portfolio
   assessment using AWS Application Discovery Service or AWS Migration
   Evaluator for accurate, customer-specific migration strategy.
   ```

4. **Adjustment Rationale**:
   ```
   Adjustments made:
   - Rehost increased to 40% due to [reason]
   - Retire increased to 10% due to [reason]
   - etc.
   ```

### Output Format Template

```markdown
## Migration Strategy Recommendation

### Data Source Analysis
- ✅ IT Infrastructure Inventory: Available
- ✅ RVTool VMware Assessment: Available
- ✅ ATX VMware Assessment: Available
- ✅ MRA Organizational Readiness: Available
- ❌ Application Portfolio Assessment: NOT Available

⚠️ **IMPORTANT**: Recommendations based on industry-standard ranges
(30-40/10-20/10-20/5-10/5-10/5-10) and available infrastructure data.

🔍 **STRONG RECOMMENDATION**: Conduct comprehensive application portfolio
assessment for accurate, customer-specific strategy.

### Recommended Distribution

Based on infrastructure analysis: [describe context]

| Strategy | Applications | Percentage | Rationale |
|----------|-------------|------------|-----------|
| Rehost | X | X% | [Reason for this percentage] |
| Replatform | X | X% | [Reason for this percentage] |
| Repurchase | X | X% | [Reason for this percentage] |
| Refactor | X | X% | [Reason for this percentage] |
| Retire | X | X% | [Reason for this percentage] |
| Retain | X | X% | [Reason for this percentage] |
| **TOTAL** | **X** | **100%** | |

### Adjustments Made
- [List any adjustments from typical values and why]

### Migration Wave Plan
[4-wave breakdown using the distribution above]
```

### Validation Checklist

Before finalizing recommendations, verify:

- [ ] All percentages are within defined ranges (30-40/10-20/10-20/5-10/5-10/5-10)
- [ ] Total sums to 100% (±0.5%)
- [ ] Adjustments are justified by infrastructure data
- [ ] Disclaimers are included
- [ ] Portfolio assessment is recommended
- [ ] Typical values used as baseline
- [ ] Context-based adjustments documented
- [ ] Rationale provided for each strategy
- [ ] Windows Server OLA flagged if >20 servers
- [ ] Customer-specific factors noted

---

## Summary for Agents

**Key Points**:
1. Use ranges (30-40/10-20/10-20/5-10/5-10/5-10) when portfolio assessment unavailable
2. Start with typical/midpoint values (35/15/15/7/7/7)
3. Analyze infrastructure data for context indicators
4. Adjust within ranges based on context
5. Scale to 100%
6. Always include disclaimers
7. Strongly recommend portfolio assessment
8. Document all adjustments and rationale

**Remember**: These ranges are guidance, not rigid rules. Customer-specific portfolio assessment is always preferred for accurate migration strategy.
