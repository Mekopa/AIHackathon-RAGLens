// src/pages/DocHubPage.tsx

import React, { useState, useCallback } from 'react';
import { useDocHubStructure } from '../hooks/useDocHubStructure';
import ActionBar from '../components/dochub/ActionBar';
import TopNavigation from '../components/dochub/TopNavigation';
import DocHubGrid from '../components/dochub/DocHubGrid';
import CreateFolderModal from '../components/dochub/CreateFolderModal';
import UploadDocumentModal from '../components/dochub/UploadDocumentModal';

export default function DocHubPage() {
  // UI state
  const [showCreateFolder, setShowCreateFolder] = useState(false);
  const [showUploadDocument, setShowUploadDocument] = useState(false);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());

  // Initialize DocHub structure hook
  const {
    folders,
    documents,
    currentPath,
    isLoading,
    error,
    getCurrentFolder,
    getChildFolders,
    getFolderDocuments,
    navigateToFolder,
    createFolderInCurrent,
    uploadDocumentsToCurrent,
    deleteDocumentById,
    deleteFolderById,
    renameDocumentById,
    renameFolderById,
  } = useDocHubStructure();

  // Get current state
  const currentFolder = getCurrentFolder();
  const childFolders = getChildFolders(currentFolder?.id || null);
  const folderDocuments = getFolderDocuments(currentFolder?.id || null);
  
  // Build folder path for breadcrumbs
  const folderPath = currentPath.map(id => 
    folders.find(f => f.id === id)
  ).filter(Boolean) as Array<typeof folders[0]>;
  
  // Modal handlers
  const handleCreateFolder = () => setShowCreateFolder(true);
  const handleUploadDocument = () => setShowUploadDocument(true);

  // Handler for selection changes
  const handleSelectionChange = useCallback((newSelection: Set<string>) => {
    setSelectedItems(newSelection);
  }, []);

  // Handler for navigation
  const handleNavigateToFolder = useCallback((folderId: string) => {
    navigateToFolder(folderId);
    setSelectedItems(new Set());
  }, [navigateToFolder]);

  // Handler for going back
  const handleBack = useCallback(() => {
    if (currentPath.length > 1) {
      // If in a subfolder, go up one level
      navigateToFolder(currentPath[currentPath.length - 2]);
    } else {
      // If in a root folder, go to root (null)
      navigateToFolder(null);
    }
    setSelectedItems(new Set());
  }, [currentPath, navigateToFolder]);

  // Handler for creating a folder
  const handleConfirmCreateFolder = async (name: string) => {
    await createFolderInCurrent(name);
    setShowCreateFolder(false);
  };

  // Handler for uploading documents
  const handleConfirmUploadDocuments = async (files: File[]) => {
    await uploadDocumentsToCurrent(files);
    setShowUploadDocument(false);
  };

  // Handler for renaming items
  const handleRename = async (id: string, newName: string, isFolder: boolean) => {
    if (isFolder) {
      await renameFolderById(id, newName);
    } else {
      await renameDocumentById(id, newName);
    }
  };

  // Handler for deleting items
  const handleDelete = async (id: string, isFolder: boolean) => {
    if (isFolder) {
      await deleteFolderById(id);
    } else {
      await deleteDocumentById(id);
    }
    // Clear selection after delete
    setSelectedItems(prev => {
      const newSelection = new Set(prev);
      newSelection.delete(id);
      return newSelection;
    });
  };

  // Handler for downloading files
  const handleDownload = (url: string, name: string) => {
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-900">
      {/* Header and Navigation */}
      <div className="flex-none">
        <ActionBar
          onUpload={handleUploadDocument}
          onCreateFolder={handleCreateFolder}
        />
        <TopNavigation
          currentFolder={currentFolder}
          folderPath={folderPath}
          onBack={handleBack}
          onNavigateToFolder={navigateToFolder}
        />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full text-red-500">
            <p>Error: {error}</p>
            <button 
              onClick={() => window.location.reload()} 
              className="mt-4 px-4 py-2 bg-gray-800 text-white rounded hover:bg-gray-700 transition-colors"
            >
              Reload
            </button>
          </div>
        ) : (
          <DocHubGrid
            folders={childFolders}
            documents={folderDocuments}
            selectedItems={selectedItems}
            onSelectionChange={handleSelectionChange}
            onNavigateToFolder={handleNavigateToFolder}
            onRename={handleRename}
            onDelete={handleDelete}
            onDownload={handleDownload}
          />
        )}
      </div>

      {/* Modals */}
      <CreateFolderModal
        isOpen={showCreateFolder}
        onClose={() => setShowCreateFolder(false)}
        onCreate={handleConfirmCreateFolder}
        currentFolder={currentFolder?.id || null}
      />
      
      <UploadDocumentModal
        isOpen={showUploadDocument}
        onClose={() => setShowUploadDocument(false)}
        onUpload={handleConfirmUploadDocuments}
        currentFolder={currentFolder?.id || null}
      />
    </div>
  );
}