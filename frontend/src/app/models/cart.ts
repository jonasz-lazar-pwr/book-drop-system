import { UUID } from '@models/types';

export interface CartItem {
  isbn: string;
  title: string;
  authors: string;
  thumbnail?: string;
  quantity: number;
  available_count?: number;
}

export interface CartResponse {
  id: UUID;
  user_id: UUID;
  items: CartItem[];
  total_items: number;
}

export interface AddItemRequest {
  isbn: string;
}

export interface UpdateQuantityRequest {
  quantity: number;
}
