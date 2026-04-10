import React, { createContext, useContext, useState } from 'react';

const MapAssessmentContext = createContext();

export const useMapAssessment = () => {
  const context = useContext(MapAssessmentContext);
  if (!context) {
    throw new Error('useMapAssessment must be used within MapAssessmentProvider');
  }
  return context;
};

export const MapAssessmentProvider = ({ children }) => {
  // State for each GenAI use case
  const [modernizationData, setModernizationData] = useState({
    inventoryAnalysis: '',
    architectureAnalysis: '',
    pathwayRecommendations: ''
  });

  const [migrationStrategyData, setMigrationStrategyData] = useState({
    strategy: ''
  });

  const [resourcePlanningData, setResourcePlanningData] = useState({
    plan: ''
  });

  const [learningPathwayData, setLearningPathwayData] = useState({
    pathway: ''
  });

  const [businessCaseReviewData, setBusinessCaseReviewData] = useState({
    validation: ''
  });

  const [architectureDiagramData, setArchitectureDiagramData] = useState({
    diagram: ''
  });

  const [serviceAnalysisData, setServiceAnalysisData] = useState({
    analysis: ''
  });

  const [olaData, setOLAData] = useState({
    results: null
  });

  // Reset functions for each use case
  const resetModernization = () => {
    setModernizationData({
      inventoryAnalysis: '',
      architectureAnalysis: '',
      pathwayRecommendations: ''
    });
  };

  const resetMigrationStrategy = () => {
    setMigrationStrategyData({ strategy: '' });
  };

  const resetResourcePlanning = () => {
    setResourcePlanningData({ plan: '' });
  };

  const resetLearningPathway = () => {
    setLearningPathwayData({ pathway: '' });
  };

  const resetBusinessCaseReview = () => {
    setBusinessCaseReviewData({ validation: '' });
  };

  const resetArchitectureDiagram = () => {
    setArchitectureDiagramData({ diagram: '' });
  };

  const resetServiceAnalysis = () => {
    setServiceAnalysisData({ analysis: '' });
  };

  const resetOLA = () => {
    setOLAData({
      results: null
    });
  };

  const resetAll = () => {
    resetModernization();
    resetMigrationStrategy();
    resetResourcePlanning();
    resetLearningPathway();
    resetBusinessCaseReview();
    resetArchitectureDiagram();
    resetServiceAnalysis();
    resetOLA();
  };

  // Get context data by type for chat assistant
  const getContextData = (contextType) => {
    switch (contextType) {
      case 'modernization':
        return modernizationData;
      case 'migration-strategy':
        return migrationStrategyData;
      case 'resource-planning':
        return resourcePlanningData;
      case 'learning-pathway':
        return learningPathwayData;
      case 'business-case':
        return businessCaseReviewData;
      case 'architecture':
        return architectureDiagramData;
      case 'service-analysis':
        return serviceAnalysisData;
      case 'ola-analysis':
        return olaData;
      default:
        return null;
    }
  };

  const value = {
    // Modernization
    modernizationData,
    setModernizationData,
    resetModernization,
    
    // Migration Strategy
    migrationStrategyData,
    setMigrationStrategyData,
    resetMigrationStrategy,
    
    // Resource Planning
    resourcePlanningData,
    setResourcePlanningData,
    resetResourcePlanning,
    
    // Learning Pathway
    learningPathwayData,
    setLearningPathwayData,
    resetLearningPathway,
    
    // Business Case Review
    businessCaseReviewData,
    setBusinessCaseReviewData,
    resetBusinessCaseReview,
    
    // Architecture Diagram
    architectureDiagramData,
    setArchitectureDiagramData,
    resetArchitectureDiagram,
    
    // Service Analysis
    serviceAnalysisData,
    setServiceAnalysisData,
    resetServiceAnalysis,
    
    // OLA Analysis
    olaData,
    setOLAData,
    resetOLA,
    
    // Utilities
    resetAll,
    getContextData
  };

  return (
    <MapAssessmentContext.Provider value={value}>
      {children}
    </MapAssessmentContext.Provider>
  );
};
