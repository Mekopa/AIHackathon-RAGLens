// src/types/dochub.ts

export interface Folder {
    id: string;
    name: string;
    parent: string | null;
    created_at: string;
    updated_at: string;
    document_count?: number;
    subfolder_count?: number;
  }
  
  export interface Document {
    id: string;
    name: string;
    file: string;
    url: string;
    folder: string | null;
    file_type: string;
    size: number;
    status: 'processing' | 'ready' | 'error';
    error_message?: string;
    created_at: string;
    updated_at: string;
  }
  
  // Add a type to track documents being processed
  export interface DocumentStatus {
    [documentId: string]: {
      checkInterval: NodeJS.Timeout | null;
      retryCount: number;
    }
  }