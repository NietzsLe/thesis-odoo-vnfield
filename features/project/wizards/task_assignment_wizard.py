from odoo import models, fields, api, _
from odoo.exceptions import UserError

class TaskAssignmentWizard(models.TransientModel):
    _name = 'vnfield.task.assignment.wizard'
    _description = 'Task Assignment Wizard'

    task_id = fields.Many2one('vnfield.task', string='Task', required=True)
    assigner_id = fields.Many2one('res.users', string='Assigner', readonly=True)
    verifier_id = fields.Many2one('res.users', string='Verifier',
        domain="[('id', 'in', project_user_ids)]",
        help='Chỉ chọn user thuộc project')
    is_outsourced = fields.Boolean('Is Outsourced')
    contractor_assignee_id = fields.Many2one(
        'vnfield.contractor',
        string='Contractor Assignee',
        domain="[('id', 'in', project_contractor_ids)]",
        help='Chỉ chọn contractor thuộc project'
    )
    assignee_id = fields.Many2one(
        'res.users',
        string='Assignee',
        domain="[('id', 'in', project_user_ids)]",
        help='Chỉ chọn user thuộc project'
    )
    outsource_project_id = fields.Many2one('vnfield.project', string='Outsourced Project')

    project_contractor_ids = fields.Many2many(
        'vnfield.contractor',
        string='Project Contractors',
        compute='_compute_project_contractor_ids',
        store=True,
        help='Danh sách contractor thuộc project này (dùng cho domain)'
    )
    
    @api.depends('task_id', 'task_id.project_id', 'task_id.project_id.contractor_ids')
    def _compute_project_contractor_ids(self):
        for rec in self:
            rec.project_contractor_ids = rec.task_id.project_id.contractor_ids
    
    
    project_user_ids = fields.Many2many(
        'res.users',
        string='Project Users',
        compute='_compute_project_user_ids',
        store=True,
        help='Danh sách user thuộc project này (dùng cho domain)'
    )

    @api.depends('task_id', 'task_id.project_id', 'task_id.project_id.user_ids')
    def _compute_project_user_ids(self):
        for rec in self:
            rec.project_user_ids = rec.task_id.project_id.user_ids

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        task = self.env['vnfield.task'].browse(self.env.context.get('active_id'))
        res['task_id'] = task.id
        # Nếu task chưa có assigner_id thì mặc định là user hiện tại
        res['assigner_id'] = task.assigner_id.id if task.assigner_id else self.env.uid
        res['verifier_id'] = task.verifier_id.id
        res['is_outsourced'] = task.is_outsourced
        res['contractor_assignee_id'] = task.contractor_assignee_id.id
        res['assignee_id'] = task.assignee_id.id
        res['outsource_project_id'] = task.outsource_project_id.id
        return res

    def action_assign(self):
        self.ensure_one()
        self.task_id.write({
            'verifier_id': self.verifier_id.id,
            'is_outsourced': self.is_outsourced,
            'contractor_assignee_id': self.contractor_assignee_id.id,
            'assignee_id': self.assignee_id.id,
            'outsource_project_id': self.outsource_project_id.id,
            'status': 'planning',
        })
        return {'type': 'ir.actions.act_window_close'}

    def action_create_remote_requirement(self):
        """Mở wizard tạo remote requirement với task_id hiện tại"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Remote Requirement',
            'res_model': 'vnfield.market.create.remote.requirement.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_task_id': self.task_id.id,
                'from_task_assignment': True,
            }
        }
