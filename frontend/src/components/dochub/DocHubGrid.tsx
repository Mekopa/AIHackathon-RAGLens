// src/components/dochub/DocHubGrid.tsx

import React from 'react';
import FileItem from './FileItem';
import { Document, Folder } from '../../types/dochub';

interface DocHubGridProps {
  folders: Folder[];
  documents: Document[];
  selectedItems: Set<string>;
  onSelectionChange: (newSelection: Set<string>) => void;
  onNavigateToFolder: (folderId: string) => void;
  onRename?: (id: string, newName: string, isFolder: boolean) => void;
  onDelete?: (id: string, isFolder: boolean) => void;
  onDownload?: (url: string, name: string) => void;
}

export default function DocHubGrid({
  folders,
  documents,
  selectedItems,
  onSelectionChange,
  onNavigateToFolder,
  onRename,
  onDelete,
  onDownload
}: DocHubGridProps) {
  const [lastClickedItem, setLastClickedItem] = React.useState<string | null>(null);
  const [lastClickTime, setLastClickTime] = React.useState<number>(0);

  const handleItemClick = (id: string, isFolder: boolean) => {
    const now = Date.now();
    const isDoubleClick = id === lastClickedItem && now - lastClickTime < 400;

    // Update last click info
    setLastClickedItem(id);
    setLastClickTime(now);

    // If double-clicking a folder, navigate into it
    if (isDoubleClick && isFolder) {
      onNavigateToFolder(id);
      return;
    }

    // Update selection
    onSelectionChange(new Set([id]));
  };

  const handleRename = (id: string, newName: string) => {
    if (onRename) {
      const isFolder = folders.some(folder => folder.id === id);
      onRename(id, newName, isFolder);
    }
  };

  const handleDelete = (id: string) => {
    if (onDelete) {
      const isFolder = folders.some(folder => folder.id === id);
      onDelete(id, isFolder);
    }
  };

  // Combine items and sort: folders first, then documents, both alphabetically
  const allItems = [
    ...folders.map(folder => ({ ...folder, itemType: 'folder' as const })),
    ...documents.map(doc => ({ ...doc, itemType: 'document' as const }))
  ].sort((a, b) => {
    // Folders first
    if (a.itemType !== b.itemType) {
      return a.itemType === 'folder' ? -1 : 1;
    }
    // Then alphabetical by name
    return a.name.localeCompare(b.name);
  });

  if (allItems.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <p>No items found</p>
        <p className="text-sm">Upload documents or create folders to get started</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4 p-4">
      {allItems.map(item => (
        <FileItem
          key={item.id}
          item={item.itemType === 'folder' ? item : item}
          isFolder={item.itemType === 'folder'}
          isSelected={selectedItems.has(item.id)}
          onClick={() => handleItemClick(item.id, item.itemType === 'folder')}
          onRename={handleRename}
          onDelete={handleDelete}
          onDownload={onDownload}
        />
      ))}
    </div>
  );
}