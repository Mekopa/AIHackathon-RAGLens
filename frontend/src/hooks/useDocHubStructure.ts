// src/hooks/useDocHubStructure.ts

import { useState, useEffect, useCallback, useRef } from 'react';
import { useDocHubActions } from './useDocHubActions';
import { Folder, Document, DocumentStatus } from '../types/dochub';

// Define constants for status checking
const STATUS_CHECK_INTERVAL = 3000; // 3 seconds
const MAX_RETRY_COUNT = 20; // About 1 minute total (20 * 3s)

export function useDocHubStructure() {
  // States
  const [folders, setFolders] = useState<Folder[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [currentPath, setCurrentPath] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Ref to track documents being processed
  const processingDocuments = useRef<DocumentStatus>({});

  // Actions
  const {
    listFolders,
    listDocuments,
    createFolder,
    uploadDocuments,
    deleteDocument,
    deleteFolder,
    renameDocument,
    renameFolder,
    getDocumentStatus,
  } = useDocHubActions();

  // Clean up intervals when component unmounts
  useEffect(() => {
    return () => {
      // Clear all status check intervals
      Object.values(processingDocuments.current).forEach(doc => {
        if (doc.checkInterval) {
          clearInterval(doc.checkInterval);
        }
      });
    };
  }, []);

  // Fetch folders and documents on mount
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        // Fetch both folders and documents
        const [foldersResponse, documentsResponse] = await Promise.all([
          listFolders(),
          listDocuments()
        ]);
        
        // Debug logging to see what the API is returning
        console.log('Folders Response:', foldersResponse);
        console.log('Documents Response:', documentsResponse);
        
        // Ensure we handle different API response formats
        const foldersData = Array.isArray(foldersResponse) ? foldersResponse : 
                          (foldersResponse.results || foldersResponse.data || []);
        
        const documentsData = Array.isArray(documentsResponse) ? documentsResponse : 
                            (documentsResponse.results || documentsResponse.data || []);
        
        setFolders(foldersData);
        setDocuments(documentsData);
        
        // Check for any processing documents and start tracking them
        documentsData.forEach(doc => {
          if (doc.status === 'processing') {
            startStatusTracking(doc.id);
          }
        });
      } catch (err) {
        console.error('Error fetching data:', err);
        setError('Failed to fetch data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [listFolders, listDocuments]);

  // Function to start tracking document status
  const startStatusTracking = useCallback((documentId: string) => {
    // Skip if already tracking
    if (processingDocuments.current[documentId]) {
      return;
    }
    
    console.log(`Starting status tracking for document ${documentId}`);
    
    // Set up interval to check document status
    const checkInterval = setInterval(async () => {
      try {
        // Get current tracking info
        const tracking = processingDocuments.current[documentId];
        if (!tracking) return;
        
        // If we've reached max retries, stop checking
        if (tracking.retryCount >= MAX_RETRY_COUNT) {
          console.warn(`Max retries reached for document ${documentId}`);
          clearInterval(tracking.checkInterval!);
          processingDocuments.current[documentId].checkInterval = null;
          return;
        }
        
        // Increment retry count
        processingDocuments.current[documentId].retryCount++;
        
        // Get updated document status
        const updatedDoc = await getDocumentStatus(documentId);
        console.log(`Document ${documentId} status: ${updatedDoc.status}`);
        
        // Update document in state
        setDocuments(prev => prev.map(doc => 
          doc.id === documentId ? updatedDoc : doc
        ));
        
        // If document is no longer processing, stop checking
        if (updatedDoc.status !== 'processing') {
          console.log(`Document ${documentId} processing complete`);
          clearInterval(tracking.checkInterval!);
          delete processingDocuments.current[documentId];
        }
      } catch (err) {
        console.error(`Error checking status for document ${documentId}:`, err);
      }
    }, STATUS_CHECK_INTERVAL);
    
    // Store interval and retry count
    processingDocuments.current[documentId] = {
      checkInterval,
      retryCount: 0
    };
  }, [getDocumentStatus]);

  // Get current folder
  const getCurrentFolder = useCallback((): Folder | null => {
    if (currentPath.length === 0) return null;
    const currentFolderId = currentPath[currentPath.length - 1];
    return folders.find(folder => folder.id === currentFolderId) || null;
  }, [currentPath, folders]);

  // Get subfolders of current folder
  const getChildFolders = useCallback((parentId: string | null): Folder[] => {
    if (!Array.isArray(folders)) {
      console.error('folders is not an array:', folders);
      return [];
    }
    return folders.filter(folder => folder.parent === parentId);
  }, [folders]);

  // Get documents in current folder
  const getFolderDocuments = useCallback((folderId: string | null): Document[] => {
    if (!Array.isArray(documents)) {
      console.error('documents is not an array:', documents);
      return [];
    }
    return documents.filter(doc => doc.folder === folderId);
  }, [documents]);

  // Navigate to folder
  const navigateToFolder = useCallback((folderId: string | null) => {
    if (!folderId) {
      setCurrentPath([]);
      return;
    }

    // Build path from root to folder
    const path: string[] = [];
    let current: Folder | undefined = folders.find(f => f.id === folderId);
    
    while (current) {
      path.unshift(current.id);
      if (current.parent) {
        current = folders.find(f => f.id === current?.parent);
      } else {
        break;
      }
    }
    
    setCurrentPath(path);
  }, [folders]);

  // Create folder in current location
  const createFolderInCurrent = async (name: string) => {
    const parentFolder = getCurrentFolder();
    const parentId = parentFolder?.id ?? null;

    setIsLoading(true);
    setError(null);
    try {
      const newFolder = await createFolder({ name, parent: parentId });
      setFolders(prev => [...prev, newFolder]);
      return newFolder;
    } catch (err) {
      console.error('Error creating folder:', err);
      setError('Failed to create folder');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  // Upload documents to current folder
  const uploadDocumentsToCurrent = async (files: File[]) => {
    const currentFolder = getCurrentFolder();
    const folderId = currentFolder?.id ?? null;

    setIsLoading(true);
    setError(null);
    try {
      const uploadedDocs = await uploadDocuments(files, folderId);
      console.log('Uploaded documents:', uploadedDocs);
      
      // Start status tracking for each uploaded document
      uploadedDocs.forEach(doc => {
        if (doc.status === 'processing') {
          startStatusTracking(doc.id);
        }
      });

      // Update documents state with new documents
      setDocuments(prev => [...prev, ...uploadedDocs]);
      return uploadedDocs;
    } catch (err) {
      console.error('Error uploading documents:', err);
      setError('Failed to upload documents');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  // Delete document
  const deleteDocumentById = async (documentId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await deleteDocument(documentId);
      
      // Remove any status tracking for this document
      if (processingDocuments.current[documentId]) {
        clearInterval(processingDocuments.current[documentId].checkInterval!);
        delete processingDocuments.current[documentId];
      }
      
      setDocuments(prev => prev.filter(doc => doc.id !== documentId));
    } catch (err) {
      console.error('Error deleting document:', err);
      setError('Failed to delete document');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  // Delete folder
  const deleteFolderById = async (folderId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await deleteFolder(folderId);
      setFolders(prev => prev.filter(folder => folder.id !== folderId));
      
      // If we're in the deleted folder, navigate to parent or root
      if (currentPath.includes(folderId)) {
        const folderIndex = currentPath.indexOf(folderId);
        if (folderIndex === 0) {
          // If it's the root folder of our path, go to root
          navigateToFolder(null);
        } else {
          // Otherwise, go to parent
          navigateToFolder(currentPath[folderIndex - 1]);
        }
      }
    } catch (err) {
      console.error('Error deleting folder:', err);
      setError('Failed to delete folder');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  // Rename document
  const renameDocumentById = async (documentId: string, newName: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await renameDocument(documentId, newName);
      setDocuments(prev => 
        prev.map(doc => doc.id === documentId ? { ...doc, name: newName } : doc)
      );
    } catch (err) {
      console.error('Error renaming document:', err);
      setError('Failed to rename document');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  // Rename folder
  const renameFolderById = async (folderId: string, newName: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await renameFolder(folderId, newName);
      setFolders(prev => 
        prev.map(folder => folder.id === folderId ? { ...folder, name: newName } : folder)
      );
    } catch (err) {
      console.error('Error renaming folder:', err);
      setError('Failed to rename folder');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    // State
    folders,
    documents,
    currentPath,
    isLoading,
    error,
    
    // Getters
    getCurrentFolder,
    getChildFolders,
    getFolderDocuments,
    
    // Navigation
    navigateToFolder,
    
    // Actions
    createFolderInCurrent,
    uploadDocumentsToCurrent,
    deleteDocumentById,
    deleteFolderById,
    renameDocumentById,
    renameFolderById,
  };
}