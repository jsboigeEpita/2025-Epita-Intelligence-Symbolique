import React, { createContext, useState, useContext } from 'react';

const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [analysisResult, setAnalysisResult] = useState(null);
  const [fallacyResult, setFallacyResult] = useState(null);
  const [reconstructionResult, setReconstructionResult] = useState(null);
  const [logicGraphResult, setLogicGraphResult] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [frameworkResult, setFrameworkResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const [textInputs, setTextInputs] = useState({
    analyzer: '',
    fallacy_detector: '',
    reconstructor: '',
    logic_graph: '',
  });

  const updateTextInput = (tab, value) => {
    setTextInputs(prev => ({ ...prev, [tab]: value }));
  };

  const resetAllStates = () => {
    setAnalysisResult(null);
    setFallacyResult(null);
    setReconstructionResult(null);
    setLogicGraphResult(null);
    setValidationResult(null);
    setFrameworkResult(null);
    setTextInputs({
      analyzer: '',
      fallacy_detector: '',
      reconstructor: '',
      logic_graph: '',
    });
  };

  const value = {
    // Results
    analysisResult,
    setAnalysisResult,
    fallacyResult,
    setFallacyResult,
    reconstructionResult,
    setReconstructionResult,
    logicGraphResult,
    setLogicGraphResult,
    validationResult,
    setValidationResult,
    frameworkResult,
    setFrameworkResult,
    // Loading state
    isLoading,
    setIsLoading,
    // Text Inputs
    textInputs,
    updateTextInput,
    // Global Actions
    resetAllStates,
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => {
  return useContext(AppContext);
};