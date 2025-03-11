// src/components/dochub/CreateFolderModal.tsx

import React, { useState } from 'react';
import { X } from 'lucide-react';

interface CreateFolderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (name: string) => Promise<void>;
  currentFolder: string | null;
}

export default function CreateFolderModal({
  isOpen,
  onClose,
  onCreate,
  currentFolder
}: CreateFolderModalProps) {
  const [folderName, setFolderName] = useState('New Folder');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!folderName.trim()) {
      setError('Folder name cannot be empty');
      return;
    }
    
    setIsCreating(true);
    setError('');
    
    try {
      await onCreate(folderName);
      onClose();
    } catch (err) {
      setError('Failed to create folder');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-gray-800 rounded-lg max-w-md w-full shadow-lg">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-xl font-semibold text-white">Create New Folder</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-700 rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>
        
        <form onSubmit={handleCreate} className="p-4">
          <div className="mb-4">
            <label htmlFor="folderName" className="block text-sm font-medium text-gray-400 mb-2">
              Folder Name
            </label>
            <input
              type="text"
              id="folderName"
              value={folderName}
              onChange={(e) => setFolderName(e.target.value)}
              className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
            {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
          </div>
          
          {currentFolder && (
            <div className="mb-4">
              <p className="text-sm text-gray-400">
                This folder will be created in the current location.
              </p>
            </div>
          )}
          
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-300 hover:bg-gray-700 rounded transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isCreating}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {isCreating ? 'Creating...' : 'Create Folder'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}