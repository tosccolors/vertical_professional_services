# Professional Services Leave Management

This module adds a boolean field in the object project.project, named 'Holiday
Consumption'. When this boolean is TRUE for a certain project.project and a user writes
time in the hr_timesheet.sheet and this time record has the status "Approved" on the
project.project it should not only make a line in the object account.analytic.line but
also a new record in the object hr.leave.
