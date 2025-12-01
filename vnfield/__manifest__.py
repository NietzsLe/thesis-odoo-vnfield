# -*- coding: utf-8 -*-
# ═══════════════════════════════════════════════════
# ═             🏗️ VNFIELD CONTRACTOR SYSTEM        ═
# ═   Multi-site contractor management với IS sync   ═
# ═══════════════════════════════════════════════════
#
#    Original Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Enhanced for contractor management by Assistant
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#############################################################################
{
    "name": "VN Field Contractor System (CS)",
    "version": "17.0.2.0.2",
    "category": "Project Management",
    "summary": "Multi-site contractor management với Integration System sync",
    "description": """
        VN Field Contractor System (CS)
        ===================================
        
        ✨ Features:
        • 👷 Multi-site contractor management
        • 📄 Agreement management between contractors  
        • 📋 Enhanced task management và assignment
        • 🌐 JSON-RPC integration với Integration System (IS)
        • 🔄 Kafka message broker cho change propagation
        • 📊 Professional kanban và form views
        • 🎯 Workflow automation và approval processes
        
        🔧 Technical:
        • Odoo 17.0 compatible
        • REST API integration
        • External system synchronization
        • Modern UI/UX design
    """,
    "author": "VN Field Team",
    "website": "https://vnfield.com",
    "depends": [
        "base",
        "mail",
    ],
    "external_dependencies": {
        "python": ["confluent_kafka"],
    },
    "data": [
        'features/organization/security/vnfield_groups.xml',
        'features/shared/security/ir.model.access.csv',
        'features/shared/security/sync_request_security.xml',
        'features/shared/views/sync_request_views.xml',
        'features/shared/views/sync_request_menus.xml',
        'features/setting/security/ir.model.access.csv',
        'features/setting/views/vnfield_setting_menus.xml',
        'features/setting/wizards/kafka_config_wizard_views.xml',
        'features/setting/wizards/system_type_config_wizard_views.xml',
        'features/setting/wizards/kafka_cron_manager_wizard_views.xml',
        'features/setting/views/contractor_representative_wizard_views.xml',
        'features/setting/views/vnfield_setting_overview.xml',
        'features/organization/security/ir.model.access.csv',
        'features/project/security/ir.model.access.csv',
        'features/project/views/project_views.xml',
        'features/project/views/project_invitation_views.xml',
        'features/project/views/task_views.xml',
        'features/project/views/task_assignment_wizard_views.xml',
        'features/project/views/approval_views.xml',
        'features/project/views/approval_step_views.xml',
        'features/project/views/approver_views.xml',
        'features/project/views/project_actions.xml',
        'features/project/data/invitation_cron.xml',
        'features/organization/views/contractor_views.xml',
        'features/organization/views/subcontractor_views.xml',
        'features/organization/views/user_views.xml',
        'features/organization/views/team_views.xml',
        'features/organization/views/organization_menus.xml',
        'features/organization/data/team_cron.xml',
        'features/project/wizards/task_mapping_wizard_view.xml',
        'features/market/security/ir.model.access.csv',
        'features/market/views/requirement_views.xml',
        'features/market/views/capacity_profile_views.xml',
        'features/market/views/remote_capacity_profile_views.xml',
        'features/market/views/remote_requirement_views.xml',
        'features/market/views/create_remote_requirement_wizard_views.xml',
        'features/market/views/create_remote_capacity_profile_wizard_views.xml',
        'features/market/views/market_menus.xml',
    ],
    "demo": [],
    "images": ["static/description/banner.png"],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
    "application": True,
}
