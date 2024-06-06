# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64
import json
import requests
from datetime import date, timedelta, datetime
from geopy.geocoders import Nominatim
from odoo import exceptions, fields, models, _


class OdooAPIController(http.Controller):

    @http.route('/web/user/profile', type='http', auth='user')
    def get_profile(self, **kw):
        if not request.session.uid:
            return {'error': 'User not logged in'}
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
        return json.dumps(user_info)

    @http.route('/web/today/check_in_out', type='http', auth='user')
    def get_today_check_in_out(self, **kw):
        if not request.session.uid:
            return {'error': 'User not logged in'}
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
        return json.dumps(user_info)

    @http.route('/web/attendance/user_attend', type='http', auth='user')
    def get_user_attend(self, **kw):
        if not request.session.uid:
            return {'error': 'User not logged in'}
        user = request.env.user
        employee_id = request.env['hr.employee'].search([('user_id', '=', user.id)])
        attendance = request.env['hr.attendance'].search(
            [('employee_id', '=', employee_id.id)])
        data_attendance = []
        for data in attendance:
            work_hours_decimal = data.worked_hours
            hours = int(work_hours_decimal)
            minutes_decimal = (work_hours_decimal - hours) * 60
            minutes = int(minutes_decimal)
            seconds_decimal = (minutes_decimal - minutes) * 60
            seconds = int(seconds_decimal)
            time_format = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
            new_checkin = data.check_in + timedelta(hours=7)
            new_checkout = data.check_out + timedelta(hours=7)
            data_attendance.append({
                'name': data.employee_id.name,
                'check_in': str(new_checkin),
                'check_out': str(new_checkout),
                'checkin_latitude': data.checkin_latitude,
                'checkin_longitude': data.checkin_longitude,
                'checkout_latitude': data.checkout_latitude,
                'checkout_longitude': data.checkout_longitude,
                'worked_hours': time_format,
                'checkin_location': data.checkin_location,
                'checkout_location': data.checkout_location,
            })
        return json.dumps(data_attendance)

    @http.route('/web/attendance/checkin', type='json', auth='user', methods=['POST'], csrf=False)
    def checkin(self, **kw):
        data = json.loads(http.request.httprequest.data)
        employee_id = data.get('employee_id')
        # date_format = "%Y-%m-%d %H:%M:%S"
        # date_obj = datetime.strptime(data.get('check_in'), date_format)
        time_check_in = fields.Datetime.now()
        geolocator = Nominatim(user_agent='my-app')
        latitudes = data.get('latitudes')
        longitudes = data.get('longitudes')
        location = geolocator.reverse(str(latitudes) + ', ' + str(longitudes))
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
            'checkin_address': location.address,
            'checkin_latitude': latitudes,
            'checkin_longitude': longitudes,
            'checkin_location': 'https://www.google.com/maps/place/' + location.address,
        })
        return {'status': 'success', 'attendance_id': attendance.id, 'message': 'Checked in successfully'}

    @http.route('/web/attendance/checkout', type='json', auth='user', methods=['POST'], csrf=False)
    def checkout(self, **kw):
        data = json.loads(http.request.httprequest.data)
        employee_id = data.get('employee_id')
        # date_format = "%Y-%m-%d %H:%M:%S"
        # date_obj = datetime.strptime(data.get('check_out'), date_format)
        time_check_out = fields.Datetime.now()
        geolocator = Nominatim(user_agent='my-app')
        latitudes = data.get('latitudes')
        longitudes = data.get('longitudes')
        location = geolocator.reverse(str(latitudes) + ', ' + str(longitudes))
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

        attendance.sudo().write({
            'check_out': time_check_out,
            'checkout_address': location.address,
            'checkout_latitude': latitudes,
            'checkout_longitude': longitudes,
            'checkout_location': 'https://www.google.com/maps/place/' + location.address,
        })
        return {'status': 'success', 'attendance_id': attendance.id, 'message': 'Checked out successfully'}
