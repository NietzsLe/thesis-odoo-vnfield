# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class HealthCheckController(http.Controller):
    """
    🔗 HEALTH CHECK CONTROLLER
    
    Controller để cho các server khác kiểm tra trạng thái active của server hiện tại.
    Endpoint đơn giản trả về HTTP 200 để xác nhận server đang hoạt động.
    """

    @http.route('/vnfield/health', type='http', auth='none', methods=['GET'], csrf=False)
    def health_check(self):
        """
        🔗 HEALTH CHECK ENDPOINT
        
        Endpoint đơn giản để kiểm tra server status.
        Không cần authentication, chỉ trả về 200 OK.
        
        Returns:
            HTTP Response: 200 OK với basic server info
        """
        try:
            # Basic health check response
            response_data = {
                'status': 'ok',
                'message': 'VNField server is active and running',
                'server': 'vnfield',
                'timestamp': http.request.env['ir.config_parameter'].sudo().get_param('database.create_date', 'unknown')
            }
            
            _logger.info("Health check endpoint accessed successfully")
            
            return request.make_response(
                json.dumps(response_data),
                headers={
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                },
                status=200
            )
            
        except Exception as e:
            _logger.error(f"Health check endpoint error: {str(e)}")
            
            # Even on error, return 200 to indicate server is running
            error_response = {
                'status': 'ok',
                'message': 'VNField server is active (with minor issues)',
                'server': 'vnfield',
                'note': 'Basic connectivity confirmed'
            }
            
            return request.make_response(
                json.dumps(error_response),
                headers={
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                },
                status=200
            )

    @http.route('/vnfield/ping', type='http', auth='none', methods=['GET'], csrf=False)
    def ping(self):
        """
        🏓 SIMPLE PING ENDPOINT
        
        Endpoint cực đơn giản chỉ trả về "pong" để kiểm tra connectivity.
        
        Returns:
            HTTP Response: 200 OK với text "pong"
        """
        return request.make_response(
            "pong",
            headers={
                'Content-Type': 'text/plain',
                'Cache-Control': 'no-cache'
            },
            status=200
        )

    @http.route('/vnfield/status', type='http', auth='none', methods=['GET'], csrf=False)
    def server_status(self):
        """
        📊 SERVER STATUS ENDPOINT
        
        Endpoint chi tiết hơn với thông tin server status.
        
        Returns:
            HTTP Response: 200 OK với detailed server info
        """
        try:
            # Get basic system information
            config_param = request.env['ir.config_parameter'].sudo()
            
            response_data = {
                'status': 'active',
                'server_name': 'VNField Server',
                'application': 'vnfield',
                'version': '17.0.2.0.0',
                'database': request.env.cr.dbname,
                'uptime': 'running',
                'endpoints': {
                    'health': '/vnfield/health',
                    'ping': '/vnfield/ping', 
                    'status': '/vnfield/status'
                },
                'timestamp': http.request.env['ir.config_parameter'].sudo().get_param('database.create_date', 'unknown')
            }
            
            _logger.info("Server status endpoint accessed successfully")
            
            return request.make_response(
                json.dumps(response_data, indent=2),
                headers={
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                },
                status=200
            )
            
        except Exception as e:
            _logger.error(f"Server status endpoint error: {str(e)}")
            
            # Fallback response
            fallback_response = {
                'status': 'active',
                'server_name': 'VNField Server',
                'application': 'vnfield',
                'message': 'Server is running (limited info available)'
            }
            
            return request.make_response(
                json.dumps(fallback_response),
                headers={
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                },
                status=200
            )