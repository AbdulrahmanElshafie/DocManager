import json
import asyncio
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Document, ActivityLog
from .document_converter import DocumentConverter
from .middleware import get_user_from_token
import logging

logger = logging.getLogger(__name__)

class DocumentEditConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document_id = None
        self.document_group_name = None
        self.user = None
        self.auto_save_task = None

    async def connect(self):
        try:
            # Get document ID from URL
            self.document_id = self.scope['url_route']['kwargs']['document_id']
            self.document_group_name = f'document_{self.document_id}'
            
            # Get user from token
            token = self.scope.get('query_string', b'').decode('utf-8')
            if token.startswith('token='):
                token = token[6:]  # Remove 'token=' prefix
            
            self.user = await get_user_from_token(token)
            
            if not self.user or not self.user.is_authenticated:
                await self.close(code=4001)
                return
            
            # Check if user has permission to access this document
            has_permission = await self.check_document_permission()
            if not has_permission:
                await self.close(code=4003)
                return
            
            # Join document group
            await self.channel_layer.group_add(
                self.document_group_name,
                self.channel_name
            )
            
            await self.accept()
            
            # Log WebSocket connection activity
            await self.log_activity(
                activity_type='websocket_connect',
                channel_name=self.channel_name
            )
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'user_id': str(self.user.id),
                'document_id': self.document_id,
                'timestamp': datetime.now().isoformat()
            }))
            
            logger.info(f"User {self.user.id} connected to document {self.document_id}")
            
        except Exception as e:
            logger.error(f"Error in connect: {e}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        # Log WebSocket disconnection activity
        if self.user and self.document_id:
            await self.log_activity(
                activity_type='websocket_disconnect',
                close_code=close_code,
                channel_name=self.channel_name
            )
        
        # Cancel auto-save task if running
        if self.auto_save_task:
            self.auto_save_task.cancel()
        
        # Leave document group
        if self.document_group_name:
            await self.channel_layer.group_discard(
                self.document_group_name,
                self.channel_name
            )
        
        logger.info(f"User {self.user.id if self.user else 'Unknown'} disconnected from document {self.document_id}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'content_update':
                await self.handle_content_update(data)
            elif message_type == 'force_save':
                await self.handle_force_save(data)
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Error in receive: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def handle_content_update(self, data):
        """Handle real-time content updates"""
        try:
            content = data.get('content', '')
            content_type = data.get('content_type', 'html')
            
            # Cancel previous auto-save task
            if self.auto_save_task:
                self.auto_save_task.cancel()
            
            # Schedule auto-save in 3 seconds
            self.auto_save_task = asyncio.create_task(
                self.auto_save_content(content, content_type)
            )
            
            # Acknowledge update received
            await self.send(text_data=json.dumps({
                'type': 'update_received',
                'timestamp': datetime.now().isoformat()
            }))
            
            # Notify other users in the group about the update
            await self.channel_layer.group_send(
                self.document_group_name,
                {
                    'type': 'document_updated_by_other',
                    'user_id': str(self.user.id),
                    'timestamp': datetime.now().isoformat(),
                    'sender_channel': self.channel_name
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling content update: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Content update failed: {str(e)}'
            }))

    async def handle_force_save(self, data):
        """Handle manual save requests"""
        try:
            content = data.get('content')
            content_type = data.get('content_type', 'html')
            
            if content is not None:
                success = await self.save_document_content(content, content_type, is_manual=True)
            else:
                # Force save current content
                success = True
            
            await self.send(text_data=json.dumps({
                'type': 'save_result',
                'success': success,
                'timestamp': datetime.now().isoformat(),
                'is_manual': True
            }))
            
        except Exception as e:
            logger.error(f"Error handling force save: {e}")
            await self.send(text_data=json.dumps({
                'type': 'save_result',
                'success': False,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }))

    async def auto_save_content(self, content, content_type):
        """Auto-save content after delay"""
        try:
            # Wait for 3 seconds
            await asyncio.sleep(3)
            
            success = await self.save_document_content(content, content_type, is_manual=False)
            
            await self.send(text_data=json.dumps({
                'type': 'auto_save_result',
                'success': success,
                'timestamp': datetime.now().isoformat()
            }))
            
        except asyncio.CancelledError:
            # Task was cancelled (new update received)
            pass
        except Exception as e:
            logger.error(f"Error in auto-save: {e}")
            await self.send(text_data=json.dumps({
                'type': 'auto_save_result',
                'success': False,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }))

    @database_sync_to_async
    def save_document_content(self, content, content_type, is_manual=False):
        """Save document content to database"""
        try:
            document = Document.objects.get(id=self.document_id)
            
            # Convert content based on document type and content type
            if document.file and document.file.name:
                file_extension = document.file.name.split('.')[-1].lower()
                
                if file_extension == 'docx' and content_type == 'html':
                    # Convert HTML to DOCX
                    success = DocumentConverter.html_to_docx(content, document.file.path)
                elif file_extension == 'csv' and content_type == 'csv':
                    # Save CSV content directly
                    with open(document.file.path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    success = True
                elif file_extension == 'pdf':
                    # PDF content is handled differently (annotations)
                    success = True
                else:
                    success = True
            else:
                success = True
            
            # Log save activity
            ActivityLog.log_activity(
                document=document,
                user=self.user,
                activity_type='manual_save' if is_manual else 'auto_save',
                content_type=content_type,
                content_length=len(content),
                websocket_session=self.channel_name
            )
            
            # Update document timestamp
            document.save()
            return success
            
        except Document.DoesNotExist:
            logger.error(f"Document {self.document_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error saving document content: {e}")
            return False

    @database_sync_to_async
    def check_document_permission(self):
        """Check if user has permission to access document"""
        try:
            from .permissions import has_permission
            document = Document.objects.get(id=self.document_id)
            return has_permission(self.user, document=document, required_level='write')
        except Document.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            return False

    @database_sync_to_async
    def log_activity(self, activity_type, **kwargs):
        """Log WebSocket-related activities"""
        try:
            document = Document.objects.get(id=self.document_id)
            return ActivityLog.log_activity(
                document=document,
                user=self.user,
                activity_type=activity_type,
                **kwargs
            )
        except Document.DoesNotExist:
            logger.error(f"Document {self.document_id} not found for logging")
            return None
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            return None

    async def document_updated_by_other(self, event):
        """Handle notification that document was updated by another user"""
        # Don't send notification to the user who made the update
        if event.get('sender_channel') != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'document_updated_by_other',
                'user_id': event['user_id'],
                'timestamp': event['timestamp']
            })) 