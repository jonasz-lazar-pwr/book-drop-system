// models/order.ts
import { UUID } from '@models/types';

export interface Order {
  id: UUID;
  reader_id: UUID;
  status: OrderStatus;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
  shipment?: LockerShipment;
}

export interface OrderItem {
  id: UUID;
  order_id: UUID;
  book_item_id: UUID;
  isbn: string;
  title: string;
  authors: string;
  publisher?: string;
  thumbnail?: string;
  due_date: string;
  returned_at?: string;
}

export interface LockerShipment {
  id: UUID;
  order_id: UUID;
  locker: Locker;
  mode: 'delivery' | 'return';
  status: ShipmentStatus;
  pickup_code: string;
  placed_at?: string;
  created_at: string;
}

export interface Locker {
  id: UUID;
  locker_code: string;
  street: string;
  city: string;
  postal_code: string;
  latitude: number;
  longitude: number;
}

export type OrderStatus =
  | 'new'
  | 'prepared'
  | 'in_transit'
  | 'ready_for_pickup'
  | 'picked_up'
  | 'return_in_progress'
  | 'returned'
  | 'canceled';

export type ShipmentStatus =
  | 'created'
  | 'placed_in_locker'
  | 'retrieved_by_user'
  | 'collected_by_courier'
  | 'completed';
