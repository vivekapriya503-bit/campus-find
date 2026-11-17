// ==============================================================================
// CAMPUS-FIND MongoDB Collection Setup and Indexes
// Execute in mongosh or MongoDB Compass
// ==============================================================================

const dbName = 'campus_find_mongo';
const collName = 'item_reports';

db = db.getSiblingDB(dbName);

// Create collection with schema validation rules
db.createCollection(collName, {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["item_uuid", "report_type", "title", "category", "status", "location", "dates"],
      properties: {
        item_uuid: {
          bsonType: "string",
          description: "Unique shared UUID referencing relational records in MySQL"
        },
        report_type: {
          enum: ["lost", "found"],
          description: "Must be either 'lost' or 'found'"
        },
        title: {
          bsonType: "string",
          description: "Descriptive name of the lost or found item"
        },
        category: {
          enum: ["Electronics", "Wallets & IDs", "Keys & Bags", "Books & Notes", "Clothing", "Valuables", "Other"],
          description: "Campus category taxonomy"
        },
        status: {
          enum: ["open", "possible_match", "claimed", "returned", "closed"],
          description: "Lifecycle status of the report"
        },
        description: {
          bsonType: "string"
        },
        nested_attributes: {
          bsonType: "object",
          properties: {
            color: { bsonType: "string" },
            brand: { bsonType: "string" },
            model: { bsonType: "string" },
            distinguishing_mark: { bsonType: "string" },
            condition: { bsonType: "string" }
          }
        },
        location: {
          bsonType: "object",
          required: ["campus_zone", "building"],
          properties: {
            campus_zone: { bsonType: "string" },
            building: { bsonType: "string" },
            floor: { bsonType: "string" },
            room_or_area: { bsonType: "string" }
          }
        },
        urgency_info: {
          bsonType: "object",
          properties: {
            is_urgent: { bsonType: "bool" },
            urgency_reason: { bsonType: "string" },
            is_perishable: { bsonType: "bool" }
          }
        },
        dates: {
          bsonType: "object",
          required: ["incident_date", "reported_at"],
          properties: {
            incident_date: { bsonType: "string" },
            reported_at: { bsonType: "string" }
          }
        },
        reporter: {
          bsonType: "object",
          properties: {
            user_uuid: { bsonType: "string" },
            display_name: { bsonType: "string" },
            role: { bsonType: "string" }
          }
        },
        private_secret_hint: {
          bsonType: "string",
          description: "Public prompt asking claimants for a hidden proof detail"
        },
        photo_meta: {
          bsonType: "object",
          properties: {
            has_photo: { bsonType: "bool" },
            image_url: { bsonType: "string" }
          }
        }
      }
    }
  }
});

// Indexes for query performance
db[collName].createIndex({ "item_uuid": 1 }, { unique: true });
db[collName].createIndex({ "category": 1, "status": 1 });
db[collName].createIndex({ "location.campus_zone": 1 });
db[collName].createIndex({ "location.building": 1 });
db[collName].createIndex({ "urgency_info.is_urgent": 1 });
db[collName].createIndex({ "dates.reported_at": -1 });
db[collName].createIndex({ "title": "text", "description": "text" });

print("CAMPUS-FIND MongoDB collection and indexes created successfully in " + dbName);
