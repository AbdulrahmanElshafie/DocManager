# DocManager - Django Backend API

A comprehensive document management backend built with Django REST Framework, providing secure APIs for document organization, sharing, and collaboration with advanced features like version control, activity tracking, and real-time capabilities.

## 📋 Overview

DocManager backend is a robust REST API system that powers a full-featured document management platform. It provides secure authentication, hierarchical folder organization, document processing, permission management, and comprehensive activity tracking. The system is built with scalability and security in mind, supporting multiple document formats and real-time collaboration features.

> **Note**: This backend system was developed by incorporating vibe coding techniques using Cursor IDE, enabling high-quality results and rapid development in a remarkably short amount of time.

## ✨ Features

### 🔐 Authentication & User Management
- **JWT Authentication**: Secure token-based authentication with refresh token support
- **User Registration & Login**: Complete user management system
- **Password Reset**: Secure password reset functionality
- **Profile Management**: Update user details and preferences
- **User Listing**: API for user discovery in permission management

### 📁 Document & Folder Management
- **Hierarchical Folders**: Nested folder structure with unlimited depth
- **Document Upload**: Support for PDF, CSV, and DOCX file formats
- **File Validation**: Automatic file type and size validation (up to 50MB)
- **Document Operations**: Create, read, update, delete operations
- **Bulk Operations**: Zip folder upload with automatic extraction
- **File Organization**: Move documents between folders

### 🔄 Version Control & History
- **Document Versioning**: Track all document changes with `django-reversion`
- **Revision History**: Complete audit trail of document modifications
- **Version Restoration**: Rollback to previous document versions
- **Change Tracking**: Detailed metadata for each revision
- **User Attribution**: Track who made what changes and when

### 🛡️ Advanced Permissions System
- **Granular Permissions**: Read, write, delete, and track permissions
- **Hierarchical Inheritance**: Folder permissions cascade to child items
- **User-based Access**: Individual user permission management
- **Permission Propagation**: Automatic permission inheritance for new items

### 🔗 Sharing & Collaboration
- **Shareable Links**: Generate time-limited or permanent sharing links
- **Token-based Access**: Secure document access via unique tokens
- **Link Management**: Create, update, and revoke sharing links
- **Anonymous Access**: Allow document viewing without authentication

### 💬 Comments System (In Development)
- **Document Comments**: Add threaded comments to any document
- **Nested Replies**: Support for comment threads and discussions
- **User Attribution**: Track comment authors and timestamps
- **Attachment Support**: File attachments on comments

### 📊 Activity Logging & Analytics
- **Comprehensive Tracking**: Log all document and folder activities
- **Activity Types**: View, edit, create, delete, download, share, and more
- **User Analytics**: Track user behavior and document usage patterns
- **IP & Session Tracking**: Security monitoring with IP and user agent logging
- **Statistical Reports**: Activity summaries and usage statistics
- **Filtering & Search**: Advanced activity log filtering capabilities

### 📄 Document Processing
- **Format Conversion**: DOCX to HTML and HTML to DOCX conversion
- **PDF Conversion**: On-demand DOCX to PDF conversion via REST API
- **Markdown Support**: Markdown to HTML conversion
- **Document Parsing**: Extract and process document content
- **Content Extraction**: Text extraction from various document formats
- **Document Annotations**: Support for document markup and annotations

### 💾 Backup & Recovery
- **Automated Backups**: Scheduled database and media backups
- **Full System Backup**: Database dump and media file archiving
- **One-click Restore**: Easy restoration from backup files
- **Backup Management**: Create, list, and manage backup instances

### 🎯 Workflow Templates
- **Document Templates**: Predefined document templates for quick creation
- **Template Management**: Upload and manage document templates
- **Standardization**: Ensure consistent document formats across organization

### 🔧 System Features
- **RESTful API**: Comprehensive REST API with proper HTTP methods
- **API Documentation**: Auto-generated Swagger/OpenAPI documentation
- **CORS Support**: Cross-origin resource sharing for frontend integration
- **Docker Support**: Containerized deployment with Docker Compose
- **PostgreSQL Database**: Robust relational database for data persistence
- **Redis Integration**: Caching and session management
- **Channel Support**: Real-time capabilities with Django Channels

## 🚀 Future Updates

### 💬 Enhanced Comments System
- **Real-time Comments**: Live comment updates using WebSockets
- **Comment Notifications**: Email and in-app notifications for new comments
- **Comment Moderation**: Admin approval system for comments
- **Rich Text Comments**: Support for formatted text in comments
- **Comment Search**: Full-text search across all comments

### 📚 Complete Version Management
- **Visual Diff**: Side-by-side comparison of document versions
- **Merge Conflicts**: Handle and resolve document merge conflicts
- **Branch Management**: Support for document branching and merging
- **Version Tagging**: Add tags and labels to specific versions
- **Automated Versioning**: Smart versioning based on change significance

### 📝 Advanced DOCX Integration
- **Real-time Editing**: Collaborative document editing with conflict resolution
- **Live Cursor Tracking**: See other users' cursors and selections
- **Operational Transform**: Handle concurrent edits seamlessly
- **Document Locking**: Prevent conflicts with document check-out system
- **Rich Media Support**: Images, tables, and formatting preservation

### 🔄 Additional Features
- **Elasticsearch Integration**: Advanced full-text search across all documents
- **OCR Processing**: Extract text from scanned documents and images
- **Document Preview**: Generate thumbnails and previews for documents
- **Audit Compliance**: Enhanced logging for regulatory compliance
- **Workflow Automation**: Automated document processing workflows
- **External Integrations**: Connect with cloud storage and third-party services

