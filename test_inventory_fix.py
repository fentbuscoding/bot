#!/usr/bin/env python3
"""
Test script to verify the inventory error fixes are working correctly.
This script tests the key functions that were modified to handle corrupted inventory data.
"""

import sys
import os
import asyncio
import logging

# Add the bot directory to Python path
sys.path.append('/home/ks/Desktop/bot')

# Import the database module
from utils.db import AsyncDatabase

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_inventory_functions():
    """Test the inventory functions that were fixed"""
    
    print("🔍 Testing inventory error fixes...")
    
    # Get database instance
    db = AsyncDatabase.get_instance()
    
    # Test database connection
    try:
        connected = await db.ensure_connected()
        if connected:
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False
    
    # Test cleanup function
    try:
        print("\n🧹 Testing cleanup_corrupted_inventory function...")
        cleaned_count = await db.cleanup_corrupted_inventory()
        print(f"✅ Cleanup function works - cleaned {cleaned_count} items")
    except Exception as e:
        print(f"❌ Cleanup function error: {e}")
        return False
    
    # Test get_inventory function with type checking
    try:
        print("\n📦 Testing get_inventory function...")
        test_user_id = 123456789  # Test user ID
        inventory = await db.get_inventory(test_user_id)
        print(f"✅ get_inventory works - returned {len(inventory)} items")
        
        # Verify all items are dictionaries
        for item in inventory:
            if not isinstance(item, dict):
                print(f"❌ Found non-dict item in inventory: {type(item)}")
                return False
        print("✅ All inventory items are valid dictionaries")
        
    except Exception as e:
        print(f"❌ get_inventory error: {e}")
        return False
    
    # Test remove_from_inventory function with type checking  
    try:
        print("\n🗑️ Testing remove_from_inventory function...")
        test_user_id = 123456789
        # This should not crash even if there are invalid items
        removed = await db.remove_from_inventory(test_user_id, None, "test_item", 1)
        print(f"✅ remove_from_inventory works - removed: {removed}")
    except Exception as e:
        print(f"❌ remove_from_inventory error: {e}")
        return False
    
    print("\n🎉 All inventory function tests passed!")
    return True

async def test_specific_scenarios():
    """Test specific scenarios that could cause the original error"""
    
    print("\n🧪 Testing specific error scenarios...")
    
    db = AsyncDatabase.get_instance()
    
    # Test scenario: User with mixed inventory (dict and string items)
    # This simulates the corrupted data that was causing the original error
    test_user_id = "test_user_corrupted"
    
    try:
        # Create a test user with mixed inventory data (this simulates corrupted data)
        mixed_inventory = [
            {"id": "valid_item", "name": "Valid Item", "quantity": 1},  # Valid dict
            "corrupted_string_item",  # Invalid string (this was causing the error)
            {"id": "another_valid", "name": "Another Valid", "quantity": 2},  # Valid dict
            123,  # Invalid number
            None  # Invalid None
        ]
        
        # Insert test data (simulating corrupted state)
        await db.db.users.update_one(
            {"_id": test_user_id},
            {"$set": {"inventory": mixed_inventory}},
            upsert=True
        )
        print(f"✅ Created test user with mixed inventory data")
        
        # Test get_inventory - should filter out invalid items
        inventory = await db.get_inventory(test_user_id)
        print(f"✅ get_inventory filtered inventory: {len(inventory)} valid items")
        
        # Verify only valid items remain
        for item in inventory:
            if not isinstance(item, dict):
                print(f"❌ Invalid item found: {type(item)}")
                return False
        
        # Test cleanup function on this specific user
        cleaned_count = await db.cleanup_corrupted_inventory()
        print(f"✅ Cleanup removed {cleaned_count} corrupted items")
        
        # Verify inventory is now clean
        user_data = await db.db.users.find_one({"_id": test_user_id})
        if user_data and "inventory" in user_data:
            for item in user_data["inventory"]:
                if not isinstance(item, dict):
                    print(f"❌ Corrupted item still exists: {type(item)}")
                    return False
        
        print("✅ All corrupted items successfully removed")
        
        # Clean up test data
        await db.db.users.delete_one({"_id": test_user_id})
        print("✅ Test data cleaned up")
        
    except Exception as e:
        print(f"❌ Specific scenario test error: {e}")
        return False
    
    print("🎉 All specific scenario tests passed!")
    return True

async def main():
    """Main test function"""
    print("=" * 60)
    print("🧪 INVENTORY ERROR FIX VALIDATION TESTS")
    print("=" * 60)
    
    # Run basic function tests
    basic_tests_passed = await test_inventory_functions()
    
    if not basic_tests_passed:
        print("\n❌ Basic tests failed!")
        return False
    
    # Run specific scenario tests
    scenario_tests_passed = await test_specific_scenarios()
    
    if not scenario_tests_passed:
        print("\n❌ Scenario tests failed!")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED! INVENTORY ERROR FIX IS WORKING!")
    print("=" * 60)
    print("\n✅ The inventory error should now be resolved:")
    print("   • Type checking prevents 'str' object has no attribute 'get' errors")
    print("   • Corrupted items are filtered out safely") 
    print("   • Cleanup function removes corrupted data from database")
    print("   • All inventory operations are now safe from corrupted data")
    
    return True

if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
