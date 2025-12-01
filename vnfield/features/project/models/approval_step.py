# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

# ===========================================
# =           APPROVAL STEP MODEL           =
# ========================    

class ApprovalStep(models.Model):
    """
    ┌──────────────────────────────────────────────────────┐
    │    🧰 CHỨC NĂNG: APPROVAL STEP VỚI INVERSE FIELDS     │
    │                                                      │
    │ - Một bước phê duyệt trong quy trình approval        │
    │ - Bi-directional chain: next_step ↔ prev_step        │
    │ - Sử dụng inverse_name cho auto-sync                 │
    │ - Auto-calculate sequence dựa trên prev step         │
    │ - Validation ngăn chặn circular dependency           │
    └──────────────────────────────────────────────────────┘
    """
    _name = 'vnfield.approval.step'
    _description = 'Approval Step'
    _order = 'sequence, id'

    name = fields.Char(string='Step Name', required=True)
    approval_id = fields.Many2one('vnfield.approval', string='Approval', required=True, ondelete='cascade')
    
    # ─────────────────────────────────────────────
    # ▶ STEP CHAIN RELATIONSHIP WITH INVERSE
    # ─────────────────────────────────────────────
    
    prev_step_id = fields.Many2one(
        'vnfield.approval.step', 
        string='Previous Step',
        inverse_name='next_step_id',
        help='Bước phê duyệt trước đó trong chuỗi (auto-sync với next_step)'
    )
    
    next_step_id = fields.Many2one(
        'vnfield.approval.step', 
        string='Next Step', 
        inverse_name='prev_step_id',
        help='Bước phê duyệt tiếp theo trong chuỗi (auto-sync với prev_step)',
        unique=True
    )
    
    sequence = fields.Integer(
        string='Sequence', 
        compute='_compute_sequence',
        store=True,
        help='Thứ tự của step, tự động tính dựa trên prev_step'
    )
    
    # ─────────────────────────────────────────────
    # ▶ STEP TYPE CLASSIFICATION
    # ─────────────────────────────────────────────
    
    step_type = fields.Selection([
        ('internal', 'Internal Step'),
        ('shared', 'Shared Step')
    ], string='Step Type', default='internal', required=True, tracking=True,
       help='Internal: chỉ internal teams. Shared: external và shared teams')
    
    external_id = fields.Char(
        string='External ID',
        help='ID của step trong hệ thống bên ngoài (chỉ dành cho Shared Step)',
        copy=False
    )
    
    approver_ids = fields.One2many('vnfield.approver', 'step_id', string='Approvers')
    
    # 💡 NOTE(assistant): State đồng nhất với approval model (draft → in_progress → approved/rejected)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='State', default='draft')
    
    # ─────────────────────────────────────────────
    # ▶ COMPUTED METHODS
    # ─────────────────────────────────────────────
    
    @api.depends('prev_step_id', 'prev_step_id.sequence')
    def _compute_sequence(self):
        """
        💡 NOTE(assistant): Tự động tính sequence dựa trên prev_step
        
        🧪 Ví dụ:
        - Step A (no prev) → sequence = 1
        - Step B (prev = A) → sequence = A.sequence + 1 = 2
        - Step C (prev = B) → sequence = B.sequence + 1 = 3
        
        🔗 Business Rule: next step của một step chính là prev step của step khác
        """
        for record in self:
            if record.prev_step_id:
                # 🔄 Có prev step → sequence = prev.sequence + 1
                record.sequence = record.prev_step_id.sequence + 1
            else:
                # 🏁 Không có prev step → sequence = 1 (first step)
                record.sequence = 1
    
    # � NOTE(assistant): Với inverse_name, không cần onchange methods
    # next_step_id ↔ prev_step_id tự động sync bi-directional
    
    # ─────────────────────────────────────────────
    # ▶ VALIDATION CONSTRAINTS
    # ─────────────────────────────────────────────
    
    @api.constrains('prev_step_id', 'next_step_id')
    def _check_no_circular_dependency(self):
        """
        🔍 REVIEW(assistant): Ngăn chặn circular dependency với inverse fields
        
        💡 NOTE(assistant): Với inverse_name, bi-directional sync tự động
        Chỉ cần validate business rules: same approval, no self-ref, no circular
        
        🧪 Ví dụ lỗi:
        - Step A → next = Step B
        - Step B → next = Step A (circular!)
        """
        for record in self:
            # 🔄 Kiểm tra prev_step_id (Many2one)
            if record.prev_step_id:
                # 🔄 Kiểm tra approval_id phải giống nhau
                if record.prev_step_id.approval_id != record.approval_id:
                    raise ValidationError('Previous step phải trong cùng approval')
                
                # 🔄 Kiểm tra không tự reference chính mình
                if record.prev_step_id == record:
                    raise ValidationError('Step không thể reference chính mình')
            
            # 🔄 Kiểm tra next_step_id  
            if record.next_step_id:
                # 🔄 Kiểm tra approval_id phải giống nhau
                if record.next_step_id.approval_id != record.approval_id:
                    raise ValidationError('Next step phải trong cùng approval')
                
                # 🔄 Kiểm tra không tự reference chính mình
                if record.next_step_id == record:
                    raise ValidationError('Step không thể reference chính mình')
                
                # 🔍 REVIEW(assistant): Kiểm tra circular dependency
                visited = set()
                current = record.next_step_id
                while current and current.id not in visited:
                    visited.add(current.id)
                    if current == record:
                        raise ValidationError('Phát hiện circular dependency trong step chain')
                    current = current.next_step_id

    # ─────────────────────────────────────────────
    # ▶ CHAIN CONSISTENCY VALIDATION
    # ─────────────────────────────────────────────
    
    def _validate_bidirectional_chain(self):
        """
        🔗 Validation: next step của một step chính là prev step của step khác
        
        💡 NOTE(assistant): Inverse giữa 2 Many2one không tự động sync
        Cần validation manual để đảm bảo bi-directional consistency
        
        🧪 Business Rules:
        - Nếu Step A.next_step_id = Step B → Step B.prev_step_id phải = Step A
        - Nếu Step B.prev_step_id = Step A → Step A.next_step_id phải = Step B
        
        ⚠️ Gọi trong write method để maintain consistency
        """
        for record in self:
            # 🔄 Check next_step → prev_step consistency
            if record.next_step_id:
                if record.next_step_id.prev_step_id != record:
                    raise ValidationError(
                        f'Chain inconsistency: Step "{record.name}" points to next step "{record.next_step_id.name}", '
                        f'but that step\'s previous step is "{record.next_step_id.prev_step_id.name if record.next_step_id.prev_step_id else "None"}" '
                        f'instead of "{record.name}"'
                    )
            
            # 🔄 Check prev_step → next_step consistency
            if record.prev_step_id:
                if record.prev_step_id.next_step_id != record:
                    raise ValidationError(
                        f'Chain inconsistency: Step "{record.name}" points to previous step "{record.prev_step_id.name}", '
                        f'but that step\'s next step is "{record.prev_step_id.next_step_id.name if record.prev_step_id.next_step_id else "None"}" '
                        f'instead of "{record.name}"'
                    )

    def _sync_chain_relationships(self, vals):
        """
        🔄 Sync bi-directional chain relationships manually
        
        💡 NOTE(assistant): Helper method để sync next ↔ prev step relationships
        Inverse giữa 2 Many2one không tự động, cần sync manual
        
        🧪 Sync Logic:
        - Khi set next_step_id → auto-update prev_step_id của target step
        - Khi set prev_step_id → auto-update next_step_id của target step
        - Clear old relationships khi thay đổi
        
        Args:
            vals (dict): Values being written to the record
        """
        for record in self:
            # 🔄 Sync next_step_id changes
            if 'next_step_id' in vals:
                new_next_id = vals.get('next_step_id')
                old_next = record.next_step_id
                
                # Clear old next step's prev_step_id
                if old_next and old_next.prev_step_id == record:
                    # 💡 NOTE(assistant): Dùng super().write() để tránh đệ quy vô hạn
                    super(ApprovalStep, old_next).write({'prev_step_id': False})
                
                # Set new next step's prev_step_id
                if new_next_id:
                    new_next = self.browse(new_next_id)
                    if new_next.exists() and new_next.prev_step_id != record:
                        # 💡 NOTE(assistant): Dùng super().write() để tránh đệ quy vô hạn
                        super(ApprovalStep, new_next).write({'prev_step_id': record.id})
            
            # 🔄 Sync prev_step_id changes  
            if 'prev_step_id' in vals:
                new_prev_id = vals.get('prev_step_id')
                old_prev = record.prev_step_id
                
                # Clear old prev step's next_step_id
                if old_prev and old_prev.next_step_id == record:
                    # 💡 NOTE(assistant): Dùng super().write() để tránh đệ quy vô hạn
                    super(ApprovalStep, old_prev).write({'next_step_id': False})
                
                # Set new prev step's next_step_id
                if new_prev_id:
                    new_prev = self.browse(new_prev_id)
                    if new_prev.exists() and new_prev.next_step_id != record:
                        # 💡 NOTE(assistant): Dùng super().write() để tránh đệ quy vô hạn
                        super(ApprovalStep, new_prev).write({'next_step_id': record.id})

    # ─────────────────────────────────────────────
    # ▶ OVERRIDE METHODS  
    # ─────────────────────────────────────────────
    
    def _check_in_progress_protection(self, vals):
        """
        🔒 HELPER METHOD: Kiểm tra và ngăn chặn chỉnh sửa khi step đang in_progress
        
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
        current_records = self.env['vnfield.approval.step'].search([('id', 'in', self.ids)])
        in_progress_records = current_records.filtered(lambda r: r.state == 'in_progress')
        if in_progress_records:
            step_names = ', '.join(in_progress_records.mapped('name'))
            approval_names = ', '.join(in_progress_records.mapped('approval_id.name'))
            raise UserError(
                f"🚫 Không thể chỉnh sửa approval step đang trong quá trình phê duyệt!\n\n"
                f"Các step bị khóa: {step_names}\n"
                f"Thuộc approval: {approval_names}\n\n"
                f"💡 Lý do: Step đang ở trạng thái 'In Progress' để đảm bảo tính toàn vẹn của quy trình phê duyệt."
            )
    
    def write(self, vals):
        """
        Override write để maintain bi-directional chain consistency và write protection
        
        🔒 WRITE PROTECTION: Ngăn chặn chỉnh sửa khi step đang in_progress
        🔗 Business Rule: Đảm bảo next ↔ prev step relationships nhất quán
        
        💡 NOTE(assistant): Sử dụng helper method để maintain consistency
        
        🚫 RESTRICTION:
        - Không cho edit khi state = 'in_progress' (trừ state transitions)
        - Đảm bảo tính toàn vẹn của approval workflow
        
        🧪 Test case:
        step.state = 'in_progress'
        step.write({'name': 'New Name'}) → UserError
        step.write({'state': 'approved'}) → OK (state transition)
        """
        # 🔒 Write Protection: Sử dụng helper method để check protection
        self._check_in_progress_protection(vals)
        
        # 🔗 Sync chain relationships BEFORE write để capture old values
        if 'prev_step_id' in vals or 'next_step_id' in vals:
            self._sync_chain_relationships(vals)
        
        result = super().write(vals)
        
        # 🔍 REVIEW(assistant): Validate bi-directional chain sau khi write
        if 'prev_step_id' in vals or 'next_step_id' in vals:
            self._validate_bidirectional_chain()
        
        # 🔄 AUTO STATE TRANSITION: Cập nhật approval state khi step state thay đổi
        if 'state' in vals:
            self._handle_approval_state_transition()
        
        return result

    def _handle_approval_state_transition(self):
        """
        🔄 AUTO STATE TRANSITION: Tự động cập nhật approval state khi step state thay đổi
        
        💡 NOTE(user): Logic yêu cầu:
        - Step rejected → Approval rejected  
        - Step approved + is last step → Approval approved
        
        🎯 Business Logic:
        1. Nếu bất kỳ step nào bị rejected → approval rejected
        2. Nếu step được approved và là last step → approval approved
        3. Last step = step không có next_step_id
        
        🧪 Test cases:
        - step.state = 'rejected' → approval.state = 'rejected'
        - last_step.state = 'approved' → approval.state = 'approved'
        """
        for step in self:
            approval = step.approval_id
            if not approval:
                continue
                
            # 🚫 CASE 1: Step bị rejected → Approval rejected
            if step.state == 'rejected':
                if approval.state != 'rejected':
                    # 💡 NOTE(assistant): Bypass protection khi auto transition
                    approval.with_context(skip_in_progress_protection=True).write({'state': 'rejected'})
                    
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.info(f"🚫 Approval '{approval.name}' auto-rejected due to step '{step.name}' rejection")
            
            # ✅ CASE 2: Step approved + Last step → Approval approved
            elif step.state == 'approved':
                # 🔍 Check if this is the last step (no next_step_id)
                is_last_step = not step.next_step_id
                
                if is_last_step and approval.state != 'approved':
                    # 💡 NOTE(assistant): Bypass protection khi auto transition
                    approval.with_context(skip_in_progress_protection=True).write({'state': 'approved'})
                    
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.info(f"✅ Approval '{approval.name}' auto-approved due to last step '{step.name}' completion")
                
                # 🔄 CASE 3: Step approved + Not last step → Kích hoạt next step
                elif not is_last_step and step.next_step_id:
                    next_step = step.next_step_id
                    if next_step.state == 'draft':
                        # 💡 NOTE(assistant): Auto activate next step
                        next_step.with_context(skip_in_progress_protection=True).write({'state': 'in_progress'})
                        
                        import logging
                        _logger = logging.getLogger(__name__)
                        _logger.info(f"🔄 Next step '{next_step.name}' auto-activated after '{step.name}' approval")

    def action_approve(self):
        """
        ✅ ACTION: Phê duyệt step hiện tại
        
        💡 NOTE(user): Chuyển state → 'approved' và trigger auto transitions
        
        🎯 Business Logic:
        - Step: in_progress → approved
        - Auto trigger next step hoặc complete approval
        
        🧪 Usage:
        step.action_approve()
        """
        for record in self:
            if record.state != 'in_progress':
                raise ValidationError('Chỉ có thể phê duyệt step ở trạng thái In Progress')
            
            # 💡 NOTE(assistant): Write sẽ trigger _handle_approval_state_transition
            record.write({'state': 'approved'})
        
        return True
    
    def action_reject(self):
        """
        🚫 ACTION: Từ chối step hiện tại
        
        💡 NOTE(user): Chuyển state → 'rejected' và trigger approval rejection
        
        🎯 Business Logic:
        - Step: in_progress → rejected
        - Auto reject entire approval
        
        🧪 Usage:
        step.action_reject()
        """
        for record in self:
            if record.state != 'in_progress':
                raise ValidationError('Chỉ có thể từ chối step ở trạng thái In Progress')
            
            # 💡 NOTE(assistant): Write sẽ trigger _handle_approval_state_transition
            record.write({'state': 'rejected'})
        
        return True

