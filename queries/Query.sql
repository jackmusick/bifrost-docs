DO $$
-- DECLARE
--   org_uuid UUID;
BEGIN
--   SELECT id INTO org_uuid FROM organizations WHERE name = 'Covi, Inc.';
  DELETE FROM passwords;
  DELETE FROM configurations;
  DELETE FROM custom_assets;
  DELETE FROM organizations;
END $$;