# -*- coding: utf-8 -*-
"""
Migration script to clean up orphaned records after model deletion
"""

def migrate(cr, version):
    """Clean up all orphaned records that reference non-existent models"""
    
    print("=== Starting comprehensive cleanup of orphaned records ===")
    
    # First discover existing tables
    cr.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'ir_%'
        ORDER BY table_name
    """)
    
    existing_tables = [row[0] for row in cr.fetchall()]
    print(f"Found IR tables: {existing_tables}")
    
    try:
        # 1. Clean up orphaned ir_model_data records
        if 'ir_model_data' in existing_tables:
            print("Cleaning up orphaned ir_model_data records...")
            cr.execute("""
                DELETE FROM ir_model_data 
                WHERE (model LIKE 'vnfield.market.bid%' OR model LIKE 'vnfield.skill%')
                AND model NOT IN (SELECT model FROM ir_model)
            """)
            deleted_count = cr.rowcount
            print(f"Deleted {deleted_count} orphaned ir_model_data records")
    except Exception as e:
        print(f"Error cleaning ir_model_data: {e}")
    
    try:
        # 2. Clean up orphaned ir_model_access records
        if 'ir_model_access' in existing_tables:
            print("Cleaning up orphaned ir_model_access records...")
            cr.execute("""
                DELETE FROM ir_model_access 
                WHERE model_id NOT IN (SELECT id FROM ir_model)
            """)
            deleted_count = cr.rowcount
            print(f"Deleted {deleted_count} orphaned ir_model_access records")
    except Exception as e:
        print(f"Error cleaning ir_model_access: {e}")
    
    try:
        # 3. Clean up orphaned ir_ui_view records
        if 'ir_ui_view' in existing_tables:
            print("Cleaning up orphaned ir_ui_view records...")
            cr.execute("""
                DELETE FROM ir_ui_view 
                WHERE model LIKE 'vnfield.market.bid%' OR model LIKE 'vnfield.skill%'
            """)
            deleted_count = cr.rowcount
            print(f"Deleted {deleted_count} orphaned ir_ui_view records")
    except Exception as e:
        print(f"Error cleaning ir_ui_view: {e}")
    
    try:
        # 4. Clean up orphaned action records
        action_table = None
        for possible_name in ['ir_act_window', 'ir_actions_act_window']:
            if possible_name in existing_tables:
                action_table = possible_name
                break
        
        if action_table:
            print(f"Cleaning up orphaned {action_table} records...")
            cr.execute(f"""
                DELETE FROM {action_table} 
                WHERE res_model LIKE 'vnfield.market.bid%' OR res_model LIKE 'vnfield.skill%'
            """)
            deleted_count = cr.rowcount
            print(f"Deleted {deleted_count} orphaned {action_table} records")
    except Exception as e:
        print(f"Error cleaning action records: {e}")
    
    try:
        # 5. Clean up orphaned ir_model_fields records
        if 'ir_model_fields' in existing_tables:
            print("Cleaning up orphaned ir_model_fields records...")
            cr.execute("""
                DELETE FROM ir_model_fields 
                WHERE model LIKE 'vnfield.market.bid%' OR model LIKE 'vnfield.skill%'
            """)
            deleted_count = cr.rowcount
            print(f"Deleted {deleted_count} orphaned ir_model_fields records")
    except Exception as e:
        print(f"Error cleaning ir_model_fields: {e}")
    
    # Force commit
    cr.commit()
    
    print("=== Comprehensive cleanup completed successfully! ===")
    print("All orphaned records have been removed from the database.")