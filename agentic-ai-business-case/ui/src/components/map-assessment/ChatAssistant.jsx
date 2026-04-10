import React, { useState, useRef, useEffect } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  Input,
  Button,
  Alert,
  Box,
  Spinner,
  Select,
  Textarea,
  Modal
} from '@cloudscape-design/components';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getApiUrl } from '../../utils/apiConfig.js';
import { useMapAssessment } from '../../contexts/MapAssessmentContext.jsx';

function ChatAssistant() {
  const { getContextData } = useMapAssessment();
  
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedContext, setSelectedContext] = useState({ 
    label: 'General AWS Migration', 
    value: 'general' 
  });
  const [contextData, setContextData] = useState('');
  const [showContextModal, setShowContextModal] = useState(false);
  const messagesEndRef = useRef(null);

  const contextOptions = [
    { label: 'General AWS Migration', value: 'general' },
    { label: 'Modernization Opportunity', value: 'modernization' },
    { label: 'Migration Strategy', value: 'migration-strategy' },
    { label: 'Resource Planning', value: 'resource-planning' },
    { label: 'Learning Pathway', value: 'learning-pathway' },
    { label: 'Business Case Review', value: 'business-case' },
    { label: 'Architecture Diagram', value: 'architecture' },
    { label: 'Service Analysis', value: 'service-analysis' },
    { label: 'OLA Analysis', value: 'ola-analysis' },
    { label: 'AWS Knowledge Base', value: 'knowledge-base' }
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-load context when selected
  useEffect(() => {
    if (selectedContext.value !== 'general' && selectedContext.value !== 'knowledge-base') {
      const data = getContextData(selectedContext.value);
      if (data) {
        // Format the data for display
        const formattedData = Object.values(data)
          .filter(v => v)
          .join('\n\n---\n\n');
        setContextData(formattedData);
      } else {
        setContextData('');
      }
    } else {
      setContextData('');
    }
  }, [selectedContext, getContextData]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(getApiUrl('/map/chat/message'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: inputMessage,
          history: messages,
          context: {
            type: selectedContext.value,
            data: contextData
          }
        })
      });

      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.message);
      }

      const assistantMessage = {
        role: 'assistant',
        content: result.response,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      setError(err.message || 'Failed to send message');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setError(null);
  };

  const getContextDescription = () => {
    switch (selectedContext.value) {
      case 'general':
        return 'General AWS migration and modernization questions';
      case 'modernization':
        return 'Ask about modernization opportunities from your inventory analysis';
      case 'migration-strategy':
        return 'Discuss migration strategies and the 6Rs framework';
      case 'resource-planning':
        return 'Questions about resource planning and team structure';
      case 'learning-pathway':
        return 'Explore learning paths and skill development';
      case 'business-case':
        return 'Review and discuss business case details';
      case 'architecture':
        return 'Questions about AWS architecture and design patterns';
      case 'service-analysis':
        return 'Analyze infrastructure completeness and identify missing services';
      case 'ola-analysis':
        return 'Discuss licensing optimization and OLA recommendations';
      case 'knowledge-base':
        return 'Search AWS documentation, best practices, and knowledge base';
      default:
        return '';
    }
  };

  return (
    <SpaceBetween size="l">
      <Container
        header={
          <Header
            variant="h1"
            description="Context-Aware Conversations with Generated Outputs"
            actions={
              <Button onClick={clearChat} disabled={messages.length === 0}>
                Clear Chat
              </Button>
            }
          >
            Interactive Analysis Chat
          </Header>
        }
      >
        <SpaceBetween size="m">
          <Alert type="info">
            Select a context to focus your conversation, or choose AWS Knowledge Base to search 
            AWS documentation and best practices.
          </Alert>

          {error && (
            <Alert
              type="error"
              dismissible
              onDismiss={() => setError(null)}
            >
              {error}
            </Alert>
          )}

          {/* Context Selection */}
          <SpaceBetween size="s">
            <Box variant="h3">Conversation Context</Box>
            <SpaceBetween direction="horizontal" size="xs">
              <div style={{ flex: 1 }}>
                <Select
                  selectedOption={selectedContext}
                  onChange={({ detail }) => setSelectedContext(detail.selectedOption)}
                  options={contextOptions}
                  placeholder="Select conversation context"
                />
              </div>
              <Button 
                iconName="expand" 
                onClick={() => setShowContextModal(true)}
                disabled={!contextData || selectedContext.value === 'general' || selectedContext.value === 'knowledge-base'}
              >
                View Context
              </Button>
            </SpaceBetween>
            <Box variant="small" color="text-body-secondary">
              {getContextDescription()}
            </Box>
            
            {/* Show context data status */}
            {selectedContext.value !== 'general' && selectedContext.value !== 'knowledge-base' && contextData && (
              <Alert type="success">
                Context loaded from {selectedContext.label} ({contextData.length} characters)
              </Alert>
            )}
            
            {/* Show message if no context available */}
            {selectedContext.value !== 'general' && selectedContext.value !== 'knowledge-base' && !contextData && (
              <Alert type="info">
                No saved output found for {selectedContext.label}. Generate output in that use case first, or paste context manually below.
              </Alert>
            )}
            
            {/* Optional context data input for specific use cases */}
            {selectedContext.value !== 'general' && selectedContext.value !== 'knowledge-base' && (
              <Textarea
                value={contextData}
                onChange={({ detail }) => setContextData(detail.value)}
                placeholder={`Paste output from ${selectedContext.label} here (optional) to provide specific context for your questions...`}
                rows={4}
              />
            )}
          </SpaceBetween>

          <div
            style={{
              minHeight: '400px',
              maxHeight: '600px',
              overflowY: 'auto',
              backgroundColor: '#f9f9f9',
              borderRadius: '8px',
              border: '1px solid #e0e0e0',
              padding: '16px'
            }}
          >
            {messages.length === 0 ? (
              <Box textAlign="center" padding="xxl" color="text-body-secondary">
                <Box variant="p" fontSize="heading-m">
                  👋 Welcome to the MAP Assessment Chat
                </Box>
                <Box variant="p" padding={{ top: 's' }}>
                  {selectedContext.value === 'knowledge-base' ? (
                    <>
                      Search AWS documentation, best practices, and knowledge base.
                      <br />
                      Ask questions about AWS services, migration patterns, or best practices.
                    </>
                  ) : (
                    <>
                      Start a conversation by asking questions about AWS migration, 
                      modernization strategies, or any analysis you've generated.
                      <br />
                      Select a context above to focus your conversation.
                    </>
                  )}
                </Box>
              </Box>
            ) : (
              <SpaceBetween size="m">
                {messages.map((message, index) => (
                  <div
                    key={index}
                    style={{
                      backgroundColor: message.role === 'user' ? '#e8f4f8' : 'white',
                      borderRadius: '8px',
                      border: '1px solid #e0e0e0',
                      marginLeft: message.role === 'user' ? '20%' : '0',
                      marginRight: message.role === 'assistant' ? '20%' : '0',
                      padding: '12px'
                    }}
                  >
                    <SpaceBetween size="xs">
                      <Box variant="strong" color={message.role === 'user' ? 'text-status-info' : 'text-status-success'}>
                        {message.role === 'user' ? '👤 You' : '🤖 Assistant'}
                      </Box>
                      <div className="markdown-content">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.content}
                        </ReactMarkdown>
                      </div>
                      <Box variant="small" color="text-body-secondary">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </Box>
                    </SpaceBetween>
                  </div>
                ))}
                {loading && (
                  <Box textAlign="center" padding="m">
                    <Spinner size="large" />
                    <Box variant="p" padding={{ top: 's' }}>
                      {selectedContext.value === 'knowledge-base' 
                        ? 'Searching AWS Knowledge Base...' 
                        : 'Assistant is thinking...'}
                    </Box>
                  </Box>
                )}
                <div ref={messagesEndRef} />
              </SpaceBetween>
            )}
          </div>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <Input
                value={inputMessage}
                onChange={({ detail }) => setInputMessage(detail.value)}
                onKeyDown={handleKeyPress}
                placeholder="Type your message here... (Press Enter to send)"
                disabled={loading}
              />
            </div>
            <Button
              variant="primary"
              onClick={handleSendMessage}
              disabled={loading || !inputMessage.trim()}
              iconName="send"
            >
              Send
            </Button>
          </div>
        </SpaceBetween>
      </Container>

      {/* Context View Modal */}
      <Modal
        visible={showContextModal}
        onDismiss={() => setShowContextModal(false)}
        header={`Context: ${selectedContext.label}`}
        size="large"
      >
        <Box padding="m">
          <div 
            className="markdown-content"
            style={{ 
              maxHeight: '600px', 
              overflow: 'auto',
              whiteSpace: 'pre-wrap',
              fontSize: '14px',
              backgroundColor: '#f9f9f9',
              padding: '16px',
              borderRadius: '4px',
              border: '1px solid #e0e0e0'
            }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {contextData}
            </ReactMarkdown>
          </div>
        </Box>
      </Modal>
    </SpaceBetween>
  );
}

export default ChatAssistant;
