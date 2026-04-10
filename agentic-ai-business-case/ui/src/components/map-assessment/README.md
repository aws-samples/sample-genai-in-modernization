# MAP Assessment Components

This directory contains React components for the MAP (Migration Acceleration Program) assessment tools integrated into the AWS Migration Business Case Generator.

## 📁 Components

### 1. ModernizationOpportunity.jsx
**Purpose**: Identify AWS modernization opportunities from IT inventory data

**Features**:
- Upload IT inventory CSV files
- Upload architecture diagrams (optional)
- Define modernization scope
- Generate inventory analysis
- Analyze architecture from images
- Provide modernization pathway recommendations

**API Endpoints**:
- `POST /api/map/modernization/analyze-inventory`
- `POST /api/map/modernization/analyze-architecture`
- `POST /api/map/modernization/recommend-pathways`

**Props**: None (standalone component)

**State**:
- `inventoryFile`: Uploaded CSV file
- `architectureFile`: Uploaded image file
- `scope`: Modernization scope text
- `loading`: Loading state
- `error`: Error message
- `inventoryAnalysis`: Analysis results
- `architectureAnalysis`: Architecture analysis
- `recommendations`: Modernization recommendations

---

### 2. MigrationStrategy.jsx
**Purpose**: Generate migration strategy from AWS Calculator data

**Features**:
- Upload AWS Calculator CSV export
- Enter optional migration scope
- Generate migration patterns
- Create wave planning
- Predict MAP milestones

**API Endpoints**:
- `POST /api/map/migration-strategy/generate`

**Props**: None (standalone component)

**State**:
- `calculatorFile`: AWS Calculator CSV
- `scope`: Migration scope text
- `loading`: Loading state
- `error`: Error message
- `strategy`: Generated strategy
- `recordsProcessed`: Number of records

---

### 3. ResourcePlanning.jsx
**Purpose**: Generate team structure and resource allocation plans

**Features**:
- Upload resource profile CSV
- Enter migration strategy context
- Enter wave planning details
- Generate resource allocation plan
- Calculate resource costs

**API Endpoints**:
- `POST /api/map/resource-planning/generate`

**Props**: None (standalone component)

**State**:
- `resourceFile`: Resource profile CSV
- `migrationStrategy`: Strategy context
- `wavePlanning`: Wave planning details
- `loading`: Loading state
- `error`: Error message
- `resourcePlan`: Generated plan

---

### 4. LearningPathway.jsx
**Purpose**: Create personalized AWS training pathways

**Features**:
- Upload training catalog CSV
- Specify target role
- Select experience level
- Enter training duration
- Generate customized learning pathway

**API Endpoints**:
- `POST /api/map/learning-pathway/generate`

**Props**: None (standalone component)

**State**:
- `trainingFile`: Training data CSV
- `targetRole`: Target role string
- `experienceLevel`: Selected level
- `duration`: Training duration
- `loading`: Loading state
- `error`: Error message
- `learningPathway`: Generated pathway

---

### 5. BusinessCaseReview.jsx
**Purpose**: Validate and analyze business case documents

**Features**:
- Upload business case PDF
- Multi-page document processing
- TCO analysis validation
- Comprehensive recommendations

**API Endpoints**:
- `POST /api/map/business-validation/validate`

**Props**: None (standalone component)

**State**:
- `pdfFile`: Business case PDF
- `loading`: Loading state
- `error`: Error message
- `validation`: Validation results
- `pagesProcessed`: Number of pages

---

### 6. ArchitectureDiagram.jsx
**Purpose**: Generate AWS architecture diagrams in Draw.io format

**Features**:
- Enter architecture description
- Generate Draw.io XML
- Download XML file
- Open directly in Draw.io
- View XML source

**API Endpoints**:
- `POST /api/map/architecture-diagram/generate`

**Props**: None (standalone component)

**State**:
- `description`: Architecture description
- `loading`: Loading state
- `error`: Error message
- `diagramXml`: Generated XML

---

### 7. ChatAssistant.jsx
**Purpose**: Interactive Q&A about migration and modernization

**Features**:
- Context-aware conversations
- Chat history maintained
- Markdown rendering in messages
- Clear chat functionality
- Timestamps on messages

**API Endpoints**:
- `POST /api/map/chat/message`

**Props**: None (standalone component)

**State**:
- `messages`: Chat message array
- `inputMessage`: Current input
- `loading`: Loading state
- `error`: Error message

---

## 🎨 Design Patterns

### Common Patterns Across Components

#### 1. File Upload Pattern
```jsx
<FileUpload
  value={file}
  onChange={({ detail }) => setFile(detail.value)}
  accept=".csv,.xlsx,.pdf"
  constraintText="File type description"
/>
```

#### 2. Loading State Pattern
```jsx
{loading && (
  <ProgressBar
    status="in-progress"
    label="Processing..."
  />
)}
```

#### 3. Error Handling Pattern
```jsx
{error && (
  <Alert
    type="error"
    dismissible
    onDismiss={() => setError(null)}
  >
    {error}
  </Alert>
)}
```

