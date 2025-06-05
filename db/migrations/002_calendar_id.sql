ALTER TABLE busy_times
  ADD COLUMN IF NOT EXISTS calendar_id TEXT DEFAULT 'default';
