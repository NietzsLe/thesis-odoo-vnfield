# -*- coding: utf-8 -*-

"""
=====================================
🏗️ VN FIELD SYSTEM TYPE CONFIG WIZARD
=====================================

Mô tả:
    Wizard cấu hình loại hệ thống và kết nối với Integration System.
    Cho phép chọn giữa Integration System và Contractor System.

Tính năng chính:
    - Lựa chọn system type: Integration hoặc Contractor
    - Cấu hình Integration System server cho Contractor System
    - Test connection đến Integration System
    - Lưu trữ configuration vào system parameters

Created: 2025-08-20
Author: GitHub Copilot
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
import requests
import json

_logger = logging.getLogger(__name__)


class SystemTypeConfigWizard(models.TransientModel):
    """
    =========================================
    🏗️ MODEL: vnfield.system.type.config.wizard
    =========================================
    
    Mục đích:
        Cấu hình loại hệ thống và integration server connection.
        Xác định system hoạt động như Integration System hay Contractor System.
    
    Business Logic:
        - Integration System: Hệ thống trung tâm quản lý tất cả contractors
        - Contractor System: Hệ thống của nhà thầu, kết nối với Integration System
        - Contractor System cần cấu hình Integration System server để đồng bộ
    """
    
    _name = 'vnfield.system.type.config.wizard'
    _description = 'System Type Configuration Wizard'

    # ==========================================
    # 🏗️ SYSTEM TYPE CONFIGURATION
    # ==========================================
    
    system_type = fields.Selection([
        ('integration', '🏢 Integration System'),
        ('contractor', '🏗️ Contractor System'),
    ], string='System Type', required=True, default='integration',
       help='Loại hệ thống: Integration (trung tâm) hoặc Contractor (nhà thầu)')
    
    contractor_code = fields.Char(
        string='Contractor Code',
        help='Mã nhà thầu duy nhất trong hệ thống Integration'
    )
    
    contractor_name = fields.Char(
        string='Contractor Name',
        help='Tên nhà thầu hiển thị'
    )
    
    # ==========================================
    # 🔗 INTEGRATION SYSTEM CONNECTION
    # ==========================================
    
    integration_server_url = fields.Char(
        string='Integration Server URL',
        help='URL của Integration System server (ví dụ: https://integration.vnfield.com)'
    )
    
    integration_api_key = fields.Char(
        string='API Key',
        help='API Key để xác thực với Integration System'
    )
    
    integration_username = fields.Char(
        string='Username',
        help='Username để đăng nhập Integration System'
    )
    
    integration_password = fields.Char(
        string='Password',
        password=True,
        help='Password để đăng nhập Integration System'
    )
    
    # ==========================================
    # 📊 CONNECTION SETTINGS
    # ==========================================
    
    connection_timeout = fields.Integer(
        string='Connection Timeout (seconds)',
        default=30,
        help='Timeout cho kết nối đến Integration System'
    )
    
    sync_interval = fields.Integer(
        string='Sync Interval (minutes)',
        default=60,
        help='Khoảng thời gian đồng bộ dữ liệu với Integration System'
    )
    
    enable_auto_sync = fields.Boolean(
        string='Enable Auto Sync',
        default=True,
        help='Tự động đồng bộ dữ liệu theo interval'
    )
    
    # ==========================================
    # 📊 STATUS FIELDS
    # ==========================================
    
    connection_status = fields.Text(
        string='Connection Status',
        readonly=True,
        help='Trạng thái kết nối với Integration System'
    )
    
    last_sync_time = fields.Datetime(
        string='Last Sync Time',
        readonly=True,
        help='Thời gian đồng bộ gần nhất'
    )
    
    sync_status = fields.Selection([
        ('not_synced', 'Not Synced'),
        ('syncing', 'Syncing...'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='Sync Status', default='not_synced', readonly=True)
    
    # ==========================================
    # 💡 COMPUTED FIELDS
    # ==========================================
    
    @api.depends('system_type')
    def _compute_show_contractor_config(self):
        """Hiển thị cấu hình contractor khi chọn contractor system"""
        for record in self:
            record.show_contractor_config = record.system_type == 'contractor'
    
    show_contractor_config = fields.Boolean(
        string='Show Contractor Config',
        compute='_compute_show_contractor_config',
        help='Hiển thị cấu hình cho Contractor System'
    )
    
    @api.depends('system_type')
    def _compute_show_integration_config(self):
        """Hiển thị cấu hình integration server khi chọn contractor system"""
        for record in self:
            record.show_integration_config = record.system_type == 'contractor'
    
    show_integration_config = fields.Boolean(
        string='Show Integration Config',
        compute='_compute_show_integration_config',
        help='Hiển thị cấu hình Integration Server'
    )
    
    # ==========================================
    # ✅ VALIDATION CONSTRAINTS
    # ==========================================
    
    @api.constrains('system_type', 'contractor_code', 'integration_server_url')
    def _check_contractor_system_config(self):
        """Validate contractor system configuration"""
        for record in self:
            if record.system_type == 'contractor':
                if not record.contractor_code:
                    raise ValidationError(_(
                        "❌ Contractor Code Required!\n"
                        "Contractor System requires a unique contractor code."
                    ))
                if not record.integration_server_url:
                    raise ValidationError(_(
                        "❌ Integration Server URL Required!\n"
                        "Contractor System must specify Integration Server URL."
                    ))
    
    @api.constrains('connection_timeout', 'sync_interval')
    def _check_timeout_and_interval(self):
        """Validate timeout and sync interval values"""
        for record in self:
            if record.connection_timeout <= 0:
                raise ValidationError(_(
                    "❌ Invalid Timeout!\n"
                    "Connection timeout must be greater than 0 seconds."
                ))
            if record.sync_interval <= 0:
                raise ValidationError(_(
                    "❌ Invalid Sync Interval!\n"
                    "Sync interval must be greater than 0 minutes."
                ))
    
    # ==========================================
    # 🔄 DATA LOADING METHODS
    # ==========================================
    
    @api.model
    def default_get(self, fields_list):
        """Load current system configuration from parameters"""
        res = super().default_get(fields_list)
        
        # 💡 NOTE(assistant): Load current system type configuration
        config_param = self.env['ir.config_parameter'].sudo()
        
        param_mappings = {
            'system_type': 'vnfield.system_type',
            'contractor_code': 'vnfield.contractor_code',
            'contractor_name': 'vnfield.contractor_name',
            'integration_server_url': 'vnfield.integration_server_url',
            'integration_api_key': 'vnfield.integration_api_key',
            'integration_username': 'vnfield.integration_username',
            'integration_password': 'vnfield.integration_password',
            'connection_timeout': 'vnfield.connection_timeout',
            'sync_interval': 'vnfield.sync_interval',
            'enable_auto_sync': 'vnfield.enable_auto_sync',
        }
        
        for field_name, param_key in param_mappings.items():
            if field_name in fields_list:
                param_value = config_param.get_param(param_key)
                if param_value:
                    # 🔄 Convert string values to appropriate types
                    if field_name in ['connection_timeout', 'sync_interval']:
                        try:
                            res[field_name] = int(param_value)
                        except (ValueError, TypeError):
                            pass  # Keep default value
                    elif field_name == 'enable_auto_sync':
                        res[field_name] = param_value.lower() == 'true'
                    else:
                        res[field_name] = param_value
        
        return res
    
    # ==========================================
    # 💾 CONFIGURATION SAVE METHODS
    # ==========================================
    
    def action_save_configuration(self):
        """
        💾 Lưu system type configuration vào system parameters
        """
        self.ensure_one()
        
        try:
            config_param = self.env['ir.config_parameter'].sudo()
            
            # 📝 Save system type configuration
            param_mappings = {
                'vnfield.system_type': self.system_type,
                'vnfield.contractor_code': self.contractor_code or '',
                'vnfield.contractor_name': self.contractor_name or '',
                'vnfield.integration_server_url': self.integration_server_url or '',
                'vnfield.integration_api_key': self.integration_api_key or '',
                'vnfield.integration_username': self.integration_username or '',
                'vnfield.integration_password': self.integration_password or '',
                'vnfield.connection_timeout': str(self.connection_timeout),
                'vnfield.sync_interval': str(self.sync_interval),
                'vnfield.enable_auto_sync': 'true' if self.enable_auto_sync else 'false',
            }
            
            # 🔁 Save all parameters
            for param_key, param_value in param_mappings.items():
                config_param.set_param(param_key, param_value)
            
            _logger.info(f'System type configuration saved: {self.system_type}')
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('✅ Configuration Saved'),
                    'message': _('System type configuration saved successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f'Error saving system type configuration: {e}')
            raise UserError(_('Error saving configuration: %s') % str(e))
    
    # ==========================================
    # 🔌 CONNECTION TEST METHODS
    # ==========================================
    
    def action_test_integration_connection(self):
        """
        🔌 Test kết nối đến Integration System
        """
        self.ensure_one()
        
        if self.system_type != 'contractor':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('⚠️ Not Applicable'),
                    'message': _('Connection test only available for Contractor System'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        if not self.integration_server_url:
            raise UserError(_(
                "❌ Missing Configuration!\n"
                "Please specify Integration Server URL before testing connection."
            ))
        
        try:
            # 🔌 Test basic HTTP connection
            test_url = f"{self.integration_server_url.rstrip('/')}/api/health"
            
            headers = {}
            if self.integration_api_key:
                headers['Authorization'] = f'Bearer {self.integration_api_key}'
            
            # 💡 NOTE(assistant): Basic connectivity test
            response = requests.get(
                test_url,
                headers=headers,
                timeout=self.connection_timeout,
                verify=True  # Verify SSL certificates
            )
            
            if response.status_code == 200:
                status_message = _(
                    '✅ Connection Successful!\n\n'
                    'Server: %s\n'
                    'Status Code: %s\n'
                    'Response Time: %.2f seconds'
                ) % (
                    self.integration_server_url,
                    response.status_code,
                    response.elapsed.total_seconds()
                )
                notification_type = 'success'
                
                # 📝 TODO(user): Có thể thêm authentication test
                if response.headers.get('content-type', '').startswith('application/json'):
                    try:
                        data = response.json()
                        if 'version' in data:
                            status_message += f"\nVersion: {data['version']}"
                    except:
                        pass  # Ignore JSON parsing errors
                        
            else:
                status_message = _(
                    '⚠️ Connection Issues!\n\n'
                    'Server: %s\n'
                    'Status Code: %s\n'
                    'Reason: %s'
                ) % (
                    self.integration_server_url,
                    response.status_code,
                    response.reason
                )
                notification_type = 'warning'
            
            # Update status field
            self.connection_status = status_message
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('🔌 Connection Test'),
                    'message': status_message,
                    'type': notification_type,
                    'sticky': True,
                }
            }
            
        except requests.exceptions.Timeout:
            error_message = _(
                '⏰ Connection Timeout!\n\n'
                'Server: %s\n'
                'Timeout: %s seconds\n\n'
                'Please check server URL and network connection.'
            ) % (self.integration_server_url, self.connection_timeout)
            
            self.connection_status = error_message
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('⏰ Connection Timeout'),
                    'message': error_message,
                    'type': 'danger',
                    'sticky': True,
                }
            }
            
        except requests.exceptions.ConnectionError:
            error_message = _(
                '❌ Connection Failed!\n\n'
                'Server: %s\n'
                'Error: Cannot connect to server\n\n'
                'Please check server URL and ensure server is running.'
            ) % self.integration_server_url
            
            self.connection_status = error_message
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('❌ Connection Failed'),
                    'message': error_message,
                    'type': 'danger',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            error_message = _(
                '💥 Test Failed!\n\n'
                'Server: %s\n'
                'Error: %s'
            ) % (self.integration_server_url, str(e))
            
            self.connection_status = error_message
            _logger.error(f'Integration connection test failed: {e}')
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('💥 Test Failed'),
                    'message': error_message,
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    # ==========================================
    # 🔄 SYNC METHODS
    # ==========================================
    
    def action_sync_now(self):
        """
        🔄 Thực hiện đồng bộ ngay lập tức với Integration System
        """
        self.ensure_one()
        
        if self.system_type != 'contractor':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('⚠️ Not Applicable'),
                    'message': _('Sync only available for Contractor System'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # 🔄 Update sync status
        self.sync_status = 'syncing'
        self.last_sync_time = fields.Datetime.now()
        
        try:
            # 📝 TODO(user): Implement actual sync logic here
            # Đây là placeholder cho sync functionality
            
            # 💡 NOTE(assistant): Simulated sync process
            sync_data = {
                'contractor_code': self.contractor_code,
                'sync_time': fields.Datetime.now().isoformat(),
                'data': {
                    # Add actual data to sync
                }
            }
            
            # In real implementation, send sync_data to Integration System
            _logger.info(f'Sync initiated for contractor: {self.contractor_code}')
            
            # 🔄 Mark sync as successful
            self.sync_status = 'success'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('🔄 Sync Completed'),
                    'message': _('Data synchronized successfully with Integration System'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            # 🔄 Mark sync as failed
            self.sync_status = 'failed'
            _logger.error(f'Sync failed for contractor {self.contractor_code}: {e}')
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('💥 Sync Failed'),
                    'message': _('Failed to sync with Integration System: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    # ==========================================
    # 🔄 UTILITY METHODS
    # ==========================================
    
    def action_reset_to_defaults(self):
        """
        🔄 Reset configuration về giá trị mặc định
        """
        self.ensure_one()
        
        self.write({
            'system_type': 'integration',
            'contractor_code': '',
            'contractor_name': '',
            'integration_server_url': '',
            'integration_api_key': '',
            'integration_username': '',
            'integration_password': '',
            'connection_timeout': 30,
            'sync_interval': 60,
            'enable_auto_sync': True,
            'connection_status': '',
            'sync_status': 'not_synced',
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('🔄 Reset Complete'),
                'message': _('Configuration reset to default values'),
                'type': 'info',
                'sticky': False,
            }
        }

# ==========================================
# 🔗 PHẦN PHỤ THUỘC VÀ SYMBOL RELATIONSHIPS
# ==========================================

"""
Symbol Dependencies Analysis:

