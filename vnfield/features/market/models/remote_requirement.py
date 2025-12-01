# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
import xmlrpc.client

_logger = logging.getLogger(__name__)

class RemoteRequirement(models.AbstractModel):
    """
    🔗 PURE RPC REMOTE REQUIREMENT MODEL
    
    Pure RPC-based model for accessing remote requirements.
    KHÔNG lưu trữ data local, chỉ pure proxy đến remote server.
    
    🆔 DIRECT REMOTE ID SYSTEM:
    - ID hiển thị trong views = ID từ remote server (1, 2, 3, ...)
    - Không cần conversion logic vì không có local records
    - Đơn giản, trực tiếp, dễ hiểu và maintain
    
    Features:
    - Pure RPC-based, no local storage
    - Direct proxy to integration server requirements
    - Override all view-serving methods
    - Real-time data from remote server
    - Direct ID mapping with remote server
    """
    _name = 'vnfield.market.remote.requirement'
    _description = 'Remote Requirement (Pure RPC)'
    _auto = False  # No database table
    _rec_name = 'display_name'
    
    # ═══════════════════════════════════════════
    # 🏗️ FIELD DEFINITIONS (All Virtual/Computed)
    # ═══════════════════════════════════════════
    
    # All fields are computed from remote data, no local storage
    id = fields.Integer(string='ID')
    title = fields.Char(string='Title', required=True)
    description = fields.Html(string='Description')
    project_id = fields.Integer(string='Project ID')
    project_name = fields.Char(string='Project Name')
    
    # Subcontractor assignment
    subcontractor_id = fields.Integer(string='Assigned Subcontractor ID')
    subcontractor_name = fields.Char(string='Assigned Subcontractor Name')
    
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
    
    required_experience_years = fields.Integer(string='Required Experience Years')
    required_team_size = fields.Integer(string='Required Team Size')
    
    # Budget and timeline
    budget_min = fields.Monetary(string='Budget Min')
    budget_max = fields.Monetary(string='Budget Max')
    currency_id = fields.Many2one('res.currency', string='Currency')
    
    # Timeline
    project_start_date = fields.Date(string='Project Start Date')
    project_end_date = fields.Date(string='Project End Date')
    project_duration = fields.Integer(string='Project Duration (months)')
    
    # Status
    state = fields.Selection([
        ('waiting_match', 'Waiting Match'),
        ('matched', 'Matched'),
        ('inactive', 'Inactive')
    ], string='State', default='waiting_match')
    
    # Priority
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], string='Priority')
    
    # Location
    location = fields.Char(string='Project Location')
    
    # Computed fields
    match_count = fields.Integer(string='Match Count', compute='_compute_match_count')
    display_name = fields.Char(string='Display Name')
    
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
    
    def _rpc_call(self, method, model_name='vnfield.market.requirement', args=None, kwargs=None):
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
    
    def _get_remote_requirements(self, domain=None, offset=0, limit=None, order=None):
        """Get requirements from remote server"""
        try:
            # Convert domain to remote format
            remote_domain = self._convert_domain_to_remote(domain or [])
            remote_order = self._convert_order_to_remote(order)
            
            # Search remote records
            remote_ids = self._rpc_call(
                'search', 
                'vnfield.market.requirement',
                [remote_domain],
                {'offset': offset, 'limit': limit, 'order': remote_order}
            )
            
            if remote_ids:
                # Read remote records
                remote_records = self._rpc_call(
                    'read',
                    'vnfield.market.requirement',
                    [remote_ids],
                    {'fields': [
                        'title', 'description', 'contractor_id', 'work_category',
                        'required_experience_years', 'team_size_min', 'team_size_max',
                        'budget_min', 'budget_max', 'currency_id',
                        'start_date', 'end_date', 'duration_months',
                        'state', 'location'
                    ]}
                )
                
                # Convert to local format
                return self._convert_remote_records_to_local(remote_records)
            
            return []
            
        except Exception as e:
            _logger.error(f"Failed to get remote requirements: {str(e)}")
            return []
    
    def _get_remote_requirement_by_id(self, remote_id):
        """Get single requirement from remote server"""
        try:
            remote_records = self._rpc_call(
                'read', 
                'vnfield.market.requirement', 
                [[remote_id]], 
                {'fields': [
                    'title', 'description', 'contractor_id', 'work_category',
                    'required_experience_years', 'team_size_min', 'team_size_max',
                    'budget_min', 'budget_max', 'currency_id',
                    'start_date', 'end_date', 'duration_months',
                    'state', 'location'
                ]}
            )
            if remote_records:
                converted = self._convert_remote_records_to_local(remote_records)
                return converted[0] if converted else None
            return None
        except Exception as e:
            _logger.error(f"Failed to get remote requirement {remote_id}: {str(e)}")
            return None
    
    # ═══════════════════════════════════════════
    # 🔄 FIELD MAPPING UTILITIES
    # ═══════════════════════════════════════════
    
    def _convert_domain_to_remote(self, domain):
        """Convert local field names in domain to remote field names"""
        if not domain:
            return []
        
        # Field mapping (local_field: remote_field)
        field_mapping = {
            'project_name': 'contractor_id.name',
            'subcontractor_name': 'contractor_id.name',
            'project_start_date': 'start_date',
            'project_end_date': 'end_date',
            'project_duration': 'duration_months',
            'required_team_size': 'team_size_min',
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
            'project_name': 'contractor_id',
            'subcontractor_name': 'contractor_id',
            'project_start_date': 'start_date',
            'project_end_date': 'end_date',
            'project_duration': 'duration_months',
        }
        
        for local_field, remote_field in field_mapping.items():
            order = order.replace(local_field, remote_field)
        
        return order
    
    def _convert_remote_records_to_local(self, remote_records):
        """Convert remote record format to local format"""
        local_records = []
        
        for remote_record in remote_records:
            # Extract contractor info from remote record
            contractor_id = remote_record.get('contractor_id', [False, ''])[0] if isinstance(remote_record.get('contractor_id'), list) else remote_record.get('contractor_id')
            contractor_name = remote_record.get('contractor_id', [False, ''])[1] if isinstance(remote_record.get('contractor_id'), list) else ''
            
            # Use direct remote ID - no conversion needed since no local records exist
            remote_id = remote_record['id']
            _logger.info(f"🆔 USING DIRECT REMOTE ID: {remote_id} (same as remote server)")
            
            local_record = {
                'id': remote_id,  # Use direct remote ID
                'title': remote_record.get('title', ''),
                'display_name': remote_record.get('title', ''),  # Assign display_name directly from title
                'description': remote_record.get('description', ''),
                'project_id': contractor_id,  # Use contractor as project proxy
                'project_name': contractor_name,  # Use contractor name as project name proxy
                'subcontractor_id': contractor_id,  # Map contractor to subcontractor  
                'subcontractor_name': contractor_name,  # Map contractor name to subcontractor name
                'work_category': remote_record.get('work_category', ''),
                'required_experience_years': remote_record.get('required_experience_years', 0),
                'required_team_size': max(remote_record.get('team_size_min', 0), remote_record.get('team_size_max', 0)),
                'budget_min': remote_record.get('budget_min', 0.0),
                'budget_max': remote_record.get('budget_max', 0.0),
                'currency_id': remote_record.get('currency_id', [False, ''])[0] if isinstance(remote_record.get('currency_id'), list) else remote_record.get('currency_id'),
                'project_start_date': remote_record.get('start_date', False),
                'project_end_date': remote_record.get('end_date', False),
                'project_duration': remote_record.get('duration_months', 0),
                'state': remote_record.get('state', ''),
                'priority': 'medium',  # Default priority since local model doesn't have this
                'location': remote_record.get('location', ''),
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
            _logger.info(f"🔍 WEB_SEARCH_READ called | domain: {domain} | offset: {offset} | limit: {limit}")
            records = self._get_remote_requirements(domain, offset, limit, order)
            _logger.info(f"🔍 WEB_SEARCH_READ returning {len(records)} records with direct remote IDs: {[r.get('id') for r in records]}")
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
            _logger.info(f"🔍 WEB_READ called with direct remote ids: {ids}")
            result = []
            for record_id in ids:
                _logger.info(f"🆔 FETCHING DATA for direct remote_id: {record_id}")
                remote_data = self._get_remote_requirement_by_id(record_id)
                if remote_data:
                    # Filter fields if specified
                    if fields:
                        filtered_data = {k: v for k, v in remote_data.items() if k in fields + ['id']}
                        filtered_data['id'] = record_id  # Keep same remote ID
                        result.append(filtered_data)
                    else:
                        remote_data['id'] = record_id  # Keep same remote ID
                        result.append(remote_data)
            return result
        except Exception as e:
            _logger.error(f"web_read failed: {str(e)}")
            return []
    
    @api.model
    def search(self, domain=None, offset=0, limit=None, order=None, count=False):
        """Override search for pure RPC implementation"""
        try:
            _logger.info(f"🔍 SEARCH called | domain: {domain} | offset: {offset} | limit: {limit} | count: {count}")
            if count:
                # Get count from remote server
                remote_domain = self._convert_domain_to_remote(domain or [])
                remote_count = self._rpc_call('search_count', 'vnfield.market.requirement', [remote_domain])
                _logger.info(f"🔍 SEARCH returning count: {remote_count}")
                return remote_count
            else:
                # Get records from remote server
                records = self._get_remote_requirements(domain, offset, limit, order)
                # Create recordset with direct remote IDs
                remote_ids = [rec['id'] for rec in records]
                _logger.info(f"🔍 SEARCH returning direct remote IDs: {remote_ids}")
                return self.browse(remote_ids)
        except Exception as e:
            _logger.error(f"search failed: {str(e)}")
            return self.browse([]) if not count else 0
    
    def read(self, fields=None, load='_classic_read'):
        """Override read for pure RPC implementation"""
        try:
            # Access IDs safely without triggering field resolution
            record_ids = [r._ids[0] if r._ids else None for r in self]
            _logger.info(f"📖 READ called with records: {record_ids} | fields: {fields}")
            result = []
            for record in self:
                # Use direct remote ID since no conversion needed
                record_id = record._ids[0] if record._ids else None
                if record_id:
                    _logger.info(f"🆔 READING REMOTE DATA directly for remote_id: {record_id}")
                    remote_data = self._get_remote_requirement_by_id(record_id)
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
    
    @api.model
    def browse(self, ids=None):
        """Override browse to handle remote IDs"""
        if ids is None:
            ids = ()
        if isinstance(ids, (int, str)):
            ids = [ids]
        
        _logger.info(f"🔍 BROWSE called with remote IDs: {ids}")
        
        # For AbstractModel with remote data, just create recordset
        # The actual data will be fetched through our overridden methods
        return super().browse(ids)
    
    # def new(self, values=None, origin=None, ref=None):
    #     """Override new to handle new record creation safely - DISABLED"""
    #     # DISABLED: Creation is not allowed for remote requirements
    #     raise UserError(_('Creating new remote requirements is not allowed. View only mode.'))
    
    @api.model
    def default_get(self, fields_list):
        """Override default_get to populate form with remote data or provide defaults"""
        defaults = super().default_get(fields_list)
        
        # Check if context contains remote data
        if self.env.context.get('remote_data'):
            remote_data = self.env.context['remote_data']
            # Populate defaults with remote data
            for field in fields_list:
                if field in remote_data:
                    defaults[field] = remote_data[field]
        else:
            # No default values for new record creation since creation is disabled
            pass
        
        return defaults
    
    def exists(self):
        """Override exists to prevent database lookup for remote records"""
        try:
            # For new records (NewId), return self  
            # For existing records, check if they have valid IDs
            existing_records = self.browse([])
            for record in self:
                try:
                    record_id = getattr(record, 'id', None)
                    if record_id:
                        if isinstance(record_id, int) and record_id > 0:
                            # Valid remote ID, assume exists on remote server
                            existing_records += record
                        else:
                            # NewId or invalid ID, treat as new record (exists in form context)
                            existing_records += record
                except:
                    # Safe fallback for any ID access issues
                    existing_records += record
            
            _logger.info(f"🔍 EXISTS returning {len(existing_records)} records")
            return existing_records
        except Exception as e:
            _logger.error(f"EXISTS error: {str(e)}")
            # Safe fallback - return self to prevent blocking
            return self
    
    def _check_concurrency(self):
        """Override to prevent concurrency check on remote records"""
        try:
            _logger.info(f"🚫 _CHECK_CONCURRENCY skipped for remote records")
            # Skip concurrency check for remote records and new records
            pass
        except Exception as e:
            _logger.error(f"_CHECK_CONCURRENCY error: {str(e)}")
            # Safe fallback - no concurrency check
            pass
    
    def _update_cache(self, values, validate=True):
        """Override to prevent cache issues with NewId"""
        try:
            _logger.info(f"🔄 _UPDATE_CACHE called with values: {list(values.keys()) if values else None}")
            # For AbstractModel with remote records, handle caching carefully
            return super()._update_cache(values, validate)
        except Exception as e:
            _logger.error(f"_UPDATE_CACHE error: {str(e)}")
            # Safe fallback - skip cache update if needed
            pass
    
    def _fetch_field(self, field_names):
        """Override _fetch_field to get data from remote server instead of database"""
        try:
            _logger.info(f"📡 _FETCH_FIELD called for fields: {field_names}")
            
            # For new records, don't fetch from remote - use cached/default values
            # For existing records with valid IDs, we could fetch from remote
            # But for AbstractModel, the framework handles this through our read() method
            
            _logger.info(f"📡 _FETCH_FIELD redirected to framework handling")
            
            # Return self to indicate success
            return self
        except Exception as e:
            _logger.error(f"_FETCH_FIELD error: {str(e)}")
            # Safe fallback
            return self
    
    @api.model
    def load_views(self, views, options=None):
        """Override load_views to handle form view loading for remote records"""
        _logger.info(f"🖥️ LOAD_VIEWS called with views: {views}")
        
        # Call parent method to get view definitions
        result = super().load_views(views, options)
        
        # If we have a context with active_id, pre-load remote data
        active_id = self.env.context.get('active_id')
        if active_id:
            _logger.info(f"🔍 Pre-loading remote data for active_id: {active_id}")
            remote_data = self._get_remote_requirement_by_id(active_id)
            if remote_data:
                # Store remote data in result for form view
                result['remote_data'] = remote_data
        
        return result
    
    def _read_from_database(self, field_names, inherited_field_names=None):
        """Override to prevent database read for remote records"""
        # Access IDs safely without triggering field resolution
        record_ids = [r._ids[0] if r._ids else None for r in self]
        _logger.info(f"🚫 _READ_FROM_DATABASE blocked for remote records: {record_ids}")
        
        # Instead of reading from database, get data from remote server
        result = []
        for record in self:
            record_id = record._ids[0] if record._ids else None
            if record_id:
                remote_data = self._get_remote_requirement_by_id(record_id)
                if remote_data:
                    # Filter only requested fields
                    filtered_data = {}
                    for field_name in field_names:
                        if field_name in remote_data:
                            filtered_data[field_name] = remote_data[field_name]
                        elif field_name == 'id':
                            filtered_data['id'] = record_id
                    result.append(filtered_data)
                else:
                    # Return empty dict for missing records
                    result.append({'id': record_id})
        
        return result
    
    # ═══════════════════════════════════════════
    # 🎬 ACTION METHODS
    # ═══════════════════════════════════════════
    
    # @api.model
    # def create(self, vals):
    #     """Override create to create record on remote server via RPC"""
    #     # DISABLED: Creation is not allowed for remote requirements
    #     raise UserError(_('Creating new remote requirements is not allowed. View only mode.'))
    
    @api.model
    def create(self, vals):
        """Disabled: Create operation not allowed for remote requirements"""
        raise UserError(_('Creating new remote requirements is not allowed. This model is for viewing remote data only.'))
    
    def _convert_local_vals_to_remote(self, vals):
        """Convert local field values to remote field format"""
        remote_vals = {}
        
        # Field mapping (local_field: remote_field)
        field_mapping = {
            'title': 'title',
            'description': 'description',
            'project_id': 'contractor_id',
            'project_name': 'contractor_id',  # Will need special handling
            'subcontractor_id': 'contractor_id',
            'subcontractor_name': 'contractor_id',  # Will need special handling
            'work_category': 'work_category',
            'required_experience_years': 'required_experience_years',
            'required_team_size': 'team_size_min',  # Map to team_size_min
            'budget_min': 'budget_min',
            'budget_max': 'budget_max',
            'currency_id': 'currency_id',
            'project_start_date': 'start_date',
            'project_end_date': 'end_date',
            'project_duration': 'duration_months',
            'state': 'state',
            'location': 'location',
        }
        
        for local_field, value in vals.items():
            if local_field == 'display_name':
                # Skip display_name as it's computed
                continue
            elif local_field in field_mapping:
                remote_field = field_mapping[local_field]
                if local_field == 'required_team_size':
                    # Map required_team_size to both team_size_min and team_size_max
                    remote_vals['team_size_min'] = value
                    remote_vals['team_size_max'] = value
                elif local_field in ['project_name', 'subcontractor_name']:
                    # Skip name fields, use ID fields instead
                    continue
                else:
                    remote_vals[remote_field] = value
            else:
                # Pass through unknown fields as-is
                remote_vals[local_field] = value
        
        return remote_vals
    
    @api.model
    def write(self, vals):
        """Override write to update records on remote server via RPC"""
        try:
            _logger.info(f"✏️ WRITE called with vals: {vals}")
            
            # Convert local field names to remote field names
            remote_vals = self._convert_local_vals_to_remote(vals)
            _logger.info(f"🔄 Converted vals for remote update: {remote_vals}")
            
            # Update all records in recordset on remote server
            remote_ids = []
            for record in self:
                record_id = record._ids[0] if record._ids else None
                if record_id:
                    remote_ids.append(record_id)
            
            if remote_ids:
                success = self._rpc_call(
                    'write',
                    'vnfield.market.requirement',
                    [remote_ids, remote_vals]
                )
                
                if success:
                    _logger.info(f"✅ Updated remote requirements: {remote_ids}")
                    return True
                else:
                    raise UserError(_('Failed to update records on remote server'))
            else:
                raise UserError(_('No valid record IDs found for update'))
                
        except Exception as e:
            _logger.error(f"Write failed: {str(e)}")
            raise UserError(_('Failed to update remote requirements: %s') % str(e))
    
    def unlink(self):
        """Override unlink to delete records from remote server via RPC"""
        try:
            # Collect remote IDs to delete
            remote_ids = []
            for record in self:
                record_id = record._ids[0] if record._ids else None
                if record_id:
                    remote_ids.append(record_id)
            
            _logger.info(f"🗑️ UNLINK called for remote IDs: {remote_ids}")
            
            if remote_ids:
                success = self._rpc_call(
                    'unlink',
                    'vnfield.market.requirement',
                    [remote_ids]
                )
                
                if success:
                    _logger.info(f"✅ Deleted remote requirements: {remote_ids}")
                    return True
                else:
                    raise UserError(_('Failed to delete records from remote server'))
            else:
                return True  # Nothing to delete
                
        except Exception as e:
            _logger.error(f"Unlink failed: {str(e)}")
            raise UserError(_('Failed to delete remote requirements: %s') % str(e))
    
    def action_open_form(self):
        """Open form view for this remote requirement"""
        self.ensure_one()
        
        # Access ID safely without triggering field resolution
        record_id = self._ids[0] if self._ids else None
        _logger.info(f"📋 ACTION_OPEN_FORM called for record ID: {record_id}")
        
        # Pre-load remote data to avoid database fetch
        remote_data = self._get_remote_requirement_by_id(record_id) if record_id else None
        if not remote_data:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Remote requirement not found',
                    'type': 'warning',
                }
            }
        
        # Open form view with remote data context
        return {
            'name': f"Remote Requirement: {remote_data.get('title', 'N/A')}",
            'type': 'ir.actions.act_window',
            'res_model': 'vnfield.market.remote.requirement',
            'view_mode': 'form',
            'res_id': record_id,
            'target': 'current',
            'context': {
                'remote_data': remote_data,
                'form_view_initial_mode': 'readonly',
            }
        }
    
    def action_open_create_wizard(self):
        """Open wizard to create new remote requirement"""
        return {
            'name': 'Create New Remote Requirement',
            'type': 'ir.actions.act_window',
            'res_model': 'vnfield.market.create.remote.requirement.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_state': 'draft',
            }
        }
    
    # @api.model
    # def action_create_new(self):
    #     """Action to create a new remote requirement - DISABLED"""
    #     # DISABLED: Creation is not allowed for remote requirements
    #     raise UserError(_('Creating new remote requirements is not allowed. View only mode.'))