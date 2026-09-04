export interface Appointment {
  id: number;
  customer_id: number;
  service_id: number;
  start_time: string;
  end_time: string;
  status: string;
}

export interface Customer {
  id: number;
  name: string;
  phone: string;
  email: string | null;
}

export interface Service {
  id: number;
  name: string;
  duration_minutes: number;
  price: number;
}

export interface WorkingHours {
  id: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_closed: boolean;
}

export interface Token {
  access_token: string;
  token_type: string;
}
