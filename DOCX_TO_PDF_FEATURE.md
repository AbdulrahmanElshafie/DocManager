# DOCX to PDF Conversion Feature

## Overview
This feature adds server-side support to convert Microsoft Word .docx files to PDF on-demand and return the PDF bytes in the HTTP response.

## API Endpoint
- **Endpoint**: `GET /api/manager/document/{id}/convert/pdf/`
- **Method**: GET
- **Authentication**: Required (same as existing document endpoints)
- **Response**: PDF file with appropriate headers

## Implementation Details

### 1. New Utility Module
- **File**: `manager/utils/convert_docx_to_pdf.py`
- **Function**: `convert_docx_to_pdf(input_path_or_buffer)`
- **Features**:
  - Multiple conversion methods with fallbacks
  - Supports both file paths and byte buffers
  - Comprehensive error handling
  - Automatic temporary file cleanup

### 2. Conversion Methods (Priority Order)
1. **LibreOffice API** (`libreoffice-convert` library)
2. **System LibreOffice** (`soffice` command)  
3. **Basic PDF Fallback** (extracts DOCX text and creates simple PDF using fpdf2)

### 3. API Endpoint Implementation
- **Location**: `manager/views.py` - `DocumentView.convert_to_pdf()`
- **URL Pattern**: Automatically handled by DRF with `@action(detail=True, url_path='convert/pdf')`
- **Validation**:
  - Checks if document exists and has a file
  - Validates that file is a DOCX document (`.docx` extension)
  - Returns appropriate HTTP error codes

### 4. Response Headers
```
Content-Type: application/pdf
Content-Disposition: inline; filename="{document_name}.pdf"
```

## Dependencies Added
```
# PDF conversion dependencies
libreoffice-convert==1.0
docx2pdf==0.1.8
fpdf2==2.8.4
reportlab==4.4.3
tqdm>=4.41.0
```

## Error Handling
- **404**: Document not found or no file associated
- **400**: File is not a DOCX document
- **500**: Conversion failed (with detailed error message)

## Activity Logging
- Conversion requests are logged as 'view' activity type
- Includes metadata indicating PDF conversion from DOCX

## Testing
- **Unit Tests**: `manager/test_pdf_conversion.py`
- **Test Coverage**: 
  - Conversion utility functions
  - API endpoint responses
  - Error conditions
  - File validation

## Usage Example

### Frontend Request
```javascript
fetch('/api/manager/document/{id}/convert/pdf/', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + token
  }
})
.then(response => {
  if (response.ok) {
    return response.blob();
  }
  throw new Error('Conversion failed');
})
.then(blob => {
  // Open PDF in browser or download
  const url = window.URL.createObjectURL(blob);
  window.open(url, '_blank');
});
```

### Backend Response
```python
# Success response
HTTP 200 OK
Content-Type: application/pdf
Content-Disposition: inline; filename="document.pdf"
[PDF binary data]

# Error responses
HTTP 404 Not Found
{"error": "File not found"}

HTTP 400 Bad Request  
{"error": "File is not a DOCX document. Only DOCX files can be converted to PDF."}

HTTP 500 Internal Server Error
{"error": "Conversion failed: [detailed error message]"}
```

## Deployment Notes

### Production Setup
For best results in production, install LibreOffice on the server:
```bash
# Ubuntu/Debian
sudo apt-get install libreoffice

# CentOS/RHEL
sudo yum install libreoffice
```

### Docker Setup
Add to your Dockerfile:
```dockerfile
RUN apt-get update && apt-get install -y libreoffice
```

### Fallback Behavior
If LibreOffice is not available, the system will:
1. Try the `libreoffice-convert` Python library
2. Try the system `soffice` command
3. Fall back to basic PDF generation (extracts text only)

The fallback ensures the API always returns a PDF, though formatting may be simplified.

## Security Considerations
- File type validation prevents processing of non-DOCX files
- Temporary files are automatically cleaned up
- Uses existing Django authentication and permissions
- No direct file system access from frontend