# -*- coding: utf-8 -*-

"""
=====================================
🔄 VN FIELD SYNC REQUEST MODEL
=====================================

Mô tả:
    Model quản lý các yêu cầu đồng bộ dữ liệu.
    Mỗi user chỉ có thể xem và quản lý các yêu cầu đồng bộ của mình.

Tính năng chính:
    - Tạo yêu cầu đồng bộ với tên hoạt động và mô tả
    - Theo dõi trạng thái của yêu cầu đồng bộ
    - Access control: chỉ người tạo mới xem được yêu cầu của mình
    - Workflow quản lý vòng đời của yêu cầu

Created: 2025-08-20
Author: GitHub Copilot
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class SyncRequest(models.Model):
    """
    =========================================
    📋 MODEL: vnfield.sync.request
    =========================================
    
    Mục đích:
        Quản lý các yêu cầu đồng bộ dữ liệu từ người dùng.
        Đảm bảo chỉ người tạo yêu cầu mới có thể xem và quản lý.
    
    Business Logic:
        - Mỗi user có thể tạo nhiều sync requests
        - User chỉ xem được các requests của mình
        - Workflow: draft → pending → processing → completed/failed
        - Tự động track người tạo và thời gian tạo
    """
    
    _name = 'vnfield.sync.request'
    _description = 'Sync Request Management'
    _order = 'create_date desc'
    _rec_name = 'activity_name'
    
    # 💡 NOTE(assistant): Enable automatic access logging
    _log_access = True

    # ==========================================
    # 📝 CORE FIELDS - THÔNG TIN CƠ BẢN
    # ==========================================
    
    activity_name = fields.Char(
        string='Activity Name',
        required=True,
        help='Tên hoạt động cần đồng bộ'
    )
    
    description = fields.Text(
        string='Description',
        help='Mô tả chi tiết về yêu cầu đồng bộ'
    )
    
    message_payload = fields.Text(
        string='Message Payload',
        help='Nội dung tin nhắn gốc từ Kafka topic'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),           # Nháp - mới tạo
        ('approved', 'Approved'),     # Đã duyệt
        ('rejected', 'Rejected'),     # Từ chối
    ], string='Status', default='draft', required=True, tracking=True,
       help='Trạng thái hiện tại của yêu cầu đồng bộ')

    # ==========================================
    # 📁 ARCHIVE FUNCTIONALITY - CHỨC NĂNG LƯU TRỮ
    # ==========================================
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Bỏ tick để archive sync request này. Các record đã archive sẽ không hiển thị trong danh sách mặc định.'
    )
    
    # ==========================================
    #  METADATA FIELDS - THÔNG TIN BỔ SUNG
    # ==========================================
    # ==========================================
    # 📅 COMPUTED FIELDS - TRƯỜNG TÍNH TOÁN
    # ==========================================
    
    @api.depends('create_date')
    def _compute_display_create_date(self):
        """Tính toán hiển thị ngày tạo với format dễ đọc"""
        for record in self:
            if record.create_date:
                record.display_create_date = record.create_date.strftime('%d/%m/%Y %H:%M')
            else:
                record.display_create_date = ''
    
    display_create_date = fields.Char(
        string='Created On',
        compute='_compute_display_create_date',
        store=False,
        help='Ngày tạo yêu cầu (định dạng dễ đọc)'
    )
    
    @api.depends('state')
    def _compute_is_active_request(self):
        """Kiểm tra xem request có đang active không"""
        for record in self:
            record.is_active_request = record.state == 'draft'
    
    is_active_request = fields.Boolean(
        string='Is Active',
        compute='_compute_is_active_request',
        store=True,
        help='Request đang active hay không'
    )
    
    # ==========================================
    # 🎯 ACTION METHODS - PHƯƠNG THỨC HÀNH ĐỘNG
    # ==========================================
    
    def action_approve(self):
        """Phê duyệt yêu cầu đồng bộ và xử lý business logic"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Chỉ có thể phê duyệt yêu cầu ở trạng thái Draft!"))
            
            # 🎯 XỬ LÝ BUSINESS LOGIC theo action type
            try:
                # Parse message payload để lấy thông tin action
                import ast
                if record.message_payload:
                    try:
                        message_data = ast.literal_eval(record.message_payload)
                        action_name = message_data.get('action')
                        vals = message_data.get('vals', {})
                        extra = message_data.get('extra', {})
                        
                        # 🏗️ XỬ LÝ MATCH CAPACITY PROFILE - tạo project mới
                        if action_name == 'match_capacity_profile':
                            requirement_id = vals.get('requirement_id')
                            capacity_profile_id = vals.get('capacity_profile_id')
                            requirement_title = vals.get('requirement_title', f'Requirement {requirement_id}')
                            task_id = vals.get('task_id')
                            
                            if requirement_id and capacity_profile_id:
                                # Tạo project name từ requirement title
                                project_name = f"Project for {requirement_title}"
                                
                                # Tạo project mới (không cần kiểm tra requirement vì là remote)
                                project = self.env['vnfield.project'].sudo().create({
                                    'name': project_name,
                                    'source_task_id': task_id,  # Lưu task_id từ message
                                    'is_outsourced': True,  # Đánh dấu là project outsource
                                    'description': f"Project created from capacity profile match\nRequirement: {requirement_title}\nRemote Requirement ID: {requirement_id}\nCapacity Profile ID: {capacity_profile_id}\nCreated by sync request: {record.activity_name}",
                                })
                                
                                _logger.info(f"✅ Created project ID: {project.id} from sync_request ID: {record.id}")
                                
                                # Cập nhật description của sync_request để ghi lại kết quả
                                record.description = f"{record.description}\n\n🎉 RESULT: Created project '{project.name}' (ID: {project.id})"
                                
                            else:
                                _logger.warning(f"⚠️ Missing requirement_id or capacity_profile_id in message")
                                record.description = f"{record.description}\n\n❌ ERROR: Missing requirement_id or capacity_profile_id"
                        
                        # 🔄 XỬ LÝ CÁC ACTION KHÁC - có thể thêm sau
                        elif action_name == 'register_user_map':
                            _logger.info(f"📝 Approved register_user_map action for sync_request ID: {record.id}")
                            
                        elif action_name == 'create_user':
                            _logger.info(f"📝 Approved create_user action for sync_request ID: {record.id}")
                            
                        else:
                            _logger.info(f"📝 Approved unknown action '{action_name}' for sync_request ID: {record.id}")
                            
                    except (ValueError, SyntaxError) as e:
                        _logger.error(f"❌ Failed to parse message_payload: {str(e)}")
                        record.description = f"{record.description}\n\n❌ ERROR: Failed to parse message payload"
                        
            except Exception as e:
                _logger.error(f"❌ Error during approve processing: {str(e)}")
                record.description = f"{record.description}\n\n❌ ERROR: {str(e)}"
                
            # ✅ CẬP NHẬT STATE cuối cùng
            record.state = 'approved'
            
        return True
    
    def action_reject(self):
        """Từ chối yêu cầu đồng bộ"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Chỉ có thể từ chối yêu cầu ở trạng thái Draft!"))
            record.state = 'rejected'
        return True
    
    def action_archive(self):
        """Lưu trữ yêu cầu đồng bộ"""
        # Handle both single and multiple records properly
        for record in self:
            record.active = False
        return True
    
    def toggle_active(self):
        """Toggle trạng thái active/inactive của yêu cầu đồng bộ"""
        # Handle both single and multiple records properly
        for record in self:
            record.active = not record.active
        return True
    
    # ==========================================
    # 🔄 KAFKA CONSUME METHOD
    # ==========================================
    
    @api.model
    def consume(self):
        """
        Consume message from pubsub_service, xử lý qua message_handler callback.
        """
        config_param = self.env['ir.config_parameter'].sudo()
        topic = config_param.get_param('vnfield.kafka.topic', 'vnfield')
        system_name = config_param.get_param('vnfield.system_name', 'Unknown System')
        
        pubsub_service = self.env['vnfield.pubsub.service'].create({})
        print(f"DEBUG: Consuming messages from topic: {topic} with group_id: {system_name}")
        
        # Truyền message_handler làm callback cho consume_message
        return pubsub_service.consume_messages(topic, group_id=system_name, timeout=10, message_handler=self.message_handler)

    def message_handler(self, headers, value):
        """
        Xử lý message: lọc message theo destination, chia nhánh action name để gọi handler_* với handle_type='consume'.
        Chỉ xử lý message có destination trùng với system_name hiện tại.
        """
        # 🔍 FILTER: Chỉ xử lý message có destination là system này
        config_param = self.env['ir.config_parameter'].sudo()
        current_system_name = config_param.get_param('vnfield.system_name', 'Unknown System')
        message_destination = value.get('destination')
        
        # Bỏ qua message không có destination
        if not message_destination:
            return {
                'result': 'message_ignored', 
                'reason': 'No destination specified in message'
            }
        
        # Bỏ qua message không dành cho system này
        if message_destination != current_system_name:
            return {
                'result': 'message_ignored',
                'reason': 'Message not for this system',
                'current_system': current_system_name,
                'message_destination': message_destination
            }
        
        action_name = value.get('action')
        vals = value.get('vals', {})
        extra = value.get('extra', {})
        
        # 📝 TẠO SYNC REQUEST MỚI từ thông tin message
        try:
            # Tạo activity name dựa trên action
            activity_name = f"{action_name.replace('_', ' ').title()} - {message_destination}"
            
            # Tạo description từ vals và extra
            description_parts = []
            if vals:
                description_parts.append(f"Message data: {str(vals)}")
            if extra:
                description_parts.append(f"Extra info: {str(extra)}")
            
            description = "\n".join(description_parts) if description_parts else f"Action: {action_name}"
            
            # Tạo sync_request record
            sync_request = self.env['vnfield.sync.request'].sudo().create({
                'activity_name': activity_name,
                'description': description,
                'message_payload': str(value),  # Lưu toàn bộ message content
                'state': 'draft',  # Tạo ở trạng thái draft để chờ approve/reject
            })
            
            _logger.info(f"✅ Created sync_request ID: {sync_request.id} for action: {action_name}")
            
            # � CHỈ TẠO SYNC_REQUEST - không xử lý logic business tại đây
            return {
                'result': 'success',
                'action': action_name,
                'message': f'Created sync_request for action: {action_name}',
                'sync_request_id': sync_request.id
            }
                
        except Exception as e:
            _logger.error(f"❌ Failed to create sync_request: {str(e)}")
            return {
                'result': 'error',
                'reason': f'Failed to create sync_request: {str(e)}',
                'action': action_name
            }
        
        
    # ==========================================
    # 🔍 OVERRIDE METHODS - GHI ĐÈ PHƯƠNG THỨC
    # ==========================================
    
    @api.model
    def create(self, vals):
        """Override create để log thông tin"""
        result = super(SyncRequest, self).create(vals)
        _logger.info(f"📝 New sync request created: '{result.activity_name}'")
        return result
    
    def unlink(self):
        """Override unlink để kiểm tra business logic"""
        for record in self:
            if record.state == 'approved':
                raise UserError(_("❌ Không thể xóa yêu cầu đã được phê duyệt!"))
        
        activity_names = [r.activity_name for r in self]
        result = super(SyncRequest, self).unlink()
        _logger.info(f"🗑️ Sync requests deleted: {', '.join(activity_names)}")
        return result
