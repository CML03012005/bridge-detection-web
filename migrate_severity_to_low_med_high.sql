-- Migration: severity_level rename
--   LOCALIZED   → LOW
--   DISTRIBUTED → MEDIUM
--   EXTENSIVE   → HIGH
--
-- Run via phpMyAdmin SQL tab against the bridge_inspection database.

USE bridge_inspection;

-- Step 1: widen ENUM so both old and new values are temporarily valid
ALTER TABLE inspections
    MODIFY severity_level ENUM(
        'NONE', 'LOCALIZED', 'DISTRIBUTED', 'EXTENSIVE',
        'LOW', 'MEDIUM', 'HIGH'
    ) DEFAULT 'NONE';

-- Step 2: rewrite existing rows
UPDATE inspections SET severity_level = 'LOW'    WHERE severity_level = 'LOCALIZED';
UPDATE inspections SET severity_level = 'MEDIUM' WHERE severity_level = 'DISTRIBUTED';
UPDATE inspections SET severity_level = 'HIGH'   WHERE severity_level = 'EXTENSIVE';

-- Step 3: narrow ENUM back down to the final value set
ALTER TABLE inspections
    MODIFY severity_level ENUM('NONE', 'LOW', 'MEDIUM', 'HIGH') DEFAULT 'NONE';

-- Verify
SELECT severity_level, COUNT(*) AS n
FROM inspections
GROUP BY severity_level;
