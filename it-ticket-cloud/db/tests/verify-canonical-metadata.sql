-- Read-only metadata gate. Select the intended test/target database explicitly.
SELECT 'ticket.ticket_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='ticket_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket.creator_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='creator_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket.nature' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='nature' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket.category_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='category_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket.title' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='title' AND LOWER(column_type)='varchar(100)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket.description' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='description' AND LOWER(column_type)='text' AND is_nullable='NO')
UNION ALL
SELECT 'ticket.impact_description' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='impact_description' AND LOWER(column_type)='text' AND is_nullable='NO')
UNION ALL
SELECT 'ticket.urgency_description' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='urgency_description' AND LOWER(column_type)='text' AND is_nullable='NO')
UNION ALL
SELECT 'ticket.location' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='location' AND LOWER(column_type)='varchar(255)')
UNION ALL
SELECT 'ticket.contact' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='contact' AND LOWER(column_type)='varchar(255)')
UNION ALL
SELECT 'ticket.asset_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='asset_id' AND LOWER(column_type)='varchar(64)')
UNION ALL
SELECT 'ticket.status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='status' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket.priority' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='priority' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket.assignee_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='assignee_id' AND LOWER(column_type)='varchar(64)')
UNION ALL
SELECT 'ticket.source_session_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='source_session_id' AND LOWER(column_type)='varchar(32)')
UNION ALL
SELECT 'ticket.field_definition_snapshot' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='field_definition_snapshot' AND LOWER(column_type)='json')
UNION ALL
SELECT 'ticket.version' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='version' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'ticket.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket.completed_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='completed_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'ticket.closed_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket' AND column_name='closed_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'ticket:index(creator_id,status)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='ticket' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='creator_id,status')
UNION ALL
SELECT 'ticket:index(assignee_id,status)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='ticket' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='assignee_id,status')
UNION ALL
SELECT 'ticket:index(priority,status)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='ticket' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='priority,status')
UNION ALL
SELECT 'ticket_transition.transition_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_transition' AND column_name='transition_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_transition.ticket_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_transition' AND column_name='ticket_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_transition.from_status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_transition' AND column_name='from_status' AND LOWER(column_type)='varchar(32)')
UNION ALL
SELECT 'ticket_transition.to_status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_transition' AND column_name='to_status' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_transition.event' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_transition' AND column_name='event' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_transition.operator_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_transition' AND column_name='operator_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_transition.reason' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_transition' AND column_name='reason' AND LOWER(column_type)='text')
UNION ALL
SELECT 'ticket_transition.occurred_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_transition' AND column_name='occurred_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_transition:index(ticket_id,occurred_at,transition_id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='ticket_transition' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='ticket_id,occurred_at,transition_id')
UNION ALL
SELECT 'ticket_transition:index(ticket_id,occurred_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='ticket_transition' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='ticket_id,occurred_at')
UNION ALL
SELECT 'service_calendar.calendar_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='service_calendar' AND column_name='calendar_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'service_calendar.timezone' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='service_calendar' AND column_name='timezone' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'service_calendar.work_week_json' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='service_calendar' AND column_name='work_week_json' AND LOWER(column_type)='json' AND is_nullable='NO')
UNION ALL
SELECT 'service_calendar.work_intervals_json' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='service_calendar' AND column_name='work_intervals_json' AND LOWER(column_type)='json' AND is_nullable='NO')
UNION ALL
SELECT 'service_calendar.lunch_pauses' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='service_calendar' AND column_name='lunch_pauses' AND LOWER(column_type)='tinyint(1)' AND is_nullable='NO')
UNION ALL
SELECT 'service_calendar.version' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='service_calendar' AND column_name='version' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'service_calendar.effective_from' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='service_calendar' AND column_name='effective_from' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'service_calendar.effective_to' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='service_calendar' AND column_name='effective_to' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'service_calendar.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='service_calendar' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'service_calendar.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='service_calendar' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'calendar_holiday.holiday_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='calendar_holiday' AND column_name='holiday_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'calendar_holiday.calendar_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='calendar_holiday' AND column_name='calendar_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'calendar_holiday.holiday_date' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='calendar_holiday' AND column_name='holiday_date' AND LOWER(column_type)='date' AND is_nullable='NO')
UNION ALL
SELECT 'calendar_holiday.name' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='calendar_holiday' AND column_name='name' AND LOWER(column_type)='varchar(255)' AND is_nullable='NO')
UNION ALL
SELECT 'calendar_holiday.is_working_day' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='calendar_holiday' AND column_name='is_working_day' AND LOWER(column_type)='tinyint(1)' AND is_nullable='NO')
UNION ALL
SELECT 'calendar_holiday:index(calendar_id,holiday_date)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='calendar_holiday' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='calendar_id,holiday_date')
UNION ALL
SELECT 'exception_queue.exception_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='exception_queue' AND column_name='exception_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'exception_queue.object_type' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='exception_queue' AND column_name='object_type' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'exception_queue.object_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='exception_queue' AND column_name='object_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'exception_queue.reason_code' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='exception_queue' AND column_name='reason_code' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'exception_queue.status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='exception_queue' AND column_name='status' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'exception_queue.claimed_by' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='exception_queue' AND column_name='claimed_by' AND LOWER(column_type)='varchar(64)')
UNION ALL
SELECT 'exception_queue.claimed_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='exception_queue' AND column_name='claimed_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'exception_queue.resolved_by' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='exception_queue' AND column_name='resolved_by' AND LOWER(column_type)='varchar(64)')
UNION ALL
SELECT 'exception_queue.resolved_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='exception_queue' AND column_name='resolved_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'exception_queue.reason' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='exception_queue' AND column_name='reason' AND LOWER(column_type)='text')
UNION ALL
SELECT 'exception_queue.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='exception_queue' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'exception_queue.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='exception_queue' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'exception_queue:index(status,created_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='exception_queue' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='status,created_at')
UNION ALL
SELECT 'exception_queue:index(object_type,object_id,reason_code,status)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='exception_queue' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='object_type,object_id,reason_code,status')
UNION ALL
SELECT 'user.user_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user' AND column_name='user_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'user.employee_no' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user' AND column_name='employee_no' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'user.name' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user' AND column_name='name' AND LOWER(column_type)='varchar(255)' AND is_nullable='NO')
UNION ALL
SELECT 'user.department_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user' AND column_name='department_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'user.status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user' AND column_name='status' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'user.identity_source' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user' AND column_name='identity_source' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'user.last_identity_sync_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user' AND column_name='last_identity_sync_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'user.version' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user' AND column_name='version' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'user.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'user.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'user:index(employee_no)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='user' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='employee_no')
UNION ALL
SELECT 'user:index(department_id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='user' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='department_id')
UNION ALL
SELECT 'user:index(status)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='user' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='status')
UNION ALL
SELECT 'user_role.user_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user_role' AND column_name='user_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'user_role.role_code' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user_role' AND column_name='role_code' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'user_role.granted_by' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user_role' AND column_name='granted_by' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'user_role.granted_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user_role' AND column_name='granted_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'user_role.revoked_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user_role' AND column_name='revoked_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'user_role.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user_role' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'user_role.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user_role' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'user_role:index(user_id,role_code)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='user_role' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='user_id,role_code')
UNION ALL
SELECT 'user_role:index(revoked_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='user_role' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='revoked_at')
UNION ALL
SELECT 'support_team.team_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='support_team' AND column_name='team_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'support_team.name' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='support_team' AND column_name='name' AND LOWER(column_type)='varchar(255)' AND is_nullable='NO')
UNION ALL
SELECT 'support_team.status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='support_team' AND column_name='status' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'support_team.version' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='support_team' AND column_name='version' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'support_team.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='support_team' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'support_team.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='support_team' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'support_team:index(name)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='support_team' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='name')
UNION ALL
SELECT 'support_team:index(status)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='support_team' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='status')
UNION ALL
SELECT 'team_member.team_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='team_member' AND column_name='team_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'team_member.engineer_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='team_member' AND column_name='engineer_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'team_member.joined_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='team_member' AND column_name='joined_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'team_member.left_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='team_member' AND column_name='left_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'team_member.status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='team_member' AND column_name='status' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'team_member.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='team_member' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'team_member.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='team_member' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'team_member:index(team_id,engineer_id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='team_member' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='team_id,engineer_id')
UNION ALL
SELECT 'team_member:index(engineer_id,status)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='team_member' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='engineer_id,status')
UNION ALL
SELECT 'engineer_runtime_state.engineer_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_runtime_state' AND column_name='engineer_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_runtime_state.presence' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_runtime_state' AND column_name='presence' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_runtime_state.last_activity_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_runtime_state' AND column_name='last_activity_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'engineer_runtime_state.last_assigned_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_runtime_state' AND column_name='last_assigned_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'engineer_runtime_state.version' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_runtime_state' AND column_name='version' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_runtime_state.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_runtime_state' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_runtime_state.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_runtime_state' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_runtime_state:index(presence,last_activity_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='engineer_runtime_state' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='presence,last_activity_at')
UNION ALL
SELECT 'engineer_category_capability.engineer_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_category_capability' AND column_name='engineer_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_category_capability.category_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_category_capability' AND column_name='category_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_category_capability.team_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_category_capability' AND column_name='team_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_category_capability.enabled' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_category_capability' AND column_name='enabled' AND LOWER(column_type)='tinyint(1)' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_category_capability.effective_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_category_capability' AND column_name='effective_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_category_capability.expired_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_category_capability' AND column_name='expired_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'engineer_category_capability.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_category_capability' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_category_capability.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_category_capability' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_category_capability:index(engineer_id,category_id,team_id,effective_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='engineer_category_capability' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='engineer_id,category_id,team_id,effective_at')
UNION ALL
SELECT 'engineer_category_capability:index(category_id,team_id,enabled)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='engineer_category_capability' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='category_id,team_id,enabled')
UNION ALL
SELECT 'category.category_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category' AND column_name='category_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'category.parent_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category' AND column_name='parent_id' AND LOWER(column_type)='varchar(64)')
UNION ALL
SELECT 'category.ticket_nature' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category' AND column_name='ticket_nature' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'category.name' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category' AND column_name='name' AND LOWER(column_type)='varchar(255)' AND is_nullable='NO')
UNION ALL
SELECT 'category.level' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category' AND column_name='level' AND LOWER(column_type)='smallint' AND is_nullable='NO')
UNION ALL
SELECT 'category.definition_version' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category' AND column_name='definition_version' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'category.status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category' AND column_name='status' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'category.version' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category' AND column_name='version' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'category.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'category.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'category:index(parent_id,level,status)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='category' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='parent_id,level,status')
UNION ALL
SELECT 'category_route.category_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category_route' AND column_name='category_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'category_route.team_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category_route' AND column_name='team_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'category_route.route_order' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category_route' AND column_name='route_order' AND LOWER(column_type)='int' AND is_nullable='NO')
UNION ALL
SELECT 'category_route.effective_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category_route' AND column_name='effective_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'category_route.expired_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category_route' AND column_name='expired_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'category_route.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category_route' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'category_route.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category_route' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'category_route:index(category_id,team_id,effective_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='category_route' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='category_id,team_id,effective_at')
UNION ALL
SELECT 'category_route:index(category_id,route_order,effective_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='category_route' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='category_id,route_order,effective_at')
UNION ALL
SELECT 'consultation.session_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation' AND column_name='session_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'consultation.creator_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation' AND column_name='creator_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'consultation.category_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation' AND column_name='category_id' AND LOWER(column_type)='varchar(64)')
UNION ALL
SELECT 'consultation.status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation' AND column_name='status' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'consultation.current_engineer_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation' AND column_name='current_engineer_id' AND LOWER(column_type)='varchar(64)')
UNION ALL
SELECT 'consultation.source' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation' AND column_name='source' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'consultation.resolved_type' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation' AND column_name='resolved_type' AND LOWER(column_type)='varchar(32)')
UNION ALL
SELECT 'consultation.converted_ticket_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation' AND column_name='converted_ticket_id' AND LOWER(column_type)='varchar(32)')
UNION ALL
SELECT 'consultation.closed_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation' AND column_name='closed_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'consultation.version' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation' AND column_name='version' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'consultation.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'consultation.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'consultation:index(creator_id,status,created_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='consultation' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='creator_id,status,created_at')
UNION ALL
SELECT 'consultation:index(current_engineer_id,status)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='consultation' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='current_engineer_id,status')
UNION ALL
SELECT 'consultation_message.message_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation_message' AND column_name='message_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'consultation_message.session_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation_message' AND column_name='session_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'consultation_message.sender_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation_message' AND column_name='sender_id' AND LOWER(column_type)='varchar(64)')
UNION ALL
SELECT 'consultation_message.sender_type' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation_message' AND column_name='sender_type' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'consultation_message.client_message_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation_message' AND column_name='client_message_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'consultation_message.content' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation_message' AND column_name='content' AND LOWER(column_type)='mediumtext' AND is_nullable='NO')
UNION ALL
SELECT 'consultation_message.citation_json' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation_message' AND column_name='citation_json' AND LOWER(column_type)='json')
UNION ALL
SELECT 'consultation_message.sent_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation_message' AND column_name='sent_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'consultation_message.withdrawn_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation_message' AND column_name='withdrawn_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'consultation_message.withdraw_reason' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation_message' AND column_name='withdraw_reason' AND LOWER(column_type)='varchar(2000)')
UNION ALL
SELECT 'consultation_message.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation_message' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'consultation_message.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='consultation_message' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'consultation_message:index(session_id,sent_at,message_id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='consultation_message' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='session_id,sent_at,message_id')
UNION ALL
SELECT 'consultation_message:index(session_id,client_message_id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='consultation_message' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='session_id,client_message_id')
UNION ALL
SELECT 'ticket_draft.draft_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_draft' AND column_name='draft_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_draft.creator_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_draft' AND column_name='creator_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_draft.ticket_nature' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_draft' AND column_name='ticket_nature' AND LOWER(column_type)='varchar(32)')
UNION ALL
SELECT 'ticket_draft.category_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_draft' AND column_name='category_id' AND LOWER(column_type)='varchar(64)')
UNION ALL
SELECT 'ticket_draft.payload_json' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_draft' AND column_name='payload_json' AND LOWER(column_type)='json' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_draft.last_saved_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_draft' AND column_name='last_saved_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_draft.expires_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_draft' AND column_name='expires_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_draft.version' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_draft' AND column_name='version' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_draft.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_draft' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_draft.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_draft' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_draft:index(creator_id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='ticket_draft' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='creator_id')
UNION ALL
SELECT 'assignment.assignment_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='assignment' AND column_name='assignment_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'assignment.biz_type' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='assignment' AND column_name='biz_type' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'assignment.biz_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='assignment' AND column_name='biz_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'assignment.engineer_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='assignment' AND column_name='engineer_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'assignment.assigned_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='assignment' AND column_name='assigned_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'assignment.response_deadline' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='assignment' AND column_name='response_deadline' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'assignment.responded_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='assignment' AND column_name='responded_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'assignment.end_reason' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='assignment' AND column_name='end_reason' AND LOWER(column_type)='varchar(32)')
UNION ALL
SELECT 'assignment.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='assignment' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'assignment.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='assignment' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'assignment:index(biz_type,biz_id,assigned_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='assignment' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='biz_type,biz_id,assigned_at')
UNION ALL
SELECT 'assignment:index(engineer_id,end_reason)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='assignment' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='engineer_id,end_reason')
UNION ALL
SELECT 'sla_instance.sla_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='sla_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'sla_instance.ticket_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='ticket_id' AND LOWER(column_type)='varchar(32)')
UNION ALL
SELECT 'sla_instance.biz_type' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='biz_type' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'sla_instance.biz_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='biz_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'sla_instance.sla_type' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='sla_type' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'sla_instance.status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='status' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'sla_instance.target_work_seconds' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='target_work_seconds' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'sla_instance.elapsed_work_seconds' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='elapsed_work_seconds' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'sla_instance.paused_seconds' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='paused_seconds' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'sla_instance.target_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='target_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'sla_instance.breach_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='breach_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'sla_instance.met_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='met_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'sla_instance.calendar_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='calendar_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'sla_instance.calendar_version' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='calendar_version' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'sla_instance.version' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='version' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'sla_instance.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'sla_instance.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_instance' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'sla_instance:index(biz_type,biz_id,sla_type)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='sla_instance' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='biz_type,biz_id,sla_type')
UNION ALL
SELECT 'sla_instance:index(status,target_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='sla_instance' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='status,target_at')
UNION ALL
SELECT 'sla_instance:index(ticket_id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='sla_instance' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='ticket_id')
UNION ALL
SELECT 'sla_pause.pause_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_pause' AND column_name='pause_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'sla_pause.sla_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_pause' AND column_name='sla_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'sla_pause.reason_type' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_pause' AND column_name='reason_type' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'sla_pause.started_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_pause' AND column_name='started_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'sla_pause.ended_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_pause' AND column_name='ended_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'sla_pause.operator_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_pause' AND column_name='operator_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'sla_pause.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_pause' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'sla_pause.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='sla_pause' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'sla_pause:index(sla_id,started_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='sla_pause' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='sla_id,started_at')
UNION ALL
SELECT 'notification.notification_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='notification' AND column_name='notification_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'notification.event_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='notification' AND column_name='event_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'notification.receiver_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='notification' AND column_name='receiver_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'notification.channel' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='notification' AND column_name='channel' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'notification.dedup_key' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='notification' AND column_name='dedup_key' AND LOWER(column_type)='varchar(255)' AND is_nullable='NO')
UNION ALL
SELECT 'notification.status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='notification' AND column_name='status' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'notification.attempts' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='notification' AND column_name='attempts' AND LOWER(column_type)='int' AND is_nullable='NO')
UNION ALL
SELECT 'notification.last_error' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='notification' AND column_name='last_error' AND LOWER(column_type)='varchar(1000)')
UNION ALL
SELECT 'notification.sent_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='notification' AND column_name='sent_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'notification.read_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='notification' AND column_name='read_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'notification.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='notification' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'notification.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='notification' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'notification:index(dedup_key)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='notification' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='dedup_key')
UNION ALL
SELECT 'notification:index(receiver_id,status)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='notification' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='receiver_id,status')
UNION ALL
SELECT 'audit_log.audit_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='audit_log' AND column_name='audit_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'audit_log.actor_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='audit_log' AND column_name='actor_id' AND LOWER(column_type)='varchar(64)')
UNION ALL
SELECT 'audit_log.action' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='audit_log' AND column_name='action' AND LOWER(column_type)='varchar(128)' AND is_nullable='NO')
UNION ALL
SELECT 'audit_log.object_type' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='audit_log' AND column_name='object_type' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'audit_log.object_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='audit_log' AND column_name='object_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'audit_log.before_value' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='audit_log' AND column_name='before_value' AND LOWER(column_type)='json')
UNION ALL
SELECT 'audit_log.after_value' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='audit_log' AND column_name='after_value' AND LOWER(column_type)='json')
UNION ALL
SELECT 'audit_log.reason' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='audit_log' AND column_name='reason' AND LOWER(column_type)='varchar(2000)')
UNION ALL
SELECT 'audit_log.request_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='audit_log' AND column_name='request_id' AND LOWER(column_type)='varchar(128)' AND is_nullable='NO')
UNION ALL
SELECT 'audit_log.occurred_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='audit_log' AND column_name='occurred_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'audit_log.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='audit_log' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'audit_log.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='audit_log' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'audit_log:index(object_type,object_id,occurred_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='audit_log' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='object_type,object_id,occurred_at')
UNION ALL
SELECT 'audit_log:index(actor_id,occurred_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='audit_log' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='actor_id,occurred_at')
UNION ALL
SELECT 'idempotency_record.record_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='idempotency_record' AND column_name='record_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'idempotency_record.owner_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='idempotency_record' AND column_name='owner_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'idempotency_record.operation' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='idempotency_record' AND column_name='operation' AND LOWER(column_type)='varchar(128)' AND is_nullable='NO')
UNION ALL
SELECT 'idempotency_record.idempotency_key' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='idempotency_record' AND column_name='idempotency_key' AND LOWER(column_type)='varchar(128)' AND is_nullable='NO')
UNION ALL
SELECT 'idempotency_record.request_hash' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='idempotency_record' AND column_name='request_hash' AND LOWER(column_type)='char(64)' AND is_nullable='NO')
UNION ALL
SELECT 'idempotency_record.status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='idempotency_record' AND column_name='status' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'idempotency_record.result_json' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='idempotency_record' AND column_name='result_json' AND LOWER(column_type)='json')
UNION ALL
SELECT 'idempotency_record.expires_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='idempotency_record' AND column_name='expires_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'idempotency_record.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='idempotency_record' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'idempotency_record.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='idempotency_record' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'idempotency_record:index(owner_id,operation,idempotency_key)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='idempotency_record' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='owner_id,operation,idempotency_key')
UNION ALL
SELECT 'idempotency_record:index(expires_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='idempotency_record' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='expires_at')
UNION ALL
SELECT 'outbox_event.event_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='outbox_event' AND column_name='event_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'outbox_event.event_type' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='outbox_event' AND column_name='event_type' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'outbox_event.aggregate_type' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='outbox_event' AND column_name='aggregate_type' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'outbox_event.aggregate_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='outbox_event' AND column_name='aggregate_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'outbox_event.event_version' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='outbox_event' AND column_name='event_version' AND LOWER(column_type)='int' AND is_nullable='NO')
UNION ALL
SELECT 'outbox_event.aggregate_version' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='outbox_event' AND column_name='aggregate_version' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'outbox_event.payload_json' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='outbox_event' AND column_name='payload_json' AND LOWER(column_type)='json' AND is_nullable='NO')
UNION ALL
SELECT 'outbox_event.status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='outbox_event' AND column_name='status' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'outbox_event.attempts' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='outbox_event' AND column_name='attempts' AND LOWER(column_type)='int' AND is_nullable='NO')
UNION ALL
SELECT 'outbox_event.next_attempt_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='outbox_event' AND column_name='next_attempt_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'outbox_event.published_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='outbox_event' AND column_name='published_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'outbox_event.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='outbox_event' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'outbox_event.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='outbox_event' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'outbox_event:index(status,next_attempt_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='outbox_event' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='status,next_attempt_at')
UNION ALL
SELECT 'outbox_event:index(aggregate_type,aggregate_id,aggregate_version)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='outbox_event' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='aggregate_type,aggregate_id,aggregate_version')
UNION ALL
SELECT 'knowledge_article.article_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_article' AND column_name='article_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_article.status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_article' AND column_name='status' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_article.current_version_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_article' AND column_name='current_version_id' AND LOWER(column_type)='varchar(64)')
UNION ALL
SELECT 'knowledge_article.category_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_article' AND column_name='category_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_article.risk_level' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_article' AND column_name='risk_level' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_article.version' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_article' AND column_name='version' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_article.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_article' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_article.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_article' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_article:index(status,category_id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='knowledge_article' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='status,category_id')
UNION ALL
SELECT 'knowledge_version.version_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_version' AND column_name='version_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_version.article_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_version' AND column_name='article_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_version.version_no' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_version' AND column_name='version_no' AND LOWER(column_type)='int' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_version.content' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_version' AND column_name='content' AND LOWER(column_type)='json' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_version.author_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_version' AND column_name='author_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_version.reviewer_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_version' AND column_name='reviewer_id' AND LOWER(column_type)='varchar(64)')
UNION ALL
SELECT 'knowledge_version.published_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_version' AND column_name='published_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'knowledge_version.change_note' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_version' AND column_name='change_note' AND LOWER(column_type)='varchar(2000)')
UNION ALL
SELECT 'knowledge_version.platform_reviewer_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_version' AND column_name='platform_reviewer_id' AND LOWER(column_type)='varchar(64)')
UNION ALL
SELECT 'knowledge_version.platform_reviewed_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_version' AND column_name='platform_reviewed_at' AND LOWER(column_type)='datetime(6)')
UNION ALL
SELECT 'knowledge_version.platform_review_decision' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_version' AND column_name='platform_review_decision' AND LOWER(column_type)='varchar(32)')
UNION ALL
SELECT 'knowledge_version.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_version' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_version.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_version' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_version:index(article_id,version_no)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='knowledge_version' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='article_id,version_no')
UNION ALL
SELECT 'ai_interaction.interaction_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ai_interaction' AND column_name='interaction_id' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'ai_interaction.session_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ai_interaction' AND column_name='session_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'ai_interaction.model_version' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ai_interaction' AND column_name='model_version' AND LOWER(column_type)='varchar(128)' AND is_nullable='NO')
UNION ALL
SELECT 'ai_interaction.retrieved_versions' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ai_interaction' AND column_name='retrieved_versions' AND LOWER(column_type)='json' AND is_nullable='NO')
UNION ALL
SELECT 'ai_interaction.confidence' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ai_interaction' AND column_name='confidence' AND LOWER(column_type)='decimal(8,4)')
UNION ALL
SELECT 'ai_interaction.feedback' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ai_interaction' AND column_name='feedback' AND LOWER(column_type)='varchar(32)')
UNION ALL
SELECT 'ai_interaction.latency' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ai_interaction' AND column_name='latency' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'ai_interaction.occurred_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ai_interaction' AND column_name='occurred_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'ai_interaction.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ai_interaction' AND column_name='created_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'ai_interaction.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ai_interaction' AND column_name='updated_at' AND LOWER(column_type)='datetime(6)' AND is_nullable='NO')
UNION ALL
SELECT 'ai_interaction:index(session_id,occurred_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='ai_interaction' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='session_id,occurred_at')
UNION ALL
SELECT 'attachment.attachment_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='attachment' AND column_name='attachment_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'attachment.biz_type' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='attachment' AND column_name='biz_type' AND LOWER(column_type)='varchar(16)' AND is_nullable='NO')
UNION ALL
SELECT 'attachment.biz_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='attachment' AND column_name='biz_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'attachment.uploader_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='attachment' AND column_name='uploader_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'attachment.file_name' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='attachment' AND column_name='file_name' AND LOWER(column_type)='varchar(255)' AND is_nullable='NO')
UNION ALL
SELECT 'attachment.size' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='attachment' AND column_name='size' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'attachment.hash' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='attachment' AND column_name='hash' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'attachment.scan_status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='attachment' AND column_name='scan_status' AND LOWER(column_type)='varchar(16)' AND is_nullable='NO')
UNION ALL
SELECT 'attachment.withdrawn_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='attachment' AND column_name='withdrawn_at' AND LOWER(column_type)='datetime')
UNION ALL
SELECT 'attachment.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='attachment' AND column_name='created_at' AND LOWER(column_type)='datetime' AND is_nullable='NO')
UNION ALL
SELECT 'attachment:index(attachment_id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='attachment' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='attachment_id')
UNION ALL
SELECT 'attachment:index(biz_type,biz_id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='attachment' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='biz_type,biz_id')
UNION ALL
SELECT 'case_candidate.case_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='case_candidate' AND column_name='case_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'case_candidate.source_type' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='case_candidate' AND column_name='source_type' AND LOWER(column_type)='varchar(16)' AND is_nullable='NO')
UNION ALL
SELECT 'case_candidate.source_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='case_candidate' AND column_name='source_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'case_candidate.structured_content' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='case_candidate' AND column_name='structured_content' AND LOWER(column_type)='text')
UNION ALL
SELECT 'case_candidate.masking_status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='case_candidate' AND column_name='masking_status' AND LOWER(column_type)='varchar(16)' AND is_nullable='NO')
UNION ALL
SELECT 'case_candidate.reusable_flag' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='case_candidate' AND column_name='reusable_flag' AND LOWER(column_type)='tinyint' AND is_nullable='NO')
UNION ALL
SELECT 'case_candidate.status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='case_candidate' AND column_name='status' AND LOWER(column_type)='varchar(16)' AND is_nullable='NO')
UNION ALL
SELECT 'case_candidate.cluster_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='case_candidate' AND column_name='cluster_id' AND LOWER(column_type)='varchar(32)')
UNION ALL
SELECT 'case_candidate.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='case_candidate' AND column_name='created_at' AND LOWER(column_type)='datetime' AND is_nullable='NO')
UNION ALL
SELECT 'case_candidate.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='case_candidate' AND column_name='updated_at' AND LOWER(column_type)='datetime' AND is_nullable='NO')
UNION ALL
SELECT 'case_candidate:index(case_id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='case_candidate' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='case_id')
UNION ALL
SELECT 'case_candidate:index(status,reusable_flag)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='case_candidate' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='status,reusable_flag')
UNION ALL
SELECT 'category_field_def.field_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category_field_def' AND column_name='field_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'category_field_def.category_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category_field_def' AND column_name='category_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'category_field_def.name' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category_field_def' AND column_name='name' AND LOWER(column_type)='varchar(64)' AND is_nullable='NO')
UNION ALL
SELECT 'category_field_def.field_type' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category_field_def' AND column_name='field_type' AND LOWER(column_type)='varchar(16)' AND is_nullable='NO')
UNION ALL
SELECT 'category_field_def.required' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category_field_def' AND column_name='required' AND LOWER(column_type)='tinyint' AND is_nullable='NO')
UNION ALL
SELECT 'category_field_def.options' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category_field_def' AND column_name='options' AND LOWER(column_type)='varchar(1000)')
UNION ALL
SELECT 'category_field_def.sort_order' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category_field_def' AND column_name='sort_order' AND LOWER(column_type)='int' AND is_nullable='NO')
UNION ALL
SELECT 'category_field_def.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category_field_def' AND column_name='created_at' AND LOWER(column_type)='datetime' AND is_nullable='NO')
UNION ALL
SELECT 'category_field_def.updated_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='category_field_def' AND column_name='updated_at' AND LOWER(column_type)='datetime' AND is_nullable='NO')
UNION ALL
SELECT 'category_field_def:index(field_id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='category_field_def' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='field_id')
UNION ALL
SELECT 'category_field_def:index(category_id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='category_field_def' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='category_id')
UNION ALL
SELECT 'engineer_status_log.id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_status_log' AND column_name='id' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_status_log.engineer_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_status_log' AND column_name='engineer_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_status_log.status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_status_log' AND column_name='status' AND LOWER(column_type)='varchar(16)' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_status_log.source' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_status_log' AND column_name='source' AND LOWER(column_type)='varchar(16)' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_status_log.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='engineer_status_log' AND column_name='created_at' AND LOWER(column_type)='datetime' AND is_nullable='NO')
UNION ALL
SELECT 'engineer_status_log:index(id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='engineer_status_log' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='id')
UNION ALL
SELECT 'engineer_status_log:index(engineer_id,created_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='engineer_status_log' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='engineer_id,created_at')
UNION ALL
SELECT 'knowledge_cluster.cluster_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_cluster' AND column_name='cluster_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_cluster.similarity_basis' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_cluster' AND column_name='similarity_basis' AND LOWER(column_type)='varchar(200)' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_cluster.status' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_cluster' AND column_name='status' AND LOWER(column_type)='varchar(16)' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_cluster.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='knowledge_cluster' AND column_name='created_at' AND LOWER(column_type)='datetime' AND is_nullable='NO')
UNION ALL
SELECT 'knowledge_cluster:index(cluster_id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='knowledge_cluster' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='cluster_id')
UNION ALL
SELECT 'ticket_field_value.id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_field_value' AND column_name='id' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_field_value.ticket_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_field_value' AND column_name='ticket_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_field_value.field_definition_snapshot' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_field_value' AND column_name='field_definition_snapshot' AND LOWER(column_type)='varchar(1000)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_field_value.field_value' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_field_value' AND column_name='field_value' AND LOWER(column_type)='varchar(2000)')
UNION ALL
SELECT 'ticket_field_value.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_field_value' AND column_name='created_at' AND LOWER(column_type)='datetime' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_field_value:index(id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='ticket_field_value' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='id')
UNION ALL
SELECT 'ticket_field_value:index(ticket_id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='ticket_field_value' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='ticket_id')
UNION ALL
SELECT 'ticket_message.message_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_message' AND column_name='message_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_message.ticket_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_message' AND column_name='ticket_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_message.sender_id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_message' AND column_name='sender_id' AND LOWER(column_type)='varchar(32)' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_message.content' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_message' AND column_name='content' AND LOWER(column_type)='text' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_message.withdrawn_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_message' AND column_name='withdrawn_at' AND LOWER(column_type)='datetime')
UNION ALL
SELECT 'ticket_message.created_at' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ticket_message' AND column_name='created_at' AND LOWER(column_type)='datetime' AND is_nullable='NO')
UNION ALL
SELECT 'ticket_message:index(message_id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='ticket_message' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='message_id')
UNION ALL
SELECT 'ticket_message:index(ticket_id,created_at)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='ticket_message' GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='ticket_id,created_at')
UNION ALL
SELECT 'work_calendar.id' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='work_calendar' AND column_name='id' AND LOWER(column_type)='bigint' AND is_nullable='NO')
UNION ALL
SELECT 'work_calendar.cal_date' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='work_calendar' AND column_name='cal_date' AND LOWER(column_type)='date' AND is_nullable='NO')
UNION ALL
SELECT 'work_calendar.day_type' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='work_calendar' AND column_name='day_type' AND LOWER(column_type)='varchar(16)' AND is_nullable='NO')
UNION ALL
SELECT 'work_calendar.start_time' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='work_calendar' AND column_name='start_time' AND LOWER(column_type)='time')
UNION ALL
SELECT 'work_calendar.end_time' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='work_calendar' AND column_name='end_time' AND LOWER(column_type)='time')
UNION ALL
SELECT 'work_calendar.lunch_pause' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='work_calendar' AND column_name='lunch_pause' AND LOWER(column_type)='tinyint' AND is_nullable='NO')
UNION ALL
SELECT 'work_calendar:index(id)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='work_calendar' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='id')
UNION ALL
SELECT 'work_calendar:index(cal_date)' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='work_calendar' AND non_unique=0 GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='cal_date');
