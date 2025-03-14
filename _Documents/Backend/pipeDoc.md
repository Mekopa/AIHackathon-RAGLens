# Comprehensive Development Documentation for RAGLens Document Processing Pipeline

## Project Overview

This document provides a detailed explanation of the RAGLens document processing pipeline implementation, focusing on the modular architecture designed for the hackathon project. The pipeline processes documents through extraction, splitting, embedding, indexing, and knowledge graph generation stages.

## Table of Contents

1. [Project Structure](#project-structure)
2. [Core Components](#core-components)
   - [Models](#models)
   - [Pipeline Components](#pipeline-components)
   - [Services](#services)
   - [Tasks](#tasks)
   - [API Layer](#api-layer)
3. [Graph Generation Module](#graph-generation-module)
4. [Testing Framework](#testing-framework)
5. [Development Guide](#development-guide)
6. [Original vs. New Implementation](#original-vs-new-implementation)
7. [Common Issues and Solutions](#common-issues-and-solutions)

## Project Structure

```
backend/
├── config/                          # Project configuration
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py                  # Django settings
│   ├── urls.py                      # Main URL routing
│   └── wsgi.py
├── dochub/                          # Document hub application
│   ├── api/                         # API layer
│   │   ├── __init__.py
│   │   ├── serializers.py           # Data serializers
│   │   ├── urls.py                  # API endpoints
│   │   └── views.py                 # API views
│   ├── management/                  # Custom management commands
│   │   └── commands/
│   │       └── test_pipeline.py     # Testing command
│   ├── migrations/                  # Database migrations
│   ├── models/                      # Data models
│   │   ├── __init__.py
│   │   ├── document.py              # Document model
│   │   └── folder.py                # Folder model
│   ├── pipeline/                    # Processing pipeline components
│   │   ├── __init__.py
│   │   ├── extractors/              # Text extraction
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Base extractor interface
│   │   │   └── docling_extractor.py # Docling implementation
│   │   ├── splitters/               # Text splitting
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Base splitter interface
│   │   │   └── langchain_splitter.py# Langchain implementation
│   │   ├── embeddings/              # Embedding generation
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Base generator interface
│   │   │   └── openai_embeddings.py # OpenAI implementation
│   │   ├── indexers/                # Vector indexing
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Base indexer interface
│   │   │   └── chroma_indexer.py    # ChromaDB implementation
│   │   └── graphs/                  # Knowledge graph generation
│   │       ├── __init__.py
│   │       ├── client.py            # Neo4j client (from neo4j_client.py)
│   │       ├── generator.py         # Graph generator (from graph_generator.py)
│   │       └── schema.py            # Schema manager (from schema_manager.py)
│   ├── services/                    # Business logic services
│   │   ├── __init__.py
│   │   ├── document_service.py      # Document processing orchestration
│   │   └── search_service.py        # Document search functionality
│   ├── signals.py                   # Signal handlers
│   ├── tasks/                       # Celery tasks
│   │   ├── __init__.py
│   │   └── document_tasks.py        # Document processing tasks
│   ├── templates/                   # HTML templates
│   │   └── dochub/
│   │       └── test_dashboard.html  # Pipeline test dashboard
│   ├── utils/                       # Utility functions
│   │   ├── __init__.py
│   │   ├── pipeline_logger.py       # Pipeline testing logger
│   │   └── graph_visualizer.py      # Graph visualization utility
│   ├── __init__.py
│   ├── apps.py                      # App configuration
│   └── views.py                     # Django views
├── chatbot/                         # Chatbot application (optional)
├── utils/                           # Shared utilities
│   └── __init__.py
├── media/                           # Media files
│   ├── Documents/                   # Document storage
│   └── pipeline_tests/              # Pipeline test artifacts
├── celery.py                        # Celery configuration
├── manage.py                        # Django management script
└── requirements.txt                 # Project dependencies
```

## Core Components

### Models

#### Document Model (`dochub/models/document.py`)

The Document model represents a file uploaded to the system:

```python
class Document(models.Model):
    STATUS_CHOICES = (
        ('processing', 'Processing'),
        ('ready', 'Ready'),
        ('error', 'Error'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=document_upload_path)
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True, related_name='documents')
    file_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

Key fields:
- `id`: UUID for unique identification
- `name`: Document name
- `file`: Actual file storage
- `folder`: Optional parent folder
- `status`: Processing status ('processing', 'ready', 'error')
- `file_type`: MIME type or extension
- `size`: File size in bytes

The `document_upload_path` function determines where files are stored, organizing them by folder structure.

#### Folder Model (`dochub/models/folder.py`)

The Folder model organizes documents in a hierarchical structure:

```python
class Folder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subfolders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

Key fields:
- `id`: UUID for unique identification
- `name`: Folder name
- `parent`: Optional parent folder (self-referential)

The `build_folder_path` function builds the file path for folders based on the hierarchy.

### Pipeline Components

The pipeline uses a modular architecture with clear interfaces for each component. This allows easy replacement of implementations.

#### Text Extraction (`dochub/pipeline/extractors/`)

Text extractors convert document files to plain text:

- `base.py`: Defines the `TextExtractor` interface
- `docling_extractor.py`: Implements text extraction using Docling library

The `DoclingExtractor` extracts text from various file formats:
- Plain text (.txt): Simple file reading
- PDF (.pdf): Docling's PDF processing with OCR
- Other formats: Graceful fallback to simpler methods

#### Text Splitting (`dochub/pipeline/splitters/`)

Text splitters divide long documents into manageable chunks:

- `base.py`: Defines the `TextSplitter` interface
- `langchain_splitter.py`: Implements text splitting using LangChain

The `LangchainSplitter` uses recursive character splitting with configurable chunk size and overlap.

#### Embedding Generation (`dochub/pipeline/embeddings/`)

Embedding generators create vector representations of text chunks:

- `base.py`: Defines the `EmbeddingGenerator` interface
- `openai_embeddings.py`: Implements embedding generation using OpenAI's API

The `OpenAIEmbeddingGenerator` uses models like "text-embedding-ada-002" to create high-dimensional vector representations.

#### Vector Indexing (`dochub/pipeline/indexers/`)

Vector indexers store and retrieve embeddings:

- `base.py`: Defines the `VectorIndexer` interface
- `chroma_indexer.py`: Implements vector indexing using ChromaDB

The `ChromaIndexer` stores document chunks with their embeddings and metadata, enabling semantic search.

### Graph Generation Module (`dochub/pipeline/graphs/`)

This critical module creates knowledge graphs from document content:

#### Neo4j Client (`dochub/pipeline/graphs/client.py`)

The `Neo4jClient` class handles connections to the Neo4j graph database:

```python
class Neo4jClient:
    def __init__(self):
        uri = settings.NEO4J_URI
        username = settings.NEO4J_USERNAME
        password = settings.NEO4J_PASSWORD
        
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self._initialize_constraints()
```

Key functions:
- `create_document_node`: Create a node for a document
- `create_custom_entity_node`: Create an entity node
- `create_relationship_safely`: Create a relationship between entities
- `get_document_graph`: Retrieve graph data for a document
- `get_folder_graph`: Retrieve graph data for a folder

#### Graph Generator (`dochub/pipeline/graphs/generator.py`)

The `GraphGenerator` class extracts entities and relationships from document text:

```python
class GraphGenerator:
    def __init__(self, user_id=None, schema_data=None, llm_provider="openai"):
        self.neo4j_client = Neo4jClient()
        self.llm_provider = llm_provider
        
        # Use provided schema or get from schema manager
        self.schema_manager = SchemaManager()
        
        if schema_data:
            self.schema = schema_data
        elif user_id:
            self.schema = self.schema_manager.get_user_schema(user_id)
        else:
            self.schema = self.schema_manager.get_system_default_schema()
```

Key functions:
- `extract_entities_and_relations_openai`: Extract entities and relationships using OpenAI
- `process_document`: Process a document to generate a knowledge graph
- `detect_document_type`: Detect the type of document for better entity extraction

This class uses OpenAI's models to extract structured information from unstructured text.

#### Schema Manager (`dochub/pipeline/graphs/schema.py`)

The `SchemaManager` class manages graph schemas for document processing:

```python
class SchemaManager:
    def __init__(self):
        self._system_default_schema = self._load_system_default_schema()
    
    def get_system_default_schema(self):
        return self._system_default_schema
    
    def get_user_schema(self, user_id):
        schema = GraphSchema.get_user_active_schema(user_id)
        
        if schema:
            return schema.schema_data
        
        return self._system_default_schema
```

Key functions:
- `_load_system_default_schema`: Load the default schema
- `validate_schema`: Validate a schema's structure
- `register_missing_relationship`: Dynamically register a missing relationship type

The schema defines entity types (Person, Organization, etc.) and relationship types.

### Services

#### Document Service (`dochub/services/document_service.py`)

The `DocumentService` orchestrates the document processing pipeline:

```python
class DocumentService:
    def __init__(self):
        self.extractor = DoclingExtractor()
        self.splitter = LangchainSplitter()
        self.embedding_generator = OpenAIEmbeddingGenerator()
        self.indexer = ChromaIndexer()
        self.graph_generator = GraphGenerator()
    
    def process_document(self, document):
        # 1. Extract text
        text = self.extractor.extract(document.file.path)
        
        # 2. Split text into chunks
        chunks = self.splitter.split(text)
        
        # 3. Generate embeddings
        embeddings = self.embedding_generator.generate(chunks)
        
        # 4. Index chunks
        metadata = {...}  # Document metadata
        self.indexer.index(chunks, embeddings, metadata)
        
        # 5. Generate knowledge graph
        graph_result = self.graph_generator.process_document(...)
        
        return {...}  # Result information
```

This service handles the full pipeline from text extraction to graph generation.

### Tasks

#### Document Processing Task (`dochub/tasks/document_tasks.py`)

Celery tasks for asynchronous document processing:

```python
@shared_task(bind=True, max_retries=3)
def process_document_task(self, document_id):
    try:
        # Get document
        with transaction.atomic():
            document = Document.objects.select_for_update().get(id=document_id)
            document.status = 'processing'
            document.save(update_fields=['status'])
        
        # Process document
        service = DocumentService()
        result = service.process_document(document)
        
        # Update status to ready
        with transaction.atomic():
            document = Document.objects.select_for_update().get(id=document_id)
            document.status = 'ready'
            document.save(update_fields=['status'])
        
        return result
        
    except Exception as e:
        # Update status to error
        with transaction.atomic():
            document = Document.objects.select_for_update().get(id=document_id)
            document.status = 'error'
            document.error_message = str(e)
            document.save(update_fields=['status', 'error_message'])
        
        # Retry if appropriate
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {"error": str(e)}
```

Additional tasks:
- `cleanup_processing_documents`: Fix documents stuck in processing state
- `reprocess_failed_document`: Retry processing for failed documents
- `mock_process_document_task`: Simplified version for testing

### Signals

Signal handlers in `dochub/signals.py` automate document and folder operations:

```python
@receiver(post_save, sender=Document)
def handle_document_post_save(sender, instance, created, **kwargs):
    if created and instance.file:
        # Update file metadata
        instance.file_type = ...
        instance.size = ...
        
        # Queue processing task
        process_document_task.delay(str(instance.id))

@receiver(post_save, sender=Folder)
def handle_folder_post_save(sender, instance, created, **kwargs):
    if created:
        # Create physical directory
        path = instance.physical_path
        os.makedirs(path, exist_ok=True)

@receiver(pre_delete, sender=Document)
def handle_document_pre_delete(sender, instance, **kwargs):
    if instance.file:
        # Delete physical file
        file_path = instance.file.path
        if os.path.exists(file_path):
            os.remove(file_path)
```

These handlers ensure:
- Document metadata is updated on creation
- Processing tasks are queued automatically
- Physical folders are created/deleted as needed
- Physical files are deleted when documents are deleted

### API Layer

#### Serializers (`dochub/api/serializers.py`)

Serializers convert between Django models and JSON:

```python
class DocumentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = ['id', 'name', 'file', 'url', 'folder', 'file_type', 'size', 
                  'status', 'error_message', 'created_at', 'updated_at']
        read_only_fields = ['file_type', 'size', 'status', 'error_message', 
                            'created_at', 'updated_at']
    
    def get_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None
```

Key serializers:
- `FolderSerializer`: For Folder model data
- `DocumentSerializer`: For Document model data
- `BulkUploadSerializer`: For uploading multiple files
- `BulkDeleteSerializer`: For deleting multiple items

#### Views (`dochub/api/views.py`)

Views handle API requests:

```python
class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    
    def get_queryset(self):
        queryset = Document.objects.all()
        
        # Filter by folder if specified
        folder = self.request.query_params.get('folder', None)
        if folder:
            if folder.lower() == 'null' or folder.lower() == 'root':
                queryset = queryset.filter(folder__isnull=True)
            else:
                queryset = queryset.filter(folder=folder)
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        serializer = BulkUploadSerializer(data=request.data)
        if serializer.is_valid():
            documents = serializer.save()
            
            doc_serializer = DocumentSerializer(
                documents, 
                many=True,
                context={'request': request}
            )
            return Response(
                {"message": f"Successfully uploaded {len(documents)} files", 
                 "documents": doc_serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

Key views:
- `FolderViewSet`: CRUD operations for folders
- `DocumentViewSet`: CRUD operations for documents
- `BulkDeleteView`: Bulk deletion of folders and documents
- `document_graph`, `folder_graph`, `entity_graph`: Graph data endpoints

#### URLs (`dochub/api/urls.py`)

URL patterns for API endpoints:

```python
router = DefaultRouter()
router.register('folders', FolderViewSet, basename='folder')
router.register('documents', DocumentViewSet, basename='document')

urlpatterns = [
    path('', include(router.urls)),
    path('bulk_delete/', BulkDeleteView.as_view(), name='bulk-delete'),
    path('graph/document/<uuid:document_id>/', document_graph, name='document-graph'),
    path('graph/folder/<uuid:folder_id>/', folder_graph, name='folder-graph'),
    path('graph/entity/', entity_graph, name='entity-graph'),
    path('documents/status/<uuid:document_id>/', document_status, name='document-status'),
    path('documents/status/', document_status, name='documents-status'),
]
```

## Testing Framework

### Pipeline Logger (`dochub/utils/pipeline_logger.py`)

The `PipelineLogger` captures detailed information during pipeline testing:

```python
class PipelineLogger:
    def __init__(self, document_id, log_level=logging.DEBUG, save_artifacts=True):
        self.document_id = str(document_id)
        self.log_level = log_level
        self.save_artifacts = save_artifacts
        self.metrics = {}
        self.step_times = {}
        
        if self.save_artifacts:
            self.artifact_dir = Path(settings.MEDIA_ROOT) / 'pipeline_tests' / self.document_id
            os.makedirs(self.artifact_dir, exist_ok=True)
    
    def log_step(self, step_name):
        """Decorator to log and time a pipeline step"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                self.log(f"Starting step: {step_name}")
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Calculate step time
                    step_time = time.time() - start_time
                    self.step_times[step_name] = step_time
                    self.log(f"Completed step: {step_name} in {step_time:.2f} seconds")
                    
                    return result
                except Exception as e:
                    self.log(f"Error in step {step_name}: {str(e)}", logging.ERROR)
                    raise
                    
            return wrapper
        return decorator
```

The logger provides methods to log and save:
- Extracted text
- Text chunks
- Embeddings
- OpenAI API requests and responses
- Graph data

### Test Command (`dochub/management/commands/test_pipeline.py`)

The `test_pipeline` command runs the pipeline on a specific document:

```python
python manage.py test_pipeline <document_id> --verbose --save-artifacts
```

Options:
- `--verbose`: Enable verbose output
- `--save-artifacts`: Save intermediate artifacts
- `--log-file`: Specify a log file
- `--openai-model`: Specify an OpenAI model for graph generation

### Dashboard (`dochub/templates/dochub/test_dashboard.html`)

The test dashboard displays pipeline test results:
- Document information
- Performance metrics
- Text extraction results
- Chunk analysis
- Embedding details
- Knowledge graph visualization
- OpenAI API calls and responses

## Development Guide

### Environment Setup

1. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Create a `.env` file with:
   ```
   # Django settings
   SECRET_KEY=your-secret-key
   DEBUG=True
   
   # Neo4j settings
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your-password
   
   # OpenAI settings
   OPENAI_API_KEY=your-openai-api-key
   
   # Celery settings
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   ```

4. **Create necessary directories**:
   ```bash
   mkdir -p media/Documents
   mkdir -p media/pipeline_tests
   ```

5. **Apply migrations**:
   ```bash
   python manage.py makemigrations dochub
   python manage.py migrate
   ```

### Testing the Pipeline

1. **Start required services**:
   ```bash
   # Start Redis for Celery
   redis-server
   
   # Start Neo4j
   # (Use Neo4j Desktop or Docker)
   
   # Start Celery worker
   celery -A config worker --loglevel=info
   
   # Start Django development server
   python manage.py runserver
   ```

2. **Upload a document**:
   - Use the frontend interface or Django admin
   - Note the document ID for testing

3. **Run a basic test**:
   ```bash
   python manage.py test_pipeline <document_id>
   ```

4. **Run a detailed test with artifacts**:
   ```bash
   python manage.py test_pipeline <document_id> --verbose --save-artifacts
   ```

5. **View the test dashboard**:
   Open `http://localhost:8000/dochub/test-dashboard/<document_id>/`

6. **Test with different document types**:
   - PDF documents (text and scanned)
   - Word documents (.docx)
   - Plain text files (.txt)
   - Large documents

### Common Issues and Solutions

#### 1. OpenAI API Issues

**Problem**: API key errors or rate limits

**Solution**:
- Check your API key is correctly set in `.env`
- Consider using a different model (e.g., `gpt-4o-mini` instead of `gpt-4o`)
- Implement retries with exponential backoff

#### 2. Neo4j Connection Issues

**Problem**: Cannot connect to Neo4j

**Solution**:
- Ensure Neo4j is running
- Check connection parameters in `.env`
- Verify Neo4j allows connections from your application

#### 3. Document Processing Timeouts

**Problem**: Processing gets stuck

**Solution**:
- Implement the `cleanup_processing_documents` task as a scheduled job
- Add better error handling in each pipeline step
- Implement progress tracking

#### 4. Text Extraction Issues

**Problem**: Poor text extraction quality

**Solution**:
- Adjust OCR settings for PDFs
- Implement file type-specific extraction methods
- Add better error handling for corrupted files

#### 5. Large Documents

**Problem**: Memory issues with large documents

**Solution**:
- Implement streaming processing
- Process documents in smaller batches
- Set reasonable limits on document size

## Original vs. New Implementation

### Original Codebase

The original codebase had:

1. **Complex architecture**:
   - Multiple apps (vault, cloud, assistant)
   - Authentication and authorization
   - Complex folder structure

2. **Neo4j graph generation**:
   - `neo4j_client.py`: Neo4j database interaction
   - `graph_generator.py`: Entity and relationship extraction
   - `schema_manager.py`: Schema definition and management

3. **Processing pipeline**:
   - `text_extractor.py`: Text extraction from documents
   - `text_splitter.py`: Text chunking
   - `embedding_generator.py`: Embedding generation
   - `indexer.py`: Vector database storage

4. **Celery integration**:
   - Asynchronous document processing
   - Background tasks

### New Implementation

The new implementation:

1. **Simplified architecture**:
   - Modular pipeline with clear interfaces
   - Removal of authentication (for hackathon simplicity)
   - Focus on document processing functionality

2. **Enhanced testability**:
   - Pipeline testing framework
   - Performance monitoring
   - Visual dashboard

3. **Improved error handling**:
   - Better logging
   - Graceful fallbacks
   - Status tracking

4. **Maintained core functionality**:
   - Full document processing pipeline
   - Knowledge graph generation
   - Vector search capabilities

### Key Migration Notes

1. **Graph Module**:
   - The `graphs` directory is migrated from original files
   - `neo4j_client.py` → `dochub/pipeline/graphs/client.py`
   - `graph_generator.py` → `dochub/pipeline/graphs/generator.py`
   - `schema_manager.py` → `dochub/pipeline/graphs/schema.py`

2. **Processing Components**:
   - Each component now follows an interface-based design
   - Original implementations moved to concrete classes

3. **Settings**:
   - Environment variables for API keys and connection parameters
   - Configurable options for pipeline components

4. **Celery Tasks**:
   - Improved error handling
   - Retry mechanism
   - Status tracking

## Conclusion

This document processing pipeline provides a modular, extensible framework for:
- Extracting text from various document formats
- Splitting text into manageable chunks
- Generating vector embeddings for semantic search
- Building knowledge graphs from document content

The modular architecture allows for easy customization and extension, while the testing framework enables detailed performance analysis and optimization.

By following the development guide and testing procedures, you can ensure a robust implementation for your hackathon project.