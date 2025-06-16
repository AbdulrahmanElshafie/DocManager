# Document Activity Tracking API

This document provides comprehensive documentation for the document activity tracking feature, including all available endpoints, parameters, and examples.

## Overview

The activity tracking system logs all user interactions with documents and folders, providing detailed audit trails and analytics. Activities are automatically logged for:

- Document views, edits, downloads, uploads
- Document creation, deletion, renaming, moving
- Real-time editing sessions (WebSocket connections)
- Permission changes and sharing
- Folder operations (create, rename, move, delete)

## Permissions

### Activity Tracking Permission Levels

- **read**: Can view documents/folders
- **write**: Can edit documents/folders  
- **delete**: Can delete documents/folders (includes all other permissions)
- **track**: Can view activity logs for documents/folders

### Permission Requirements

- **Document owners**: Always have access to their document's activity logs
- **Superusers**: Have access to all activity logs
- **Other users**: Need explicit "track" permission to view activity logs

## API Endpoints

### 1. List Activity Logs

**GET** `/api/activity/`

Lists activity logs based on user permissions with comprehensive filtering options.

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document` | UUID | No | Filter by document ID |
| `activity_type` | String | No | Filter by activity type (see Activity Types below) |
| `user` | String/UUID | No | Filter by user ID or username |
| `start_date` | ISO DateTime | No | Filter activities from this date |
| `end_date` | ISO DateTime | No | Filter activities until this date |
| `ip_address` | IP Address | No | Filter by IP address |
| `resource_type` | String | No | Filter by resource type (`document` or `folder`) |
| `page` | Integer | No | Page number for pagination |
| `page_size` | Integer | No | Number of results per page |

#### Example Request

```bash
GET /api/activity/?document=123e4567-e89b-12d3-a456-426614174000&activity_type=edit&start_date=2024-01-01T00:00:00Z
Authorization: Bearer <jwt_token>
```

#### Example Response

```json
{
  "count": 50,
  "next": "http://localhost:8000/api/activity/?page=2",
  "previous": null,
  "results": [
    {
      "id": "789e4567-e89b-12d3-a456-426614174001",
      "document": "123e4567-e89b-12d3-a456-426614174000",
      "document_name": "My Document.docx",
      "user": 1,
      "user_details": {
        "id": 1,
        "username": "john.doe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe"
      },
      "activity_type": "edit",
      "activity_type_display": "Document Edited",
      "timestamp": "2024-01-15T14:30:00Z",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "session_id": "abcd1234efgh5678",
      "metadata": {
        "action": "update_content",
        "content_type": "html",
        "content_length": 2456
      },
      "description": "john.doe edited document My Document.docx"
    }
  ]
}
```

### 2. Get Document Activity

**GET** `/api/activity/document/`

Get activity logs for a specific document.

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | UUID | **Yes** | Document ID to get activities for |
| `activity_type` | String | No | Filter by activity type |

#### Example Request

```bash
GET /api/activity/document/?document_id=123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <jwt_token>
```

### 3. Get Folder Activity

**GET** `/api/activity/folder/`

Get activity logs for folder operations by the current user.

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `activity_type` | String | No | Filter by activity type |
| `folder_id` | UUID | No | Filter by specific folder ID |

#### Example Request

```bash
GET /api/activity/folder/?folder_id=456e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <jwt_token>
```

### 4. Get User Activity (Admin Only)

**GET** `/api/activity/user/`

Get activity logs for a specific user (superuser only).

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | UUID | **Yes** | User ID to get activities for |

#### Example Request

```bash
GET /api/activity/user/?user_id=789e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <jwt_token>
```

### 5. Get Activity Statistics

**GET** `/api/activity/stats/`

Get comprehensive activity statistics.

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document` | UUID | No | Filter stats by document ID |
| `resource_type` | String | No | Filter by resource type (`document` or `folder`) |

#### Example Request

```bash
GET /api/activity/stats/?document=123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <jwt_token>
```

#### Example Response

```json
{
  "total_activities": 1250,
  "recent_activities_24h": 45,
  "activity_counts": {
    "view": 650,
    "edit": 200,
    "create": 50,
    "delete": 15,
    "download": 180,
    "upload": 25,
    "share": 30,
    "permission_change": 12,
    "restore": 3,
    "rename": 25,
    "move": 18,
    "websocket_connect": 35,
    "websocket_disconnect": 35,
    "auto_save": 150,
    "manual_save": 42
  },
  "top_users": [
    {
      "user__username": "john.doe",
      "activity_count": 345
    },
    {
      "user__username": "jane.smith",
      "activity_count": 278
    }
  ]
}
```

### 6. Get Activity Log Details

**GET** `/api/activity/{id}/`

Get detailed information about a specific activity log entry.

#### Example Request

```bash
GET /api/activity/789e4567-e89b-12d3-a456-426614174001/
Authorization: Bearer <jwt_token>
```

### 7. Delete Activity Log (Admin Only)

**DELETE** `/api/activity/{id}/`

