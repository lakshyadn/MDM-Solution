export interface DataRecord {
  [key: string]: string | number | boolean | null;
}

export interface Discrepancy {
  id: string;
  recordId: string;
  fieldName: string;
  givenValue: string;
  correctValue: string;
  otherMasterValue: string;
  status: 'anomaly' | 'fixed' | 'correct';
  selected: boolean;
}

export interface UploadedFile {
  name: string;
  data: DataRecord[];
  status: 'idle' | 'uploading' | 'success' | 'error';
  progress: number;
}

export interface ComparisonResult {
  discrepancies: Discrepancy[];
  totalRecords: number;
}
