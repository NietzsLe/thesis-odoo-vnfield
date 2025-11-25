# Team-Project State Mapping Documentation

## Project States (vnfield.project)

```python
state = fields.Selection([
    ('draft', 'Draft'),
    ('planning', 'Planning'),
    ('in_progress', 'In Progress'),
    ('on_hold', 'On Hold'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled')
], ...)
```

## Team Auto State Mapping

| Project State | Team Auto State | Description                                   |
| ------------- | --------------- | --------------------------------------------- |
| `draft`       | `inactive`      | Team chưa hoạt động khi project còn draft     |
| `planning`    | `inactive`      | Team chưa hoạt động trong giai đoạn planning  |
| `in_progress` | `active`        | **Team hoạt động** khi project đang tiến hành |
| `on_hold`     | `inactive`      | Team tạm dừng khi project bị hold             |
| `completed`   | `inactive`      | Team ngừng hoạt động khi project hoàn thành   |
| `cancelled`   | `disbanded`     | **Team giải tán** khi project bị hủy          |

## Business Logic

### Active Team Conditions

- Team chỉ `active` khi project ở trạng thái `in_progress`
- Tất cả trạng thái khác của project đều làm team `inactive`
- Chỉ có `cancelled` project làm team `disbanded`

### Lifecycle Management

1. **Auto Sync**: Cron job chạy hàng ngày sync team states
2. **Manual Sync**: Button "Sync with Project" trong form
3. **Force Disband**: Method để force disband từ project model
4. **Message Logging**: Tất cả state changes đều được log

### State Priorities

- `disbanded` > `active` > `inactive` > `draft`
- Một khi team `disbanded` thì không thể activate lại
- Team có thể manual override auto_state nếu cần thiết

### Integration Points

- Project model có thể call `team.force_disband_from_project()`
- Cron job `cron_sync_team_lifecycle()` chạy định kỳ
- Computed field `auto_state` realtime update theo project

## Code References

- **Model**: `features/organization/models/team.py`
- **Views**: `features/organization/views/team_views.xml`
- **Cron**: `features/organization/data/team_cron.xml`
- **Method**: `_compute_auto_state()` line ~213
