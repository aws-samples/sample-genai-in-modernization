# AWS Migration Business Case Generator - Web UI

A modern React-based user interface for generating AWS migration business cases using AI-powered multi-agent analysis.

## Features

### Core Features
✅ **5-Step Wizard Interface** - Guided workflow from project info to results  
✅ **AWS Cloudscape Design System** - Professional AWS look and feel  
✅ **File Upload Management** - Upload and manage assessment files  
✅ **Agent Configuration** - Select which agents to run  
✅ **Real-time Progress** - Monitor generation progress  
✅ **Results Preview** - View generated business case with markdown rendering  
✅ **Export Options** - Export as PDF or Markdown  

### AI-Powered Features
✅ **AI Description Enhancement** - Uses AWS Bedrock to enhance project descriptions  
✅ **Multi-Agent Orchestration** - Coordinates 9 AI agents for comprehensive analysis  

### Optional Storage Features
✅ **DynamoDB Persistence** - Save and load business cases  
✅ **S3 File Storage** - Automatic file backup and restore  
✅ **Version Tracking** - Track when cases were last updated  

---

## Architecture

```
ui/
├── src/
│   ├── components/          # React components
│   │   ├── ProjectInfoStep.js       # Step 1: Project information
│   │   ├── FileUploadStep.js        # Step 2: File uploads
│   │   ├── AgentConfigStep.js       # Step 3: Agent configuration
│   │   ├── ReviewStep.js            # Step 4: Review and generate
│   │   └── ResultsStep.js           # Step 5: View results
│   ├── services/
│   │   └── api.js           # API service layer
│   ├── styles/
│   │   └── App.css          # Custom styles
│   ├── App.js               # Main application
│   └── index.js             # Entry point
├── backend/
│   ├── app.py               # Flask API server
│   └── requirements.txt     # Python dependencies
├── public/
│   └── index.html           # HTML template
└── package.json             # Node dependencies
```

---

## Prerequisites

### Frontend
- Node.js 16+ and npm
- React 18+

### Backend
- Python 3.x
- Flask
- AWS credentials configured

---

## Installation

### 1. Install Frontend Dependencies

```bash
cd ui
npm install
```

### 2. Install Backend Dependencies

```bash
# Install UI backend dependencies
cd ui/backend
pip install -r requirements.txt

# Install agent dependencies (required for business case generation)
cd ../../agents
pip install -r requirements.txt
```

**Note:** The backend needs both sets of dependencies:
- **UI Backend** (`ui/backend/requirements.txt`): Flask, Flask-CORS, boto3 for API
- **Agents** (`agents/requirements.txt`): strands-agents, pandas, openpyxl, etc. for business case generation

---

## Running the Application

### Option 1: Development Mode (Recommended)

**Terminal 1 - Start Backend API:**
```bash
cd ui/backend
python app.py
```
Backend will run on `http://localhost:5000`

**Terminal 2 - Start Frontend:**
```bash
cd ui
npm start
```
Frontend will run on `http://localhost:3000`

### Option 2: Production Build

```bash
cd ui
npm run build
```

Serve the `build/` folder with your preferred web server.

---

## Usage Guide

### Step 1: Project Information
1. Enter project name (required)
2. Enter customer name (required)
3. Select target AWS region
4. Enter or generate project description using AI

### Step 2: Upload Assessment Files

Upload the following files:

| File | Description | Required |
|------|-------------|----------|
| **IT Infrastructure Inventory** | Excel file with IT asset inventory | ✅ Yes |
| **RVTool VMware Assessment** | CSV export from RVTool | ✅ Yes |
| **ATX Analysis Data (Excel)** | AWS Transform for VMware - environment data | ✅ Yes |
| **ATX Technical Report (PDF)** | AWS Transform for VMware - technical report | ✅ Yes |
| **ATX Business Case (PowerPoint)** | AWS Transform for VMware - presentation | ✅ Yes |
| **MRA Document** | Migration Readiness Assessment | ✅ Yes |
| **Application Portfolio** | Detailed application portfolio | ⚪ Optional |

### Step 3: Configure Agents

Choose to run:
- **All Agents** (Recommended) - Complete analysis with all 9 agents
- **Custom Selection** - Select specific agents to run

**Agents Available:**

**Phase 1: Data Analysis** (~2-3 min each)
- IT Inventory Analysis
- RVTool VMware Analysis
- ATX VMware Analysis
- MRA Organizational Readiness

**Phase 2: Synthesis** (~1-2 min each)
- Current State Synthesis
- AWS Cost Analysis
- Migration Strategy (6Rs)

**Phase 3: Planning** (~1-2 min)
- Migration Plan (MAP)

**Phase 4: Final** (~1 min)
- Business Case Generation

### Step 4: Review & Generate
1. Review your configuration
2. Click "Generate Business Case"
3. Monitor progress (6-10 minutes)

