# SchemaZero Test Database Setup

Install and configure each supported database engine, then run the schema and seed scripts to generate a test environment you can connect to SchemaZero.

---

## Test Schema

All relational databases use the same six-table schema. Document and key-value databases use an equivalent structure adapted to their data model.

**Tables:** `users`, `categories`, `products`, `orders`, `order_items`, `reviews`

---

## PostgreSQL

Supabase and Neon are Postgres-compatible — use the same schema. CockroachDB is also covered in its own section below.

### Install

**Linux (Ubuntu / Debian)**
```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable --now postgresql
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
```

**Linux (RHEL / Fedora)**
```bash
sudo dnf install -y postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
```

**Windows**
Download the installer: https://www.postgresql.org/download/windows/

Or with winget:
```powershell
winget install PostgreSQL.PostgreSQL
```

Or with Chocolatey:
```powershell
choco install postgresql
```

After install, open pgAdmin or run `psql` from the Start menu.

**Docker (any OS)**
```bash
docker run -d --name sz-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:16
```

### Connection string
```
postgresql://postgres:postgres@localhost:5432/testdb
```

### Schema + seed

```sql
-- Run as: psql -U postgres -f postgres_testdb.sql
-- Or paste into psql / pgAdmin / Supabase SQL editor

CREATE DATABASE testdb;
\c testdb

CREATE TABLE users (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  email       TEXT NOT NULL UNIQUE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE categories (
  id    SERIAL PRIMARY KEY,
  name  TEXT NOT NULL,
  slug  TEXT NOT NULL UNIQUE
);

CREATE TABLE products (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  price       NUMERIC(10,2) NOT NULL,
  category_id INT REFERENCES categories(id),
  stock       INT NOT NULL DEFAULT 0,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE orders (
  id         SERIAL PRIMARY KEY,
  user_id    INT REFERENCES users(id),
  status     TEXT NOT NULL DEFAULT 'pending',
  total      NUMERIC(10,2) NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE order_items (
  id         SERIAL PRIMARY KEY,
  order_id   INT REFERENCES orders(id),
  product_id INT REFERENCES products(id),
  quantity   INT NOT NULL,
  unit_price NUMERIC(10,2) NOT NULL
);

CREATE TABLE reviews (
  id         SERIAL PRIMARY KEY,
  product_id INT REFERENCES products(id),
  user_id    INT REFERENCES users(id),
  rating     SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  body       TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_orders_user       ON orders(user_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_reviews_product   ON reviews(product_id);

-- Seed data
INSERT INTO users (name, email) VALUES
  ('Alice Chen',    'alice@example.com'),
  ('Bob Martinez',  'bob@example.com'),
  ('Carol Johnson', 'carol@example.com');

INSERT INTO categories (name, slug) VALUES
  ('Electronics', 'electronics'),
  ('Books',       'books'),
  ('Clothing',    'clothing');

INSERT INTO products (name, price, category_id, stock) VALUES
  ('Wireless Headphones', 79.99,  1, 50),
  ('USB-C Hub',           34.99,  1, 120),
  ('PostgreSQL: Up & Running', 49.99, 2, 30),
  ('Merino Wool Sweater', 89.99,  3, 40),
  ('Running Shorts',      29.99,  3, 75);

INSERT INTO orders (user_id, status, total) VALUES
  (1, 'completed', 114.98),
  (2, 'pending',   49.99),
  (3, 'completed', 89.99);

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
  (1, 1, 1, 79.99),
  (1, 2, 1, 34.99),
  (2, 3, 1, 49.99),
  (3, 4, 1, 89.99);

INSERT INTO reviews (product_id, user_id, rating, body) VALUES
  (1, 1, 5, 'Great sound quality.'),
  (2, 1, 4, 'Solid hub, runs a bit warm.'),
  (3, 2, 5, 'Best Postgres reference I have found.'),
  (4, 3, 5, 'Super comfortable.');
```

### Test schema changes for SchemaZero

```sql
-- Add a column (LOW risk)
ALTER TABLE users ADD COLUMN phone TEXT;

-- Drop an index (HIGH risk — SchemaZero should fire)
DROP INDEX idx_reviews_product;

-- Drop a column (CRITICAL risk)
ALTER TABLE products DROP COLUMN stock;
```

---

## MySQL

### Install

**Linux (Ubuntu / Debian)**
```bash
sudo apt update
sudo apt install -y mysql-server
sudo systemctl enable --now mysql
sudo mysql_secure_installation
```

