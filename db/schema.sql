-- Users table to store authentication details
create table users (
  telegram_id bigint primary key,
  access_token text,
  refresh_token text,
  expires_at bigint,
  athlete_id bigint,
  first_name text,
  last_name text,
  telegram_username text,
  phone_number text,
  is_verified boolean default false
);
-- Activities table to store Strava activities and calculated scores
create table activities (
  activity_id bigint primary key,
  user_id bigint references users(telegram_id),
  type text,
  distance float,
  weighted_distance float,
  name text,
  start_date timestamp
);
-- Allowed phone numbers table for verification
create table allowed_numbers (
  id bigint generated always as identity primary key,
  phone_number text unique not null,
  name text,
  created_at timestamp with time zone default now()
);

-- Activity weights table for scoring calculations
create table activity_weights (
  sport_type text primary key,
  weight decimal not null,
  icon text
);