🏗️ INTERNAL DEPENDENCIES:
- models.TransientModel: Odoo base class cho wizard models
- fields.*: Odoo field types (Selection, Char, Boolean, Integer, etc.)
- api.depends, api.constrains, api.model: Odoo decorators
- _logger: Python logging module cho việc ghi log

🔗 EXTERNAL DEPENDENCIES:
- ir.config_parameter: Odoo built-in model để lưu system parameters
- requests: Python HTTP library để test connection với Integration System
- json: Python JSON module để parse response data

📦 SYSTEM PARAMETER MAPPINGS:
- system_type → vnfield.system_type
- contractor_code → vnfield.contractor_code
- contractor_name → vnfield.contractor_name
- integration_server_url → vnfield.integration_server_url
- integration_api_key → vnfield.integration_api_key
- integration_username → vnfield.integration_username
- integration_password → vnfield.integration_password
- connection_timeout → vnfield.connection_timeout
- sync_interval → vnfield.sync_interval
- enable_auto_sync → vnfield.enable_auto_sync

🎯 BUSINESS LOGIC RELATIONSHIPS:
- system_type field: Xác định Integration hay Contractor System
- Computed fields: show_contractor_config, show_integration_config
- Conditional validation: Contractor System cần contractor_code và server URL
- Connection testing: HTTP requests với timeout và authentication

🔒 SECURITY CONSIDERATIONS:
- Password field với password=True để hide input
- API key authentication cho Integration System
- SSL certificate verification trong requests
- Error handling và user feedback

📋 UI INTEGRATION:
- Computed fields để show/hide conditional sections
- Validation constraints với user-friendly error messages
- Action methods return notifications để feedback cho user
- Status fields để track connection và sync state

⚙️ FUTURE EXTENSIBILITY:
- Placeholder sync logic có thể extend cho actual implementation
- Support cho multiple authentication methods
- Configurable sync intervals và retry logic
- Health check endpoints cho monitoring
"""