#### 4. Results Display Pattern
```jsx
<ExpandableSection
  headerText="Results"
  variant="container"
  defaultExpanded
>
  <div className="markdown-content">
    <ReactMarkdown remarkPlugins={[remarkGfm]}>
      {results}
    </ReactMarkdown>
  </div>
  <Button onClick={() => downloadMarkdown(results, 'filename.md')}>
    Download Report
  </Button>
</ExpandableSection>
```

#### 5. API Call Pattern
```jsx
const handleGenerate = async () => {
  setLoading(true);
  setError(null);
  
  try {
    const formData = new FormData();
    formData.append('file', file[0]);
    
    const response = await fetch(getApiUrl('/map/endpoint'), {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    
    if (!result.success) {
      throw new Error(result.message);
    }
    
    setResults(result.data);
  } catch (err) {
    setError(err.message || 'Operation failed');
  } finally {
    setLoading(false);
  }
};
```

---

## 🔧 Utilities

### Download Markdown Function
```jsx
const downloadMarkdown = (content, filename) => {
  const blob = new Blob([content], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};
```

### API URL Helper
```jsx
import { getApiUrl } from '../../utils/apiConfig.js';

// Usage
const url = getApiUrl('/map/endpoint');
```

---

## 📦 Dependencies

### Required Packages
```json
{
  "@cloudscape-design/components": "^3.0.0",
  "react": "^18.2.0",
  "react-markdown": "^9.0.0",
  "remark-gfm": "^4.0.1"
}
```

### Cloudscape Components Used
- Container
- Header
- SpaceBetween
- FormField
- FileUpload
- Textarea
- Input
- Select
- Button
- Alert
- ExpandableSection
- ProgressBar
- Box
- ColumnLayout
- Tabs
- Spinner
- CodeView

---

## 🎨 Styling

### CSS Classes
Components use these CSS classes from `MapAssessment.css`:

- `.markdown-content` - Markdown rendering styles
- `.chat-message` - Chat message styling
- `.chat-message-user` - User message styling
- `.chat-message-assistant` - Assistant message styling
- `.map-header-gradient` - Gradient headers
- `.map-info-card` - Info card styling
- `.map-results-section` - Results section styling

---

## 🧪 Testing

### Component Testing Checklist
For each component:
- [ ] Renders without errors
- [ ] File upload works
- [ ] Validation shows errors
- [ ] Loading state displays
- [ ] API call succeeds
- [ ] Results display correctly
- [ ] Markdown renders properly
- [ ] Download button works
- [ ] Error handling works
- [ ] Responsive on mobile

### Example Test Flow
1. Navigate to component
2. Upload valid file
3. Fill required fields
4. Click generate button
5. Verify loading indicator
6. Verify results display
7. Test download button
8. Test error scenarios

---

## 🐛 Common Issues

### Issue: "Module not found"
**Solution**: Ensure all imports are correct and files exist

### Issue: "API endpoint not found"
**Solution**: Verify backend is running and routes are registered

### Issue: "File upload fails"
**Solution**: Check file size and type constraints

### Issue: "Markdown not rendering"
**Solution**: Verify `react-markdown` and `remark-gfm` are installed

### Issue: "Styling not applied"
**Solution**: Ensure `MapAssessment.css` is imported in `App.jsx`

---

## 📚 Resources

### Documentation
- [Cloudscape Design System](https://cloudscape.design/)
- [React Markdown](https://github.com/remarkjs/react-markdown)
- [Remark GFM](https://github.com/remarkjs/remark-gfm)

### Related Files
- Backend: `ui/backend/map_routes.py`
- Styling: `ui/src/styles/MapAssessment.css`
- Main App: `ui/src/App.jsx`
- Prompt Library: `prompt_library/`

---

## 🚀 Adding New Components

### Steps to Add a New MAP Tool

1. **Create Component File**
```jsx
// NewTool.jsx
import React, { useState } from 'react';
import { Container, Header, SpaceBetween } from '@cloudscape-design/components';

function NewTool() {
  // Component logic
  return (
    <SpaceBetween size="l">
      <Container header={<Header variant="h1">New Tool</Header>}>
        {/* Component content */}
      </Container>
    </SpaceBetween>
  );
}

export default NewTool;
```

2. **Add Backend Endpoint**
```python
# In map_routes.py
@map_bp.route('/new-tool/endpoint', methods=['POST'])
def new_tool_endpoint():
    # Endpoint logic
    return jsonify({'success': True, 'data': result})
```

3. **Update App.jsx**
```jsx
// Import component
import NewTool from './components/map-assessment/NewTool.jsx';

// Add to navigation
{
  type: 'link',
  text: 'New Tool',
  href: '#/new-tool'
}

// Add to renderContent()
case 'new-tool':
  return <NewTool />;
```

4. **Test and Deploy**

---

**Last Updated**: February 4, 2026
**Maintainer**: Development Team
**Status**: Active
