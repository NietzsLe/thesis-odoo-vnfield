# -*- coding: utf-8 -*-

# ===========================================
# =           📡 PUBSUB SERVICE              =
# ===========================================

"""
┌────────────────────────────────────────────┐
│    🧰 CHỨC NĂNG: KAFKA PUBSUB SERVICE       │
│                                            │
│ - Quản lý producer và consumer Kafka       │
│ - Sử dụng system parameter cho cấu hình    │
│ - Dựa trên TransientModel cho tính tạm thời│
└────────────────────────────────────────────┘
"""

import logging
import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError

# 💡 NOTE(assistant): Import confluent_kafka để xử lý Kafka
try:
    from confluent_kafka import Producer, Consumer, KafkaException, KafkaError
except ImportError:
    Producer = Consumer = KafkaException = KafkaError = None

_logger = logging.getLogger(__name__)


class PubSubService(models.TransientModel):
    """
    🔄 PubSub Service cho Kafka
    
    Service này cung cấp khả năng:
    - Produce messages đến Kafka topics
    - Consume messages từ Kafka topics  
    - Quản lý cấu hình thông qua system parameters
    """
    
    _name = 'vnfield.pubsub.service'
    _description = 'Kafka PubSub Service'

    # ─────────────────────────────────────────────
    # ▶ Cấu hình và khởi tạo
    # ─────────────────────────────────────────────
    
    def _get_kafka_config(self):
        """
        🔧 Lấy cấu hình Kafka từ system parameters
        
        Returns:
            dict: Dictionary chứa cấu hình Kafka
        """
        # 💡 NOTE(assistant): Lấy các system parameter cho cấu hình Kafka
        config = {}
        
        # Bootstrap servers - required
        bootstrap_servers = self.env['ir.config_parameter'].sudo().get_param(
            'kafka.bootstrap_servers', 'localhost:9092'
        )
        config['bootstrap.servers'] = bootstrap_servers
        
        # Security protocol
        security_protocol = self.env['ir.config_parameter'].sudo().get_param(
            'kafka.security_protocol', 'PLAINTEXT'
        )
        config['security.protocol'] = security_protocol
        
        # SASL mechanism (if using SASL)
        if security_protocol in ['SASL_PLAINTEXT', 'SASL_SSL']:
            sasl_mechanism = self.env['ir.config_parameter'].sudo().get_param(
                'kafka.sasl_mechanism', 'PLAIN'
            )
            config['sasl.mechanism'] = sasl_mechanism
            
            sasl_username = self.env['ir.config_parameter'].sudo().get_param(
                'kafka.sasl_username', ''
            )
            if sasl_username:
                config['sasl.username'] = sasl_username
                
            sasl_password = self.env['ir.config_parameter'].sudo().get_param(
                'kafka.sasl_password', ''
            )
            if sasl_password:
                config['sasl.password'] = sasl_password
        
        # SSL configuration (if using SSL)
        if security_protocol in ['SSL', 'SASL_SSL']:
            ssl_ca_location = self.env['ir.config_parameter'].sudo().get_param(
                'kafka.ssl_ca_location', ''
            )
            if ssl_ca_location:
                config['ssl.ca.location'] = ssl_ca_location
                
            ssl_certificate_location = self.env['ir.config_parameter'].sudo().get_param(
                'kafka.ssl_certificate_location', ''
            )
            if ssl_certificate_location:
                config['ssl.certificate.location'] = ssl_certificate_location
                
            ssl_key_location = self.env['ir.config_parameter'].sudo().get_param(
                'kafka.ssl_key_location', ''
            )
            if ssl_key_location:
                config['ssl.key.location'] = ssl_key_location
        
        # 🧪 Ví dụ cấu hình:
        # config = {
        #     'bootstrap.servers': 'localhost:9092',
        #     'security.protocol': 'PLAINTEXT'
        # }
        
        return config

    def _check_kafka_availability(self):
        """
        ✅ Kiểm tra tính khả dụng của Kafka
        
        Raises:
            UserError: Nếu confluent_kafka không được cài đặt
        """
        if not Producer or not Consumer:
            raise UserError(_(
                "confluent_kafka library is not installed. "
                "Please install it using: pip install confluent-kafka"
            ))

    # ─────────────────────────────────────────────
    # ▶ Producer Methods  
    # ─────────────────────────────────────────────

    def produce_message(self, topic, message, key=None, headers=None):
        """
        📤 Gửi message đến Kafka topic
        
        Args:
            topic (str): Tên topic để gửi message
            message (str|dict): Nội dung message (sẽ được serialize)
            key (str, optional): Key cho message
            headers (dict, optional): Headers cho message
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        # 🔍 REVIEW(user): Kiểm tra tính khả dụng của Kafka
        self._check_kafka_availability()
        
        try:
            # Lấy cấu hình Kafka
            config = self._get_kafka_config()
            
            # 💡 NOTE(assistant): Thêm cấu hình producer specific
            producer_config = config.copy()
            producer_config.update({
                'acks': self.env['ir.config_parameter'].sudo().get_param(
                    'kafka.producer_acks', 'all'
                ),
                'retries': int(self.env['ir.config_parameter'].sudo().get_param(
                    'kafka.producer_retries', '3'
                )),
                'batch.size': int(self.env['ir.config_parameter'].sudo().get_param(
                    'kafka.producer_batch_size', '16384'
                )),
                'linger.ms': int(self.env['ir.config_parameter'].sudo().get_param(
                    'kafka.producer_linger_ms', '5'
                )),
            })
            
            # Tạo Producer instance
            producer = Producer(producer_config)
            
            # 🔁 Serialize message nếu là dict
            if isinstance(message, dict):
                message = json.dumps(message, ensure_ascii=False)
            
            # Encode message thành bytes
            if isinstance(message, str):
                message = message.encode('utf-8')
                
            # Encode key nếu có
            if key and isinstance(key, str):
                key = key.encode('utf-8')
            
            # Delivery report callback
            def delivery_report(err, msg):
                """
                📊 Callback được gọi khi message được deliver hoặc fail
                """
                if err is not None:
                    _logger.error(f'Message delivery failed: {err}')
                else:
                    _logger.info(f'Message delivered to {msg.topic()} [{msg.partition()}]')
            
            # 🚀 Produce message
            producer.produce(
                topic=topic,
                value=message,
                key=key,
                headers=headers,
                callback=delivery_report
            )
            
            # 📝 TODO(user): Có thể thêm timeout configuration
            producer.flush(timeout=10)  # Wait tối đa 10 giây
            
            _logger.info(f'Successfully produced message to topic: {topic}')
            return True
            
        except KafkaException as e:
            _logger.error(f'Kafka error when producing message: {e}')
            raise UserError(_('Kafka error: %s') % str(e))
        except Exception as e:
            _logger.error(f'Error producing message: {e}')
            raise UserError(_('Error producing message: %s') % str(e))
    # ─────────────────────────────────────────────
    # ▶ Consumer Methods
    # ─────────────────────────────────────────────

    def consume_messages(self, topics, group_id=None, timeout=1.0, max_messages=10, message_handler=None):
        """
        📥 Consume messages từ Kafka topics
        
        Args:
            topics (list): Danh sách topics để subscribe
            group_id (str, optional): Consumer group ID
            timeout (float): Timeout cho mỗi poll (seconds)
            max_messages (int): Số lượng message tối đa để consume
            message_handler (callable, optional): Function để xử lý từng message
                Signature: handler(headers, value, message_info) -> processed_value
                - headers (dict): Message headers
                - value (any): Message value (đã decode và parse JSON nếu có thể)
                - message_info (dict): Thông tin metadata của message
                - Returns: Giá trị đã xử lý hoặc None để bỏ qua message
            
        Returns:
            list: Danh sách messages đã consume (và đã xử lý nếu có handler)
        """
        # 🔍 REVIEW(user): Kiểm tra tính khả dụng của Kafka
        self._check_kafka_availability()
        
        if not topics:
            raise UserError(_('Topics list cannot be empty'))
            
        if not isinstance(topics, list):
            topics = [topics]
            
        try:
            # Lấy cấu hình Kafka
            config = self._get_kafka_config()
            
            # 💡 NOTE(assistant): Thêm cấu hình consumer specific
            consumer_config = config.copy()
            
            # Group ID - mặc định sử dụng database name + timestamp
            if not group_id:
                group_id = f"odoo_{self.env.cr.dbname}_{self.env.context.get('uid', 'system')}"
            
            consumer_config.update({
                'group.id': group_id,
                'auto.offset.reset': self.env['ir.config_parameter'].sudo().get_param(
                    'kafka.consumer_auto_offset_reset', 'earliest'
                ),
                'enable.auto.commit': self.env['ir.config_parameter'].sudo().get_param(
                    'kafka.consumer_auto_commit', 'true'
                ).lower() == 'true',
                'session.timeout.ms': int(self.env['ir.config_parameter'].sudo().get_param(
                    'kafka.consumer_session_timeout', '30000'
                )),
                'heartbeat.interval.ms': int(self.env['ir.config_parameter'].sudo().get_param(
                    'kafka.consumer_heartbeat_interval', '10000'
                )),
            })
            
            # Tạo Consumer instance
            consumer = Consumer(consumer_config)
            
            # Subscribe to topics
            consumer.subscribe(topics)
            _logger.info(f'Consumer subscribed to topics: {topics} with group: {group_id}')
            _logger.info(f'Consumer config - offset reset: {consumer_config.get("auto.offset.reset", "unknown")}')
            
            messages = []
            consumed_count = 0
            
            _logger.info(f'Starting to consume from topics: {topics}')
            
            # 🔁 Loop để consume messages với retry logic
            try:
                import time
                start_time = time.time()
                
                # 📝 Load timeout configs from system parameters
                max_total_time_multiplier = int(self.env['ir.config_parameter'].sudo().get_param(
                    'kafka.consumer_max_total_time_multiplier', '10'
                ))
                max_total_time = timeout * max_total_time_multiplier  # Maximum total time to spend consuming
                
                no_message_count = 0
                max_no_message_retries = int(self.env['ir.config_parameter'].sudo().get_param(
                    'kafka.consumer_max_no_message_retries', '3'
                ))  # Retry X times when no message
                
                while consumed_count < max_messages and (time.time() - start_time) < max_total_time:
                    msg = consumer.poll(timeout=timeout)
                    
                    if msg is None:
                        # No message received - retry a few times before giving up
                        no_message_count += 1
                        _logger.debug(f'No message received (attempt {no_message_count}/{max_no_message_retries})')
                        
                        if no_message_count >= max_no_message_retries:
                            _logger.debug('Max retries reached, stopping consume...')
                            break
                        continue  # Try again
                        
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            # End of partition - không phải lỗi thật
                            _logger.debug(f'End of partition reached: {msg.topic()}[{msg.partition()}]')
                            continue
                        else:
                            # Lỗi thực sự
                            _logger.error(f'Consumer error: {msg.error()}')
                            raise KafkaException(msg.error())
                    
                    # 📨 Process message thành công
                    try:
                        # Reset no message counter khi có message
                        no_message_count = 0
                        
                        # Decode message
                        value = msg.value().decode('utf-8') if msg.value() else None
                        key = msg.key().decode('utf-8') if msg.key() else None
                        
                        # Thử parse JSON nếu có thể
                        try:
                            if value:
                                value = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            # Giữ nguyên string nếu không parse được JSON
                            pass
                        
                        # 🏗️ Prepare headers dictionary
                        headers = dict(msg.headers()) if msg.headers() else {}
                        
                        # 📊 Prepare message metadata
                        message_info = {
                            'topic': msg.topic(),
                            'partition': msg.partition(),
                            'offset': msg.offset(),
                            'key': key,
                            'timestamp': msg.timestamp()
                        }
                        
                        # 🔧 Call message handler if provided
                        processed_value = value  # Default: keep original value
                        handler_success = True
                        
                        if message_handler and callable(message_handler):
                            try:
                                # 🎯 Call user-provided handler function
                                _logger.debug(f'Calling message handler for message from {msg.topic()}[{msg.partition()}] offset {msg.offset()}')
                                
                                # Handler signature: handler(headers, value, message_info) -> processed_value
                                processed_result = message_handler(headers, value)
                                
                                # 💡 NOTE(assistant): Handler có thể return None để bỏ qua message
                                if processed_result is None:
                                    _logger.debug(f'Message handler returned None, skipping message from {msg.topic()}[{msg.partition()}] offset {msg.offset()}')
                                    continue  # Skip this message
                                
                                processed_value = processed_result
                                _logger.debug(f'Message handler processed successfully for {msg.topic()}[{msg.partition()}] offset {msg.offset()}')
                                
                            except Exception as handler_error:
                                # 🐞 FIXME(assistant): Handler error - có thể chọn skip hoặc keep original
                                _logger.error(f'Message handler error for {msg.topic()}[{msg.partition()}] offset {msg.offset()}: {handler_error}')
                                
                                # 📝 TODO(user): Có thể thêm option để quyết định có skip message khi handler lỗi
                                # Mặc định: giữ nguyên giá trị gốc và tiếp tục
                                processed_value = value
                                handler_success = False
                        
                        # 📦 Build final message data
                        message_data = {
                            'topic': msg.topic(),
                            'partition': msg.partition(),
                            'offset': msg.offset(),
                            'key': key,
                            'value': processed_value,  # Use processed value instead of original
                            'original_value': value,   # Keep original value for reference
                            'timestamp': msg.timestamp(),
                            'headers': headers,
                            'handler_applied': message_handler is not None,
                            'handler_success': handler_success
                        }
                        
                        messages.append(message_data)
                        consumed_count += 1
                        
                        # 📝 Log message với nội dung trong 1 dòng
                        content_preview = str(processed_value)[:100] + "..." if len(str(processed_value)) > 100 else str(processed_value)
                        handler_status = " [HANDLER_APPLIED]" if message_handler else ""
                        handler_status += " [HANDLER_ERROR]" if message_handler and not handler_success else ""
                        _logger.info(f'Consumed message from {msg.topic()}[{msg.partition()}] offset {msg.offset()}{handler_status} | Content: {content_preview}')
                        
                    except Exception as decode_error:
                        _logger.error(f'Error decoding message: {decode_error}')
                        # Continue với message tiếp theo
                        continue
                        
            finally:
                # 🧹 Cleanup: Close consumer
                consumer.close()
                
            _logger.info(f'Successfully consumed {len(messages)} messages')
            return messages
            
        except KafkaException as e:
            _logger.error(f'Kafka error when consuming messages: {e}')
            raise UserError(_('Kafka error: %s') % str(e))
        except Exception as e:
            _logger.error(f'Error consuming messages: {e}')
            raise UserError(_('Error consuming messages: %s') % str(e))

    # ─────────────────────────────────────────────
    # ▶ Utility Methods
    # ─────────────────────────────────────────────

    @api.model
    def test_kafka_connection(self):
        """
        🔌 Test kết nối đến Kafka cluster
        
        Returns:
            dict: Kết quả test connection
        """
        try:
            self._check_kafka_availability()
            config = self._get_kafka_config()
            
            # Tạo AdminClient để test connection
            from confluent_kafka.admin import AdminClient
            
            admin_client = AdminClient(config)
            
            # 📝 TODO(user): Thêm timeout configuration cho metadata
            metadata = admin_client.list_topics(timeout=10)
            
            return {
                'success': True,
                'message': _('Successfully connected to Kafka'),
                'broker_count': len(metadata.brokers),
                'topic_count': len(metadata.topics),
                'topics': list(metadata.topics.keys())
            }
            
        except Exception as e:
            _logger.error(f'Kafka connection test failed: {e}')
            return {
                'success': False,
                'message': _('Failed to connect to Kafka: %s') % str(e),
                'error': str(e)
            }

    # ─────────────────────────────────────────────
    # ▶ Message Handler Utilities
    # ─────────────────────────────────────────────

    @api.model
    def create_simple_handler(self, processing_func=None, filter_func=None):
        """
        🛠️ Tạo message handler đơn giản với processing và filtering
        
        Args:
            processing_func (callable, optional): Function để xử lý value
                Signature: func(value) -> processed_value
            filter_func (callable, optional): Function để filter message
                Signature: func(headers, value, message_info) -> bool
                Return True để keep message, False để skip
                
        Returns:
            callable: Message handler function
        """
        def handler(headers, value, message_info):
            """
            🔧 Generated message handler
            """
            try:
                # 🔍 Apply filter if provided
                if filter_func and callable(filter_func):
                    if not filter_func(headers, value, message_info):
                        # Filter says to skip this message
                        return None
                
                # 🔄 Apply processing if provided
                if processing_func and callable(processing_func):
                    return processing_func(value)
                
                # 📝 No processing, return original value
                return value
                
            except Exception as e:
                _logger.error(f'Error in simple handler: {e}')
                # Return original value on error
                return value
        
        return handler

    @api.model
    def create_json_validator_handler(self, required_fields=None, schema_validator=None):
        """
        ✅ Tạo message handler để validate JSON schema
        
        Args:
            required_fields (list, optional): Danh sách fields bắt buộc
            schema_validator (callable, optional): Function để validate schema
                Signature: func(json_data) -> bool
                
        Returns:
            callable: Message handler function
        """
        def handler(headers, value, message_info):
            """
            ✅ JSON validation message handler
            """
            try:
                # 🔍 Check if value is dict (JSON parsed)
                if not isinstance(value, dict):
                    _logger.warning(f'Message value is not JSON dict, skipping validation: {type(value)}')
                    return value
                
                # ✅ Check required fields
                if required_fields:
                    missing_fields = [field for field in required_fields if field not in value]
                    if missing_fields:
                        _logger.warning(f'Message missing required fields {missing_fields}, skipping')
                        return None  # Skip message
                
                # 🔧 Apply custom schema validator
                if schema_validator and callable(schema_validator):
                    if not schema_validator(value):
                        _logger.warning(f'Message failed schema validation, skipping')
                        return None  # Skip message
                
                # ✅ Validation passed
                return value
                
            except Exception as e:
                _logger.error(f'Error in JSON validator handler: {e}')
                return None  # Skip on error
        
        return handler

    @api.model
    def create_transform_handler(self, field_mapping=None, add_metadata=False):
        """
        🔄 Tạo message handler để transform data structure
        
        Args:
            field_mapping (dict, optional): Mapping old_field -> new_field
            add_metadata (bool): Có thêm metadata vào message không
                
        Returns:
            callable: Message handler function
        """
        def handler(headers, value, message_info):
            """
            🔄 Transform message handler
            """
            try:
                result = value
                
                # 🗺️ Apply field mapping if provided
                if field_mapping and isinstance(value, dict):
                    result = {}
                    for old_field, new_field in field_mapping.items():
                        if old_field in value:
                            result[new_field] = value[old_field]
                    
                    # 📝 Keep unmapped fields
                    for field, val in value.items():
                        if field not in field_mapping and field not in result:
                            result[field] = val
                
                # 📊 Add metadata if requested
                if add_metadata:
                    if isinstance(result, dict):
                        result['_kafka_metadata'] = {
                            'topic': message_info['topic'],
                            'partition': message_info['partition'],
                            'offset': message_info['offset'],
                            'timestamp': message_info['timestamp'],
                            'headers': headers
                        }
                    else:
                        # 📦 Wrap non-dict values
                        result = {
                            'data': result,
                            '_kafka_metadata': {
                                'topic': message_info['topic'],
                                'partition': message_info['partition'],
                                'offset': message_info['offset'],
                                'timestamp': message_info['timestamp'],
                                'headers': headers
                            }
                        }
                
                return result
                
            except Exception as e:
                _logger.error(f'Error in transform handler: {e}')
                return value  # Return original on error
        
        return handler

# ─────────────────────────────────────────────
# ▶ Dependencies và Symbol Relationships
# ─────────────────────────────────────────────

"""
🔗 Phụ thuộc của các symbols trong file này:

