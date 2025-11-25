# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

# =           🔐 APPROVAL MODEL                   # 🔒 REVIEW(assistant): Sử dụng helper method để check protection
# ===========================================

class Approval(models.Model):
    """
    ┌──────────────────────────────────────────────────────┐
    │    🧰 CHỨC NĂNG: QUẢN LÝ APPROVAL PROCESS               │
    │                                                      │
    │ - Đại diện cho một approval tổng hợp nhiều bước      │
    │ - Theo dõi ai gửi approval và tư cách gì             │
    │ - Hỗ trợ internal/shared classification              │
    │ - Validation tự động cho submission tracking         │
    └──────────────────────────────────────────────────────┘
    """
    _name = 'vnfield.approval'
    _description = 'Approval Process'
    _order = 'create_date desc, id desc'

    # ─────────────────────────────────────────────
    # ▶ CORE APPROVAL FIELDS
    # ─────────────────────────────────────────────
    
    name = fields.Char(string='Approval Name', required=True)
    description = fields.Text(string='Description')
    
    step_ids = fields.One2many(
        'vnfield.approval.step', 
        'approval_id', 
        string='Approval Steps', 
        help='Các bước phê duyệt tuần tự'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='State', default='draft')
    
    # ─────────────────────────────────────────────
    # ▶ APPROVAL TYPE CLASSIFICATION
    # ─────────────────────────────────────────────
    
    approval_type = fields.Selection([
        ('internal', 'Internal Approval'),
        ('shared', 'Shared Approval')
    ], string='Approval Type', default='internal', required=True, tracking=True,
       help='Internal: chỉ internal teams. Shared: external và shared teams')
    
    external_id = fields.Char(
        string='External ID',
        help='ID của approval trong hệ thống bên ngoài (chỉ dành cho Shared Approval)',
        copy=False
    )
    
    # ─────────────────────────────────────────────
    # ▶ SUBMISSION TRACKING
    # ─────────────────────────────────────────────
    
    submitted_by_user_id = fields.Many2one(
        'res.users',
        string='Submitted By User',
        help='Người dùng cụ thể đã gửi approval này'
    )
    
    submitted_as_type = fields.Selection([
        ('user', 'As Personal User'),
        ('team', 'As Team Member'),
        ('contractor', 'As Contractor')
    ], string='Submitted As',
       help='Tư cách mà approval được gửi')
    
    submitted_as_id = fields.Reference([
        ('res.users', 'User'),
        ('vnfield.team', 'Team'),
        ('vnfield.contractor', 'Contractor')
    ], string='Submitted As Entity',
       help='Entity cụ thể mà người gửi đại diện')
    
    # ─────────────────────────────────────────────
    # ▶ PROJECT RELATIONSHIP
    # ─────────────────────────────────────────────
    
    project_id = fields.Many2one(
        'vnfield.project',
        string='Related Project',
        help='Project liên quan đến approval này'
    )
    
    # ─────────────────────────────────────────────
    # ▶ ACCESS CONTROL
    # ─────────────────────────────────────────────
    
    visible_to_user_ids = fields.Many2many(
        'res.users',
        'approval_visible_user_rel',
        'approval_id',
        'user_id', 
        string='Visible To Users',
        compute='_compute_visible_to_user_ids',
        store=True,
        help='Danh sách users có quyền xem approval này'
    )
    
    can_current_user_view = fields.Boolean(
        string='Can Current User View',
        compute='_compute_can_current_user_view',
        help='Current user có quyền xem approval này hay không'
    )
    
    # ─────────────────────────────────────────────
    # ▶ VALIDATION CONSTRAINTS
    # ─────────────────────────────────────────────
    
    @api.constrains('submitted_as_type', 'submitted_as_id')
    def _check_submission_consistency(self):
        """
        💡 NOTE(assistant): Đảm bảo tính nhất quán của thông tin submission
        
        🧪 Ví dụ:
        - submitted_as_type = 'team' → submitted_as_id phải là vnfield.team
        - submitted_as_type = None → submitted_as_id cũng phải None
        """
        for record in self:
            # 🔍 REVIEW(assistant): Kiểm tra cả 2 field phải cùng có hoặc cùng không
            if record.submitted_as_type and not record.submitted_as_id:
                raise ValidationError('Khi có Submitted As Type, phải có Submitted As Entity tương ứng')
            if record.submitted_as_id and not record.submitted_as_type:
                raise ValidationError('Khi có Submitted As Entity, phải có Submitted As Type tương ứng')
            
            # 🔍 REVIEW(assistant): Kiểm tra model type phù hợp với selection
            if record.submitted_as_type and record.submitted_as_id:
                expected_model = {
                    'user': 'res.users',
                    'team': 'vnfield.team', 
                    'contractor': 'vnfield.contractor'
                }.get(record.submitted_as_type)
                
                if record.submitted_as_id._name != expected_model:
                    raise ValidationError(f'Submitted As Entity phải là {expected_model} khi type là {record.submitted_as_type}')
    
    # ─────────────────────────────────────────────
    # ▶ COMPUTED METHODS
    # ─────────────────────────────────────────────
    
    @api.depends('project_id', 'submitted_by_user_id', 'submitted_as_type', 'submitted_as_id', 'step_ids.approver_ids')
    def _compute_visible_to_user_ids(self):
        """
        🔍 COMPUTED METHOD: Tính danh sách users có quyền xem approval
        
        💡 NOTE(user): Logic phức tạp dựa trên relationships:
        1. Project manager của project hiện tại
        2. Related users của submit user (team leaders, directors, project directors)  
        3. Related users của tất cả approvers trong các steps
        
        🧪 Dependencies:
        - project_id → project manager
        - submitted_by_user_id → user's team leaders, contractor directors
        - step_ids.approver_ids → approver related users
        """
        for record in self:
            visible_users = set()
            
            # 🎯 CASE 1: Project Manager của project hiện tại
            if record.project_id and record.project_id.project_manager_id:
                visible_users.add(record.project_id.project_manager_id.id)
            
            # 🎯 CASE 2: Related users của submit user
            if record.submitted_by_user_id:
                submit_related = record._get_related_users_for_user(record.submitted_by_user_id)
                visible_users.update(submit_related)
            
            # 🎯 CASE 3: Related users của submitted_as entity
            if record.submitted_as_type and record.submitted_as_id:
                entity_related = record._get_related_users_for_entity(record.submitted_as_type, record.submitted_as_id)
                visible_users.update(entity_related)
            
            # 🎯 CASE 4: Related users của tất cả approvers
            for step in record.step_ids:
                for approver in step.approver_ids:
                    approver_related = record._get_related_users_for_approver(approver)
                    visible_users.update(approver_related)
            
            # 🔄 Convert set to recordset và assign
            record.visible_to_user_ids = [(6, 0, list(visible_users))]
    
    @api.depends('visible_to_user_ids')
    def _compute_can_current_user_view(self):
        """
        🔍 COMPUTED METHOD: Check current user có quyền xem approval không
        
        💡 NOTE(assistant): Utility để filter trong views và security rules
        """
        current_user_id = self.env.user.id
        for record in self:
            record.can_current_user_view = current_user_id in record.visible_to_user_ids.ids
    
    def _get_related_users_for_user(self, user):
        """
        👤 HELPER: Lấy related users cho một user cụ thể
        
        💡 NOTE(user): Bao gồm:
        - Team leaders của teams mà user tham gia
        - Director và project directors của contractor mà user thuộc về
        
        Args:
            user (res.users): User cần tìm related users
            
        Returns:
            set: Set of user IDs
        """
        related_users = set()
        
        # 👥 Team leaders của teams mà user tham gia
        user_teams = self.env['vnfield.team'].search([('team_member_ids', 'in', user.id)])
        for team in user_teams:
            if team.team_leader_id:
                related_users.add(team.team_leader_id.id)
        
        # 🏢 Director và project directors của contractor
        if user.contractor_id:
            contractor = user.contractor_id
            if contractor.director_id:
                related_users.add(contractor.director_id.id)
            for project_director in contractor.project_director_ids:
                related_users.add(project_director.id)
        
        return related_users
    
    def _get_related_users_for_entity(self, entity_type, entity):
        """
        🏢 HELPER: Lấy related users cho submitted_as entity
        
        💡 NOTE(user): Logic tùy theo entity type:
        - user: gọi _get_related_users_for_user
        - team: team leader + contractor directors
        - contractor: director + project directors
        
        Args:
            entity_type (str): 'user', 'team', 'contractor'
            entity (Model): Entity object
            
        Returns:
            set: Set of user IDs
        """
        related_users = set()
        
        if entity_type == 'user':
            related_users.update(self._get_related_users_for_user(entity))
            
        elif entity_type == 'team':
            # Team leader
            if entity.team_leader_id:
                related_users.add(entity.team_leader_id.id)
            # Contractor directors
            if entity.contractor_id:
                contractor = entity.contractor_id
                if contractor.director_id:
                    related_users.add(contractor.director_id.id)
                for project_director in contractor.project_director_ids:
                    related_users.add(project_director.id)
                    
        elif entity_type == 'contractor':
            # Director và project directors
            if entity.director_id:
                related_users.add(entity.director_id.id)
            for project_director in entity.project_director_ids:
                related_users.add(project_director.id)
        
        return related_users
    
    def _get_related_users_for_approver(self, approver):
        """
        ✅ HELPER: Lấy related users cho một approver
        
        💡 NOTE(user): Logic tùy theo approver type:
        - user_id: team leaders + contractor directors của user
        - team_id: team leader + contractor directors của team
        - contractor_id: director + project directors của contractor
        
        Args:
            approver (vnfield.approver): Approver record
            
        Returns:
            set: Set of user IDs
        """
        related_users = set()
        
        # 👤 Approver User
        if approver.user_id:
            related_users.update(self._get_related_users_for_user(approver.user_id))
            # Thêm chính user đó vào danh sách
            related_users.add(approver.user_id.id)
            
        # 👥 Approver Team  
        elif approver.team_id:
            team = approver.team_id
            # Team leader
            if team.team_leader_id:
                related_users.add(team.team_leader_id.id)
            # Contractor directors
            if team.contractor_id:
                contractor = team.contractor_id
                if contractor.director_id:
                    related_users.add(contractor.director_id.id)
                for project_director in contractor.project_director_ids:
                    related_users.add(project_director.id)
                    
        # 🏢 Approver Contractor
        elif approver.contractor_id:
            contractor = approver.contractor_id
            # Director và project directors
            if contractor.director_id:
                related_users.add(contractor.director_id.id)
            for project_director in contractor.project_director_ids:
                related_users.add(project_director.id)
        
        return related_users
    
    def can_user_view_approval(self, user_id=None):
        """
        🔍 UTILITY METHOD: Kiểm tra user có quyền xem approval hay không
        
        💡 NOTE(assistant): Tiện ích để check access rights
        
        Args:
            user_id (int, optional): User ID để check. Defaults to current user.
            
        Returns:
            bool: True nếu user có quyền xem
            
        🧪 Usage:
        if approval.can_user_view_approval():
            # Show approval
        """
        if not user_id:
            user_id = self.env.user.id
            
        return user_id in self.visible_to_user_ids.ids
    
    def refresh_visible_users(self):
        """
        🔄 ACTION: Refresh lại danh sách visible users
        
        💡 NOTE(assistant): Tiện ích để force recompute visible_to_user_ids
        
        🧪 Usage:
        approval.refresh_visible_users()
        """
        self._compute_visible_to_user_ids()
        return True
    
    # ─────────────────────────────────────────────
    # ▶ BUSINESS LOGIC METHODS
    # ─────────────────────────────────────────────
    
    def _check_in_progress_protection(self, vals):
        """
        🔒 HELPER METHOD: Kiểm tra và ngăn chặn chỉnh sửa khi approval đang in_progress
        
        💡 NOTE(assistant): Helper method để avoid code duplication
        
        🎯 Business Logic:
        - Check state từ database, không phải memory  
        - Allow state changes (draft→in_progress, in_progress→approved/rejected)  
        - Block data modification khi đã in_progress
        - Bypass protection khi có context flag từ action_send
        
        📝 Parameters:
        - vals: dict values để check có phải chỉ state change không
        
        🧪 Usage:
        self._check_in_progress_protection(vals)
        """
        # 🔍 REVIEW(assistant): Bypass protection trong action_send workflow
        if self.env.context.get('skip_in_progress_protection'):
            return
            
        # 🔍 REVIEW(assistant): Nếu chỉ update state thì cho phép (state transitions)
        if len(vals) == 1 and 'state' in vals:
            return  # Allow state transitions like draft→in_progress
        
        # 🔍 REVIEW(user): Query database để lấy state thực tế (không dùng memory)
        # 💡 NOTE(assistant): Dùng search database để check state hiện tại
        current_records = self.env['vnfield.approval'].search([('id', 'in', self.ids)])
        in_progress_records = current_records.filtered(lambda r: r.state == 'in_progress')
        if in_progress_records:
            record_names = ', '.join(in_progress_records.mapped('name'))
            raise UserError(
                f"🚫 Không thể chỉnh sửa approval đang trong quá trình phê duyệt!\n\n"
                f"Các approval bị khóa: {record_names}\n\n"
                f"💡 Lý do: Approval đang ở trạng thái 'In Progress' để đảm bảo tính toàn vẹn của quy trình phê duyệt."
            )
    
    def write(self, vals):
        """
        🔒 WRITE PROTECTION: Ngăn chặn chỉnh sửa khi approval đang in_progress
        
        💡 NOTE(assistant): Sử dụng helper method để maintain consistency
        
        🚫 RESTRICTION:
        - Không cho edit khi state = 'in_progress'
        - Đảm bảo tính toàn vẹn của approval process
        
        🧪 Test case:
        approval.state = 'in_progress'
        approval.write({'name': 'New Name'}) → UserError
        """
        # � REVIEW(assistant): Sử dụng helper method để check protection
        self._check_in_progress_protection(vals)
        
        return super(Approval, self).write(vals)
    
    def action_send(self):
        """
        📤 CHỨC NĂNG: GỬI APPROVAL ĐỂ BẮT ĐẦU QUY TRÌNH PHÊ DUYỆT
        
        💡 NOTE(assistant): Chuyển state từ draft → in_progress và kích hoạt first steps
        
        🧪 Business Logic:
        - Approval: draft → in_progress
        - First steps (no prev_step_id): draft → in_progress
        - Set submission info nếu chưa có
        
        🔗 Ví dụ workflow:
        - approval.action_send() → state = 'in_progress'
        - first_steps.state = 'in_progress' → ready for approval
        """
        for record in self:
            if record.state != 'draft':
                raise ValidationError('Chỉ có thể gửi approval ở trạng thái Draft')
            
            # 🔄 Chuyển approval state sang in_progress
            # 💡 NOTE(assistant): Sử dụng write() với context bypass protection
            record.with_context(skip_in_progress_protection=True).write({
                'state': 'in_progress',
                'submitted_by_user_id': record.submitted_by_user_id.id if record.submitted_by_user_id else self.env.user.id
            })
            
            # 🚀 Kích hoạt first steps (không có prev_step_id)
            first_steps = record.step_ids.filtered(lambda s: not s.prev_step_id and s.state == 'draft')
            if first_steps:
                # 💡 NOTE(assistant): Steps cũng bypass protection trong action_send
                first_steps.with_context(skip_in_progress_protection=True).write({'state': 'in_progress'})
                
                # 💡 NOTE(assistant): Log thông tin steps được kích hoạt
                step_names = ', '.join(first_steps.mapped('name'))
                # 📝 TODO(assistant): Log info thay vì message_post vì chưa inherit mail.thread
                import logging
                _logger = logging.getLogger(__name__)
                _logger.info(f"📋 Approval '{record.name}' sent! Activated first steps: {step_names}")
            
            # 💡 NOTE(assistant): Có thể thêm logic gửi notification hoặc trigger workflow
            
        return True


