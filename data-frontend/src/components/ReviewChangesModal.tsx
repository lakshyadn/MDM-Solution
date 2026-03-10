import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Loader2, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { dataDiscrepancyAPI, type Anomaly, type ApplyFixesPayload } from '@/lib/api';

interface ReviewChangesModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedAnomalies: Anomaly[];
  onApplyFixes: (fixes: ApplyFixesPayload[]) => void;
  isLoading: boolean;
}

interface RecordData {
  [key: string]: string | number | boolean | null | undefined;
}

export const ReviewChangesModal: React.FC<ReviewChangesModalProps> = ({
  open,
  onOpenChange,
  selectedAnomalies,
  onApplyFixes,
  isLoading,
}) => {
  const [recordsData, setRecordsData] = useState<Record<number, RecordData>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFixes, setSelectedFixes] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (open && selectedAnomalies.length > 0) {
      fetchRecordsData();
      // Initialize all as selected
      const allKeys = selectedAnomalies.map(a => `${a.record_id}-${a.field}`);
      setSelectedFixes(new Set(allKeys));
    } else if (!open) {
      // Clear state when modal closes
      setSelectedFixes(new Set());
      setRecordsData({});
      setError(null);
    }
  }, [open, selectedAnomalies]);

  const fetchRecordsData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await dataDiscrepancyAPI.getData('given');
      const recordsMap: Record<number, RecordData> = {};
      
      // Build a map of record_id to full record data
      data.forEach((record: RecordData) => {
        const recordId = record.id || record.record_id;
        if (recordId !== undefined && typeof recordId === 'number') {
          recordsMap[recordId] = record;
        }
      });
      
      setRecordsData(recordsMap);
    } catch (err) {
      setError('Failed to fetch record data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const toggleFix = (recordId: number, field: string) => {
    const key = `${recordId}-${field}`;
    setSelectedFixes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(key)) {
        newSet.delete(key);
      } else {
        newSet.add(key);
      }
      return newSet;
    });
  };

  const handleApply = () => {
    const fixes: ApplyFixesPayload[] = selectedAnomalies
      .filter(a => selectedFixes.has(`${a.record_id}-${a.field}`))
      .map(a => ({
        record_id: a.record_id,
        field: a.field,
        correct_value: a.correct_value,
      }));
    
    onApplyFixes(fixes);
  };

  const getRecordPreview = (recordId: number) => {
    return recordsData[recordId] || {};
  };

  // Group anomalies by record_id
  const groupedAnomalies = selectedAnomalies.reduce((acc, anomaly) => {
    if (!acc[anomaly.record_id]) {
      acc[anomaly.record_id] = [];
    }
    acc[anomaly.record_id].push(anomaly);
    return acc;
  }, {} as Record<number, Anomaly[]>);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Review Changes</DialogTitle>
          <DialogDescription>
            Review the complete records and their proposed changes before applying fixes
          </DialogDescription>
        </DialogHeader>

        {loading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            <span className="ml-2 text-sm text-gray-600">Loading record data...</span>
          </div>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {!loading && !error && (
          <div className="space-y-6">
            {Object.entries(groupedAnomalies).map(([recordIdStr, anomalies]) => {
              const recordId = Number(recordIdStr);
              const recordData = getRecordPreview(recordId);
              const allColumns = Object.keys(recordData);
              
              // Build arrays for horizontal display
              const changedFields = new Set(anomalies.map(a => a.field));
              const newValues: Record<string, any> = {};
              anomalies.forEach(a => {
                newValues[a.field] = a.correct_value;
              });

              return (
                <div key={recordId} className="border rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-lg">
                      Record ID: {recordId}
                      {recordData.university_name && (
                        <span className="ml-2 text-blue-600">- {recordData.university_name}</span>
                      )}
                    </h3>
                    <Badge variant="outline">{anomalies.length} change{anomalies.length !== 1 ? 's' : ''}</Badge>
                  </div>

                  {/* Excel-style Horizontal Table */}
                  <div className="border rounded overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-gray-50">
                          <TableHead className="font-semibold sticky left-0 bg-gray-50 border-r">Field</TableHead>
                          {allColumns.map(column => (
                            <TableHead 
                              key={column} 
                              className={`font-semibold min-w-[120px] ${changedFields.has(column) ? 'bg-yellow-100' : ''}`}
                            >
                              {column}
                            </TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {/* Current Values Row */}
                        <TableRow>
                          <TableCell className="font-medium sticky left-0 bg-white border-r">Current</TableCell>
                          {allColumns.map(column => {
                            const hasChange = changedFields.has(column);
                            return (
                              <TableCell 
                                key={column}
                                className={hasChange ? 'bg-red-50' : ''}
                              >
                                <span className={hasChange ? 'text-red-600 font-semibold' : 'text-gray-600'}>
                                  {String(recordData[column] ?? '')}
                                </span>
                              </TableCell>
                            );
                          })}
                        </TableRow>
                        
                        {/* New Values Row */}
                        <TableRow>
                          <TableCell className="font-medium sticky left-0 bg-white border-r">New</TableCell>
                          {allColumns.map(column => {
                            const hasChange = changedFields.has(column);
                            const anomaly = anomalies.find(a => a.field === column);
                            return (
                              <TableCell 
                                key={column}
                                className={hasChange ? 'bg-green-50' : ''}
                              >
                                {hasChange ? (
                                  <span className="text-green-600 font-semibold">
                                    {newValues[column]}
                                  </span>
                                ) : (
                                  <span className="text-gray-400">—</span>
                                )}
                              </TableCell>
                            );
                          })}
                        </TableRow>

                        {/* Apply Checkbox Row */}
                        <TableRow>
                          <TableCell className="font-medium sticky left-0 bg-white border-r">Apply</TableCell>
                          {allColumns.map(column => {
                            const anomaly = anomalies.find(a => a.field === column);
                            const hasChange = !!anomaly;
                            const isSelected = anomaly ? selectedFixes.has(`${recordId}-${column}`) : false;
                            
                            return (
                              <TableCell key={column} className={hasChange ? 'bg-yellow-50' : ''}>
                                {hasChange && anomaly && (
                                  <Checkbox
                                    checked={isSelected}
                                    onCheckedChange={() => toggleFix(recordId, column)}
                                    disabled={isLoading}
                                  />
                                )}
                              </TableCell>
                            );
                          })}
                        </TableRow>
                      </TableBody>
                    </Table>
                  </div>

                  {/* Show reason for changes */}
                  <div className="text-sm text-gray-600 space-y-1">
                    {anomalies.map(a => (
                      <div key={a.field} className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs">{a.field}</Badge>
                        <span>→ {a.reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <DialogFooter>
          <div className="flex items-center justify-between w-full">
            <span className="text-sm text-gray-600">
              {selectedFixes.size} change{selectedFixes.size !== 1 ? 's' : ''} selected
            </span>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>
                Cancel
              </Button>
              <Button onClick={handleApply} disabled={isLoading || selectedFixes.size === 0}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Applying...
                  </>
                ) : (
                  `Apply ${selectedFixes.size} Fix${selectedFixes.size !== 1 ? 'es' : ''}`
                )}
              </Button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
