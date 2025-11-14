export interface CheckoutBookItem {
  isbn: string;
  title: string;
  authors: string;
  quantity: number;
}

export interface CheckoutSummaryResponse {
  user_id: string;
  first_name: string;
  last_name: string;
  email: string;
  total_items: number;
  distinct_titles: number;
  books: CheckoutBookItem[];
}

export interface LockerResponse {
  id: string;
  locker_code: string;
  street: string;
  city: string;
  postal_code: string;
  lat: number;
  lon: number;
  distance_km?: number | null;
}

export interface CheckoutSubmitResponse {
  order_id: string;
  shipment_id: string;
  pickup_code: string;
  locker_code: string;
  city: string;
  postal_code: string;
  message: string;
}