# ─────────────────────────────────────────────────────────
# ▶ PHỤ THUỘC VÀ QUAN HỆ GIỮA CÁC SYMBOL
# ─────────────────────────────────────────────────────────

"""
🔗 SYMBOL DEPENDENCIES:

📋 Core Models:
- vnfield.approval → vnfield.approval.step (One2many qua approval_id)
- vnfield.approval → res.users (Many2one qua submitted_by_user_id)
- vnfield.approval → vnfield.team (Reference qua submitted_as_id)
- vnfield.approval → vnfield.contractor (Reference qua submitted_as_id)

🧮 Validation Logic:
- _check_submission_consistency() → submitted_as_type + submitted_as_id
- Constraint decorator @api.constrains() → ValidationError exception

🎯 Business Logic Flow:
1. User tạo approval với submitted_by_user_id (người gửi thực tế)
2. User chọn submitted_as_type (tư cách: user/team/contractor)
3. User chọn submitted_as_id (entity cụ thể tương ứng với type)
4. Constraint validation đảm bảo type và id phù hợp
5. User click nút Send (chỉ hiển thị khi state = 'draft')
6. action_send() chuyển state → 'in_progress' và auto-set submitted_by_user_id
7. UI hiển thị submission info readonly trong form/tree/kanban
"""
