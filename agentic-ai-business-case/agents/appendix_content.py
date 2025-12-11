"""
Static appendix content for AWS business case documents
Contains reference information about AWS partner programs and resources
"""

AWS_PARTNER_PROGRAMS_APPENDIX = """
## Appendix: AWS Partner Programs for Migration and Modernization

This appendix provides information about AWS partner programs that can support your migration journey.

### Core Migration Programs

#### 1. MAP (Migration Acceleration Program)
Comprehensive cloud migration program with three phases: Assess, Mobilize, and Migrate & Modernize. Provides funding to offset initial migration costs and accelerate cloud adoption.

**Learn more:** [AWS Migration Acceleration Program](https://aws.amazon.com/migration-acceleration-program/)

#### 2. OLA (Optimization and Licensing Assessment)
Helps assess on-premises environments and provides data-driven recommendations for migration optimization. Analyzes current licensing and resource utilization to optimize cloud costs.

**Learn more:** [AWS Optimization and Licensing Assessment](https://aws.amazon.com/optimization-and-licensing-assessment/)

#### 3. ISV Workload Migration Program (WMP)
Specifically designed for Independent Software Vendor workload migrations. Supports partners migrating ISV applications to AWS across all major geographies.

**Learn more:** [AWS Partner Funding Programs](https://aws.amazon.com/partners/funding/)

#### 4. VMware Migration Programs
- **AWS Transform for VMware:** Streamlined service for migrating VMware workloads to AWS
- **Amazon Elastic VMware Service (Amazon EVS):** Fastest path to migrate and operate VMware workloads on AWS
- **VMware Migration Accelerator (VMA):** Provides credits when migrating VMware workloads to Amazon EC2

**Learn more:** [VMware on AWS Migration](https://aws.amazon.com/vmware/)

#### 5. POC (Proof of Concept) Program
Supports proof of concept projects that can include migration assessment phases. Available for smaller projects under $10,000 with Partner Referral ownership.

**Learn more:** [AWS Partner Programs](https://aws.amazon.com/partners/programs/)

### Additional Resources

#### AWS Application Migration Service (MGN)
Simplifies and expedites migration to AWS by automatically converting source servers to run natively on AWS.

**Learn more:** [AWS Application Migration Service](https://aws.amazon.com/application-migration-service/)

#### AWS Database Migration Service (DMS)
Helps migrate databases to AWS quickly and securely with minimal downtime.

**Learn more:** [AWS Database Migration Service](https://aws.amazon.com/dms/)

#### AWS Migration Evaluator
Provides a clear baseline of your current on-premises footprint and projects costs for running applications in AWS.

**Learn more:** [AWS Migration Evaluator](https://aws.amazon.com/migration-evaluator/)

---

*For the most current information about AWS partner programs and eligibility requirements, please consult with your AWS account team or visit the AWS Partner Network portal.*
"""

def get_appendix():
    """Return the AWS partner programs appendix content"""
    return AWS_PARTNER_PROGRAMS_APPENDIX
