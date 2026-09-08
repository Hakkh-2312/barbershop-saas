export interface Appointment {
  id: number;
  customer_id: number;
  service_id: number;
  customer_name: string;
  customer_phone: string;
  service_name: string;
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

export interface Tenant {
  id: number;
  name: string;
  phone: string | null;
  address: string | null;
  country_code: string | null;
  whatsapp_phone_number_id: string | null;
  subscription_status: string | null;
  trial_ends_at: string | null;
}

export interface TimeBlock {
  id: number;
  start_time: string;
  end_time: string;
  reason: string | null;
}

export interface Notification {
  id: number;
  type: string;
  title: string;
  message: string;
  customer_name: string | null;
  service_name: string | null;
  appointment_time: string | null;
  appointment_id: number | null;
  is_read: boolean;
  created_at: string;
}

export interface AnalyticsOverview {
  range: { start: string; end: string };
  revenue: number;
  new_customers: number;
  returning_customers: number;
  total_customers: number;
}
