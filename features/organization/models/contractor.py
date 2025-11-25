# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

# ===========================================
# =         🏢 CONTRACTOR MODEL             =
# ===========================================

class Contractor(models.Model):

    """
    Contractor model quản lý các nhà thầu nội bộ và bên ngoài.
    - Có thể là internal hoặc external contractor
    - Có external_id nếu đã đăng ký với ứng dụng tích hợp
    """
    _name = 'vnfield.contractor'
    _description = 'Contractor'

    name = fields.Char(string='Contractor Name', required=True)
    description = fields.Text(string='Description', help='Mô tả chi tiết về nhà thầu')
    external_id = fields.Char(string='External ID', help='ID trên hệ tích hợp nếu đã đăng ký')
    contractor_type = fields.Selection([
        ('internal', 'Internal - Nội bộ'),
        ('external', 'External - Bên ngoài'), 
        ('shared', 'Shared - Liên nhà thầu')
    ], string='Contractor Type', default='internal', required=True)
    
    representative_url = fields.Char(
        string='Representative Server URL', 
        help='Link HTTP để kiểm tra server của contractor'
    )
    
    project_director_ids_readonly = fields.Boolean(
        compute='_compute_project_director_ids_readonly',
        string='Readonly Project Directors',
        default=True
    )
    bidding_manager_ids_readonly = fields.Boolean(
        compute='_compute_bidding_manager_ids_readonly',
        string='Readonly Bidding Managers',
        default=True
    )
    director_id_readonly = fields.Boolean(
        compute='_compute_director_id_readonly',
        string='Readonly Director',
        default=True
    )


    # ─────────────────────────────────────────────
    # ▶ RELATIONSHIP FIELDS 
    # ─────────────────────────────────────────────

    # ─────────────────────────────────────────────
    # ▶ SPECIAL ROLES FIELDS
    # ─────────────────────────────────────────────
    director_id = fields.Many2one(
        'res.users',
        string='Director',
        help='Người chịu trách nhiệm chính của contractor này'
    )
    
    project_director_ids = fields.Many2many(
        'res.users',
        'contractor_project_director_rel',
        'contractor_id',
        'user_id',
        string='Project Directors',
        help='Các Project Director thuộc contractor này'
    )
    bidding_manager_ids = fields.Many2many(
        'res.users',
        'contractor_bidding_manager_rel',
        'contractor_id',
        'user_id',
        string='Bidding Managers',
        help='Các Bidding Manager thuộc contractor này'
    )
    user_ids = fields.One2many('res.users', 'contractor_id', string='Users')
    
    team_ids = fields.One2many(
        'vnfield.team', 
        'contractor_id', 
        string='Teams',
        help='Các teams thuộc contractor này'
    )
    
    project_ids = fields.Many2many(
        'vnfield.project',
        'project_contractor_rel',
        'contractor_id',
        'project_id',
        string='Projects',
        help='Các projects mà contractor này tham gia'
    )
    
    # 📊 COMPUTED FIELDS: Counts để hiển thị trong kanban và buttons
    user_count = fields.Integer(
        string='User Count',
        compute='_compute_user_count',
        store=True,
        help='Số lượng users thuộc contractor này'
    )
    
    team_count = fields.Integer(
        string='Team Count',
        compute='_compute_team_count',
        store=True,
        help='Số lượng teams thuộc contractor này'
    )
    
    project_count = fields.Integer(
        string='Project Count', 
        compute='_compute_project_count',
        store=True,
        help='Số lượng projects mà contractor tham gia'
    )

    @api.model
    def write(self, vals):
        """
        ✏️ OVERRIDE WRITE: Log lại vals khi ghi dữ liệu vào contractor (debug)
        """
        print(f"[Contractor.write] vals: {vals}")
        return super().write(vals)
    
    @api.depends('director_id')
    def _compute_director_id_readonly(self):
        uid = self.env.uid
        for rec in self:
            # Chỉ readonly nếu record đã tồn tại và director_id khác uid
            if rec.id and rec.director_id and rec.director_id.id != uid:
                rec.director_id_readonly = True
            else:
                rec.director_id_readonly = False

    @api.model
    def create(self, vals):
        print(vals)
        if 'director_id' not in vals or not vals['director_id']:
            vals['director_id'] = self.env.uid
        return super().create(vals)

    @api.depends('director_id')
    def _compute_project_director_ids_readonly(self):
        uid = self.env.uid
        for rec in self:
            rec.project_director_ids_readonly = rec.director_id.id != uid

    @api.depends('director_id')
    def _compute_bidding_manager_ids_readonly(self):
        uid = self.env.uid
        for rec in self:
            rec.bidding_manager_ids_readonly = rec.director_id.id != uid

    @api.depends('user_ids')
    def _compute_user_count(self):
        """
        📊 COMPUTED FIELD: Tính số lượng users thuộc contractor
        Đảm bảo count chính xác cho hiển thị trong kanban view
        """
        for record in self:
            record.user_count = len(record.user_ids)
    
    @api.depends('team_ids')
    def _compute_team_count(self):
        """
        📊 COMPUTED FIELD: Tính số lượng teams thuộc contractor
        Sử dụng One2many relationship team_ids
        """
        for record in self:
            record.team_count = len(record.team_ids)
    
    @api.depends('project_ids')
    def _compute_project_count(self):
        """
        📊 COMPUTED FIELD: Tính số lượng projects mà contractor tham gia
        Sử dụng Many2many relationship project_ids
        """
        for record in self:
            record.project_count = len(record.project_ids)

    # ─────────────────────────────────────────────
    # ▶ ACTIONS: Các hành động người dùng có thể thực hiện
    # ─────────────────────────────────────────────

    def action_view_users(self):
        """
        👤 ACTION: Hiển thị tất cả users thuộc contractor này
        
        Returns:
            dict: Window action để hiển thị user kanban view
        """
        return {
            'type': 'ir.actions.act_window',
            'name': f'👤 View Users ({self.user_count})',
            'res_model': 'res.users',
            'view_mode': 'kanban,tree,form',
            'domain': [('contractor_id', '=', self.id)],
            'context': {'default_contractor_id': self.id},
            'target': 'current',
        }

    def action_view_projects(self):
        """
        📊 ACTION: Hiển thị tất cả projects mà contractor này tham gia
        
        Sử dụng Many2many relationship project_ids
        
        Returns:
            dict: Window action để hiển thị project kanban view
        """
        return {
            'type': 'ir.actions.act_window',
            'name': f'🏗️ View Projects ({self.project_count})',
            'res_model': 'vnfield.project',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', self.project_ids.ids)],
            'context': {'default_contractor_id': self.id},
            'target': 'current',
        }
    
    def action_view_teams(self):
        """
        👥 ACTION: Hiển thị tất cả teams thuộc contractor này
        
        Sử dụng One2many relationship team_ids
        
        Returns:
            dict: Window action để hiển thị team kanban view
        """
        return {
            'type': 'ir.actions.act_window',
            'name': f'👥 View Teams ({self.team_count})',
            'res_model': 'vnfield.team',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', self.team_ids.ids)],
            'context': {'default_contractor_id': self.id},
            'target': 'current',
        }

    def action_register_external(self):
        """
        🔧 ACTION: Đăng ký contractor với hệ thống tích hợp bên ngoài
        
        📝 TODO(user): Implement logic to register contractor with external system
        - Gọi API để đăng ký contractor
        - Lưu external_id nhận được từ API
        - Hiển thị thông báo thành công/thất bại
        
        Returns:
            dict: Action result (có thể là notification, redirect, etc.)
        """
        # 🕓 TEMP(assistant): Placeholder implementation - user sẽ cập nhật sau
        for record in self:
            if record.contractor_type == 'internal':
                continue
            
            # TODO: Implement external registration logic here
            # Example structure:
            # try:
            #     external_id = self._call_external_api_register(record)
            #     record.external_id = external_id
            #     return {
            #         'type': 'ir.actions.client',
            #         'tag': 'display_notification',
            #         'params': {
            #             'message': f'Contractor {record.name} registered successfully!',
            #             'type': 'success',
            #         }
            #     }
            # except Exception as e:
            #     return {
            #         'type': 'ir.actions.client', 
            #         'tag': 'display_notification',
            #         'params': {
            #             'message': f'Registration failed: {str(e)}',
            #             'type': 'danger',
            #         }
            #     }
            pass

    def action_check_server_status(self):
        """
        🔗 Kiểm tra trạng thái server của contractor qua representative_url
        Returns notification action
        """
        self.ensure_one()
        
        if not self.representative_url:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': '❌ No URL',
                    'message': 'No representative server URL configured.',
                    'sticky': True,
                }
            }
        
        try:
            import requests
            response = requests.get(self.representative_url, timeout=5)
            if response.status_code == 200:
                msg = f'Server is ONLINE. Status code: 200'
                msg_type = 'success'
                title = '✅ Server Online'
            else:
                msg = f'Server responded with status code: {response.status_code}'
                msg_type = 'warning'
                title = '⚠️ Server Issue'
        except Exception as e:
            msg = f'Failed to connect: {str(e)}'
            msg_type = 'danger'
            title = '❌ Connection Failed'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': msg_type,
                'title': title,
                'message': msg,
                'sticky': False,
            }
        }

    # ─────────────────────────────────────────────
    # ▶ RPC ENDPOINTS: API endpoints cho external systems
    # ─────────────────────────────────────────────

    @api.model
    def rpc_register_contractor(self, contractor_data):
        """
        🌐 RPC ENDPOINT: Đăng ký contractor từ external system
        
        Args:
            contractor_data (dict): Thông tin contractor cần đăng ký
                - name (str): Tên contractor
                - description (str): Mô tả
                - contractor_type (str): Loại contractor (internal/external/shared)
                - email (str): Email liên hệ
                - phone (str): Số điện thoại
                - address (str): Địa chỉ
                - website (str): Website
                - external_id (str, optional): ID từ hệ thống external
        
        Returns:
            dict: Kết quả đăng ký
                - success (bool): Thành công hay không
                - contractor_id (int): ID của contractor được tạo
                - message (str): Thông báo
                - data (dict): Thông tin contractor đã tạo
        
        Raises:
            ValidationError: Nếu dữ liệu không hợp lệ
            AccessError: Nếu không có quyền truy cập
        """
        try:
            # 🔍 Validate required fields
            required_fields = ['name', 'contractor_type']
            missing_fields = [field for field in required_fields if not contractor_data.get(field)]
            if missing_fields:
                return {
                    'success': False,
                    'message': f'Missing required fields: {", ".join(missing_fields)}',
                    'contractor_id': None,
                    'data': None
                }
            
            # 🔍 Validate contractor_type
            valid_types = ['internal', 'external', 'shared']
            if contractor_data.get('contractor_type') not in valid_types:
                return {
                    'success': False,
                    'message': f'Invalid contractor_type. Must be one of: {", ".join(valid_types)}',
                    'contractor_id': None,
                    'data': None
                }
            
            # 🔍 Check if contractor with same external_id already exists
            external_id = contractor_data.get('external_id')
            if external_id:
                existing = self.search([('external_id', '=', external_id)], limit=1)
                if existing:
                    return {
                        'success': False,
                        'message': f'Contractor with external_id "{external_id}" already exists (ID: {existing.id})',
                        'contractor_id': existing.id,
                        'data': {
                            'id': existing.id,
                            'name': existing.name,
                            'external_id': existing.external_id,
                            'contractor_type': existing.contractor_type
                        }
                    }
            
            # 🔍 Check if contractor with same name already exists
            existing_name = self.search([('name', '=', contractor_data.get('name'))], limit=1)
            if existing_name:
                return {
                    'success': False,
                    'message': f'Contractor with name "{contractor_data.get("name")}" already exists (ID: {existing_name.id})',
                    'contractor_id': existing_name.id,
                    'data': {
                        'id': existing_name.id,
                        'name': existing_name.name,
                        'external_id': existing_name.external_id,
                        'contractor_type': existing_name.contractor_type
                    }
                }
            
            # 🏗️ Create contractor
            contractor_vals = {
                'name': contractor_data.get('name'),
                'description': contractor_data.get('description', ''),
                'contractor_type': contractor_data.get('contractor_type'),
                'external_id': contractor_data.get('external_id'),
            }
            
            # 🔧 Set director_id if provided, otherwise use current user
            if contractor_data.get('director_id'):
                contractor_vals['director_id'] = contractor_data.get('director_id')
            
            contractor = self.create(contractor_vals)
            
            # 📋 Prepare response data
            response_data = {
                'id': contractor.id,
                'name': contractor.name,
                'description': contractor.description,
                'contractor_type': contractor.contractor_type,
                'external_id': contractor.external_id,
                'director_id': contractor.director_id.id if contractor.director_id else None,
                'director_name': contractor.director_id.name if contractor.director_id else None,
                'create_date': contractor.create_date.isoformat() if contractor.create_date else None,
            }
            
            return {
                'success': True,
                'message': f'Contractor "{contractor.name}" registered successfully',
                'contractor_id': contractor.id,
                'data': response_data
            }
            
        except ValidationError as e:
            return {
                'success': False,
                'message': f'Validation error: {str(e)}',
                'contractor_id': None,
                'data': None
            }
        except Exception as e:
            _logger.error(f"Error in rpc_register_contractor: {str(e)}")
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}',
                'contractor_id': None,
                'data': None
            }
