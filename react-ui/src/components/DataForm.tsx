import React, { useState, useEffect } from 'react';
import Prism from 'prismjs';
import 'prismjs/themes/prism-tomorrow.css';
import 'prismjs/components/prism-python';
import './DataForm.css';

interface FormData {
  name: string;
  purpose: string;
  services: string[];
}

interface ApiResponse {
  name: string;
  timestamp: string;
}

interface GenerationResponse {
  function_code: string;
}

interface RetrievalFormData {
  name: string;
  timestamp: string;
}

type TabType = 'generate' | 'retrieve';

const API_URL = process.env.REACT_APP_API_URL;

if (!API_URL) {
  throw new Error('API_URL is not defined');
}

const DataForm: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('generate');
  const [formData, setFormData] = useState<FormData>({
    name: '',
    purpose: '',
    services: ['']
  });
  const [retrievalData, setRetrievalData] = useState<RetrievalFormData>({
    name: '',
    timestamp: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [timestamp, setTimestamp] = useState<string | null>(null);
  const [generatedCode, setGeneratedCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, index?: number) => {
    const { name, value } = e.target;
    
    if (name === 'services' && typeof index === 'number') {
      const newServices = [...formData.services];
      newServices[index] = value;
      setFormData({ ...formData, services: newServices });
    } else {
      setFormData({ ...formData, [name]: value });
    }
  };

  const handleRetrievalInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setRetrievalData(prev => ({ ...prev, [name]: value }));
  };

  const addservicesField = () => {
    setFormData({
      ...formData,
      services: [...formData.services, '']
    });
  };

  const removeservicesField = (index: number) => {
    const newservices = formData.services.filter((_, i) => i !== index);
    setFormData({
      ...formData,
      services: newservices
    });
  };

  const fetchGeneratedCode = async (name: string, timestamp: string) => {
    try {
      const response = await fetch(`${API_URL}?pk=${name}&sk=${timestamp}`);
      if (!response.ok) throw new Error('Failed to fetch generated code');
      
      const data: GenerationResponse = await response.json();
      setGeneratedCode(data.function_code);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch generated code');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setGeneratedCode(null);
    
    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });
      
      if (!response.ok) throw new Error('Failed to submit form');
      
      const data: ApiResponse = await response.json();
      setTimestamp(data.timestamp);
      
      setTimeout(() => {
        fetchGeneratedCode(data.name, data.timestamp);
      }, 180000);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit form');
      setIsLoading(false);
    }
  };

  const handleRetrievalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setGeneratedCode(null);

    try {
      await fetchGeneratedCode(retrievalData.name, retrievalData.timestamp);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retrieve function');
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setGeneratedCode(null);
    setTimestamp(null);
    setFormData({
      name: '',
      purpose: '',
      services: ['']
    });
    setRetrievalData({
      name: '',
      timestamp: ''
    });
    setError(null);
  };

  return (
    <div className="data-form">
      {!isLoading && !generatedCode && (
        <div className="form-container">
          <div className="tabs">
            <button
              className={`tab ${activeTab === 'generate' ? 'active' : ''}`}
              onClick={() => setActiveTab('generate')}
            >
              Generate New
            </button>
            <button
              className={`tab ${activeTab === 'retrieve' ? 'active' : ''}`}
              onClick={() => setActiveTab('retrieve')}
            >
              Retrieve Existing
            </button>
          </div>

          {activeTab === 'generate' ? (
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="name">Function Name:</label>
                <div className="input-wrapper">
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="provide a descriptive name"
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Purpose:</label>
                <div className="input-wrapper">
                  <textarea
                    name="purpose"
                    value={formData.purpose}
                    onChange={handleInputChange}
                    placeholder="what should the function do? (2-3 sentences)"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Services:</label>
                {formData.services.map((str, index) => (
                  <div key={index} className="string-list-item">
                    <input
                      type="text"
                      name="services"
                      value={str}
                      onChange={(e) => handleInputChange(e, index)}
                      required
                      placeholder="any expected AWS services"
                    />
                    {formData.services.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeservicesField(index)}
                        className="remove-button"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addservicesField}
                  className="add-button"
                >
                  Add Service
                </button>
              </div>

              <button type="submit" className="submit-button" disabled={isLoading}>
                Submit
              </button>
            </form>
          ) : (
            <form onSubmit={handleRetrievalSubmit} className="retrieval-form">
              <div className="form-group">
                <label htmlFor="name">Function Name:</label>
                <div className="input-wrapper">
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={retrievalData.name}
                    onChange={handleRetrievalInputChange}
                    placeholder="enter the function name"
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="timestamp">Timestamp:</label>
                <div className="input-wrapper">
                  <input
                    type="text"
                    id="timestamp"
                    name="timestamp"
                    value={retrievalData.timestamp}
                    onChange={handleRetrievalInputChange}
                    placeholder="enter the generation timestamp"
                    required
                  />
                </div>
              </div>

              <button type="submit" className="submit-button" disabled={isLoading}>
                Retrieve Function
              </button>
            </form>
          )}
        </div>
      )}

      {isLoading && (
        <div className="loading-container">
          <div className="spinner"></div>
          <h2>{activeTab === 'retrieve' ? 'Retrieving Your Function' : 'Generating Your Function'}</h2>
          {timestamp && <p>Generation started at: {timestamp}</p>}
          {activeTab === 'generate' && (
            <>
              <p>Please wait while your function is being generated...</p>
              <p className="estimate-text">This process takes approximately 3 minutes</p>
            </>
          )}
        </div>
      )}

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {generatedCode && !isLoading && (
        <div className="form-container code-result">
          <h2>Generated Function</h2>
          <div className="code-wrapper">
            <pre className="language-python">
              <code
                className="language-python"
                dangerouslySetInnerHTML={{
                  __html: Prism.highlight(
                    generatedCode,
                    Prism.languages.python,
                    'python'
                  ),
                }}
              />
            </pre>
          </div>
          <button 
            onClick={resetForm}
            className="submit-button"
          >
            Return
          </button>
        </div>
      )}
    </div>
  );
};

export default DataForm;
