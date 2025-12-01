# -*- coding: utf-8 -*-

# ===========================================
# =        ⚙️ SYSTEM CONFIGURATION           =
# ===========================================

"""
┌────────────────────────────────────────────┐
│    🧰 CHỨC NĂNG: SYSTEM CONFIG WIZARD       │
│                                            │
│ - Giao diện cấu hình system parameters    │
│ - Quản lý các configs qua UI thân thiện   │
│ - Dựa trên TransientModel cho wizard      │
│ - Expandable cho các configs khác
────────────────────────────────────────┘
"""

import logging
import time
import threading
from datetime import datetime, timedelta
import odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class KafkaConfigWizard(models.TransientModel):
    """
    🔧 Wizard cấu hình Kafka Parameters
    
    Wizard này cung cấp giao diện thân thiện để:
    - Cấu hình Kafka parameters
    - Test connections và validate configs
    - Backup/Restore configurations
    """
    
    _name = 'vnfield.kafka.config.wizard'
    _description = 'Kafka Configuration Wizard'

    # ─────────────────────────────────────────────
    # ▶ Basic Configuration Fields
    # ─────────────────────────────────────────────
    
    bootstrap_servers = fields.Char(
        string='Bootstrap Servers',
        required=True,
        default='localhost:9092',
        help='Địa chỉ Kafka brokers (phân cách bằng dấu phẩy nếu nhiều servers)'
    )
    
    security_protocol = fields.Selection([
        ('PLAINTEXT', 'PLAINTEXT'),
        ('SSL', 'SSL'),
        ('SASL_PLAINTEXT', 'SASL_PLAINTEXT'),
        ('SASL_SSL', 'SASL_SSL')
    ], string='Security Protocol', default='PLAINTEXT', required=True,
       help='Giao thức bảo mật cho kết nối Kafka')

    # ─────────────────────────────────────────────
    # ▶ SASL Authentication Fields
    # ─────────────────────────────────────────────
    
    sasl_mechanism = fields.Selection([
        ('PLAIN', 'PLAIN'),
        ('SCRAM-SHA-256', 'SCRAM-SHA-256'),
        ('SCRAM-SHA-512', 'SCRAM-SHA-512'),
        ('GSSAPI', 'GSSAPI'),
        ('OAUTHBEARER', 'OAUTHBEARER')
    ], string='SASL Mechanism', default='PLAIN',
       help='Cơ chế xác thực SASL')
    
    sasl_username = fields.Char(
        string='SASL Username',
        help='Username cho SASL authentication'
    )
    
    sasl_password = fields.Char(
        string='SASL Password',
        password=True,
        help='Password cho SASL authentication'
    )

    # ─────────────────────────────────────────────
    # ▶ SSL/TLS Configuration Fields
    # ─────────────────────────────────────────────
    
    ssl_ca_location = fields.Char(
        string='SSL CA Certificate Location',
        help='Đường dẫn đến CA certificate file'
    )
    
    ssl_certificate_location = fields.Char(
        string='SSL Certificate Location',
        help='Đường dẫn đến client certificate file'
    )
    
    ssl_key_location = fields.Char(
        string='SSL Key Location',
        help='Đường dẫn đến private key file'
    )

    # ─────────────────────────────────────────────
    # ▶ Producer Configuration Fields
    # ─────────────────────────────────────────────
    
    producer_acks = fields.Selection([
        ('0', '0 - No acknowledgment'),
        ('1', '1 - Leader acknowledgment'),
        ('all', 'all - Full ISR acknowledgment')
    ], string='Producer Acks', default='all',
       help='Mức độ acknowledgment từ Kafka cluster')
    
    producer_retries = fields.Integer(
        string='Producer Retries',
        default=3,
        help='Số lần retry khi gửi message thất bại'
    )
    
    producer_batch_size = fields.Integer(
        string='Producer Batch Size',
        default=16384,
        help='Kích thước batch cho producer (bytes)'
    )
    
    producer_linger_ms = fields.Integer(
        string='Producer Linger (ms)',
        default=5,
        help='Thời gian chờ để tạo batch (milliseconds)'
    )

    # ─────────────────────────────────────────────
    # ▶ Consumer Configuration Fields
    # ─────────────────────────────────────────────
    
    consumer_auto_offset_reset = fields.Selection([
        ('earliest', 'Earliest'),
        ('latest', 'Latest'),
        ('none', 'None')
    ], string='Auto Offset Reset', default='earliest',
       help='Chiến lược reset offset khi không tìm thấy offset')
    
    consumer_auto_commit = fields.Boolean(
        string='Enable Auto Commit',
        default=True,
        help='Tự động commit offset sau khi consume message'
    )
    
    consumer_session_timeout = fields.Integer(
        string='Session Timeout (ms)',
        default=30000,
        help='Timeout cho consumer session (milliseconds)'
    )
    
    consumer_heartbeat_interval = fields.Integer(
        string='Heartbeat Interval (ms)',
        default=10000,
        help='Interval gửi heartbeat (milliseconds)'
    )
    
    # ─────────────────────────────────────────────
    # ▶ Consumer Timeout Configuration Fields
    # ─────────────────────────────────────────────
    
    consumer_max_no_message_retries = fields.Integer(
        string='Max No-Message Retries',
        default=3,
        help='Số lần retry tối đa khi không có message trong consume'
    )
    
    consumer_max_total_time_multiplier = fields.Integer(
        string='Max Total Time Multiplier',
        default=10,
        help='Hệ số nhân với timeout để tính tổng thời gian consume tối đa'
    )

    # ─────────────────────────────────────────────
    # ▶ Status và Control Fields
    # ─────────────────────────────────────────────
    
    connection_status = fields.Text(
        string='Connection Status',
        readonly=True,
        help='Kết quả test connection'
    )
    
    show_sasl_config = fields.Boolean(
        string='Show SASL Config',
        compute='_compute_show_sasl_config',
        help='Hiển thị cấu hình SASL'
    )
    
    show_ssl_config = fields.Boolean(
        string='Show SSL Config',
        compute='_compute_show_ssl_config',
        help='Hiển thị cấu hình SSL'
    )
    
    # ─────────────────────────────────────────────
    # ▶ Test Pub/Sub Fields
    # ─────────────────────────────────────────────
    
    test_status = fields.Selection([
        ('not_started', 'Not Started'),
        ('testing', 'Testing...'),
        ('passed', 'Test Passed'),
        ('failed', 'Test Failed'),
        ('timeout', 'Test Timeout')
    ], string='Test Status', default='not_started', readonly=True)
    
    test_message = fields.Text(
        string='Test Result',
        readonly=True,
        help='Kết quả test pub/sub'
    )
    
    last_test_time = fields.Datetime(
        string='Last Test Time',
        readonly=True,
        help='Thời gian test gần nhất'
    )

    # ─────────────────────────────────────────────
    # ▶ Computed Fields và Constraints
    # ─────────────────────────────────────────────
    
    @api.depends('security_protocol')
    def _compute_show_sasl_config(self):
        """🔍 Hiển thị SASL config khi cần thiết"""
        for record in self:
            record.show_sasl_config = record.security_protocol in ['SASL_PLAINTEXT', 'SASL_SSL']
    
    @api.depends('security_protocol')
    def _compute_show_ssl_config(self):
        """🔍 Hiển thị SSL config khi cần thiết"""
        for record in self:
            record.show_ssl_config = record.security_protocol in ['SSL', 'SASL_SSL']
    
    @api.constrains('producer_retries')
    def _check_producer_retries(self):
        """✅ Validate producer retries"""
        for record in self:
            if record.producer_retries < 0:
                raise ValidationError(_('Producer retries must be >= 0'))
    
    @api.constrains('producer_batch_size')
    def _check_producer_batch_size(self):
        """✅ Validate producer batch size"""
        for record in self:
            if record.producer_batch_size <= 0:
                raise ValidationError(_('Producer batch size must be > 0'))
    
    @api.constrains('consumer_session_timeout', 'consumer_heartbeat_interval')
    def _check_consumer_timeouts(self):
        """✅ Validate consumer timeouts"""
        for record in self:
            if record.consumer_session_timeout <= 0:
                raise ValidationError(_('Consumer session timeout must be > 0'))
            if record.consumer_heartbeat_interval <= 0:
                raise ValidationError(_('Consumer heartbeat interval must be > 0'))
            if record.consumer_heartbeat_interval >= record.consumer_session_timeout:
                raise ValidationError(_(
                    'Heartbeat interval must be less than session timeout'
                ))
    
    @api.constrains('consumer_max_no_message_retries', 'consumer_max_total_time_multiplier')
    def _check_consumer_retry_config(self):
        """✅ Validate consumer retry configuration"""
        for record in self:
            if record.consumer_max_no_message_retries <= 0:
                raise ValidationError(_('Max no-message retries must be > 0'))
            if record.consumer_max_total_time_multiplier <= 0:
                raise ValidationError(_('Max total time multiplier must be > 0'))

    # ─────────────────────────────────────────────
    # ▶ Data Loading Methods
    # ─────────────────────────────────────────────
    
    @api.model
    def default_get(self, fields_list):
        """🔄 Load current system parameters when opening wizard"""
        res = super().default_get(fields_list)
        
        # 💡 NOTE(assistant): Load current parameters from ir.config_parameter
        param_mappings = {
            'bootstrap_servers': 'kafka.bootstrap_servers',
            'security_protocol': 'kafka.security_protocol',
            'sasl_mechanism': 'kafka.sasl_mechanism',
            'sasl_username': 'kafka.sasl_username',
            'sasl_password': 'kafka.sasl_password',
            'ssl_ca_location': 'kafka.ssl_ca_location',
            'ssl_certificate_location': 'kafka.ssl_certificate_location',
            'ssl_key_location': 'kafka.ssl_key_location',
            'producer_acks': 'kafka.producer_acks',
            'producer_retries': 'kafka.producer_retries',
            'producer_batch_size': 'kafka.producer_batch_size',
            'producer_linger_ms': 'kafka.producer_linger_ms',
            'consumer_auto_offset_reset': 'kafka.consumer_auto_offset_reset',
            'consumer_auto_commit': 'kafka.consumer_auto_commit',
            'consumer_session_timeout': 'kafka.consumer_session_timeout',
            'consumer_heartbeat_interval': 'kafka.consumer_heartbeat_interval',
            'consumer_max_no_message_retries': 'kafka.consumer_max_no_message_retries',
            'consumer_max_total_time_multiplier': 'kafka.consumer_max_total_time_multiplier',
        }
        
        config_param = self.env['ir.config_parameter'].sudo()
        
        for field_name, param_key in param_mappings.items():
            if field_name in fields_list:
                param_value = config_param.get_param(param_key)
                if param_value:
                    # 🔄 Convert string values to appropriate types
                    if field_name in ['producer_retries', 'producer_batch_size', 'producer_linger_ms',
                                    'consumer_session_timeout', 'consumer_heartbeat_interval',
                                    'consumer_max_no_message_retries', 'consumer_max_total_time_multiplier']:
                        try:
                            res[field_name] = int(param_value)
                        except (ValueError, TypeError):
                            pass  # Keep default value
                    elif field_name == 'consumer_auto_commit':
                        res[field_name] = param_value.lower() == 'true'
                    else:
                        res[field_name] = param_value
        
        return res

    # ─────────────────────────────────────────────
    # ▶ Action Methods
    # ─────────────────────────────────────────────
    
    def action_save_configuration(self):
        """💾 Lưu configuration vào system parameters"""
        self.ensure_one()
        
        try:
            config_param = self.env['ir.config_parameter'].sudo()
            
            # 📝 TODO(user): Có thể thêm backup trước khi save
            param_mappings = {
                'kafka.bootstrap_servers': self.bootstrap_servers,
                'kafka.security_protocol': self.security_protocol,
                'kafka.sasl_mechanism': self.sasl_mechanism,
                'kafka.sasl_username': self.sasl_username or '',
                'kafka.sasl_password': self.sasl_password or '',
                'kafka.ssl_ca_location': self.ssl_ca_location or '',
                'kafka.ssl_certificate_location': self.ssl_certificate_location or '',
                'kafka.ssl_key_location': self.ssl_key_location or '',
                'kafka.producer_acks': self.producer_acks,
                'kafka.producer_retries': str(self.producer_retries),
                'kafka.producer_batch_size': str(self.producer_batch_size),
                'kafka.producer_linger_ms': str(self.producer_linger_ms),
                'kafka.consumer_auto_offset_reset': self.consumer_auto_offset_reset,
                'kafka.consumer_auto_commit': 'true' if self.consumer_auto_commit else 'false',
                'kafka.consumer_session_timeout': str(self.consumer_session_timeout),
                'kafka.consumer_heartbeat_interval': str(self.consumer_heartbeat_interval),
                'kafka.consumer_max_no_message_retries': str(self.consumer_max_no_message_retries),
                'kafka.consumer_max_total_time_multiplier': str(self.consumer_max_total_time_multiplier),
            }
            
            # 🔁 Save all parameters
            for param_key, param_value in param_mappings.items():
                config_param.set_param(param_key, param_value)
            
            _logger.info('Kafka configuration saved successfully')
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Kafka configuration saved successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f'Error saving Kafka configuration: {e}')
            raise UserError(_('Error saving configuration: %s') % str(e))
    
    def action_test_connection(self):
        """🔌 Test kết nối Kafka với configuration hiện tại"""
        self.ensure_one()
        
        try:
            # 💡 NOTE(assistant): Sử dụng PubSubService để test connection
            pubsub_service = self.env['vnfield.pubsub.service'].create({})
            
            # 🔧 HACK(assistant): Temporarily update parameters for testing
            # Save current values và test với values mới
            self._temporarily_save_config()
            
            # Test connection
            result = pubsub_service.test_kafka_connection()
            
            if result['success']:
                status_message = _(
                    '✅ Connection Successful!\n\n'
                    'Brokers: %s\n'
                    'Topics: %s\n'
                    'Available Topics: %s'
                ) % (
                    result.get('broker_count', 'N/A'),
                    result.get('topic_count', 'N/A'), 
                    ', '.join(result.get('topics', [])[:10])  # Show first 10 topics
                )
                notification_type = 'success'
            else:
                status_message = _('❌ Connection Failed!\n\nError: %s') % result.get('message', 'Unknown error')
                notification_type = 'danger'
            
            # Update status field
            self.connection_status = status_message
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Test'),
                    'message': status_message,
                    'type': notification_type,
                    'sticky': True,
                }
            }
            
        except Exception as e:
            error_message = _('❌ Test Failed!\n\nError: %s') % str(e)
            self.connection_status = error_message
            _logger.error(f'Kafka connection test failed: {e}')
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Test Failed'),
                    'message': error_message,
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def _temporarily_save_config(self):
        """⏰ Temporarily save config for testing"""
        # 🕓 TEMP(assistant): Save config temporarily cho test
        config_param = self.env['ir.config_parameter'].sudo()
        
        temp_params = {
            'kafka.bootstrap_servers': self.bootstrap_servers,
            'kafka.security_protocol': self.security_protocol,
        }
        
        # Only save SASL params if needed
        if self.show_sasl_config:
            temp_params.update({
                'kafka.sasl_mechanism': self.sasl_mechanism,
                'kafka.sasl_username': self.sasl_username or '',
                'kafka.sasl_password': self.sasl_password or '',
            })
        
        # Only save SSL params if needed  
        if self.show_ssl_config:
            temp_params.update({
                'kafka.ssl_ca_location': self.ssl_ca_location or '',
                'kafka.ssl_certificate_location': self.ssl_certificate_location or '',
                'kafka.ssl_key_location': self.ssl_key_location or '',
            })
        
        for param_key, param_value in temp_params.items():
            config_param.set_param(param_key, param_value)
    
    def action_reset_to_defaults(self):
        """🔄 Reset về giá trị mặc định"""
        self.ensure_one()
        
        # 💡 NOTE(assistant): Reset fields to default values
        self.write({
            'bootstrap_servers': 'localhost:9092',
            'security_protocol': 'PLAINTEXT',
            'sasl_mechanism': 'PLAIN',
            'sasl_username': '',
            'sasl_password': '',
            'ssl_ca_location': '',
            'ssl_certificate_location': '',
            'ssl_key_location': '',
            'producer_acks': 'all',
            'producer_retries': 3,
            'producer_batch_size': 16384,
            'producer_linger_ms': 5,
            'consumer_auto_offset_reset': 'earliest',
            'consumer_auto_commit': True,
            'consumer_session_timeout': 30000,
            'consumer_heartbeat_interval': 10000,
            'consumer_max_no_message_retries': 3,
            'consumer_max_total_time_multiplier': 10,
            'connection_status': '',
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reset Complete'),
                'message': _('Configuration reset to default values'),
                'type': 'info',
                'sticky': False,
            }
        }

    # ─────────────────────────────────────────────
    # ▶ Test Pub/Sub Methods
    # ─────────────────────────────────────────────
    
    def _show_notification(self, title, message, notification_type='info', sticky=False):
        """
        📢 Hiển thị notification cho user
        """
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _(title),
                'message': _(message),
                'type': notification_type,
                'sticky': sticky,
            }
        }

    
    def action_test_pubsub(self):
        """
        🧪 Test khả năng Pub/Sub đơn giản với vòng lặp:
        1. Set consumer config để đọc message mới
        2. Publish test message
        3. Loop để consume trong 10s
        4. Nếu consume thành công → thông báo success
        5. Nếu timeout → báo lỗi
        """
        try:
            # ─────────────── 🔄 SETUP TESTING STATE ───────────────
            test_id = f'test_{int(time.time())}'
            
            self.write({
                'test_status': 'testing',
                'test_message': f'Starting pub/sub test with ID: {test_id}',
                'last_test_time': fields.Datetime.now()
            })
            
            
            try:
                # ─────────────── 📤 PUBLISH TEST MESSAGE ───────────────
                test_message = {
                    'test_id': test_id,
                    'wizard_id': self.id,
                    'timestamp': int(time.time()),
                    'message': 'This is a test message for pub/sub functionality'
                }
                
                pubsub_service = self.env['vnfield.pubsub.service'].create({})
                topic = 'vnfield_pubsub_test'
                
                _logger.info(f"📤 About to publish message: {test_message}")
                success = pubsub_service.produce_message(topic, test_message)
                _logger.info(f"📤 Publish result: {success}")
                
                if not success:
                    self.write({
                        'test_status': 'failed',
                        'test_message': 'Failed to publish test message'
                    })
                    return self._show_notification(
                        'Kafka Test Failed',
                        '💥 Could not publish test message. Check Kafka connection.',
                        'danger',
                        True
                    )
                
                # 🔥 Thông báo publish thành công
                self.env['bus.bus']._sendone(
                    'notification_channel',
                    'simple_notification',
                    {
                        'title': 'Message Published',
                        'message': f'📤 Test message sent with ID: {test_id}. Starting consumer...',
                        'type': 'info',
                        'sticky': False
                    }
                )
                
                # ─────────────── 🔄 CONSUME LOOP (No Thread) ───────────────
                unique_group_id = f'test_consumer_{int(time.time())}'
                _logger.info(f"🔥 Starting consumer with unique group: {unique_group_id}")
                _logger.info(f"🔥 This consumer will read from BEGINNING of topic to find all messages")
                
                found_message = False
                start_time = time.time()
                max_wait_time = 30.0  # 10 seconds timeout
                
                while time.time() - start_time < max_wait_time and not found_message:
                    elapsed = time.time() - start_time
                    _logger.info(f"🕐 Consumer loop iteration - elapsed: {elapsed:.1f}s / {max_wait_time}s")
                    
                    # Consume messages với timeout ngắn
                    messages = pubsub_service.consume_messages(
                        topic,
                        group_id=unique_group_id,
                        timeout=1.0,
                        max_messages=10
                    )
                    
                    _logger.info(f"🔄 Consumed {len(messages)} messages in this batch")
                    
                    # Kiểm tra từng message
                    for message in messages:
                        msg_test_id = None
                        if isinstance(message, dict) and isinstance(message.get('value'), dict):
                            msg_test_id = message['value'].get('test_id')
                            
                        _logger.info(f"🔍 Message test_id: '{msg_test_id}' | Expected: '{test_id}'")
                        
                        if msg_test_id == test_id:
                            found_message = True
                            _logger.info(f"✅ Found target message with test_id: {test_id}")
                            break
                        else:
                            _logger.info(f"🔍 NO MATCH: expected='{test_id}' vs msg='{msg_test_id}'")
                    
                    # Ngắt nếu đã tìm thấy
                    if found_message:
                        break
                        
                    # Sleep ngắn trước khi poll tiếp
                    time.sleep(0.2)
                
                # ─────────────── 📋 PROCESS RESULTS ───────────────
                if found_message:
                    # ✅ SUCCESS - Message consumed
                    elapsed_time = round(time.time() - start_time, 2)
                    self.write({
                        'test_status': 'passed',
                        'test_message': f'✅ Test PASSED! Message consumed successfully in {elapsed_time}s.'
                    })
                    
                    return self._show_notification(
                        'Kafka Test Passed',
                        f'🎉 Pub/Sub Test PASSED! Message consumed successfully in {elapsed_time}s.',
                        'success',
                        True
                    )
                else:
                    # ❌ TIMEOUT - No message received
                    self.write({
                        'test_status': 'timeout',
                        'test_message': '❌ Test TIMEOUT! No message consumed within 10 seconds.'
                    })
                    
                    return self._show_notification(
                        'Kafka Test Timeout',
                        '💥 Pub/Sub Test FAILED! TIMEOUT after 10 seconds - no message consumed.',
                        'danger',
                        True
                    )
                
            finally:
                pass
            
        except Exception as e:
            _logger.error(f"Error in test_pubsub: {str(e)}")
            self.write({
                'test_status': 'failed',
                'test_message': f'Error during test: {str(e)}'
            })
            return self._show_notification(
                'Kafka Test Error',
                f'💥 Test failed with error: {str(e)}',
                'danger',
                True
            )
    
    
