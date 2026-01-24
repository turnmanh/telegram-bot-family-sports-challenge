-- Run this SQL in your Supabase SQL Editor to restrict allowed activities
-- 1. Truncate (empty) the weights table to remove old entries
TRUNCATE activity_weights;
-- 2. Insert ONLY allowed types
INSERT INTO activity_weights (sport_type, weight, icon)
VALUES ('Run', 1.0, '🏃'),
    ('Ride', 0.25, '🚴'),
    ('Swim', 4.0, '🏊');
-- 3. Optionally: Delete existing activities from the DB that are no longer allowed
-- This ensures that /stats and leaderboard are updated immediately
DELETE FROM activities
WHERE type NOT IN (
        'Run',
        'Ride',
        'Swim',
        'VirtualRun',
        'VirtualRide'
    );
-- Note: 'VirtualRun'/'VirtualRide' etc should be matched if they map to Run/Ride in your logic.
-- If you want strictly ONLY 'Run', 'Ride', 'Swim' from Strava:
-- DELETE FROM activities
-- WHERE type NOT IN ('Run', 'Ride', 'Swim');