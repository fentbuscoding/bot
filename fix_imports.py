#!/usr/bin/env python3
"""
Script to fix async_db imports across the codebase
"""
import os
import re

# List of files that need to be updated
files_to_update = [
    '/home/ks/Desktop/bot/cogs/Reminders.py',
    '/home/ks/Desktop/bot/cogs/admin/Admin.py',
    '/home/ks/Desktop/bot/cogs/admin/Performance.py',
    '/home/ks/Desktop/bot/cogs/settings/welcome.py',
    '/home/ks/Desktop/bot/cogs/settings/economy.py',
    '/home/ks/Desktop/bot/cogs/settings/general_new.py',
    '/home/ks/Desktop/bot/cogs/settings/moderation.py',
    '/home/ks/Desktop/bot/cogs/settings/logging.py',
    '/home/ks/Desktop/bot/cogs/settings/general.py',
    '/home/ks/Desktop/bot/cogs/settings/music.py',
    '/home/ks/Desktop/bot/cogs/setup/SetupWizard.py',
    '/home/ks/Desktop/bot/cogs/economy/gambling/special_games.py',
    '/home/ks/Desktop/bot/cogs/economy/gambling/chance_games.py',
    '/home/ks/Desktop/bot/cogs/economy/gambling/__init__.py',
    '/home/ks/Desktop/bot/cogs/economy/gambling/card_games.py',
    '/home/ks/Desktop/bot/cogs/economy/gambling/plinko.py',
    '/home/ks/Desktop/bot/cogs/economy/Shop.py',
    '/home/ks/Desktop/bot/cogs/economy/Trading.py',
    '/home/ks/Desktop/bot/cogs/economy/Bazaar.py',
    '/home/ks/Desktop/bot/cogs/economy/Work.py',
    '/home/ks/Desktop/bot/cogs/economy/Giveaway.py',
    '/home/ks/Desktop/bot/cogs/economy/fishing/AutoFishing.py',
    '/home/ks/Desktop/bot/cogs/economy/fishing/fishing_inventory.py',
    '/home/ks/Desktop/bot/cogs/economy/fishing/fishing_core.py',
    '/home/ks/Desktop/bot/cogs/economy/fishing/fishing_ui.py',
    '/home/ks/Desktop/bot/cogs/economy/fishing/fishing_selling.py',
    '/home/ks/Desktop/bot/cogs/economy/fishing/fishing_stats.py',
    '/home/ks/Desktop/bot/cogs/economy/Economy.py',
    '/home/ks/Desktop/bot/utils/potion_effects.py',
    '/home/ks/Desktop/bot/botEvents/onReady.py',
    '/home/ks/Desktop/bot/bronxbot.py'
]

def fix_file(filepath):
    """Fix imports in a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Track if we made changes
        original_content = content
        
        # Replace the import statements
        content = content.replace('from utils.db import async_db as db', 'from utils.db import AsyncDatabase\ndb = AsyncDatabase.get_instance()')
        content = content.replace('from utils.db import async_db', 'from utils.db import AsyncDatabase\ndb = AsyncDatabase.get_instance()')
        
        # Handle the special case in bronxbot.py where it's imported inside a function
        if 'bronxbot.py' in filepath:
            content = re.sub(r'(\s+)from utils\.db import async_db', r'\1from utils.db import AsyncDatabase\n\1db = AsyncDatabase.get_instance()', content)
        
        # Handle the special case in onReady.py where it's imported inside a function
        if 'onReady.py' in filepath:
            content = re.sub(r'(\s+)from utils\.db import async_db', r'\1from utils.db import AsyncDatabase\n\1db = AsyncDatabase.get_instance()', content)
        
        # Replace async_db references with db (but be careful not to replace strings)
        # This is a basic replacement - might need manual review for some files
        content = re.sub(r'\basync_db\b', 'db', content)
        
        # Only write if we made changes
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed {filepath}")
            return True
        else:
            print(f"⏭️ No changes needed for {filepath}")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")
        return False

def main():
    """Main function to fix all files"""
    print("Starting import fixes...")
    
    fixed_count = 0
    for filepath in files_to_update:
        if os.path.exists(filepath):
            if fix_file(filepath):
                fixed_count += 1
        else:
            print(f"⚠️ File not found: {filepath}")
    
    print(f"\nCompleted! Fixed {fixed_count} files.")

if __name__ == "__main__":
    main()
