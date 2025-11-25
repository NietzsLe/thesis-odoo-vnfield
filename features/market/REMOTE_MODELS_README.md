# 🔗 Remote Models Implementation Guide

## 📋 Overview

This implementation provides **pure RPC-based models** for accessing remote `capacity_profiles` and `requirements` data without local storage. The models use **Odoo 17 XML-RPC** with **API key authentication** to connect to integration servers.

## 🏗️ Architecture

### Core Components

1. **Remote Capacity Profile Model** (`vnfield.market.remote.capacity.profile`)

   - Pure RPC proxy to `vnfield.market.capacity.profile` on remote server
   - No local database table (`_auto = False`)
   - Real-time data fetching via XML-RPC

2. **Remote Requirement Model** (`vnfield.market.remote.requirement`)

   - Pure RPC proxy to `vnfield.market.requirement` on remote server
   - No local database table (`_auto = False`)
   - Real-time data fetching via XML-RPC

3. **RPC Test Wizard** (`vnfield.market.rpc.test.wizard`)
   - Connection testing and diagnostics
   - Data validation and sample display

## 🔧 Configuration

### System Parameters Required

Configure these parameters in **Settings → Technical → Parameters → System Parameters**:

| Parameter                        | Example Value                     | Description                 |
| -------------------------------- | --------------------------------- | --------------------------- |
| `vnfield.integration_server_url` | `https://integration.vnfield.com` | Remote server URL           |
| `vnfield.integration_database`   | `odoo_integration`                | Remote database name        |
| `vnfield.integration_username`   | `api_user`                        | Authentication username     |
| `vnfield.integration_api_key`    | `your_api_key_here`               | API key (replaces password) |

### Wizard Configuration

Use **Market → Configuration → 🧪 RPC Connection Test** to:

- Test RPC connectivity
- Validate API credentials
- Check remote data availability
- Diagnose connection issues

## 🎯 Key Features

### Remote Capacity Profiles

- ✅ Real-time data from remote server linked to **subcontractors**
- ✅ List and form views with read-only access
- ✅ Search and filter capabilities by subcontractor
- ✅ Sync to local functionality
- ✅ No local storage required

### Remote Requirements

- ✅ Real-time data from remote server for **project requirements**
- ✅ List and form views with read-only access
- ✅ Advanced search with date filters
- ✅ Priority and state-based filtering
- ✅ Sync to local functionality

### Security & Permissions

- ✅ Read-only access for regular users
- ✅ System admin can test connections
- ✅ No create/write/delete permissions on remote data
- ✅ Secure API key authentication

## 📱 User Interface

### Menu Structure

```
Market
├── Requirements (local)
├── Capacity Profiles (local)
├── 🌐 Remote Data
│   ├── Remote Capacity Profiles
│   └── Remote Requirements
└── ⚙️ Configuration
    └── 🧪 RPC Connection Test
```

### Views Available

- **Tree Views**: Quick overview with key fields
- **Form Views**: Detailed information display
- **Search Views**: Advanced filtering and grouping
- **Test Wizard**: Connection diagnostics

## 🔄 RPC Implementation Details

### Authentication Pattern

```python
# Odoo 17 XML-RPC with API Key
common = xmlrpc.client.ServerProxy(f"{server_url}/xmlrpc/2/common")
uid = common.authenticate(database, username, api_key, {})
models = xmlrpc.client.ServerProxy(f"{server_url}/xmlrpc/2/object")
result = models.execute_kw(database, uid, api_key, model, method, args, kwargs)
```

### Virtual ID System

- Remote IDs are converted to virtual IDs: `remote_{original_id}`
- Enables Odoo ORM compatibility without database storage
- Supports form views and record browsing

### Method Overrides

- `web_search_read()`: Serves list view data
- `search()`: Handles domain filtering and counting
- `read()`: Provides form view data
- Field mapping utilities for domain/order conversion

## 🧪 Testing & Validation

### RPC Test Wizard Features

1. **Connection Test**

   - Validates server URL and credentials
   - Tests XML-RPC endpoint accessibility
   - Shows authentication status

2. **Capacity Profile Test**

   - Retrieves sample remote capacity profiles
   - Displays data format and structure
   - Counts available records

3. **Requirement Test**
   - Retrieves sample remote requirements
   - Validates data integrity
   - Shows remote server capabilities

### Troubleshooting

- Use the test wizard to diagnose connectivity issues
- Check server logs for RPC call details
- Verify API key permissions on remote server
- Ensure remote models exist with correct field structure

## 📁 File Structure

```
features/market/
├── models/
│   ├── remote_capacity_profile.py
│   ├── remote_requirement.py
│   └── __init__.py
├── views/
│   ├── remote_capacity_profile_views.xml
│   ├── remote_requirement_views.xml
│   └── market_menus.xml
├── wizards/
│   ├── rpc_test_wizard.py
│   ├── rpc_test_wizard_views.xml
│   └── __init__.py
└── security/
    └── ir.model.access.csv
```

## 🚀 Usage Examples

### Access Remote Data

```python
# Get remote capacity profiles
remote_cp = self.env['vnfield.market.remote.capacity.profile']
profiles = remote_cp.search([('state', '=', 'active')])

# Get remote requirements
remote_req = self.env['vnfield.market.remote.requirement']
requirements = remote_req.search([('priority', '=', 'high')])
```

### Sync to Local

```python
# Sync remote capacity profile to local
remote_profile.action_sync_to_local()

# Sync remote requirement to local
remote_requirement.action_sync_to_local()
```

## ⚡ Performance Notes

- Data is fetched on-demand from remote server
- No local caching implemented
- Consider implementing pagination for large datasets
- RPC calls may have network latency
- Test wizard helps identify performance bottlenecks

## 🔒 Security Considerations

- API keys should be stored securely
- Use HTTPS for production environments
- Regularly rotate API keys
- Monitor RPC call logs for security
- Restrict system parameter access

---

_This implementation follows Odoo 17 best practices for RPC integration and provides a scalable foundation for remote data access._
