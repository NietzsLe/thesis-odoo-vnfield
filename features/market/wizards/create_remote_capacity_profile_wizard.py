# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
import xmlrpc.client

_logger = logging.getLogger(__name__)

class CreateRemoteCapacityProfileWizard(models.TransientModel):
    """
    🧙‍♂️ WIZARD TO CREATE NEW REMOTE CAPACITY PROFILE
    
    Popup wizard để tạo mới remote capacity profile qua RPC.
    """
    _name = 'vnfield.market.create.remote.capacity.profile.wizard'
    _description = 'Create Remote Capacity Profile Wizard'
    
    # ═══════════════════════════════════════════
    # 🏗️ WIZARD FIELDS
    # ═══════════════════════════════════════════
    
    title = fields.Char(string='Title', required=True, help="Capacity profile title")
    description = fields.Html(string='Description', help="Detailed description")
    
    # Work details
    work_category = fields.Selection([
        ('construction', 'Thi công xây dựng'),
        ('design', 'Thiết kế'),
        ('consulting', 'Tư vấn'),
        ('supervision', 'Giám sát'),
        ('survey', 'Khảo sát'),
        ('testing', 'Thí nghiệm'),
        ('other', 'Khác')
    ], string='Work Category', required=True)
    
    experience_years = fields.Integer(string='Experience Years', default=0)
    team_size = fields.Integer(string='Team Size', default=1)
    current_workload = fields.Selection([
        ('low', 'Thấp (< 30%)'),
        ('medium', 'Vừa (30-70%)'),
        ('high', 'Cao (70-90%)'),
        ('full', 'Đầy (> 90%)')
    ], string='Current Workload', default='low')
    
    # Budget capacity
    budget_capacity_min = fields.Monetary(string='Budget Capacity Min', currency_field='currency_id')
    budget_capacity_max = fields.Monetary(string='Budget Capacity Max', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    # Availability
    available_from = fields.Date(string='Available From')
    max_project_duration = fields.Integer(string='Max Project Duration (months)', default=12)
    
    # Status - remove field completely, will be set in action
    # state = fields.Selection([
    #     ('waiting_match', 'Waiting Match'),
    #     ('matched', 'Matched'),
    #     ('inactive', 'Inactive')
    # ], string='State', default='waiting_match', required=True)
    
    # Contractor selection
    remote_contractor_id = fields.Selection(
        selection='_get_remote_contractors_selection',
        string='Contractor',
        required=True,
        help="Select contractor for this capacity profile"
    )
    
    # ═══════════════════════════════════════════
    # 🔗 REMOTE CONTRACTOR SELECTION METHODS
    # ═══════════════════════════════════════════
    
    @api.model
    def default_get(self, fields_list):
        """Override default_get to ensure correct state value"""
        defaults = super().default_get(fields_list)
        # No need to set state since field doesn't exist
        return defaults

    @api.model
    def create(self, vals):
        """Override create to ensure correct state value"""
        # No need to set state since field doesn't exist
        return super().create(vals)

    @api.model
    def _get_remote_contractors_selection(self):
        """Get list of remote contractors for selection field"""
        try:
            # Get remote contractor IDs - search method with empty domain
            remote_ids = self._rpc_call('search', 'vnfield.contractor')
            
            if not remote_ids:
                return [('', 'No contractors available')]
            
            # Read contractor names - read method with IDs and fields
            contractors = self._rpc_call(
                'read',
                'vnfield.contractor', 
                [remote_ids, ['name']]
            )
            
            # Build selection list
            selection = []
            for contractor in contractors:
                selection.append((str(contractor['id']), contractor['name']))
            
            return selection
            
        except Exception as e:
            _logger.error(f"Error getting remote contractors: {str(e)}")
            return [('', 'Error loading contractors')]
    
    # ═══════════════════════════════════════════
    # 🔄 RPC COMMUNICATION METHODS
    # ═══════════════════════════════════════════
    
    def _get_integration_config(self):
        """Lấy cấu hình integration server từ system parameters"""
        config_param = self.env['ir.config_parameter'].sudo()
        return {
            'url': config_param.get_param('vnfield.integration_server_url', ''),
            'db': config_param.get_param('vnfield.integration_database', ''),
            'username': config_param.get_param('vnfield.integration_username', ''),
            'api_key': config_param.get_param('vnfield.integration_api_key', ''),
        }
    
    def _get_rpc_connection(self):
        """Tạo RPC connection tới integration server"""
        config = self._get_integration_config()
        
        if not config['url']:
            raise UserError(_('Integration server URL not configured. Please configure in system parameters.'))
            
        if not config['db']:
            raise UserError(_('Integration database not configured.'))
            
        if not config['username']:
            raise UserError(_('Integration username not configured.'))
            
        if not config['api_key']:
            raise UserError(_('Integration API key not configured.'))
            
        try:
            # Setup XML-RPC endpoints
            server_url = config['url'].rstrip('/')
            common_endpoint = f"{server_url}/xmlrpc/2/common"
            object_endpoint = f"{server_url}/xmlrpc/2/object"
            
            # Test connection and authenticate
            common = xmlrpc.client.ServerProxy(common_endpoint)
            server_info = common.version()
            _logger.info(f"Connected to Odoo server version: {server_info.get('server_version', 'Unknown')}")
            
            uid = common.authenticate(
                config['db'],
                config['username'],
                config['api_key'],
                {}
            )
            
            if not uid:
                raise UserError(_('Authentication failed with integration server. Check username and API key.'))
                
            _logger.info(f"Authenticated successfully with UID: {uid}")
            
            models_proxy = xmlrpc.client.ServerProxy(object_endpoint)
            return config['url'], config['db'], uid, config['api_key'], models_proxy
            
        except Exception as e:
            _logger.error(f"RPC connection failed: {str(e)}")
            raise UserError(_('Failed to connect to integration server: %s') % str(e))
    
    def _rpc_call(self, method, model_name='vnfield.contractor', args=None, kwargs=None):
        """Execute RPC call to integration server"""
        try:
            server_url, db, uid, api_key, models = self._get_rpc_connection()
            
            # Prepare arguments for execute_kw call
            # Format: models.execute_kw(db, uid, password, model, method, args, kwargs)
            
            # Default args if not provided
            if args is None:
                if method == 'search':
                    args = [[]]  # Empty domain for search
                else:
                    args = []
            
            # Default kwargs if not provided  
            if kwargs is None:
                kwargs = {}
            
            # Execute RPC call with proper format
            result = models.execute_kw(db, uid, api_key, model_name, method, args, kwargs)
            _logger.info(f"RPC call {method} on {model_name} successful")
            return result
            
        except Exception as e:
            _logger.error(f"RPC call failed: {str(e)}")
            raise UserError(_('RPC call failed: %s') % str(e))
    
    # ═══════════════════════════════════════════
    # 🚀 MAIN ACTION METHODS
    # ═══════════════════════════════════════════
    
    def action_create_profile(self):
        """Create capacity profile on remote server"""
        try:
            # Validate required fields
            if not self.title:
                raise ValidationError(_('Title is required.'))
            if not self.work_category:
                raise ValidationError(_('Work category is required.'))
            if not self.remote_contractor_id:
                raise ValidationError(_('Contractor selection is required.'))
            
            # Prepare values for remote server
            remote_vals = {
                'title': self.title,
                'description': self.description or '',
                'work_category': self.work_category,
                'experience_years': self.experience_years,
                'team_size': self.team_size,
                'current_workload': self.current_workload,
                'budget_capacity_min': self.budget_capacity_min,
                'budget_capacity_max': self.budget_capacity_max,
                'currency_id': self.currency_id.id if self.currency_id else False,
                'available_from': self.available_from,
                'max_project_duration': self.max_project_duration,
                'state': 'waiting_match',  # Force correct state
                'contractor_id': int(self.remote_contractor_id),
            }
            
            _logger.info(f"🔄 Creating remote capacity profile with vals: {remote_vals}")
            
            # Create record on remote server
            remote_id = self._rpc_call(
                'create',
                'vnfield.market.capacity.profile',
                [remote_vals]
            )
            
            if remote_id:
                _logger.info(f"✅ Remote capacity profile created successfully with ID: {remote_id}")
                
                # Trigger auto matching trên local system nếu có local capacity profiles
                self._trigger_local_auto_matching()
                
                # Show success message
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Remote capacity profile created successfully! Auto matching triggered.'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(_('Failed to create remote capacity profile. No ID returned.'))
                
        except Exception as e:
            _logger.error(f"❌ Failed to create remote capacity profile: {str(e)}")
            raise UserError(_('Failed to create remote capacity profile: %s') % str(e))
    
    def action_cancel(self):
        """Cancel wizard"""
        return {'type': 'ir.actions.act_window_close'}

    def _trigger_local_auto_matching(self):
        """🎯 Trigger auto matching cho local requirements với remote capacity profile mới"""
        try:
            # Tìm local requirements đang chờ match với cùng work_category
            domain = [
                ('state', '=', 'waiting_match'),
                ('work_category', '=', self.work_category)
            ]
            
            # Lọc theo kinh nghiệm nếu có
            if self.experience_years:
                domain.append(('required_experience_years', '<=', self.experience_years))
            
            # Tìm requirement được tạo sớm nhất
            requirement = self.env['vnfield.market.requirement'].search(domain, order='create_date asc', limit=1)
            
            if requirement:
                # Cập nhật trạng thái requirement thành matched
                requirement.state = 'matched'
                
                # Gửi pubsub messages cho match
                self._send_cross_match_messages(requirement)
                
                _logger.info(f"✅ Auto matched requirement {requirement.id} with remote capacity profile")
                
        except Exception as e:
            _logger.error(f"❌ Error in auto matching: {str(e)}")

    def _send_cross_match_messages(self, requirement):
        """📨 Gửi pubsub messages khi có cross matching (local requirement với remote capacity profile)"""
        try:
            config_param = self.env['ir.config_parameter'].sudo()
            topic = config_param.get_param('vnfield.kafka.topic', 'vnfield')
            
            # Message cho requirement match (local)
            requirement_message = {
                'action': 'match_requirement',
                'contractor_id': requirement.contractor_id.id,
                'contractor_external_id': requirement.contractor_id.external_id if requirement.contractor_id.external_id else None,
                'requirement_data': {
                    'id': requirement.id,
                    'title': requirement.title,
                    'work_category': requirement.work_category,
                    'matched_remote_capacity_profile': True
                },
                'extra': {
                    'timestamp': fields.Datetime.now().isoformat(),
                    'match_type': 'requirement_to_remote_profile'
                }
            }
            
            # Message cho capacity profile match (remote contractor)
            capacity_message = {
                'action': 'match_capacity_profile',
                'contractor_id': int(self.remote_contractor_id),
                'contractor_external_id': self.remote_contractor_id,  # This is external ID
                'capacity_profile_data': {
                    'title': self.title,
                    'work_category': self.work_category,
                    'matched_local_requirement_id': requirement.id
                },
                'extra': {
                    'timestamp': fields.Datetime.now().isoformat(),
                    'match_type': 'remote_profile_to_requirement'
                }
            }
            
            # Gửi messages
            pubsub_service = self.env['vnfield.pubsub.service'].create({})
            pubsub_service.produce_message(topic, requirement_message)
            pubsub_service.produce_message(topic, capacity_message)
            
        except Exception as e:
            _logger.error(f"Error sending cross match messages: {e}")
    
    # ═══════════════════════════════════════════
    # 📝 VALIDATION METHODS
    # ═══════════════════════════════════════════
    
    @api.onchange('available_from', 'max_project_duration')
    def _onchange_availability(self):
        """Update calculated fields when availability changes"""
        # Could add calculated end date or other logic here
        pass
    
    @api.constrains('budget_capacity_min', 'budget_capacity_max')
    def _check_budget_range(self):
        """Validate budget range"""
        for record in self:
            if record.budget_capacity_min and record.budget_capacity_max:
                if record.budget_capacity_min > record.budget_capacity_max:
                    raise ValidationError(_('Budget minimum cannot be greater than budget maximum.'))
    
    @api.constrains('experience_years')
    def _check_experience_years(self):
        """Validate experience years"""
        for record in self:
            if record.experience_years < 0:
                raise ValidationError(_('Experience years cannot be negative.'))
    
    @api.constrains('team_size')
    def _check_team_size(self):
        """Validate team size"""
        for record in self:
            if record.team_size < 1:
                raise ValidationError(_('Team size must be at least 1.'))