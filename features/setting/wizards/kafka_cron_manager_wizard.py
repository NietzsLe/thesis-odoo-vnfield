# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 🛠️ KAFKA CRONJOB MANAGEMENT WIZARD
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

class KafkaCronManagerWizard(models.TransientModel):
    """
    🎯 CHỨC NĂNG: Wizard quản lý Kafka universal consumer cronjob
    
    Wizard này cho phép:
    - Xem trạng thái universal consumer cronjob
    - Start/Stop universal consumer
    - Cấu hình thông số consumer
    - Monitor hoạt động consumer
    
    📋 UNIVERSAL CONSUMER:
    - vnfield.kafka.universal.consumer: Universal consumer cho tất cả VNField messages
    """
    _name = 'vnfield.kafka.cron.manager'
    _description = 'Kafka Cron Job Manager'

    # ═══════════════════════════════════════════
    # 🏷️ BASIC FIELDS
    # ═══════════════════════════════════════════
    
    name = fields.Char('Wizard Name', default='Kafka Consumer Management', readonly=True)
    
    # ═══════════════════════════════════════════
    # 🔧 CONFIGURATION FIELDS
    # ═══════════════════════════════════════════
    
    kafka_enabled = fields.Boolean(
        '🔌 Kafka Enabled',
        compute='_compute_kafka_status',
        help='Hiển thị trạng thái Kafka connection'
    )
    
    bootstrap_servers = fields.Char(
        '🌐 Bootstrap Servers',
        compute='_compute_kafka_config',
        help='Kafka bootstrap servers từ configuration'
    )
    
    default_group_id = fields.Char(
        '👥 Default Group ID', 
        compute='_compute_kafka_config',
        help='Consumer group ID mặc định'
    )
    
    # ═══════════════════════════════════════════
    # 📊 KAFKA CONSUMER STATUS (SINGLE CONSUMER)
    # ═══════════════════════════════════════════
    
    # Single Consumer for all VNField events
    consumer_active = fields.Boolean('� VNField Consumer', compute='_compute_consumer_status')
    consumer_id = fields.Many2one('ir.cron', string='Consumer Cron Job', compute='_compute_consumer_status')
    topic_name = fields.Char('VNField Topic', default=lambda self: self._get_topic_default())
    last_run = fields.Datetime('Last Run', compute='_compute_consumer_status')
    next_run = fields.Datetime('Next Run', compute='_compute_consumer_status')

    @api.model
    def _get_topic_default(self):
        param = self.env['ir.config_parameter'].sudo()
        return param.get_param('vnfield.kafka.topic', 'vnfield')

    def write(self, vals):
        # Update topic config parameter when topic_name is changed
        if 'topic_name' in vals:
            param = self.env['ir.config_parameter'].sudo()
            param.set_param('vnfield.kafka.topic', vals['topic_name'])
        return super().write(vals)

    @api.model
    def create(self, vals):
        # Set topic config parameter when topic_name is provided
        if 'topic_name' in vals:
            param = self.env['ir.config_parameter'].sudo()
            param.set_param('vnfield.kafka.topic', vals['topic_name'])
        return super().create(vals)
    
    # ═══════════════════════════════════════════
    # 📊 CONSUMER STATISTICS
    # ═══════════════════════════════════════════
    
    total_consumers = fields.Integer('Total Consumers', compute='_compute_statistics')
    active_consumers = fields.Integer('Active Consumers', compute='_compute_statistics')
    inactive_consumers = fields.Integer('Inactive Consumers', compute='_compute_statistics')
    
    # ═══════════════════════════════════════════
    # 🔐 PERMISSION FIELDS (REMOVED - Use ACL instead)
    # ═══════════════════════════════════════════
    
    # 💡 NOTE(assistant): Đã bỏ is_admin và can_create_cron - sử dụng ACL thay thế
    
    # ═══════════════════════════════════════════
    # ⚙️ GLOBAL CRON CONFIGURATION
    # ═══════════════════════════════════════════
    
    default_interval_number = fields.Integer('🕐 Default Interval Number', default=1, 
                                            help='Default interval number for new consumers')
    default_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')
    ], string='🕐 Default Interval Type', default='minutes', 
       help='Default interval type for new consumers')
    
    default_priority = fields.Integer('📊 Default Priority', default=5,
                                    help='Default priority for new consumers (lower = higher priority)')
    
    default_numbercall = fields.Integer('🔢 Default Number of Calls', default=-1,
                                      help='Default number of times to execute (-1 = unlimited)')
    # ═══════════════════════════════════════════
    # 🔧 SINGLE CONSUMER CONFIGURATION
    # ═══════════════════════════════════════════
    
    # Consumer Config
    interval_number = fields.Integer('🕐 Consumer Interval', default=1)
    interval_type = fields.Selection([
        ('minutes', 'Minutes'), 
        ('hours', 'Hours'),
        ('days', 'Days')
    ], string='Consumer Interval Type', default='minutes')
    priority = fields.Integer('📊 Consumer Priority', default=5)
    numbercall = fields.Integer('🔢 Consumer Number of Calls', default=-1,
                               help='Number of times to execute (-1 = unlimited)')
    code = fields.Text('📝 Consumer Code', 
                      default='env["vnfield.sync.request"].consume()',
                      help='Python code to execute for universal consumer')
    
    # ═══════════════════════════════════════════
    # 🔧 SINGLE CONSUMER CONFIGURATION MAPPING
    # ═══════════════════════════════════════════
    
    @api.model
    def _get_consumer_mapping(self):
        """
        🗺️ Single universal consumer configuration
        
        Returns:
            dict: Universal consumer configuration
        """
        return {
            'vnfield_universal': {
                'model': 'vnfield.sync.request',
                'cron_name': 'Kafka Consumer - VNField Universal',
                'cron_code': 'env["vnfield.sync.request"].consume()',
                'topic_suffix': 'vnfield',
                'description': 'Universal consumer for all VNField messages',
                'interval': 1,  # minutes
                'priority': 5
            }
        }

    # ═══════════════════════════════════════════
    # 💡 COMPUTED FIELDS
    # ═══════════════════════════════════════════
    
    @api.depends()
    def _compute_kafka_status(self):
        """🔍 Kiểm tra trạng thái Kafka connection"""
        for record in self:
            try:
                # 📝 Try to get Kafka configuration
                config_param = self.env['ir.config_parameter'].sudo()
                bootstrap_servers = config_param.get_param('vnfield.kafka.bootstrap_servers', '')
                record.kafka_enabled = bool(bootstrap_servers)
            except Exception:
                record.kafka_enabled = False
    
    @api.depends()
    def _compute_kafka_config(self):
        """🔧 Load Kafka configuration"""
        for record in self:
            config_param = self.env['ir.config_parameter'].sudo()
            record.bootstrap_servers = config_param.get_param('vnfield.kafka.bootstrap_servers', '')
            record.default_group_id = config_param.get_param('vnfield.kafka.default_group_id', 'vnfield_consumer_group')
    
    @api.depends()
    def _compute_consumer_status(self):
        """📊 Compute trạng thái của universal consumer"""
        for record in self:
            mapping = record._get_consumer_mapping()
            config = mapping['vnfield_universal']
            
            # � Tìm cron job tương ứng
            cron_job = self.env['ir.cron'].search([
                ('cron_name', '=', config['cron_name'])
            ], limit=1)
            
            # 📊 Set status fields
            record.consumer_active = cron_job.active if cron_job else False
            record.consumer_id = cron_job.id if cron_job else False
            record.last_run = cron_job.lastcall if cron_job else False
            record.next_run = cron_job.nextcall if cron_job else False
    
    @api.depends('consumer_active')
    def _compute_statistics(self):
        """📈 Compute consumer statistics"""
        for record in self:
            record.total_consumers = 1
            record.active_consumers = 1 if record.consumer_active else 0
            record.inactive_consumers = 0 if record.consumer_active else 1
    
    @api.depends()
    def _compute_permissions(self):
        """🔐 REMOVED - Dùng ACL thay vì kiểm tra quyền trong code"""
        # 💡 NOTE(assistant): Đã bỏ logic kiểm tra quyền - sử dụng ACL từ ir.model.access.csv
        pass

    # ═══════════════════════════════════════════
    # ⚙️ CRON CONFIGURATION METHODS  
    # ═══════════════════════════════════════════
    
    def _get_cron_values(self, consumer_type='vnfield_universal'):
        """🛠️ Lấy cấu hình cron cho universal consumer"""
        return {
            'interval_number': self.interval_number,
            'interval_type': self.interval_type,
            'priority': self.priority,
            'numbercall': self.numbercall,
            'code': self.code,
        }
    
    def _update_cron_configuration(self, cron_record, consumer_type='vnfield_universal'):
        """🔧 Cập nhật cấu hình cron job"""
        if not cron_record:
            return False
            
        try:
            config = self._get_cron_values(consumer_type)
            
            # 🔧 Cập nhật các fields cron
            cron_record.write({
                'interval_number': config['interval_number'],
                'interval_type': config['interval_type'],
                'priority': config['priority'],
                'numbercall': config['numbercall'],
                'code': config['code'],
                'active': True,  # 🔄 Kích hoạt cron khi cấu hình
            })
            
            _logger.info(f"✅ Updated cron configuration for {consumer_type}: {config}")
            return True
            
        except Exception as e:
            _logger.error(f"❌ Error updating cron configuration: {e}")
            return False
    
    def action_apply_global_config(self):
        """🌍 Áp dụng cấu hình global cho universal consumer"""
        # 💡 NOTE(assistant): Đã bỏ permission check - sử dụng ACL thay thế
            
        # 🔍 Tìm cron job hiện tại
        if self.consumer_id and self._update_cron_configuration(self.consumer_id, 'vnfield_universal'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '✅ Configuration Applied',
                    'message': 'Updated universal consumer configuration successfully!',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client', 
                'tag': 'display_notification',
                'params': {
                    'title': '⚠️ No Updates',
                    'message': 'No active consumer found to update.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

    def action_load_current_config(self):
        """🔄 Load cấu hình hiện tại từ universal consumer cron job"""
        self.ensure_one()
        
        # 🔍 Lấy cron job hiện tại
        if self.consumer_id:
            # 📥 Load cấu hình từ cron job
            self.interval_number = self.consumer_id.interval_number
            self.interval_type = self.consumer_id.interval_type
            self.priority = self.consumer_id.priority
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '📥 Configuration Loaded',
                    'message': 'Loaded configuration from active universal consumer!',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '⚠️ No Configuration Found',
                    'message': 'No active consumer found to load configuration from.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

    def action_apply_topic_config(self):
        """📡 Áp dụng cấu hình topic vào ir.config_parameter"""
        self.ensure_one()
        
        ConfigParam = self.env['ir.config_parameter'].sudo()
        
        try:
            if self.topic_name:
                # 🔄 Cập nhật hoặc tạo mới config parameter
                ConfigParam.set_param('vnfield.kafka.topic', self.topic_name)
                _logger.info(f"✅ Updated topic config: vnfield.kafka.topic = {self.topic_name}")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '✅ Topic Configuration Applied',
                    'message': 'Updated universal topic configuration in ir.config_parameter!',
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"❌ Error applying topic configuration: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '❌ Configuration Error',
                    'message': f'Failed to apply topic configuration: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    # ═══════════════════════════════════════════
    # 🎯 ACTION METHODS
    # ═══════════════════════════════════════════
    
    def action_start_consumer(self, model_key='vnfield_universal'):
        """
        ▶️ Start universal consumer
        
        Args:
            model_key (str): Key của model (default: vnfield_universal)
        """
        self.ensure_one()
        mapping = self._get_consumer_mapping()
        
        if model_key not in mapping:
            raise ValidationError(_("Invalid model key: %s") % model_key)
        
        config = mapping[model_key]
        
        # 🔍 Tìm hoặc tạo cron job
        cron_job = self.env['ir.cron'].search([
            ('cron_name', '=', config['cron_name'])
        ], limit=1)
        
        if not cron_job:
            # 🆕 Tạo cron job mới
            cron_job = self._create_consumer_cron(model_key, config)
            _logger.info(f"Created new Kafka universal consumer cron job: {cron_job.name}")
        else:
            # ✅ Activate existing cron job
            cron_job.write({'active': True})
            _logger.info(f"Activated existing Kafka consumer cron job for {model_key}: {cron_job.name}")
        
        # 🔧 Áp dụng cấu hình từ wizard
        self._update_cron_configuration(cron_job, model_key)
        
        # 🔄 Recompute fields
        self._compute_consumer_status()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _('Consumer Started'),
                'message': _('Kafka consumer for %s has been started successfully') % config['model'],
                'sticky': False,
            }
        }
    
    def action_stop_consumer(self, model_key='vnfield_universal'):
        """
        ⏹️ Stop consumer cho một model cụ thể
        
        Args:
            model_key (str): Key của model (project, task, etc.)
        """
        self.ensure_one()
        mapping = self._get_consumer_mapping()
        
        if model_key not in mapping:
            raise ValidationError(_("Invalid model key: %s") % model_key)
        
        config = mapping[model_key]
        
        # 🔍 Tìm cron job
        cron_job = self.env['ir.cron'].search([
            ('cron_name', '=', config['cron_name'])
        ], limit=1)
        
        if cron_job:
            # ⏹️ Deactivate cron job
            cron_job.write({'active': False})
            _logger.info(f"Stopped Kafka consumer cron job for {model_key}: {cron_job.name}")
            
            # 🔄 Recompute fields
            self._compute_consumer_status()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'title': _('Consumer Stopped'),
                    'message': _('Kafka consumer for %s has been stopped') % config['model'],
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'title': _('Consumer Not Found'),
                    'message': _('No Kafka consumer found for %s') % config['model'],
                    'sticky': False,
                }
            }
    
    def _create_consumer_cron(self, model_key, config):
        """
        🆕 Tạo cron job mới cho consumer
        
        Args:
            model_key (str): Key của model
            config (dict): Configuration của consumer
            
        Returns:
            ir.cron: Cron job record được tạo
        """
        # � Check if user has permission to create cron jobs
        try:
            self.env['ir.cron'].check_access_rights('create')
        except Exception:
            raise ValidationError(_(
                "🚫 ACCESS DENIED\n\n"
                "You don't have permission to create cron jobs.\n"
                "Only system administrators can create new Kafka consumers.\n\n"
                "Please contact your administrator to:\n"
                "• Add you to 'Administration / Settings' group\n"
                "• Or ask them to create the consumer for you"
            ))
        
        # �🔍 Get model reference
        model_obj = self.env['ir.model'].search([
            ('model', '=', config['model'])
        ], limit=1)
        
        if not model_obj:
            raise ValidationError(_("Model %s not found") % config['model'])
        
        # 🆕 Create cron job
        # 🔧 Lấy cấu hình từ wizard
        cron_config = self._get_cron_values(model_key)
        
        cron_vals = {
            'name': config['cron_name'],
            'model_id': model_obj.id,
            'state': 'code',
            'code': cron_config['code'],  # Sử dụng code từ config
            'interval_number': cron_config['interval_number'],
            'interval_type': cron_config['interval_type'],
            'numbercall': cron_config['numbercall'],  # Sử dụng numbercall từ config
            'active': True,
            'doall': False,
            'user_id': self.env.ref('base.user_root').id,
            'priority': cron_config['priority']
        }
        
        return self.env['ir.cron'].create(cron_vals)

    # ═══════════════════════════════════════════
    # 🎯 BULK ACTIONS
    # ═══════════════════════════════════════════
    
    def action_start_all_consumers(self):
        """▶️ Start universal consumer"""
        self.ensure_one()
        
        try:
            self.action_start_consumer('vnfield_universal')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'title': _('Consumer Started'),
                    'message': _('Universal VNField consumer started successfully'),
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Failed to start universal consumer: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'error',
                    'title': _('Start Failed'),
                    'message': _('Failed to start universal consumer: %s') % str(e),
                    'sticky': True,
                }
            }
    
    def action_stop_all_consumers(self):
        """⏹️ Stop universal consumer"""
        self.ensure_one()
        
        try:
            self.action_stop_consumer('vnfield_universal')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'title': _('Consumer Stopped'),
                    'message': _('Universal VNField consumer stopped successfully'),
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Failed to stop universal consumer: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'error',
                    'title': _('Stop Failed'),
                    'message': _('Failed to stop universal consumer: %s') % str(e),
                    'sticky': True,
                }
            }
    
    def action_restart_all_consumers(self):
        """🔄 Restart universal consumer"""
        self.ensure_one()
        
        # ⏹️ Stop first
        self.action_stop_consumer('vnfield_universal')
        
        # ⏱️ Wait a moment
        import time
        time.sleep(1)
        
        # ▶️ Start again
        return self.action_start_all_consumers()

    # ═══════════════════════════════════════════
    # 🎯 UNIVERSAL CONSUMER ACTIONS
    # ═══════════════════════════════════════════
    
    def action_start_universal_consumer(self):
        """▶️ Start Universal Consumer"""
        return self.action_start_consumer('vnfield_universal')
    
    def action_stop_universal_consumer(self):
        """⏹️ Stop Universal Consumer"""
        return self.action_stop_consumer('vnfield_universal')
    # ═══════════════════════════════════════════
    # 🔧 UTILITY METHODS
    # ═══════════════════════════════════════════
    
    def action_view_cron_jobs(self):
        """📋 Xem universal Kafka cron job"""
        self.ensure_one()
        mapping = self._get_consumer_mapping()
        config = mapping['vnfield_universal']
        
        return {
            'name': _('VNField Universal Consumer Cron Job'),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.cron',
            'view_mode': 'tree,form',
            'domain': [('cron_name', '=', config['cron_name'])],
            'context': {'create': False},
            'target': 'current',
        }
    
    def action_refresh_status(self):
        """🔄 Refresh consumer status"""
        self.ensure_one()
        self._compute_consumer_status()
        self._compute_statistics()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'title': _('Status Refreshed'),
                'message': _('Consumer status has been refreshed'),
                'sticky': False,
            }
        }
