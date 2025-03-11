// src/components/dochub/TopNavigation.tsx

import React from 'react';
import { ChevronLeft, Home } from 'lucide-react';
import { Folder } from '../../types/dochub';

interface TopNavigationProps {
  currentFolder: Folder | null;
  folderPath: Folder[];
  onBack: () => void;
  onNavigateToFolder: (folderId: string | null) => void;
}

export default function TopNavigation({ 
  currentFolder, 
  folderPath,
  onBack, 
  onNavigateToFolder
}: TopNavigationProps) {
  return (
    <div className="flex items-center h-12 px-4 text-text border-b border-gray-700">
      <div className="flex items-center overflow-x-auto">
        <button
          onClick={() => onNavigateToFolder(null)}
          className="p-2 rounded hover:bg-gray-700 transition-colors flex-shrink-0"
          title="Home"
        >
          <Home className="w-4 h-4" />
        </button>
        
        {folderPath.length > 0 && (
          <div className="flex items-center">
            {folderPath.map((folder, index) => (
              <React.Fragment key={folder.id}>
                <span className="mx-2 text-gray-500">/</span>
                <button
                  onClick={() => onNavigateToFolder(folder.id)}
                  className="hover:text-blue-400 transition-colors truncate max-w-xs"
                >
                  {folder.name}
                </button>
              </React.Fragment>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}