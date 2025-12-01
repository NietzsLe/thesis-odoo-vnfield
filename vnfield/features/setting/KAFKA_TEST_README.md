# 🧪 Kafka Pub/Sub Test System

## 📋 Overview

Chức năng test pub/sub cho phép kiểm tra khả năng gửi và nhận message của hệ thống Kafka một cách tự động với timeout 5 giây.

## 🔧 How It Works

### 1. Test Flow

```
[User clicks Test] → [Publish Message] → [Create Cron Jobs] → [Consume Message] → [Report Result]
                                              ↓
                                         [Timeout Timer (5s)]
```

### 2. Components

#### 🎯 Test Button (`action_test_pubsub`)

- Gửi test message đến topic `vnfield_pubsub_test`
- Message chứa unique `test_id` và timestamp
- Tạo 2 cron jobs: consumer và timeout

#### ⏰ Cron Jobs

1. **Consumer Cron**: Chạy ngay để consume messages
2. **Timeout Cron**: Chạy sau 5s để handle timeout

#### 📥 Consumer Logic (`_consume_test_message`)

- Retry 10 lần, mỗi lần 500ms (tổng 5s)
- Tìm message với matching `test_id`
- Update status: `passed` nếu tìm thấy, `failed` nếu không

#### ⏱️ Timeout Handler (`_timeout_test`)

- Chạy sau 5s để cleanup cron jobs
- Set status `timeout` nếu test vẫn đang chạy

## 🎨 UI Features

### Status Display

```
🧪 Pub/Sub Test Status
┌─────────────────────────────────────┐
│ Status: [Testing...] [🟡]           │
│ Last Test: 2024-08-13 15:30:00      │
│ Result: Starting pub/sub test...     │
└─────────────────────────────────────┘
```

### Status Colors

- 🟢 **Green**: Test Passed
- 🟡 **Yellow**: Testing in Progress
- 🔴 **Red**: Test Failed/Timeout

## 📊 Test Results

### Success Case

```
✅ Test PASSED! Message with test_id "test_2024-08-13T15:30:00" consumed successfully after 3 attempts.
```

### Failure Case

```
❌ Test FAILED! Message with test_id "test_2024-08-13T15:30:00" not found after consuming 15 messages.
```

### Timeout Case

```
⏱️ Test TIMEOUT! No message with test_id "test_2024-08-13T15:30:00" consumed within 5 seconds.
```

## 🔧 Configuration

### System Parameters

- `kafka.test_topic`: Topic name for testing (default: `vnfield_pubsub_test`)
- `kafka.test_timeout_seconds`: Timeout in seconds (default: `5`)
- `kafka.test_consumer_group`: Consumer group for testing

### Test Message Format

```json
{
  "test_id": "test_2024-08-13T15:30:00.123456",
  "wizard_id": 123,
  "timestamp": "2024-08-13T15:30:00.123456",
  "message": "This is a test message for pub/sub functionality"
}
```

## 🚀 Usage

1. Navigate to **VN Field Settings → System Configuration → Kafka Configuration**
2. Configure Kafka connection settings
3. Click **🧪 Test Pub/Sub** button
4. Wait for result (max 5 seconds)
5. Check test status and message

## 🔍 Troubleshooting

### Common Issues

#### 1. Test Always Times Out

- Check Kafka broker is running
- Verify bootstrap servers configuration
- Check network connectivity

#### 2. Messages Not Consumed

- Verify consumer group configuration
- Check topic exists and permissions
- Review Kafka logs

#### 3. Cron Jobs Not Working

- Check cron service is enabled in Odoo
- Verify model permissions
- Review system logs

### Debug Info

- Check logs in `_logger` with prefix `Kafka Test`
- Monitor cron job execution in Settings → Technical → Automation → Scheduled Actions
- Use Kafka tools to verify topic and messages

## 🎯 Best Practices

1. **Run test after configuration changes**
2. **Wait for previous test to complete**
3. **Check Kafka broker status before testing**
4. **Monitor system resources during test**
5. **Clean up failed cron jobs periodically**

## 🔮 Future Enhancements

- [ ] Batch message testing
- [ ] Performance benchmarking
- [ ] Multiple consumer group testing
- [ ] Message ordering validation
- [ ] Error injection testing
