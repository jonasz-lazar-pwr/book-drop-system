-- =====================================================
--  BookDrop — Database Initialization Script (v1.1)
--  PostgreSQL 15 + PostGIS 3.4
-- =====================================================

-- =====================================================
--  Environment setup
-- =====================================================
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
SET search_path TO public;

-- =====================================================
--  Reset (drop existing tables and ENUM types)
-- =====================================================
DROP TABLE IF EXISTS locker_shipment CASCADE;
DROP TABLE IF EXISTS order_item CASCADE;
DROP TABLE IF EXISTS "order" CASCADE;
DROP TABLE IF EXISTS cart_item CASCADE;
DROP TABLE IF EXISTS cart CASCADE;
DROP TABLE IF EXISTS locker_box CASCADE;
DROP TABLE IF EXISTS locker CASCADE;
DROP TABLE IF EXISTS book_item CASCADE;
DROP TABLE IF EXISTS book CASCADE;
DROP TABLE IF EXISTS "user" CASCADE;

DROP TYPE IF EXISTS user_role, order_status, shipment_mode, shipment_status, cart_status, book_location CASCADE;

-- =====================================================
--  ENUM definitions
-- =====================================================
CREATE TYPE user_role AS ENUM ('reader', 'librarian', 'courier');
COMMENT ON TYPE user_role IS 'User role in the system.';

CREATE TYPE order_status AS ENUM (
    'new', 'prepared', 'in_transit', 'ready_for_pickup',
    'picked_up', 'return_in_progress', 'returned', 'canceled'
);
COMMENT ON TYPE order_status IS 'Lifecycle of an order.';

CREATE TYPE shipment_mode AS ENUM ('delivery', 'return');
COMMENT ON TYPE shipment_mode IS 'Shipment direction: delivery or return.';

CREATE TYPE shipment_status AS ENUM (
    'created', 'placed_in_locker', 'retrieved_by_user',
    'collected_by_courier', 'completed'
);
COMMENT ON TYPE shipment_status IS 'Stages of a shipment process.';

CREATE TYPE cart_status AS ENUM ('active', 'submitted');
COMMENT ON TYPE cart_status IS 'Shopping cart lifecycle.';

CREATE TYPE book_location AS ENUM ('library', 'transit', 'locker', 'borrowed');
COMMENT ON TYPE book_location IS 'Physical location of a book copy.';

-- =====================================================
--  Table: user
-- =====================================================
CREATE TABLE "user" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    password TEXT NOT NULL,
    role user_role NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "user" IS 'System users (readers, librarians, couriers).';

-- Force lowercase emails
CREATE OR REPLACE FUNCTION enforce_lowercase_email()
RETURNS TRIGGER AS $$
BEGIN
  NEW.email := LOWER(NEW.email);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_user_lower_email
BEFORE INSERT OR UPDATE ON "user"
FOR EACH ROW
EXECUTE FUNCTION enforce_lowercase_email();

-- Enforce unique lowercase email
CREATE UNIQUE INDEX uq_user_email_lower ON "user"(LOWER(email));
CREATE INDEX idx_user_role ON "user"(role);

-- =====================================================
--  Table: book
-- =====================================================
CREATE TABLE book (
    isbn TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT NOT NULL,
    publisher TEXT,
    published_date TEXT,
    thumbnail TEXT,
    description TEXT,
    source TEXT
);
COMMENT ON TABLE book IS 'Books available in the library catalog.';
COMMENT ON COLUMN book.source IS 'Data source: manual | open_library | google_books.';

-- Full-text indexes
CREATE INDEX idx_book_title   ON book USING gin (to_tsvector('simple', title));
CREATE INDEX idx_book_authors ON book USING gin (to_tsvector('simple', authors));

-- =====================================================
--  Table: book_item
-- =====================================================
CREATE TABLE book_item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    isbn TEXT NOT NULL REFERENCES book(isbn) ON DELETE CASCADE ON UPDATE CASCADE,
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    current_location book_location NOT NULL DEFAULT 'library',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE book_item IS 'Physical copies of books.';
CREATE INDEX idx_book_item_isbn         ON book_item(isbn);
CREATE INDEX idx_book_item_availability ON book_item(is_available);
CREATE INDEX idx_book_item_location     ON book_item(current_location);

-- =====================================================
--  Table: cart
-- =====================================================
CREATE TABLE cart (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    status cart_status NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE cart IS 'User shopping carts. Each user may have multiple carts (historical or active), but only one ACTIVE at a time.';

CREATE INDEX idx_cart_user_id ON cart(user_id);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_cart_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_cart_updated
BEFORE UPDATE ON cart
FOR EACH ROW
EXECUTE FUNCTION update_cart_timestamp();

-- =====================================================
--  Table: cart_item
-- =====================================================
CREATE TABLE cart_item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cart_id UUID NOT NULL REFERENCES cart(id) ON DELETE CASCADE,
    isbn TEXT NOT NULL REFERENCES book(isbn),
    quantity INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    added_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (cart_id, isbn)
);
COMMENT ON TABLE cart_item IS 'Books added to user cart. No physical copy assigned yet.';
CREATE INDEX idx_cart_item_cart_id ON cart_item(cart_id);

