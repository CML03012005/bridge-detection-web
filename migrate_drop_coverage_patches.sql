-- Migration: drop coverage_ratio and patch_count columns.
--
-- Severity is now driven entirely by the YOLO model's per-detection class
-- (max-wins). Pixel-based coverage and connected-component patches are no
-- longer computed or stored.
--
-- Run via phpMyAdmin SQL tab against the bridge_inspection database.

USE bridge_inspection;

ALTER TABLE inspections
    DROP COLUMN coverage_ratio,
    DROP COLUMN patch_count;

-- Verify
DESCRIBE inspections;
