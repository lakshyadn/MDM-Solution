import { Database, AlertTriangle, CheckCircle2, FileWarning } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

interface SummaryPanelProps {
  totalRecords: number;
  totalAnomalies: number;
  totalSelected: number;
  totalFixed: number;
}

const stats = [
  { key: 'totalRecords', label: 'Total Records', icon: Database, color: 'text-primary' },
  { key: 'totalAnomalies', label: 'Anomalies Detected', icon: AlertTriangle, color: 'text-destructive' },
  { key: 'totalSelected', label: 'Fixes Selected', icon: FileWarning, color: 'text-warning' },
  { key: 'totalFixed', label: 'Applied Fixes', icon: CheckCircle2, color: 'text-success' },
] as const;

export function SummaryPanel({ totalRecords, totalAnomalies, totalSelected, totalFixed }: SummaryPanelProps) {
  const values = { totalRecords, totalAnomalies, totalSelected, totalFixed };

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map(({ key, label, icon: Icon, color }) => (
        <Card key={key}>
          <CardContent className="flex items-center gap-4 p-4">
            <div className={`rounded-lg bg-secondary p-2.5 ${color}`}>
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-2xl font-bold font-mono">{values[key]}</p>
              <p className="text-xs text-muted-foreground">{label}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
