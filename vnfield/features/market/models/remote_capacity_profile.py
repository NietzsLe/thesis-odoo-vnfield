# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
import xmlrpc.client

_logger = logging.getLogger(__name__)

class RemoteCapacityProfile(models.AbstractModel):
    """
    🔗 PURE RPC REMOTE CAPACITY PROFILE MODEL
    
    Pure RPC-based model for accessing remote capacity profiles.
    KHÔNG lưu trữ data local, chỉ pure proxy đến remote server.
    
    Features:
    - Pure RPC-based, no local storage
    - Direct proxy to integration server capacity profiles
    - Override all view-serving methods
    - Real-time data from remote server
    """
    _name = 'vnfield.market.remote.capacity.profile'
    _description = 'Remote Capacity Profile (Pure RPC)'
    _auto = False  # No database table
    _rec_name = 'display_name'
    
    # ═══════════════════════════════════════════
    # 🏗️ FIELD DEFINITIONS (All Virtual/Computed)
    # ═══════════════════════════════════════════
    
    # All fields are computed from remote data, no local storage
    id = fields.Integer(string='ID')
    title = fields.Char(string='Title')
    display_name = fields.Char(string='Display Name')
    description = fields.Html(string='Description')
    subcontractor_id = fields.Integer(string='Subcontractor ID')
    subcontractor_name = fields.Char(string='Subcontractor Name')
    
    # Work details
    work_category = fields.Selection([
        ('construction', 'Thi công xây dựng'),
        ('design', 'Thiết kế'),
        ('consulting', 'Tư vấn'),
        ('supervision', 'Giám sát'),
        ('survey', 'Khảo sát'),
        ('testing', 'Thí nghiệm'),
        ('other', 'Khác')
    ], string='Work Category')
    
    experience_years = fields.Integer(string='Experience Years')
    team_size = fields.Integer(string='Team Size')
    current_workload = fields.Selection([
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao'),
        ('full', 'Đầy')
    ], string='Current Workload')
    
    # Budget capacity
    budget_capacity_min = fields.Monetary(string='Budget Capacity Min')
    budget_capacity_max = fields.Monetary(string='Budget Capacity Max')
    currency_id = fields.Many2one('res.currency', string='Currency')
    
    # Status
    state = fields.Selection([
        ('waiting_match', 'Waiting Match'),
        ('matched', 'Matched'),
        ('inactive', 'Inactive')
    ], string='State')
    
    available_from = fields.Date(string='Available From')
    max_project_duration = fields.Integer(string='Max Project Duration (months)')
    
    # Computed fields
    match_count = fields.Integer(string='Match Count', compute='_compute_match_count')
    
    # ═══════════════════════════════════════════
    # 🔄 RPC COMMUNICATION METHODS
    # ═══════════════════════════════════════════
    
    def _get_integration_config(self):
        """Lấy cấu hình integration server từ system parameters theo format chuẩn"""
        config_param = self.env['ir.config_parameter'].sudo()
        return {
            'url': config_param.get_param('vnfield.integration_server_url', ''),
            'db': config_param.get_param('vnfield.integration_database', ''),
            'username': config_param.get_param('vnfield.integration_username', ''),
            'api_key': config_param.get_param('vnfield.integration_api_key', ''),
        }
    
    def _get_rpc_connection(self):
        """
        Tạo RPC connection tới integration server theo pattern chuẩn từ contractor_representative_wizard
        Returns: (url, db, uid, api_key, models) tuple or raises exception
        """
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
            # Setup XML-RPC endpoints following Odoo documentation
            server_url = config['url'].rstrip('/')
            common_endpoint = f"{server_url}/xmlrpc/2/common"
            object_endpoint = f"{server_url}/xmlrpc/2/object"
            
            # Step 1: Test connection and get server info
            common = xmlrpc.client.ServerProxy(common_endpoint)
            server_info = common.version()
            _logger.info(f"Connected to Odoo server version: {server_info.get('server_version', 'Unknown')}")
            
            # Step 2: Authenticate using username + API key (replaces password)
            uid = common.authenticate(
                config['db'],
                config['username'],
                config['api_key'],  # API Key used instead of password
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
    
    def _rpc_call(self, method, model_name='vnfield.market.capacity.profile', args=None, kwargs=None):
        """
        Execute RPC call to integration server theo chuẩn Odoo 17 với API key authentication
        Args:
            method: string - RPC method name (search, read, create, write, unlink)
            model_name: string - target model name on integration server  
            args: list - positional arguments for the method
            kwargs: dict - keyword arguments for the method
        Returns: RPC result
        """
        try:
            url, db, uid, api_key, models = self._get_rpc_connection()
            
            # Prepare arguments theo format execute_kw chuẩn Odoo
            if args is None:
                args = []
            if kwargs is None:
                kwargs = {}
                
            # Call execute_kw với format: db, uid, api_key, model, method, args, kwargs
            return models.execute_kw(db, uid, api_key, model_name, method, args, kwargs)
            
        except Exception as e:
            _logger.error(f"RPC call failed - method: {method}, model: {model_name}, args: {args}, kwargs: {kwargs}, error: {str(e)}")
            raise UserError(_('RPC call failed: %s') % str(e))
    
    # ═══════════════════════════════════════════
    # 🔍 REMOTE DATA ACCESS METHODS
    # ═══════════════════════════════════════════
    
    def _get_remote_capacity_profiles(self, domain=None, offset=0, limit=None, order=None):
        """Get capacity profiles from remote server"""
        try:
            # Convert domain to remote format
            remote_domain = self._convert_domain_to_remote(domain or [])
            remote_order = self._convert_order_to_remote(order)
            
            # Search remote records
            remote_ids = self._rpc_call(
                'search', 
                'vnfield.market.capacity.profile',
                [remote_domain],
                {'offset': offset, 'limit': limit, 'order': remote_order}
            )
            
            if remote_ids:
                # Read remote records
                remote_records = self._rpc_call(
                    'read',
                    'vnfield.market.capacity.profile',
                    [remote_ids],
                    {'fields': [
                        'title', 'description', 'contractor_id', 'work_category',
                        'experience_years', 'team_size', 'current_workload',
                        'budget_capacity_min', 'budget_capacity_max', 'currency_id',
                        'state', 'available_from', 'max_project_duration'
                    ]}
                )
                
                # Convert to local format
                return self._convert_remote_records_to_local(remote_records)
            
            return []
            
        except Exception as e:
            _logger.error(f"Failed to get remote capacity profiles: {str(e)}")
            return []
    
    def _get_remote_capacity_profile_by_id(self, remote_id):
        """Get single capacity profile from remote server"""
        try:
            remote_records = self._rpc_call(
                'read', 
                'vnfield.market.capacity.profile', 
                [[remote_id]], 
                {'fields': [
                    'title', 'description', 'contractor_id', 'work_category',
                    'experience_years', 'team_size', 'current_workload',
                    'budget_capacity_min', 'budget_capacity_max', 'currency_id',
                    'state', 'available_from', 'max_project_duration'
                ]}
            )
            if remote_records:
                converted = self._convert_remote_records_to_local(remote_records)
                return converted[0] if converted else None
            return None
        except Exception as e:
            _logger.error(f"Failed to get remote capacity profile {remote_id}: {str(e)}")
            return None
    
    # ═══════════════════════════════════════════
    # 🔄 FIELD MAPPING UTILITIES
    # ═══════════════════════════════════════════
    
    def _convert_domain_to_remote(self, domain):
        """Convert local field names in domain to remote field names"""
        if not domain:
            return []
        
        # Field mapping if needed (local_field: remote_field)
        field_mapping = {
            'contractor_name': 'contractor_id.name',
        }
        
        converted_domain = []
        for item in domain:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                field, operator, value = item[0], item[1], item[2]
                remote_field = field_mapping.get(field, field)
                converted_domain.append([remote_field, operator, value])
            else:
                converted_domain.append(item)
        
        return converted_domain
    
    def _convert_order_to_remote(self, order):
        """Convert local field names in order to remote field names"""
        if not order:
            return 'title'
        
        field_mapping = {
            'contractor_name': 'contractor_id',
        }
        
        for local_field, remote_field in field_mapping.items():
            order = order.replace(local_field, remote_field)
        
        return order
    
    def _convert_remote_records_to_local(self, remote_records):
        """Convert remote record format to local format"""
        local_records = []
        
        for remote_record in remote_records:
            # Use negative ID to distinguish from local records
            virtual_id = -(remote_record['id'] + 1000000)  # Negative ID with offset
            
            local_record = {
                'id': virtual_id,  # Use negative integer instead of string
                'title': remote_record.get('title', ''),
                'display_name': remote_record.get('title', ''),  # Assign display_name from title
                'description': remote_record.get('description', ''),
                'subcontractor_id': remote_record.get('contractor_id', [False, ''])[0] if isinstance(remote_record.get('contractor_id'), list) else remote_record.get('contractor_id'),
                'subcontractor_name': remote_record.get('contractor_id', [False, ''])[1] if isinstance(remote_record.get('contractor_id'), list) else '',
                'work_category': remote_record.get('work_category', ''),
                'experience_years': remote_record.get('experience_years', 0),
                'team_size': remote_record.get('team_size', 0),
                'current_workload': remote_record.get('current_workload', ''),
                'budget_capacity_min': remote_record.get('budget_capacity_min', 0.0),
                'budget_capacity_max': remote_record.get('budget_capacity_max', 0.0),
                'currency_id': remote_record.get('currency_id', [False, ''])[0] if isinstance(remote_record.get('currency_id'), list) else remote_record.get('currency_id'),
                'state': remote_record.get('state', ''),
                'available_from': remote_record.get('available_from', False),
                'max_project_duration': remote_record.get('max_project_duration', 0),
                'match_count': 0,  # Will be computed
                '_remote_id': remote_record['id']  # Store original remote ID for reference
            }
            local_records.append(local_record)
        
        return local_records
    
    # ═══════════════════════════════════════════
    # 🎯 COMPUTED FIELDS
    # ═══════════════════════════════════════════
    
    def _compute_match_count(self):
        """Compute match count (placeholder)"""
        for record in self:
            record.match_count = 0
    
    # ═══════════════════════════════════════════
    # 🔍 OVERRIDE ODOO METHODS FOR RPC
    # ═══════════════════════════════════════════
    
    @api.model
    def web_search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, specification=None, **kwargs):
        """Override web_search_read for pure RPC implementation"""
        try:
            records = self._get_remote_capacity_profiles(domain, offset, limit, order)
            return {
                'records': records,
                'length': len(records)
            }
        except Exception as e:
            _logger.error(f"web_search_read failed: {str(e)}")
            return {'records': [], 'length': 0}
    
    @api.model
    def web_read(self, ids, fields=None, specification=None):
        """Override web_read for form view support"""
        try:
            result = []
            for record_id in ids:
                if isinstance(record_id, int) and record_id < 0:
                    remote_id = -(record_id + 1000000)  # Convert back to original remote ID
                    remote_data = self._get_remote_capacity_profile_by_id(remote_id)
                    if remote_data:
                        # Filter fields if specified
                        if fields:
                            filtered_data = {k: v for k, v in remote_data.items() if k in fields + ['id']}
                            filtered_data['id'] = record_id  # Keep virtual ID
                            result.append(filtered_data)
                        else:
                            remote_data['id'] = record_id  # Keep virtual ID
                            result.append(remote_data)
            return result
        except Exception as e:
            _logger.error(f"web_read failed: {str(e)}")
            return []
    
    @api.model
    def search(self, domain=None, offset=0, limit=None, order=None, count=False):
        """Override search for pure RPC implementation"""
        try:
            if count:
                # Get count from remote server
                remote_domain = self._convert_domain_to_remote(domain or [])
                remote_count = self._rpc_call('search_count', 'vnfield.market.capacity.profile', [remote_domain])
                return remote_count
            else:
                # Get records from remote server
                records = self._get_remote_capacity_profiles(domain, offset, limit, order)
                # Create recordset with virtual IDs
                virtual_ids = [rec['id'] for rec in records]
                return self.browse(virtual_ids)
        except Exception as e:
            _logger.error(f"search failed: {str(e)}")
            return self.browse([]) if not count else 0
    
    def read(self, fields=None, load='_classic_read'):
        """Override read for pure RPC implementation"""
        try:
            result = []
            for record in self:
                # Extract remote ID from virtual ID
                if isinstance(record.id, str) and record.id.startswith('remote_'):
                    remote_id = int(record.id.replace('remote_', ''))
                    remote_data = self._get_remote_capacity_profile_by_id(remote_id)
                    if remote_data:
                        # Filter fields if specified
                        if fields:
                            filtered_data = {k: v for k, v in remote_data.items() if k in fields}
                            result.append(filtered_data)
                        else:
                            result.append(remote_data)
            return result
        except Exception as e:
            _logger.error(f"read failed: {str(e)}")
            return []
    
    # ═══════════════════════════════════════════
    # 🎯 ACTION METHODS
    # ═══════════════════════════════════════════
    
    def action_open_form(self):
        """Open form view for this capacity profile"""
        return {
            'name': 'Remote Capacity Profile',
            'type': 'ir.actions.act_window',
            'res_model': 'vnfield.market.remote.capacity.profile',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }
    
    def action_open_create_wizard(self):
        """Open wizard to create new remote capacity profile"""
        return {
            'name': 'Create New Remote Capacity Profile',
            'type': 'ir.actions.act_window',
            'res_model': 'vnfield.market.create.remote.capacity.profile.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_state': 'draft',
            }
        }