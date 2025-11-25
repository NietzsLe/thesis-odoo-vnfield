# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class ContractorRepresentativeWizard(models.TransientModel):
    """
    🏢 CONTRACTOR REPRESENTATIVE CONFIGURATION WIZARD
    
    Wizard để cấu hình thông tin contractor đại diện cho hệ thống.
    Cho phép:
    - Cấu hình thông tin contractor cơ bản
    - Lưu cấu hình vào ir.config_parameter
    - Đăng ký với integration system thông qua RPC
    - Quản lý trạng thái: not_configured → configured → registered
    """
    _name = 'vnfield.contractor.representative.wizard'
    _description = 'Contractor Representative Configuration Wizard'

    # ═══════════════════════════════════════════
    # 🏢 CONTRACTOR BASIC INFORMATION
    # ═══════════════════════════════════════════
    
    name = fields.Char(
        string='Contractor Name',
        required=True,
        help='Name of the contractor company'
    )
    
    description = fields.Text(
        string='Description',
        help='Company description and capabilities'
    )
    
    contractor_type = fields.Selection([
        ('internal', 'Internal - Nội bộ'),
        ('external', 'External - Bên ngoài'), 
        ('shared', 'Shared - Liên nhà thầu')
    ], string='Contractor Type', default='external', required=True)
    
    # ═══════════════════════════════════════════
    # 📞 CONTACT INFORMATION
    # ═══════════════════════════════════════════
    
    email = fields.Char(
        string='Email',
        required=True,
        help='Official email address'
    )
    
    phone = fields.Char(
        string='Phone',
        help='Contact phone number'
    )
    
    address = fields.Text(
        string='Address',
        help='Full address of the contractor'
    )
    
    website = fields.Char(
        string='Website',
        help='Company website URL'
    )
    
    # ═══════════════════════════════════════════
    # 📊 STATUS AND REGISTRATION INFORMATION
    # ═══════════════════════════════════════════
    
    status = fields.Selection([
        ('not_configured', 'Not Configured'),
        ('configured', 'Configured'),
        ('registered', 'Registered')
    ], string='Status', default='not_configured', readonly=True)
    
    external_id = fields.Char(
        string='External ID',
        readonly=True,
        help='ID assigned by integration system after registration'
    )
    
    registration_date = fields.Datetime(
        string='Registration Date',
        readonly=True,
        help='Date when contractor was registered in integration system'
    )
    
    integration_server_url = fields.Char(
        string='Integration Server URL',
        help='URL of the integration system for RPC calls (e.g. https://integration-server.com)'
    )
    
    integration_database = fields.Char(
        string='Integration Database',
        help='Database name on the integration server'
    )
    
    integration_username = fields.Char(
        string='Integration Username',
        help='Username for authentication on integration server'
    )
    
    integration_api_key = fields.Char(
        string='Integration API Key',
        help='API Key for authentication (replaces password for security)'
    )
    
    # ═══════════════════════════════════════════
    # 🔧 METHODS
    # ═══════════════════════════════════════════
    
    def _validate_server_url(self, url):
        """Validate server URL format"""
        import urllib.parse
        
        if not url:
            return False, "Server URL is required"
            
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.netloc:
                return False, "Invalid URL format"
            return True, url
        except Exception as e:
            return False, f"URL validation error: {str(e)}"
    
    def _get_troubleshooting_tips(self, error_type):
        """Get troubleshooting tips based on error type"""
        tips = {
            'unsupported_xmlrpc': [
                "Server is not an Odoo instance",
                "XML-RPC is disabled on the server", 
                "Wrong URL format - use base URL only",
                "Try: https://your-server.com (not /xmlrpc/2/common)"
            ],
            'connection_refused': [
                "Odoo server is not running",
                "Server is behind firewall",
                "Wrong port number",
                "Check server status and network connectivity"
            ],
            'ssl_error': [
                "SSL certificate issues",
                "Try HTTP instead of HTTPS for testing",
                "Certificate not trusted",
                "Self-signed certificate problem"
            ],
            'dns_error': [
                "Cannot resolve hostname",
                "Check if server URL is correct",
                "DNS server issues",
                "Domain name doesn't exist"
            ],
            'timeout': [
                "Server is not responding",
                "Network connectivity issues",
                "Server overloaded",
                "Firewall blocking connection"
            ]
        }
        return tips.get(error_type, ["Check server configuration", "Verify network connectivity"])
    
    def action_diagnose_connection(self):
        """🔍 Run comprehensive connection diagnostics"""
        self.ensure_one()
        
        if not self.integration_server_url:
            raise ValidationError("Integration server URL is required for diagnostics")
        
        diagnostics = []
        server_url = self.integration_server_url.rstrip('/')
        
        # Step 1: Validate URL format
        is_valid, result = self._validate_server_url(server_url)
        if not is_valid:
            diagnostics.append(f"❌ URL Format: {result}")
            server_url = result if is_valid else server_url
        else:
            diagnostics.append(f"✅ URL Format: Valid")
            server_url = result
        
        # Step 2: Test DNS resolution
        try:
            import socket
            import urllib.parse
            parsed_url = urllib.parse.urlparse(server_url)
            hostname = parsed_url.hostname
            ip = socket.gethostbyname(hostname)
            diagnostics.append(f"✅ DNS Resolution: {hostname} → {ip}")
        except Exception as e:
            diagnostics.append(f"❌ DNS Resolution: {str(e)}")
        
        # Step 3: Test basic HTTP connectivity
        try:
            import requests
            test_url = f"{server_url}/web/database/list"
            response = requests.get(test_url, timeout=5, verify=False)
            diagnostics.append(f"✅ HTTP Connectivity: Status {response.status_code}")
        except requests.exceptions.SSLError:
            diagnostics.append(f"⚠️ HTTP Connectivity: SSL Certificate issue")
        except requests.exceptions.ConnectionError:
            diagnostics.append(f"❌ HTTP Connectivity: Connection refused")
        except requests.exceptions.Timeout:
            diagnostics.append(f"❌ HTTP Connectivity: Timeout")
        except Exception as e:
            diagnostics.append(f"❌ HTTP Connectivity: {str(e)}")
        
        # Step 4: Test XML-RPC endpoint
        try:
            import xmlrpc.client
            common_endpoint = f"{server_url}/xmlrpc/2/common"
            common = xmlrpc.client.ServerProxy(common_endpoint, verbose=False)
            server_info = common.version()
            version = server_info.get('server_version', 'Unknown')
            diagnostics.append(f"✅ XML-RPC Endpoint: Odoo {version}")
        except xmlrpc.client.ProtocolError as e:
            diagnostics.append(f"❌ XML-RPC Endpoint: Protocol Error {e.errcode}")
        except Exception as e:
            if "unsupported XML-RPC protocol" in str(e):
                diagnostics.append(f"❌ XML-RPC Endpoint: Not an Odoo server")
            else:
                diagnostics.append(f"❌ XML-RPC Endpoint: {str(e)}")
        
        # Step 5: Test authentication if credentials provided
        if self.integration_database and self.integration_username and self.integration_api_key:
            try:
                import xmlrpc.client
                common_endpoint = f"{server_url}/xmlrpc/2/common"
                common = xmlrpc.client.ServerProxy(common_endpoint)
                uid = common.authenticate(
                    self.integration_database,
                    self.integration_username,
                    self.integration_api_key,
                    {}
                )
                if uid:
                    diagnostics.append(f"✅ Authentication: Success (UID: {uid})")
                else:
                    diagnostics.append(f"❌ Authentication: Failed - Check credentials")
            except Exception as e:
                diagnostics.append(f"❌ Authentication: {str(e)}")
        else:
            diagnostics.append(f"⚠️ Authentication: Credentials not configured")
        
        # Format results
        result_message = "🔍 Connection Diagnostics Results:\n\n" + "\n".join(diagnostics)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'title': '🔍 Connection Diagnostics',
                'message': result_message,
                'sticky': True,
            }
        }
    
    @api.model
    def default_get(self, fields_list):
        """Load contractor representative configuration from ir.config_parameter"""
        res = super().default_get(fields_list)
        
        # Load contractor configuration if exists
        config_param = self.env['ir.config_parameter'].sudo()
        
        res.update({
            'name': config_param.get_param('vnfield.contractor_representative.name', ''),
            'description': config_param.get_param('vnfield.contractor_representative.description', ''),
            'contractor_type': config_param.get_param('vnfield.contractor_representative.contractor_type', 'external'),
            'email': config_param.get_param('vnfield.contractor_representative.email', ''),
            'phone': config_param.get_param('vnfield.contractor_representative.phone', ''),
            'address': config_param.get_param('vnfield.contractor_representative.address', ''),
            'website': config_param.get_param('vnfield.contractor_representative.website', ''),
            'status': config_param.get_param('vnfield.contractor_representative.status', 'not_configured'),
            'external_id': config_param.get_param('vnfield.contractor_representative.external_id', ''),
            'integration_server_url': config_param.get_param('vnfield.integration_server_url', ''),
            'integration_database': config_param.get_param('vnfield.integration_database', ''),
            'integration_username': config_param.get_param('vnfield.integration_username', ''),
            'integration_api_key': config_param.get_param('vnfield.integration_api_key', ''),
        })
        
        # Load registration date if exists
        reg_date = config_param.get_param('vnfield.contractor_representative.registration_date', False)
        if reg_date:
            try:
                res['registration_date'] = fields.Datetime.from_string(reg_date)
            except:
                pass
                
        return res
    
    def action_save_configuration(self):
        """💾 Lưu cấu hình contractor đại diện"""
        self.ensure_one()
        
        # Validate required fields
        if not self.name:
            raise ValidationError("Contractor name is required")
        if not self.email:
            raise ValidationError("Email is required")
        
        try:
            # Save to ir.config_parameter
            config_param = self.env['ir.config_parameter'].sudo()
            
            config_param.set_param('vnfield.contractor_representative.name', self.name or '')
            config_param.set_param('vnfield.contractor_representative.description', self.description or '')
            config_param.set_param('vnfield.contractor_representative.contractor_type', self.contractor_type or 'external')
            config_param.set_param('vnfield.contractor_representative.email', self.email or '')
            config_param.set_param('vnfield.contractor_representative.phone', self.phone or '')
            config_param.set_param('vnfield.contractor_representative.address', self.address or '')
            config_param.set_param('vnfield.contractor_representative.website', self.website or '')
            config_param.set_param('vnfield.integration_server_url', self.integration_server_url or '')
            config_param.set_param('vnfield.integration_database', self.integration_database or '')
            config_param.set_param('vnfield.integration_username', self.integration_username or '')
            config_param.set_param('vnfield.integration_api_key', self.integration_api_key or '')
            
            # Update status to configured
            config_param.set_param('vnfield.contractor_representative.status', 'configured')
            self.status = 'configured'
            
            _logger.info(f"Contractor representative configuration saved: {self.name}")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'title': '✅ Configuration Saved',
                    'message': 'Contractor representative configuration has been saved successfully!',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Failed to save contractor configuration: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': '❌ Save Failed',
                    'message': f'Failed to save contractor configuration: {str(e)}',
                    'sticky': True,
                }
            }
    
    def action_register_contractor(self):
        """📝 Đăng ký contractor với integration system"""
        self.ensure_one()
        
        if self.status != 'configured':
            raise ValidationError("Please configure and save contractor information first")
        
        if not self.integration_server_url:
            raise ValidationError("Integration server URL is required for registration")
        if not self.integration_database:
            raise ValidationError("Integration database name is required for registration")
        if not self.integration_username:
            raise ValidationError("Integration username is required for registration")
        if not self.integration_api_key:
            raise ValidationError("Integration API key is required for registration")
        
        try:
            # Prepare contractor data based on vnfield.contractor model
            contractor_data = {
                'name': self.name,
                'description': self.description,
                'contractor_type': self.contractor_type,
                'email': self.email,
                'phone': self.phone,
                'address': self.address,
                'website': self.website,
            }
            
            # Use Odoo standard XML-RPC for integration
            import xmlrpc.client
            
            # Setup XML-RPC endpoints following Odoo documentation
            server_url = self.integration_server_url.rstrip('/')
            common_endpoint = f"{server_url}/xmlrpc/2/common"
            object_endpoint = f"{server_url}/xmlrpc/2/object"
            
            # Step 1: Test connection and get server info
            common = xmlrpc.client.ServerProxy(common_endpoint)
            server_info = common.version()
            _logger.info(f"Connected to Odoo server version: {server_info.get('server_version', 'Unknown')}")
            
            # Step 2: Authenticate using API key (replaces password)
            uid = common.authenticate(
                self.integration_database,
                self.integration_username,
                self.integration_api_key,  # API Key used instead of password
                {}
            )
            
            if not uid:
                raise Exception("Authentication failed. Please check username and API key.")
            
            _logger.info(f"Authenticated successfully with UID: {uid}")
            
            # Step 3: Call contractor registration method using new RPC endpoint
            models = xmlrpc.client.ServerProxy(object_endpoint)
            
            # Execute contractor registration using rpc_register_contractor
            result = models.execute_kw(
                self.integration_database,        # database
                uid,                              # user id
                self.integration_api_key,         # API key (password)
                'vnfield.contractor',             # model
                'rpc_register_contractor',        # method name (updated)
                [contractor_data],                # positional args
                {}                                # keyword args
            )
            
            if result and result.get('success'):
                # Save registration info from new RPC endpoint response
                external_id = result.get('contractor_id')  # Updated field name
                contractor_data_response = result.get('data', {})
                reg_date = fields.Datetime.now()
                
                self.external_id = str(external_id) if external_id else ''
                self.registration_date = reg_date
                self.status = 'registered'
                
                # Save to config parameters
                config_param = self.env['ir.config_parameter'].sudo()
                config_param.set_param('vnfield.contractor_representative.external_id', str(external_id) if external_id else '')
                config_param.set_param('vnfield.contractor_representative.registration_date', str(reg_date))
                config_param.set_param('vnfield.contractor_representative.status', 'registered')
                
                _logger.info(f"Contractor registered successfully with ID: {external_id}")
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'success',
                        'title': '✅ Registration Successful',
                        'message': f'{result.get("message", "Contractor registered successfully")} (ID: {external_id})',
                        'sticky': False,
                    }
                }
            else:
                error_msg = result.get('message', 'Unknown registration error')  # Updated field name
                raise Exception(error_msg)
                
        except Exception as e:
            _logger.error(f"Failed to register contractor: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': '❌ Registration Failed',
                    'message': f'Failed to register contractor: {str(e)}',
                    'sticky': True,
                }
            }
    
    def action_reload_configuration(self):
        """🔄 Reload contractor configuration from ir.config_parameter"""
        self.ensure_one()
        
        config_param = self.env['ir.config_parameter'].sudo()
        
        self.write({
            'name': config_param.get_param('vnfield.contractor_representative.name', ''),
            'description': config_param.get_param('vnfield.contractor_representative.description', ''),
            'contractor_type': config_param.get_param('vnfield.contractor_representative.contractor_type', 'external'),
            'email': config_param.get_param('vnfield.contractor_representative.email', ''),
            'phone': config_param.get_param('vnfield.contractor_representative.phone', ''),
            'address': config_param.get_param('vnfield.contractor_representative.address', ''),
            'website': config_param.get_param('vnfield.contractor_representative.website', ''),
            'status': config_param.get_param('vnfield.contractor_representative.status', 'not_configured'),
            'external_id': config_param.get_param('vnfield.contractor_representative.external_id', ''),
            'integration_server_url': config_param.get_param('vnfield.integration_server_url', ''),
            'integration_database': config_param.get_param('vnfield.integration_database', ''),
            'integration_username': config_param.get_param('vnfield.integration_username', ''),
            'integration_api_key': config_param.get_param('vnfield.integration_api_key', ''),
        })
        
        # Load registration date
        reg_date = config_param.get_param('vnfield.contractor_representative.registration_date', False)
        if reg_date:
            try:
                self.registration_date = fields.Datetime.from_string(reg_date)
            except:
                pass
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'title': '🔄 Configuration Loaded',
                'message': 'Contractor configuration has been reloaded from system parameters',
                'sticky': False,
            }
        }
    
    def action_test_connection(self):
        """🔗 Test connection to integration system"""
        self.ensure_one()
        
        if not self.integration_server_url:
            raise ValidationError("Integration server URL is required")
        
        server_url = self.integration_server_url.rstrip('/')
        
        # Step 1: Test basic HTTP connectivity first
        try:
            import requests
            import urllib.parse
            
            # Validate URL format
            parsed_url = urllib.parse.urlparse(server_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValidationError("Invalid server URL format. Use format: https://server.com")
            
            # Test basic HTTP connectivity
            test_url = f"{server_url}/web/database/list"
            response = requests.get(test_url, timeout=10, verify=False)  # Skip SSL verification for testing
            
            _logger.info(f"HTTP test response: {response.status_code}")
            
        except requests.exceptions.SSLError as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'title': '🔒 SSL Certificate Issue',
                    'message': f'SSL certificate problem: {str(e)}. Try using HTTP instead of HTTPS for testing.',
                    'sticky': True,
                }
            }
        except requests.exceptions.ConnectionError as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': '🌐 Connection Failed',
                    'message': f'Cannot reach server at {server_url}. Check URL and network connectivity.',
                    'sticky': True,
                }
            }
        except requests.exceptions.Timeout:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'title': '⏱️ Connection Timeout',
                    'message': f'Server {server_url} is not responding. Check if server is running.',
                    'sticky': True,
                }
            }
        except Exception as e:
            _logger.error(f"HTTP connectivity test failed: {str(e)}")
        
        # Step 2: Test XML-RPC connectivity
        try:
            import xmlrpc.client
            import socket
            
            # Test XML-RPC endpoint
            common_endpoint = f"{server_url}/xmlrpc/2/common"
            
            _logger.info(f"Testing XML-RPC endpoint: {common_endpoint}")
            
            # Create ServerProxy with custom transport for better error handling
            common = xmlrpc.client.ServerProxy(common_endpoint, verbose=False, allow_none=True)
            
            # Test server version call
            server_info = common.version()
            
            if not isinstance(server_info, dict) or 'server_version' not in server_info:
                raise Exception("Server returned invalid response. This may not be an Odoo server.")
            
            _logger.info(f"Server version: {server_info}")
            
            # Step 3: Test authentication if credentials provided
            if self.integration_database and self.integration_username and self.integration_api_key:
                try:
                    uid = common.authenticate(
                        self.integration_database,
                        self.integration_username,
                        self.integration_api_key,
                        {}
                    )
                    
                    if uid:
                        message = f'✅ Successfully connected to Odoo {server_info.get("server_version", "Unknown")} and authenticated as UID {uid}'
                        notification_type = 'success'
                    else:
                        message = f'⚠️ Connected to server (v{server_info.get("server_version", "Unknown")}) but authentication failed. Check database name, username and API key.'
                        notification_type = 'warning'
                        
                except Exception as auth_error:
                    message = f'⚠️ Connected to server (v{server_info.get("server_version", "Unknown")}) but authentication error: {str(auth_error)}'
                    notification_type = 'warning'
            else:
                message = f'✅ Successfully connected to Odoo server version {server_info.get("server_version", "Unknown")}. Configure database, username and API key for full authentication test.'
                notification_type = 'info'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': notification_type,
                    'title': '🔗 Connection Test Result',
                    'message': message,
                    'sticky': False,
                }
            }
                
        except xmlrpc.client.ProtocolError as e:
            # Handle XML-RPC protocol errors
            error_msg = f"XML-RPC Protocol Error: {e.errmsg} (Code: {e.errcode})"
            if e.errcode == 404:
                error_msg += "\n\nPossible causes:\n• Server URL is incorrect\n• XML-RPC endpoint not available\n• Not an Odoo server"
            elif e.errcode == 500:
                error_msg += "\n\nPossible causes:\n• Internal server error\n• Database issue\n• Server misconfiguration"
                
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': '🚫 XML-RPC Protocol Error',
                    'message': error_msg,
                    'sticky': True,
                }
            }
            
        except xmlrpc.client.Fault as e:
            # Handle XML-RPC faults (server-side errors)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': '🚫 Server Error',
                    'message': f'Server returned error: {e.faultString} (Code: {e.faultCode})',
                    'sticky': True,
                }
            }
            
        except socket.gaierror as e:
            # Handle DNS resolution errors
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': '🌐 DNS Resolution Failed',
                    'message': f'Cannot resolve hostname. Check if server URL is correct: {str(e)}',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            # Handle any other exceptions
            error_msg = str(e)
            
            # Provide specific guidance for common errors
            if "unsupported XML-RPC protocol" in error_msg.lower():
                error_msg += "\n\nThis usually means:\n• Server is not an Odoo instance\n• XML-RPC is disabled\n• Wrong URL format\n\nTry: https://your-server.com (not /xmlrpc/2/common)"
            elif "connection refused" in error_msg.lower():
                error_msg += "\n\nServer is not accepting connections.\nCheck if Odoo server is running."
            elif "ssl" in error_msg.lower():
                error_msg += "\n\nSSL/HTTPS issue. Try using HTTP instead for testing."
                
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': '⚠️ Connection Failed',
                    'message': error_msg,
                    'sticky': True,
                }
            }

    def action_reset_contractor(self):
        """🔄 Reset contractor configuration về trạng thái chưa cấu hình"""
        self.ensure_one()
        
        try:
            config_param = self.env['ir.config_parameter'].sudo()
            
            # Xóa các cấu hình contractor (GIỮ LẠI RPC configs)
            contractor_keys = [
                'vnfield.contractor_representative.name',
                'vnfield.contractor_representative.description', 
                'vnfield.contractor_representative.contractor_type',
                'vnfield.contractor_representative.email',
                'vnfield.contractor_representative.phone',
                'vnfield.contractor_representative.address',
                'vnfield.contractor_representative.website',
                'vnfield.contractor_representative.status',
                'vnfield.contractor_representative.external_id',
                'vnfield.contractor_representative.registration_date',
            ]
            
            # Xóa contractor parameters nhưng GIỮ RPC parameters
            for key in contractor_keys:
                config_param.set_param(key, '')
            
            # Reset status về not_configured
            config_param.set_param('vnfield.contractor_representative.status', 'not_configured')
            
            # Update wizard fields (reset contractor info, keep RPC info)
            self.write({
                'name': '',
                'description': '',
                'contractor_type': 'external',  # default value
                'email': '',
                'phone': '',
                'address': '',
                'website': '',
                'status': 'not_configured',
                'external_id': '',
                'registration_date': False,
                # Giữ nguyên: integration_server_url, integration_database, 
                # integration_username, integration_api_key
            })
            
            _logger.info("Contractor representative configuration has been reset")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'title': '🔄 Configuration Reset',
                    'message': 'Contractor configuration has been reset. RPC settings are preserved.',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Failed to reset contractor configuration: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': '❌ Reset Failed',
                    'message': f'Failed to reset contractor configuration: {str(e)}',
                    'sticky': True,
                }
            }