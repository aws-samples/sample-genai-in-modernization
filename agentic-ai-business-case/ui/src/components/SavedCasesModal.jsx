import React, { useState, useEffect } from 'react';
import {
  Modal,
  Box,
  SpaceBetween,
  Table,
  Button,
  Header,
  Alert,
  StatusIndicator,
  TextFilter
} from '@cloudscape-design/components';

const SavedCasesModal = ({ visible, onDismiss, onLoadCase }) => {
  const [savedCases, setSavedCases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filteringText, setFilteringText] = useState('');
  const [selectedItems, setSelectedItems] = useState([]);

  useEffect(() => {
    if (visible) {
      loadSavedCases();
    }
  }, [visible]);

  const loadSavedCases = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:5000/api/dynamodb/list');
      const data = await response.json();
      
      if (data.success) {
        setSavedCases(data.cases || []);
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError('Failed to load saved cases: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadCase = async () => {
    if (selectedItems.length === 0) return;
    
    const caseId = selectedItems[0].caseId;
    setLoading(true);
    
    try {
      const response = await fetch(`http://localhost:5000/api/dynamodb/load/${caseId}`);
      const data = await response.json();
      
      if (data.success) {
        onLoadCase(data.case);
        onDismiss();
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError('Failed to load case: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCase = async () => {
    if (selectedItems.length === 0) return;
    
    const caseId = selectedItems[0].caseId;
    setLoading(true);
    
    try {
      const response = await fetch(`http://localhost:5000/api/dynamodb/delete/${caseId}`, {
        method: 'DELETE'
      });
      const data = await response.json();
      
      if (data.success) {
        setSelectedItems([]);
        loadSavedCases();
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError('Failed to delete case: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  const filteredCases = savedCases.filter(item => {
    if (!filteringText) return true;
    const searchText = filteringText.toLowerCase();
    return (
      item.caseId?.toLowerCase().includes(searchText) ||
      item.projectInfo?.projectName?.toLowerCase().includes(searchText) ||
      item.projectInfo?.customerName?.toLowerCase().includes(searchText)
    );
  });

  return (
    <Modal
      visible={visible}
      onDismiss={onDismiss}
      size="large"
      header="Saved Business Cases"
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={onDismiss}>
              Cancel
            </Button>
            <Button
              variant="normal"
              onClick={handleDeleteCase}
              disabled={selectedItems.length === 0 || loading}
            >
              Delete
            </Button>
            <Button
              variant="primary"
              onClick={handleLoadCase}
              disabled={selectedItems.length === 0 || loading}
            >
              Load Selected
            </Button>
          </SpaceBetween>
        </Box>
      }
    >
      <SpaceBetween size="l">
        {error && (
          <Alert
            type="error"
            dismissible
            onDismiss={() => setError(null)}
          >
            {error}
          </Alert>
        )}

        <Table
          columnDefinitions={[
            {
              id: 'caseId',
              header: 'Case ID',
              cell: item => item.caseId || 'N/A',
              sortingField: 'caseId'
            },
            {
              id: 'projectName',
              header: 'Project Name',
              cell: item => item.projectInfo?.projectName || 'N/A',
              sortingField: 'projectName'
            },
            {
              id: 'customerName',
              header: 'Customer',
              cell: item => item.projectInfo?.customerName || 'N/A',
              sortingField: 'customerName'
            },
            {
              id: 'createdAt',
              header: 'Created',
              cell: item => formatDate(item.createdAt),
              sortingField: 'createdAt'
            },
            {
              id: 'lastUpdated',
              header: 'Last Updated',
              cell: item => formatDate(item.lastUpdated),
              sortingField: 'lastUpdated'
            }
          ]}
          items={filteredCases}
          loading={loading}
          loadingText="Loading saved cases..."
          selectionType="single"
          selectedItems={selectedItems}
          onSelectionChange={({ detail }) => setSelectedItems(detail.selectedItems)}
          empty={
            <Box textAlign="center" color="inherit">
              <b>No saved business cases</b>
              <Box padding={{ bottom: 's' }} variant="p" color="inherit">
                Generate and save a business case to see it here.
              </Box>
            </Box>
          }
          filter={
            <TextFilter
              filteringText={filteringText}
              filteringPlaceholder="Search cases"
              onChange={({ detail }) => setFilteringText(detail.filteringText)}
            />
          }
          header={
            <Header
              counter={`(${filteredCases.length})`}
              actions={
                <Button
                  iconName="refresh"
                  onClick={loadSavedCases}
                  disabled={loading}
                >
                  Refresh
                </Button>
              }
            >
              Saved Cases
            </Header>
          }
        />
      </SpaceBetween>
    </Modal>
  );
};

export default SavedCasesModal;