**Linux (RHEL / Fedora)**
```bash
sudo dnf install -y mysql-server
sudo systemctl enable --now mysqld
sudo mysql_secure_installation
```

**Windows**
Download MySQL Installer: https://dev.mysql.com/downloads/installer/

Includes MySQL Server, Workbench, and Shell. Choose "Developer Default."

Or with winget:
```powershell
winget install Oracle.MySQL
```

**Docker (any OS)**
```bash
docker run -d --name sz-mysql \
  -e MYSQL_ROOT_PASSWORD=mysql \
  -e MYSQL_DATABASE=testdb \
  -p 3306:3306 \
  mysql:8
```

### Connection string
```
mysql://root:mysql@localhost:3306/testdb
```

### Schema + seed

```sql
-- Run as: mysql -u root -p < mysql_testdb.sql

CREATE DATABASE IF NOT EXISTS testdb;
USE testdb;

CREATE TABLE users (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(255) NOT NULL,
  email      VARCHAR(255) NOT NULL UNIQUE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categories (
  id   INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE products (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(255) NOT NULL,
  price       DECIMAL(10,2) NOT NULL,
  category_id INT,
  stock       INT NOT NULL DEFAULT 0,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE orders (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT,
  status     VARCHAR(50) NOT NULL DEFAULT 'pending',
  total      DECIMAL(10,2) NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE order_items (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  order_id   INT,
  product_id INT,
  quantity   INT NOT NULL,
  unit_price DECIMAL(10,2) NOT NULL,
  FOREIGN KEY (order_id)   REFERENCES orders(id),
  FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE reviews (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  product_id INT,
  user_id    INT,
  rating     TINYINT NOT NULL,
  body       TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (product_id) REFERENCES products(id),
  FOREIGN KEY (user_id)    REFERENCES users(id)
);

CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_orders_user       ON orders(user_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_reviews_product   ON reviews(product_id);

-- Seed data
INSERT INTO users (name, email) VALUES
  ('Alice Chen',    'alice@example.com'),
  ('Bob Martinez',  'bob@example.com'),
  ('Carol Johnson', 'carol@example.com');

INSERT INTO categories (name, slug) VALUES
  ('Electronics', 'electronics'),
  ('Books',       'books'),
  ('Clothing',    'clothing');

INSERT INTO products (name, price, category_id, stock) VALUES
  ('Wireless Headphones',      79.99, 1, 50),
  ('USB-C Hub',                34.99, 1, 120),
  ('PostgreSQL: Up and Running', 49.99, 2, 30),
  ('Merino Wool Sweater',      89.99, 3, 40),
  ('Running Shorts',           29.99, 3, 75);

INSERT INTO orders (user_id, status, total) VALUES
  (1, 'completed', 114.98),
  (2, 'pending',   49.99),
  (3, 'completed', 89.99);

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
  (1, 1, 1, 79.99),
  (1, 2, 1, 34.99),
  (2, 3, 1, 49.99),
  (3, 4, 1, 89.99);

INSERT INTO reviews (product_id, user_id, rating, body) VALUES
  (1, 1, 5, 'Great sound quality.'),
  (2, 1, 4, 'Solid hub, runs a bit warm.'),
  (3, 2, 5, 'Best Postgres reference I have found.'),
  (4, 3, 5, 'Super comfortable.');
```

### Test schema changes for SchemaZero

```sql
ALTER TABLE users ADD COLUMN phone VARCHAR(20);
DROP INDEX idx_reviews_product ON reviews;
ALTER TABLE products DROP COLUMN stock;
```

---

## MongoDB

### Install

**Linux (Ubuntu / Debian)**
```bash
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
  sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
  https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
  sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

sudo apt update
sudo apt install -y mongodb-org
sudo systemctl enable --now mongod
```

**Linux (RHEL / Fedora)**
```bash
# Create repo file
cat <<EOF | sudo tee /etc/yum.repos.d/mongodb-org-7.0.repo
[mongodb-org-7.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/9/mongodb-org/7.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-7.0.asc
EOF

sudo dnf install -y mongodb-org
sudo systemctl enable --now mongod
```

**Windows**
Download: https://www.mongodb.com/try/download/community

Or with winget:
```powershell
winget install MongoDB.Server
```

Install MongoDB Compass (GUI): https://www.mongodb.com/try/download/compass

**Docker (any OS)**
```bash
docker run -d --name sz-mongo \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=mongo \
  -p 27017:27017 \
  mongo:7
```

