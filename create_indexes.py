"""
Script to create database indexes for optimal performance.
Run this once to improve query speed.
"""
import asyncio
from app.core.database import db

async def create_indexes():
    print("Creating database indexes for performance optimization...")
    
    # Connect to DB
    db.connect()
    
    try:
        # Index on buckets.project_id for faster lookups
        await db.db.buckets.create_index("project_id")
        print("✅ Created index on buckets.project_id")
        
        # Index on files.project_id for faster aggregations
        await db.db.files.create_index("project_id")
        print("✅ Created index on files.project_id")
        
        # Index on projects.api_key for faster authentication
        await db.db.projects.create_index("api_key", unique=True)
        print("✅ Created unique index on projects.api_key")
        
        # Index on projects.name for faster duplicate checks
        await db.db.projects.create_index("name", unique=True)
        print("✅ Created unique index on projects.name")
        
        # Compound index on files for better aggregation performance
        await db.db.files.create_index([("project_id", 1), ("size", 1)])
        print("✅ Created compound index on files (project_id, size)")
        
        print("\n✨ All indexes created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating indexes: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(create_indexes())
