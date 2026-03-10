import React, { useState } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Loader2, CheckCircle2 } from 'lucide-react';
import { AnomalyTable } from './AnomalyTable';
import { dataDiscrepancyAPI, type Anomaly, type ApplyFixesPayload } from '@/lib/api';

interface ComparisonSectionProps {
  anomalies: Anomaly[];
  setAnomalies: (anomalies: Anomaly[]) => void;
  comparisonLoading: boolean;
  setComparisonLoading: (loading: boolean) => void;
  comparisonError: string | null;
  setComparisonError: (error: string | null) => void;
  comparisonSuccess: string | null;
  setComparisonSuccess: (success: string | null) => void;
  fixedFileName: string | null;
  setFixedFileName: (fileName: string | null) => void;
  onComparisonComplete?: () => void;
}

export const ComparisonSection: React.FC<ComparisonSectionProps> = ({
  anomalies,
  setAnomalies,
  comparisonLoading,
  setComparisonLoading,
  comparisonError,
  setComparisonError,
  comparisonSuccess,
  setComparisonSuccess,
  fixedFileName,
  setFixedFileName,
  onComparisonComplete,
}) => {
  const [preferredMaster, setPreferredMaster] = useState<'master1' | 'master2'>('master1');
  const [applying, setApplying] = useState(false);

  const handleCompare = async () => {
    setComparisonLoading(true);
    setComparisonError(null);
    setComparisonSuccess(null);
    setFixedFileName(null);

    try {
      const result = await dataDiscrepancyAPI.compareDatasets(preferredMaster);
      setAnomalies(result.anomalies || []);

      if (result.anomalies.length === 0) {
        setComparisonSuccess('Comparison complete! No discrepancies found.');
      } else {
        setComparisonSuccess(`Comparison complete! Found ${result.anomalies.length} discrepancies.`);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to compare datasets';
      setComparisonError(errorMessage);
      setAnomalies([]);
    } finally {
      setComparisonLoading(false);
    }
  };

  const handleApplyFixes = async (fixes: ApplyFixesPayload[]) => {
    setApplying(true);
    setComparisonError(null);
    setComparisonSuccess(null);
    setFixedFileName(null);

    try {
      const result = await dataDiscrepancyAPI.applyFixes(fixes);
      setComparisonSuccess(`${result.message}`);
      if (result.file_name) {
        setFixedFileName(result.file_name);
      }

      // Remove applied fixes from the table
      const appliedKeys = new Set(fixes.map((f) => `${f.record_id}-${f.field}`));
      setAnomalies(
        anomalies.filter((a) => !appliedKeys.has(`${a.record_id}-${a.field}`))
      );

      onComparisonComplete?.();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to apply fixes';
      setComparisonError(errorMessage);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Data Comparison & Correction</CardTitle>
        <CardDescription>
          Compare your given data with a master database to detect and fix discrepancies
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Preferred Master Selection */}
        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label className="text-sm font-medium mb-2 block">Preferred Master Database</label>
            <Select value={preferredMaster} onValueChange={(value) => setPreferredMaster(value as 'master1' | 'master2')}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="master1">Master Database 1</SelectItem>
                <SelectItem value="master2">Master Database 2</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button
            onClick={handleCompare}
            disabled={comparisonLoading}
            className="w-32"
          >
            {comparisonLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Comparing...
              </>
            ) : (
              'Compare'
            )}
          </Button>
        </div>

        {/* Error Alert */}
        {comparisonError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{comparisonError}</AlertDescription>
          </Alert>
        )}

        {/* Success Alert */}
        {comparisonSuccess && (
          <Alert className="border-green-200 bg-green-50">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800">
              <div className="flex items-center justify-between gap-3">
                <span>{comparisonSuccess}</span>
                {fixedFileName && (
                  <Button
                    variant="outline"
                    onClick={() => {
                      const url = dataDiscrepancyAPI.getFixedGivenDownloadUrl(fixedFileName);
                      window.location.href = url;
                    }}
                  >
                    Download Fixed CSV
                  </Button>
                )}
              </div>
            </AlertDescription>
          </Alert>
        )}

        {/* Anomaly Table */}
        {anomalies.length > 0 && (
          <div className="space-y-4">
            <div className="border-t pt-6">
              <h3 className="text-lg font-semibold mb-4">Discrepancies Found</h3>
              <AnomalyTable
                anomalies={anomalies}
                onFixesSelected={handleApplyFixes}
                isLoading={applying}
                preferredMaster={preferredMaster}
              />
            </div>
          </div>
        )}

        {/* Loading State */}
        {comparisonLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-4" />
              <p className="text-gray-600">Analyzing datasets with AI...</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
