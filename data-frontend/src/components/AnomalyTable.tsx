import React, { useState, useEffect } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { ReviewChangesModal } from '@/components/ReviewChangesModal';
import type { Anomaly, ApplyFixesPayload } from '@/lib/api';
import { dataDiscrepancyAPI } from '@/lib/api';

interface AnomalyTableProps {
  anomalies: Anomaly[];
  onFixesSelected: (fixes: ApplyFixesPayload[]) => void;
  isLoading?: boolean;
  preferredMaster: 'master1' | 'master2';
}

interface RecordData {
  [key: string]: string | number | boolean | null | undefined;
}

export const AnomalyTable: React.FC<AnomalyTableProps> = ({
  anomalies,
  onFixesSelected,
  isLoading = false,
  preferredMaster,
}) => {
  const [selectedFixes, setSelectedFixes] = useState<Set<string>>(new Set());
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [reasonFilter, setReasonFilter] = useState<string>('all');
  const [recordsData, setRecordsData] = useState<Record<number, RecordData>>({});
  const [masterRecordsData, setMasterRecordsData] = useState<Record<number, RecordData>>({});

  // Clear selections when anomalies change (after fixes are applied)
  useEffect(() => {
    setSelectedFixes(new Set());
  }, [anomalies.length]);

  // Fetch complete record data
  useEffect(() => {
    const fetchRecords = async () => {
      try {
        // Fetch given data
        const givenData = await dataDiscrepancyAPI.getData('given');
        const givenRecordsMap: Record<number, RecordData> = {};
        
        givenData.forEach((record: RecordData) => {
          const recordId = record.id || record.record_id;
          if (recordId !== undefined && typeof recordId === 'number') {
            givenRecordsMap[recordId] = record;
          }
        });
        
        setRecordsData(givenRecordsMap);

        // Fetch preferred master data
        const masterData = await dataDiscrepancyAPI.getData(preferredMaster);
        const masterRecordsMap: Record<number, RecordData> = {};
        
        masterData.forEach((record: RecordData) => {
          const recordId = record.id || record.record_id;
          if (recordId !== undefined && typeof recordId === 'number') {
            masterRecordsMap[recordId] = record;
          }
        });
        
        setMasterRecordsData(masterRecordsMap);
      } catch (err) {
        console.error('Failed to fetch record data:', err);
      }
    };

    if (anomalies.length > 0) {
      fetchRecords();
    }
  }, [anomalies.length, preferredMaster]);

  if (anomalies.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No discrepancies found!</p>
      </div>
    );
  }

  const getFixKey = (recordId: number, field: string) => `${recordId}-${field}`;

  const handleCheckboxChange = (anomaly: Anomaly) => {
    const key = getFixKey(anomaly.record_id, anomaly.field);
    const newSelected = new Set(selectedFixes);

    if (newSelected.has(key)) {
      newSelected.delete(key);
    } else {
      newSelected.add(key);
    }
    setSelectedFixes(newSelected);
  };

  const handleReviewChanges = () => {
    setReviewModalOpen(true);
  };

  const handleApplyFixes = (fixes: ApplyFixesPayload[]) => {
    onFixesSelected(fixes);
    setSelectedFixes(new Set());
    setReviewModalOpen(false);
  };

  const getSelectedAnomalies = (): Anomaly[] => {
    return anomalies.filter((anomaly) =>
      selectedFixes.has(getFixKey(anomaly.record_id, anomaly.field))
    );
  };

  const normalizeReason = (reason: string) =>
    reason
      .replace(/\s*\(confidence:\s*[^)]+\)/i, '')
      .replace(/\s+/g, ' ')
      .trim();

  const reasonOptions = Array.from(
    new Set(anomalies.map((anomaly) => normalizeReason(anomaly.reason)))
  ).sort();

  const reasonFilteredAnomalies = reasonFilter === 'all'
    ? anomalies
    : anomalies.filter((anomaly) => normalizeReason(anomaly.reason) === reasonFilter);

  const query = searchQuery.trim().toLowerCase();
  const filteredAnomalies = query
    ? reasonFilteredAnomalies.filter((anomaly) => {
        const haystack = [
          String(anomaly.record_id),
          anomaly.record_identifier || '',
          anomaly.field,
          anomaly.given_value,
          anomaly.correct_value,
          normalizeReason(anomaly.reason),
        ]
          .join(' ')
          .toLowerCase();

        return haystack.includes(query);
      })
    : reasonFilteredAnomalies;

  return (
    <TooltipProvider>
      <div className="w-full space-y-4">
        <div className="flex items-center justify-between gap-3">
          <Input
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Search"
            className="w-[260px]"
          />

          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-700">Filter by Reason Type</span>
            <Select value={reasonFilter} onValueChange={setReasonFilter}>
              <SelectTrigger className="w-[240px]">
                <SelectValue placeholder="All Reason Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Reason Types</SelectItem>
                {reasonOptions.map((reason) => (
                  <SelectItem key={reason} value={reason}>{reason}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow className="bg-gray-50">
                <TableHead className="w-12">Fix</TableHead>
                <TableHead>Record ID</TableHead>
                <TableHead>Record Name</TableHead>
                <TableHead>Field</TableHead>
                <TableHead className="text-red-600">Given Value</TableHead>
                <TableHead className="text-green-600">Preferred Master Database</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead>Secondary Master Database</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAnomalies.map((anomaly, index) => {
                const recordData = recordsData[anomaly.record_id];
                const masterRecordData = masterRecordsData[anomaly.record_id];
                const secondaryValues = anomaly.recommendations.length > 0
                  ? anomaly.recommendations
                  : anomaly.secondary_reference
                    ? [anomaly.secondary_reference]
                    : [];
                
                return (
                  <Tooltip key={index}>
                    <TooltipTrigger asChild>
                      <TableRow className="hover:bg-gray-50 cursor-pointer">
                        <TableCell>
                          <Checkbox
                            checked={selectedFixes.has(getFixKey(anomaly.record_id, anomaly.field))}
                            onCheckedChange={() => handleCheckboxChange(anomaly)}
                            disabled={isLoading}
                          />
                        </TableCell>
                        <TableCell className="font-medium">{anomaly.record_id}</TableCell>
                        <TableCell className="font-medium text-blue-600">
                          {anomaly.record_identifier || '—'}
                        </TableCell>
                        <TableCell>{anomaly.field}</TableCell>
                        <TableCell className="text-red-600 font-semibold">
                          {anomaly.given_value}
                        </TableCell>
                        <TableCell className="text-green-600 font-semibold">
                          {anomaly.correct_value}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{anomaly.reason}</Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-600">
                          {secondaryValues.length > 0 ? (
                            <div className="space-y-1">
                              {secondaryValues.map((rec, i) => (
                                <div key={i} className="text-xs bg-blue-50 px-2 py-1 rounded">
                                  • {rec}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <span className="text-gray-400">None</span>
                          )}
                        </TableCell>
                      </TableRow>
                    </TooltipTrigger>
                    {(recordData || masterRecordData) && (
                      <TooltipContent side="top" className="max-w-[400px] p-4 max-h-96 overflow-auto">
                        <div className="space-y-3">
                          <p className="font-semibold text-sm border-b pb-2 mb-3">Complete Record Data</p>
                          
                          <div className="space-y-1">
                            {/* Column headers */}
                            <div className="grid grid-cols-3 gap-3 text-xs font-semibold border-b pb-1">
                              <div className="w-28">Field</div>
                              <div className="text-red-600">Given Database</div>
                              <div className="text-green-600">Preferred Master</div>
                            </div>
                            
                            {/* Data rows */}
                            {recordData && Object.keys(recordData).map((key) => (
                              <div key={key} className="grid grid-cols-3 gap-3 text-xs py-0.5">
                                <div className="font-medium text-gray-700 w-28 truncate" title={key}>{key}</div>
                                <div className="text-gray-600 break-words">{String(recordData[key])}</div>
                                <div className="text-gray-600 break-words">{masterRecordData ? String(masterRecordData[key]) : '—'}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </TooltipContent>
                    )}
                  </Tooltip>
                );
              })}
            </TableBody>
          </Table>
        </div>

        {selectedFixes.size > 0 && (
          <div className="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg p-4">
            <span className="text-sm font-medium text-blue-900">
              {selectedFixes.size} fix{selectedFixes.size !== 1 ? 'es' : ''} selected
            </span>

            <Button onClick={handleReviewChanges} disabled={isLoading}>
              Review Changes
            </Button>
          </div>
        )}

        <ReviewChangesModal
          open={reviewModalOpen}
          onOpenChange={setReviewModalOpen}
          selectedAnomalies={getSelectedAnomalies()}
          onApplyFixes={handleApplyFixes}
          isLoading={isLoading}
        />
      </div>
    </TooltipProvider>
  );
};
