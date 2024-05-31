# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64
import json
import requests
from datetime import date, timedelta, datetime

class OdooAPIController(http.Controller):

    @http.route('/web/user/profile', type='http', auth='user')
    def get_profile(self, **kw):
        if not request.session.uid:
            return {'error': 'User not logged in'}
        json_data = []
        user = request.env.user
        employee_id = request.env['hr.employee'].search([('user_id', '=', user.id)])
        user_info = {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'login': user.login,
            'employee_id': employee_id.id,
            'groups': [group.name for group in user.groups_id],
        }
        json_data.append(user_info)
        return json.dumps(json_data)

    @http.route('/web/today/check_in_out', type='http', auth='user')
    def get_today_check_in_out(self, **kw):
        if not request.session.uid:
            return {'error': 'User not logged in'}
        json_data = []
        user = request.env.user
        employee_id = request.env['hr.employee'].search([('user_id', '=', user.id)])
        date_today = date.today()
        attendance = request.env['hr.attendance'].search([('employee_id', '=', employee_id.id), ('check_in', '>=', date_today)])
        user_info = {
            'date': str(date_today),
            'checkin': str(attendance.check_in),
            'checkout': str(attendance.check_out),
            'login': user.login,
            'employee_id': employee_id.id,
        }
        json_data.append(user_info)
        return json.dumps(json_data)

    @http.route('/web/attendance/checkin', type='json', auth='user', methods=['POST'], csrf=False)
    def checkin(self, **kw):
        data = json.loads(http.request.httprequest.data)
        employee_id = data.get('employee_id')
        date_format = "%Y-%m-%d %H:%M:%S"
        date_obj = datetime.strptime(data.get('check_in'), date_format)
        time_check_in = date_obj
        if not employee_id:
            return {'status': 'error', 'message': 'employee_id is required'}

        employee = request.env['hr.employee'].sudo().browse(employee_id)
        if not employee:
            return {'status': 'error', 'message': 'Employee not found'}

        if employee.attendance_state == 'checked_in':
            return {'status': 'error', 'message': 'Already checked in'}

        attendance = request.env['hr.attendance'].sudo().create({
            'employee_id': employee.id,
            'check_in': time_check_in,
        })
        return {'status': 'success', 'attendance_id': attendance.id, 'message': 'Checked in successfully'}

    @http.route('/web/attendance/checkout', type='json', auth='user', methods=['POST'], csrf=False)
    def checkout(self, **kw):
        data = json.loads(http.request.httprequest.data)
        employee_id = data.get('employee_id')
        date_format = "%Y-%m-%d %H:%M:%S"
        date_obj = datetime.strptime(data.get('check_out'), date_format)
        time_check_out = date_obj
        if not employee_id:
            return {'status': 'error', 'message': 'employee_id is required'}

        employee = request.env['hr.employee'].sudo().browse(employee_id)
        if not employee:
            return {'status': 'error', 'message': 'Employee not found'}

        if employee.attendance_state == 'checked_out':
            return {'status': 'error', 'message': 'Already checked out'}

        attendance = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False)
        ], limit=1)
        if not attendance:
            return {'status': 'error', 'message': 'No active check-in found'}

        attendance.sudo().write({'check_out': time_check_out})
        return {'status': 'success', 'attendance_id': attendance.id, 'message': 'Checked out successfully'}
