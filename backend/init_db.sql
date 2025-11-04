CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
SET search_path TO public;

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

CREATE TYPE user_role AS ENUM ('reader', 'librarian', 'courier');
CREATE TYPE order_status AS ENUM ('new', 'prepared', 'in_transit', 'ready_for_pickup', 'picked_up', 'return_in_progress', 'returned', 'canceled');
CREATE TYPE shipment_mode AS ENUM ('delivery', 'return');
CREATE TYPE shipment_status AS ENUM ('created', 'placed_in_locker', 'retrieved_by_user', 'collected_by_courier', 'completed');
CREATE TYPE cart_status AS ENUM ('active', 'submitted');
CREATE TYPE book_location AS ENUM ('library', 'transit', 'locker', 'borrowed');

CREATE TABLE "user" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    password TEXT NOT NULL,
    role user_role NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

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

CREATE UNIQUE INDEX uq_user_email_lower ON "user"(LOWER(email));
CREATE INDEX idx_user_role ON "user"(role);

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

CREATE INDEX idx_book_title   ON book USING gin (to_tsvector('simple', title));
CREATE INDEX idx_book_authors ON book USING gin (to_tsvector('simple', authors));

CREATE TABLE book_item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    isbn TEXT NOT NULL REFERENCES book(isbn) ON DELETE CASCADE ON UPDATE CASCADE,
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    current_location book_location NOT NULL DEFAULT 'library',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_book_item_isbn         ON book_item(isbn);
CREATE INDEX idx_book_item_availability ON book_item(is_available);
CREATE INDEX idx_book_item_location     ON book_item(current_location);

CREATE TABLE cart (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES "user"(id) ON DELETE CASCADE,
    status cart_status NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cart_user_id ON cart(user_id);

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

CREATE TABLE cart_item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cart_id UUID NOT NULL REFERENCES cart(id) ON DELETE CASCADE,
    isbn TEXT NOT NULL REFERENCES book(isbn),
    quantity INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    added_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (cart_id, isbn)
);

CREATE INDEX idx_cart_item_cart_id ON cart_item(cart_id);

CREATE TABLE "order" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reader_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    status order_status NOT NULL DEFAULT 'new',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz
);

CREATE INDEX idx_order_reader ON "order"(reader_id);
CREATE INDEX idx_order_status ON "order"(status);

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

CREATE TABLE order_item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES "order"(id) ON DELETE CASCADE,
    book_item_id UUID NOT NULL REFERENCES book_item(id),
    due_date timestamptz,
    returned_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_order_dates CHECK (returned_at IS NULL OR returned_at >= due_date),
    CONSTRAINT uq_book_item_once UNIQUE (book_item_id)
);

CREATE INDEX idx_order_item_order     ON order_item(order_id);
CREATE INDEX idx_order_item_book_item ON order_item(book_item_id);

CREATE TABLE locker (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    locker_code TEXT UNIQUE NOT NULL,
    street TEXT NOT NULL,
    city TEXT NOT NULL,
    postal_code VARCHAR(10) NOT NULL,
    location GEOGRAPHY(Point, 4326) NOT NULL
);

CREATE INDEX idx_locker_location ON locker USING GIST(location);
CREATE INDEX idx_locker_city  ON locker(city);

CREATE TABLE locker_box (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    locker_id UUID NOT NULL REFERENCES locker(id) ON DELETE CASCADE,
    number INT NOT NULL CHECK (number > 0),
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (locker_id, number)
);

CREATE INDEX idx_locker_box_available ON locker_box(is_available);

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

CREATE INDEX idx_shipment_order  ON locker_shipment(order_id);
CREATE INDEX idx_shipment_mode   ON locker_shipment(mode);
CREATE INDEX idx_shipment_status ON locker_shipment(status);

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

CREATE OR REPLACE FUNCTION sync_book_item_availability()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE book_item SET is_available = FALSE, current_location = 'borrowed' WHERE id = NEW.book_item_id;
  ELSIF TG_OP = 'UPDATE' AND NEW.returned_at IS NOT NULL THEN
    UPDATE book_item SET is_available = TRUE, current_location = 'library' WHERE id = NEW.book_item_id;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE book_item SET is_available = TRUE, current_location = 'library' WHERE id = OLD.book_item_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_order_item_sync
AFTER INSERT OR UPDATE OR DELETE ON order_item
FOR EACH ROW
EXECUTE FUNCTION sync_book_item_availability();

CREATE OR REPLACE FUNCTION auto_close_old_carts()
RETURNS void AS $$
BEGIN
  UPDATE cart SET status = 'submitted' WHERE status = 'active' AND created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;