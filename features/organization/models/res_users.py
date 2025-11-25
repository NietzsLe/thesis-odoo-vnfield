# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import AccessError

# ===========================================
# =      👤 EXTEND RES.USERS MODEL           =
# ===========================================

class ResUsers(models.Model):

    _inherit = 'res.users'
    # Định nghĩa lại trường name cho res.users: Char, required, lưu trực tiếp
    name = fields.Char(
        related='partner_id.name',
        store=True,
        help='Tên hiển thị của người dùng (không related partner)'
    )
    
    contractor_id = fields.Many2one('vnfield.contractor', string='Contractor')
    subcontractor_id = fields.Many2one('vnfield.subcontractor', string='Subcontractor')
    external_id = fields.Char(string='External ID', help='ID trên hệ tích hợp nếu đã đăng ký')
    external_login = fields.Char(string='External Login')
    external_password = fields.Char(string='External Password')
    user_type = fields.Selection([
        ('internal', 'Internal - Nội bộ'),
        ('external', 'External - Bên ngoài'),
        ('shared', 'Shared - Liên nhà thầu')
    ], string='User Type', compute='_compute_user_type', store=True)

    # 🎯 VNField Groups: Field riêng cho VNField groups với domain filter
    vnfield_groups_id = fields.Many2many(
        'res.groups',
        'vnfield_res_users_groups_rel',  # Custom relation table
        'user_id',
        'group_id', 
        string='Nhóm Quyền VNField',
        domain=lambda self: self._get_vnfield_groups_domain(),
        help='Chọn các nhóm quyền VNField cho người dùng này'
    )
    # ─────────────────────────────────────────────
    # ▶ FIELD LOGIN INPUT GIẢ (KHÔNG LƯU DB)
    # ─────────────────────────────────────────────
    login_input = fields.Char(
        string='Login (Input)',
        compute='_compute_login_input',
        inverse='_inverse_login_input',
        store=False,
        help='Trường nhập liệu login giả, dùng cho giao diện. Khi lưu sẽ gán vào login thật.'
    )
    
    @api.onchange('login_input')
    def _onchange_login_input_sync_login(self):
        """
        ĐỒNG BỘ GIAO DIỆN: Khi nhập login_input trên giao diện, cập nhật luôn login thật (2 chiều UI)
        """
        for rec in self:
            if rec.login_input:
                rec.login = rec.login_input

    @api.depends('login')
    def _compute_login_input(self):
        for rec in self:
            rec.login_input = rec.login

    def _inverse_login_input(self):
        for rec in self:
            if rec.login_input:
                rec.login = rec.login_input


    @api.model 
    def _sync_vnfield_groups_to_groups_id(self):
        """
        🔄 ĐỒNG BỘ: Đồng bộ vnfield_groups_id vào groups_id
        - Thêm các group VNField được chọn vào groups_id
        - Giữ nguyên các group khác đã có
        """
        for user in self:
            # Thêm các vnfield groups vào groups_id (không xóa groups cũ)
            user.groups_id = user.groups_id | user.vnfield_groups_id
            
    @api.model
    def write(self, vals):
        """
        ✏️ OVERRIDE WRITE: Đồng bộ vnfield_groups_id vào groups_id khi có thay đổi
        """
        result = super().write(vals)
        if 'vnfield_groups_id' in vals:
            self._sync_vnfield_groups_to_groups_id()
        return result

    @api.model
    def _get_vnfield_groups_domain(self):
        """
        🎯 DOMAIN: Trả về domain cho groups_id field  
        - Chỉ hiển thị các group thuộc VNField category
        """
        category = self.env.ref('vnfield.module_category_vnfield', raise_if_not_found=False)
        if category:
            return [('category_id', '=', category.id)]
        return [('id', '=', False)]  # Không có category thì không hiển thị gì

    @api.depends('contractor_id', 'contractor_id.contractor_type')
    def _compute_user_type(self):
        for record in self:
            record.user_type = record.contractor_id.contractor_type if record.contractor_id else 'internal'

    @api.model
    def create(self, vals):
        """
        Override create method để đảm bảo user được tạo đúng cách
        khi tạo user từ contractor form
        """
        # 💡 ĐỒNG BỘ login_input → login nếu có
        if vals.get('login_input'):
            vals['login'] = vals['login_input']
        # ...existing code...
        print(f"DEBUG: User creation vals: {vals}")
        
        # �📧 EMAIL FALLBACK: Nếu không có login thì sử dụng email
        if not vals.get('login'):
            if vals.get('email') and vals.get('email') != False:
                vals['login'] = vals['email']
                print(f"DEBUG: Using email as login: {vals['email']}")
            else:
                print("DEBUG: No login or email provided, raising error")
                raise ValueError("Login field or Email is required for creating users")
        
        # 🎯 SIMPLIFIED: Let Odoo handle partner creation automatically
        # res.users sẽ tự động tạo partner nếu cần, không cần tạo manual
        # Loại bỏ logic tạo partner phức tạp để tránh lỗi validation
        
        print(f"DEBUG: Final vals before super(): {vals}")
        user = super(ResUsers, self).create(vals)
        
        # 🛡️ ENSURE BASIC GROUPS: Đảm bảo user có quyền cơ bản
        self._ensure_basic_groups(user)
        
        return user

    @api.model
    def _ensure_basic_groups(self, user):
        """
        🛡️ ĐẢM BẢO QUYỀN CƠ BẢN: Thêm các group cơ bản cho user
        - Internal User group cho quyền truy cập cơ bản
        """
        basic_group = self.env.ref('base.group_user', raise_if_not_found=False)
        if basic_group and basic_group not in user.groups_id:
            user.groups_id = user.groups_id | basic_group

    def write(self, vals):
        """
        ✏️ OVERRIDE WRITE: Merge toàn bộ logic kiểm tra quyền, đồng bộ group, đồng bộ login_input
        
        Logic:
        - Nếu user không có contractor → có thể edit
        - Nếu user có contractor → current user phải cùng contractor mới được edit
        - Đồng bộ login_input → login nếu có
        - Đồng bộ vnfield_groups_id vào groups_id khi có thay đổi
        """
        # 💡 ĐỒNG BỘ login_input → login nếu có
        if vals.get('login_input'):
            vals['login'] = vals['login_input']

        # 🔒 PERMISSION CHECK: Kiểm tra quyền edit cho từng user
        for user in self:
            if not user.can_current_user_edit():
                raise AccessError(
                    _("Access Denied: You can only edit users from the same contractor or users without contractor assignment.")
                )

        # 📨 ĐỒNG BỘ LOGIN = EMAIL KHI CẬP NHẬT EMAIL (nếu login chưa có trong vals hoặc login cũ == email cũ)
        if 'email' in vals:
            for user in self:
                old_email = user.email or False
                old_login = user.login or False
                new_email = vals['email']
                if ('login' not in vals) and (old_login == old_email):
                    vals['login'] = new_email

        # Gọi super để thực hiện ghi dữ liệu
        result = super().write(vals)

        # 🔄 ĐỒNG BỘ VNFIELD GROUPS: Nếu có thay đổi vnfield_groups_id thì đồng bộ vào groups_id
        if 'vnfield_groups_id' in vals:
            self._sync_vnfield_groups_to_groups_id()

        return result

    # ─────────────────────────────────────────────
    # ▶ PROJECT ASSIGNMENT ACTIONS
    # ─────────────────────────────────────────────

    def can_current_user_add_to_project(self):
        """
        🔒 HELPER METHOD: Kiểm tra current user có thể add user này vào project không
        
        Returns:
            bool: True nếu current user có thể add user này vào project
        """
        current_user = self.env.user
        
        # Kiểm tra current user có contractor không
        if not current_user.contractor_id:
            return False
            
        # Kiểm tra user đang xem có contractor không  
        if not self.contractor_id:
            return False
            
        # So sánh contractor của current user và user đang xem
        return current_user.contractor_id.id == self.contractor_id.id

    def can_current_user_edit(self):
        """
        ✏️ HELPER METHOD: Kiểm tra current user có thể edit user này không
        
        Logic:
        - Nếu user không có contractor → có thể edit
        - Nếu user có contractor → current user phải cùng contractor mới được edit
        
        Returns:
            bool: True nếu current user có thể edit user này
        """
        current_user = self.env.user
        
        # Kiểm tra user đang edit có contractor không
        if not self.contractor_id:
            # User không có contractor → có thể edit
            return True
            
        # User có contractor → kiểm tra current user có cùng contractor không
        if not current_user.contractor_id:
            # Current user không có contractor nhưng user đang edit có → không được edit
            return False
            
        # So sánh contractor của current user và user đang edit
        return current_user.contractor_id.id == self.contractor_id.id

    def action_add_to_project(self):
        """
        📂 ACTION: Thêm user vào Project với kiểm tra permission
        
        Kiểm tra permission trước khi cho phép thực hiện action
        """
        # 🔒 PERMISSION CHECK: Kiểm tra current user có quyền add user này không
        if not self.can_current_user_add_to_project():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'You can only add users from the same contractor to projects!',
                    'type': 'warning',
                }
            }

    def action_register_user(self):
        """
        📝 ACTION: Đăng ký user vào hệ thống external
        
        Logic:
        - Kiểm tra user là external/shared và chưa được đăng ký
        - Produce message đến pubsub service để gửi thông tin user tới external system
        - Hiển thị notification thành công/thất bại
        
        Returns:
            dict: Action result (notification về việc gửi message)
        """
        for record in self:
            # Kiểm tra điều kiện: chỉ cho phép external/shared user
            if record.user_type not in ['external', 'shared']:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Only external/shared users can be registered!',
                        'type': 'warning',
                    }
                }
            
            # Kiểm tra đã được đăng ký chưa
            if record.external_id:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': f'User {record.name} is already registered with external ID: {record.external_id}',
                        'type': 'warning',
                    }
                }
            
            # Produce message đến external system
            try:
                # Get system_name từ config
                config_param = self.env['ir.config_parameter'].sudo()
                system_name = config_param.get_param('vnfield.system_name', 'Unknown System')
                
                # Chuẩn bị message data
                message_data = {
                    'action': 'register_user',
                    'source': system_name,
                    'destination': 'external_system',
                    'user_data': {
                        'name': record.name,
                        'login': record.login,
                        'email': record.email,
                        'contractor_id': record.contractor_id.id if record.contractor_id else None,
                        'contractor_external_id': record.contractor_id.external_id if record.contractor_id else None,
                        'user_type': record.user_type,
                    },
                    'vals': {
                        'id': record.id,
                        'name': record.name,
                        'login': record.login,
                        'email': record.email,
                    },
                    'extra': {
                        'timestamp': fields.Datetime.now().isoformat(),
                        'source_contractor': record.contractor_id.external_id if record.contractor_id else None,
                    }
                }
                
                # Get topic từ config
                topic = config_param.get_param('vnfield.kafka.topic', 'vnfield')
                
                # Produce message
                pubsub_service = self.env['vnfield.pubsub.service'].create({})
                result = pubsub_service.produce_message(topic, message_data)
                
                if result and result.get('success'):
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': f'Registration request for {record.name} sent successfully to external system!',
                            'type': 'success',
                        }
                    }
                else:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': f'Failed to send registration request: {result.get("error", "Unknown error") if result else "Service unavailable"}',
                            'type': 'error',
                        }
                    }
                    
            except Exception as e:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': f'Error sending registration request: {str(e)}',
                        'type': 'error',
                    }
                }

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
        return pubsub_service.consume_messages(topic, group_id=system_name, timeout=30, message_handler=self.message_handler)

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
        
        # 📨 XỬ LÝ THEO ACTION NAME
        if action_name == 'register_user_map':
            # Xử lý response từ external system về việc đăng ký user
            external_id = vals.get('external_id')
            user_id = vals.get('user_id')
            
            if external_id and user_id:
                # Tìm user và cập nhật external_id
                user = self.env['res.users'].sudo().browse(user_id)
                if user.exists():
                    user.write({'external_id': external_id})
                    return {
                        'result': 'success',
                        'action': 'register_user_map',
                        'message': f'Updated external_id for user {user.name}'
                    }
            
            return {
                'result': 'error',
                'action': 'register_user_map',
                'message': 'Missing external_id or user_id in message'
            }
        
        elif action_name == 'create_user':
            # Tạo sync_request record với JSON content từ message
            try:
                sync_request = self.env['vnfield.sync.request'].sudo().create({
                    'activity_name': f"Create User Request - {vals.get('name', 'Unknown')}",
                    'description': f"Message content: {str(value)}",  # Lưu toàn bộ message content trong description
                    'sync_type': 'import',  # Sử dụng 'import' thay vì 'user_sync'
                    'priority': 'normal',   # Sử dụng 'normal' thay vì 'medium'
                })
                
                return {
                    'result': 'success',
                    'action': 'create_user',
                    'message': f'Created sync_request record with ID: {sync_request.id}',
                    'sync_request_id': sync_request.id
                }
                
            except Exception as e:
                return {
                    'result': 'error',
                    'action': 'create_user',
                    'message': f'Failed to create sync_request: {str(e)}'
                }
        
        else:
            return {
                'result': 'error',
                'reason': f'Unknown action: {action_name}'
            }