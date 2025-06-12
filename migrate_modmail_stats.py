#!/usr/bin/env python3
"""
Migration script to move ModMail stats from stats.json to modmail_stats.json
This prevents conflicts between the main bot stats and ModMail stats.
"""

import json
import os

def migrate_modmail_stats():
    """Migrate ModMail stats to separate file"""
    stats_file = "data/stats.json"
    modmail_stats_file = "data/modmail_stats.json"
    
    # Check if main stats file exists
    if not os.path.exists(stats_file):
        print("No stats.json file found, nothing to migrate.")
        return
    
    try:
        # Load main stats
        with open(stats_file, "r") as f:
            main_data = json.load(f)
        
        # Check if there are ModMail-specific stats to migrate
        if "stats" not in main_data:
            print("No stats section found in stats.json")
            return
        
        # Look for existing modmail stats file
        modmail_data = {}
        if os.path.exists(modmail_stats_file):
            with open(modmail_stats_file, "r") as f:
                modmail_data = json.load(f)
        
        # Initialize modmail data structure if needed
        if "stats" not in modmail_data:
            modmail_data["stats"] = {}
        if "guilds" not in modmail_data:
            modmail_data["guilds"] = {"count": 0, "list": []}
        
        # Check if main stats has the old ModMail structure
        migrated_count = 0
        guild_stats = main_data.get("stats", {})
        
        for guild_id, stats in guild_stats.items():
            # Only migrate if it looks like ModMail stats (has messages count)
            if isinstance(stats, dict) and "messages" in stats:
                print(f"Migrating stats for guild {guild_id}: {stats}")
                modmail_data["stats"][guild_id] = stats
                migrated_count += 1
                
                # Add to guild list if not already there
                if guild_id not in modmail_data["guilds"]["list"]:
                    modmail_data["guilds"]["list"].append(guild_id)
        
        # Update guild count
        modmail_data["guilds"]["count"] = len(modmail_data["guilds"]["list"])
        
        if migrated_count > 0:
            # Save the ModMail stats
            with open(modmail_stats_file, "w") as f:
                json.dump(modmail_data, f, indent=2)
            
            print(f"Successfully migrated {migrated_count} guild stats to {modmail_stats_file}")
            
            # Create backup of original and clean up main stats
            backup_file = "data/stats_backup_pre_migration.json"
            if not os.path.exists(backup_file):
                with open(backup_file, "w") as f:
                    json.dump(main_data, f, indent=2)
                print(f"Created backup of original stats at {backup_file}")
            
            # Remove the migrated stats from main stats file to prevent conflicts
            for guild_id in modmail_data["stats"].keys():
                if guild_id in main_data.get("stats", {}):
                    del main_data["stats"][guild_id]
            
            # Clean up empty stats section
            if not main_data.get("stats"):
                main_data.pop("stats", None)
            
            # Save cleaned main stats
            with open(stats_file, "w") as f:
                json.dump(main_data, f, indent=2)
            
            print("Cleaned up main stats.json file")
        else:
            print("No ModMail stats found to migrate")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("ModMail Stats Migration Tool")
    print("=" * 30)
    migrate_modmail_stats()
    print("Migration complete!")
