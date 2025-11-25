# -*- coding: utf-8 -*-
"""
Final migration to ensure complete cleanup
"""

def migrate(cr, version):
    """Final cleanup to ensure all orphaned records are removed"""
    
    print("=== Final cleanup migration ===")
    
    # Discover existing tables first
    cr.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'ir_%'
        ORDER BY table_name
    """)
    
    existing_tables = [row[0] for row in cr.fetchall()]
    
    # Generic cleanup queries to remove any remaining orphaned records
    cleanup_operations = [
        {
            'table': 'ir_model_data',
            'description': 'model data records',
            'query': """
                DELETE FROM ir_model_data 
                WHERE model IN ('vnfield.market.bid', 'vnfield.market.bid.invitation', 'vnfield.skill')
            """
        },
        {
            'table': 'ir_ui_view',
            'description': 'view records',
            'query': """
                DELETE FROM ir_ui_view 
                WHERE name LIKE '%bid%' OR name LIKE '%skill%' OR name LIKE '%invitation%'
            """
        }
    ]
    
    # Try to find the correct action table name
    action_table = None
    for possible_name in ['ir_act_window', 'ir_actions_act_window']:
        if possible_name in existing_tables:
            action_table = possible_name
            break
    
    if action_table:
        cleanup_operations.append({
            'table': action_table,
            'description': 'action records',
            'query': f"""
                DELETE FROM {action_table} 
                WHERE name LIKE '%bid%' OR name LIKE '%skill%' OR name LIKE '%invitation%'
            """
        })
    
    # Execute cleanup operations
    for operation in cleanup_operations:
        if operation['table'] in existing_tables:
            try:
                cr.execute(operation['query'])
                if cr.rowcount > 0:
                    print(f"Cleaned up {cr.rowcount} {operation['description']}")
            except Exception as e:
                print(f"Failed to clean {operation['description']}: {e}")
    
    # Force commit
    cr.commit()
    print("=== Final cleanup completed ===")