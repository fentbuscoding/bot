from motor.motor_asyncio import AsyncIOMotorClient
import asyncio, json

with open('data/config.json', 'r') as f:
    config = json.load(f)

async def migrate_rod_inventory():
    # Connect to your MongoDB
    client = AsyncIOMotorClient(config['MONGO_URI'])  # Update with your connection string
    db = client.your_database_name  # Update with your DB name
    
    # Get all rods from the rods collection to create a mapping
    rods = await db.rods.find().to_list(None)
    rod_id_to_name = {str(rod["_id"]): rod["name"] for rod in rods}
    
    # Process all users
    async for user in db.users.find({"inventory.rod": {"$exists": True}}):
        updated_rods = {}
        needs_update = False
        
        # Check current rod inventory
        current_rods = user.get("inventory", {}).get("rod", {})
        
        for rod_id, quantity in current_rods.items():
            # If the key is an ObjectID string (24 char hex)
            if len(rod_id) == 24 and all(c in '0123456789abcdef' for c in rod_id.lower()):
                if rod_id in rod_id_to_name:
                    # Convert to the proper rod name
                    proper_name = rod_id_to_name[rod_id]
                    updated_rods[proper_name] = quantity
                    needs_update = True
                    print(f"Migrating {rod_id} → {proper_name} for user {user['_id']}")
                else:
                    print(f"Warning: No rod found with ID {rod_id}, keeping as-is")
                    updated_rods[rod_id] = quantity
            else:
                # Already in correct format, keep as-is
                updated_rods[rod_id] = quantity
        
        # Update active_rod if it's an ObjectID
        active_rod = user.get("active_rod")
        if active_rod and len(active_rod) == 24 and all(c in '0123456789abcdef' for c in active_rod.lower()):
            if active_rod in rod_id_to_name:
                new_active = rod_id_to_name[active_rod]
                print(f"Updating active rod {active_rod} → {new_active}")
                needs_update = True
            else:
                new_active = None
                print(f"Warning: Active rod {active_rod} not found in rods collection")
        else:
            new_active = active_rod
        
        # Update the user if needed
        if needs_update:
            update_data = {"$set": {"inventory.rod": updated_rods}}
            if new_active is not None:
                update_data["$set"]["active_rod"] = new_active
            
            await db.users.update_one(
                {"_id": user["_id"]},
                update_data
            )
            print(f"Successfully updated user {user['_id']}")

    print("Migration complete!")

# Run the migration
asyncio.run(migrate_rod_inventory())