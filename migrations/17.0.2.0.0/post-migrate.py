# -*- coding: utf-8 -*-
"""
Migration script to clean up deleted models metadata and orphaned records
"""

def migrate(cr, version):
    """Clean up metadata for deleted models and orphaned records"""
    
    # List of deleted models
    deleted_models = [
        'vnfield.market.bid',
        'vnfield.market.bid.invitation', 
        'vnfield.skill'
    ]
    
    print("Starting cleanup of deleted models metadata...")
    
    # First, let's discover what tables actually exist
    cr.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'ir_%'
        ORDER BY table_name
    """)
    
    existing_tables = [row[0] for row in cr.fetchall()]
    print(f"Found IR tables: {existing_tables}")
    
    for model_name in deleted_models:
        print(f"Cleaning up model: {model_name}")
        
        try:
            # 1. Delete model access records (always exists in Odoo)
            if 'ir_model_access' in existing_tables:
                cr.execute("""
                    DELETE FROM ir_model_access 
                    WHERE model_id IN (
                        SELECT id FROM ir_model WHERE model = %s
                    )
                """, (model_name,))
                print(f"Deleted {cr.rowcount} access records for {model_name}")
            
            # 2. Delete field records (always exists in Odoo)
            if 'ir_model_fields' in existing_tables:
                cr.execute("""
                    DELETE FROM ir_model_fields 
                    WHERE model = %s
                """, (model_name,))
                print(f"Deleted {cr.rowcount} field records for {model_name}")
            
            # 3. Delete UI view records (always exists in Odoo)
            if 'ir_ui_view' in existing_tables:
                cr.execute("""
                    DELETE FROM ir_ui_view 
                    WHERE model = %s
                """, (model_name,))
                print(f"Deleted {cr.rowcount} view records for {model_name}")
            
            # 4. Delete action records - check for different possible table names
            action_table = None
            for possible_name in ['ir_act_window', 'ir_actions_act_window']:
                if possible_name in existing_tables:
                    action_table = possible_name
                    break
            
            if action_table:
                cr.execute(f"""
                    DELETE FROM {action_table} 
                    WHERE res_model = %s
                """, (model_name,))
                print(f"Deleted {cr.rowcount} action records from {action_table} for {model_name}")
            
            # 5. Delete model data records (XML IDs) - always exists
            if 'ir_model_data' in existing_tables:
                cr.execute("""
                    DELETE FROM ir_model_data 
                    WHERE model = %s
                """, (model_name,))
                print(f"Deleted {cr.rowcount} model_data records for {model_name}")
            
            # 6. Delete the model record itself - always exists
            if 'ir_model' in existing_tables:
                cr.execute("""
                    DELETE FROM ir_model 
                    WHERE model = %s
                """, (model_name,))
                print(f"Deleted {cr.rowcount} model records for {model_name}")
            
        except Exception as e:
            print(f"Error cleaning up {model_name}: {e}")
            continue
    
    # Clean up orphaned database tables
    tables_to_drop = [
        'vnfield_market_bid',
        'vnfield_market_bid_invitation',
        'vnfield_skill',
        'vnfield_market_capacity_profile_skill_rel',
        'vnfield_market_requirement_skill_rel'
    ]
    
    print("Checking for orphaned database tables to drop...")
    cr.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'vnfield_%'
        ORDER BY table_name
    """)
    
    existing_vnfield_tables = [row[0] for row in cr.fetchall()]
    print(f"Found vnfield tables: {existing_vnfield_tables}")
    
    for table_name in tables_to_drop:
        if table_name in existing_vnfield_tables:
            try:
                print(f"Dropping table: {table_name}")
                cr.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                print(f"Successfully dropped table: {table_name}")
            except Exception as e:
                print(f"Could not drop table {table_name}: {e}")
    
    # Clean up orphaned records
    try:
        if 'ir_model_data' in existing_tables:
            cr.execute("""
                DELETE FROM ir_model_data 
                WHERE model LIKE 'vnfield.market.bid%' 
                OR model LIKE 'vnfield.skill%'
            """)
            print(f"Cleaned up {cr.rowcount} orphaned ir_model_data records")
    except Exception as e:
        print(f"Error cleaning orphaned records: {e}")
    
    # Force commit to ensure all changes are applied
    cr.commit()
    
    print("Migration completed successfully!")
    print("Deleted models and all related metadata have been removed.")