### Step 5: Results
1. View generated business case
2. Switch between Preview and Markdown views
3. Export as PDF or Markdown
4. Copy to clipboard
5. (Optional) Save to DynamoDB for later retrieval

### Optional: Persistent Storage (DynamoDB + S3)

Enable optional persistent storage to save and manage business cases with file backup:

#### Quick Setup (Recommended)

```bash
cd ui
./setup-storage.sh
```

This interactive script sets up both DynamoDB and S3 (optional).

#### Manual Setup

**1. DynamoDB (Business Case Metadata)**
```bash
cd ui/backend
python setup_dynamodb.py
```
See [DYNAMODB_SETUP.md](./DYNAMODB_SETUP.md) for details.

**2. S3 (File Storage - Optional but Recommended)**
```bash
cd ui/backend
export S3_BUCKET_NAME=your-bucket-name
python setup_s3.py
```
See [S3_STORAGE_SETUP.md](./S3_STORAGE_SETUP.md) for details.

#### Features

**With DynamoDB Only:**
- ✅ Save/load business cases
- ✅ Track last updated timestamp
- ✅ Edit and regenerate saved cases
- ⚠️ Files must be re-uploaded when loading

**With DynamoDB + S3:**
- ✅ All DynamoDB features
- ✅ **Files automatically backed up to S3**
- ✅ **Files automatically restored when loading**
- ✅ File versioning and history
- ✅ Encrypted storage

#### Usage

1. **Enable in UI**:
   - Toggle "DynamoDB Persistence" in header
   - See "Enhanced Storage: DynamoDB + S3 enabled" if S3 is configured

2. **Save Business Cases**:
   - Generate business case
   - Click "Save to Database" in Results step
   - Files automatically uploaded to S3 (if enabled)

3. **Load Saved Cases**:
   - Click "Load Saved Cases" in top navigation
   - Select a case
   - Files automatically restored from S3 (if enabled)
   - Edit and regenerate as needed

---

## File Upload Details

### IT Infrastructure Inventory
**Format:** Excel (.xlsx, .xls)  
**Content:** Servers, storage, databases, applications, network components  
**Details:** CPU, memory, storage capacity, OS versions, utilization metrics  
**Example:** Test-Data-Set-Demo-Excel-V2.xlsx

### RVTool VMware Assessment
**Format:** CSV  
**Content:** VMware environment data from RVTool export  
**Details:** vCPUs, memory, storage, VM configurations, performance metrics  
**Example:** rvtool.csv

### ATX Analysis Data
**Format:** Excel (.xlsx, .xls)  
**Content:** AWS Transform for VMware environment data  
**Details:** VMware infrastructure, cost analysis, workload categorization  
**Example:** analysis.xlsx

### ATX Technical Report
**Format:** PDF  
**Content:** Detailed technical assessment report  
**Details:** Infrastructure analysis, migration recommendations  
**Example:** report.pdf

### ATX Business Case
**Format:** PowerPoint (.pptx, .ppt)  
**Content:** Executive business case presentation  
**Details:** High-level findings and recommendations  
**Example:** business_case.pptx

### Migration Readiness Assessment
**Format:** Markdown (.md) or Word (.docx, .doc)  
**Content:** Organizational readiness evaluation  
**Details:** Business, people, process, technology, security, operations, financial readiness  
**Example:** aws-customer-migration-readiness-assessment.md

### Application Portfolio (Optional)
**Format:** CSV or Excel  
**Content:** Detailed application portfolio  
**Details:** Application characteristics, dependencies, business criticality  
**Example:** application-portfolio.csv

---

## API Endpoints

### POST /api/generate
Generate business case from uploaded files

**Request:**
- Content-Type: multipart/form-data
- Body: Files + projectInfo + selectedAgents

**Response:**
```json
{
  "success": true,
  "content": "# Business Case...",
  "projectInfo": {...},
  "agentsExecuted": 9,
  "executionTime": "8m 32s",
  "tokenUsage": "125,432 tokens"
}
```

