# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

# ===========================================
# =         🤝 PROJECT INVITATION MODEL     =
# ===========================================

class ProjectInvitation(models.Model):
    """
    Model đại diện cho lời mời# ===========================================
# =    PROJECT INVITATION DEPENDENCIES     =
# =========================================== một contractor đến contractor khác
    để tham gia vào một project. 
    
    Business Flow:
    - Contractor A (owner) tạo project
    - Contractor A mời contractor B tham gia project
    - Contractor B có thể accept/reject invitation
    - Nếu accept, contractor B được thêm vào project.contractor_ids
    """
    _name = 'vnfield.project.invitation'
    _description = 'Project Invitation'
    _order = 'create_date desc, id desc'
    _rec_name = 'display_name'

    # ─────────────────────────────────────────────
    # ▶ BASIC INFORMATION FIELDS
    # ─────────────────────────────────────────────
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Tên hiển thị của lời mời'
    )
    
    subject = fields.Char(
        string='Subject',
        required=True,
        help='Tiêu đề lời mời'
    )
    
    message = fields.Text(
        string='Invitation Message',
        help='Nội dung chi tiết của lời mời'
    )
    
    # ─────────────────────────────────────────────
    # ▶ STATE AND WORKFLOW FIELDS
    # ─────────────────────────────────────────────
    
    state = fields.Selection([
        ('draft', 'Draft'),           # Chờ gửi
        ('sent', 'Sent'),            # Đã gửi, chờ phản hồi
        ('accepted', 'Accepted'),     # Đã chấp nhận
        ('rejected', 'Rejected'),     # Đã từ chối
        ('cancelled', 'Cancelled'),   # Đã hủy
        ('expired', 'Expired')        # Đã hết hạn
    ], string='Status', default='draft', required=True, tracking=True)
    
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], string='Priority', default='normal')
    
    # ─────────────────────────────────────────────
    # ▶ RELATIONSHIP FIELDS
    # ─────────────────────────────────────────────
    
    # Project được mời tham gia
    project_id = fields.Many2one(
        'vnfield.project',
        string='Project',
        required=True,
        ondelete='cascade',
        help='Dự án được mời tham gia'
    )
    
    # Contractor gửi lời mời (owner của project)
    inviter_contractor_id = fields.Many2one(
        'vnfield.contractor',
        string='Inviter Contractor',
        required=True,
        help='Contractor gửi lời mời (chủ sở hữu project)'
    )
    
    # Contractor nhận lời mời
    invitee_contractor_id = fields.Many2one(
        'vnfield.contractor',
        string='Invitee Contractor', 
        required=True,
        help='Contractor được mời tham gia'
    )
    
    # User tạo invitation (thuộc inviter contractor)
    inviter_user_id = fields.Many2one(
        'res.users',
        string='Inviter User',
        default=lambda self: self.env.user,
        required=True,
        help='User tạo lời mời'
    )
    
    # User phản hồi invitation (thuộc invitee contractor)
    responder_user_id = fields.Many2one(
        'res.users',
        string='Responder User',
        help='User phản hồi lời mời'
    )
    
    # ─────────────────────────────────────────────
    # ▶ DATE FIELDS
    # ─────────────────────────────────────────────
    
    sent_date = fields.Datetime(
        string='Sent Date',
        help='Ngày gửi lời mời'
    )
    
    response_date = fields.Datetime(
        string='Response Date',
        help='Ngày phản hồi lời mời'
    )
    
    expiry_date = fields.Datetime(
        string='Expiry Date',
        help='Ngày hết hạn lời mời',
        default=lambda self: datetime.now() + timedelta(days=7)
    )
    
    # ─────────────────────────────────────────────
    # ▶ COMPUTED FIELDS
    # ─────────────────────────────────────────────
    
    project_name = fields.Char(
        string='Project Name',
        related='project_id.name',
        store=True,
        help='Tên dự án'
    )
    
    project_owner_name = fields.Char(
        string='Project Owner',
        related='inviter_contractor_id.name',
        store=True,
        help='Tên contractor sở hữu project'
    )
    
    invitee_name = fields.Char(
        string='Invitee Name',
        related='invitee_contractor_id.name',
        store=True,
        help='Tên contractor được mời'
    )
    
    is_expired = fields.Boolean(
        string='Is Expired',
        compute='_compute_is_expired',
        store=True,
        help='Lời mời đã hết hạn'
    )
    
    can_respond = fields.Boolean(
        string='Can Respond',
        compute='_compute_can_respond',
        help='User hiện tại có thể phản hồi lời mời'
    )
    
    contractor_domain_types = fields.Char(
        string='Contractor Domain Types',
        compute='_compute_contractor_domain_types',
        help='Dynamic domain for contractor filtering'
    )
    
    # ─────────────────────────────────────────────
    # ▶ COMPUTED METHODS
    # ─────────────────────────────────────────────
    
    @api.depends('project_id', 'inviter_contractor_id', 'invitee_contractor_id')
    def _compute_display_name(self):
        """Tính display name cho invitation"""
        for record in self:
            if record.project_id and record.invitee_contractor_id:
                record.display_name = f"Invite {record.invitee_contractor_id.name} to {record.project_id.name}"
            else:
                record.display_name = "Project Invitation"
    
    @api.depends('expiry_date')
    def _compute_is_expired(self):
        """Kiểm tra invitation đã hết hạn chưa"""
        now = datetime.now()
        for record in self:
            if record.expiry_date:
                record.is_expired = record.expiry_date < now
            else:
                record.is_expired = False
    
    @api.depends('invitee_contractor_id', 'state')
    def _compute_can_respond(self):
        """Kiểm tra user hiện tại có thể respond không"""
        current_user = self.env.user
        for record in self:
            # User có thể respond nếu:
            # 1. Invitation ở trạng thái 'sent'
            # 2. User thuộc invitee contractor
            # 3. Chưa hết hạn
            can_respond = (
                record.state == 'sent' and
                current_user in record.invitee_contractor_id.user_ids and
                not record.is_expired
            )
            record.can_respond = can_respond

    @api.depends('project_id', 'project_id.project_type')
    def _compute_contractor_domain_types(self):
        """Tính toán domain types cho contractor filtering"""
        for record in self:
            if record.project_id and record.project_id.project_type == 'internal':
                record.contractor_domain_types = 'internal,shared'
            else:
                record.contractor_domain_types = 'internal,shared,external'
    
    # ─────────────────────────────────────────────
    # ▶ VALIDATION METHODS
    # ─────────────────────────────────────────────
    
    @api.constrains('inviter_contractor_id', 'invitee_contractor_id')
    def _check_different_contractors(self):
        """Contractor không thể mời chính mình"""
        for record in self:
            if record.inviter_contractor_id == record.invitee_contractor_id:
                raise ValidationError(_("Contractor cannot invite themselves to a project."))
    
    @api.constrains('project_id', 'inviter_contractor_id')
    def _check_project_owner(self):
        """Chỉ owner của project mới có thể mời contractor khác"""
        for record in self:
            if record.project_id.owner_contractor_id != record.inviter_contractor_id:
                raise ValidationError(_("Only the project owner can invite other contractors."))
    
    @api.constrains('expiry_date')
    def _check_expiry_date(self):
        """Expiry date phải lớn hơn ngày hiện tại"""
        for record in self:
            if record.expiry_date and record.expiry_date <= datetime.now():
                raise ValidationError(_("Expiry date must be in the future."))
    
    @api.constrains('project_id', 'invitee_contractor_id')
    def _check_project_contractor_type_compatibility(self):
        """
        🚫 VALIDATION: Kiểm tra tính tương thích giữa project type và contractor type
        
        Business Rules:
        - Internal Project: Chỉ cho phép mời internal + shared contractors
        - Shared Project: Cho phép mời tất cả loại contractors
        """
        for record in self:
            if record.project_id and record.invitee_contractor_id:
                project_type = record.project_id.project_type
                contractor_type = record.invitee_contractor_id.contractor_type
                
                if project_type == 'internal' and contractor_type == 'external':
                    raise ValidationError(_(
                        "❌ Internal projects cannot invite external contractors. "
                        "Only internal and shared contractors are allowed for internal projects."
                    ))
    
    # ─────────────────────────────────────────────
    # ▶ ONCHANGE METHODS - DOMAIN FILTERING
    # ─────────────────────────────────────────────
    
    @api.onchange('project_id')
    def _onchange_project_contractor_domain(self):
        """
        🔍 DOMAIN FILTERING: Lọc contractor list dựa trên project type
        
        Business Rules:
        - Internal Project → Internal + Shared contractors only
        - Shared Project → All contractors (internal, shared, external)
        """
        # Clear invitee_contractor_id khi thay đổi project
        self.invitee_contractor_id = False
        
        if self.project_id:
            project_type = self.project_id.project_type
            _logger.info(f"🔍 Project selected: {self.project_id.name}, type: {project_type}")
            
            if project_type == 'internal':
                # Internal project: chỉ internal và shared contractors
                _logger.info("🚫 Internal project - filtering to internal+shared contractors only")
                return {
                    'domain': {
                        'invitee_contractor_id': [('contractor_type', 'in', ['internal', 'shared'])]
                    }
                }
            else:  # shared project
                # Shared project: tất cả contractors
                _logger.info("✅ Shared project - allowing all contractor types")
                return {
                    'domain': {
                        'invitee_contractor_id': [('contractor_type', 'in', ['internal', 'shared', 'external'])]
                    }
                }
        else:
            # Không có project: hiển thị tất cả
            _logger.info("⚪ No project selected - showing all contractors")
            return {
                'domain': {
                    'invitee_contractor_id': []
                }
            }

    # ─────────────────────────────────────────────
    # ▶ BUSINESS LOGIC METHODS
    # ─────────────────────────────────────────────
    
    def action_send_invitation(self):
        """Gửi lời mời"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Only draft invitations can be sent."))
            
            # Kiểm tra contractor đã tham gia project chưa
            if record.invitee_contractor_id in record.project_id.contractor_ids:
                raise UserError(_("This contractor is already participating in the project."))
            
            record.write({
                'state': 'sent',
                'sent_date': datetime.now()
            })
    
    def action_accept_invitation(self):
        """Chấp nhận lời mời"""
        for record in self:
            if record.state != 'sent':
                raise UserError(_("Only sent invitations can be accepted."))
            
            if record.is_expired:
                raise UserError(_("This invitation has expired."))
            
            # Thêm contractor vào project
            record.project_id.contractor_ids = [(4, record.invitee_contractor_id.id)]
            
            record.write({
                'state': 'accepted',
                'response_date': datetime.now(),
                'responder_user_id': self.env.user.id
            })
    
    def action_reject_invitation(self):
        """Từ chối lời mời"""
        for record in self:
            if record.state != 'sent':
                raise UserError(_("Only sent invitations can be rejected."))
            
            record.write({
                'state': 'rejected', 
                'response_date': datetime.now(),
                'responder_user_id': self.env.user.id
            })
    
    def action_cancel_invitation(self):
        """Hủy lời mời (chỉ inviter có thể hủy)"""
        for record in self:
            if record.state not in ['draft', 'sent']:
                raise UserError(_("Only draft or sent invitations can be cancelled."))
            
            record.write({
                'state': 'cancelled',
                'response_date': datetime.now()
            })
    
    # ─────────────────────────────────────────────
    # ▶ CRON METHODS
    # ─────────────────────────────────────────────
    
    @api.model
    def _cron_expire_invitations(self):
        """Cron job để tự động expire các invitation hết hạn"""
        expired_invitations = self.search([
            ('state', '=', 'sent'),
            ('expiry_date', '<', datetime.now())
        ])
        
        expired_invitations.write({'state': 'expired'})
        
        return True


# ===========================================
# =         🏗️ ENHANCED PROJECT MODEL       =
# ===========================================

# ===========================================
# =    🏗️ PROJECT INVITATION DEPENDENCIES   =
# ===========================================

# Model Dependencies Mapping:

# Core Relationships:
# - vnfield.project.invitation: Main invitation model
# - vnfield.project: Base project model 
# - vnfield.contractor: Inviter và invitee contractors
# - res.users: Inviter user và responder user

# Business Flow:
# 1. Project owner (contractor A) tạo invitation cho contractor B
# 2. Invitation ở state 'draft' → action_send_invitation() → state 'sent'
# 3. Contractor B user có thể accept/reject invitation
# 4. Nếu accept: contractor B được add vào project.contractor_ids
# 5. Cron job tự động expire invitation hết hạn

# States Workflow:
# - draft → sent (action_send_invitation)
# - sent → accepted (action_accept_invitation) 
# - sent → rejected (action_reject_invitation)
# - draft/sent → cancelled (action_cancel_invitation)
# - sent → expired (cron job)

# Validations:
# - Contractor không thể invite chính mình
# - Chỉ project owner có thể invite
# - Expiry date phải trong tương lai
# - Chỉ sent invitation mới có thể respond
# - Không thể invite contractor đã tham gia project

# Computed Fields:
# - display_name: "Invite {invitee} to {project}"
# - is_expired: Based on expiry_date vs current time
# - can_respond: User thuộc invitee contractor và invitation chưa expire

# Security Access:
# - Inviter contractor users: create, read invitations they sent
# - Invitee contractor users: read, respond to invitations for them  
# - Admin: full access to all invitations
