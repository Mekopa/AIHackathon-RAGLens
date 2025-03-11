// src/components/dochub/UploadDocumentModal.tsx

import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { X, UploadCloud, File, Loader } from 'lucide-react';

interface UploadDocumentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (files: File[]) => Promise<void>;
  currentFolder: string | null;
}

export default function UploadDocumentModal({
  isOpen,
  onClose,
  onUpload,
  currentFolder
}: UploadDocumentModalProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [error, setError] = useState('');

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setSelectedFiles(prev => [...prev, ...acceptedFiles]);
    setError('');
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxSize: 10485760, // 10MB
    onDropRejected: () => setError('File too large. Maximum size is 10MB.')
  });

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setError('No files selected');
      return;
    }
    
    setIsUploading(true);
    setError('');
    
    // Simulate upload progress
    const progressInterval = setInterval(() => {
      setUploadProgress(prev => {
        const newProgress = Math.min(prev + 10, 90);
        return newProgress;
      });
    }, 300);
    
    try {
      await onUpload(selectedFiles);
      setUploadProgress(100);
      setTimeout(() => {
        onClose();
      }, 500);
    } catch (err) {
      setError('Failed to upload files');
      setUploadProgress(0);
    } finally {
      clearInterval(progressInterval);
      setIsUploading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-gray-800 rounded-lg max-w-md w-full shadow-lg">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-xl font-semibold text-white">Upload Documents</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-700 rounded-full transition-colors"
            disabled={isUploading}
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>
        
        <div className="p-4">
          {!isUploading ? (
            // Pre-upload view
            <>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                  isDragActive ? 'border-blue-500 bg-blue-500/10' : 'border-gray-600 hover:border-blue-500 hover:bg-blue-500/5'
                }`}
              >
                <input {...getInputProps()} />
                <UploadCloud className="w-12 h-12 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-300">
                  {isDragActive ? 'Drop files here' : 'Drag & drop files here, or click to select'}
                </p>
                <p className="text-sm text-gray-500 mt-1">Maximum file size: 10MB</p>
              </div>
              
              {error && (
                <p className="mt-2 text-sm text-red-500">{error}</p>
              )}
              
              {selectedFiles.length > 0 && (
                <div className="mt-4">
                  <h3 className="text-sm font-medium text-gray-400 mb-2">Selected Files ({selectedFiles.length})</h3>
                  <div className="max-h-40 overflow-y-auto">
                    {selectedFiles.map((file, index) => (
                      <div key={index} className="flex items-center justify-between p-2 bg-gray-700 rounded mb-2">
                        <div className="flex items-center">
                          <File className="w-4 h-4 text-gray-400 mr-2" />
                          <span className="text-sm text-white truncate">{file.name}</span>
                        </div>
                        <button
                          onClick={() => removeFile(index)}
                          className="p-1 hover:bg-gray-600 rounded-full"
                        >
                          <X className="w-4 h-4 text-gray-400" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            // Upload progress view
            <div className="py-8 flex flex-col items-center">
              <Loader className="w-12 h-12 text-blue-500 mb-4 animate-spin" />
              <h3 className="text-lg font-medium text-white mb-2">Uploading Files</h3>
              <p className="text-sm text-gray-400 mb-4">Please wait while your files are being uploaded...</p>
              
              {/* Progress bar */}
              <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden mb-2">
                <div 
                  className="h-full bg-blue-500 transition-all duration-300" 
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-xs text-gray-400">{uploadProgress}% complete</p>
              
              <p className="text-xs text-gray-500 mt-6 text-center">
                Files will be processed after upload. You'll see their processing status in the file list.
              </p>
            </div>
          )}
          
          <div className="flex justify-end gap-3 mt-4">
            {!isUploading ? (
              <>
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-gray-300 hover:bg-gray-700 rounded transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpload}
                  disabled={isUploading || selectedFiles.length === 0}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                  Upload
                </button>
              </>
            ) : (
              <p className="text-sm text-gray-400">This may take a while...</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}