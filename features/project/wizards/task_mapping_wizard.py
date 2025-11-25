from odoo import models, fields, api, _
from odoo.exceptions import UserError

class TaskAssignmentWizard(models.TransientModel):
    _name = 'vnfield.task.mapping.wizard'
    _description = 'Task Mapping Wizard'

    executer_id = fields.Many2one('res.users', string='Executer', readonly=True)
    contractor_name=fields.Char(string='Contractor Name')
    


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        # Lấy executer_id từ context, nếu không có thì dùng current user
        executer_id = self.env.context.get('executer_id')
        if executer_id:
            user = self.env['res.users'].browse(executer_id)
            if user.exists():
                res['executer_id'] = user.id
            else:
                # Nếu user không tồn tại, dùng current user làm đại diện
                res['executer_id'] = self.env.user.id
        else:
            # Nếu không có executer_id trong context, dùng current user làm đại diện
            res['executer_id'] = self.env.user.id
            
        return res

    def action_map(self):
        for record in self:
            # Get system_name từ config
            config_param = self.env['ir.config_parameter'].sudo()
            system_name = config_param.get_param('vnfield.system_name', 'Unknown System')
            
            # Tạo sync_request trước khi gửi message
            sync_request = self.env['vnfield.sync.request'].create({
                'activity_name': f"Map User to Contractor - {record.executer_id.name}",
                'description': f"Mapping user {record.executer_id.name} to contractor {record.contractor_name}",
                'sync_type': 'export',  # Export user data to external contractor
                'priority': 'normal',
            })
            
            # Chuẩn bị message data với sync_request_id
            message_data = {
                'action': 'create_user',
                'source': system_name,
                'destination': record.contractor_name,
                'sync_request_id': sync_request.id,  # Include sync_request ID
                'user_data': {
                    'name': record.executer_id.name,
                    'login': record.executer_id.login,
                    'email': record.executer_id.email,
                    'user_type': record.executer_id.user_type,
                },
                'vals': {
                    'id': record.executer_id.id,
                    'name': record.executer_id.name,
                    'login': record.executer_id.login,
                    'email': record.executer_id.email,
                },
            }
            
            # Cập nhật description của sync_request với message content
            sync_request.write({
                'description': f"Mapping user {record.executer_id.name} to contractor {record.contractor_name}\nMessage content: {str(message_data)}"
            })
            
            # Get topic từ config
            topic = config_param.get_param('vnfield.kafka.topic', 'vnfield')
            
            # Produce message
            pubsub_service = self.env['vnfield.pubsub.service'].create({})
            result = pubsub_service.produce_message(topic, message_data)
            
            # # Update sync_request state based on message result
            # if result and result.get('success'):
            #     sync_request.write({'state': 'pending'})
            # else:
            #     sync_request.write({
            #         'state': 'failed',
            #         'description': sync_request.description + f"\nError: {result.get('error', 'Unknown error') if result else 'Message service unavailable'}"
            #     })
                
        return {'type': 'ir.actions.act_window_close'}
