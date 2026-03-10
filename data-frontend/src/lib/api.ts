import axios, { AxiosInstance } from 'axios';

interface Anomaly {
  record_id: number;
  record_identifier?: string;
  field: string;
  given_value: string;
  correct_value: string;
  reason: string;
  recommendations: string[];
  secondary_reference?: string;
  source?: 'fuzzy' | 'embedding'; // Source of detection (undefined = LLM)
}

interface BackendAnomaly {
  record_id?: number | string;
  record_identifier?: string;
  field?: string;
  given_value?: string;
  correct_value?: string;
  reason?: string;
  recommendations?: string[];
  secondary_reference?: string;
  source?: 'fuzzy' | 'embedding';
}

const normalizeAnomaly = (anomaly: BackendAnomaly): Anomaly => {
  const recommendations = Array.isArray(anomaly.recommendations)
    ? anomaly.recommendations.filter((value): value is string => typeof value === 'string' && value.trim().length > 0)
    : [];

  const secondaryReference = typeof anomaly.secondary_reference === 'string' && anomaly.secondary_reference.trim().length > 0
    ? anomaly.secondary_reference
    : undefined;

  return {
    record_id: typeof anomaly.record_id === 'number' ? anomaly.record_id : Number(anomaly.record_id) || 0,
    record_identifier: anomaly.record_identifier,
    field: anomaly.field ?? '',
    given_value: anomaly.given_value ?? '',
    correct_value: anomaly.correct_value ?? '',
    reason: anomaly.reason ?? 'Manual review required',
    recommendations,
    secondary_reference: secondaryReference,
    source: anomaly.source,
  };
};

interface CompareResponse {
  anomalies: Anomaly[];
  statistics?: {
    identifier_field: string;
    total_records: number;
    exact_matches: number;
    fuzzy_anomalies: number;
    embedding_anomalies: number;
    llm_analyzed: number;
    anomalies_found: number;
    efficiency: string;
  };
}

interface ApplyFixesPayload {
  record_id: number;
  field: string;
  correct_value: string;
}

interface ApplyFixesResponse {
  message: string;
  updated_rows: number;
  file_name?: string;
}

interface StatusResponse {
  given: boolean;
  master1: boolean;
  master2: boolean;
  given_rows: number;
  master1_rows: number;
  master2_rows: number;
}

interface DataAnalyzeAnomaly {
  column: string;
  type: string;
  severity?: string;
  recommendation?: string | null;
  ml_score?: number | string;
}

interface DataAnalyzeResponse {
  structure_status?: string | null;
  report: {
    rows: number;
    columns: number;
    duplicate_rows_pct: number;
    duplicate_check_column?: string;
    columns_analysis?: Record<string, unknown>;
  };
  anomalies: DataAnalyzeAnomaly[];
  ml_status?: {
    enabled?: boolean;
    memory_records?: number;
    model_ready?: boolean;
  };
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Error handler
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const dataDiscrepancyAPI = {
  /**
   * Upload a CSV file as Given, Master1, or Master2
   */
  uploadFile: async (file: File, datasetType: 'given' | 'master1' | 'master2') => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/upload/${datasetType}`,
        formData
      );
      return response.data;
    } catch (error: any) {
      console.error('Upload error:', error.response?.data || error.message);
      throw new Error(`Failed to upload ${datasetType}: ${error.response?.data?.detail || error.message}`);
    }
  },

  /**
   * Compare Given dataset with selected Master dataset using 4-step pipeline
   */
  compareDatasets: async (
    preferredMaster: 'master1' | 'master2',
    identifierField?: string // Optional: field to match records (auto-detected if not provided)
  ): Promise<CompareResponse> => {
    try {
      const params: any = {
        preferred_master: preferredMaster,
      };
      
      // Only add identifier_field if provided, otherwise backend will auto-detect
      if (identifierField) {
        params.identifier_field = identifierField;
      }
      
      const response = await apiClient.post('/analyze', null, { params });
      const normalizedAnomalies = Array.isArray(response.data?.anomalies)
        ? response.data.anomalies.map((anomaly: BackendAnomaly) => normalizeAnomaly(anomaly))
        : [];

      return {
        ...response.data,
        anomalies: normalizedAnomalies,
      };
    } catch (error) {
      throw new Error(`Failed to compare datasets: ${error}`);
    }
  },

  /**
   * Apply selected fixes to the Given dataset
   */
  applyFixes: async (fixes: ApplyFixesPayload[]): Promise<ApplyFixesResponse> => {
    try {
      const response = await apiClient.post('/apply-fixes', fixes);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to apply fixes: ${error}`);
    }
  },

  /**
   * Build download URL for a fixed Given CSV
   */
  getFixedGivenDownloadUrl: (fileName: string) => {
    return `${API_BASE_URL}/download/given-fixed/${encodeURIComponent(fileName)}`;
  },

  /**
   * Get status of uploaded datasets
   */
  getStatus: async (): Promise<StatusResponse> => {
    try {
      const response = await apiClient.get('/status');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get status: ${error}`);
    }
  },

  /**
   * Retrieve a complete dataset
   */
  getData: async (datasetType: 'given' | 'master1' | 'master2') => {
    try {
      const response = await apiClient.get(`/data/${datasetType}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to retrieve ${datasetType}: ${error}`);
    }
  },

  analyzeDataFile: async (
    file: File,
    sheet?: string,
    duplicateKey?: string
  ): Promise<DataAnalyzeResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    if (sheet && sheet.trim().length > 0) {
      formData.append('sheet', sheet.trim());
    }

    if (duplicateKey && duplicateKey.trim().length > 0) {
      formData.append('duplicate_key', duplicateKey.trim());
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/data-analyze/analyze`, formData);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to run data analysis: ${error}`);
    }
  },
};

export type {
  Anomaly,
  CompareResponse,
  ApplyFixesPayload,
  ApplyFixesResponse,
  StatusResponse,
  DataAnalyzeResponse,
  DataAnalyzeAnomaly,
};