1. **PubSubService class**:
   - Kế thừa từ: models.TransientModel (Odoo core)
   - Phụ thuộc: confluent_kafka (Producer, Consumer, KafkaException)
   - Sử dụng: ir.config_parameter model để lấy system parameters
   - Logger: _logger để ghi log

2. **_get_kafka_config method**:
   - Phụ thuộc: self.env['ir.config_parameter'] 
   - Trả về: dict configuration cho Kafka client

3. **produce_message method**:
   - Phụ thuộc: _get_kafka_config(), _check_kafka_availability()
   - Sử dụng: confluent_kafka.Producer
   - Callback: delivery_report function

4. **consume_messages method**:
   - Phụ thuộc: _get_kafka_config(), _check_kafka_availability()  
   - Sử dụng: confluent_kafka.Consumer
   - Xử lý: JSON serialization/deserialization
   - ENHANCED: Hỗ trợ message_handler callback với signature:
     handler(headers, value, message_info) -> processed_value
   - Handler có thể return None để skip message
   - Tracking: handler_applied và handler_success trong message data

5. **test_kafka_connection method**:
   - Phụ thuộc: _get_kafka_config(), _check_kafka_availability()
   - Sử dụng: confluent_kafka.admin.AdminClient
   - Mục đích: Health check cho Kafka cluster

6. **Message Handler Utilities**:
   - create_simple_handler(): Tạo handler với processing và filtering
   - create_json_validator_handler(): Validate JSON schema và required fields
   - create_transform_handler(): Transform data structure và add metadata
   - Tất cả handlers follow signature: handler(headers, value, message_info) -> processed_value

Các system parameters được sử dụng:
- kafka.bootstrap_servers: Địa chỉ Kafka brokers
- kafka.security_protocol: Giao thức bảo mật  
- kafka.sasl_*: Cấu hình SASL authentication
- kafka.ssl_*: Cấu hình SSL/TLS
- kafka.producer_*: Cấu hình producer
- kafka.consumer_*: Cấu hình consumer

Message Handler Pattern:
- Input: (headers: dict, value: any, message_info: dict)
- Output: processed_value (any type) hoặc None để skip
- Error handling: Return original value or None tùy handler logic
- Metadata: topic, partition, offset, timestamp, key
"""