Delete a specific activity log entry (superuser only).

#### Example Request

```bash
DELETE /api/activity/789e4567-e89b-12d3-a456-426614174001/
Authorization: Bearer <jwt_token>
```

## Activity Types

The following activity types are automatically tracked:

| Type | Description | Triggered By |
|------|-------------|--------------|
| `view` | Document/folder viewed | API access, content retrieval |
| `edit` | Document/folder edited | Content updates, metadata changes |
| `create` | Document/folder created | New resource creation |
| `delete` | Document/folder deleted | Resource deletion |
| `download` | Document downloaded | File download requests |
| `upload` | Document uploaded | File upload/replacement |
| `share` | Document shared | Shareable link creation |
| `permission_change` | Permissions modified | Permission grants/revocations |
| `restore` | Document restored | Version restoration |
| `rename` | Document/folder renamed | Name changes |
| `move` | Document/folder moved | Parent folder changes |
| `websocket_connect` | Real-time editing started | WebSocket connection |
| `websocket_disconnect` | Real-time editing ended | WebSocket disconnection |
| `auto_save` | Document auto-saved | Automatic save during editing |
| `manual_save` | Document manually saved | User-triggered save |

## Metadata Fields

Activity logs include rich metadata based on the activity type:

### Common Metadata
- `action`: Specific action performed
- `ip_address`: Client IP address
- `user_agent`: Browser/client information
- `session_id`: Session identifier

### Document-Specific Metadata
- `file_type`: Document file extension
- `content_type`: Content format (html, markdown, etc.)
- `content_length`: Content size in characters
- `folder`: Target folder name

### Folder-Specific Metadata
- `resource_type`: "folder"
- `resource_id`: Folder UUID
- `resource_name`: Folder name

### WebSocket-Specific Metadata
- `websocket_session`: WebSocket channel name
- `channel_name`: Connection identifier

### Permission-Specific Metadata
- `target_user`: User receiving permission
- `permission_level`: Permission level granted
- `action`: "grant_permission" or "revoke_permission"

### Sharing-Specific Metadata
- `share_token`: Generated sharing token
- `expires_at`: Link expiration date

## Error Responses

### 400 Bad Request
```json
{
  "error": "document_id parameter is required"
}
```

### 403 Forbidden
```json
{
  "error": "You don't have permission to view activity logs for this document."
}
```

### 404 Not Found
```json
{
  "error": "Document not found"
}
```

### 405 Method Not Allowed
```json
{
  "error": "Activity logs are created automatically and cannot be manually created."
}
```

## Integration Examples

### JavaScript/Frontend Integration

```javascript
// Get activity logs for a document
async function getDocumentActivity(documentId, options = {}) {
  const params = new URLSearchParams({
    document_id: documentId,
    ...options
  });
  
  const response = await fetch(`/api/activity/document/?${params}`, {
    headers: {
      'Authorization': `Bearer ${getAuthToken()}`,
      'Content-Type': 'application/json'
    }
  });
  
  return response.json();
}

// Get activity statistics
async function getActivityStats(documentId = null) {
  const params = documentId ? `?document=${documentId}` : '';
  
  const response = await fetch(`/api/activity/stats/${params}`, {
    headers: {
      'Authorization': `Bearer ${getAuthToken()}`,
      'Content-Type': 'application/json'
    }
  });
  
  return response.json();
}

// Example usage
getDocumentActivity('123e4567-e89b-12d3-a456-426614174000', {
  activity_type: 'edit',
  start_date: '2024-01-01T00:00:00Z'
}).then(activities => {
  console.log('Document activities:', activities);
});
```

### Python/Django Integration

```python
from manager.models import ActivityLog, Document

# Get activity logs for a document
document = Document.objects.get(id='123e4567-e89b-12d3-a456-426614174000')
activities = ActivityLog.objects.filter(document=document).order_by('-timestamp')

# Log a custom activity
ActivityLog.log_activity(
    document=document,
    user=request.user,
    activity_type='custom_action',
    request=request,
    custom_field='custom_value'
)

# Get activity statistics
from django.db.models import Count
stats = ActivityLog.objects.values('activity_type').annotate(
    count=Count('id')
).order_by('-count')
```

## Best Practices

1. **Pagination**: Always use pagination for large result sets
2. **Filtering**: Use specific filters to reduce response size
3. **Permissions**: Ensure users only access activity logs they're authorized to see
4. **Rate Limiting**: Consider rate limiting for activity log endpoints
5. **Archiving**: Implement log archiving for long-term storage
6. **Privacy**: Be mindful of sensitive data in activity logs

## Security Considerations

1. **Authentication**: All endpoints require valid JWT tokens
2. **Authorization**: Users can only view activities for resources they have access to
3. **IP Logging**: IP addresses are logged for security auditing
4. **Session Tracking**: Session IDs help track user sessions
5. **Admin Controls**: Only superusers can view all activities and delete logs

This comprehensive activity tracking system provides detailed audit trails while maintaining security and performance. 