### Connection string
```
mongodb://admin:mongo@localhost:27017/testdb?authSource=admin
```

### Schema + seed

Run in `mongosh` or MongoDB Compass shell:

```javascript
// mongosh "mongodb://admin:mongo@localhost:27017/testdb?authSource=admin"

use testdb

// Collections with schema validation

db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["name", "email", "created_at"],
      properties: {
        name:       { bsonType: "string" },
        email:      { bsonType: "string" },
        created_at: { bsonType: "date" }
      }
    }
  }
})

db.createCollection("categories")
db.createCollection("products")
db.createCollection("orders")
db.createCollection("order_items")
db.createCollection("reviews")

// Indexes
db.users.createIndex({ email: 1 }, { unique: true })
db.products.createIndex({ category_id: 1 })
db.orders.createIndex({ user_id: 1 })
db.order_items.createIndex({ order_id: 1 })
db.reviews.createIndex({ product_id: 1 })

// Seed data
const userIds = db.users.insertMany([
  { name: "Alice Chen",    email: "alice@example.com", created_at: new Date() },
  { name: "Bob Martinez",  email: "bob@example.com",   created_at: new Date() },
  { name: "Carol Johnson", email: "carol@example.com", created_at: new Date() }
]).insertedIds

const catIds = db.categories.insertMany([
  { name: "Electronics", slug: "electronics" },
  { name: "Books",       slug: "books" },
  { name: "Clothing",    slug: "clothing" }
]).insertedIds

const prodIds = db.products.insertMany([
  { name: "Wireless Headphones",       price: 79.99, category_id: catIds[0], stock: 50,  created_at: new Date() },
  { name: "USB-C Hub",                 price: 34.99, category_id: catIds[0], stock: 120, created_at: new Date() },
  { name: "PostgreSQL: Up & Running",  price: 49.99, category_id: catIds[1], stock: 30,  created_at: new Date() },
  { name: "Merino Wool Sweater",       price: 89.99, category_id: catIds[2], stock: 40,  created_at: new Date() },
  { name: "Running Shorts",            price: 29.99, category_id: catIds[2], stock: 75,  created_at: new Date() }
]).insertedIds

const orderIds = db.orders.insertMany([
  { user_id: userIds[0], status: "completed", total: 114.98, created_at: new Date() },
  { user_id: userIds[1], status: "pending",   total: 49.99,  created_at: new Date() },
  { user_id: userIds[2], status: "completed", total: 89.99,  created_at: new Date() }
]).insertedIds

db.order_items.insertMany([
  { order_id: orderIds[0], product_id: prodIds[0], quantity: 1, unit_price: 79.99 },
  { order_id: orderIds[0], product_id: prodIds[1], quantity: 1, unit_price: 34.99 },
  { order_id: orderIds[1], product_id: prodIds[2], quantity: 1, unit_price: 49.99 },
  { order_id: orderIds[2], product_id: prodIds[3], quantity: 1, unit_price: 89.99 }
])

db.reviews.insertMany([
  { product_id: prodIds[0], user_id: userIds[0], rating: 5, body: "Great sound quality.",              created_at: new Date() },
  { product_id: prodIds[1], user_id: userIds[0], rating: 4, body: "Solid hub, runs a bit warm.",       created_at: new Date() },
  { product_id: prodIds[2], user_id: userIds[1], rating: 5, body: "Best Postgres reference out there.", created_at: new Date() },
  { product_id: prodIds[3], user_id: userIds[2], rating: 5, body: "Super comfortable.",                created_at: new Date() }
])
```

### Test schema changes for SchemaZero

```javascript
// Add a field to validator (equivalent of ADD COLUMN)
db.runCommand({
  collMod: "users",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["name", "email", "created_at"],
      properties: {
        name:       { bsonType: "string" },
        email:      { bsonType: "string" },
        phone:      { bsonType: "string" },
        created_at: { bsonType: "date" }
      }
    }
  }
})

// Drop an index (SchemaZero should catch this)
db.reviews.dropIndex("product_id_1")

// Drop a collection (CRITICAL)
db.order_items.drop()
```

---

## Redis

Redis stores data as keys rather than tables. The test schema uses hashes for records and sorted sets for indexes.

### Install

**Linux (Ubuntu / Debian)**
```bash
sudo apt update
sudo apt install -y redis-server
sudo systemctl enable --now redis-server
```

