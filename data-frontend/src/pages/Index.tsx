import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { FileUploader } from '@/components/FileUploader';
import { ComparisonSection } from '@/components/ComparisonSection';
import { dataDiscrepancyAPI, type Anomaly, type DataAnalyzeResponse } from '@/lib/api';
import { useEffect } from 'react';

interface UploadStatus {
  given: boolean;
  master1: boolean;
  master2: boolean;
  givenRows: number;
  master1Rows: number;
  master2Rows: number;
}

const Index = () => {
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({
    given: false,
    master1: false,
    master2: false,
    givenRows: 0,
    master1Rows: 0,
    master2Rows: 0,
  });

  const [uploading, setUploading] = useState<{
    given: boolean;
    master1: boolean;
    master2: boolean;
  }>({
    given: false,
    master1: false,
    master2: false,
  });

  const [uploadErrors, setUploadErrors] = useState<Record<string, string>>({});

  // Comparison state - persists across tab switches
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState<string | null>(null);
  const [comparisonSuccess, setComparisonSuccess] = useState<string | null>(null);
  const [fixedFileName, setFixedFileName] = useState<string | null>(null);

  const [analyzeFile, setAnalyzeFile] = useState<File | null>(null);
  const [analyzeSheet, setAnalyzeSheet] = useState('');
  const [analyzeDuplicateKey, setAnalyzeDuplicateKey] = useState('');
  const [analyzeLoading, setAnalyzeLoading] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [analyzeResult, setAnalyzeResult] = useState<DataAnalyzeResponse | null>(null);

  // Check upload status on mount
  useEffect(() => {
    checkUploadStatus();
  }, []);

  const checkUploadStatus = async () => {
    try {
      const status = await dataDiscrepancyAPI.getStatus();
      setUploadStatus({
        given: status.given,
        master1: status.master1,
        master2: status.master2,
        givenRows: status.given_rows,
        master1Rows: status.master1_rows,
        master2Rows: status.master2_rows,
      });
    } catch (error) {
      console.error('Failed to check upload status:', error);
    }
  };

  const handleFileSelect = async (
    file: File,
    datasetType: 'given' | 'master1' | 'master2'
  ) => {
    const isValidFile = file.name.endsWith('.csv') || file.name.endsWith('.xlsx');
    if (!isValidFile) {
      setUploadErrors({ ...uploadErrors, [datasetType]: 'Please upload a CSV or XLSX file' });
      return;
    }

    setUploading({ ...uploading, [datasetType]: true });
    setUploadErrors({ ...uploadErrors, [datasetType]: '' });

    try {
      const response = await dataDiscrepancyAPI.uploadFile(file, datasetType);
      setUploadStatus({
        ...uploadStatus,
        [datasetType]: true,
        [`${datasetType}Rows`]: response.rows,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      setUploadErrors({ ...uploadErrors, [datasetType]: errorMessage });
    } finally {
      setUploading({ ...uploading, [datasetType]: false });
    }
  };

  const allUploaded = uploadStatus.given && uploadStatus.master1 && uploadStatus.master2;

  const handleAnalyzeDataProject = async () => {
    if (!analyzeFile) {
      setAnalyzeError('Please select a CSV or Excel file first.');
      return;
    }

    setAnalyzeLoading(true);
    setAnalyzeError(null);

    try {
      const result = await dataDiscrepancyAPI.analyzeDataFile(
        analyzeFile,
        analyzeSheet,
        analyzeDuplicateKey
      );
      setAnalyzeResult(result);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to analyze file';
      setAnalyzeError(errorMessage);
      setAnalyzeResult(null);
    } finally {
      setAnalyzeLoading(false);
    }
  };

  const handleDownloadAnalyzeReport = () => {
    if (!analyzeResult) return;

    const json = JSON.stringify(analyzeResult, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'data_quality_report.json';
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto py-8 px-4 max-w-6xl">
        {/* Top-level tabs */}
        <Tabs defaultValue="analyze" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="analyze">Data Inspector</TabsTrigger>
            <TabsTrigger value="discrepancy">Data Discrepancy</TabsTrigger>
          </TabsList>

          <TabsContent value="discrepancy" className="space-y-6">
            <div className="pt-2">
              <h1 className="text-4xl font-bold text-slate-900 mb-2">
                Data Discrepancy Detection & Correction
              </h1>
              <p className="text-lg text-slate-600">
                Upload your datasets and use AI to detect and fix inconsistencies
              </p>
            </div>

            <Tabs defaultValue="upload" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="upload">Upload Data</TabsTrigger>
                <TabsTrigger value="compare" disabled={!allUploaded}>
                  Compare & Fix
                </TabsTrigger>
              </TabsList>

              {/* Upload Tab */}
              <TabsContent value="upload" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Upload Your Datasets</CardTitle>
                    <CardDescription>
                      Upload three CSV or XLSX files: one Given database and two Master databases for comparison
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-8">
                    {/* Given Database */}
                    <div>
                      <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
                        Given Database
                        {uploadStatus.given && (
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                        )}
                      </h3>
                      <FileUploader
                        label="Given Database (CSV/XLSX)"
                        description="The database you want to check and fix"
                        file={null}
                        onFileSelect={(file) => handleFileSelect(file, 'given')}
                        accept=".csv,.xlsx"
                      />
                      {uploadStatus.given && (
                        <p className="text-xs text-slate-600 mt-2">
                          {uploadStatus.givenRows} records uploaded
                        </p>
                      )}
                      {uploadErrors.given && (
                        <Alert variant="destructive" className="mt-2">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>{uploadErrors.given}</AlertDescription>
                        </Alert>
                      )}
                      {uploading.given && (
                        <div className="flex items-center gap-2 mt-2 text-sm text-slate-600">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Uploading...
                        </div>
                      )}
                    </div>

                    {/* Master Database 1 */}
                    <div>
                      <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
                        Master Database 1
                        {uploadStatus.master1 && (
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                        )}
                      </h3>
                      <FileUploader
                        label="Master Database 1 (CSV/XLSX)"
                        description="First source of truth database"
                        file={null}
                        onFileSelect={(file) => handleFileSelect(file, 'master1')}
                        accept=".csv,.xlsx"
                      />
                      {uploadStatus.master1 && (
                        <p className="text-xs text-slate-600 mt-2">
                          {uploadStatus.master1Rows} records uploaded
                        </p>
                      )}
                      {uploadErrors.master1 && (
                        <Alert variant="destructive" className="mt-2">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>{uploadErrors.master1}</AlertDescription>
                        </Alert>
                      )}
                      {uploading.master1 && (
                        <div className="flex items-center gap-2 mt-2 text-sm text-slate-600">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Uploading...
                        </div>
                      )}
                    </div>

                    {/* Master Database 2 */}
                    <div>
                      <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
                        Master Database 2
                        {uploadStatus.master2 && (
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                        )}
                      </h3>
                      <FileUploader
                        label="Master Database 2 (CSV/XLSX)"
                        description="Second source of truth database (for recommendations)"
                        file={null}
                        onFileSelect={(file) => handleFileSelect(file, 'master2')}
                        accept=".csv,.xlsx"
                      />
                      {uploadStatus.master2 && (
                        <p className="text-xs text-slate-600 mt-2">
                          {uploadStatus.master2Rows} records uploaded
                        </p>
                      )}
                      {uploadErrors.master2 && (
                        <Alert variant="destructive" className="mt-2">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>{uploadErrors.master2}</AlertDescription>
                        </Alert>
                      )}
                      {uploading.master2 && (
                        <div className="flex items-center gap-2 mt-2 text-sm text-slate-600">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Uploading...
                        </div>
                      )}
                    </div>

                    {allUploaded && (
                      <Alert className="border-green-200 bg-green-50">
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                        <AlertDescription className="text-green-800">
                          All datasets uploaded successfully! Go to the Compare & Fix tab to begin.
                        </AlertDescription>
                      </Alert>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Compare Tab */}
              <TabsContent value="compare">
                <ComparisonSection
                  anomalies={anomalies}
                  setAnomalies={setAnomalies}
                  comparisonLoading={comparisonLoading}
                  setComparisonLoading={setComparisonLoading}
                  comparisonError={comparisonError}
                  setComparisonError={setComparisonError}
                  comparisonSuccess={comparisonSuccess}
                  setComparisonSuccess={setComparisonSuccess}
                  fixedFileName={fixedFileName}
                  setFixedFileName={setFixedFileName}
                  onComparisonComplete={checkUploadStatus}
                />
              </TabsContent>
            </Tabs>
          </TabsContent>

          <TabsContent value="analyze" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>📊 Universal Data Inspector</CardTitle>
                <CardDescription>
                  Upload a CSV or Excel file to analyze structure, quality & data issues
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="text-sm font-medium text-slate-700 mb-2 block">Drop CSV / Excel file here</label>
                      <Input
                        type="file"
                        accept=".csv,.xlsx,.xls,.xlsm,.txt"
                        onChange={(event) => {
                          const file = event.target.files?.[0] || null;
                          setAnalyzeFile(file);
                        }}
                      />
                    </div>

                    <div>
                      <label className="text-sm font-medium text-slate-700 mb-2 block">Excel Sheet (name or index, optional)</label>
                      <Input
                        value={analyzeSheet}
                        onChange={(event) => setAnalyzeSheet(event.target.value)}
                        placeholder="Sheet name or index"
                      />
                    </div>

                    <div>
                      <label className="text-sm font-medium text-slate-700 mb-2 block">Select column for duplicate detection</label>
                      <Input
                        value={analyzeDuplicateKey}
                        onChange={(event) => setAnalyzeDuplicateKey(event.target.value)}
                        placeholder="Auto when empty"
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <Button onClick={handleAnalyzeDataProject} disabled={analyzeLoading}>
                      {analyzeLoading ? 'Analyzing...' : '🔍 Analyze File'}
                    </Button>
                    {analyzeFile && (
                      <span className="text-sm text-slate-600">Selected: {analyzeFile.name}</span>
                    )}
                  </div>

                  {analyzeError && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{analyzeError}</AlertDescription>
                    </Alert>
                  )}

                  {analyzeResult && (
                    <div className="space-y-4 border rounded-md p-4 bg-slate-50">
                      {/* File Summary */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div className="rounded border bg-white p-3">
                          <p className="text-xs text-slate-500">Rows</p>
                          <p className="text-lg font-semibold">{analyzeResult.report?.rows ?? 0}</p>
                        </div>
                        <div className="rounded border bg-white p-3">
                          <p className="text-xs text-slate-500">Columns</p>
                          <p className="text-lg font-semibold">{analyzeResult.report?.columns ?? 0}</p>
                        </div>
                        <div className="rounded border bg-white p-3">
                          <p className="text-xs text-slate-500">Duplicate %</p>
                          <p className="text-lg font-semibold">{analyzeResult.report?.duplicate_rows_pct ?? 0}</p>
                        </div>
                        <div className="rounded border bg-white p-3">
                          <p className="text-xs text-slate-500">Anomalies</p>
                          <p className="text-lg font-semibold">{analyzeResult.anomalies?.length ?? 0}</p>
                        </div>
                      </div>

                      <p className="text-sm text-slate-600">
                        Duplicate check column: {analyzeResult.report?.duplicate_check_column || 'Auto'}
                      </p>

                      {analyzeResult.structure_status && (
                        <Alert variant={analyzeResult.structure_status.startsWith('row_wise') ? 'default' : 'destructive'}>
                          <AlertDescription>
                            Structure Status: {analyzeResult.structure_status}
                          </AlertDescription>
                        </Alert>
                      )}

                      {/* Machine Learning Status */}
                      <div className="rounded border bg-white p-4 space-y-2">
                        <h3 className="text-sm font-semibold text-slate-800">🧠 Machine Learning Status</h3>
                        {analyzeResult.ml_status?.enabled ? (
                          <p className="text-sm text-green-700">ML Engine is ACTIVE</p>
                        ) : (
                          <p className="text-sm text-amber-700">ML Engine not initialized</p>
                        )}
                        <p className="text-sm text-slate-700">
                          Learned anomaly patterns: <strong>{analyzeResult.ml_status?.memory_records ?? 0}</strong>
                        </p>
                        {analyzeResult.ml_status?.model_ready ? (
                          <p className="text-sm text-green-700">ML is ready to recommend improvements</p>
                        ) : (
                          <p className="text-sm text-slate-600">ML is learning. Upload more files to improve accuracy.</p>
                        )}
                      </div>

                      {/* ML Recommendations */}
                      <div className="rounded border bg-white p-4 space-y-2">
                        <h3 className="text-sm font-semibold text-slate-800">🛠 ML Recommendations</h3>
                        {(analyzeResult.anomalies || []).some((item) => !!item.recommendation) ? (
                          <div className="space-y-2">
                            {(analyzeResult.anomalies || [])
                              .filter((item) => !!item.recommendation)
                              .map((item, index) => (
                                <Alert key={`${item.column}-${index}`}>
                                  <AlertDescription>
                                    Column <strong>{item.column}</strong> → {item.recommendation}{' '}
                                    (confidence: {item.ml_score ?? 'n/a'})
                                  </AlertDescription>
                                </Alert>
                              ))}
                          </div>
                        ) : (
                          <p className="text-sm text-slate-600">No actionable ML recommendations yet.</p>
                        )}
                      </div>

                      {/* Column Analysis */}
                      <div className="rounded border bg-white p-4 space-y-3">
                        <h3 className="text-sm font-semibold text-slate-800">🔍 Column Analysis</h3>
                        {Object.entries(analyzeResult.report?.columns_analysis || {}).map(([columnName, columnInfo]) => {
                          const info = columnInfo as Record<string, unknown>;
                          const mixedDatatype = info.mixed_datatype_analysis;
                          const qualityFlags = Array.isArray(info.quality_flags) ? (info.quality_flags as string[]) : [];
                          const semanticMismatch = info.semantic_mismatch as Record<string, unknown> | undefined;

                          return (
                            <details key={columnName} className="rounded border p-3 bg-slate-50">
                              <summary className="cursor-pointer text-sm font-medium text-slate-800">{columnName}</summary>
                              <div className="mt-3 space-y-2 text-sm text-slate-700">
                                <p><strong>Inferred Type:</strong> {String(info.inferred_type ?? 'N/A')}</p>
                                <p><strong>Null %:</strong> {String(info.null_pct ?? 'N/A')}</p>
                                <p><strong>Unique Values:</strong> {String(info.unique_values ?? 'N/A')}</p>

                                {semanticMismatch && (
                                  <Alert variant="destructive">
                                    <AlertDescription>
                                      {String(semanticMismatch.issue ?? 'Semantic mismatch detected')}
                                      {semanticMismatch.string_count !== undefined && (
                                        <> (rows: {String(semanticMismatch.string_count)})</>
                                      )}
                                    </AlertDescription>
                                  </Alert>
                                )}

                                {qualityFlags.length > 0 && (
                                  <Alert>
                                    <AlertDescription>⚠ {qualityFlags.join(', ')}</AlertDescription>
                                  </Alert>
                                )}

                                {mixedDatatype && (
                                  <div>
                                    <p className="font-medium">Mixed Data Types</p>
                                    <pre className="mt-1 text-xs overflow-auto max-h-[180px] bg-white p-2 border rounded">
                                      {JSON.stringify(mixedDatatype, null, 2)}
                                    </pre>
                                  </div>
                                )}
                              </div>
                            </details>
                          );
                        })}
                      </div>

                      {/* Download Report */}
                      <div className="flex justify-end">
                        <Button variant="outline" onClick={handleDownloadAnalyzeReport}>
                          📥 Download JSON Report
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
};

export default Index;
