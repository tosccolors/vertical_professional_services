Human Resources Management - extended
=====================================

This module adds the following fields:

In the object hr.employee on the tab 'HR Settings' under the heading 'Duration of Service' creates three new date fields called: 'Official Date of Employment', 'Temporary Contract' and 'End Date of Employment'. These first two date fields do not affect the 'lengt_of_service' field, the end-date-of-employment stops the counting of the length of service from the 'initial_employment_date'.

In the object hr.employee on the tab 'Public Information' under the heading 'Position' creates a new boolean called 'External'. If the boolean is set to true a new character field called 'Supplier' becomes visible.

In the object hr.employee on the tab 'Public Information' under the heading 'Position' creates a new m2o selection field of hr.employee called 'Mentor' similar to Manager (parent_id) and Coach (coach_id).

In the object hr.employee on the tab 'HR Settings' under the heading 'Leaves' creates two new integer fields called 'Parttime' and 'Allocated Leaves'.

In the object hr.employee on the tab 'Personal Information' under the heading 'Contact Information' creates a new character field called 'Emergency Contact'.

In the object hr.employee creates a new tab called 'Description' and on this tab creates a new text field called 'Description'.

In the object hr.employee on the tab 'HR Settings' under the heading 'Status' creates a new character field called 'Pass Number Alarm'.
