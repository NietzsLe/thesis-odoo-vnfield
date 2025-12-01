# -*- coding: utf-8 -*-

"""
=====================================
🏗️ VN FIELD SYSTEM TYPE CONFIG WIZARD
=====================================

Mô tả:
    Wizard cấu hình loại hệ thống.
    Cho phép chọn giữa Integration System và Contractor System.

Tính năng:
    - Lựa chọn system type: Integration hoặc Contractor
    - Cấu hình Integration System server cho Contractor System

Created: 2025-08-20
Author: GitHub Copilot
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging

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
    
    system_name = fields.Char(
        string='System Name',
        required=True,
        help='Tên định danh của hệ thống này (ví dụ: VNField Central, Contractor ABC, etc.)'
    )
    
    # ==========================================
    # 🔗 INTEGRATION SYSTEM CONNECTION
    # ==========================================
    
    integration_server_url = fields.Char(
        string='Integration Server URL',
        help='URL của Integration System server (ví dụ: https://integration.vnfield.com)'
    )
    
    # ==========================================
    # 💡 COMPUTED FIELDS
    # ==========================================
    
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
    
    @api.constrains('system_type', 'integration_server_url')
    def _check_contractor_system_config(self):
        """Validate contractor system configuration"""
        for record in self:
            if record.system_type == 'contractor':
                if not record.integration_server_url:
                    raise ValidationError(_(
                        "❌ Integration Server URL Required!\n"
                        "Contractor System must specify Integration Server URL."
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
            'system_name': 'vnfield.system_name',
            'integration_server_url': 'vnfield.integration_server_url',
        }
        
        for field_name, param_key in param_mappings.items():
            if field_name in fields_list:
                param_value = config_param.get_param(param_key)
                if param_value:
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
                'vnfield.system_name': self.system_name or '',
                'vnfield.integration_server_url': self.integration_server_url or '',
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
# 🔗 PHẦN PHỤ THUỘC VÀ SYMBOL RELATIONSHIPS
# ==========================================

"""
Symbol Dependencies Analysis:

🏗️ INTERNAL DEPENDENCIES:
- models.TransientModel: Odoo base class cho wizard models
- fields.*: Odoo field types (Selection, Char, Boolean)
- api.depends, api.constrains, api.model: Odoo decorators
- _logger: Python logging module cho việc ghi log

🔗 EXTERNAL DEPENDENCIES:
- ir.config_parameter: Odoo built-in model để lưu system parameters

📦 SYSTEM PARAMETER MAPPINGS:
- system_type → vnfield.system_type
- system_name → vnfield.system_name
- integration_server_url → vnfield.integration_server_url

🎯 BUSINESS LOGIC RELATIONSHIPS:
- system_type field: Xác định Integration hay Contractor System
- Computed field: show_integration_config
- Conditional validation: Contractor System cần server URL

🔒 SECURITY CONSIDERATIONS:
- Validation constraints với user-friendly error messages
- Error handling và user feedback

📋 UI INTEGRATION:
- Computed field để show/hide conditional sections
- Action method return notifications để feedback cho user

⚙️ SIMPLIFIED DESIGN:
- Chỉ giữ lại system type selection và integration server URL
- Loại bỏ các trường phức tạp như authentication, sync settings
- Đơn giản hóa validation và configuration storage
"""
