export interface PaginatedList<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiError {
  status: number;
  code: string;
  message: string;
}
