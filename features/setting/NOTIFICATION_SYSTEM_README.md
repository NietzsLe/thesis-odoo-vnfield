# 🔔 Kafka Test Notification System

## 📋 Overview

Hệ thống thông báo cho Kafka Pub/Sub test sử dụng **Odoo Display Notification System** để gửi thông báo trực tiếp đến user interface như Connection Test.

## 🚀 Features

### 1. **Display Notifications**

- Sử dụng `display_notification` client action
- Thông báo popup trực tiếp trên UI
- Support multiple notification types và sticky options

### 2. **Notification Types**

```
🎉 Success (Green) - Test passed
⚠️  Warning (Yellow) - Test timeout
💥 Danger (Red) - Test failed/error
ℹ️  Info (Blue) - Test started
```

### 3. **Sticky vs Non-sticky**

- **Sticky**: Thông báo quan trọng (lỗi, timeout) - cần user dismiss
- **Non-sticky**: Thông báo thông thường (start, success) - tự động disappear

## 🔧 Implementation Details

### Display Notification Method

```python
def _show_notification(self, title, message, notification_type='info', sticky=False):
    """📢 Hiển thị notification cho user"""
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
```

### Notification Timeline

```
[Test Start] → Info notification (non-sticky) → Return to UI
     ↓
[Processing] → (Background cron jobs handle consume & timeout)
     ↓
[Result] → Success/Danger/Warning notification (try/catch for cron context)
```

## 📊 Notification Examples

### 1. **Test Started**

```
Type: info (blue, non-sticky)
Title: "Kafka Test Started"
Message: "🚀 Test message published. Waiting for result (5s timeout)..."
```

### 2. **Test Passed**

```
Type: success (green, non-sticky)
Title: "Kafka Test Result"
Message: "🎉 Pub/Sub Test PASSED! Message consumed successfully."
```

### 3. **Test Failed**

```
Type: danger (red, sticky)
Title: "Kafka Test Result"
Message: "💥 Pub/Sub Test FAILED! Message not found or consumed."
```

### 4. **Test Timeout**

```
Type: warning (yellow, sticky)
Title: "Kafka Test Timeout"
Message: "⏱️ Pub/Sub Test TIMEOUT! No response within 5 seconds."
```

### 5. **Test Error**

```
Type: danger (red, sticky)
Title: "Kafka Test Error"
Message: "💥 Test Error: [error details]"
```

## 🎯 User Experience

### Visual Feedback

1. **Click Test Button** → Immediate "Test Started" notification
2. **Status Updated** → UI shows "Testing..." with spinner
3. **Result Available** → Success/Failure notification appears
4. **Status Display** → Detailed result in test status section

### Notification Behavior

- **Success**: Green toast, disappears after 3s
- **Info**: Blue toast, disappears after 3s
- **Warning/Error**: Red/Yellow toast, stays until dismissed

## 🔍 Debugging

### Test Notification Button

- Added `action_test_notification()` method
- Creates test notification to verify bus system
- Use for debugging notification issues

### Troubleshooting

1. **No notifications appearing**:

   - Check bus.bus service is running
   - Verify user permissions
   - Check browser console for errors

2. **Notifications not real-time**:
   - Check long-polling connection
   - Verify bus.bus configuration
   - Check network connectivity

## 🔮 Benefits

1. **Immediate Feedback**: User knows test started instantly
2. **No Page Refresh**: Real-time updates via bus system
3. **Visual Clarity**: Color-coded notifications for different states
4. **Professional UX**: Modern notification system like other enterprise apps
5. **Error Visibility**: Sticky error notifications ensure user sees issues

## 📝 Code Locations

- **Notification Logic**: `kafka_config_wizard.py` → `_send_bus_notification()`
- **Test Methods**: All test-related methods send appropriate notifications
- **UI Integration**: Notifications appear automatically in Odoo's notification area
- **Debug Button**: `action_test_notification()` for testing notification system
