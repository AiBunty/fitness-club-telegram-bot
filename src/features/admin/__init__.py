"""
Admin Feature Package

Consolidated admin handlers (32 functions, 1,360 lines):
- Attendance approval (cmd_pending_attendance, callback_approve_attend, callback_reject_attend)
- Shake management (cmd_pending_shakes, callback_ready_shake, callback_cancel_shake)
- Staff management (cmd_add_staff, cmd_remove_staff, cmd_list_staff, handle_staff_id_input)
- Admin role management (cmd_add_admin, cmd_remove_admin, cmd_list_admins)
- User management (cmd_pending_users, callback_approve_user, callback_reject_user)
- Manual operations (cmd_manual_shake_deduction, get_manual_shake_deduction_handler)
- QR/Attendance (cmd_qr_attendance_link, cmd_override_attendance, cmd_download_qr_code)
"""

# Export all admin handler functions
from src.features.admin.handlers import (
    # Admin utilities
    get_admin_ids,
    get_admin_users,
    # Attendance management
    cmd_pending_attendance,
    callback_review_attendance,
    callback_approve_attend,
    callback_reject_attend,
    # Shake management
    cmd_pending_shakes,
    callback_review_shakes,
    callback_ready_shake,
    callback_cancel_shake,
    # Staff management
    cmd_add_staff,
    cmd_remove_staff,
    cmd_list_staff,
    handle_staff_id_input,
    # Admin role management
    cmd_add_admin,
    cmd_remove_admin,
    cmd_list_admins,
    # User management
    cmd_list_users,
    cmd_delete_user,
    cmd_ban_user,
    cmd_unban_user,
    # User approval
    callback_approve_user,
    callback_reject_user,
    cmd_pending_users,
    # Manual operations
    cmd_manual_shake_deduction,
    get_manual_shake_deduction_handler,
    # QR/Attendance
    cmd_qr_attendance_link,
    cmd_override_attendance,
    cmd_download_qr_code,
)

__all__ = [
    'get_admin_ids', 'get_admin_users',
    'cmd_pending_attendance', 'callback_review_attendance', 'callback_approve_attend', 'callback_reject_attend',
    'cmd_pending_shakes', 'callback_review_shakes', 'callback_ready_shake', 'callback_cancel_shake',
    'cmd_add_staff', 'cmd_remove_staff', 'cmd_list_staff', 'handle_staff_id_input',
    'cmd_add_admin', 'cmd_remove_admin', 'cmd_list_admins',
    'cmd_list_users', 'cmd_delete_user', 'cmd_ban_user', 'cmd_unban_user',
    'callback_approve_user', 'callback_reject_user', 'cmd_pending_users',
    'cmd_manual_shake_deduction', 'get_manual_shake_deduction_handler',
    'cmd_qr_attendance_link', 'cmd_override_attendance', 'cmd_download_qr_code',
]
