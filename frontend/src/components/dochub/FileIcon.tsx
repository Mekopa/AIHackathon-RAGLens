// src/components/dochub/FileIcon.tsx

import React from 'react';
import { 
  FileText, Image, File as FileIcon, 
  FileSpreadsheet, Code, Archive 
} from 'lucide-react';

interface FileIconProps {
  type: string;
  className?: string;
  size?: number;
}

export default function FileTypeIcon({ type, className = '', size = 24 }: FileIconProps) {
  let Icon = FileText;
  
  if (type.startsWith('image/')) {
    Icon = Image;
  } else if (type.includes('spreadsheet') || type.includes('excel') || type.includes('csv')) {
    Icon = FileSpreadsheet;
  } else if (type.includes('code') || type.includes('javascript') || type.includes('typescript')) {
    Icon = Code;
  } else if (type.includes('zip') || type.includes('archive')) {
    Icon = Archive;
  } else if (!type.includes('pdf') && !type.includes('doc')) {
    Icon = FileIcon;
  }
  
  return <Icon className={className} size={size} />;
}