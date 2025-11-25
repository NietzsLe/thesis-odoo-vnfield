# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
import xmlrpc.client

_logger = logging.getLogger(__name__)

class CreateRemoteRequirementWizard(models.TransientModel):
    """
    🧙‍♂️ WIZARD TO CREATE NEW REMOTE REQUIREMENT
    
    Popup wizard để tạo mới remote requirement qua RPC.
    Không dùng nút "New" mặc định mà dùng custom wizard.
    """
    _name = 'vnfield.market.create.remote.requirement.wizard'
    _description = 'Create Remote Requirement Wizard'
    
    # ═══════════════════════════════════════════
    # 🏗️ WIZARD FIELDS
    # ═══════════════════════════════════════════
    
    title = fields.Char(string='Title', required=True, help="Requirement title")
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
    
    required_experience_years = fields.Integer(string='Required Experience Years', default=0)
    required_team_size = fields.Integer(string='Required Team Size', default=1)
    
    # Budget
    budget_min = fields.Monetary(string='Budget Min', currency_field='currency_id')
    budget_max = fields.Monetary(string='Budget Max', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    # Timeline
    project_start_date = fields.Date(string='Project Start Date')
    project_end_date = fields.Date(string='Project End Date')
    project_duration = fields.Integer(string='Project Duration (months)', default=1)
    
    # Location
    location = fields.Char(string='Project Location')
    
    # Task ID field
    task_id = fields.Integer(string='Task ID', help="Optional task ID reference")
    
    # Status - remove field completely, will be set in action
    # state = fields.Selection([
    #     ('waiting_match', 'Waiting Match'),
    #     ('matched', 'Matched'),
    #     ('inactive', 'Inactive')
    # ], string='State', default='waiting_match', required=True)
    
    # Remote contractor selection field (primary and only contractor field)
    remote_contractor_id = fields.Selection(
        selection='_get_remote_contractors_selection',
        string='Remote Contractor',
        help="Select from available remote contractors"
    )
    
    # ═══════════════════════════════════════════
    # � REMOTE CONTRACTOR SELECTION METHODS
    # ═══════════════════════════════════════════
    
    @api.model
    def default_get(self, fields_list):
        """Override default_get to handle task_id from context and provide default values"""
        defaults = super().default_get(fields_list)
        
        # Load data from task_id if provided in context
        task_id = self.env.context.get('default_task_id')
        if task_id:
            task = self.env['vnfield.task'].browse(task_id)
            if task.exists():
                # Set task_id field
                defaults['task_id'] = task.id
                # Set title from task
                defaults['title'] = f"Remote requirement for: {task.name}"
                # Set description from task
                if task.description:
                    defaults['description'] = f"<p>Task description: {task.description}</p>"
                # Set dates if available from project
                if task.project_id:
                    if task.project_id.start_date:
                        defaults['project_start_date'] = task.project_id.start_date
                    if task.project_id.end_date:
                        defaults['project_end_date'] = task.project_id.end_date
                    if task.project_id.budget:
                        defaults['budget_max'] = task.project_id.budget
        
        # Set default currency to VND if available
        if 'currency_id' in fields_list:
            vnd_currency = self.env['res.currency'].search([('name', '=', 'VND')], limit=1)
            if vnd_currency:
                defaults['currency_id'] = vnd_currency.id
            else:
                defaults['currency_id'] = self.env.company.currency_id.id
                
        return defaults

    @api.model
    def _get_remote_contractors_selection(self):
        """Get list of remote contractors for selection field"""
        try:
            # Check if we have integration config first
            config_param = self.env['ir.config_parameter'].sudo()
            url = config_param.get_param('vnfield.integration_server_url', '')
            
            if not url:
                _logger.warning("Integration server URL not configured")
                return [('', 'Integration server not configured')]
            
            # Use static method to get RPC connection without creating record
            url, db, uid, api_key, models = self._get_static_rpc_connection()
            
            # Get remote contractor IDs
            remote_ids = models.execute_kw(db, uid, api_key, 'vnfield.contractor', 'search', [[]])
            
            if not remote_ids:
                return [('', 'No contractors available')]
            
            # Read contractor names
            contractors = models.execute_kw(db, uid, api_key, 'vnfield.contractor', 'read', [remote_ids], {'fields': ['name']})
            
            # Build selection list
            selection = []
            for contractor in contractors:
                selection.append((str(contractor['id']), contractor['name']))
            
            return selection
            
        except Exception as e:
            _logger.error(f"Error getting remote contractors: {str(e)}")
            return [('', f'Error loading contractors: {str(e)}')]

    def _get_static_rpc_connection(self):
        """Static method to get RPC connection without record context"""
        config_param = self.env['ir.config_parameter'].sudo()
        config = {
            'url': config_param.get_param('vnfield.integration_server_url', ''),
            'db': config_param.get_param('vnfield.integration_database', ''),
            'username': config_param.get_param('vnfield.integration_username', ''),
            'api_key': config_param.get_param('vnfield.integration_api_key', ''),
        }
        
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
    
    def _rpc_call(self, method, model_name='vnfield.market.requirement', args=None, kwargs=None):
        """Execute RPC call to integration server"""
        try:
            url, db, uid, api_key, models = self._get_rpc_connection()
            
            if args is None:
                args = []
            if kwargs is None:
                kwargs = {}
                
            return models.execute_kw(db, uid, api_key, model_name, method, args, kwargs)
            
        except Exception as e:
            _logger.error(f"RPC call failed - method: {method}, model: {model_name}, error: {str(e)}")
            raise UserError(_('RPC call failed: %s') % str(e))
    
    # ═══════════════════════════════════════════
    # 🎬 WIZARD ACTIONS
    # ═══════════════════════════════════════════
    
    @api.model
    def create(self, vals):
        """Override create to ensure correct state value"""
        # No need to set state since field doesn't exist
        return super().create(vals)
    
    def action_create_requirement(self):
        """Create new requirement on remote server"""
        self.ensure_one()
        
        try:
            _logger.info(f"🆕 WIZARD CREATE called for: {self.title}")
            
            # Validate required fields
            if not self.remote_contractor_id:
                raise ValidationError(_('Remote contractor selection is required.'))
            
            # Prepare values for remote server
            remote_vals = {
                'title': self.title,
                'description': self.description or '',
                'work_category': self.work_category,
                'required_experience_years': self.required_experience_years,
                'team_size_min': self.required_team_size,
                'team_size_max': self.required_team_size,
                'budget_min': self.budget_min,
                'budget_max': self.budget_max,
                'currency_id': self.currency_id.id if self.currency_id else False,
                'start_date': self.project_start_date,
                'end_date': self.project_end_date,
                'duration_months': self.project_duration,
                'location': self.location or '',
                'task_id': self.task_id if self.task_id else None,  # Add task_id to remote vals
                'state': 'waiting_match',  # Force correct state
            }
            
            # Add remote contractor ID
            if self.remote_contractor_id:
                remote_vals['contractor_id'] = int(self.remote_contractor_id)
                _logger.info(f"Using remote contractor ID: {self.remote_contractor_id}")
            else:
                raise ValidationError(_('Remote contractor selection is required.'))
            
            _logger.info(f"🔄 Creating remote requirement with vals: {remote_vals}")
            
            # Create record on remote server
            remote_id = self._rpc_call(
                'create',
                'vnfield.market.requirement',
                [remote_vals]
            )
            
            if remote_id:
                _logger.info(f"✅ Created remote requirement with ID: {remote_id}")
                
                # Trigger auto matching trên local system nếu có local capacity profiles
                self._trigger_local_auto_matching()
                
                # Show success notification
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': f'Remote requirement "{self.title}" created successfully with ID: {remote_id}. Auto matching triggered.',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(_('Failed to create record on remote server'))
                
        except Exception as e:
            _logger.error(f"Create failed: {str(e)}")
            raise UserError(_('Failed to create remote requirement: %s') % str(e))
    
    def action_cancel(self):
        """Cancel wizard"""
        return {'type': 'ir.actions.act_window_close'}

    def _trigger_local_auto_matching(self):
        """🎯 Trigger auto matching cho local capacity profiles với remote requirement mới"""
        try:
            # Tìm local capacity profiles đang chờ match với cùng work_category
            domain = [
                ('state', '=', 'waiting_match'),
                ('work_category', '=', self.work_category)
            ]
            
            # Lọc theo kinh nghiệm nếu có
            if self.required_experience_years:
                domain.append(('experience_years', '>=', self.required_experience_years))
            
            # Tìm capacity profile được tạo sớm nhất
            capacity_profile = self.env['vnfield.market.capacity.profile'].search(domain, order='create_date asc', limit=1)
            
            if capacity_profile:
                # Cập nhật trạng thái capacity profile thành matched
                capacity_profile.state = 'matched'
                
                # Gửi pubsub messages cho match
                self._send_cross_match_messages(capacity_profile)
                
                _logger.info(f"✅ Auto matched capacity profile {capacity_profile.id} with remote requirement")
                
        except Exception as e:
            _logger.error(f"❌ Error in auto matching: {str(e)}")

    def _send_cross_match_messages(self, capacity_profile):
        """📨 Gửi pubsub messages khi có cross matching (local capacity profile với remote requirement)"""
        try:
            config_param = self.env['ir.config_parameter'].sudo()
            topic = config_param.get_param('vnfield.kafka.topic', 'vnfield')
            
            # Message cho capacity profile match (local)
            capacity_message = {
                'action': 'match_capacity_profile',
                'contractor_id': capacity_profile.contractor_id.id,
                'contractor_external_id': capacity_profile.contractor_id.external_id if capacity_profile.contractor_id.external_id else None,
                'capacity_profile_data': {
                    'id': capacity_profile.id,
                    'title': capacity_profile.title,
                    'work_category': capacity_profile.work_category,
                    'matched_remote_requirement': True
                },
                'extra': {
                    'timestamp': fields.Datetime.now().isoformat(),
                    'match_type': 'profile_to_remote_requirement'
                }
            }
            
            # Message cho requirement match (remote contractor)
            requirement_contractor_id = None
            if self.remote_contractor_id:
                requirement_contractor_id = int(self.remote_contractor_id)
            elif self.contractor_id:
                requirement_contractor_id = self.contractor_id.id
                
            requirement_message = {
                'action': 'match_requirement',
                'contractor_id': requirement_contractor_id,
                'contractor_external_id': self.remote_contractor_id if self.remote_contractor_id else None,
                'requirement_data': {
                    'title': self.title,
                    'work_category': self.work_category,
                    'matched_local_capacity_profile_id': capacity_profile.id
                },
                'extra': {
                    'timestamp': fields.Datetime.now().isoformat(),
                    'match_type': 'remote_requirement_to_profile'
                }
            }
            
            # Gửi messages
            pubsub_service = self.env['vnfield.pubsub.service'].create({})
            pubsub_service.produce_message(topic, capacity_message)
            pubsub_service.produce_message(topic, requirement_message)
            
        except Exception as e:
            _logger.error(f"Error sending cross match messages: {e}")
    
    # ═══════════════════════════════════════════
    # 🔄 ONCHANGE METHODS
    # ═══════════════════════════════════════════
    
    @api.onchange('project_start_date', 'project_end_date')
    def _onchange_project_dates(self):
        """Auto-calculate duration when dates change"""
        if self.project_start_date and self.project_end_date:
            if self.project_end_date > self.project_start_date:
                delta = self.project_end_date - self.project_start_date
                self.project_duration = max(1, round(delta.days / 30))  # Convert to months
    
    @api.onchange('project_duration')
    def _onchange_project_duration(self):
        """Auto-calculate end date when duration changes"""
        if self.project_start_date and self.project_duration:
            from datetime import timedelta
            self.project_end_date = self.project_start_date + timedelta(days=self.project_duration * 30)
    
    @api.constrains('budget_min', 'budget_max')
    def _check_budget_range(self):
        """Validate budget range"""
        for record in self:
            if record.budget_min and record.budget_max:
                if record.budget_min > record.budget_max:
                    raise ValidationError(_('Budget minimum cannot be greater than budget maximum.'))
    
    @api.constrains('remote_contractor_id')
    def _check_contractor_required(self):
        """Validate contractor is selected"""
        for record in self:
            if not record.remote_contractor_id and not record.contractor_id:
                raise ValidationError(_('Contractor selection is required.'))
    
    @api.constrains('project_start_date', 'project_end_date')
    def _check_date_range(self):
        """Validate date range"""
        for record in self:
            if record.project_start_date and record.project_end_date:
                if record.project_start_date > record.project_end_date:
                    raise ValidationError(_('Project start date cannot be after end date.'))