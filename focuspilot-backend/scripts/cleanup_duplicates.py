"""
Clean up duplicate blocklist entries (e.g., youtube.com and www.youtube.com)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import get_supabase

def normalize_domain(domain):
    """Normalize domain by removing www. prefix"""
    return domain.lower().replace('www.', '')

def cleanup_duplicates():
    supabase = get_supabase()
    
    # Get all blocklist items
    result = supabase.table('blocklist').select("*").execute()
    items = result.data
    
    print(f"Found {len(items)} blocklist entries")
    
    # Group by normalized domain and user_id
    domain_groups = {}
    for item in items:
        normalized = normalize_domain(item['domain'])
        key = (normalized, item['user_id'])
        
        if key not in domain_groups:
            domain_groups[key] = []
        domain_groups[key].append(item)
    
    # Find and remove duplicates
    deleted_count = 0
    for (normalized, user_id), group in domain_groups.items():
        if len(group) > 1:
            print(f"\nFound {len(group)} entries for {normalized} (user: {user_id}):")
            
            # Sort by created_at to keep the oldest
            sorted_group = sorted(group, key=lambda x: x.get('created_at', ''))
            keep = sorted_group[0]
            duplicates = sorted_group[1:]
            
            print(f"  Keeping: {keep['domain']} (id: {keep['id']}, created: {keep.get('created_at', 'unknown')})")
            
            for dup in duplicates:
                print(f"  Deleting: {dup['domain']} (id: {dup['id']}, created: {dup.get('created_at', 'unknown')})")
                
                # Delete the duplicate
                supabase.table('blocklist').delete().eq('id', dup['id']).execute()
                deleted_count += 1
    
    print(f"\n✓ Cleanup complete! Deleted {deleted_count} duplicate entries")

if __name__ == "__main__":
    cleanup_duplicates()
