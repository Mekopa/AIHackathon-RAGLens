// src/utils/fileUtils.ts

export function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  }
  
  export function getFileTypeIcon(type: string): string {
    if (type.startsWith('image/')) return 'image';
    if (type.includes('pdf')) return 'pdf';
    if (type.includes('word') || type.includes('document')) return 'word';
    if (type.includes('spreadsheet') || type.includes('excel') || type.includes('csv')) return 'excel';
    if (type.includes('text/plain')) return 'text';
    return 'file';
  }