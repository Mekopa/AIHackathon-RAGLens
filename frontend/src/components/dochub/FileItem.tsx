// src/components/dochub/FileItem.tsx

import React from 'react';
import { Folder, MoreVertical, Edit, Trash, Download, AlertCircle, Loader } from 'lucide-react';
import FileTypeIcon from './FileIcon';
import { Document, Folder as FolderType } from '../../types/dochub';
import { formatFileSize } from '../../utils/fileUtils';

interface FileItemProps {
  item: Document | FolderType;
  isFolder: boolean;
  isSelected: boolean;
  onClick: () => void;
  onRename?: (id: string, newName: string) => void;
  onDelete?: (id: string) => void;
  onDownload?: (url: string, name: string) => void;
}

export default function FileItem({
  item,
  isFolder,
  isSelected,
  onClick,
  onRename,
  onDelete,
  onDownload
}: FileItemProps) {
  const [showDropdown, setShowDropdown] = React.useState(false);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  // Determine if the document is processing
  const isProcessing = !isFolder && (item as Document).status === 'processing';
  
  // Determine if the document has an error
  const hasError = !isFolder && (item as Document).status === 'error';

  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleMoreClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowDropdown(!showDropdown);
  };

  const handleRename = () => {
    const newName = prompt('Enter new name:', item.name);
    if (newName && newName !== item.name && onRename) {
      onRename(item.id, newName);
    }
    setShowDropdown(false);
  };

  const handleDelete = () => {
    if (window.confirm(`Are you sure you want to delete "${item.name}"?`) && onDelete) {
      onDelete(item.id);
    }
    setShowDropdown(false);
  };

  const handleDownload = () => {
    if (!isFolder && 'url' in item && onDownload) {
      onDownload(item.url, item.name);
    }
    setShowDropdown(false);
  };

  return (
    <div
      className={`group flex flex-col items-center p-4 rounded-xl transition-all duration-200 cursor-pointer w-[180px] ${
        isSelected ? 'bg-blue-500/10' : 'hover:bg-gray-100/10'
      }`}
      onClick={onClick}
    >
      {/* Processing Indicator */}
      {isProcessing && (
        <div className="absolute top-2 left-2">
          <div className="flex items-center p-1 bg-blue-500/20 rounded-full">
            <Loader className="w-4 h-4 text-blue-500 animate-spin" />
          </div>
        </div>
      )}
      
      {/* Error Indicator */}
      {hasError && (
        <div className="absolute top-2 left-2">
          <div className="flex items-center p-1 bg-red-500/20 rounded-full" title={(item as Document).error_message || 'Error processing file'}>
            <AlertCircle className="w-4 h-4 text-red-500" />
          </div>
        </div>
      )}

      {/* Menu Button */}
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={handleMoreClick}
          className="p-1 rounded-lg hover:bg-gray-200/10 text-gray-400 hover:text-white"
        >
          <MoreVertical className="w-4 h-4" />
        </button>
        
        {showDropdown && (
          <div ref={dropdownRef} className="absolute right-0 mt-1 w-40 bg-gray-800 rounded-lg shadow-lg border border-gray-700 overflow-hidden z-10">
            <button
              onClick={handleRename}
              className="w-full px-4 py-2 text-left text-sm flex items-center gap-2 hover:bg-gray-700"
            >
              <Edit className="w-4 h-4" />
              <span>Rename</span>
            </button>
            
            {!isFolder && (
              <button
                onClick={handleDownload}
                className="w-full px-4 py-2 text-left text-sm flex items-center gap-2 hover:bg-gray-700"
              >
                <Download className="w-4 h-4" />
                <span>Download</span>
              </button>
            )}
            
            <button
              onClick={handleDelete}
              className="w-full px-4 py-2 text-left text-sm text-red-400 flex items-center gap-2 hover:bg-red-500/10"
            >
              <Trash className="w-4 h-4" />
              <span>Delete</span>
            </button>
          </div>
        )}
      </div>

      {/* Icon */}
      <div className={`p-4 mb-3 rounded-xl ${
        isFolder 
          ? 'bg-blue-500/10' 
          : (isProcessing ? 'bg-blue-500/10 animate-pulse' :
             hasError ? 'bg-red-500/10' : 'bg-gray-500/10')
      }`}>
        {isFolder ? (
          <Folder className="w-8 h-8 text-blue-500" />
        ) : (
          <FileTypeIcon 
            type={(item as Document).file_type} 
            className={`w-8 h-8 ${isProcessing ? 'text-blue-400' : 
                                  hasError ? 'text-red-400' : 'text-gray-400'}`} 
            size={32} 
          />
        )}
      </div>

      {/* Name and Info */}
      <div className="w-full text-center">
        <h4 className="font-medium text-white truncate">{item.name}</h4>
        {isFolder ? (
          <p className="text-sm text-gray-400">
            {(item as FolderType).document_count ?? 0} items
          </p>
        ) : (
          <div>
            <p className="text-sm text-gray-400">
              {formatFileSize((item as Document).size)}
            </p>
            {/* Status message */}
            {isProcessing && (
              <p className="text-xs text-blue-400 mt-1">Processing...</p>
            )}
            {hasError && (
              <p className="text-xs text-red-400 mt-1">Error</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}