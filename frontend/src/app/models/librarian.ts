export interface LibrarianOrderListItem {
  order_id: string;
  reader_id: string;
  reader_email: string;
  reader_first_name: string;
  reader_last_name: string;
  status: string;
  created_at: string;
}

export interface RequestedBook {
  isbn: string;
  title: string;
  quantity: number;
}

export interface AvailableBookItem {
  id: string;
  location: string;
  is_available: boolean;
}

export interface LibrarianOrderDetails {
  order_id: string;
  status: string;
  created_at: string;

  reader_email: string;
  reader_first_name: string;
  reader_last_name: string;

  books: RequestedBook[];
  available_items: Record<string, AvailableBookItem[]>;
}

export interface SummaryReaderInfo {
  first_name: string;
  last_name: string;
  email: string;
}

export interface SummaryBookInfo {
  isbn: string;
  title: string;
  authors: string;
  publisher: string;
  published_date: string;
  quantity: number;
  assigned_items: string[];
}

export interface LibrarianOrderSummary {
  order_id: string;
  status: string;
  created_at: string;

  reader: SummaryReaderInfo;
  books: SummaryBookInfo[];
}

export interface AssignItemsEntry {
  isbn: string;
  book_item_ids: string[];
}

export interface AssignItemsRequest {
  items: AssignItemsEntry[];
}

export interface SimpleMessageResponse {
  message: string;
}
