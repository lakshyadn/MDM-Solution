import { useState, useMemo } from 'react';
import { Search, ArrowUpDown, ChevronLeft, ChevronRight, Info } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Discrepancy } from '@/lib/types';

interface DiscrepancyTableProps {
  discrepancies: Discrepancy[];
  onToggleSelect: (id: string) => void;
  onToggleSelectAll: (selected: boolean) => void;
}

type SortField = 'recordId' | 'fieldName' | 'status';
type SortDir = 'asc' | 'desc';

const PAGE_SIZES = [10, 25, 50];

export function DiscrepancyTable({ discrepancies, onToggleSelect, onToggleSelectAll }: DiscrepancyTableProps) {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('recordId');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const filtered = useMemo(() => {
    let result = discrepancies;
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(d =>
        d.recordId.toLowerCase().includes(q) ||
        d.fieldName.toLowerCase().includes(q) ||
        d.givenValue.toLowerCase().includes(q) ||
        d.correctValue.toLowerCase().includes(q)
      );
    }
    if (statusFilter !== 'all') {
      result = result.filter(d => d.status === statusFilter);
    }
    result = [...result].sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      const cmp = String(aVal).localeCompare(String(bVal));
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return result;
  }, [discrepancies, search, statusFilter, sortField, sortDir]);

  const totalPages = Math.ceil(filtered.length / pageSize);
  const paged = filtered.slice(page * pageSize, (page + 1) * pageSize);
  const allPageSelected = paged.length > 0 && paged.every(d => d.selected);

  const toggleSort = (field: SortField) => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('asc'); }
  };

  const statusBadge = (status: Discrepancy['status']) => {
    if (status === 'fixed') return <Badge className="bg-success/15 text-success border-success/30 hover:bg-success/20">Fixed</Badge>;
    if (status === 'anomaly') return <Badge variant="destructive" className="bg-destructive/15 text-destructive border-destructive/30 hover:bg-destructive/20">Anomaly</Badge>;
    return <Badge variant="secondary">Correct</Badge>;
  };

  const SortHeader = ({ field, children }: { field: SortField; children: React.ReactNode }) => (
    <button onClick={() => toggleSort(field)} className="flex items-center gap-1 hover:text-foreground transition-colors">
      {children}
      <ArrowUpDown className="h-3 w-3" />
    </button>
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search records, fields, values..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            className="pl-9"
          />
        </div>
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(0); }}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Filter status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="anomaly">Anomaly</SelectItem>
            <SelectItem value="fixed">Fixed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead className="w-[50px]">
                <Checkbox
                  checked={allPageSelected}
                  onCheckedChange={(checked) => onToggleSelectAll(!!checked)}
                />
              </TableHead>
              <TableHead><SortHeader field="recordId">Record ID</SortHeader></TableHead>
              <TableHead><SortHeader field="fieldName">Field Name</SortHeader></TableHead>
              <TableHead>Given Value</TableHead>
              <TableHead>Correct Value</TableHead>
              <TableHead>Other Master</TableHead>
              <TableHead><SortHeader field="status">Status</SortHeader></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paged.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  No discrepancies found.
                </TableCell>
              </TableRow>
            ) : (
              paged.map((d) => (
                <TableRow key={d.id} className={d.selected ? 'bg-primary/5' : ''}>
                  <TableCell>
                    <Checkbox
                      checked={d.selected}
                      onCheckedChange={() => onToggleSelect(d.id)}
                      disabled={d.status === 'fixed'}
                    />
                  </TableCell>
                  <TableCell className="font-mono text-sm">{d.recordId}</TableCell>
                  <TableCell className="text-sm">{d.fieldName}</TableCell>
                  <TableCell>
                    <span className="bg-value-incorrect px-2 py-0.5 rounded text-sm text-value-incorrect font-mono">
                      {d.givenValue}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="bg-value-correct px-2 py-0.5 rounded text-sm text-value-correct font-mono">
                      {d.correctValue}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="flex items-center gap-1 text-sm text-muted-foreground cursor-help">
                          {d.otherMasterValue || '—'}
                          {d.otherMasterValue && <Info className="h-3 w-3" />}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="text-xs">Value from the other master database</p>
                      </TooltipContent>
                    </Tooltip>
                  </TableCell>
                  <TableCell>{statusBadge(d.status)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Rows per page</span>
          <Select value={String(pageSize)} onValueChange={(v) => { setPageSize(Number(v)); setPage(0); }}>
            <SelectTrigger className="w-[70px] h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PAGE_SIZES.map(s => <SelectItem key={s} value={String(s)}>{s}</SelectItem>)}
            </SelectContent>
          </Select>
          <span className="text-xs text-muted-foreground">
            {filtered.length} result{filtered.length !== 1 ? 's' : ''}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="outline" size="icon" className="h-8 w-8" disabled={page === 0} onClick={() => setPage(p => p - 1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-xs text-muted-foreground px-2">
            {totalPages > 0 ? `${page + 1} / ${totalPages}` : '0 / 0'}
          </span>
          <Button variant="outline" size="icon" className="h-8 w-8" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
