# ─────────────────────────────────────────────────────────────────────────────
# ▶ ACTION: MỞ WIZARD ASSIGNMENT INFO TỪ NÚT "ASSIGN TASK"
# ─────────────────────────────────────────────────────────────────────────────
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# ===========================================
# =         ✅ TASK MODEL                   =
# ===========================================

class VnfieldTask(models.Model):
    """
    Task model để quản lý các công việc trong dự án.
    - Bắt buộc thuộc một project (Many2one required với vnfield.project)
    - Có assignee, assigner, verifier là res.users
    - Các thông tin cơ bản: name, description, status, priority, dates, etc.
    """
    _name = 'vnfield.task'
    _description = 'VNField Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, create_date desc, name'
    
    # ─────────────────────────────────────────────
    # ▶ BASIC INFORMATION FIELDS
    # ─────────────────────────────────────────────
    
    name = fields.Char(
        string='Task Name',
        required=True,
        help='Tên công việc'
    )
    
    description = fields.Text(
        string='Description',
        help='Mô tả chi tiết công việc'
    )
    
    task_code = fields.Char(
        string='Task Code',
        help='Mã công việc duy nhất',
        copy=False
    )
    
    # ─────────────────────────────────────────────
    # ▶ TASK TYPE CLASSIFICATION
    # ─────────────────────────────────────────────
    
    task_type = fields.Selection([
        ('internal', 'Internal Task'),
        ('shared', 'Shared Task')
    ], string='Task Type', default='internal', required=True, tracking=True,
       help='Internal: internal + shared users tham gia. Shared: chỉ shared + external users')
    
    external_id = fields.Char(
        string='External ID',
        help='ID của task trong hệ thống bên ngoài (chỉ dành cho Shared Task)',
        copy=False
    )
    
    # ─────────────────────────────────────────────
    # ▶ STATUS AND WORKFLOW FIELDS
    # ─────────────────────────────────────────────
    
    status = fields.Selection([
        ("draft", "Draft"),
        ("planning", "Planning"),
        ("in-progress", "In Progress"),
        ("on-hold", "On Hold"),
        ("review", "Under Review"),
        ("completed", "Completed"),
        ("canceled", "Canceled"),
    ], string="Status", default="draft", tracking=True)
    
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'), 
        ('3', 'Critical')
    ], string='Priority', default='1')
    
    # ─────────────────────────────────────────────
    # ▶ PROJECT RELATIONSHIP (REQUIRED)
    # ─────────────────────────────────────────────
    
    project_id = fields.Many2one(
        'vnfield.project',
        string='Project',
        required=True,
        ondelete='cascade',
        help='Dự án mà task này thuộc về'
    )
    
    # ─────────────────────────────────────────────
    # ▶ USER RELATIONSHIPS
    # ─────────────────────────────────────────────
    
    assignee_id = fields.Many2one(
        'res.users',
        string='Assignee',
        domain="[('id', 'in', project_id.contractor_ids.user_ids)]",
        help='Người được giao thực hiện task, chỉ chọn user thuộc project'
    )
    
    assigner_id = fields.Many2one(
        'res.users',
        string='Assigner',
        help='Người giao task'
    )
    # Temp
    executer_id = fields.Many2one(
        'res.users',
        string='Executer',
        help='Người thực hiện task'
    )
    
    verifier_id = fields.Many2one(
        'res.users',
        string='Verifier',
        help='Người xác nhận/kiểm tra task'
    )
    
    # ─────────────────────────────────────────────
    # ▶ DATE FIELDS
    # ─────────────────────────────────────────────
    
    start_date = fields.Date(
        string='Start Date',
        help='Ngày bắt đầu task'
    )
    
    end_date = fields.Date(
        string='End Date',
        help='Ngày kết thúc task'
    )
    
    deadline = fields.Datetime(
        string='Deadline',
        help='Hạn chót hoàn thành task'
    )
    
    assigned_date = fields.Datetime(
        string='Assigned Date',
        help='Ngày được giao task'
    )
    
    completed_date = fields.Datetime(
        string='Completed Date',
        help='Ngày hoàn thành task'
    )
    
    # ─────────────────────────────────────────────
    # ▶ ESTIMATION AND TRACKING FIELDS
    # ─────────────────────────────────────────────
    
    estimated_hours = fields.Float(
        string='Estimated Hours',
        help='Số giờ ước tính để hoàn thành'
    )
    
    actual_hours = fields.Float(
        string='Actual Hours',
        help='Số giờ thực tế đã làm'
    )
    
    progress = fields.Float(
        string='Progress (%)',
        help='Tiến độ hoàn thành task (0-100%)'
    )
    
    # ─────────────────────────────────────────────
    # ▶ COMPUTED FIELDS
    # ─────────────────────────────────────────────
    
    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_is_overdue',
        help='Task có quá hạn không'
    )
    
    duration_days = fields.Integer(
        string='Duration (Days)',
        compute='_compute_duration',
        store=True,
        help='Số ngày từ start đến end date'
    )
    
    # Project related computed fields
    project_name = fields.Char(
        related='project_id.name',
        string='Project Name',
        store=True
    )
    
    project_state = fields.Selection(
        related='project_id.state',
        string='Project Status',
        store=True
    )
    
    
        # ─────────────────────────────────────────────
    # ▶ OUTSOURCE FIELDS
    # ─────────────────────────────────────────────
    is_outsourced = fields.Boolean(
        string='Is Outsourced',
        help='Đánh dấu task này là outsource cho project khác'
    )

    outsource_project_id = fields.Many2one(
        'vnfield.project',
        string='Outsourced Project',
        help='Nếu là outsource, liên kết đến project mà task này outsource cho'
    )
    
    contractor_assignee_id = fields.Many2one(
        'vnfield.contractor',
        string='Contractor Assignee',
        domain="[('id', 'in', project_id.contractor_ids)]",
        help='Chỉ dùng khi là outsource, chỉ chọn contractor thuộc project'
    )

    @api.constrains('assignee_id', 'contractor_assignee_id', 'is_outsourced')
    def _check_assignee_exclusive(self):
        for rec in self:
            if rec.is_outsourced:
                if rec.assignee_id and rec.contractor_assignee_id:
                    raise ValidationError(_('Task outsource chỉ được có 1 trong 2: assignee hoặc contractor assignee!'))
                if not rec.contractor_assignee_id:
                    raise ValidationError(_('Task outsource phải có contractor assignee!'))
                if rec.assignee_id:
                    raise ValidationError(_('Task outsource không được có user assignee!'))
            else:
                if rec.contractor_assignee_id:
                    raise ValidationError(_('Task không outsource không được có contractor assignee!'))
                if not rec.assignee_id:
                    raise ValidationError(_('Task không outsource phải có user assignee!'))
    
    # ─────────────────────────────────────────────
    # ▶ COMPUTED METHODS
    # ─────────────────────────────────────────────
    
    def _compute_is_overdue(self):
        """
        ⏰ COMPUTED FIELD: Kiểm tra task có quá hạn không
        """
        today = fields.Datetime.now()
        for record in self:
            record.is_overdue = (
                record.deadline and 
                record.deadline < today and 
                record.status not in ['completed', 'canceled']
            )
            
    @api.depends('outsource_project_id')
    def _sync_outsource_project(self):
        """
        Đảm bảo quan hệ 1-1 giữa task.outsource_project_id và project.outsourced_task_id ở mức computed.
        """
        for rec in self:
            # Nếu có liên kết, cập nhật ngược lại project
            if rec.outsource_project_id:
                project = rec.outsource_project_id
                # Nếu project đã có outsourced_task_id khác thì raise
                if project.outsourced_task_id and project.outsourced_task_id != rec:
                    raise ValidationError(_('Project %s đã liên kết với một task outsource khác!') % project.name)
                project.outsourced_task_id = rec.id
            # Nếu không có liên kết, xóa ngược lại bên project
            else:
                # Tìm project cũ nếu có
                projects = self.env['vnfield.project'].search([('outsourced_task_id', '=', rec.id)])
                for project in projects:
                    project.outsourced_task_id = False
    
    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        """
        📅 COMPUTED FIELD: Tính số ngày duration
        """
        for record in self:
            if record.start_date and record.end_date:
                delta = record.end_date - record.start_date
                record.duration_days = delta.days
            else:
                record.duration_days = 0
    

    # ─────────────────────────────────────────────
    # ▶ VALIDATION METHODS
    # ─────────────────────────────────────────────    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """
        ✅ VALIDATION: Kiểm tra start_date <= end_date
        """
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError(_('Start date must be earlier than or equal to end date!'))
    
    @api.constrains('progress')
    def _check_progress(self):
        """
        ✅ VALIDATION: Kiểm tra progress trong khoảng 0-100
        """
        for record in self:
            if record.progress < 0 or record.progress > 100:
                raise ValidationError(_('Progress must be between 0 and 100%!'))
    
    @api.constrains('estimated_hours', 'actual_hours')
    def _check_hours(self):
        """
        ✅ VALIDATION: Kiểm tra hours >= 0
        """
        for record in self:
            if record.estimated_hours and record.estimated_hours < 0:
                raise ValidationError(_('Estimated hours must be positive!'))
            if record.actual_hours and record.actual_hours < 0:
                raise ValidationError(_('Actual hours must be positive!'))
    
    @api.constrains('task_type', 'project_id')
    def _check_task_project_type_compatibility(self):
        """
        🚫 CONSTRAINT: Internal project không thể có shared task
        ✅ ALLOWED: Shared project có thể có internal hoặc shared task
        
        Business Rules:
        - Internal Project + Internal Task ✅ 
        - Internal Project + Shared Task ❌ FORBIDDEN
        - Shared Project + Internal Task ✅
        - Shared Project + Shared Task ✅
        """
        for task in self:
            if (task.project_id and 
                task.project_id.project_type == 'internal' and 
                task.task_type == 'shared'):
                raise ValidationError(_(
                    "🚫 Business Rule Violation!\n\n"
                    "Internal Project '%s' không thể có Shared Task '%s'.\n"
                    "Chỉ Internal Tasks được phép trong Internal Projects."
                ) % (task.project_id.name, task.name))

    # ─────────────────────────────────────────────
    # ▶ WORKFLOW METHODS  
    # ─────────────────────────────────────────────
    
    def action_assign_task(self):
        """
        📋 ACTION: Giao task (chuyển sang assigned)
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assign Task',
            'res_model': 'vnfield.task.assignment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_task_id': self.id,
                'active_id': self.id,
                'active_model': 'vnfield.task',
            },
        }
        
    def action_send_task(self):
        """
        📋 ACTION: Giao task (chuyển sang assigned)
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Mapping Task',
            'res_model': 'vnfield.task.mapping.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'executer': self.executer_id.id,
            },
        }
    
    def action_start_task(self):
        """
        🚀 ACTION: Bắt đầu làm task
        """
        self.write({'status': 'in-progress'})
    
    def action_submit_for_review(self):
        """
        🔍 ACTION: Gửi để review
        """
        self.write({'status': 'review'})
    
    def action_mark_done(self):
        """
        ✅ ACTION: Đánh dấu hoàn thành
        """
        self.write({
            'status': 'completed',
            'completed_date': fields.Datetime.now(),
            'progress': 100.0
        })
    
    def action_cancel_task(self):
        """
        ❌ ACTION: Hủy task
        """
        self.write({'status': 'canceled'})
    
    # ─────────────────────────────────────────────
    # ▶ ONCHANGE METHODS
    # ─────────────────────────────────────────────
    
    @api.onchange('assignee_id')
    def _onchange_assignee_id(self):
        """
        🔄 ONCHANGE: Tự động set assigner khi có assignee
        """
        if self.assignee_id and not self.assigner_id:
            self.assigner_id = self.env.user.id

    # ─────────────────────────────────────────────
    # ▶ DEPENDENCIES DESCRIPTION
    # ─────────────────────────────────────────────
    
    """
    🔗 SYMBOL DEPENDENCIES:
    
    Internal Dependencies:
    - vnfield.project: Many2one required relationship (task bắt buộc thuộc project)
    
    External Dependencies:
    - res.users: Many2one relationships cho assignee, assigner, verifier
    - odoo.exceptions.ValidationError: Cho validation constraints
    
    Fields Pattern:
    - Basic info: name, description, task_code
    - Workflow: state, priority với selection values cho task management
    - Required relationship: project_id với cascade delete
    - User assignments: assignee_id, assigner_id, verifier_id
    - Time management: start_date, end_date, deadline, assigned_date, completed_date
    - Performance tracking: estimated_hours, actual_hours, progress
    - Computed analytics: is_overdue, duration_days, project_name, project_state
    - Validation: dates, progress percentage, hours constraints
    - Workflow actions: assign, start, submit_review, mark_done, cancel
    - Smart onchange: auto-assign assigner when assignee is set
    """
