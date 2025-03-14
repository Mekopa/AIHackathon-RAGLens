# RAGLens Error Debugging Documentation

This document explains the error debugging dashboard implemented in the RAGLens application to help you identify and fix issues in the document processing pipeline.

## Document Processing Requirements

To ensure optimal document processing, make sure you have the following dependencies installed:

```bash
# For PDF processing with multilingual support
sudo apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-eng tesseract-ocr-lit tesseract-ocr-tur

# For DOC file processing (Microsoft Word)
sudo apt-get install -y antiword catdoc libreoffice

# For Python dependencies
pip install docling pymupdf python-docx PyPDF2 easyocr pytesseract langdetect
```

These tools help extract text from various document formats, including scanned documents.

## Table of Contents
1. [Overview](#overview)
2. [How to Access the Debug Dashboard](#how-to-access-the-debug-dashboard)
3. [Dashboard Features](#dashboard-features)
4. [Pipeline Components](#pipeline-components)
5. [Common Error Types](#common-error-types)
6. [Troubleshooting Guide](#troubleshooting-guide)

## Overview

The debug dashboard provides detailed visualization of the document processing pipeline, making it easy to:
- Monitor the status of each pipeline component
- Identify exactly where errors occur
- View detailed error messages and stack traces
- Track the progress of document processing

## How to Access the Debug Dashboard

1. Start the Django development server:
   ```bash
   cd backend
   python manage.py runserver
   ```
   
2. Open your browser and navigate to:
   ```
   http://localhost:8000/dochub/test-dashboard/
   ```

3. Use the "Load Documents" button to load your documents
4. Select a document from the dropdown to view its processing status

## Dashboard Features

The dashboard is divided into several tabs:

### Pipeline Steps
- Timeline view of all processing steps
- Color-coded status indicators (blue = started, yellow = in progress, green = completed, red = error)
- Collapsible details for each step

### Text Chunks
- View the text chunks created from the document
- Useful for verifying text extraction and splitting

### Entities
- Table of extracted entities from the document
- Includes entity type, name, and properties

### Relationships
- Table of relationships between entities
- Shows source entity, relationship type, and target entity

### Graph Preview
- Visual preview of the knowledge graph
- Link to view the full graph

### Error Debug
- Detailed error analysis for each pipeline component
- Status indicators for each processing stage
- Detailed error messages and stack traces
- Troubleshooting suggestions

## Pipeline Components

The document processing pipeline consists of the following components:

1. **Text Extraction**
   - Extracts text from various document formats (PDF, DOCX, TXT)
   - Common errors: Corrupted files, unsupported formats, OCR failures

2. **Text Splitting**
   - Splits text into manageable chunks
   - Common errors: Text too short, invalid chunk size

3. **Embedding Generation**
   - Creates vector embeddings for each text chunk
   - Common errors: API timeouts, rate limiting, invalid model

4. **Vector Indexing**
   - Stores embeddings in vector database (ChromaDB)
   - Common errors: Database connection issues, duplicate IDs

5. **Graph Extraction**
   - Extracts entities and relationships using OpenAI
   - Common errors: API errors, JSON parsing failures, rate limiting

6. **Neo4j Storage**
   - Stores graph data in Neo4j graph database
   - Common errors: Connection failures, schema conflicts

## Common Error Types

### 1. File-Related Errors
- **Symptoms:** Text extraction fails, "No such file or directory"
- **Fixes:** 
  - Verify file exists and is accessible
  - Check file permissions
  - Try re-uploading the file

### 2. API Errors
- **Symptoms:** "OpenAI API request failed", "timeout"
- **Fixes:**
  - Check API keys are valid
  - Verify API rate limits
  - Check for network issues

### 3. Database Errors
- **Symptoms:** "Failed to connect to Neo4j", "ChromaDB collection not found"
- **Fixes:**
  - Ensure database services are running
  - Check connection credentials
  - Verify network connectivity

### 4. Processing Errors
- **Symptoms:** "Invalid JSON response", "Failed to parse"
- **Fixes:**
  - Check for malformed content
  - Verify correct settings for document type
  - Adjust chunk size or model parameters

## Troubleshooting Guide

### Step 1: Check the Document Status
First, look at the overall document status in the Error Debug tab. The status indicator will show:
- **Gray**: Not processed
- **Blue**: New/uploaded
- **Yellow**: Processing
- **Green**: Completed
- **Red**: Error

### Step 2: Identify the Failed Component
In the Error Debug tab, check each component's status. Look for components with red indicators, which show where processing failed.

### Step 3: Review Error Details
Click on the component that failed to see detailed error information:
- Error message
- Stack trace (for technical debugging)
- Any context about the failure

**Note:** For pipeline steps like text extraction and splitting, you can see detailed logs by clicking the "Refresh Logs" button. This will update the error details with the latest error information directly from the server logs.

### Step 4: Check Incomplete Steps
The Error Debug tab will also show any steps that started but didn't complete, which can help identify timeouts or hanging processes.

### Step 5: Apply Fixes
Based on the error message and component:
1. Fix file issues by re-uploading or checking format
2. Resolve API issues by checking keys and limits
3. Fix database issues by ensuring services are running
4. Address processing errors by adjusting parameters

### Step 6: Re-Process
After fixing the issue, upload the document again and monitor the pipeline through the dashboard.

## Additional Notes

- The dashboard uses a simulated error environment that can be triggered by:
  - Documents with "error" or "failed" in the status field
  - Documents with specific formats (PDF) and certain names (containing "model", "graph", or "neo4j")
- This allows for testing the error handling without actual failures
- In production, real error data will be displayed

For any questions or issues with the debugging dashboard, please contact the development team.