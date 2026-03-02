INSERT INTO master.doc_category(code, name, descr, lang_code, is_active, cr_by, cr_dtimes, upd_by, upd_dtimes, is_deleted, del_dtimes) VALUES
('POI','Proof of Identity','Identity Proof','eng',TRUE,'superadmin',TIMESTAMP '2018-12-10 11:42:52.994',NULL,NULL,NULL,NULL),
('POI','Proof of Identity','Identity Proof','ara',TRUE,'superadmin',TIMESTAMP '2018-12-10 11:42:52.994',NULL,NULL,NULL,NULL),
('POA','Proof of Address','Address Proof','eng',TRUE,'superadmin',TIMESTAMP '2018-12-10 11:42:52.994',NULL,NULL,NULL,NULL),
('POA','Proof of Address','Address Proof','ara',TRUE,'superadmin',TIMESTAMP '2018-12-10 11:42:52.994',NULL,NULL,NULL,NULL),
('POR','Proof of Relationship','Proof Relationship','eng',TRUE,'superadmin',TIMESTAMP '2018-12-10 11:42:52.994',NULL,NULL,NULL,NULL),
('POR','Proof of Relationship','Proof Relationship','ara',TRUE,'superadmin',TIMESTAMP '2018-12-10 11:42:52.994',NULL,NULL,NULL,NULL),
('POB','Proof of Birth','Proof of Birth','eng',TRUE,'superadmin',TIMESTAMP '2018-12-10 11:42:52.994',NULL,NULL,NULL,NULL)
ON CONFLICT DO NOTHING;

INSERT INTO master.doc_type(code, name, descr, lang_code, is_active, cr_by, cr_dtimes, upd_by, upd_dtimes, is_deleted, del_dtimes) VALUES
('CIN','Certification of Exception','Certificate of Exception','eng',TRUE,'superadmin',TIMESTAMP '2018-12-10 11:42:52.994',NULL,NULL,NULL,NULL),
('DOC002','PAN card','PAN card','eng',TRUE,'superadmin',TIMESTAMP '2018-12-10 11:42:52.994',NULL,NULL,NULL,NULL),
('COR','Certificate of residence','Proof of Resident','eng',TRUE,'superadmin',TIMESTAMP '2018-12-10 11:42:52.994',NULL,NULL,NULL,NULL),
('C1','Certificate of residence1','Proof of Resident','eng',TRUE,'superadmin',TIMESTAMP '2018-12-10 11:42:52.994',NULL,NULL,NULL,NULL)
ON CONFLICT DO NOTHING;

INSERT INTO master.valid_document(doctyp_code, doccat_code, lang_code, is_active, cr_by, cr_dtimes, upd_by, upd_dtimes, is_deleted, del_dtimes) VALUES
('CIN','POI','eng',TRUE,'superadmin',TIMESTAMP '2018-12-10 11:42:52.994',NULL,NULL,NULL,NULL),
('CIN','POI','ara',TRUE,'superadmin',TIMESTAMP '2018-12-10 11:42:52.994',NULL,NULL,NULL,NULL),
('COR','POA','eng',TRUE,'superadmin',TIMESTAMP '2018-12-10 11:42:52.994',NULL,NULL,NULL,NULL),
('DOC002','POI','eng',TRUE,'superadmin',TIMESTAMP '2018-12-10 11:42:52.994',NULL,NULL,NULL,NULL)
ON CONFLICT DO NOTHING;