**Linux (RHEL / Fedora)**
```bash
sudo dnf install -y redis
sudo systemctl enable --now redis
```

**Windows**

Redis does not have an official Windows native build. Two options:

Option 1 — WSL2 (recommended):
```powershell
# In PowerShell as Administrator
wsl --install
# Then inside WSL terminal:
sudo apt install -y redis-server
sudo service redis-server start
```

Option 2 — Docker:
```powershell
docker run -d --name sz-redis -p 6379:6379 redis:7
```

**Docker (any OS)**
```bash
docker run -d --name sz-redis -p 6379:6379 redis:7
```

### Connection string
```
redis://localhost:6379
```

### Schema + seed

Run in `redis-cli` or paste as a script:

```bash
# redis-cli < redis_testdb.sh

# Users — hash per record, set for index
HSET user:1 name "Alice Chen"    email "alice@example.com"    created_at "2024-01-01T00:00:00Z"
HSET user:2 name "Bob Martinez"  email "bob@example.com"      created_at "2024-01-02T00:00:00Z"
HSET user:3 name "Carol Johnson" email "carol@example.com"    created_at "2024-01-03T00:00:00Z"
SADD users:all 1 2 3

# Categories
HSET category:1 name "Electronics" slug "electronics"
HSET category:2 name "Books"       slug "books"
HSET category:3 name "Clothing"    slug "clothing"
SADD categories:all 1 2 3

# Products
HSET product:1 name "Wireless Headphones"      price "79.99" category_id "1" stock "50"
HSET product:2 name "USB-C Hub"                price "34.99" category_id "1" stock "120"
HSET product:3 name "PostgreSQL: Up & Running" price "49.99" category_id "2" stock "30"
HSET product:4 name "Merino Wool Sweater"      price "89.99" category_id "3" stock "40"
HSET product:5 name "Running Shorts"           price "29.99" category_id "3" stock "75"
SADD products:all 1 2 3 4 5
SADD products:by_category:1 1 2
SADD products:by_category:2 3
SADD products:by_category:3 4 5

# Orders
HSET order:1 user_id "1" status "completed" total "114.98" created_at "2024-01-10T00:00:00Z"
HSET order:2 user_id "2" status "pending"   total "49.99"  created_at "2024-01-11T00:00:00Z"
HSET order:3 user_id "3" status "completed" total "89.99"  created_at "2024-01-12T00:00:00Z"
SADD orders:all 1 2 3
SADD orders:by_user:1 1
SADD orders:by_user:2 2
SADD orders:by_user:3 3

# Order items
HSET order_item:1 order_id "1" product_id "1" quantity "1" unit_price "79.99"
HSET order_item:2 order_id "1" product_id "2" quantity "1" unit_price "34.99"
HSET order_item:3 order_id "2" product_id "3" quantity "1" unit_price "49.99"
HSET order_item:4 order_id "3" product_id "4" quantity "1" unit_price "89.99"
SADD order_items:all 1 2 3 4
SADD order_items:by_order:1 1 2
SADD order_items:by_order:2 3
SADD order_items:by_order:3 4

# Reviews
HSET review:1 product_id "1" user_id "1" rating "5" body "Great sound quality."
HSET review:2 product_id "2" user_id "1" rating "4" body "Solid hub, runs a bit warm."
HSET review:3 product_id "3" user_id "2" rating "5" body "Best Postgres reference out there."
HSET review:4 product_id "4" user_id "3" rating "5" body "Super comfortable."
SADD reviews:all 1 2 3 4
SADD reviews:by_product:1 1
SADD reviews:by_product:2 2
SADD reviews:by_product:3 3
SADD reviews:by_product:4 4

# Enable keyspace notifications (required for SchemaZero)
CONFIG SET notify-keyspace-events KEA
```

### Test schema changes for SchemaZero

```bash
# Add a new field to an existing hash (schema evolution)
HSET user:1 phone "+1-555-0100"

# Delete an index set (SchemaZero catches key deletion)
DEL products:by_category:1

# Delete a record type entirely
DEL review:1
SREM reviews:all 1
```

---

## CouchDB

### Install

**Linux (Ubuntu / Debian)**
```bash
curl https://couchdb.apache.org/repo/keys.asc | gpg --dearmor | \
  sudo tee /usr/share/keyrings/couchdb-archive-keyring.gpg > /dev/null

echo "deb [signed-by=/usr/share/keyrings/couchdb-archive-keyring.gpg] \
  https://apache.jfrog.io/artifactory/couchdb-deb/ $(lsb_release -sc) main" | \
  sudo tee /etc/apt/sources.list.d/couchdb.list

sudo apt update
sudo apt install -y couchdb
# Choose "standalone" mode, set admin password when prompted
sudo systemctl enable --now couchdb
```

