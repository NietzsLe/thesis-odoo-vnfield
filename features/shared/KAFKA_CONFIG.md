# Kafka Configuration Guide

## System Parameters cho PubSubService

Để sử dụng PubSubService, bạn cần cấu hình các system parameters sau trong Odoo:

### 🔧 Cấu hình cơ bản

| Parameter                 | Mô tả                 | Giá trị mặc định | Ví dụ                                            |
| ------------------------- | --------------------- | ---------------- | ------------------------------------------------ |
| `kafka.bootstrap_servers` | Địa chỉ Kafka brokers | `localhost:9092` | `kafka1:9092,kafka2:9092`                        |
| `kafka.security_protocol` | Giao thức bảo mật     | `PLAINTEXT`      | `PLAINTEXT`, `SSL`, `SASL_PLAINTEXT`, `SASL_SSL` |

### 🔐 Cấu hình SASL Authentication

| Parameter              | Mô tả             | Giá trị mặc định |
| ---------------------- | ----------------- | ---------------- |
| `kafka.sasl_mechanism` | Cơ chế SASL       | `PLAIN`          |
| `kafka.sasl_username`  | Username cho SASL | -                |
| `kafka.sasl_password`  | Password cho SASL | -                |

### 🛡️ Cấu hình SSL/TLS

| Parameter                        | Mô tả                        | Giá trị mặc định |
| -------------------------------- | ---------------------------- | ---------------- |
| `kafka.ssl_ca_location`          | Đường dẫn CA certificate     | -                |
| `kafka.ssl_certificate_location` | Đường dẫn client certificate | -                |
| `kafka.ssl_key_location`         | Đường dẫn private key        | -                |

### 📤 Cấu hình Producer

| Parameter                   | Mô tả                | Giá trị mặc định |
| --------------------------- | -------------------- | ---------------- |
| `kafka.producer_acks`       | Acknowledgment level | `all`            |
| `kafka.producer_retries`    | Số lần retry         | `3`              |
| `kafka.producer_batch_size` | Kích thước batch     | `16384`          |
| `kafka.producer_linger_ms`  | Thời gian chờ batch  | `5`              |

### 📥 Cấu hình Consumer

| Parameter                           | Mô tả                   | Giá trị mặc định |
| ----------------------------------- | ----------------------- | ---------------- |
| `kafka.consumer_auto_offset_reset`  | Reset offset strategy   | `earliest`       |
| `kafka.consumer_auto_commit`        | Auto commit offset      | `true`           |
| `kafka.consumer_session_timeout`    | Session timeout (ms)    | `30000`          |
| `kafka.consumer_heartbeat_interval` | Heartbeat interval (ms) | `10000`          |

## 📝 Cách thiết lập trong Odoo

1. Đi đến **Settings > Technical > Parameters > System Parameters**
2. Tạo các record mới với Key và Value tương ứng
3. Ví dụ:
   - Key: `kafka.bootstrap_servers`
   - Value: `localhost:9092`

## 🧪 Ví dụ sử dụng

### Producer

```python
# Trong controller hoặc model khác
pubsub_service = self.env['vnfield.pubsub.service'].create({})

# Gửi message
success = pubsub_service.produce_message(
    topic='user_events',
    message={'user_id': 123, 'action': 'login'},
    key='user_123'
)
```

### Consumer

```python
# Consume messages
messages = pubsub_service.consume_messages(
    topics=['user_events', 'system_events'],
    group_id='odoo_consumer_group',
    max_messages=50
)

for msg in messages:
    print(f"Topic: {msg['topic']}, Value: {msg['value']}")
```

### Test Connection

```python
# Test kết nối
result = pubsub_service.test_kafka_connection()
if result['success']:
    print("Kafka connection OK")
else:
    print(f"Connection failed: {result['message']}")
```

## 🚀 Installation Requirements

```bash
pip install confluent-kafka
```

## 🔍 Troubleshooting

1. **Import Error**: Đảm bảo `confluent-kafka` đã được cài đặt
2. **Connection Failed**: Kiểm tra `kafka.bootstrap_servers` và network
3. **Authentication Failed**: Kiểm tra SASL/SSL configuration
4. **Permission Denied**: Kiểm tra topic permissions và ACLs
