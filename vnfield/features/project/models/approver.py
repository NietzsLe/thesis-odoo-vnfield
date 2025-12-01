# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# ===========================================
# =           APPROVER MODEL                =
# ===========================================

class Approver(models.Model):
    """
    Đại diện cho một người hoặc team phê duyệt trong một bước.
    """
    _name = 'vnfield.approver'
    _description = 'Approver (User or Team)'

    step_id = fields.Many2one('vnfield.approval.step', string='Approval Step', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User Approver')
    team_id = fields.Many2one('vnfield.team', string='Team Approver')
    contractor_id = fields.Many2one('vnfield.contractor', string='Contractor Approver')
    
    # ─────────────────────────────────────────────
    # ▶ APPROVER TYPE CLASSIFICATION
    # ─────────────────────────────────────────────
    
    approver_type = fields.Selection([
        ('internal', 'Internal Approver'),
        ('shared', 'Shared Approver')
    ], string='Approver Type', default='internal', required=True, tracking=True,
       help='Internal: chỉ internal teams. Shared: external và shared teams')
    
    external_id = fields.Char(
        string='External ID',
        help='ID của approver trong hệ thống bên ngoài (chỉ dành cho Shared Approver)',
        copy=False
    )
    
    role = fields.Selection([
        ('project_initiator', 'Project Initiator'),
        ('subcontractor_approver', 'Subcontractor Approver'),
        ('main_contractor_approver', 'Main Contractor Approver'),
        ('consultant_approver', 'Consultant Approver'),
        ('client_representative', 'Client Representative'),
        ('technical_approver', 'Technical Approver'),
        ('qaqc_approver', 'QA/QC Approver'),
        ('hse_approver', 'HSE Approver'),
        ('contract_approver', 'Contract Approver'),
        ('finance_approver', 'Finance Approver'),
        ('planning_approver', 'Planning Approver'),
        ('legal_approver', 'Legal Approver'),
    ], string='Approver Role', required=True)
    
    # ─────────────────────────────────────────────
    # ▶ APPROVAL DECISION TRACKING
    # ─────────────────────────────────────────────
    
    decision = fields.Selection([
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('delegated', 'Delegated')
    ], string='Decision', default='pending', required=True, tracking=True,
       help='Quyết định phê duyệt của approver này')
    
    decision_date = fields.Datetime(
        string='Decision Date',
        help='Thời gian đưa ra quyết định phê duyệt'
    )
    
    decision_comments = fields.Text(
        string='Decision Comments',
        help='Ghi chú hoặc lý do cho quyết định phê duyệt'
    )
    
    delegated_to_user_id = fields.Many2one(
        'res.users',
        string='Delegated To User',
        help='Người được ủy quyền phê duyệt (nếu decision = delegated)'
    )
    
    # ─────────────────────────────────────────────
    # ▶ COMPUTED FIELDS
    # ─────────────────────────────────────────────
    
    approver_name = fields.Char(
        string='Approver Name',
        compute='_compute_approver_name',
        store=True,
        help='Tên hiển thị của approver (user/team/contractor)'
    )
    
    @api.depends('user_id', 'team_id', 'contractor_id')
    def _compute_approver_name(self):
        """
        💡 NOTE(assistant): Tính tên hiển thị của approver
        
        🧪 Logic:
        - Nếu là user → user.name
        - Nếu là team → team.name  
        - Nếu là contractor → contractor.name
        """
        for record in self:
            if record.user_id:
                record.approver_name = record.user_id.name
            elif record.team_id:
                record.approver_name = record.team_id.name
            elif record.contractor_id:
                record.approver_name = record.contractor_id.name
            else:
                record.approver_name = 'No Approver'

    @api.constrains('user_id', 'team_id', 'contractor_id')
    def _check_approver_entity(self):
        for rec in self:
            entities = [bool(rec.user_id), bool(rec.team_id), bool(rec.contractor_id)]
            if entities.count(True) == 0:
                raise ValidationError(_('Approver must be a user, a team, or a contractor.'))
            if entities.count(True) > 1:
                raise ValidationError(_('Approver can only be one of: user, team, or contractor.'))
    
    @api.constrains('decision', 'delegated_to_user_id')
    def _check_delegation_consistency(self):
        """
        💡 NOTE(assistant): Đảm bảo tính nhất quán của delegation
        
        🧪 Business Rule:
        - decision = 'delegated' → phải có delegated_to_user_id
        - decision != 'delegated' → không được có delegated_to_user_id
        """
        for record in self:
            if record.decision == 'delegated' and not record.delegated_to_user_id:
                raise ValidationError('Khi decision là Delegated, phải chỉ định người được ủy quyền')
            if record.decision != 'delegated' and record.delegated_to_user_id:
                raise ValidationError('Chỉ khi decision là Delegated mới được chỉ định người ủy quyền')
    
    # ─────────────────────────────────────────────
    # ▶ BUSINESS LOGIC METHODS
    # ─────────────────────────────────────────────
    
    def action_approve(self):
        """
        ✅ ACTION: Approver phê duyệt
        
        💡 NOTE(assistant): Set decision = 'approved' và timestamp
        
        🧪 Usage:
        approver.action_approve()
        """
        for record in self:
            if record.decision != 'pending':
                raise ValidationError(f'Không thể phê duyệt approver đã có quyết định: {record.decision}')
            
            record.write({
                'decision': 'approved',
                'decision_date': fields.Datetime.now()
            })
        
        return True
    
    def action_reject(self):
        """
        🚫 ACTION: Approver từ chối
        
        💡 NOTE(assistant): Set decision = 'rejected' và timestamp
        
        🧪 Usage:
        approver.action_reject()
        """
        for record in self:
            if record.decision != 'pending':
                raise ValidationError(f'Không thể từ chối approver đã có quyết định: {record.decision}')
            
            record.write({
                'decision': 'rejected',
                'decision_date': fields.Datetime.now()
            })
        
        return True
    
    def action_delegate(self, delegated_user_id, comments=None):
        """
        🔄 ACTION: Ủy quyền phê duyệt
        
        💡 NOTE(assistant): Set decision = 'delegated' và chỉ định người ủy quyền
        
        🧪 Usage:
        approver.action_delegate(user_id, "Ủy quyền do bận công tác")
        """
        for record in self:
            if record.decision != 'pending':
                raise ValidationError(f'Không thể ủy quyền approver đã có quyết định: {record.decision}')
            
            record.write({
                'decision': 'delegated',
                'decision_date': fields.Datetime.now(),
                'delegated_to_user_id': delegated_user_id,
                'decision_comments': comments or 'Ủy quyền phê duyệt'
            })
        
        return True
    
    def action_reset(self):
        """
        🔄 ACTION: Reset quyết định về pending
        
        💡 NOTE(assistant): Reset decision về pending để có thể phê duyệt lại
        
        🧪 Usage:
        approver.action_reset()
        """
        for record in self:
            record.write({
                'decision': 'pending',
                'decision_date': False,
                'decision_comments': False,
                'delegated_to_user_id': False
            })
        
        return True