-- =====================================================
--  Table: order
-- =====================================================
CREATE TABLE "order" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reader_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    status order_status NOT NULL DEFAULT 'new',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz
);
COMMENT ON TABLE "order" IS 'Formalized book order created from cart contents.';
CREATE INDEX idx_order_reader ON "order"(reader_id);
CREATE INDEX idx_order_status ON "order"(status);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_order_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_order_updated
BEFORE UPDATE ON "order"
FOR EACH ROW
EXECUTE FUNCTION update_order_timestamp();

-- =====================================================
--  Table: order_item
-- =====================================================
CREATE TABLE order_item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES "order"(id) ON DELETE CASCADE,
    book_item_id UUID REFERENCES book_item(id),
    due_date timestamptz,
    returned_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_order_dates CHECK (returned_at IS NULL OR returned_at >= due_date),
    CONSTRAINT uq_book_item_once UNIQUE (book_item_id)
);
COMMENT ON TABLE order_item IS 'Each record = one borrowed physical copy with return tracking.';
CREATE INDEX idx_order_item_order     ON order_item(order_id);
CREATE INDEX idx_order_item_book_item ON order_item(book_item_id);

-- =====================================================
--  Table: locker
-- =====================================================
CREATE TABLE locker (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    locker_code TEXT UNIQUE NOT NULL,
    street TEXT NOT NULL,
    city TEXT NOT NULL,
    postal_code VARCHAR(10) NOT NULL,
    location GEOGRAPHY(Point, 4326) NOT NULL
);
COMMENT ON TABLE locker IS 'Lockers used for book deliveries and returns.';
CREATE INDEX idx_locker_location ON locker USING GIST(location);
CREATE INDEX idx_locker_city  ON locker(city);

-- =====================================================
--  Table: locker_box
-- =====================================================
CREATE TABLE locker_box (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    locker_id UUID NOT NULL REFERENCES locker(id) ON DELETE CASCADE,
    number INT NOT NULL CHECK (number > 0),
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (locker_id, number)
);
COMMENT ON TABLE locker_box IS 'Individual boxes inside a locker.';
CREATE INDEX idx_locker_box_available ON locker_box(is_available);

-- =====================================================
--  Table: locker_shipment
-- =====================================================
CREATE TABLE locker_shipment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES "order"(id) ON DELETE CASCADE,
    locker_box_id UUID NOT NULL REFERENCES locker_box(id),
    mode shipment_mode NOT NULL,
    status shipment_status NOT NULL,
    pickup_code VARCHAR(8) UNIQUE,
    placed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_pickup_code_length CHECK (pickup_code IS NULL OR char_length(pickup_code) = 8)
);
COMMENT ON TABLE locker_shipment IS 'Logistics operations: deliveries and returns.';
CREATE INDEX idx_shipment_order  ON locker_shipment(order_id);
CREATE INDEX idx_shipment_mode   ON locker_shipment(mode);
CREATE INDEX idx_shipment_status ON locker_shipment(status);

-- Auto-generate random pickup code
CREATE OR REPLACE FUNCTION generate_pickup_code()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.pickup_code IS NULL THEN
    NEW.pickup_code := substring(encode(gen_random_bytes(6), 'hex') from 1 for 8);
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_locker_shipment_pickup_code
BEFORE INSERT ON locker_shipment
FOR EACH ROW
EXECUTE FUNCTION generate_pickup_code();

-- =====================================================
--  Synchronization triggers
-- =====================================================

-- Auto-update book availability on borrow/return/delete
CREATE OR REPLACE FUNCTION sync_book_item_availability()
RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT' AND NEW.book_item_id IS NULL)
     OR (TG_OP = 'UPDATE' AND NEW.book_item_id IS NULL)
     OR (TG_OP = 'DELETE' AND OLD.book_item_id IS NULL) THEN
    RETURN NEW;
  END IF;

  IF TG_OP = 'INSERT' THEN
    UPDATE book_item
    SET is_available = FALSE,
        current_location = 'borrowed'
    WHERE id = NEW.book_item_id;

  ELSIF TG_OP = 'UPDATE' AND NEW.returned_at IS NOT NULL THEN
    UPDATE book_item
    SET is_available = TRUE,
        current_location = 'library'
    WHERE id = NEW.book_item_id;

  ELSIF TG_OP = 'DELETE' THEN
    UPDATE book_item
    SET is_available = TRUE,
        current_location = 'library'
    WHERE id = OLD.book_item_id;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_order_item_sync
AFTER INSERT OR UPDATE OR DELETE ON order_item
FOR EACH ROW
EXECUTE FUNCTION sync_book_item_availability();

-- =====================================================
--  Maintenance helper (optional)
-- =====================================================
CREATE OR REPLACE FUNCTION auto_close_old_carts()
RETURNS void AS $$
BEGIN
  UPDATE cart
  SET status = 'submitted'
  WHERE status = 'active'
    AND created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- =====================================================
--  Verification
-- =====================================================
-- \dt             -- list all tables
-- \dT+            -- list ENUM types