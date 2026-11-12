CREATE TABLE approval_decisions (
	id VARCHAR(36) NOT NULL, 
	run_id VARCHAR(36) NOT NULL, 
	stage_id VARCHAR(36) NOT NULL, 
	actor_id VARCHAR(36) NOT NULL, 
	decision VARCHAR(30) NOT NULL, 
	comment TEXT NOT NULL, 
	decided_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_approval_run_stage_decision UNIQUE (run_id, stage_id), 
	FOREIGN KEY(run_id) REFERENCES approval_runs (id), 
	FOREIGN KEY(stage_id) REFERENCES approval_stages (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id)
);
CREATE TABLE approval_runs (
	id VARCHAR(36) NOT NULL, 
	template_id VARCHAR(36) NOT NULL, 
	document_version_id VARCHAR(36) NOT NULL, 
	current_position INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	started_by VARCHAR(36) NOT NULL, 
	started_at DATETIME NOT NULL, 
	completed_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_approval_run_version_template UNIQUE (document_version_id, template_id), 
	FOREIGN KEY(template_id) REFERENCES approval_templates (id), 
	FOREIGN KEY(document_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(started_by) REFERENCES users (id)
);
CREATE TABLE approval_stage_assignments (
	run_id VARCHAR(36) NOT NULL, 
	stage_id VARCHAR(36) NOT NULL, 
	due_at DATETIME, 
	delegate_id VARCHAR(36), 
	expires_at DATETIME, 
	assigned_by VARCHAR(36), 
	reason TEXT NOT NULL, 
	PRIMARY KEY (run_id, stage_id), 
	FOREIGN KEY(run_id) REFERENCES approval_runs (id), 
	FOREIGN KEY(stage_id) REFERENCES approval_stages (id), 
	FOREIGN KEY(delegate_id) REFERENCES users (id), 
	FOREIGN KEY(assigned_by) REFERENCES users (id)
);
CREATE TABLE approval_stage_policies (
	stage_id VARCHAR(36) NOT NULL, 
	due_days INTEGER NOT NULL, 
	PRIMARY KEY (stage_id), 
	FOREIGN KEY(stage_id) REFERENCES approval_stages (id)
);
CREATE TABLE approval_stages (
	id VARCHAR(36) NOT NULL, 
	template_id VARCHAR(36) NOT NULL, 
	position INTEGER NOT NULL, 
	name VARCHAR(140) NOT NULL, 
	reviewer_role_id VARCHAR(36) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_approval_stage_position UNIQUE (template_id, position), 
	FOREIGN KEY(template_id) REFERENCES approval_templates (id), 
	FOREIGN KEY(reviewer_role_id) REFERENCES roles (id)
);
CREATE TABLE approval_templates (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(140) NOT NULL, 
	folder_slug VARCHAR(10) NOT NULL, 
	document_type VARCHAR(100) NOT NULL, 
	active BOOLEAN NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE archived_emails (
	id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	document_version_id VARCHAR(36) NOT NULL, 
	message_id VARCHAR(250) NOT NULL, 
	subject VARCHAR(300) NOT NULL, 
	sender VARCHAR(300) NOT NULL, 
	recipients TEXT NOT NULL, 
	carbon_copy TEXT NOT NULL, 
	sent_at_raw VARCHAR(180) NOT NULL, 
	body_excerpt TEXT NOT NULL, 
	attachments_json TEXT NOT NULL, 
	archived_by VARCHAR(36) NOT NULL, 
	archived_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	UNIQUE (document_version_id), 
	FOREIGN KEY(document_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(archived_by) REFERENCES users (id)
);
CREATE TABLE audit_events (
	id VARCHAR(36) NOT NULL, 
	action VARCHAR(70) NOT NULL, 
	actor_id VARCHAR(36), 
	target_type VARCHAR(60) NOT NULL, 
	target_id VARCHAR(36) NOT NULL, 
	detail TEXT NOT NULL, 
	occurred_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE business_order_launches (
	launch_id VARCHAR(36) NOT NULL, 
	order_id VARCHAR(36) NOT NULL, 
	linked_by VARCHAR(36) NOT NULL, 
	linked_at DATETIME NOT NULL, 
	PRIMARY KEY (launch_id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(order_id) REFERENCES business_orders (id), 
	FOREIGN KEY(linked_by) REFERENCES users (id)
);
CREATE TABLE business_orders (
	id VARCHAR(36) NOT NULL, 
	client_id VARCHAR(36) NOT NULL, 
	reference VARCHAR(100) NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (client_id, reference), 
	FOREIGN KEY(client_id) REFERENCES partners (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE business_value_revisions (
	id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	"key" VARCHAR(70) NOT NULL, 
	revision INTEGER NOT NULL, 
	value_text VARCHAR(45) NOT NULL, 
	unit VARCHAR(30) NOT NULL, 
	source_version_id VARCHAR(36) NOT NULL, 
	reason TEXT NOT NULL, 
	recorded_by VARCHAR(36) NOT NULL, 
	recorded_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_business_value_revision UNIQUE (launch_id, "key", revision), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(source_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(recorded_by) REFERENCES users (id)
);
CREATE TABLE client_publications (
	id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	document_version_id VARCHAR(36) NOT NULL, 
	client_name VARCHAR(150) NOT NULL, 
	reason TEXT NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	revoked_by VARCHAR(36), 
	revoked_at DATETIME, 
	revoked_reason TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(document_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(created_by) REFERENCES users (id), 
	FOREIGN KEY(revoked_by) REFERENCES users (id)
);
CREATE TABLE client_requirements (
	id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	source_version_id VARCHAR(36) NOT NULL, 
	title VARCHAR(180) NOT NULL, 
	category VARCHAR(48) NOT NULL, 
	description TEXT NOT NULL, 
	source_excerpt VARCHAR(500) NOT NULL, 
	evidence_version_id VARCHAR(36), 
	review_note TEXT NOT NULL, 
	reviewed_by VARCHAR(36), 
	reviewed_at DATETIME, 
	reviewed_source_version_id VARCHAR(36), 
	reviewed_evidence_version_id VARCHAR(36), 
	created_by VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(source_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(evidence_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(reviewed_by) REFERENCES users (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE completeness_profiles (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	description TEXT NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE completeness_rules (
	id VARCHAR(36) NOT NULL, 
	profile_id VARCHAR(36) NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	folder_slug VARCHAR(10) NOT NULL, 
	document_type VARCHAR(100) NOT NULL, 
	due_phase VARCHAR(30) NOT NULL, 
	requires_validation BOOLEAN NOT NULL, 
	active BOOLEAN NOT NULL, 
	guidance TEXT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_profile_folder_document_type UNIQUE (profile_id, folder_slug, document_type), 
	FOREIGN KEY(profile_id) REFERENCES completeness_profiles (id)
);
CREATE TABLE confirmed_extracted_fields (
	id VARCHAR(36) NOT NULL, 
	document_version_id VARCHAR(36) NOT NULL, 
	field_key VARCHAR(50) NOT NULL, 
	value VARCHAR(140) NOT NULL, 
	unit VARCHAR(30) NOT NULL, 
	source_excerpt VARCHAR(180) NOT NULL, 
	confirmed_by VARCHAR(36) NOT NULL, 
	confirmed_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (document_version_id, field_key), 
	FOREIGN KEY(document_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(confirmed_by) REFERENCES users (id)
);
CREATE TABLE cross_document_rules (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(140) NOT NULL, 
	field_key VARCHAR(70) NOT NULL, 
	left_doc_type VARCHAR(100) NOT NULL, 
	right_doc_type VARCHAR(100) NOT NULL, 
	left_folder VARCHAR(10) NOT NULL, 
	right_folder VARCHAR(10) NOT NULL, 
	tolerance_text VARCHAR(35) NOT NULL, 
	active BOOLEAN NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE document_data (
	id VARCHAR(36) NOT NULL, 
	document_version_id VARCHAR(36) NOT NULL, 
	field_key VARCHAR(70) NOT NULL, 
	value_text VARCHAR(50) NOT NULL, 
	unit VARCHAR(30) NOT NULL, 
	recorded_by VARCHAR(36) NOT NULL, 
	recorded_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_document_datum_field UNIQUE (document_version_id, field_key), 
	FOREIGN KEY(document_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(recorded_by) REFERENCES users (id)
);
CREATE TABLE document_excel_policies (
	document_id VARCHAR(36) NOT NULL, 
	cells_json TEXT NOT NULL, 
	configured_by VARCHAR(36) NOT NULL, 
	PRIMARY KEY (document_id), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	FOREIGN KEY(configured_by) REFERENCES users (id)
);
CREATE TABLE document_reviews (
	id VARCHAR(36) NOT NULL, 
	document_version_id VARCHAR(36) NOT NULL, 
	decision VARCHAR(30) NOT NULL, 
	comment TEXT NOT NULL, 
	reviewed_by VARCHAR(36) NOT NULL, 
	reviewed_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(reviewed_by) REFERENCES users (id)
);
CREATE TABLE document_versions (
	id VARCHAR(36) NOT NULL, 
	document_id VARCHAR(36) NOT NULL, 
	number INTEGER NOT NULL, 
	original_name VARCHAR(250) NOT NULL, 
	disk_name VARCHAR(80) NOT NULL, 
	content_type VARCHAR(120) NOT NULL, 
	size INTEGER NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	uploaded_by VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (document_id, number), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	UNIQUE (disk_name), 
	FOREIGN KEY(uploaded_by) REFERENCES users (id)
);
CREATE TABLE documents (
	id VARCHAR(36) NOT NULL, 
	folder_id VARCHAR(36) NOT NULL, 
	title VARCHAR(220) NOT NULL, 
	doc_type VARCHAR(100) NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(folder_id) REFERENCES folders (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE email_commitments (
	id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	email_id VARCHAR(36) NOT NULL, 
	description VARCHAR(650) NOT NULL, 
	responsible VARCHAR(250) NOT NULL, 
	due_date VARCHAR(10), 
	condition VARCHAR(500) NOT NULL, 
	source_excerpt VARCHAR(650) NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	decision_note TEXT NOT NULL, 
	confirmed_by VARCHAR(36) NOT NULL, 
	confirmed_at DATETIME NOT NULL, 
	updated_by VARCHAR(36), 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(email_id) REFERENCES archived_emails (id), 
	FOREIGN KEY(confirmed_by) REFERENCES users (id), 
	FOREIGN KEY(updated_by) REFERENCES users (id)
);
CREATE TABLE excel_inspections (
	id VARCHAR(36) NOT NULL, 
	document_version_id VARCHAR(36) NOT NULL, 
	baseline_version_id VARCHAR(36), 
	status VARCHAR(24) NOT NULL, 
	scanned_cells INTEGER NOT NULL, 
	formula_count INTEGER NOT NULL, 
	findings_json TEXT NOT NULL, 
	inspected_by VARCHAR(36) NOT NULL, 
	inspected_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_excel_inspection_version UNIQUE (document_version_id), 
	FOREIGN KEY(document_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(baseline_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(inspected_by) REFERENCES users (id)
);
CREATE TABLE folders (
	id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	slug VARCHAR(10) NOT NULL, 
	label VARCHAR(70) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (launch_id, slug), 
	FOREIGN KEY(launch_id) REFERENCES launches (id)
);
CREATE TABLE impact_alerts (
	id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	rule_id VARCHAR(36) NOT NULL, 
	source_ref_id VARCHAR(36) NOT NULL, 
	old_value VARCHAR(70), 
	new_value VARCHAR(70), 
	status VARCHAR(35) NOT NULL, 
	resolution_note TEXT NOT NULL, 
	resolved_by VARCHAR(36), 
	created_at DATETIME NOT NULL, 
	resolved_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_rule_source_alert UNIQUE (rule_id, source_ref_id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(rule_id) REFERENCES impact_rules (id), 
	FOREIGN KEY(resolved_by) REFERENCES users (id)
);
CREATE TABLE impact_rules (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(130) NOT NULL, 
	source_kind VARCHAR(20) NOT NULL, 
	source_key VARCHAR(100) NOT NULL, 
	source_folder VARCHAR(10) NOT NULL, 
	target_folder VARCHAR(10) NOT NULL, 
	instruction TEXT NOT NULL, 
	active BOOLEAN NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE impact_simulations (
	id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	payload_json TEXT NOT NULL, 
	result_json TEXT NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE internal_notifications (
	id VARCHAR(36) NOT NULL, 
	recipient_id VARCHAR(36) NOT NULL, 
	event_key VARCHAR(160) NOT NULL, 
	kind VARCHAR(40) NOT NULL, 
	title VARCHAR(180) NOT NULL, 
	message TEXT NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	folder_slug VARCHAR(10) NOT NULL, 
	created_at DATETIME NOT NULL, 
	read_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_notification_recipient_event UNIQUE (recipient_id, event_key), 
	FOREIGN KEY(recipient_id) REFERENCES users (id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id)
);
CREATE TABLE launch_completeness (
	launch_id VARCHAR(36) NOT NULL, 
	profile_id VARCHAR(36), 
	phase VARCHAR(30) NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (launch_id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(profile_id) REFERENCES completeness_profiles (id)
);
CREATE TABLE launch_members (
	id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	granted_by VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_launch_member UNIQUE (launch_id, user_id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(granted_by) REFERENCES users (id)
);
CREATE TABLE launch_order_contexts (
	launch_id VARCHAR(36) NOT NULL, 
	order_type VARCHAR(100) NOT NULL, 
	PRIMARY KEY (launch_id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id)
);
CREATE TABLE launches (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(180) NOT NULL, 
	order_ref VARCHAR(100), 
	client_name VARCHAR(150), 
	orli_ref VARCHAR(100), 
	status VARCHAR(40) NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	restricted BOOLEAN DEFAULT '0' NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE material_lines (
	id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	reference VARCHAR(100) NOT NULL, 
	label VARCHAR(180) NOT NULL, 
	unit VARCHAR(12) NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (launch_id, reference), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE material_movements (
	id VARCHAR(36) NOT NULL, 
	line_id VARCHAR(36) NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	quantity NUMERIC(18, 3) NOT NULL, 
	source_version_id VARCHAR(36) NOT NULL, 
	counterparty VARCHAR(140), 
	reference VARCHAR(100), 
	note TEXT NOT NULL, 
	recorded_by VARCHAR(36) NOT NULL, 
	recorded_at DATETIME NOT NULL, 
	cancelled_at DATETIME, 
	cancelled_by VARCHAR(36), 
	cancellation_reason TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(line_id) REFERENCES material_lines (id), 
	FOREIGN KEY(source_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(recorded_by) REFERENCES users (id), 
	FOREIGN KEY(cancelled_by) REFERENCES users (id)
);
CREATE TABLE material_plan_revisions (
	id VARCHAR(36) NOT NULL, 
	line_id VARCHAR(36) NOT NULL, 
	quantity NUMERIC(18, 3) NOT NULL, 
	source_version_id VARCHAR(36) NOT NULL, 
	note TEXT NOT NULL, 
	recorded_by VARCHAR(36) NOT NULL, 
	recorded_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(line_id) REFERENCES material_lines (id), 
	FOREIGN KEY(source_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(recorded_by) REFERENCES users (id)
);
CREATE TABLE orli_import_batches (
	id VARCHAR(36) NOT NULL, 
	file_name VARCHAR(240) NOT NULL, 
	file_sha256 VARCHAR(64) NOT NULL, 
	format_name VARCHAR(12) NOT NULL, 
	mapping_json TEXT NOT NULL, 
	total_rows INTEGER NOT NULL, 
	valid_rows INTEGER NOT NULL, 
	imported_by VARCHAR(36) NOT NULL, 
	imported_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(imported_by) REFERENCES users (id)
);
CREATE TABLE orli_imported_launches (
	id VARCHAR(36) NOT NULL, 
	batch_id VARCHAR(36) NOT NULL, 
	row_number INTEGER NOT NULL, 
	orli_ref VARCHAR(100), 
	order_ref VARCHAR(100), 
	client_name VARCHAR(150), 
	designation VARCHAR(180), 
	quantity VARCHAR(60), 
	status VARCHAR(80), 
	error_json TEXT NOT NULL, 
	raw_json TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(batch_id) REFERENCES orli_import_batches (id)
);
CREATE TABLE orli_links (
	id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	record_id VARCHAR(36) NOT NULL, 
	confirmed_by VARCHAR(36) NOT NULL, 
	confirmed_at DATETIME NOT NULL, 
	decision_note TEXT NOT NULL, 
	source_ref VARCHAR(100) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (launch_id), 
	UNIQUE (record_id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(record_id) REFERENCES orli_imported_launches (id), 
	FOREIGN KEY(confirmed_by) REFERENCES users (id)
);
CREATE TABLE orli_mapping_profiles (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	mapping_json TEXT NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE orli_refresh_decisions (
	id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	previous_record_id VARCHAR(36) NOT NULL, 
	next_record_id VARCHAR(36) NOT NULL, 
	decision VARCHAR(20) NOT NULL, 
	reason TEXT NOT NULL, 
	decided_by VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(previous_record_id) REFERENCES orli_imported_launches (id), 
	FOREIGN KEY(next_record_id) REFERENCES orli_imported_launches (id), 
	FOREIGN KEY(decided_by) REFERENCES users (id)
);
CREATE TABLE partner_accounts (
	id VARCHAR(36) NOT NULL, 
	partner_id VARCHAR(36) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	password_hash TEXT, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(partner_id) REFERENCES partners (id), 
	UNIQUE (email)
);
CREATE TABLE partner_administrative_documents (
	id VARCHAR(36) NOT NULL, 
	partner_id VARCHAR(36) NOT NULL, 
	title VARCHAR(150) NOT NULL, 
	number INTEGER NOT NULL, 
	owner VARCHAR(80) NOT NULL, 
	original_name VARCHAR(240) NOT NULL, 
	disk_name VARCHAR(64) NOT NULL, 
	size INTEGER NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	reason TEXT NOT NULL, 
	reviewed_by VARCHAR(36), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (partner_id, title, number), 
	FOREIGN KEY(partner_id) REFERENCES partners (id), 
	UNIQUE (disk_name), 
	FOREIGN KEY(reviewed_by) REFERENCES users (id)
);
CREATE TABLE partner_attachments (
	id VARCHAR(36) NOT NULL, 
	partner_id VARCHAR(36) NOT NULL, 
	event_id VARCHAR(36), 
	message_id VARCHAR(36), 
	owner VARCHAR(80) NOT NULL, 
	classification VARCHAR(30) NOT NULL, 
	original_name VARCHAR(240) NOT NULL, 
	disk_name VARCHAR(64) NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	size INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CHECK ((event_id IS NOT NULL AND message_id IS NULL) OR (event_id IS NULL AND message_id IS NOT NULL)), 
	FOREIGN KEY(partner_id) REFERENCES partners (id), 
	FOREIGN KEY(event_id) REFERENCES partner_events (id), 
	FOREIGN KEY(message_id) REFERENCES partner_messages (id), 
	UNIQUE (disk_name)
);
CREATE TABLE partner_client_order_events (
	id VARCHAR(36) NOT NULL, 
	order_id VARCHAR(36) NOT NULL, 
	message TEXT NOT NULL, 
	actor_id VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES partner_client_orders (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id)
);
CREATE TABLE partner_client_orders (
	id VARCHAR(36) NOT NULL, 
	partner_id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	reference VARCHAR(100) NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	confirmed_due DATE, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (partner_id, launch_id), 
	FOREIGN KEY(partner_id) REFERENCES partners (id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id)
);
CREATE TABLE partner_confirmed_datum_sources (
	datum_id VARCHAR(36) NOT NULL, 
	confirmed_id VARCHAR(36) NOT NULL, 
	PRIMARY KEY (datum_id), 
	FOREIGN KEY(datum_id) REFERENCES document_data (id), 
	FOREIGN KEY(confirmed_id) REFERENCES confirmed_extracted_fields (id)
);
CREATE TABLE partner_deliveries (
	id VARCHAR(36) NOT NULL, 
	line_id VARCHAR(36) NOT NULL, 
	operation_key VARCHAR(80) NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	quantity NUMERIC(18, 3) NOT NULL, 
	source_id VARCHAR(36) NOT NULL, 
	actor VARCHAR(80) NOT NULL, 
	note TEXT NOT NULL, 
	occurred_on DATE NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (line_id, operation_key), 
	FOREIGN KEY(line_id) REFERENCES partner_order_lines (id), 
	FOREIGN KEY(source_id) REFERENCES partner_submissions (id)
);
CREATE TABLE partner_event_reads (
	account_id VARCHAR(36) NOT NULL, 
	event_id VARCHAR(36) NOT NULL, 
	read_at DATETIME NOT NULL, 
	PRIMARY KEY (account_id, event_id), 
	FOREIGN KEY(account_id) REFERENCES partner_accounts (id), 
	FOREIGN KEY(event_id) REFERENCES partner_events (id)
);
CREATE TABLE partner_events (
	id VARCHAR(36) NOT NULL, 
	request_id VARCHAR(36) NOT NULL, 
	actor VARCHAR(80) NOT NULL, 
	kind VARCHAR(30) NOT NULL, 
	message TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(request_id) REFERENCES partner_requests (id)
);
CREATE TABLE partner_integrations (
	submission_id VARCHAR(36) NOT NULL, 
	version_id VARCHAR(36) NOT NULL, 
	integrated_by VARCHAR(36) NOT NULL, 
	integrated_at DATETIME NOT NULL, 
	active BOOLEAN NOT NULL, 
	withdrawal_reason TEXT NOT NULL, 
	PRIMARY KEY (submission_id), 
	FOREIGN KEY(submission_id) REFERENCES partner_submissions (id), 
	UNIQUE (version_id), 
	FOREIGN KEY(version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(integrated_by) REFERENCES users (id)
);
CREATE TABLE partner_mail (
	id VARCHAR(36) NOT NULL, 
	event_id VARCHAR(36) NOT NULL, 
	account_id VARCHAR(36) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	attempts INTEGER NOT NULL, 
	next_at DATETIME NOT NULL, 
	last_error VARCHAR(100) NOT NULL, 
	accepted_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (event_id, account_id), 
	FOREIGN KEY(event_id) REFERENCES partner_events (id), 
	FOREIGN KEY(account_id) REFERENCES partner_accounts (id)
);
CREATE TABLE partner_mail_preferences (
	account_id VARCHAR(36) NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	PRIMARY KEY (account_id), 
	FOREIGN KEY(account_id) REFERENCES partner_accounts (id)
);
CREATE TABLE partner_messages (
	id VARCHAR(36) NOT NULL, 
	thread_id VARCHAR(36) NOT NULL, 
	author VARCHAR(80) NOT NULL, 
	text TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(thread_id) REFERENCES partner_threads (id)
);
CREATE TABLE partner_movement_cancellations (
	movement_id VARCHAR(36) NOT NULL, 
	actor VARCHAR(80) NOT NULL, 
	reason TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (movement_id), 
	FOREIGN KEY(movement_id) REFERENCES partner_deliveries (id)
);
CREATE TABLE partner_notice_reads (
	account_id VARCHAR(36) NOT NULL, 
	notice_id VARCHAR(36) NOT NULL, 
	read_at DATETIME NOT NULL, 
	PRIMARY KEY (account_id, notice_id), 
	FOREIGN KEY(account_id) REFERENCES partner_accounts (id), 
	FOREIGN KEY(notice_id) REFERENCES partner_notices (id)
);
CREATE TABLE partner_notices (
	id VARCHAR(36) NOT NULL, 
	partner_id VARCHAR(36) NOT NULL, 
	event_key VARCHAR(160) NOT NULL, 
	scope VARCHAR(20) NOT NULL, 
	target_id VARCHAR(36) NOT NULL, 
	kind VARCHAR(30) NOT NULL, 
	message TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (partner_id, event_key), 
	FOREIGN KEY(partner_id) REFERENCES partners (id)
);
CREATE TABLE partner_order_lines (
	id VARCHAR(36) NOT NULL, 
	partner_id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	order_ref VARCHAR(100) NOT NULL, 
	material_ref VARCHAR(100) NOT NULL, 
	unit VARCHAR(20) NOT NULL, 
	ordered NUMERIC(18, 3) NOT NULL, 
	expected_date DATE, 
	created_by VARCHAR(36) NOT NULL, 
	revision INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (partner_id, order_ref, material_ref), 
	FOREIGN KEY(partner_id) REFERENCES partners (id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE partner_profiles (
	partner_id VARCHAR(36) NOT NULL, 
	trade_name VARCHAR(150) NOT NULL, 
	address TEXT NOT NULL, 
	domains_json TEXT NOT NULL, 
	administrative_json TEXT NOT NULL, 
	PRIMARY KEY (partner_id), 
	FOREIGN KEY(partner_id) REFERENCES partners (id)
);
CREATE TABLE partner_publications (
	id VARCHAR(36) NOT NULL, 
	publication_id VARCHAR(36) NOT NULL, 
	partner_id VARCHAR(36) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (publication_id, partner_id), 
	FOREIGN KEY(publication_id) REFERENCES client_publications (id), 
	FOREIGN KEY(partner_id) REFERENCES partners (id)
);
CREATE TABLE partner_requests (
	id VARCHAR(36) NOT NULL, 
	partner_id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	order_ref VARCHAR(100) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	doc_type VARCHAR(100) NOT NULL, 
	due_date DATE, 
	status VARCHAR(20) NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	revision INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(partner_id) REFERENCES partners (id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE partner_role_assignments (
	account_id VARCHAR(36) NOT NULL, 
	role_id VARCHAR(36) NOT NULL, 
	PRIMARY KEY (account_id), 
	FOREIGN KEY(account_id) REFERENCES partner_accounts (id), 
	FOREIGN KEY(role_id) REFERENCES partner_roles (id)
);
CREATE TABLE partner_roles (
	id VARCHAR(36) NOT NULL, 
	partner_id VARCHAR(36) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	permissions_json TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(partner_id) REFERENCES partners (id)
);
CREATE TABLE partner_submissions (
	id VARCHAR(36) NOT NULL, 
	request_id VARCHAR(36) NOT NULL, 
	number INTEGER NOT NULL, 
	account_id VARCHAR(36) NOT NULL, 
	original_name VARCHAR(240) NOT NULL, 
	disk_name VARCHAR(64) NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	size INTEGER NOT NULL, 
	content_type VARCHAR(160) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	reason TEXT NOT NULL, 
	reviewed_by VARCHAR(36), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (request_id, number), 
	FOREIGN KEY(request_id) REFERENCES partner_requests (id), 
	FOREIGN KEY(account_id) REFERENCES partner_accounts (id), 
	FOREIGN KEY(reviewed_by) REFERENCES users (id)
);
CREATE TABLE partner_threads (
	id VARCHAR(36) NOT NULL, 
	order_id VARCHAR(36) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES partner_client_orders (id)
);
CREATE TABLE partner_tokens (
	digest VARCHAR(64) NOT NULL, 
	account_id VARCHAR(36) NOT NULL, 
	kind VARCHAR(12) NOT NULL, 
	expires_at DATETIME NOT NULL, 
	consumed BOOLEAN NOT NULL, 
	PRIMARY KEY (digest), 
	FOREIGN KEY(account_id) REFERENCES partner_accounts (id)
);
CREATE TABLE partners (
	id VARCHAR(36) NOT NULL, 
	kind VARCHAR(12) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	active BOOLEAN NOT NULL, 
	contact TEXT NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE pilot_reports (
	id VARCHAR(36) NOT NULL, 
	reporter_id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36), 
	module VARCHAR(80) NOT NULL, 
	title VARCHAR(180) NOT NULL, 
	steps TEXT NOT NULL, 
	expected TEXT NOT NULL, 
	observed TEXT NOT NULL, 
	severity VARCHAR(24) NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	resolution_note TEXT NOT NULL, 
	resolved_by VARCHAR(36), 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(reporter_id) REFERENCES users (id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(resolved_by) REFERENCES users (id)
);
CREATE TABLE quality_decisions (
	id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	rule_id VARCHAR(36) NOT NULL, 
	evidence_signature VARCHAR(64) NOT NULL, 
	decision VARCHAR(32) NOT NULL, 
	note TEXT NOT NULL, 
	decided_by VARCHAR(36) NOT NULL, 
	decided_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(rule_id) REFERENCES cross_document_rules (id), 
	FOREIGN KEY(decided_by) REFERENCES users (id)
);
CREATE TABLE requirement_exceptions (
	id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	rule_id VARCHAR(36) NOT NULL, 
	reason TEXT NOT NULL, 
	active BOOLEAN NOT NULL, 
	recorded_by VARCHAR(36) NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_launch_rule_exception UNIQUE (launch_id, rule_id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(rule_id) REFERENCES completeness_rules (id), 
	FOREIGN KEY(recorded_by) REFERENCES users (id)
);
CREATE TABLE requirement_policies (
	rule_id VARCHAR(36) NOT NULL, 
	order_type VARCHAR(100) NOT NULL, 
	optional BOOLEAN NOT NULL, 
	days_after_launch INTEGER, 
	requires_client_publication BOOLEAN NOT NULL, 
	PRIMARY KEY (rule_id), 
	FOREIGN KEY(rule_id) REFERENCES completeness_rules (id)
);
CREATE TABLE requirement_validations (
	id VARCHAR(36) NOT NULL, 
	rule_id VARCHAR(36) NOT NULL, 
	document_version_id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	validated_by VARCHAR(36) NOT NULL, 
	validated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_rule_version_validation UNIQUE (rule_id, document_version_id), 
	FOREIGN KEY(rule_id) REFERENCES completeness_rules (id), 
	FOREIGN KEY(document_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(validated_by) REFERENCES users (id)
);
CREATE TABLE role_permissions (
	id VARCHAR(36) NOT NULL, 
	role_id VARCHAR(36) NOT NULL, 
	action VARCHAR(60) NOT NULL, 
	folder_slug VARCHAR(10), 
	PRIMARY KEY (id), 
	FOREIGN KEY(role_id) REFERENCES roles (id)
);
CREATE TABLE roles (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);
CREATE TABLE schema_migrations (version VARCHAR(80) PRIMARY KEY, applied_at VARCHAR(50) NOT NULL);
CREATE TABLE security_login_buckets (
	"key" VARCHAR(64) NOT NULL, 
	window_start INTEGER NOT NULL, 
	failures INTEGER NOT NULL, 
	PRIMARY KEY ("key")
);
CREATE TABLE specification_ambiguities (
	id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	source_version_id VARCHAR(36) NOT NULL, 
	excerpt VARCHAR(500) NOT NULL, 
	kind VARCHAR(48) NOT NULL, 
	question VARCHAR(500) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	resolution TEXT NOT NULL, 
	clarification_version_id VARCHAR(36), 
	confirmed_by VARCHAR(36) NOT NULL, 
	confirmed_at DATETIME NOT NULL, 
	closed_by VARCHAR(36), 
	closed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(source_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(clarification_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(confirmed_by) REFERENCES users (id), 
	FOREIGN KEY(closed_by) REFERENCES users (id)
);
CREATE TABLE supplier_document_requests (
	id VARCHAR(36) NOT NULL, 
	launch_id VARCHAR(36) NOT NULL, 
	folder_slug VARCHAR(10) NOT NULL, 
	supplier_name VARCHAR(150) NOT NULL, 
	requested_title VARCHAR(200) NOT NULL, 
	expected_doc_type VARCHAR(100) NOT NULL, 
	note TEXT NOT NULL, 
	due_date DATE, 
	status VARCHAR(24) NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	response_version_id VARCHAR(36), 
	resolved_by VARCHAR(36), 
	resolved_at DATETIME, 
	resolution_note TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(launch_id) REFERENCES launches (id), 
	FOREIGN KEY(created_by) REFERENCES users (id), 
	FOREIGN KEY(response_version_id) REFERENCES document_versions (id), 
	FOREIGN KEY(resolved_by) REFERENCES users (id)
);
CREATE TABLE user_roles (
	user_id VARCHAR(36) NOT NULL, 
	role_id VARCHAR(36) NOT NULL, 
	PRIMARY KEY (user_id, role_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(role_id) REFERENCES roles (id)
);
CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	password_hash VARCHAR(256) NOT NULL, 
	active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_audit_action_target_time ON audit_events (action, target_id, occurred_at);
CREATE INDEX ix_security_login_buckets_window_start ON security_login_buckets (window_start);
CREATE INDEX ix_role_permissions_role_id ON role_permissions (role_id);
CREATE INDEX ix_orli_import_batches_file_sha256 ON orli_import_batches (file_sha256);
CREATE INDEX ix_partner_roles_partner_id ON partner_roles (partner_id);
CREATE INDEX ix_partner_administrative_documents_partner_id ON partner_administrative_documents (partner_id);
CREATE INDEX ix_business_orders_client_id ON business_orders (client_id);
CREATE INDEX ix_partner_notices_partner_id ON partner_notices (partner_id);
CREATE INDEX ix_partner_notices_created_at ON partner_notices (created_at);
CREATE INDEX ix_partner_accounts_partner_id ON partner_accounts (partner_id);
CREATE INDEX ix_folders_launch_id ON folders (launch_id);
CREATE INDEX ix_launch_members_launch_id ON launch_members (launch_id);
CREATE INDEX ix_launch_members_user_id ON launch_members (user_id);
CREATE INDEX ix_completeness_rules_profile_id ON completeness_rules (profile_id);
CREATE INDEX ix_impact_alerts_launch_id ON impact_alerts (launch_id);
CREATE INDEX ix_quality_decisions_launch_id ON quality_decisions (launch_id);
CREATE INDEX ix_impact_simulations_launch_id ON impact_simulations (launch_id);
CREATE INDEX ix_orli_imported_launches_orli_ref ON orli_imported_launches (orli_ref);
CREATE INDEX ix_orli_imported_launches_batch_id ON orli_imported_launches (batch_id);
CREATE INDEX ix_material_lines_launch_id ON material_lines (launch_id);
CREATE INDEX ix_approval_stages_template_id ON approval_stages (template_id);
CREATE INDEX ix_internal_notifications_recipient_id ON internal_notifications (recipient_id);
CREATE INDEX ix_partner_client_orders_partner_id ON partner_client_orders (partner_id);
CREATE INDEX ix_business_order_launches_order_id ON business_order_launches (order_id);
CREATE INDEX ix_pilot_reports_launch_id ON pilot_reports (launch_id);
CREATE INDEX ix_pilot_reports_reporter_id ON pilot_reports (reporter_id);
CREATE INDEX ix_partner_tokens_account_id ON partner_tokens (account_id);
CREATE INDEX ix_partner_requests_launch_id ON partner_requests (launch_id);
CREATE INDEX ix_partner_requests_partner_id ON partner_requests (partner_id);
CREATE INDEX ix_partner_order_lines_partner_id ON partner_order_lines (partner_id);
CREATE INDEX ix_documents_folder_id ON documents (folder_id);
CREATE INDEX ix_requirement_exceptions_rule_id ON requirement_exceptions (rule_id);
CREATE INDEX ix_requirement_exceptions_launch_id ON requirement_exceptions (launch_id);
CREATE INDEX ix_orli_links_launch_id ON orli_links (launch_id);
CREATE INDEX ix_orli_links_record_id ON orli_links (record_id);
CREATE INDEX ix_partner_threads_order_id ON partner_threads (order_id);
CREATE INDEX ix_orli_refresh_decisions_launch_id ON orli_refresh_decisions (launch_id);
CREATE INDEX ix_partner_client_order_events_order_id ON partner_client_order_events (order_id);
CREATE INDEX ix_partner_submissions_request_id ON partner_submissions (request_id);
CREATE INDEX ix_partner_events_request_id ON partner_events (request_id);
CREATE INDEX ix_document_versions_document_id ON document_versions (document_id);
CREATE INDEX ix_partner_messages_thread_id ON partner_messages (thread_id);
CREATE INDEX ix_partner_deliveries_line_id ON partner_deliveries (line_id);
CREATE INDEX ix_partner_mail_account_id ON partner_mail (account_id);
CREATE INDEX ix_requirement_validations_launch_id ON requirement_validations (launch_id);
CREATE INDEX ix_requirement_validations_rule_id ON requirement_validations (rule_id);
CREATE INDEX ix_requirement_validations_document_version_id ON requirement_validations (document_version_id);
CREATE INDEX ix_document_reviews_document_version_id ON document_reviews (document_version_id);
CREATE INDEX ix_business_value_revisions_launch_id ON business_value_revisions (launch_id);
CREATE INDEX ix_document_data_document_version_id ON document_data (document_version_id);
CREATE INDEX ix_excel_inspections_document_version_id ON excel_inspections (document_version_id);
CREATE INDEX ix_confirmed_extracted_fields_document_version_id ON confirmed_extracted_fields (document_version_id);
CREATE INDEX ix_client_requirements_source_version_id ON client_requirements (source_version_id);
CREATE INDEX ix_client_requirements_launch_id ON client_requirements (launch_id);
CREATE INDEX ix_specification_ambiguities_launch_id ON specification_ambiguities (launch_id);
CREATE INDEX ix_specification_ambiguities_source_version_id ON specification_ambiguities (source_version_id);
CREATE INDEX ix_archived_emails_launch_id ON archived_emails (launch_id);
CREATE INDEX ix_material_plan_revisions_line_id ON material_plan_revisions (line_id);
CREATE INDEX ix_material_movements_line_id ON material_movements (line_id);
CREATE INDEX ix_approval_runs_document_version_id ON approval_runs (document_version_id);
CREATE INDEX ix_client_publications_launch_id ON client_publications (launch_id);
CREATE INDEX idx_client_publication_launch ON client_publications (launch_id, status);
CREATE INDEX idx_supplier_request_launch ON supplier_document_requests (launch_id, status);
CREATE INDEX ix_supplier_document_requests_launch_id ON supplier_document_requests (launch_id);
CREATE INDEX ix_partner_attachments_partner_id ON partner_attachments (partner_id);
CREATE INDEX ix_email_commitments_launch_id ON email_commitments (launch_id);
CREATE INDEX ix_email_commitments_email_id ON email_commitments (email_id);
CREATE INDEX ix_approval_decisions_run_id ON approval_decisions (run_id);
CREATE INDEX ix_partner_publications_partner_id ON partner_publications (partner_id);
