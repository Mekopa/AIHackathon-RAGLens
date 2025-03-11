// src/components/dochub/ActionBar.tsx

import React from 'react';
import { UploadCloud, FolderPlus } from 'lucide-react';

interface ActionBarProps {
  onUpload: () => void;
  onCreateFolder: () => void;
}

export default function ActionBar({ onUpload, onCreateFolder }: ActionBarProps) {
  return (
    <div className="flex items-center justify-between h-16 px-4 text-text">
      <div className="flex-1"></div>
      
      {/* Center section with main actions */}
      <div className="flex items-center gap-4">
        <button
          onClick={onUpload}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <UploadCloud className="w-5 h-5" />
          <span>Upload</span>
        </button>
        
        <button
          onClick={onCreateFolder}
          className="flex items-center gap-2 px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-800 transition-colors"
        >
          <FolderPlus className="w-5 h-5" />
          <span>New Folder</span>
        </button>
      </div>
      
      <div className="flex-1"></div>
    </div>
  );
}