**Linux (RHEL / Fedora)**
```bash
cat <<EOF | sudo tee /etc/yum.repos.d/bintray-apache-couchdb-rpm.repo
[bintray-apache-couchdb-rpm]
name=bintray-apache-couchdb-rpm
baseurl=https://apache.jfrog.io/artifactory/couchdb-rpm/el\$releasever/
gpgcheck=0
repo_gpgcheck=0
enabled=1
EOF

sudo dnf install -y couchdb
sudo systemctl enable --now couchdb
```

**Windows**
Download: https://couchdb.apache.org/#download

The Windows installer includes Fauxton (web UI) accessible at http://localhost:5984/_utils

**Docker (any OS)**
```bash
docker run -d --name sz-couchdb \
  -e COUCHDB_USER=admin \
  -e COUCHDB_PASSWORD=couchdb \
  -p 5984:5984 \
  couchdb:3
```

### Connection string
```
http://admin:couchdb@localhost:5984
```

Fauxton UI: http://localhost:5984/_utils

### Schema + seed

Run with curl or paste into the Fauxton console (http://localhost:5984/_utils):

```bash
# Set these for convenience
export COUCH="http://admin:couchdb@localhost:5984"

# Create database
curl -X PUT "$COUCH/testdb"

# Users
curl -X POST "$COUCH/testdb/_bulk_docs" -H "Content-Type: application/json" -d '{
  "docs": [
    { "_id": "user:1", "type": "user", "name": "Alice Chen",    "email": "alice@example.com",  "created_at": "2024-01-01" },
    { "_id": "user:2", "type": "user", "name": "Bob Martinez",  "email": "bob@example.com",    "created_at": "2024-01-02" },
    { "_id": "user:3", "type": "user", "name": "Carol Johnson", "email": "carol@example.com",  "created_at": "2024-01-03" }
  ]
}'

# Categories
curl -X POST "$COUCH/testdb/_bulk_docs" -H "Content-Type: application/json" -d '{
  "docs": [
    { "_id": "category:1", "type": "category", "name": "Electronics", "slug": "electronics" },
    { "_id": "category:2", "type": "category", "name": "Books",       "slug": "books" },
    { "_id": "category:3", "type": "category", "name": "Clothing",    "slug": "clothing" }
  ]
}'

# Products
curl -X POST "$COUCH/testdb/_bulk_docs" -H "Content-Type: application/json" -d '{
  "docs": [
    { "_id": "product:1", "type": "product", "name": "Wireless Headphones",      "price": 79.99, "category_id": "category:1", "stock": 50 },
    { "_id": "product:2", "type": "product", "name": "USB-C Hub",                "price": 34.99, "category_id": "category:1", "stock": 120 },
    { "_id": "product:3", "type": "product", "name": "PostgreSQL: Up & Running", "price": 49.99, "category_id": "category:2", "stock": 30 },
    { "_id": "product:4", "type": "product", "name": "Merino Wool Sweater",      "price": 89.99, "category_id": "category:3", "stock": 40 },
    { "_id": "product:5", "type": "product", "name": "Running Shorts",           "price": 29.99, "category_id": "category:3", "stock": 75 }
  ]
}'

# Orders
curl -X POST "$COUCH/testdb/_bulk_docs" -H "Content-Type: application/json" -d '{
  "docs": [
    { "_id": "order:1", "type": "order", "user_id": "user:1", "status": "completed", "total": 114.98, "created_at": "2024-01-10" },
    { "_id": "order:2", "type": "order", "user_id": "user:2", "status": "pending",   "total": 49.99,  "created_at": "2024-01-11" },
    { "_id": "order:3", "type": "order", "user_id": "user:3", "status": "completed", "total": 89.99,  "created_at": "2024-01-12" }
  ]
}'

# Order items
curl -X POST "$COUCH/testdb/_bulk_docs" -H "Content-Type: application/json" -d '{
  "docs": [
    { "_id": "order_item:1", "type": "order_item", "order_id": "order:1", "product_id": "product:1", "quantity": 1, "unit_price": 79.99 },
    { "_id": "order_item:2", "type": "order_item", "order_id": "order:1", "product_id": "product:2", "quantity": 1, "unit_price": 34.99 },
    { "_id": "order_item:3", "type": "order_item", "order_id": "order:2", "product_id": "product:3", "quantity": 1, "unit_price": 49.99 },
    { "_id": "order_item:4", "type": "order_item", "order_id": "order:3", "product_id": "product:4", "quantity": 1, "unit_price": 89.99 }
  ]
}'

# Reviews
curl -X POST "$COUCH/testdb/_bulk_docs" -H "Content-Type: application/json" -d '{
  "docs": [
    { "_id": "review:1", "type": "review", "product_id": "product:1", "user_id": "user:1", "rating": 5, "body": "Great sound quality." },
    { "_id": "review:2", "type": "review", "product_id": "product:2", "user_id": "user:1", "rating": 4, "body": "Solid hub, runs a bit warm." },
    { "_id": "review:3", "type": "review", "product_id": "product:3", "user_id": "user:2", "rating": 5, "body": "Best Postgres reference out there." },
    { "_id": "review:4", "type": "review", "product_id": "product:4", "user_id": "user:3", "rating": 5, "body": "Super comfortable." }
  ]
}'

# Design document (view index — equivalent of a schema index)
curl -X PUT "$COUCH/testdb/_design/products" -H "Content-Type: application/json" -d '{
  "views": {
    "by_category": {
      "map": "function(doc) { if (doc.type === '\''product'\'') emit(doc.category_id, doc); }"
    }
  }
}'
```

### Test schema changes for SchemaZero

```bash
# Update a document to add a new field (schema evolution)
REV=$(curl -s "$COUCH/testdb/user:1" | python3 -c "import sys,json; print(json.load(sys.stdin)['_rev'])")
curl -X PUT "$COUCH/testdb/user:1" -H "Content-Type: application/json" -d "{
  \"_rev\": \"$REV\",
  \"type\": \"user\",
  \"name\": \"Alice Chen\",
  \"email\": \"alice@example.com\",
  \"phone\": \"+1-555-0100\",
  \"created_at\": \"2024-01-01\"
}"

# Delete a design document index (SchemaZero should catch this)
REV=$(curl -s "$COUCH/testdb/_design/products" | python3 -c "import sys,json; print(json.load(sys.stdin)['_rev'])")
curl -X DELETE "$COUCH/testdb/_design/products?rev=$REV"

# Delete the database entirely (CRITICAL)
curl -X DELETE "$COUCH/testdb"
```

---

## CockroachDB

CockroachDB speaks the PostgreSQL wire protocol. Use the Postgres schema above with the connection string below.

### Install

**Linux**
```bash
curl https://binaries.cockroachdb.com/cockroach-v23.2.0.linux-amd64.tgz | tar -xz
sudo cp cockroach-v23.2.0.linux-amd64/cockroach /usr/local/bin/

# Start a single-node cluster for testing
cockroach start-single-node --insecure --listen-addr=localhost:26257 --background
```

**Windows**
Download: https://www.cockroachlabs.com/docs/stable/install-cockroachdb-windows

Or with Chocolatey:
```powershell
choco install cockroachdb
cockroach start-single-node --insecure --listen-addr=localhost:26257 --background
```

**Docker (any OS)**
```bash
docker run -d --name sz-cockroach \
  -p 26257:26257 -p 8080:8080 \
  cockroachdb/cockroach:v23.2.0 \
  start-single-node --insecure
```

### Connection string
```
postgresql://root@localhost:26257/testdb?sslmode=disable
```

CockroachDB Console: http://localhost:8080

### Schema + seed

Create the database first:

```bash
cockroach sql --insecure --host=localhost:26257 -e "CREATE DATABASE testdb;"
```

Then run the same SQL as the PostgreSQL section above, replacing `\c testdb` with `USE testdb;`. All PostgreSQL syntax is compatible.

### Test schema changes for SchemaZero

Same as the PostgreSQL test commands above.

---

## Connecting to SchemaZero

Once your database is running with the test schema:

1. Open your SchemaZero dashboard
2. Click **Add Database**
3. Paste the connection string for your engine
4. SchemaZero reads the full schema automatically

Then run any of the **Test schema changes** commands above. SchemaZero should:
- Detect the DDL event within seconds
- Score the risk (LOW / MEDIUM / HIGH / CRITICAL)
- Fire a Slack or webhook alert with a plain-English explanation of what changed and what to check

Use the HIGH and CRITICAL changes (dropping indexes, dropping columns) to verify alert routing end-to-end.
