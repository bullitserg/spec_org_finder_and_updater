get_procedures_data_query = '''SELECT
  p.id,
  p.version,
  p.registrationNumber,
  p.placerId,
  p.customerId,
  p.editDateTime,
  p.urlPrintForm
FROM procedures p
WHERE p.procedureTypeId = 10
AND p.actualId IS NULL
AND p.urlPrintForm is NOT NULL
AND p.editDateTime BETWEEN DATE_FORMAT(SUBDATE(NOW(), INTERVAL %s MINUTE), '%Y-%m-%d %H:00:00')
AND DATE_FORMAT(NOW(), '%Y-%m-%d %H:00:00')
ORDER BY p.editDateTime;'''


get_organization_id_query = '''SELECT
  o_spec.id
FROM organization o
  JOIN organization o_spec
    ON o_spec.inn = o.inn
    AND o_spec.kpp = o.kpp
    AND o_spec.organizationTypeId = 21
    AND o_spec.actualId IS NULL
WHERE o.oosRegistrationNumber = '%s'
AND o.actualId IS NULL
;'''