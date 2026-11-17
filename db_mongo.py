"""
CAMPUS-FIND: MongoDB Document Store Layer
Handles item reports with nested attributes, location zones, and resilient fallback.
"""

import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "campus_find_mongo")
RESILIENCE_MODE = os.getenv("RESILIENCE_MODE", "auto").lower()

_mongo_client = None
_use_mock = False
_engine_type = "untested"
_last_error = None
_mock_client = None


def test_mongo_connection():
    """Attempt a direct handshake with the MongoDB server."""
    global _mongo_client, _use_mock, _engine_type, _last_error, _mock_client
    client = None
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1500)
        client.admin.command('ping')
        _mongo_client = client
        _use_mock = False
        _engine_type = "MongoDB (Live Network)"
        _last_error = None
        return True, "Connected to MongoDB successfully"
    except Exception as e:
        if client:
            try:
                client.close()
            except Exception:
                pass
        _last_error = str(e)
        if RESILIENCE_MODE == "auto":
            try:
                import mongomock
                if _mock_client is None:
                    _mock_client = mongomock.MongoClient()
                _use_mock = True
                _engine_type = "MongoMock (Resilience In-Memory Mode)"
                return True, f"MongoDB unavailable ({e}); auto-resilience active using MongoMock engine."
            except ImportError:
                _use_mock = False
                _engine_type = "MongoDB (Offline)"
                return False, f"MongoDB offline and mongomock not installed: {e}"
        else:
            _use_mock = False
            _engine_type = "MongoDB (Offline)"
            return False, f"MongoDB connection failed: {e}"


def get_db():
    """Returns the MongoDB database instance."""
    global _mongo_client, _mock_client, _use_mock
    if _engine_type == "untested":
        test_mongo_connection()

    if _use_mock:
        return _mock_client[MONGO_DB_NAME]
    
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URI)
    return _mongo_client[MONGO_DB_NAME]


def get_items_collection():
    """Returns the 'item_reports' collection."""
    db = get_db()
    return db["item_reports"]


def insert_item_report(doc):
    """Inserts a new item report into MongoDB."""
    coll = get_items_collection()
    # Strip any internal MongoDB _id if passed
    doc.pop("_id", None)
    result = coll.insert_one(doc)
    return result.inserted_id


def find_item_by_uuid(item_uuid, include_private_secret=False):
    """
    Finds a single report by item_uuid.
    Privacy rule: strips 'private_secret_hash' or raw secret details unless requested by moderator.
    """
    coll = get_items_collection()
    doc = coll.find_one({"item_uuid": item_uuid}, {"_id": 0})
    if not doc:
        return None
    
    if not include_private_secret:
        doc.pop("private_secret_detail", None)
        doc.pop("private_secret_hash", None)
    return doc


def query_items(filter_query=None, sort_field="dates.reported_at", limit=50):
    """Queries item reports, excluding private secrets for public listings."""
    coll = get_items_collection()
    q = filter_query or {}
    projection = {"_id": 0, "private_secret_detail": 0, "private_secret_hash": 0}
    cursor = coll.find(q, projection).sort(sort_field, -1).limit(limit)
    return list(cursor)


def query_by_nested_location(campus_zone=None, building=None):
    """
    Demonstrates a MongoDB nested field query on 'location.campus_zone' and 'location.building'.
    """
    q = {}
    if campus_zone and campus_zone != "all":
        q["location.campus_zone"] = campus_zone
    if building:
        q["location.building"] = {"$regex": building, "$options": "i"}
    return query_items(q)


def query_by_nested_attribute(color=None, brand=None):
    """
    Demonstrates a MongoDB nested field query on 'nested_attributes.color' and 'nested_attributes.brand'.
    """
    q = {}
    if color:
        q["nested_attributes.color"] = {"$regex": color, "$options": "i"}
    if brand:
        q["nested_attributes.brand"] = {"$regex": brand, "$options": "i"}
    return query_items(q)


def query_urgent_items():
    """
    Demonstrates a MongoDB nested field query on 'urgency_info.is_urgent'.
    """
    return query_items({"urgency_info.is_urgent": True})


def update_item_status(item_uuid, new_status):
    """Updates the status field of an item in MongoDB."""
    coll = get_items_collection()
    res = coll.update_one(
        {"item_uuid": item_uuid},
        {"$set": {"status": new_status}}
    )
    return res.modified_count > 0


def get_mongo_status():
    """Provides health and status information for UI and diagnostics."""
    if _engine_type == "untested":
        test_mongo_connection()

    item_count = 0
    try:
        coll = get_items_collection()
        item_count = coll.count_documents({})
    except Exception:
        pass

    return {
        "engine": _engine_type,
        "is_connected": True if _engine_type != "MongoDB (Offline)" else False,
        "uri": MONGO_URI if not _use_mock else "In-Memory MongoMock Store",
        "database": MONGO_DB_NAME,
        "collection": "item_reports",
        "item_count": item_count,
        "last_error": _last_error
    }
