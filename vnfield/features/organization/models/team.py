# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

# =================================
# =         👥 TEAM MODEL                   =
# ===========================================

class VnfieldTeam(models.Model):
    """
    Team model đại diện cho một contractor trong project.
    - Gắn chặt với một contractor (Many2one required)
    - Chỉ tham gia một project (Many2one required)
    - Có team leader và team members
    - Quản lý cấu trúc team cho project management
    """
    _name = 'vnfield.team'
    _description = 'VNField Team'
    _order = 'project_id, contractor_id, name'
    
    # ─────────────────────────────────────────────
    # ▶ BASIC INFORMATION FIELDS
    # ─────────────────────────────────────────────
    
    name = fields.Char(
        string='Team Name',
        required=True,
        help='Tên đội nhóm'
    )
    
    description = fields.Text(
        string='Description',
        help='Mô tả về team và vai trò trong project'
    )
    
    code = fields.Char(
        string='Team Code',
        help='Mã team duy nhất',
        copy=False
    )
    
    external_id = fields.Char(
        string='External ID',
        help='ID từ hệ thống bên ngoài',
        copy=False
    )
    
    # ─────────────────────────────────────────────
    # ▶ REQUIRED RELATIONSHIPS
    # ─────────────────────────────────────────────
    
    contractor_id = fields.Many2one(
        'vnfield.contractor',
        string='Contractor',
        required=False,
        ondelete='cascade',
        help='Contractor mà team này đại diện'
    )
    
    subcontractor_id = fields.Many2one(
        'vnfield.subcontractor',
        string='Subcontractor',
        required=False,
        ondelete='cascade',
        help='Subcontractor mà team này đại diện'
    )
    
    project_id = fields.Many2one(
        'vnfield.project',
        string='Project',
        required=True,
        ondelete='cascade',
        help='Project mà team này tham gia'
    )
    
    # ─────────────────────────────────────────────
    # ▶ TEAM STRUCTURE FIELDS
    # ─────────────────────────────────────────────
    
    team_leader_id = fields.Many2one(
        'res.users',
        string='Team Leader',
        required=True,
        help='Trưởng nhóm của team'
    )
    
    team_member_ids = fields.Many2many(
        'res.users',
        'team_member_rel',
        'team_id',
        'user_id',
        string='Team Members',
        help='Các thành viên trong team'
    )
    
    # ─────────────────────────────────────────────
    # ▶ STATUS AND WORKFLOW FIELDS
    # ─────────────────────────────────────────────
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('disbanded', 'Disbanded')
    ], string='Status', default='draft', required=True)
    
    # ─────────────────────────────────────────────
    # ▶ COMPUTED FIELDS
    # ─────────────────────────────────────────────
    
    member_count = fields.Integer(
        string='Member Count',
        compute='_compute_member_count',
        store=True,
        help='Số lượng thành viên trong team'
    )
    
    total_members = fields.Integer(
        string='Total Members',
        compute='_compute_total_members',
        store=True,
        help='Tổng số người trong team (bao gồm leader)'
    )
    
    user_count = fields.Integer(
        string='User Count',
        compute='_compute_user_count',
        store=True,
        help='Tổng số users trong team (leader + members) - để hiển thị trong button'
    )
    
    # Related fields từ contractor
    contractor_name = fields.Char(
        related='contractor_id.name',
        string='Contractor Name',
        store=True
    )
    
    contractor_type = fields.Selection(
        related='contractor_id.contractor_type',
        string='Contractor Type',
        store=True
    )
    
    # ⭐ TEAM TYPE INHERITED FROM CONTRACTOR
    team_type = fields.Selection([
        ('internal', 'Internal Team - Nội bộ'),
        ('external', 'External Team - Bên ngoài'),
        ('shared', 'Shared Team - Liên nhà thầu')
    ], string='Team Type', 
       compute='_compute_team_type', 
       store=True,
       help='Team type được kế thừa từ contractor type')
    
    # 🔄 AUTO STATE MANAGEMENT BASED ON PROJECT
    auto_state = fields.Selection([
        ('active', 'Auto Active'),
        ('inactive', 'Auto Inactive'),
        ('disbanded', 'Auto Disbanded')
    ], string='Auto State',
       compute='_compute_auto_state',
       store=True,
       help='Team state tự động dựa trên project lifecycle')
    
    # Related fields từ project
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
    # ▶ DATE FIELDS
    # ─────────────────────────────────────────────
    
    start_date = fields.Date(
        string='Team Start Date',
        help='Ngày team bắt đầu tham gia project'
    )
    
    end_date = fields.Date(
        string='Team End Date',
        help='Ngày team kết thúc tham gia project'
    )
    
    # ─────────────────────────────────────────────
    # ▶ COMPUTED METHODS
    # ─────────────────────────────────────────────
    
    @api.depends('team_member_ids')
    def _compute_member_count(self):
        """
        👥 COMPUTED FIELD: Tính số lượng team members (không bao gồm leader)
        """
        for record in self:
            record.member_count = len(record.team_member_ids)
    
    @api.depends('team_member_ids', 'team_leader_id')
    def _compute_total_members(self):
        """
        📊 COMPUTED FIELD: Tính tổng số người trong team (bao gồm leader)
        """
        for record in self:
            total = len(record.team_member_ids)
            if record.team_leader_id:
                total += 1
            record.total_members = total
    
    @api.depends('contractor_id.contractor_type')
    def _compute_team_type(self):
        """
        ⭐ COMPUTED FIELD: Team type kế thừa từ contractor type
        """
        for record in self:
            if record.contractor_id and record.contractor_id.contractor_type:
                record.team_type = record.contractor_id.contractor_type
            else:
                record.team_type = 'internal'  # Default
    
    @api.depends('project_id.state')
    def _compute_auto_state(self):
        """
        🔄 COMPUTED FIELD: Auto state dựa trên project lifecycle
        Team tự động ngừng hoạt động khi project kết thúc/bị hủy
        """
        for record in self:
            if record.project_id and record.project_id.state:
                project_state = record.project_id.state
                
                # 📝 MAPPING: Project states to team auto states
                # Project states: 'draft', 'planning', 'in_progress', 'on_hold', 'completed', 'cancelled'
                if project_state == 'in_progress':
                    record.auto_state = 'active'
                elif project_state == 'completed':
                    record.auto_state = 'inactive'  
                elif project_state == 'cancelled':
                    record.auto_state = 'disbanded'
                else:  # draft, planning, on_hold
                    record.auto_state = 'inactive'
            else:
                record.auto_state = 'inactive'
    
    # ─────────────────────────────────────────────
    # ▶ VALIDATION METHODS
    # ─────────────────────────────────────────────
    
    @api.constrains('team_leader_id', 'contractor_id')
    def _check_leader_contractor(self):
        """
        ✅ VALIDATION: Team leader phải thuộc cùng contractor
        """
        for record in self:
            if record.team_leader_id and record.contractor_id:
                if record.team_leader_id.contractor_id.id != record.contractor_id.id:
                    raise ValidationError(
                        _('Team leader must belong to the same contractor as the team!')
                    )
    
    @api.constrains('team_member_ids', 'contractor_id')
    def _check_members_contractor(self):
        """
        ✅ VALIDATION: Tất cả team members phải thuộc cùng contractor
        """
        for record in self:
            if record.team_member_ids and record.contractor_id:
                invalid_members = record.team_member_ids.filtered(
                    lambda member: member.contractor_id.id != record.contractor_id.id
                )
                if invalid_members:
                    raise ValidationError(
                        _('All team members must belong to the same contractor as the team!')
                    )
    
    @api.constrains('team_leader_id', 'team_member_ids')
    def _check_leader_not_in_members(self):
        """
        ✅ VALIDATION: Team leader không được là team member
        """
        for record in self:
            if record.team_leader_id and record.team_leader_id.id in record.team_member_ids.ids:
                raise ValidationError(
                    _('Team leader cannot be a team member at the same time!')
                )
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """
        ✅ VALIDATION: Kiểm tra start_date <= end_date
        """
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError(_('Start date must be earlier than or equal to end date!'))
    
    @api.constrains('contractor_id', 'project_id')
    def _check_contractor_in_project(self):
        """
        ✅ VALIDATION: Contractor phải tham gia project này
        """
        for record in self:
            if record.contractor_id and record.project_id:
                if record.contractor_id.id not in record.project_id.contractor_ids.ids:
                    raise ValidationError(
                        _('The contractor must be participating in this project to create a team!')
                    )
    
    @api.constrains('external_id', 'team_type')
    def _check_external_id(self):
        """
        ✅ VALIDATION: External ID validation theo type mới
        - External: Bắt buộc có external_id và phải unique
        - Shared: Có thể có external_id, nếu có phải unique
        - Internal: Không được có external_id
        """
        for record in self:
            if record.team_type == 'external':
                # External teams bắt buộc có external_id
                if not record.external_id:
                    raise ValidationError(
                        _('External teams must have an External ID!')
                    )
                # Check uniqueness
                duplicate = self.search([
                    ('external_id', '=', record.external_id),
                    ('team_type', 'in', ['external', 'shared']),
                    ('id', '!=', record.id)
                ])
                if duplicate:
                    raise ValidationError(
                        _('External ID must be unique!')
                    )
            elif record.team_type == 'shared':
                # Shared teams có thể có external_id, nếu có phải unique
                if record.external_id:
                    duplicate = self.search([
                        ('external_id', '=', record.external_id),
                        ('team_type', 'in', ['external', 'shared']),
                        ('id', '!=', record.id)
                    ])
                    if duplicate:
                        raise ValidationError(
                            _('External ID must be unique!')
                        )
            else:  # internal
                # Internal teams không được có external_id
                if record.external_id:
                    raise ValidationError(
                        _('Internal teams cannot have External ID!')
                    )
    
    # ─────────────────────────────────────────────
    # ▶ ACTION METHODS
    # ─────────────────────────────────────────────
    
    def action_view_users(self):
        """
        👥 ACTION: Hiển thị tất cả users thuộc team này
        
        Bao gồm team leader và team members
        
        Returns:
            dict: Window action để hiển thị user kanban view
        """
        # Kết hợp team leader và team members
        all_user_ids = []
        if self.team_leader_id:
            all_user_ids.append(self.team_leader_id.id)
        all_user_ids.extend(self.team_member_ids.ids)
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'👥 View Users ({self.user_count})',
            'res_model': 'res.users',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', all_user_ids)],
            'context': {'default_contractor_id': self.contractor_id.id},
            'target': 'current',
        }

    def action_activate_team(self):
        """
        ✅ ACTION: Kích hoạt team
        """
        self.write({'state': 'active'})
    
    def action_deactivate_team(self):
        """
        ⏸️ ACTION: Tạm dừng team
        """
        self.write({'state': 'inactive'})
    
    def action_disband_team(self):
        """
        🔚 ACTION: Giải tán team
        """
        self.write({'state': 'disbanded'})
    
    # ─────────────────────────────────────────────
    # ▶ LIFECYCLE MANAGEMENT METHODS
    # ─────────────────────────────────────────────
    
    def action_sync_with_project(self):
        """
        🔄 ACTION: Đồng bộ team state với project lifecycle
        Team sẽ tự động cập nhật state dựa trên project state
        """
        for record in self:
            if record.auto_state and record.auto_state != record.state:
                # 💡 NOTE(assistant): Chỉ sync nếu auto_state khác state hiện tại
                old_state = record.state
                record.state = record.auto_state
                
                # Log lifecycle change without message_post
                _logger.info(f'Team {record.name} state changed from {old_state} to {record.state} due to project lifecycle.')
    
    @api.model
    def cron_sync_team_lifecycle(self):
        """
        ⏰ CRON JOB: Định kỳ đồng bộ team state với project lifecycle
        Chạy mỗi ngày để đảm bảo team states được cập nhật
        """
        active_teams = self.search([
            ('state', 'in', ['draft', 'active', 'inactive']),
            ('project_id', '!=', False)
        ])
        
        sync_count = 0
        for team in active_teams:
            old_state = team.state
            team.action_sync_with_project()
            if team.state != old_state:
                sync_count += 1
        
        # 📊 Log summary
        _logger.info(f'Team lifecycle sync completed: {sync_count} teams updated out of {len(active_teams)} checked.')
        return sync_count
    
    def force_disband_from_project(self):
        """
        🚫 ACTION: Force disband team khi project bị cancelled
        Method này được gọi từ project model khi project cancelled
        """
        for record in self:
            if record.state not in ['disbanded']:
                record.write({
                    'state': 'disbanded',
                    'end_date': fields.Date.today()
                })
                # Log without message_post
                _logger.info(f'Team {record.name} has been disbanded due to project cancellation.')
    
    # ─────────────────────────────────────────────
    # ▶ ONCHANGE METHODS
    # ─────────────────────────────────────────────
    
    @api.onchange('contractor_id')
    def _onchange_contractor_id(self):
        """
        🔄 ONCHANGE: Reset team leader và members khi đổi contractor
        """
        if self.contractor_id:
            self.team_leader_id = False
            self.team_member_ids = [(5, 0, 0)]  # Clear all members
            
            # Set domain cho team_leader_id và team_member_ids
            contractor_users = self.contractor_id.user_ids.ids
            return {
                'domain': {
                    'team_leader_id': [('id', 'in', contractor_users)],
                    'team_member_ids': [('id', 'in', contractor_users)]
                }
            }
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """
        🔄 ONCHANGE: Set domain cho contractor dựa trên project
        """
        if self.project_id:
            # Chỉ cho phép chọn contractors đang tham gia project này
            return {
                'domain': {
                    'contractor_id': [('id', 'in', self.project_id.contractor_ids.ids)]
                }
            }
    
    @api.onchange('team_leader_id')
    def _onchange_team_leader_id(self):
        """
        🔄 ONCHANGE: Loại bỏ leader khỏi team_members nếu có
        """
        if self.team_leader_id and self.team_leader_id.id in self.team_member_ids.ids:
            self.team_member_ids = [(3, self.team_leader_id.id)]  # Remove leader from members
    
    # ─────────────────────────────────────────────
    # ▶ NAME METHODS
    # ─────────────────────────────────────────────
    
    def name_get(self):
        """
        📝 NAME_GET: Custom display name for team
        """
        result = []
        for record in self:
            name = f"{record.name}"
            if record.contractor_name and record.project_name:
                name = f"{record.name} ({record.contractor_name} - {record.project_name})"
            result.append((record.id, name))
        return result

    @api.depends('team_member_ids', 'team_leader_id')
    def _compute_total_members(self):
        """
        🔢 COMPUTED FIELD: Tính tổng số người trong team (bao gồm leader)
        """
        for record in self:
            count = len(record.team_member_ids)
            if record.team_leader_id:
                count += 1
            record.total_members = count
    
    @api.depends('team_member_ids', 'team_leader_id')
    def _compute_user_count(self):
        """
        👥 COMPUTED FIELD: Tính tổng số users trong team cho button display
        Giống total_members nhưng dành riêng cho button count
        """
        for record in self:
            count = len(record.team_member_ids)
            if record.team_leader_id:
                count += 1
            record.user_count = count
    # ─────────────────────────────────────────────
    # ▶ DEPENDENCIES DESCRIPTION
    # ─────────────────────────────────────────────
    
    """
    🔗 SYMBOL DEPENDENCIES:
    
    Internal Dependencies:
    - vnfield.contractor: Many2one required (team gắn chặt với contractor)
    - vnfield.project: Many2one required (team chỉ tham gia 1 project)
    
    External Dependencies:
    - res.users: Many2one cho team_leader, Many2many cho team_members
    - odoo.exceptions.ValidationError: Cho validation constraints
    
    Relationships Pattern:
    - Required relationships: contractor_id, project_id với ondelete='cascade'
    - Team structure: team_leader_id (Many2one), team_member_ids (Many2many)
    - Related fields: contractor_name, contractor_type, project_name, project_state
    - Computed analytics: member_count, total_members
    
    Business Logic:
    - Team leader phải thuộc cùng contractor
    - Team members phải thuộc cùng contractor  
    - Team leader không được là team member
    - Contractor phải tham gia project mới tạo được team
    - Smart domain filters trong onchange methods
    - Custom name_get cho display format
    
    Validation Rules:
    - Contractor consistency across leader/members
    - Date validation cho start/end dates
    - Project participation validation
    - Leader vs members separation
    """