# ─────────────────────────────────────────────
# ▶ Dependencies và Symbol Relationships
# ─────────────────────────────────────────────

"""
🔗 Phụ thuộc của các symbols trong file này:

1. **SystemConfigWizard class**:
   - Kế thừa từ: models.TransientModel (Odoo core)
   - Phụ thuộc: ir.config_parameter model để lưu/đọc system parameters
   - Sử dụng: vnfield.pubsub.service để test connection
   - Logger: _logger để ghi log

2. **Fields**:
   - 16 fields tương ứng với 16 system parameters
   - Computed fields: show_sasl_config, show_ssl_config
   - Status field: connection_status

3. **default_get method**:
   - Load current values từ ir.config_parameter
   - Type conversion cho integer và boolean fields

4. **action_save_configuration method**:
   - Save tất cả fields vào system parameters
   - Notification success/error

5. **action_test_connection method**:
   - Sử dụng vnfield.pubsub.service.test_kafka_connection()
   - Temporarily save config để test
   - Update connection_status field

6. **Validation constraints**:
   - _check_producer_retries, _check_producer_batch_size
   - _check_consumer_timeouts
   - Ensure heartbeat < session timeout

Mapping giữa wizard fields và system parameters:
- bootstrap_servers → kafka.bootstrap_servers
- security_protocol → kafka.security_protocol  
- sasl_* → kafka.sasl_*
- ssl_* → kafka.ssl_*
- producer_* → kafka.producer_*
- consumer_* → kafka.consumer_*
"""
