import { useCallback, useRef } from 'react';
import { Upload, CheckCircle2, AlertCircle, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { UploadedFile } from '@/lib/types';

interface FileUploaderProps {
  label: string;
  description: string;
  file: UploadedFile | null;
  onFileSelect: (file: File) => void;
  accept?: string;
}

export function FileUploader({ label, description, file, onFileSelect, accept = '.csv,.json' }: FileUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) onFileSelect(droppedFile);
  }, [onFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const statusIcon = () => {
    if (!file) return <Upload className="h-8 w-8 text-muted-foreground" />;
    if (file.status === 'uploading') return <FileText className="h-8 w-8 text-primary animate-pulse" />;
    if (file.status === 'success') return <CheckCircle2 className="h-8 w-8 text-success" />;
    if (file.status === 'error') return <AlertCircle className="h-8 w-8 text-destructive" />;
    return <Upload className="h-8 w-8 text-muted-foreground" />;
  };

  return (
    <Card className="border-2 border-dashed hover:border-primary/50 transition-colors">
      <CardContent className="p-4">
        <div
          className="flex flex-col items-center gap-3 cursor-pointer"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onClick={() => inputRef.current?.click()}
        >
          {statusIcon()}
          <div className="text-center">
            <p className="text-sm font-semibold">{label}</p>
            <p className="text-xs text-muted-foreground">{description}</p>
          </div>

          {file?.status === 'uploading' && (
            <div className="w-full space-y-1">
              <Progress value={file.progress} className="h-1.5" />
              <p className="text-xs text-muted-foreground text-center">{file.progress}%</p>
            </div>
          )}

          {file?.status === 'success' && (
            <div className="flex items-center gap-2 rounded-md bg-success/10 px-3 py-1.5">
              <FileText className="h-3.5 w-3.5 text-success" />
              <span className="text-xs font-medium text-success">{file.name}</span>
              <span className="text-xs text-muted-foreground">({file.data.length} records)</span>
            </div>
          )}

          {file?.status === 'error' && (
            <p className="text-xs text-destructive">Upload failed. Try again.</p>
          )}

          {(!file || file.status === 'error') && (
            <Button variant="outline" size="sm" className="text-xs">
              Choose File
            </Button>
          )}

          <input
            ref={inputRef}
            type="file"
            accept={accept}
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onFileSelect(f);
              e.target.value = '';
            }}
          />
        </div>
      </CardContent>
    </Card>
  );
}