## 📦 Dependencies

### Core Framework
- **Django 5.2**: Modern Python web framework
- **djangorestframework 3.15.2**: Powerful REST API framework
- **djangorestframework-simplejwt 5.3.1**: JWT authentication
- **django-cors-headers 4.6.0**: CORS handling

### Database & Storage
- **psycopg2-binary 2.9.10**: PostgreSQL database adapter
- **django-environ 0.11.2**: Environment variable management

### Document Processing
- **python-docx 1.1.2**: DOCX document manipulation
- **markdown2 2.5.1**: Markdown processing
- **html2text 2024.2.26**: HTML to text conversion
- **beautifulsoup4 4.12.3**: HTML parsing and manipulation
- **fpdf2 2.8.4**: PDF generation library
- **reportlab 4.4.3**: Advanced PDF generation
- **libreoffice-convert 1.0**: LibreOffice-based document conversion
- **docx2pdf 0.1.8**: Alternative DOCX to PDF conversion

### Version Control & Logging
- **django-reversion 5.1.0**: Model versioning and revision tracking

### Real-time & Caching
- **channels 4.2.0**: WebSocket and async support
- **channels-redis 4.2.1**: Redis channel layer
- **redis 5.2.1**: Redis client
- **daphne 4.2.0**: ASGI HTTP/WebSocket server

### API Documentation
- **drf-yasg 1.21.8**: Swagger/OpenAPI documentation generation

## 🛠️ Development Setup

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Redis 6+
- Docker & Docker Compose (optional)

### Local Development

1. **Clone the repository**
   ```bash
   git clone [repository-url]
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment configuration**
   ```bash
   cp .env_ex .env
   # Edit .env with your database and email settings
   ```

5. **Database setup**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Run development server**
   ```bash
   python manage.py runserver
   ```

### Docker Development

1. **Docker setup**
   ```bash
   cp docker.env.example docker.env
   # Edit docker.env with your configuration
   ```

2. **Build and run**
   ```bash
   docker-compose up --build
   ```

3. **Run migrations**
   ```bash
   docker-compose exec backend python manage.py migrate
   docker-compose exec backend python manage.py createsuperuser
   ```

## 🔗 Frontend Integration

**Frontend Repository**: [DocManager Frontend](https://github.com/AbdulrahmanElshafie/DocManagerFront)

The backend provides RESTful APIs consumed by a Flutter frontend application. Ensure both applications are running for full functionality.

### API Configuration
The backend exposes APIs at `http://localhost:8000/api/` with the following main endpoints:

- **Authentication**: `/api/auth/`
- **Document Management**: `/api/manager/`
- **Backups**: `/api/backups/`
- **Workflows**: `/api/workflows/`

### API Documentation
- **Swagger UI**: `http://localhost:8000/swagger/`
- **ReDoc**: `http://localhost:8000/redoc/`

## 🏗️ Architecture Overview

```
backend/
├── DocManager/          # Main Django project
│   ├── settings.py     # Configuration
│   ├── urls.py         # URL routing
│   └── asgi.py         # ASGI configuration
├── manager/            # Core document management
│   ├── models.py       # Data models
│   ├── views.py        # API views
│   ├── serializers.py  # Data serialization
│   ├── permissions.py  # Access control
│   └── document_converter.py  # File processing
├── UserAuth/           # Authentication system
├── backups_management/ # Backup functionality
├── workflows/          # Template management
└── requirements.txt    # Dependencies
```

## 🔌 API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `POST /api/auth/token/refresh/` - Refresh JWT token
- `GET/PUT /api/auth/user/` - User profile management

### Document Management
- `GET/POST /api/manager/document/` - List/create documents
- `GET/PUT/DELETE /api/manager/document/{id}/` - Document operations
- `GET /api/manager/document/{id}/download/` - Download document
- `GET /api/manager/document/{id}/convert/pdf/` - Convert DOCX to PDF on-demand
- `GET /api/manager/folder/` - Folder management
- `POST /api/manager/folder/upload/` - Bulk folder upload

### Activity Tracking
- `GET /api/manager/activity/` - Activity logs
- `GET /api/manager/activity/stats/` - Usage statistics
- `GET /api/manager/activity/document/` - Document-specific activity

### Sharing
- `POST /api/manager/share/` - Create shareable link
- `GET /api/manager/share/{token}/` - Access shared document

## 🐳 Production Deployment

### Docker Production
```bash
# Build production image
docker build -t docmanager:prod .

# Deploy with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables
```bash
SECRET_KEY=your-secret-key
DEBUG=False
DB_NAME=docmanager
DB_USER=dbuser
DB_PASSWORD=dbpass
DB_HOST=localhost
DB_PORT=5432
REDIS_HOST=localhost
REDIS_PORT=6379
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## 📊 Database Schema

### Core Models
- **User**: Django's built-in user model
- **Folder**: Hierarchical folder structure
- **Document**: File storage and metadata
- **Permission**: Access control system
- **ActivityLog**: Comprehensive activity tracking
- **ShareableLink**: Document sharing system
- **Comment**: Document commenting system
- **Backup**: System backup management

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Permission-based Access**: Granular permission system
- **Input Validation**: Comprehensive data validation
- **File Upload Security**: File type and size validation
- **CORS Configuration**: Secure cross-origin requests
- **SQL Injection Protection**: Django ORM protection
- **XSS Prevention**: Template and data sanitization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Write comprehensive tests
- Update documentation for new features
- Use meaningful commit messages

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the API documentation at `/swagger/`
- Contact the development team

---

**Built with ❤️ using Django REST Framework** 