### GET /api/health
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "message": "API is running"
}
```

### POST /api/enhance-description
Enhance project description with AI

**Request:**
```json
{
  "projectName": "Migration Project",
  "customerName": "Acme Corp",
  "currentDescription": "Existing text...",
  "awsRegion": "us-east-1"
}
```

**Response:**
```json
{
  "success": true,
  "enhancedDescription": "Enhanced description..."
}
```

### DynamoDB API Endpoints (Optional)

#### GET /api/dynamodb/status
Check if DynamoDB is enabled

**Response:**
```json
{
  "enabled": true,
  "tableName": "aws-migration-business-cases",
  "region": "us-east-1"
}
```

#### POST /api/dynamodb/save
Save business case to DynamoDB

**Request:**
```json
{
  "caseId": "case-20241124-143022",
  "projectInfo": {...},
  "businessCaseContent": "...",
  "selectedAgents": {...}
}
```

**Response:**
```json
{
  "success": true,
  "caseId": "case-20241124-143022",
  "lastUpdated": "2024-11-24T14:30:22.000Z"
}
```

#### GET /api/dynamodb/list
List all saved business cases

**Response:**
```json
{
  "success": true,
  "cases": [
    {
      "caseId": "case-20241124-143022",
      "projectInfo": {...},
      "createdAt": "2024-11-24T14:30:22.000Z",
      "lastUpdated": "2024-11-24T15:45:10.000Z"
    }
  ]
}
```

#### GET /api/dynamodb/load/:caseId
Load specific business case

**Response:**
```json
{
  "success": true,
  "case": {
    "caseId": "case-20241124-143022",
    "projectInfo": {...},
    "businessCaseContent": "...",
    "lastUpdated": "2024-11-24T15:45:10.000Z"
  }
}
```

#### DELETE /api/dynamodb/delete/:caseId
Delete business case (and associated S3 files if enabled)

**Response:**
```json
{
  "success": true,
  "message": "Business case deleted successfully"
}
```

#### GET /api/storage/status
Check storage configuration status

**Response:**
```json
{
  "dynamodb": {
    "enabled": true,
    "tableName": "aws-migration-business-cases",
    "region": "us-east-1"
  },
  "s3": {
    "enabled": true,
    "bucketName": "aws-migration-business-cases-files",
    "region": "us-east-1"
  }
}
```

---

## Environment Variables

Create a `.env` file in the `ui/` directory:

```env
REACT_APP_API_URL=http://localhost:5000/api
```

For DynamoDB and S3 (optional):
```bash
export DYNAMODB_TABLE_NAME=aws-migration-business-cases
export S3_BUCKET_NAME=your-bucket-name
export AWS_REGION=us-east-1
```

---

## Troubleshooting

### Frontend Issues

**Port 3000 already in use:**
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

**Dependencies not installing:**
```bash
rm -rf node_modules package-lock.json
npm install
```

### Backend Issues

**Port 5000 already in use:**
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9
```

**AWS credentials error:**
```bash
# Configure AWS credentials
aws configure
# OR
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

**Module not found:**
```bash
pip install -r backend/requirements.txt
```

### Generation Issues

**Timeout error:**
- Increase timeout in `backend/app.py` (default: 600 seconds)
- Check AWS Bedrock access and quotas

**File upload error:**
- Check file size (max 100MB)
- Verify file format matches requirements
- Ensure all required files are uploaded

---

## Customization

### Change AWS Region Options
Edit `src/components/ProjectInfoStep.js`:
```javascript
const awsRegions = [
  { label: 'Your Region', value: 'your-region' },
  // Add more regions
];
```

### Modify Agent Configuration
Edit `src/components/AgentConfigStep.js`:
```javascript
const agentConfigs = [
  // Add or modify agent configurations
];
```

### Update Styling
Edit `src/styles/App.css` for custom styles

### Change API URL
Update `.env` file:
```env
REACT_APP_API_URL=https://your-api-url.com/api
```

---

## Production Deployment

### Build Frontend
```bash
cd ui
npm run build
```

### Deploy Options

**Option 1: AWS Amplify**
```bash
amplify init
amplify add hosting
amplify publish
```

**Option 2: AWS S3 + CloudFront**
```bash
aws s3 sync build/ s3://your-bucket-name
```

**Option 3: Docker**
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### Deploy Backend

**Option 1: AWS Lambda + API Gateway**
- Use Zappa or Serverless Framework

**Option 2: AWS ECS/Fargate**
- Containerize Flask app

**Option 3: AWS EC2**
- Deploy with Gunicorn + Nginx

---

## Security Considerations

1. **File Upload Validation**
   - File type checking
   - File size limits (100MB)
   - Virus scanning (recommended)

2. **API Security**
   - Add authentication (JWT, OAuth)
   - Rate limiting
   - CORS configuration

3. **AWS Credentials**
   - Never expose in frontend
   - Use IAM roles in production
   - Rotate credentials regularly

4. **Data Privacy**
   - Encrypt files at rest
   - Use HTTPS in production
   - Implement data retention policies

---

## Performance Optimization

1. **Frontend**
   - Code splitting
   - Lazy loading components
   - Optimize bundle size

2. **Backend**
   - Async job processing
   - Caching results
   - Load balancing

3. **File Handling**
   - Stream large files
   - Compress uploads
   - Clean up temp files

---

## Support

For issues or questions:
1. Check troubleshooting section
2. Review API logs in backend console
3. Check browser console for frontend errors
4. Verify AWS credentials and Bedrock access

---

## License

This UI is part of the AWS Migration Business Case Generator project.

---

**Ready to generate professional AWS migration business cases with a beautiful UI!** 🚀
