# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# ===========================================
# =         🚀 PROJECT MODEL                =
# ===========================================

class Project(models.Model):

    """
    Project model để quản lý các dự án.
    - Có nhiều tasks (One2many relationship)
    - Có các contractors tham gia (Many2many với vnfield.contractor)
    - Có các users tham gia (Many2many với res.users)
    - Các thông tin cơ bản: name, description, status, dates, budget, etc.
    """
    _name = 'vnfield.project'
    _description = 'VNField Project'
    _order = 'create_date desc, name'
    
    # ─────────────────────────────────────────────
    # ▶ BASIC INFORMATION FIELDS
    # ─────────────────────────────────────────────
    
    name = fields.Char(
        string='Project Name',
        required=True,
        help='Tên dự án'
    )
    
    description = fields.Text(
        string='Description',
        help='Mô tả chi tiết về dự án'
    )
    
    code = fields.Char(
        string='Project Code',
        help='Mã dự án duy nhất',
        copy=False
    )
    
    # ─────────────────────────────────────────────
    # ▶ PROJECT TYPE CLASSIFICATION
    # ─────────────────────────────────────────────
    
    project_type = fields.Selection([
        ('internal', 'Internal Project'),
        ('shared', 'Shared Project')
    ], string='Project Type', default='internal', required=True, tracking=True,
       help='Internal: chỉ internal teams tham gia. Shared: external và shared teams tham gia')
    
    external_id = fields.Char(
        string='External ID',
        help='ID của dự án trong hệ thống bên ngoài (chỉ dành cho Shared Project)',
        copy=False
    )
    
    # ─────────────────────────────────────────────
    # ▶ STATUS AND WORKFLOW FIELDS
    # ─────────────────────────────────────────────
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)
    
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'), 
        ('2', 'High'),
        ('3', 'Urgent')
    ], string='Priority', default='1')
    
    # ─────────────────────────────────────────────
    # ▶ DATE FIELDS
    # ─────────────────────────────────────────────
    
    start_date = fields.Date(
        string='Start Date',
        help='Ngày bắt đầu dự án'
    )
    
    end_date = fields.Date(
        string='End Date', 
        help='Ngày kết thúc dự án'
    )
    
    deadline = fields.Datetime(
        string='Deadline',
        help='Hạn chót hoàn thành dự án'
    )
    
    # ─────────────────────────────────────────────
    # ▶ FINANCIAL FIELDS
    # ─────────────────────────────────────────────
    
    budget = fields.Monetary(
        string='Budget',
        currency_field='currency_id',
        help='Ngân sách dự án'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    # ─────────────────────────────────────────────
    # ▶ RELATIONSHIP FIELDS
    # ─────────────────────────────────────────────
    
    # One2many với Tasks
    task_ids = fields.One2many(
        'vnfield.task',
        'project_id',
        string='Tasks',
        help='Danh sách tasks thuộc dự án này'
    )

    # ─────────────────────────────────────────────
    # ▶ OWNER RELATIONSHIP
    # ─────────────────────────────────────────────
    
    owner_contractor_id = fields.Many2one(
        'vnfield.contractor',
        string='Project Owner',
        help='Contractor sở hữu dự án này'
    )
    
    # ─────────────────────────────────────────────
    # ▶ MAIN CONTRACTOR FIELD
    # ─────────────────────────────────────────────
    main_contractor_id = fields.Many2one(
        'vnfield.contractor',
        string='Main Contractor',
        help='Nhà thầu chính chịu trách nhiệm chính cho dự án này. Một contractor có thể là main của nhiều project.'
    )
    
    # Many2many với Contractors
    contractor_ids = fields.Many2many(
        'vnfield.contractor',
        'project_contractor_rel',
        'project_id',
        'contractor_id',
        string='Contractors',
        help='Các contractors tham gia dự án'
    )
    
    # Many2many với Users
    user_ids = fields.Many2many(
        'res.users',
        'project_user_rel',
        'project_id', 
        'user_id',
        string='Team Members',
        help='Các thành viên tham gia dự án'
    )
    
    # Project Manager
    project_manager_id = fields.Many2one(
        'res.users',
        string='Project Manager',
        help='Người quản lý dự án'
    )
    
    # ─────────────────────────────────────────────
    # ▶ COMPUTED FIELDS
    # ─────────────────────────────────────────────
    
    task_count = fields.Integer(
        string='Task Count',
        compute='_compute_task_count',
        store=True,
        help='Số lượng tasks trong dự án'
    )
    
    progress = fields.Float(
        string='Progress (%)',
        compute='_compute_progress',
        store=True,
        help='Tiến độ hoàn thành dự án dựa trên tasks'
    )
    
    # ─────────────────────────────────────────────
    # ▶ INVITATION RELATIONSHIP
    # ─────────────────────────────────────────────
    
    invitation_ids = fields.One2many(
        'vnfield.project.invitation',
        'project_id',
        string='Invitations',
        help='Các lời mời tham gia dự án'
    )
    
    invitation_count = fields.Integer(
        string='Invitation Count',
        compute='_compute_invitation_count',
        store=True,
        help='Số lượng lời mời'
    )
    
    # ─────────────────────────────────────────────
    # ▶ OUTSOURCED RELATIONSHIP
    # ─────────────────────────────────────────────
    outsourced_task_id = fields.Many2one(
        'vnfield.task',
        string='Outsourced From Task',
        help='Task đại diện cho việc project này là outsource của task nào',
        ondelete='set null',
        index=True,
        unique=True
    )

    source_task_id = fields.Integer(
        string='Source Task ID',
        help='ID số của task gốc khi project này là outsource',
        index=True
    )

    is_outsourced = fields.Boolean(
        string='Outsourced',
        compute='_compute_is_outsourced',
        store=True,
        help='Tự động xác định dự án là outsourced nếu có liên kết với một task outsource.'
    )
    # ─────────────────────────────────────────────
    # ▶ COMPUTED METHODS
    # ─────────────────────────────────────────────
    
    @api.depends('outsourced_task_id', 'source_task_id')
    def _compute_is_outsourced(self):
        for rec in self:
            rec.is_outsourced = bool(rec.outsourced_task_id) or bool(rec.source_task_id)
    
    @api.depends('task_ids')
    def _compute_task_count(self):
        """
        📊 COMPUTED FIELD: Tính số lượng tasks trong dự án
        """
        for record in self:
            record.task_count = len(record.task_ids)
    
    @api.depends('task_ids', 'task_ids.status')
    def _compute_progress(self):
        """
        📈 COMPUTED FIELD: Tính tiến độ dự án dựa trên tasks completed
        """
        for record in self:
            if not record.task_ids:
                record.progress = 0.0
            else:
                completed_tasks = len(record.task_ids.filtered(lambda t: t.status == 'completed'))
                total_tasks = len(record.task_ids)
                record.progress = (completed_tasks / total_tasks) * 100.0 if total_tasks > 0 else 0.0
    
    @api.depends('invitation_ids')
    def _compute_invitation_count(self):
        """Tính số lượng invitation"""
        for record in self:
            record.invitation_count = len(record.invitation_ids)
    
    # ─────────────────────────────────────────────
    # ▶ VALIDATION METHODS
    # ─────────────────────────────────────────────
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """
        ✅ VALIDATION: Kiểm tra start_date <= end_date
        """
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError(_('Start date must be earlier than or equal to end date!'))
    
    @api.constrains('budget')
    def _check_budget(self):
        """
        ✅ VALIDATION: Kiểm tra budget >= 0
        """
        for record in self:
            if record.budget and record.budget < 0:
                raise ValidationError(_('Budget must be positive!'))

    # ─────────────────────────────────────────────
    # ▶ HELPER METHODS
    # ─────────────────────────────────────────────
    
    def _generate_project_code(self):
        """
        🔢 HELPER: Generate unique project code
        
        Returns:
            str: Generated project code in format PRJ-YYYY-####
        """
        # 📅 Get current year
        current_year = fields.Date.today().year
        
        # 🔍 Find existing projects with same year pattern
        existing_codes = self.env['vnfield.project'].search([
            ('code', 'like', f'PRJ-{current_year}-%')
        ]).mapped('code')
        
        # 🔢 Extract sequence numbers
        sequence_numbers = []
        for code in existing_codes:
            try:
                # Extract number from PRJ-YYYY-#### format
                parts = code.split('-')
                if len(parts) == 3 and parts[2].isdigit():
                    sequence_numbers.append(int(parts[2]))
            except (ValueError, IndexError):
                continue
        
        # 📈 Get next sequence number
        next_number = max(sequence_numbers, default=0) + 1
        
        # 🏷️ Generate new code
        return f'PRJ-{current_year}-{next_number:04d}'

    # ─────────────────────────────────────────────
    # ▶ ACTION METHODS
    # ─────────────────────────────────────────────    
    def action_start_project(self):
        """
        🚀 ACTION: Bắt đầu dự án
        """
        self.write({'state': 'in_progress'})
    
    def action_complete_project(self):
        """
        ✅ ACTION: Hoàn thành dự án
        """
        self.write({'state': 'completed'})
    
    def action_cancel_project(self):
        """
        ❌ ACTION: Hủy dự án
        """
        self.write({'state': 'cancelled'})
    
    def action_view_tasks(self):
        """
        📋 ACTION: Xem tất cả tasks của project này
        """
        self.ensure_one()
        action = {
            'name': f'Tasks - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'vnfield.task',
            'view_mode': 'kanban,tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {
                'default_project_id': self.id,
                'search_default_project_id': self.id,
            },
            'target': 'current',
        }
        
        # Nếu chỉ có 1 task, mở form view trực tiếp
        if len(self.task_ids) == 1:
            action.update({
                'res_id': self.task_ids.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
            })
        
        return action

    def action_view_contractors(self):
        """
        👥 ACTION: Xem tất cả contractors tham gia project này
        """
        self.ensure_one()
        action = {
            'name': f'Contractors - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'vnfield.contractor',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', self.contractor_ids.ids)],
            'context': {
                'default_project_id': self.id,
            },
            'target': 'current',
        }
            
        # Nếu chỉ có 1 contractor, mở form view trực tiếp
        if len(self.contractor_ids) == 1:
            action.update({
                'res_id': self.contractor_ids.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
            })
        
        return action

    def action_view_members(self):
        """
        Mở danh sách user_ids (thành viên) đang tham gia project này
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Project Members'),
            'res_model': 'res.users',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.user_ids.ids)],
            'target': 'current',
            'context': dict(self.env.context, default_project_id=self.id),
        }

    def action_invite_contractor(self):
        """Mở wizard để mời contractor tham gia"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invite Contractor',
            'res_model': 'vnfield.project.invitation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
                'default_inviter_contractor_id': self.owner_contractor_id.id,
                'default_subject': f'Invitation to join project: {self.name}'
            }
        }
    
    def action_view_invitations(self):
        """Xem danh sách invitation"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Project Invitations',
            'res_model': 'vnfield.project.invitation',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id}
        }

    # ─────────────────────────────────────────────
    # ▶ OVERRIDE METHODS
    # ─────────────────────────────────────────────
    
    @api.model
    def create(self, vals):
        # Tự động generate code nếu chưa có
        if not vals.get('code'):
            vals['code'] = self._generate_project_code()
        
        # Nếu chưa gán owner_contractor_id thì lấy contractor của user tạo
        if not vals.get('owner_contractor_id'):
            contractor = getattr(self.env.user, 'contractor_id', False)
            if contractor:
                vals['owner_contractor_id'] = contractor.id
        return super().create(vals)
