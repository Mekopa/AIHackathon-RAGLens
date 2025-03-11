// src/hooks/useDocHubActions.ts

import { useCallback } from 'react';
import axiosInstance from '../api/axiosInstance';
import { Folder, Document } from '../types/dochub';

export function useDocHubActions() {
  // FOLDER ACTIONS
  const listFolders = useCallback(async (): Promise<Folder[]> => {
    const response = await axiosInstance.get('/api/dochub/folders/');
    return response.data;
  }, []);

  const createFolder = useCallback(async (data: { name: string; parent?: string | null }): Promise<Folder> => {
    const response = await axiosInstance.post('/api/dochub/folders/', {
      name: data.name,
      parent: data.parent ?? null,
    });
    return response.data;
  }, []);

  const renameFolder = useCallback(async (folderId: string, newName: string): Promise<void> => {
    await axiosInstance.put(`/api/dochub/folders/${folderId}/`, { name: newName });
  }, []);

  const deleteFolder = useCallback(async (folderId: string): Promise<void> => {
    await axiosInstance.delete(`/api/dochub/folders/${folderId}/`);
  }, []);

  // DOCUMENT ACTIONS
  const listDocuments = useCallback(async (): Promise<Document[]> => {
    const response = await axiosInstance.get('/api/dochub/documents/');
    return response.data;
  }, []);

  const uploadDocument = useCallback(async (file: File, folderID?: string | null): Promise<Document> => {
    const formData = new FormData();
    formData.append('name', file.name);
    formData.append('file', file);
    if (folderID) {
      formData.append('folder', folderID);
    }

    const response = await axiosInstance.post('/api/dochub/documents/', formData);
    return response.data;
  }, []);

  const uploadDocuments = useCallback(async (files: File[], folderID?: string | null): Promise<Document[]> => {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    if (folderID) {
      formData.append('folder', folderID);
    }

    try {
      console.log('Sending files:', files.map(f => f.name));
      console.log('To folder:', folderID);
      
      const response = await axiosInstance.post('/api/dochub/documents/bulk_upload/', formData);
      console.log('Upload API response:', response.data);
      
      // Handle the specific response format from your backend
      if (response.data && response.data.documents) {
        return response.data.documents;
      } else if (Array.isArray(response.data)) {
        return response.data;
      } else {
        return [response.data];
      }
    } catch (error) {
      console.error('Error uploading documents:', error);
      throw error;
    }
  }, []);

  const deleteDocument = useCallback(async (documentId: string): Promise<void> => {
    await axiosInstance.delete(`/api/dochub/documents/${documentId}/`);
  }, []);

  const renameDocument = useCallback(async (documentId: string, newName: string): Promise<void> => {
    await axiosInstance.put(`/api/dochub/documents/${documentId}/`, { name: newName });
  }, []);

  // Get document status (for tracking processing status)
  const getDocumentStatus = useCallback(async (documentId: string): Promise<Document> => {
    const response = await axiosInstance.get(`/api/dochub/documents/${documentId}/`);
    return response.data;
  }, []);

  return {
    // Folder actions
    listFolders,
    createFolder,
    renameFolder,
    deleteFolder,

    // Document actions
    listDocuments,
    uploadDocument,
    uploadDocuments,
    deleteDocument,
    renameDocument,
    getDocumentStatus
  };
}